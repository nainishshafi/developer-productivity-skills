# Python Developer Architectural Reference Guide

Deep-dive patterns, architectural trade-offs, and reference implementations for Python codebases.

---

## 1. Architectural Style Comparison Matrix

| Architecture Style | Ideal When | Drawbacks / Risks | Python Implementation Mechanism |
|---|---|---|---|
| **Layered (Controller / Service / Repo)** | Standard CRUD APIs, small to medium web services, team familiarity is priority. | Potential layer bloat, trampoline pass-through methods if domain logic is thin. | FastAPI routers -> Service classes -> SQLAlchemy async repositories -> Pydantic schemas. |
| **Feature-Based / Vertical Slice** | Large applications with multiple domains (e.g. auth, billing, inventory) developed by multiple engineers. | Cross-feature sharing requires intentional shared packages or event dispatchers. | Packages grouped by business capability (`app/billing/`, `app/users/`), keeping models and handlers cohesive. |
| **Hexagonal (Ports & Adapters)** | Complex domain logic, multiple database backends, high requirement for unit-test isolation without DB. | Increased boilerplate, mapping overhead between domain and persistence models. | `typing.Protocol` for Ports; concrete classes in `adapters/`; pure domain models in `domain/`. |
| **Functional / Pipeline** | Data transformations, ETL pipelines, CLI automation, background workers. | Less suitable for complex entity state transitions with relational dependencies. | Pure functions, generator streams, `itertools`, immutable dataclasses. |

---

## 2. Implementing Ports & Adapters in Modern Python

### The Domain & Port (Pure Python, Zero Framework Dependencies)
```python
# domain/models.py
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

@dataclass(slots=True, frozen=True)
class Account:
    id: UUID
    owner_email: str
    balance_cents: int
    created_at: datetime

    def can_withdraw(self, amount_cents: int) -> bool:
        return self.balance_cents >= amount_cents

# domain/ports.py
from typing import Protocol

class AccountRepositoryPort(Protocol):
    async def get_by_id(self, account_id: UUID) -> Account | None: ...
    async def update_balance(self, account_id: UUID, new_balance_cents: int) -> None: ...
```

### The Application Service (Orchestration & Business Logic)
```python
# application/transfer_service.py
from uuid import UUID
from domain.ports import AccountRepositoryPort
from domain.exceptions import InsufficientFundsError, AccountNotFoundError

class TransferService:
    def __init__(self, repo: AccountRepositoryPort) -> None:
        self._repo = repo

    async def transfer(self, from_id: UUID, to_id: UUID, amount_cents: int) -> None:
        sender = await self._repo.get_by_id(from_id)
        if not sender:
            raise AccountNotFoundError(f"Sender account {from_id} not found")

        receiver = await self._repo.get_by_id(to_id)
        if not receiver:
            raise AccountNotFoundError(f"Receiver account {to_id} not found")

        if not sender.can_withdraw(amount_cents):
            raise InsufficientFundsError("Insufficient funds for transfer")

        await self._repo.update_balance(from_id, sender.balance_cents - amount_cents)
        await self._repo.update_balance(to_id, receiver.balance_cents + amount_cents)
```

### The Adapter (Infrastructure Implementation)
```python
# infrastructure/adapters/sql_account_repository.py
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from domain.models import Account

class SqlAccountRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, account_id: UUID) -> Account | None:
        # Query database and map to pure domain Account dataclass
        ...

    async def update_balance(self, account_id: UUID, new_balance_cents: int) -> None:
        # Execute update query
        ...
```

---

## 3. Testing Architecture: The Testing Pyramid

When architecting tests in Python:

1. **Domain Unit Tests (Base)**:
   - Fast, in-memory, zero I/O. Test business invariants and domain rules directly on pure models and services using fake/in-memory implementations of Ports.
2. **Integration Tests (Middle)**:
   - Test adapters against real external boundaries (e.g., using `testcontainers-python` for real PostgreSQL or Redis instances). Verify SQL queries, transactions, and connection pools.
3. **End-to-End / API Contract Tests (Top)**:
   - Use `httpx.AsyncClient` with `app` to verify full HTTP request/response flows, status codes, serialization, and error response shapes.

---

## 4. Discovery Guide for LLMs

When analyzing an existing Python codebase, look for these architectural signals:

```python
# 1. Check imports in API routes:
# If routers directly import SQLAlchemy models or call db.execute():
# -> Project is Layered or Flat. Keep changes direct; do not invent a multi-class port hierarchy.

# 2. Check for dependency injection:
# If routers use `Depends(get_service)` or class constructor injection:
# -> Respect the DI container or factory functions already in place.

# 3. Check for repository classes:
# If repositories exist:
# -> Place all new database queries inside existing or new repository classes. Do not leak raw queries into services.
```
