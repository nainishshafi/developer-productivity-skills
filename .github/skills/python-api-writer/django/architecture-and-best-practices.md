# Django & Django Ninja: Architecture & Best Practices

Django provides an enterprise-ready foundation with a mature ORM, built-in security, and automated admin dashboards. Whether using **Django REST Framework (DRF)** or modern **Django Ninja**, high-scale architectures require disciplined QuerySet optimization, explicit transaction boundaries, and a clean service layer.

---

## Architectural Pattern: Django MVT + Service Layer (vs. MVVM)

Django follows **MVT (Model–View–Template)** rather than frontend **MVVM (Model–View–ViewModel)**. For API backends (DRF / Django Ninja), **follow this consistent layered pattern across every Django app** (`apps/<domain>/`):

| Layer | File | Responsibility (What Goes Here) | Anti-Pattern to Avoid |
|---|---|---|---|
| **Model** | `models.py` | DB schema, relationships, custom `QuerySet`/`Manager` | Putting multi-model workflows or HTTP logic in `Model.save()` |
| **Schema / Serializer** | `schemas.py` / `serializers.py` | Input validation & output shaping (acts as the API **DTO / ViewModel** boundary) | Performing DB writes or business rules inside `Serializer.create()` |
| **Service** | `services.py` | Business logic, `@transaction.atomic` write boundaries, `transaction.on_commit` | Returning `HttpResponse` or touching `request` objects |
| **View / Endpoint** | `api.py` / `views.py` | Thin HTTP adapter: parse input schema, call service, return response DTO | Inlining ORM queries or business calculations in views/ViewSets |
| **Template** *(HTML only)* | `templates/` | Server-rendered HTML (omitted in pure JSON APIs) | Embedding business logic in template tags |

**Agent Rule**: Apply this exact `models.py` → `schemas.py` / `serializers.py` → `services.py` → `api.py` / `views.py` separation uniformly across every app in the Django project.

---

## 1. Django REST Framework (DRF) vs. Django Ninja

| Architectural Dimension | Django REST Framework (DRF) | Django Ninja |
|---|---|---|
| **Validation Engine** | Custom DRF Serializers | **Pydantic v2** |
| **Type Hint Integration** | Partial; largely class/attribute-based | Full Python 3.10+ type annotations |
| **API Documentation** | Requires `drf-spectacular` plugin | Native **OpenAPI 3.1 & Swagger** out of the box |
| **Performance** | Higher serializer overhead | $2\text{--}4\times$ faster serialization via Pydantic v2 |
| **Async Support** | Limited / experimental | Native `async def` route handlers |
| **Ecosystem Maturity** | Decades of battle-tested third-party apps | Modern, rapidly growing, FastAPI-like ergonomics |

### Django Ninja Example (Modern Idiom)
```python
# api.py
from ninja import NinjaAPI, Schema
from django.shortcuts import get_object_or_404
from .models import Order

api = NinjaAPI(title="E-Commerce API", version="1.0.0")

class OrderIn(Schema):
    item_ids: list[int]
    coupon_code: str | None = None

class OrderOut(Schema):
    id: int
    total_amount: float
    status: str

@api.post("/orders", response={201: OrderOut})
def create_order(request, payload: OrderIn):
    order = order_service.place_order(user=request.user, payload=payload)
    return 201, order
```

---

## 2. The Service Layer Pattern (Skinny Views, Clean Domain)

Avoid the legacy Django anti-pattern of putting all business logic into "Fat Models" or bloated ViewSets. Decouple domain workflows into pure service functions:

```python
# services/order_service.py
from django.db import transaction
from django.core.exceptions import ValidationError
from ..models import Order, OrderItem, Product

@transaction.atomic
def place_order(*, user, item_ids: list[int], coupon_code: str | None = None) -> Order:
    """Encapsulates the complete business transaction with atomic rollback."""
    # 1. Fetch & lock product rows to prevent inventory overselling
    products = Product.objects.select_for_update().filter(id__in=item_ids)
    if len(products) != len(item_ids):
        raise ValidationError("One or more selected products do not exist")

    # 2. Validate stock invariants
    for p in products:
        if p.stock < 1:
            raise ValidationError(f"Product {p.title} is out of stock")
        p.stock -= 1
        p.save(update_fields=["stock"])

    # 3. Create domain records
    total = sum(p.price for p in products)
    order = Order.objects.create(user=user, total_amount=total, status="pending")

    # 4. Schedule side effects strictly ON COMMIT (never inside the uncommitted transaction)
    transaction.on_commit(lambda: send_order_confirmation_email.delay(order.id))

    return order
```

---

## 3. QuerySet Optimization & N+1 Prevention

Django's ORM is lazy; without explicit join instructions, accessing related models in loops generates hundreds of individual SQL queries ($N+1$ problem).

### The Selection Rule:
- **`select_related`**: Uses SQL `INNER JOIN` or `LEFT OUTER JOIN`. Use for **single-valued relationships** (`ForeignKey`, `OneToOneField`).
- **`prefetch_related`**: Performs a separate `WHERE IN (...)` query and joins in Python memory. Use for **multi-valued relationships** (`ManyToManyField`, reverse `ForeignKey` / related sets).

```python
# ❌ BAD: Generates 101 database queries for 100 orders
orders = Order.objects.all()
for order in orders:
    print(order.customer.email)  # Query per customer!
    for item in order.items.all():  # Query per order items!
        print(item.product.name)

# ✅ GOOD: Exactly 3 SQL queries total regardless of order volume
orders = (
    Order.objects
    .select_related("customer")  # SQL JOIN for single FK
    .prefetch_related("items__product")  # Prefetch items and products
    .only("id", "total_amount", "customer__email")  # Restrict columns
)
```

---

## 4. Custom Managers & QuerySets

Encapsulate reusable query filters in custom `models.QuerySet` classes instead of scattering `.filter(status="active", is_deleted=False)` across multiple views:

```python
# models.py
from django.db import models

class OrderQuerySet(models.QuerySet):
    def active(self):
        return self.filter(status__in=["pending", "processing", "shipped"])

    def for_customer(self, customer_id: int):
        return self.filter(customer_id=customer_id)

    def with_items_count(self):
        return self.annotate(total_items=models.Count("items"))

class Order(models.Model):
    customer = models.ForeignKey("Customer", on_delete=models.CASCADE)
    status = models.CharField(max_length=20)
    
    # Expose custom queries cleanly
    objects = OrderQuerySet.as_manager()

# Usage in views/services:
active_orders = Order.objects.active().for_customer(user.id).with_items_count()
```

---

## 5. Related Django & Common Reference Docs

- **Django Middleware, Exception Handlers, Auth & Split Settings**: [middleware-and-app-wiring.md](middleware-and-app-wiring.md)
- **AOP, Decorators & `@method_decorator` for CBVs**: [aop-and-decorators.md](../aspect-oriented-programming/aop-and-decorators.md)
- **API Security, JWT vs. Sessions, CORS & Rate Limiting**: [api-security.md](../security-and-auth/api-security.md)
- **Validation & Schemas (Pydantic v2 / Django Ninja & DRF Serializers)**: [data-validation-and-schemas.md](../validation-and-data/data-validation-and-schemas.md)
- **Async Views & Django Async ORM (`a-` methods)**: [event-loop-hygiene.md](../async-and-concurrency/event-loop-hygiene.md)
- **ORMs & Connection Pooling**: [orms-and-migrations.md](../persistence/orms-and-migrations.md)
- **Automated API Testing (`pytest-django`)**: [api-testing-patterns.md](../testing/api-testing-patterns.md)

