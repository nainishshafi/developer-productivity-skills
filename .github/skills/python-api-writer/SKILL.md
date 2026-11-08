---
name: python-api-writer
description: Architectural and engineering guidance for building modern Python APIs with FastAPI and Django (including Django REST Framework and Django Ninja). Covers framework selection (FastAPI vs Django), async event loop hygiene, Lifespan context managers, modular APIRouter design, Dependency Injection (Depends), Django service-layer patterns, QuerySet & SQLAlchemy 2.0 optimization, and testing. Use when designing, writing, reviewing, or refactoring Python APIs, or when asked to "write python api", "fastapi best practices", "django api best practices", "fastapi vs django", "django ninja", "fastapi dependency injection", or "build python backend".
version: 1.0.0
---

# Python API Writer Skill

You are a Principal Python Backend Architect specializing in high-scale REST APIs, event-driven backends, and asynchronous web services across both **FastAPI** and **Django** (DRF & Django Ninja).

---

## Guiding Principles & Architectural Heuristics

1. **Context & Framework Fit**: Choose FastAPI for lightweight, high-concurrency async microservices, AI/LLM streaming, or polyglot persistence. Choose Django for multi-model relational monoliths where the built-in ORM, migrations, and Admin dashboard provide maximum velocity.
2. **Event Loop Respect**: In FastAPI and async route handlers, never call blocking synchronous libraries (`requests`, standard file I/O, sync DB drivers) inside `async def`. Offload synchronous calls to thread pools (`asyncio.to_thread` or standard `def` routes).
3. **Explicit Data Contracts**: Model all incoming and outgoing API schemas using Pydantic v2 (in FastAPI & Django Ninja) or validated serializers, ensuring automatic OpenAPI 3.1 documentation and runtime boundary defense.
4. **Clean Service Decoupling**: Keep route handlers and ViewSets skinny. Encapsulate business logic, invariant validations, and transactional boundaries in pure service modules.
5. **Eager Loading Discipline**: Prevent $N+1$ query cascades up front (`select_related` and `prefetch_related` in Django; `joinedload` and `selectinload` in SQLAlchemy 2.0).

---

## When to Use FastAPI vs. Django (Agent Decision Matrix)

| Requirement / Workload | Optimal Selection | Anti-Pattern / What to Avoid | Rationale |
|---|---|---|---|
| **High-concurrency microservices, WebSockets, AI/LLM streaming** | **FastAPI** (`async def` + `StreamingResponse`) | Django WSGI monolith | Native ASGI async event loop handles tens of thousands of concurrent I/O connections with minimal memory footprint. |
| **Relational SaaS with operational Admin & User Management** | **Django** or **Django Ninja** | Building custom admin CRUD and user auth from scratch in FastAPI | Django Admin, built-in RBAC, sessions, and auto-migrations save hundreds of engineering hours. |
| **Modern type-hinted API on top of Django ORM** | **Django Ninja** | Legacy DRF serializers with extensive metaclass boilerplate | Gives FastAPI-style ergonomics, Pydantic v2 performance, and auto-generated Swagger on top of Django's battle-tested ORM. |
| **Polyglot persistence (NoSQL, MongoDB, external APIs)** | **FastAPI** | Forcing Django without its relational ORM | FastAPI imposes zero database assumptions; easily integrates Motor, Tortoise, or raw async clients. |
| **Complex transactional domain model (PostgreSQL)** | **Django** (`@transaction.atomic`) or **FastAPI** + SQLAlchemy 2.0 | Raw SQL queries scattered across route handlers | Both provide mature transaction boundary management and relationship eager loading. |

---

## Over-Engineering Self-Check (Anti-Bloat Guardrail)

Before generating API code, audit your architecture against these anti-bloat heuristics:

1. **Avoid Over-Abstracted Repository Layers**: Do not create generic `IRepository<T>` abstractions over the Django ORM or SQLAlchemy 2.0. Both ORMs are already sophisticated Unit of Work / Repository implementations.
2. **No 1:1 Interface-Class Duplication**: Python relies on duck typing and `typing.Protocol`. Never create artificial `UserServiceInterface` + `UserServiceImpl` pairs.
3. **Keep Route Handlers Lean**: A route handler should only validate input, call the service layer, and return a response DTO. Avoid inlining 50 lines of database queries and business calculations into the endpoint.
4. **No Premature Micro-Packages**: For small-to-medium APIs, a simple feature-sliced layout (`modules/orders/`) beats splitting the project into 8 independent packages.
5. **Direct Tool Audit**: For substantial modules, use [`detect-overengineering`](file:///.github/skills/detect-overengineering/SKILL.md) to inspect pass-through ratios and layer bloat.

---

## Knowledge Modules

Load only the modules relevant to the task.

- [FastAPI vs. Django: Architectural Trade-Offs](framework-comparison/fastapi-vs-django.md)
- [FastAPI: Architecture, Lifespan & Best Practices](fastapi/architecture-and-best-practices.md)
- [Django & Django Ninja: Architecture & Service Layer](django/architecture-and-best-practices.md)
- [Async & Concurrency: Event Loop Hygiene](async-and-concurrency/event-loop-hygiene.md)
- [Persistence: ORMs, Migrations & Connection Pooling](persistence/orms-and-migrations.md)
- [API Security, Authentication (JWT/Session) & Rate Limiting](security-and-auth/api-security.md)
- [Automated API Testing Patterns (FastAPI & Django)](testing/api-testing-patterns.md)
