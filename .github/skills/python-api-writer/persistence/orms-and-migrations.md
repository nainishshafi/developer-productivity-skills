# Persistence: ORMs, Migrations & Connection Pooling

Modern Python APIs use either **SQLAlchemy 2.0** (standard for FastAPI and async services) or **Django ORM** (standard for Django applications). Both require careful connection pool configuration and eager loading to prevent $N+1$ query cascades.

---

## 1. ORM Comparison: SQLAlchemy 2.0 vs. Django ORM

| Feature | SQLAlchemy 2.0 (Async) | Django ORM |
|---|---|---|
| **Programming Model** | Data Mapper pattern (explicit session unit-of-work) | Active Record pattern (model instances save themselves) |
| **Async Support** | Native `AsyncSession` via `asyncpg` / `asyncmy` | Hybrid (sync by default, async via `aget`, `afirst`) |
| **Migration Tool** | **Alembic** (`alembic upgrade head`) | **Built-in** (`makemigrations`, `migrate`) |
| **Relationship Eager Loading** | `joinedload()` (SQL JOIN) & `selectinload()` (IN clause) | `select_related()` (SQL JOIN) & `prefetch_related()` (IN clause) |
| **Inspection & Flexibility** | High; allows arbitrary SQL, CTEs, window functions | High for standard relational; requires `.raw()` for complex CTEs |

---

## 2. SQLAlchemy 2.0 Async Best Practices

### Modern 2.0 Syntax (Declarative Mapped & Select)
In SQLAlchemy 2.0, the legacy 1.x `session.query(Model)` syntax is deprecated in favor of explicit `select()` statements:

```python
from sqlalchemy import select, String, ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, selectinload, joinedload
from sqlalchemy.ext.asyncio import AsyncSession

class Base(DeclarativeBase):
    pass

class Customer(Base):
    __tablename__ = "customers"
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    orders: Mapped[list["Order"]] = relationship(back_populates="customer")

class Order(Base):
    __tablename__ = "orders"
    id: Mapped[int] = mapped_column(primary_key=True)
    total: Mapped[float]
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"))
    customer: Mapped["Customer"] = relationship(back_populates="orders")
```

### Eager Loading Strategies (Preventing Async N+1 Exceptions)
In async SQLAlchemy, lazy-loading an un-fetched relationship raises `MissingGreenlet: greenlet_spawn has not been called`. Always specify eager loading:

- **`joinedload()`**: Generates an SQL `LEFT OUTER JOIN`. Ideal for one-to-one and many-to-one relationships.
- **`selectinload()`**: Issues a second `SELECT ... WHERE id IN (...)` query. **Mandatory** for one-to-many and many-to-many collections.

```python
# Query order with customer joined (1 SQL query) and all order items loaded via SELECT IN (1 SQL query)
stmt = (
    select(Order)
    .where(Order.id == order_id)
    .options(
        joinedload(Order.customer),      # Single parent: joinedload
        selectinload(Order.items)        # Multi-child: selectinload
    )
)
result = await session.execute(stmt)
order = result.scalar_one_or_none()
```

---

## 3. Production Connection Pool Sizing

An incorrectly sized connection pool either exhausts database server connections or starves API worker threads.

```python
from sqlalchemy.ext.asyncio import create_async_engine

engine = create_async_engine(
    "postgresql+asyncpg://app_user:secret@db.internal:5432/production_db",
    pool_size=20,           # Steady-state open connections per worker process
    max_overflow=10,        # Burst connections allowed during spikes
    pool_timeout=30,        # Seconds to wait before raising TimeoutError
    pool_recycle=1800,      # Recycle connections every 30 minutes to drop dead TCP links
    pool_pre_ping=True      # Tests connection liveness with SELECT 1 before checkout
)
```

> [!IMPORTANT]
> **Total Database Connections Formula**:
> $$\text{Max DB Connections} = \text{Gunicorn Workers} \times (\text{pool\_size} + \text{max\_overflow}) \times \text{Container Instances}$$
> Ensure this total is strictly below the database server's `max_connections` (e.g., PostgreSQL default 100). Use **PgBouncer** when scaling beyond 4 API instances.

