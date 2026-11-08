# Caching & Queue Senior Code Review Checklist

This checklist provides a structured audit rubric for senior engineers and automated reviewer agents evaluating caching, Redis, message broker, and Kafka implementations across codebases.

---

## 1. The 7-Dimension Audit Matrix

### Dimension 1: Eviction, Expiration & Memory Safety
- [ ] **Mandatory TTL**: Does every volatile or temporary key written to Redis have an explicit expiration time (`SETEX`, `EXPIRE`, `PEXPIRE`)?
- [ ] **Bounded In-Memory Limits**: Do in-process caches (`IMemoryCache`, `lru-cache`, `cachetools`) have a strict `maxsize` / `SizeLimit` configured?
- [ ] **Redis Eviction Alignment**: Is the Redis server's `maxmemory-policy` aligned with the workload (e.g. `volatile-lru` or `allkeys-lfu` for caches vs `noeviction` for primary session stores)?

### Dimension 2: Cache Stampede & Cold Start Defense
- [ ] **Single-Flight / Mutex Locking**: When high-traffic keys expire or on system cold start, is there a mechanism (distributed lock, single-flight helper, or .NET `HybridCache`) preventing thousands of concurrent queries from hitting the underlying database simultaneously?
- [ ] **Jittered Expiration**: Do batch cache entries add random jitter to their TTL (e.g., `TTL = 3600 + random(-300, 300)`) to prevent synchronized mass expiration?

### Dimension 3: Atomicity & Concurrency Integrity
- [ ] **Elimination of Check-Then-Act**: Are multi-step read-modify-write operations executed atomically via Redis Lua scripts or atomic primitives (`INCR`, `SETNX`, `HINCRBY`) rather than separated client network calls?
- [ ] **Safe Distributed Lock Release**: Does the lock release logic verify token ownership via a Lua script before issuing `DEL`?
- [ ] **Short Lua Execution Time**: Are Lua scripts kept under 5 ms to avoid blocking the single-threaded Redis engine?

### Dimension 4: Queue Consumption & Poison Pill Resilience
- [ ] **Dead Letter Queue (DLQ)**: Are deserialization errors (JSON parse failures) and unrecoverable domain validation errors caught and routed to a DLQ rather than crashing the consumer in an infinite retry loop?
- [ ] **Bounded Consumer Concurrency**: Do background workers throttle concurrent job execution (e.g. BullMQ concurrency, Channel reader limits) to prevent saturating database connection pools?

### Dimension 5: Kafka Partitioning & Offset Hygiene
- [ ] **Disabled Auto-Commit for Critical Pipelines**: Is `enable.auto.commit` disabled or carefully managed so offsets are committed strictly **after** message side-effects are safely persisted?
- [ ] **Deterministic Partition Keys**: Are messages keyed by entity ID (`order_id`, `user_id`) when sequential ordering is mandatory?
- [ ] **Partition Skew Check**: Is the partition key sufficiently granular to prevent 80% of events from flooding a single partition?

### Dimension 6: Non-Blocking Event Loop & Driver Hygiene
- [ ] **No Blocking Redis Commands**: Are `KEYS *`, `FLUSHALL`, `FLUSHDB`, and `SMEMBERS` on large sets banned in production code? Are `SCAN`, `HSCAN`, `SSCAN` used instead?
- [ ] **Driver Lifecycle / Singleton Multiplexer**: Is the Redis/Kafka client connection pooled or managed as a long-lived singleton rather than instantiated per HTTP request?
- [ ] **Asynchronous I/O**: Are all driver calls non-blocking (`await`) in Node.js, Python (`redis.asyncio`), and C# (`await _db.StringSetAsync`) to prevent event loop starvation?

### Dimension 7: Serialization & Payload Efficiency
- [ ] **Payload Minimization**: Are cached objects pruned to essential fields rather than storing multi-megabyte ORM entities with circular navigations?
- [ ] **Compression for Large Values**: Are cache values exceeding 50 KB compressed (e.g., Gzip/Brotli/Zstandard) before writing to Redis to reduce network egress?

---

## 2. Severity Classification Standards

| Severity | Definition | Action Required |
|---|---|---|
| **`[P0 - Blocker]`** | Unbounded in-memory cache risking OOM crash; missing TTL on high-volume Redis writes; unhandled poison pill halting consumer; race condition in lock release; auto-commit causing data loss. | Must fix before deployment. |
| **`[P1 - Major Issue]`** | Vulnerability to cache stampede on top-tier hot keys; blocking Redis commands (`KEYS *`); Kafka partition skew; unthrottled worker concurrency saturating database. | Must fix before release. |
| **`[P2 - Minor Optimization]`** | Missing pipelining for sequential multi-key writes; lack of `EVALSHA` caching for custom Lua; missing TTL jitter. | Recommended follow-up. |
| **`[P3 - Nit]`** | Key naming format deviations (e.g., not using `: ` namespaces `domain:entity:id`); minor metric tagging omissions. | Optional polish. |

---

## 3. High-Impact Anti-Pattern Code Diffs

### Anti-Pattern 1: Unsafe Distributed Lock Release
```typescript
// ❌ BAD: Del releases lock even if expired and re-acquired by worker B
async function unlock(lockKey: string) {
  await redis.del(lockKey);
}

// ✅ GOOD: Atomic Lua script verifies ownership token
async function unlock(lockKey: string, ownerToken: string) {
  const lua = `
    if redis.call("GET", KEYS[1]) == ARGV[1] then
      return redis.call("DEL", KEYS[1])
    else
      return 0
    end
  `;
  await redis.eval(lua, 1, lockKey, ownerToken);
}
```

### Anti-Pattern 2: Unbounded Local In-Memory Cache
```python
# ❌ BAD: Standard dictionary grows indefinitely without eviction (Memory Leak)
user_cache = {}

def get_user(user_id: str):
    if user_id not in user_cache:
        user_cache[user_id] = query_db(user_id)
    return user_cache[user_id]

# ✅ GOOD: Bounded TTL cache with automatic eviction
from cachetools import TTLCache

user_cache = TTLCache(maxsize=10_000, ttl=900)

def get_user(user_id: str):
    if user_id not in user_cache:
        user_cache[user_id] = query_db(user_id)
    return user_cache[user_id]
```
