# Python Architectural Styles & Discovery

Guidance on identifying, choosing, and implementing architectural patterns in modern Python (3.10–3.13).

---

## 1. Architectural Style Comparison Matrix

| Architecture Style | Ideal When | Drawbacks / Risks | Python Implementation Pattern |
|---|---|---|---|
| **Layered (Router / Service / Repo)** | Standard CRUD APIs, small to medium FastAPI/Flask services. | Potential layer bloat; pass-through methods if domain logic is thin. | `api/` -> `services/` -> `repositories/` -> `models/`. |
| **Feature-Based / Vertical Slice** | Multi-domain services, modular monoliths worked on by multiple engineers. | Cross-feature sharing requires intentional shared packages or event dispatchers. | Packages grouped by capability (`app/billing/`, `app/users/`), keeping models and handlers cohesive. |
| **Hexagonal (Ports & Adapters)** | Rich business domain, multiple database backends, automated unit-testing without DB. | Mapping boilerplate between domain entities and persistence/ORM models. | `typing.Protocol` for Ports; concrete classes in `adapters/`; pure models in `domain/`. |
| **Functional / Pipeline** | ETL pipelines, data science scripts, CLI automation utilities. | Less suitable for complex entity state transitions with relational dependencies. | Pure functions, generator streams, `itertools`, immutable dataclasses. |

---

## 2. Implementing Ports & Adapters in Modern Python

### A. The Domain & Port (Pure Python, Zero Framework Dependencies)
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

### B. The Application Service (Orchestration & Business Logic)
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

### C. The Infrastructure Adapter (SQLAlchemy / SQLModel)
```python
# infrastructure/adapters/sql_account_repository.py
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from domain.models import Account
from domain.ports import AccountRepositoryPort

class SqlAccountRepository(AccountRepositoryPort):
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

## 3. Discovery Guide for Codebases

When inspecting an unfamiliar Python codebase:
1. **Toolchain & Version**: Inspect `pyproject.toml`, `setup.cfg`, or `requirements.txt`. Note package manager (`uv`, `poetry`, `pip`).
2. **Architecture Style**:
   - If routers directly call `db.execute()` or import ORM models: Keep changes direct; do not force a multi-layer abstraction.
   - If services and repositories exist: Respect the abstraction layers.
3. **Dependency Injection**: If FastAPI uses `Depends(get_service)`, follow dependency injection rather than instantiating global state.

