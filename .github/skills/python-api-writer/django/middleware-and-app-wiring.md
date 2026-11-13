# Django & Django Ninja: Middleware, Exception Handling & App Wiring

This guide covers Django-specific cross-cutting wiring—`MIDDLEWARE` ordering, async-capable custom middleware, DRF & Django Ninja exception handlers, auth/throttling, and split settings—and links to the shared reference modules for common concerns.

---

## 1. Django Middleware Architecture & Ordering

Django processes `MIDDLEWARE` **top-to-bottom on requests** and **bottom-to-top on responses**. Order matters:

```python
# config/settings/base.py
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",          # 1. Security headers / HTTPS redirect
    "corsheaders.middleware.CorsMiddleware",                # 2. CORS (must precede CommonMiddleware)
    "django.middleware.common.CommonMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "apps.common.middleware.RequestContextMiddleware",      # Custom correlation ID & timing
]
```

### Writing Async-Capable Middleware (WSGI + ASGI Safe)
When running Django under ASGI (Uvicorn/Daphne) with `async def` views, synchronous-only middleware forces Django to run an extra thread/sync-async adapter per request. Use `sync_and_async_middleware` so the middleware stays non-blocking on ASGI while still working on WSGI:

```python
# apps/common/middleware.py
import time
import uuid
from asgiref.sync import iscoroutinefunction
from django.utils.decorators import sync_and_async_middleware

@sync_and_async_middleware
def RequestContextMiddleware(get_response):
    if iscoroutinefunction(get_response):
        async def middleware(request):
            request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
            request.request_id = request_id
            start = time.perf_counter()
            response = await get_response(request)
            response["X-Request-ID"] = request_id
            response["X-Process-Time-Ms"] = f"{(time.perf_counter() - start) * 1000:.2f}"
            return response
    else:
        def middleware(request):
            request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
            request.request_id = request_id
            start = time.perf_counter()
            response = get_response(request)
            response["X-Request-ID"] = request_id
            response["X-Process-Time-Ms"] = f"{(time.perf_counter() - start) * 1000:.2f}"
            return response

    return middleware
```

---

## 2. Global Exception Handling (DRF & Django Ninja)

Keep service modules decoupled from HTTP by raising pure domain exceptions (`DomainError`) and translating them at the API boundary.

### Django REST Framework (`EXCEPTION_HANDLER`)
```python
# apps/common/exceptions.py
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler

class DomainError(Exception):
    def __init__(self, message: str, code: str = "DOMAIN_ERROR", status_code: int = 400) -> None:
        self.message = message
        self.code = code
        self.status_code = status_code
        super().__init__(message)

def custom_drf_exception_handler(exc, context):
    if isinstance(exc, DomainError):
        return Response(
            {"error": {"code": exc.code, "message": exc.message}},
            status=exc.status_code,
        )
    response = exception_handler(exc, context)
    if response is not None:
        response.data = {
            "error": {
                "code": getattr(exc, "default_code", "API_ERROR"),
                "message": response.data,
            }
        }
    return response
```

Register it in `REST_FRAMEWORK`:
```python
REST_FRAMEWORK = {
    "EXCEPTION_HANDLER": "apps.common.exceptions.custom_drf_exception_handler",
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.CursorPagination",
    "PAGE_SIZE": 50,
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.UserRateThrottle",
        "rest_framework.throttling.AnonRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {"user": "1000/hour", "anon": "100/hour"},
}
```

### Django Ninja (`@api.exception_handler`)
```python
# config/api.py
from ninja import NinjaAPI
from ninja.security import HttpBearer
from apps.common.exceptions import DomainError

class BearerAuth(HttpBearer):
    def authenticate(self, request, token: str):
        # Validate JWT/token and return user or None
        return verify_jwt_and_get_user(token)

api = NinjaAPI(title="E-Commerce API", version="1.0.0", auth=BearerAuth())

@api.exception_handler(DomainError)
def handle_domain_error(request, exc: DomainError):
    return api.create_response(
        request,
        {"error": {"code": exc.code, "message": exc.message}},
        status=exc.status_code,
    )
```

---

## 3. Recommended Directory Layout & Split Settings

Organize by domain app and split environment settings so production secrets and `DEBUG=False` are never mixed with local defaults:

```
project/
├── config/
│   ├── settings/
│   │   ├── base.py          # Shared INSTALLED_APPS, MIDDLEWARE, REST_FRAMEWORK
│   │   ├── local.py         # DEBUG=True, local DB, console email backend
│   │   └── production.py    # SECURE_SSL_REDIRECT, CONN_MAX_AGE, Redis cache
│   ├── asgi.py
│   ├── wsgi.py
│   └── urls.py              # Mounts /api/v1/ (DRF routers or NinjaAPI)
└── apps/
    ├── common/
    │   ├── exceptions.py    # DomainError + DRF exception handler
    │   └── middleware.py    # RequestContextMiddleware
    ├── users/
    └── orders/
        ├── models.py        # Models + custom QuerySet/Manager
        ├── services.py      # @transaction.atomic business logic
        ├── schemas.py       # Ninja Schemas or DRF Serializers
        ├── api.py           # Thin views/ViewSets/Ninja routers
        └── tests.py
```

### Database Connection Persistence (`CONN_MAX_AGE`)
In `config/settings/production.py`, avoid opening a fresh TCP/TLS connection on every request:
- Set `CONN_MAX_AGE = 60` (or `CONN_HEALTH_CHECKS = True` in Django 4.1+) for persistent connections, or `CONN_MAX_AGE = 0` when routing through **PgBouncer** in transaction pooling mode.

---

## 4. Related Django & Common Reference Docs

- **Django Core Patterns** (DRF vs. Django Ninja, Service Layer, `@transaction.atomic`, N+1 Prevention, Custom Managers): [architecture-and-best-practices.md](architecture-and-best-practices.md)
- **AOP, Decorators & `@method_decorator` for CBVs**: [aop-and-decorators.md](../aspect-oriented-programming/aop-and-decorators.md)
- **API Security, JWT vs. Sessions, CORS & Rate Limiting**: [api-security.md](../security-and-auth/api-security.md)
- **Validation & Schemas (Pydantic v2 / Django Ninja & DRF Serializers)**: [data-validation-and-schemas.md](../validation-and-data/data-validation-and-schemas.md)
- **Async Views & Django Async ORM (`a-` methods)**: [event-loop-hygiene.md](../async-and-concurrency/event-loop-hygiene.md)
- **ORMs & Connection Pooling**: [orms-and-migrations.md](../persistence/orms-and-migrations.md)
- **Automated API Testing (`pytest-django`)**: [api-testing-patterns.md](../testing/api-testing-patterns.md)

