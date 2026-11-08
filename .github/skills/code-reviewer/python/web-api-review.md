# Python Web & API Review Guide

Audit guide for Python web APIs (FastAPI, Django, Django Ninja) cross-referencing [`python-api-writer`](file:///.github/skills/python-api-writer/SKILL.md).

---

## 1. 4-Tier Architectural Boundaries

Verify strict separation of concerns across layers:
1. **Presentation / Route Layer (`routers/` or `views/`)**: Accepts HTTP requests, parses schemas, validates inputs, and returns HTTP responses. Must contain **zero business logic** or direct database queries.
2. **Service / Domain Layer (`services/`)**: Implements core business logic, validation rules, and workflow orchestration. Independent of HTTP constructs (`Request`, `Response`, status codes).
3. **Repository / Data Access Layer (`repositories/`)**: Encapsulates ORM calls, SQL execution, and persistence queries.
4. **Data Modeling & Schemas (`schemas/` or `models/`)**: Pydantic models for contract definitions and SQLAlchemy / Django ORM models for database mapping.

Flag routes that execute direct database queries or instantiate ORM models without a service layer as `[P1 - Major]`.

---

## 2. Pydantic v2 & Input Validation

- [ ] **Field Constraints**: Are fields constrained with explicit bounds (`Field(min_length=1, max_length=100)`, `ge=0`, `le=1000`)?
- [ ] **Email & URL Types**: Are structured types (`EmailStr`, `HttpUrl`) used rather than loose `str`?
- [ ] **Sensitive Data Scrubbing**: Are passwords, tokens, and secrets annotated with `SecretStr` to prevent leakages in `repr()`, logs, or error responses?
- [ ] **Model Configuration**: Is `extra="forbid"` configured on request models to prevent mass-assignment attacks?
- [ ] **Model Validators**: Are custom validators using `@field_validator` or `@model_validator(mode="after")` properly returning the value or instance?

---

## 3. Framework-Specific Reviews

### FastAPI
- [ ] **Async vs. Sync Route Handlers**:
  - `async def` endpoints: Must **never** execute blocking synchronous I/O (e.g. `requests.get()`, `time.sleep()`, synchronous database drivers).
  - Sync `def` endpoints: FastAPI automatically runs standard `def` routes in a thread pool (`asyncio.to_thread`). Use `def` if using synchronous DB drivers.
- [ ] **Dependency Injection**: Are DB sessions and auth tokens provided via `Depends(get_db)` and `Depends(get_current_user)`?
- [ ] **Status Codes & Response Models**: Are endpoints explicitly specifying `status_code=status.HTTP_201_CREATED` and `response_model=ItemResponse`?

### Django & Django Ninja
- [ ] **Queryset Optimization**: Are queries using `select_related()` (for ForeignKey / OneToOne) and `prefetch_related()` (for ManyToMany / reverse FK) to prevent N+1 query cascades?
- [ ] **Atomic Transactions**: Are multi-step mutations wrapped in `transaction.atomic()`?
- [ ] **CSRF & Middleware**: Is CSRF middleware enabled for cookie-authenticated sessions?
- [ ] **Django Ninja Schema Isolation**: Are Ninja `Schema` objects strictly separated from Django ORM models?

---

## 4. Aspect-Oriented Programming (AOP) & Decorators

- [ ] **`@functools.wraps`**: Do all custom decorators use `@wraps(func)` to preserve function name, docstrings, and signature metadata?
- [ ] **Async Decorator Compatibility**: Does the decorator handle both sync and async functions correctly (inspecting `inspect.iscoroutinefunction(func)`)?
- [ ] **Exception Preservation**: Do interceptors avoid swallowing exceptions raised inside the wrapped target?

---

## 5. API Security & Authentication Auditing

- [ ] **Token Verification**: Are JWTs verified using asymmetric keys (RS256/ES256)? Is algorithm `none` rejected?
- [ ] **Password Hashing**: Are passwords hashed using Argon2id or bcrypt with appropriate work factors?
- [ ] **CORS Configuration**: Is `allow_origins=["*"]` forbidden in production with credentials enabled? Flag wildcard CORS with credentials as `[P0 - Blocker]`.

