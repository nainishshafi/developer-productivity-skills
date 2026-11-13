# FastAPI: Middleware, Exception Handling & App Wiring

This guide covers FastAPI-specific cross-cutting wiring in `main.py` and `core/`—middleware, global exception handlers, typed configuration, and app factory composition—and links to the shared reference modules for common concerns.

---

## 1. Middleware Architecture (ASGI vs. `BaseHTTPMiddleware`)

FastAPI delegates HTTP middleware to **Starlette**. Middleware wraps every request/response globally and executes in **LIFO registration order** (the last middleware added via `app.add_middleware(...)` is the outermost layer and runs first on incoming requests).

### Prefer Pure ASGI Middleware for Production
Starlette's `BaseHTTPMiddleware` buffers streaming responses and can break `contextvars` or `StreamingResponse` backpressure. For production telemetry, correlation IDs, or header injection, write a **pure ASGI middleware**:

```python
# src/core/middleware.py
import time
import uuid
from starlette.types import ASGIApp, Message, Receive, Scope, Send

class RequestContextMiddleware:
    """Pure ASGI middleware for correlation IDs and request timing without buffering."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = dict(scope.get("headers", []))
        request_id = headers.get(b"x-request-id", b"").decode() or str(uuid.uuid4())
        start = time.perf_counter()

        async def send_wrapper(message: Message) -> None:
            if message["type"] == "http.response.start":
                elapsed_ms = (time.perf_counter() - start) * 1000
                resp_headers = list(message.get("headers", []))
                resp_headers.append((b"x-request-id", request_id.encode()))
                resp_headers.append((b"x-process-time-ms", f"{elapsed_ms:.2f}".encode()))
                message["headers"] = resp_headers
            await send(message)

        await self.app(scope, receive, send_wrapper)
```

### Built-In Starlette / FastAPI Middlewares
- **`CORSMiddleware`** (`fastapi.middleware.cors`): Register **last** (outermost) so preflight `OPTIONS` requests and error responses receive CORS headers.
- **`TrustedHostMiddleware`** (`fastapi.middleware.trustedhost`): Rejects requests with spoofed `Host` headers.
- **`GZipMiddleware`** (`fastapi.middleware.gzip`): Compresses responses above `minimum_size` bytes (avoid on `text/event-stream` SSE routes).

> **Middleware vs. `Depends` vs. Decorators**: Use middleware only for global HTTP concerns that do not need route-level auth or DB sessions. See [AOP & Decorators](../aspect-oriented-programming/aop-and-decorators.md) for the full decision matrix.

---

## 2. Global Exception Handlers (`@app.exception_handler`)

Keep domain services decoupled from HTTP by raising pure Python domain exceptions in `src/common/exceptions.py`, then translating them centrally in `main.py`:

```python
# src/common/exceptions.py
class DomainError(Exception):
    def __init__(self, message: str, code: str = "DOMAIN_ERROR", status_code: int = 400) -> None:
        self.message = message
        self.code = code
        self.status_code = status_code
        super().__init__(message)

class ResourceNotFoundError(DomainError):
    def __init__(self, resource: str, identifier: str) -> None:
        super().__init__(
            message=f"{resource} '{identifier}' was not found.",
            code="NOT_FOUND",
            status_code=404,
        )
```

```python
# src/core/exception_handlers.py
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from src.common.exceptions import DomainError

def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(DomainError)
    async def domain_error_handler(request: Request, exc: DomainError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": {"code": exc.code, "message": exc.message}},
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "Request validation failed.",
                    "details": exc.errors(),
                }
            },
        )
```

---

## 3. Typed Configuration (`pydantic-settings`)

Centralize environment variables in `src/core/config.py` using `pydantic-settings` and `@lru_cache`:

```python
# src/core/config.py
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    APP_NAME: str = "Order Fulfillment Service"
    ENVIRONMENT: str = "development"
    DATABASE_URL: str
    CORS_ORIGINS: list[str] = ["http://localhost:3000"]

@lru_cache
def get_settings() -> Settings:
    return Settings()
```

---

## 4. App Factory Wiring (`src/main.py`)

Use a `create_app()` factory to keep test instantiation clean and guarantee middleware registration order:

```python
# src/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from src.core.config import get_settings
from src.core.exception_handlers import register_exception_handlers
from src.core.lifespan import lifespan
from src.core.middleware import RequestContextMiddleware
from src.modules.orders.router import router as orders_router
from src.modules.users.router import router as users_router

def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.APP_NAME,
        lifespan=lifespan,
        docs_url="/docs" if settings.ENVIRONMENT != "production" else None,
        redoc_url=None,
    )

    # Middleware (registered in reverse execution order; last = outermost)
    app.add_middleware(GZipMiddleware, minimum_size=1024)
    app.add_middleware(RequestContextMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_exception_handlers(app)

    app.include_router(users_router, prefix="/api/v1")
    app.include_router(orders_router, prefix="/api/v1")
    return app

app = create_app()
```

---

## 5. Related FastAPI & Common Reference Docs

- **FastAPI Core Patterns** (Lifespan, Feature-Slice Layout, `APIRouter`, `Depends`, `BackgroundTasks`, `StreamingResponse`): [architecture-and-best-practices.md](architecture-and-best-practices.md)
- **AOP, Decorators & Middleware vs. `Depends`**: [aop-and-decorators.md](../aspect-oriented-programming/aop-and-decorators.md)
- **API Security, CORS, JWT & Rate Limiting**: [api-security.md](../security-and-auth/api-security.md)
- **Pydantic v2 Validation & Payload Size Limits**: [data-validation-and-schemas.md](../validation-and-data/data-validation-and-schemas.md)
- **Async Event Loop Hygiene**: [event-loop-hygiene.md](../async-and-concurrency/event-loop-hygiene.md)
- **SQLAlchemy 2.0, Migrations & Pooling**: [orms-and-migrations.md](../persistence/orms-and-migrations.md)
- **Automated API Testing (`httpx.AsyncClient` & `dependency_overrides`)**: [api-testing-patterns.md](../testing/api-testing-patterns.md)

