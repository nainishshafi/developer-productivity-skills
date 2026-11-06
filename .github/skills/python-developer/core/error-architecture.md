# Python Error Architecture & Resilience

Design robust error handling by establishing domain exception hierarchies and handling errors at architectural boundaries.

---

## 1. Structured Domain Exception Hierarchy

Define explicit, typed exception classes for business rule violations rather than raising generic `ValueError` or `Exception`:

```python
# domain/exceptions.py
class DomainError(Exception):
    """Base exception for all business domain errors."""
    def __init__(self, message: str, code: str = "DOMAIN_ERROR") -> None:
        super().__init__(message)
        self.message = message
        self.code = code

class EntityNotFoundError(DomainError):
    def __init__(self, entity_name: str, entity_id: str) -> None:
        super().__init__(f"{entity_name} with ID '{entity_id}' not found.", code="NOT_FOUND")
        self.entity_name = entity_name
        self.entity_id = entity_id

class InsufficientBalanceError(DomainError):
    def __init__(self, current_cents: int, requested_cents: int) -> None:
        super().__init__(
            f"Insufficient balance: {current_cents} < {requested_cents}.",
            code="INSUFFICIENT_FUNDS"
        )
```

---

## 2. Boundary Exception Translation (FastAPI / Web APIs)

Catch domain exceptions in API middleware or global exception handlers to translate them into clean HTTP status codes, keeping presentation logic separated from domain code:

```python
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from domain.exceptions import EntityNotFoundError, DomainError

app = FastAPI()

@app.exception_handler(EntityNotFoundError)
async def not_found_handler(request: Request, exc: EntityNotFoundError) -> JSONResponse:
    return JSONResponse(
        status_code=404,
        content={"error": exc.code, "message": exc.message}
    )

@app.exception_handler(DomainError)
async def domain_error_handler(request: Request, exc: DomainError) -> JSONResponse:
    return JSONResponse(
        status_code=400,
        content={"error": exc.code, "message": exc.message}
    )
```

---

## 3. Context Managers for Transaction Boundaries

Always manage database transactions and external resources with context managers (`with` / `async with`):

```python
from contextlib import asynccontextmanager
from typing import AsyncIterator

class UnitOfWork:
    def __init__(self, session_factory) -> None:
        self._session_factory = session_factory

    @asynccontextmanager
    async def transaction(self) -> AsyncIterator["UnitOfWork"]:
        async with self._session_factory() as session:
            async with session.begin():
                yield self
```

