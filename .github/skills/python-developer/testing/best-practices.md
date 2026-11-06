# Python Testing & Quality Best Practices

Fast, deterministic testing architectures in modern Python using `pytest`.

---

## 1. Testing Pyramid

- **Pure Domain Unit Tests (70%)**: Test business invariants on pure dataclasses and services using fake Protocol implementations. Zero external I/O, runs in milliseconds.
- **Integration Tests (20%)**: Test real database queries and transaction boundaries using `testcontainers-python` (real PostgreSQL/Redis Docker containers).
- **End-to-End API Tests (10%)**: Test HTTP endpoints with `httpx.AsyncClient(app=app, base_url="http://test")`.

---

## 2. In-Memory Protocol Fakes for Unit Tests

Avoid over-mocking with `unittest.mock.MagicMock` (which easily silently passes invalid method calls). Use typed in-memory fakes implementing the `Protocol`:

```python
# tests/fakes/fake_account_repo.py
from uuid import UUID
from domain.models import Account
from domain.ports import AccountRepositoryPort

class FakeAccountRepository(AccountRepositoryPort):
    def __init__(self) -> None:
        self.accounts: dict[UUID, Account] = {}

    async def get_by_id(self, account_id: UUID) -> Account | None:
        return self.accounts.get(account_id)

    async def update_balance(self, account_id: UUID, new_balance_cents: int) -> None:
        acc = self.accounts[account_id]
        self.accounts[account_id] = Account(
            id=acc.id,
            owner_email=acc.owner_email,
            balance_cents=new_balance_cents,
            created_at=acc.created_at,
        )
```

---

## 3. Pytest Fixture Scope & Isolation

- Use `scope="function"` (the default) for anything that mutates state (DB transactions, in-memory repositories).
- Use `scope="session"` only for immutable read-only resources (e.g. running Testcontainer container instance).
- Always use `yield` in fixtures to ensure teardown runs even when tests fail.

