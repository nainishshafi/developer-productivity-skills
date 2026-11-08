# FastAPI: Architecture & Best Practices

FastAPI is an asynchronous, high-performance web framework based on Starlette and Pydantic. Writing production-grade FastAPI services requires clean modular routing, strict dependency injection lifecycles, and event loop discipline.

---

## 1. Modern Lifespan Protocol (Application Startup & Teardown)

FastAPI deprecated `@app.on_event("startup")` and `@app.on_event("shutdown")`. Always use the **Lifespan Context Manager** pattern with `contextlib.asynccontextmanager`:

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
import logging

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- Startup ---
    logger.info("Initializing connection pools and warm-up caches...")
    await database.connect()
    redis_client = await init_redis_pool()
    app.state.redis = redis_client
    
    yield  # Application serves requests here
    
    # --- Teardown ---
    logger.info("Draining connections and shutting down...")
    await app.state.redis.close()
    await database.disconnect()

app = FastAPI(
    title="Order Fulfillment Service",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url=None
)
```

---

## 2. Recommended Directory Architecture (Feature-Slice Layout)

For scalable services, organize by **domain feature** rather than technical layer:

```
src/
├── main.py                  # FastAPI app factory, middleware, lifespan
├── core/
│   ├── config.py            # pydantic-settings BaseSettings
│   ├── database.py          # async_sessionmaker & engine
│   └── security.py          # Password hashing, JWT creation
├── common/
│   ├── exceptions.py        # Custom domain exceptions
│   └── pagination.py        # Generic Page[T] DTO
└── modules/
    ├── users/
    │   ├── router.py        # APIRouter with endpoints
    │   ├── schemas.py       # Pydantic request/response models
    │   ├── models.py        # SQLAlchemy / Tortoise ORM models
    │   ├── service.py       # Business logic operations
    │   └── dependencies.py  # get_current_user Depends()
    └── orders/
        ├── router.py
        ├── schemas.py
        ├── models.py
        └── service.py
```

---

## 3. Modular APIRouter Composition

```python
# src/modules/orders/router.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from src.core.database import get_db_session
from src.modules.orders.schemas import OrderCreate, OrderResponse
from src.modules.orders import service

router = APIRouter(prefix="/orders", tags=["Orders"])

@router.post(
    "",
    response_model=OrderResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new customer order"
)
async def create_order(
    payload: OrderCreate,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_active_user)
) -> OrderResponse:
    return await service.create_order(session, payload, current_user.id)
```

---

## 4. Robust Dependency Injection (`Depends`)

Dependency Injection in FastAPI ensures database connections are automatically opened, injected, committed, or rolled back, and cleanly closed per request.

```python
# src/core/database.py
from collections.abc import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

engine = create_async_engine(
    "postgresql+asyncpg://user:pass@localhost:5432/orders_db",
    pool_size=20,
    max_overflow=10,
    pool_pre_ping=True
)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)

async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Yields a database session scoped strictly to a single request lifecycle."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
```

---

## 5. BackgroundTasks vs. Distributed Queues

FastAPI includes a built-in `BackgroundTasks` parameter, but its scope is often misunderstood:

```python
from fastapi import BackgroundTasks

@router.post("/send-receipt")
async def send_receipt(order_id: str, bg_tasks: BackgroundTasks):
    # OK for: Lightweight, non-critical in-process tasks (e.g. logging metrics, fire-and-forget emails)
    bg_tasks.add_task(log_audit_event, order_id)
    return {"status": "enqueued"}
```

- **When `BackgroundTasks` is appropriate**: Micro-tasks completing in < 1 second within the same process where losing the task during server restart is acceptable.
- **When NOT to use `BackgroundTasks`**: Heavy data processing, payment capture, video transcode, or critical webhooks. Use an external broker queue (**Arq**, **Celery**, **RabbitMQ**, or **Kafka**) so tasks survive server crashes and support retries.

---

## 6. Real-Time Streaming Responses (SSE / LLM Tokens)

FastAPI makes streaming token-by-token output straightforward:

```python
from fastapi.responses import StreamingResponse
from collections.abc import AsyncGenerator

async def token_generator(prompt: str) -> AsyncGenerator[str, None]:
    async for chunk in llm_client.stream(prompt):
        yield f"data: {chunk.content}\n\n"

@router.get("/stream-completion")
async def stream_completion(prompt: str):
    return StreamingResponse(
        token_generator(prompt),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
    )
```

