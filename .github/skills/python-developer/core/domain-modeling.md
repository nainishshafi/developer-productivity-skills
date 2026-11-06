# Python Domain Modeling & Immutability

Guidelines for modeling clean business domains using modern Python features (dataclasses, Pydantic v2, and Protocols).

---

## 1. Domain Modeling with `@dataclass`

For domain models that should remain free of third-party framework dependencies, use Python standard library dataclasses with `slots=True` and `frozen=True`:

```python
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

@dataclass(slots=True, frozen=True)
class Customer:
    id: UUID
    email: str
    is_verified: bool
    created_at: datetime

    def can_place_order(self) -> bool:
        return self.is_verified
```

**Why `slots=True` and `frozen=True`?**
- `slots=True`: Drastically reduces memory usage by eliminating the dynamic `__dict__` and speeds up attribute access.
- `frozen=True`: Enforces immutability, preventing accidental mutation of domain state and allowing instances to be hashable (usable in sets or dict keys).

---

## 2. Pydantic v2 for API Contracts & DTOs

Use Pydantic v2 for parsing and validating external untrusted inputs at the API presentation boundary:

```python
from pydantic import BaseModel, ConfigDict, EmailStr, Field

class CreateCustomerRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    email: EmailStr
    name: str = Field(min_length=1, max_length=100)
    age: int = Field(ge=18, le=120)
```

---

## 3. Separating Internal Domain Models from Public DTOs

Never return raw database ORM models (SQLAlchemy / Tortoise) or domain entities containing private data directly in API endpoints:

```python
# Domain Entity (Internal)
@dataclass(slots=True, frozen=True)
class UserEntity:
    id: str
    email: str
    password_hash: str  # Sensitive internal secret!
    is_active: bool

# Public DTO
class UserResponse(BaseModel):
    id: str
    email: str
    is_active: bool

    @classmethod
    def from_entity(cls, entity: UserEntity) -> "UserResponse":
        return cls(id=entity.id, email=entity.email, is_active=entity.is_active)
```

---

## 4. Structural Subtyping with `typing.Protocol`

Decouple interfaces without forcing inheritance hierarchies:

```python
from typing import Protocol, runtime_checkable

@runtime_checkable
class Notifier(Protocol):
    async def send_notification(self, recipient: str, body: str) -> None: ...
```

