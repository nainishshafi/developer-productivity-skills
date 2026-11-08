# API Testing Patterns: FastAPI & Django

Reliable, fast automated testing for Python APIs requires isolated database fixtures, zero network pollution, and dependency mocking.

---

## 1. FastAPI Testing with `httpx.AsyncClient` & `pytest-asyncio`

Use `httpx.AsyncClient` using an ASGI transport to test the application in-memory with sub-second feedback without binding to an actual network port:

```python
# tests/conftest.py
import pytest
from collections.abc import AsyncGenerator
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from src.main import app
from src.core.database import get_db_session, Base

# Use in-memory SQLite or isolated test database
TEST_DB_URL = "sqlite+aiosqlite:///:memory:"
test_engine = create_async_engine(TEST_DB_URL)
TestSessionLocal = async_sessionmaker(test_engine, expire_on_commit=False)

@pytest.fixture(autouse=True)
async def setup_test_database():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    async with TestSessionLocal() as session:
        yield session

@pytest.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    # Override production database dependency with test session
    app.dependency_overrides[get_db_session] = lambda: db_session
    
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
        
    app.dependency_overrides.clear()
```

### Writing the Test
```python
# tests/test_orders.py
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_create_order_success(client: AsyncClient):
    payload = {"item_ids": [1, 2], "coupon_code": "SUMMER10"}
    response = await client.post("/orders", json=payload)
    
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["status"] == "pending"

@pytest.mark.asyncio
async def test_create_order_validation_failure(client: AsyncClient):
    # Missing required field
    response = await client.post("/orders", json={})
    assert response.status_code == 422
```

---

## 2. Django Testing with `pytest-django`

In Django, `pytest-django` provides transactional test database fixtures with automatic rollback after every test case:

```python
# tests/test_django_orders.py
import pytest
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model
from orders.models import Product

User = get_user_model()

@pytest.fixture
def auth_client(db):
    user = User.objects.create_user(username="tester", email="test@example.com")
    client = APIClient()
    client.force_authenticate(user=user)
    return client

@pytest.mark.django_db
def test_place_order_service(auth_client):
    product = Product.objects.create(title="Laptop", price=1200.0, stock=5)
    
    response = auth_client.post("/api/orders", {"item_ids": [product.id]}, format="json")
    
    assert response.status_code == 201
    assert response.data["total_amount"] == 1200.0
    
    # Verify database state was updated
    product.refresh_from_db()
    assert product.stock == 4
```

