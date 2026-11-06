# Pydantic v2 Architecture, Validation & Settings

Enterprise patterns for data modeling, boundary defense, serialization, and settings management using modern Pydantic v2.

---

## 1. Pydantic v2 Fundamentals

Pydantic v2 is powered by a high-performance Rust validation engine (`pydantic-core`). It enforces validation, parsing, and serialization at API boundaries.

### The Standard Secure Model
```python
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict, EmailStr, Field

class UserModel(BaseModel):
    model_config = ConfigDict(
        frozen=True,               # Immutable instances (hashable, prevents accidental mutation)
        extra="forbid",            # Rejects unknown fields (prevents mass-assignment vulnerabilities)
        str_strip_whitespace=True, # Automatically strips leading/trailing spaces
        populate_by_name=True,     # Allows instantiating with alias or python field name
    )

    id: UUID
    email: EmailStr
    username: str = Field(min_length=3, max_length=50, pattern=r"^[a-zA-Z0-9_-]+$")
    created_at: datetime
```

---

## 2. Field & Model Validators (v2 Syntax)

### `@field_validator` (Per-Field Validation)
Use `mode="after"` (default) to validate parsed typed objects; use `mode="before"` only if raw strings/types must be pre-sanitized:

```python
from pydantic import BaseModel, field_validator

class TransactionModel(BaseModel):
    amount_cents: int
    currency: str

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, v: str) -> str:
        upper = v.upper()
        if upper not in {"USD", "EUR", "GBP"}:
            raise ValueError(f"Unsupported currency: {v}")
        return upper
```

### `@model_validator` (Cross-Field Invariants)
Validate invariants spanning multiple fields:

```python
from datetime import date
from pydantic import BaseModel, model_validator

class DateRange(BaseModel):
    start_date: date
    end_date: date

    @model_validator(mode="after")
    def validate_date_order(self) -> "DateRange":
        if self.end_date < self.start_date:
            raise ValueError("end_date cannot be earlier than start_date")
        return self
```

---

## 3. Computed Fields & Hidden Secrets

### Masking Sensitive Data with `SecretStr`
Never store plain passwords, API keys, or JWT tokens in standard `str` fields. `SecretStr` masks values when printed or logged:

```python
from pydantic import BaseModel, SecretStr

class DatabaseConfig(BaseModel):
    host: str
    password: SecretStr

config = DatabaseConfig(host="localhost", password="my-secret-password")
print(config)  # Output: host='localhost' password=SecretStr('**********')

# Extract raw value only when passing to secure DB driver:
raw_secret = config.password.get_secret_value()
```

### `@computed_field`
Expose dynamically calculated properties in JSON outputs and serialization:

```python
from pydantic import BaseModel, computed_field

class Rectangle(BaseModel):
    width: float
    height: float

    @computed_field
    @property
    def area(self) -> float:
        return self.width * self.height
```

---

## 4. Validating Arbitrary Types with `TypeAdapter`

When validating lists, tuples, or primitives without wrapping them in a dummy model, use `TypeAdapter`:

```python
from pydantic import TypeAdapter

# Validate a raw list of integers
int_list_adapter = TypeAdapter(list[int])
parsed = int_list_adapter.validate_python(["1", 2, "3"])  # [1, 2, 3]

# Zero-cost deserialization directly from raw JSON bytes
parsed_from_json = int_list_adapter.validate_json(b'[1, 2, 3]')
```

---

## 5. Application Configuration with `pydantic-settings`

Manage environment variables, `.env` files, and secrets in a type-safe manner:

```python
# app/core/config.py
from pydantic import PostgresDsn, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "My Microservice"
    environment: str = "production"
    port: int = 8000
    database_url: PostgresDsn
    jwt_secret_key: SecretStr

# Instantiate singleton
settings = AppSettings()
```

---

## 6. Migration Traps: Pydantic v1 vs v2

| Pydantic v1 (Deprecated) | Pydantic v2 (Modern Standard) |
|---|---|
| `model.dict()` | `model.model_dump()` |
| `model.json()` | `model.model_dump_json()` |
| `Model.parse_obj(data)` | `Model.model_validate(data)` |
| `Model.parse_raw(json_str)` | `Model.model_validate_json(json_str)` |
| `@validator('field')` | `@field_validator('field', mode='after')` |
| `@root_validator` | `@model_validator(mode='after')` |
| `class Config:` | `model_config = ConfigDict(...)` |
| `BaseSettings` in `pydantic` | `from pydantic_settings import BaseSettings` |

