---
name: python-developer
description: Architectural and engineering guidance for modern Python development (3.10–3.13). Helps the LLM analyze existing project architecture, adapt to codebase conventions, and apply clean architecture, domain modeling, and testing patterns pragmatically without imposing dogmatic hard rules. Use when designing, writing, reviewing, or refactoring Python code, or when the user asks to "write python code", "develop python service", "python architecture best practices", "design python backend", or "refactor python".
version: 1.1.0
---

# Python Developer Skill

An architectural guidance framework for modern Python (3.10–3.13). This skill is **not an inflexible rulebook**; it guides the LLM to inspect, discover, and respect the project's existing architecture while applying battle-tested architectural best practices.

---

## 1. Adaptive Architectural Discovery (Find First, Then Align)

Before generating or modifying Python code, the LLM must **inspect the project context**:

1. **Detect Toolchain & Version**:
   - Check `pyproject.toml`, `setup.cfg`, `Pipfile`, or `requirements.txt` to identify the Python version, package manager (`uv`, `poetry`, `pipenv`), and installed libraries.
   - Never introduce syntax, libraries, or patterns incompatible with the project's baseline.
2. **Identify the Architecture Style**:
   - **Layered Architecture** (`routers/` -> `services/` -> `repositories/` -> `models/`): Common in CRUD and FastAPI services.
   - **Feature-Based / Modular Monolith** (`users/`, `billing/`, `catalog/` each with their own domain and handlers): Common in growing medium-to-large apps.
   - **Hexagonal / Clean Architecture** (`domain/`, `application/`, `infrastructure/`, `adapters/`): Common in enterprise, domain-rich systems.
   - **Flat / Lightweight Scripting**: Common in CLI tools, data pipelines, and automation utilities.
   - *Rule:* Match the established architectural style. Do not force hexagonal abstractions on a 50-line utility, and do not dump raw SQL into routers in a layered service.
3. **Assess Conventions & Libraries**:
   - ORM / Persistence: SQLAlchemy (sync/async), SQLModel, Tortoise, Peewee, or raw queries?
   - Data Validation: Pydantic v1, Pydantic v2, dataclasses, or attrs?
   - Web/API Framework: FastAPI, Flask, Django, Litestar, or a CLI framework (Click/Typer)?
   - Testing Framework: `pytest`, `unittest`, or custom fixtures?

---

## 2. Core Architectural Principles in Python

### A. Separation of Concerns & Boundary Defense
- **Domain Layer (Core)**: Pure business entities and domain rules. Keep it free of framework dependencies, raw HTTP logic, and direct database drivers.
- **Application Layer (Use Cases)**: Coordinates domain objects and external services. Encapsulates business transactions and use-case workflows.
- **Infrastructure Layer (Adapters)**: Implements database persistence, external HTTP APIs, message brokers, and filesystem interactions.
- **Presentation Layer (Interfaces)**: HTTP routers, GraphQL resolvers, or CLI commands. Keep controllers thin: validate input, call use case, return DTO/response.

### B. Dependency Inversion via `typing.Protocol`
Use Python's structural subtyping (`typing.Protocol`) to decouple high-level application logic from low-level infrastructure without heavyweight inheritance:

```python
from typing import Protocol, runtime_checkable

@runtime_checkable
class OrderRepository(Protocol):
    async def get_by_id(self, order_id: str) -> Order | None: ...
    async def save(self, order: Order) -> None: ...

# Application service depends on the Protocol, not on the concrete database class
class OrderService:
    def __init__(self, repo: OrderRepository) -> None:
        self._repo = repo
```

### C. Domain Modeling & Immutability
- Choose the modeling tool matching project conventions:
  - When Pydantic is already the standard: use `BaseModel` with `model_config = ConfigDict(frozen=True)` for immutable DTOs/value objects.
  - When lightweight stdlib is preferred: use `@dataclass(slots=True, frozen=True)` for domain entities and value objects.
- Separate **Domain Entities** (internal business logic) from **API DTOs** (public request/response contracts) to prevent external changes from leaking into business rules.

### D. Error Architecture & Resilience
- Prefer domain-specific exception hierarchies over generic `Exception` or string error messages:
  - `DomainError` -> `EntityNotFoundError`, `BusinessRuleViolationError`, `UnauthorizedError`.
- Catch exceptions at architectural boundaries (e.g. middleware or presentation exception handlers) to translate them into appropriate API status codes.
- Use context managers (`with`, `async with`) for all resource lifecycles (DB sessions, files, sockets) to prevent resource leaks.

---

## 3. Practical Architecture Patterns

### Pattern 1: Feature-Based / Hexagonal Layout
For enterprise and multi-domain services:

```text
src/app/
├── billing/                       # Domain / Feature package
│   ├── domain/                    # Pure domain models and business rules
│   │   ├── models.py
│   │   └── exceptions.py
│   ├── ports/                     # Interfaces / Protocols
│   │   └── repository.py
│   ├── services.py                # Application use cases / orchestration
│   └── adapters/                  # Infrastructure implementations
│       ├── sql_repository.py
│       └── stripe_gateway.py
└── api/                           # Presentation layer
    └── v1/
        └── billing_router.py
```

### Pattern 2: Lightweight Service-Repository Layout
For standard microservices and web APIs:

```text
src/app/
├── api/          # Thin routers/controllers, request validation, response serialization
├── services/     # Business logic, workflow coordination, transaction orchestration
├── repositories/ # Data access, query building, database sessions
├── schemas/      # Request/response DTOs (Pydantic / dataclasses)
└── models/       # Database ORM entities (SQLAlchemy / SQLModel)
```

---

## 4. Architectural Pragmatism (Avoid Over-Engineering)

- **Do Not Dogmatically Enforce Complexity**: If a simple function or a 10-line class solves the problem cleanly, do not create 4 layers of interfaces, factories, and adapters (adhere to YAGNI and KISS).
- **Follow Existing Patterns Over Idealized Ones**: Consistency across the codebase is more important than theoretical purity. If the project uses a standard repository pattern, adopt that pattern rather than rewriting it in hexagonal ports.
- **Evolutionary Architecture**: Start simple. Refactor toward deeper boundary separation only when multiple implementations exist or when domain complexity genuinely demands it.

---

## References

- [Python Developer Reference Guide](file:///.github/skills/python-developer/references/python-developer-reference.md) — Architectural case studies, repository implementations, and dependency injection patterns.
