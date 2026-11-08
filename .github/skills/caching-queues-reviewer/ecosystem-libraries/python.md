# Python: Caching & Queue Ecosystem

Comprehensive architectural guidance for Python (3.10–3.13) when designing and reviewing caching architectures, Redis integrations, asynchronous worker queues, and Apache Kafka consumers.

---

## 1. Library Selection Matrix

| Category | Recommended Library | Alternative | When to Choose What |
|---|---|---|---|
| **In-Memory Cache (L1)** | **`cachetools`** (`TTLCache`, `LRUCache`) | `functools.lru_cache` | Use `cachetools.TTLCache` for time-expiring bounded caches. Only use standard `@lru_cache(maxsize=1024)` for pure functions with immutable arguments. **Never** use `@lru_cache(maxsize=None)` in production. |
| **Redis Client** | **`redis`** (`redis-py` 5.0+) | `aioredis` (merged into `redis.asyncio`) | Official client supporting both synchronous (`redis.Redis`) and asynchronous (`redis.asyncio.Redis`) drivers, connection pooling, Cluster, Sentinel, and automatic `EVALSHA` Lua scripting. |
| **Distributed Task Queue** | **`Celery`** (Heavy/Multi-broker) or **`Arq`** (Asyncio/Redis) | `RQ` (Redis Queue) | Use `Arq` for modern `asyncio`/FastAPI microservices. Use `Celery` for complex multi-step workflows, canvas chords/chains, and RabbitMQ backends. Use `RQ` for lightweight synchronous worker pools. |
| **Apache Kafka Client** | **`confluent-kafka`** (librdkafka C bindings) | `aiokafka` | `confluent-kafka` provides $10\text{--}50\times$ the throughput of pure-Python alternatives and is the enterprise standard. Use `aiokafka` when strict integration with an `asyncio` event loop is mandated. |

---

## 2. In-Memory Caching with `cachetools`

```python
from cachetools import TTLCache, cached
import threading

# Thread-safe TTL cache: max 5,000 items, expires in 10 minutes
cache_lock = threading.RLock()
api_cache = TTLCache(maxsize=5000, ttl=600)

@cached(cache=api_cache, lock=cache_lock)
def get_user_permissions(user_id: str) -> frozenset[str]:
    # Expensive database lookup
    return query_database_permissions(user_id)
```

---

## 3. High-Throughput Async Redis & Lua Execution with `redis.asyncio`

```python
import redis.asyncio as aioredis

# Always share a single ConnectionPool across the application lifecycle
pool = aioredis.ConnectionPool(
    host="localhost",
    port=6379,
    db=0,
    max_connections=50,
    decode_responses=True,
)
redis_client = aioredis.Redis(connection_pool=pool)

# Atomic Distributed Lock Release Script
LUA_RELEASE_LOCK = """
if redis.call("GET", KEYS[1]) == ARGV[1] then
    return redis.call("DEL", KEYS[1])
else
    return 0
end
"""
release_lock_script = redis_client.register_script(LUA_RELEASE_LOCK)

async def release_distributed_lock(lock_key: str, owner_token: str) -> bool:
    # Executes via EVALSHA automatically
    result = await release_lock_script(keys=[lock_key], args=[owner_token])
    return bool(result)

async def batch_cache_aside(keys: list[str]) -> dict[str, str]:
    """Demonstrates pipelined reads with zero per-key roundtrip latency."""
    async with redis_client.pipeline(transaction=False) as pipe:
        for key in keys:
            pipe.get(key)
        values = await pipe.execute()
    return dict(zip(keys, values))
```

---

## 4. Modern Asyncio Worker Queue with `Arq`

For FastAPI and asyncio applications, `Arq` avoids the heavy thread/process overhead of Celery by executing jobs as coroutines over Redis.

```python
# worker.py
from arq import create_pool
from arq.connections import RedisSettings

async def send_welcome_email(ctx, user_id: str, email: str) -> None:
    # Asynchronous task logic
    await mailer_client.send(to=email, template="welcome")

class WorkerSettings:
    functions = [send_welcome_email]
    redis_settings = RedisSettings(host="127.0.0.1", port=6379)
    max_jobs = 20  # Bounded worker concurrency
    job_timeout = 60  # Prevent zombie tasks

# Enqueueing from FastAPI endpoint:
# redis = await create_pool(RedisSettings())
# await redis.enqueue_job("send_welcome_email", user_id="123", email="user@domain.com")
```

---

## 5. Kafka High-Throughput Consumer with `confluent-kafka`

```python
from confluent_kafka import Consumer, KafkaError, KafkaException
import json
import logging

logger = logging.getLogger(__name__)

conf = {
    "bootstrap.servers": "localhost:9092",
    "group.id": "order-analytics-group",
    "auto.offset.reset": "earliest",
    "enable.auto.commit": False,  # Manual commit control
    "max.poll.interval.ms": 300000,
}

consumer = Consumer(conf)
consumer.subscribe(["orders.v1"])

def run_consumer_loop():
    try:
        while True:
            # Poll with timeout in milliseconds
            msg = consumer.poll(timeout=1.0)
            if msg is None:
                continue
            if msg.error():
                if msg.error().code() == KafkaError._PARTITION_EOF:
                    continue
                else:
                    raise KafkaException(msg.error())

            try:
                order_event = json.loads(msg.value().decode("utf-8"))
                process_order_event(order_event)

                # Commit strictly after successful processing
                consumer.commit(message=msg, asynchronous=True)
            except json.JSONDecodeError as err:
                logger.error(f"Poison pill detected at offset {msg.offset()}: {err}")
                route_to_dlq(msg)
                consumer.commit(message=msg, asynchronous=False)
    finally:
        consumer.close()
```

