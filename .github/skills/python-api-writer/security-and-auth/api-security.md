# API Security & Authentication in Python

Production Python APIs require strict defense-in-depth across authentication, authorization, CORS boundaries, input sanitization, and rate limiting.

---

## 1. Authentication: JWT vs. Stateful Sessions

| Strategy | When to Use | Mechanism | Token Revocation |
|---|---|---|---|
| **Stateless JWT (Bearer)** | Mobile clients, cross-domain microservices, distributed public APIs | Signed JSON payload containing `sub`, `exp`, `roles` verified with public/private RSA key or HMAC secret. | Difficult without a centralized Redis token blacklist or short TTL (e.g. 15 minutes) + Refresh token. |
| **Stateful Sessions (HttpOnly Cookie)** | Single-Page Apps (SPA) on same domain or first-party frontend | Random session ID stored in HttpOnly, Secure, SameSite=Lax cookie; state held in Redis or DB. | Trivial; instant server-side revocation on logout or compromise. |

---

## 2. FastAPI JWT Implementation Pattern

```python
from datetime import datetime, timedelta, timezone
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
import jwt
from pydantic import BaseModel

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

SECRET_KEY = "your-production-secret-loaded-from-env"
ALGORITHM = "HS256"

class TokenPayload(BaseModel):
    sub: str
    role: str
    exp: datetime

def create_access_token(user_id: str, role: str) -> str:
    expires = datetime.now(timezone.utc) + timedelta(minutes=15)
    payload = {"sub": user_id, "role": role, "exp": expires}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

async def get_current_user(token: str = Depends(oauth2_scheme)) -> TokenPayload:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        data = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return TokenPayload(**data)
    except (jwt.PyJWTError, ValueError):
        raise credentials_exception

# Role-Based Access Control (RBAC) dependency factory
def require_role(required_role: str):
    async def role_checker(current_user: TokenPayload = Depends(get_current_user)):
        if current_user.role != required_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )
        return current_user
    return role_checker
```

---

## 3. CORS Configuration Hygiene

A common vulnerability is setting `allow_origins=["*"]` combined with `allow_credentials=True`, which either throws browser security errors or opens cross-origin session theft.

```python
from fastapi.middleware.cors import CORSMiddleware

# ✅ SAFE: Explicit allowed origins loaded from environment
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://app.example.com",
        "https://admin.example.com"
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
    max_age=86400  # Cache preflight response for 24 hours
)
```

---

## 4. Rate Limiting with Redis

Protect endpoints against brute-force attacks and volumetric DoS:

### In FastAPI (via `slowapi`):
```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address, default_limits=["100/minute"])
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@app.post("/auth/login")
@limiter.limit("5/minute")  # Strict limit for authentication
async def login(request: Request):
    ...
```

---

## 5. Type-Safe Configuration with `pydantic-settings`

Never access raw `os.environ.get()` strings throughout codebase modules:

```python
# src/core/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import PostgresDsn, RedisDsn

class Settings(BaseSettings):
    ENVIRONMENT: str = "production"
    DEBUG: bool = False
    SECRET_KEY: str
    DATABASE_URL: PostgresDsn
    REDIS_URL: RedisDsn

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )

settings = Settings()
```

