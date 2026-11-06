# Python Asyncio, Event Loop Hygiene & Concurrency

Prevent event loop blocking, manage concurrent tasks with structured concurrency, and select the right concurrency model (threads vs processes vs async).

---

## 1. Event Loop Starvation: Never Block the Main Async Loop

The `asyncio` event loop runs on a single thread. Executing synchronous I/O or CPU-heavy work inside an `async def` function halts all concurrent request processing for all users.

### The Traps
- `time.sleep()` inside `async def` (use `await asyncio.sleep()`).
- Synchronous HTTP clients (`requests.get`, `urllib.request`) in async routes (use `httpx.AsyncClient` or `aiohttp`).
- Synchronous database drivers (use async drivers like `asyncpg`, `aiosqlite`, or SQLAlchemy async).

```python
# ❌ ANTI-PATTERN: Blocking file I/O or sync crypto inside async endpoint freezes the server
@app.get("/export")
async def export_data():
    time.sleep(2)  # Blocks all concurrent users for 2 seconds!
    return {"status": "done"}

# ✅ BEST PRACTICE: Offload sync blocking code to thread pool
import asyncio

@app.get("/export")
async def export_data():
    result = await asyncio.to_thread(heavy_synchronous_computation)
    return {"status": "done", "result": result}
```

---

## 2. Structured Concurrency with `asyncio.TaskGroup` (Python 3.11+)

Avoid fire-and-forget `asyncio.create_task()` or unbounded `asyncio.gather()`. Use `asyncio.TaskGroup`, which guarantees that if one task fails, all sibling tasks are cancelled and cleaned up immediately:

```python
import asyncio

async def fetch_customer_dashboard(customer_id: str):
    async with asyncio.TaskGroup() as tg:
        orders_task = tg.create_task(fetch_orders(customer_id))
        invoices_task = tg.create_task(fetch_invoices(customer_id))
        profile_task = tg.create_task(fetch_profile(customer_id))

    # All three succeeded if execution reaches here
    return {
        "orders": orders_task.result(),
        "invoices": invoices_task.result(),
        "profile": profile_task.result(),
    }
```

---

## 3. Concurrency Model Decision Matrix

| Task Type | Bottleneck | Recommended Model | Implementation Tool |
|---|---|---|---|
| **High I/O Web Service** | Network / DB latency | `asyncio` (single thread event loop) | FastAPI, Litestar, `httpx.AsyncClient` |
| **Legacy Blocking I/O** | Third-party sync SDKs | Thread pool | `asyncio.to_thread()` / `ThreadPoolExecutor` |
| **Heavy CPU Computation** | Math, hashing, image encoding | Multi-process (bypasses GIL) | `concurrent.futures.ProcessPoolExecutor` |

