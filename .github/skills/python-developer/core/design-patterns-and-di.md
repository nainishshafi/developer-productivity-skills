# Python Design Patterns & Dependency Injection Architecture

Comprehensive architectural guide to Dependency Injection (DI) and Modern Design Patterns in Python (Python 3.10–3.13, FastAPI, Protocols, and `dependency-injector`).

---

## 1. Dependency Injection Patterns in Python

In Python, Dependency Injection is implemented through structural subtyping (`typing.Protocol`), modern web framework DI (FastAPI `Depends`), or enterprise IoC containers (`dependency-injector`).

### 1.1 Structural Subtyping DI with `typing.Protocol` (The Python Gold Standard)
Unlike Java or C#, Python's static type system supports **structural subtyping** (static duck typing). Clients define the dependency interface without the implementation needing to inherit from it.

```python
from typing import Protocol, runtime_checkable

# 1. Consumer defines the exact interface contract it requires
@runtime_checkable
class NotificationService(Protocol):
    async def send_alert(self, user_id: str, message: str) -> bool:
        ...

# 2. Domain Service accepts the protocol via Constructor Injection
class OrderProcessor:
    def __init__(self, notifier: NotificationService) -> None:
        self._notifier = notifier

    async def complete_order(self, order_id: str, user_id: str) -> None:
        # Processing logic...
        await self._notifier.send_alert(user_id, f"Order {order_id} confirmed")

# 3. Implementation does NOT need to import or inherit from NotificationService!
class SlackNotifier:
    def __init__(self, webhook_url: str) -> None:
        self._webhook = webhook_url

    async def send_alert(self, user_id: str, message: str) -> bool:
        # Matches the protocol signature structurally
        print(f"Sending Slack message to {user_id}: {message}")
        return True
```

---

### 1.2 FastAPI Dependency Injection (`Depends`)

FastAPI features a built-in, hierarchical dependency injection engine supporting caching, sub-dependencies, and automatic teardown.

#### A. Basic Injection with `Depends`
```python
from fastapi import Depends, FastAPI
from sqlalchemy.ext.asyncio import AsyncSession

# Database Session Dependency with automatic context manager teardown
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise

# Service Factory Dependency resolving other dependencies
async def get_order_service(db: AsyncSession = Depends(get_db_session)) -> OrderService:
    return OrderService(repository=SqlOrderRepository(db))

# Route Handler with Injected Service
@app.post("/orders")
async def create_order(
    payload: OrderCreateDto,
    order_service: OrderService = Depends(get_order_service),
) -> OrderResponseDto:
    return await order_service.create(payload)
```

#### B. Overriding Dependencies in Tests (Zero-Friction Mocking)
FastAPI allows replacing any dependency node without touching source code:
```python
def test_create_order(client: TestClient):
    mock_service = Mock(spec=OrderService)
    mock_service.create.return_value = OrderResponseDto(id="123", status="PAID")

    # Override the dependency globally for the test suite
    app.dependency_overrides[get_order_service] = lambda: mock_service

    response = client.post("/orders", json={"amount": 100})
    assert response.status_code == 200
    assert response.json()["id"] == "123"

    # Cleanup override
    app.dependency_overrides.clear()
```

---

### 1.3 Container DI with `dependency-injector`

For non-FastAPI applications (Celery workers, CLI tools, event consumers), `dependency-injector` provides an enterprise IoC container:

```python
from dependency_injector import containers, providers
from dependency_injector.wiring import Provide, inject

class Container(containers.DeclarativeContainer):
    config = providers.Configuration()

    # Singleton Database Client
    db_pool = providers.Singleton(DatabasePool, url=config.db.url)

    # Factory (Transient) Service: created on each injection
    user_repository = providers.Factory(SqlUserRepository, db=db_pool)
    user_service = providers.Factory(UserService, repo=user_repository)

# Declarative injection into functions:
@inject
def handle_user_signup(
    email: str,
    service: UserService = Provide[Container.user_service],
):
    service.register(email)
```

---

## 2. Pythonic Design Patterns

### 2.1 Strategy Pattern (First-Class Functions & Callables)
**Intent**: Define interchangeable algorithms without creating class hierarchies.

- In Python, functions are first-class objects. Use `Callable[[Input], Output]` instead of abstract strategy classes:

```python
from typing import Callable

DiscountStrategy = Callable[[float], float]

def regular_discount(price: float) -> float:
    return price * 0.95

def vip_discount(price: float) -> float:
    return price * 0.80

def compute_total(subtotal: float, strategy: DiscountStrategy = regular_discount) -> float:
    return strategy(subtotal)
```

---

### 2.2 Factory Pattern (Classmethods & Registries)
**Intent**: Provide expressive constructor alternatives and dynamic subclass instantiation.

```python
class MessageEvent:
    def __init__(self, topic: str, payload: dict, timestamp: float) -> None:
        self.topic = topic
        self.payload = payload
        self.timestamp = timestamp

    # Static Factory Classmethods:
    @classmethod
    def from_kafka(cls, kafka_record: dict) -> "MessageEvent":
        return cls(
            topic=kafka_record["topic"],
            payload=kafka_record["value"],
            timestamp=kafka_record["timestamp"],
        )

    @classmethod
    def from_sqs(cls, sqs_message: dict) -> "MessageEvent":
        return cls(
            topic=sqs_message["MessageAttributes"]["Topic"]["StringValue"],
            payload=json.loads(sqs_message["Body"]),
            timestamp=float(sqs_message["Attributes"]["SentTimestamp"]) / 1000.0,
        )
```

---

### 2.3 Decorator Pattern (Function Wrappers with `functools.wraps`)
**Intent**: Attach cross-cutting concerns (caching, metrics, retry, authentication) cleanly.

```python
import functools
import time
from typing import Any, Callable

def retry(max_attempts: int = 3, delay: float = 1.0):
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            last_err = None
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_err = e
                    if attempt == max_attempts:
                        raise
                    time.sleep(delay * attempt)
            raise last_err
        return wrapper
    return decorator
```

---

### 2.4 Adapter Pattern
**Intent**: Decouple domain logic from external cloud SDKs or proprietary APIs.

```python
class ObjectStoragePort(Protocol):
    async def upload(self, key: str, data: bytes) -> str:
        ...

class S3StorageAdapter:
    def __init__(self, s3_client: Any, bucket_name: str) -> None:
        self._s3 = s3_client
        self._bucket = bucket_name

    async def upload(self, key: str, data: bytes) -> str:
        await self._s3.put_object(Bucket=self._bucket, Key=key, Body=data)
        return f"s3://{self._bucket}/{key}"
```

---

### 2.5 Repository & Unit of Work Pattern (Async SQLAlchemy)
**Intent**: Manage transactional integrity and encapsulate queries cleanly.

```python
from contextlib import asynccontextmanager

class UnitOfWork:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory
        self.session: AsyncSession | None = None

    @asynccontextmanager
    async def __call__(self) -> AsyncGenerator["UnitOfWork", None]:
        async with self._session_factory() as session:
            self.session = session
            try:
                yield self
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                self.session = None

    @property
    def orders(self) -> SqlOrderRepository:
        if not self.session:
            raise RuntimeError("UnitOfWork accessed outside context")
        return SqlOrderRepository(self.session)
```
