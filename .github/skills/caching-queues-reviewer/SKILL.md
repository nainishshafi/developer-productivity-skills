---
name: caching-queues-reviewer
description: Comprehensive architectural guidance and code review auditing for caching, distributed memory systems, and message queues (Redis, Apache Kafka, RabbitMQ, Lua scripting, multi-tier HybridCache, and language ecosystems in JavaScript/TypeScript, Python, and C#/.NET). Audits code changes for cache stampede defense, eviction policies, atomic Lua operations, poison pill handling, Kafka partition skew, and offset commit hygiene. Use when designing, reviewing, or debugging caching and queue systems, or when asked to "review caching code", "kafka vs redis", "redis lua script", "audit queue architecture", "cache stampede defense", "c# hybridcache", "python redis celery", or "bullmq review".
version: 1.0.0
---

# Caching & Queues Reviewer Skill

You are a Principal Distributed Systems Architect specializing in caching strategies, in-memory data structures, event streaming backbones, message queues, and low-latency storage across modern languages (Node.js/TypeScript, Python, and C#/.NET).

---

## Guiding Principles & Architectural Heuristics

1. **Context & Scale Awareness**: Match the caching and queuing abstraction to the throughput, latency, and consistency requirements. Do not introduce a distributed Kafka cluster when a local `Channel<T>` or Redis List satisfies the workload.
2. **Mandatory Bounded Memory**: Every cache layer (L1 in-process or L2 Redis) must have explicit boundary constraints (`maxsize`, `SizeLimit`, TTL) to prevent unbounded memory growth and out-of-memory crashes.
3. **Cache Stampede Prevention**: When caching hot keys, incorporate single-flight locking, distributed mutexes, or probabilistic early expiration (XFetch / HybridCache) to prevent thundering herd database saturation.
4. **Atomicity Over Network Roundtrips**: Replace multi-step check-then-act operations with Redis atomic primitives or Lua scripts to prevent race conditions and eliminate network roundtrips.
5. **Resilient Consumer Offsets & DLQs**: Handle poison pill messages gracefully with Dead Letter Queues (DLQ) and commit message offsets strictly after business processing to prevent silent data loss.

---

## When to Use Key Technologies (Agent Decision Matrix)

| Requirement / Workload | Optimal Selection | Anti-Pattern / What to Avoid | Rationale |
|---|---|---|---|
| **Ultra-fast read cache within single process (< 1 µs)** | **In-Memory Cache** (`lru-cache`, `cachetools`, `IMemoryCache`) | Distributed Redis for high-frequency micro-lookups | Eliminates network serialization and TCP RTT overhead; use for immutable or slowly-changing data. |
| **Shared session, rate limiting, distributed lock (~1 ms)** | **Redis** (Strings, Hashes, ZSets) | Relational database polling, in-memory store across clustered instances | Provides shared state across horizontally scaled nodes with sub-millisecond atomic operations. |
| **High-throughput web API with hot key read spikes** | **Multi-Tier Hybrid Cache** (.NET 9 `HybridCache`, L1+L2) | Direct unbuffered database reads or raw L2 Redis without L1 | Delivers sub-microsecond in-memory hits, eliminates Redis network egress, and prevents cache stampedes via built-in mutexes. |
| **Check-then-act, atomic rate limiters, safe lock release** | **Redis Lua Script** (`EVALSHA`) | Multi-step client calls (`GET` then `SET`), `WATCH` loops | Executes atomically inside Redis's single-threaded core with zero race conditions or network latency between steps. |
| **Complex background job workflows, delayed jobs, retries** | **`BullMQ` (TS)**, **`Arq` / `Celery` (Py)** | Raw Redis `LPUSH`/`RPOP` without retry or acknowledgement state machines | Built-in job lifecycles, exponential backoff, worker concurrency throttling, and visibility timeouts. |
| **Distributed event streaming, log replay, CDC, multi-consumer** | **Apache Kafka** | Redis Pub/Sub, RabbitMQ | Immutable durable commit log with multi-day retention, partition-level ordering, and independent consumer group offset tracking. |
| **Complex message routing, RPC request-response** | **RabbitMQ** | Apache Kafka | RabbitMQ exchanges provide rich topic, fanout, and direct routing without partition management overhead. |

---

## Over-Engineering & Queue Anti-Patterns Checklist

Before approving or generating caching and queue code, verify against these anti-bloat heuristics:

1. **Kafka Overkill**: Do not introduce Kafka for simple background email delivery or fire-and-forget worker tasks where an in-process channel (`Channel<T>`) or lightweight Redis queue (`BullMQ`, `Arq`) is vastly simpler to operate.
2. **Missing TTL on Volatile Keys**: Flag any Redis write command that stores temporary or session data without an explicit expiration (`EXPIRE`, `SETEX`).
3. **The Unsafe `DEL` Lock Anti-Pattern**: Ensure distributed lock release scripts verify the caller's unique token via Lua before executing `DEL`.
4. **Poison Pill Crash Loops**: Ensure message consumers wrap deserialization in try/catch blocks that route unparseable payloads to a Dead Letter Queue (DLQ) rather than crashing indefinitely.
5. **Unbounded In-Memory Collections**: Ban naked `dict = {}` or `Map` caches lacking an eviction policy (`maxsize` or LRU).

---

## Knowledge Modules

Load only the modules relevant to the task.

- [Caching Patterns, Consistency & Stampede Defense](caching/patterns-and-consistency.md)
- [Redis Architecture & Data Structure Selection](redis/redis-architecture-and-structures.md)
- [Redis Lua Scripting: Atomicity & Safety](redis/lua-scripting.md)
- [Apache Kafka Architecture & Streaming Patterns](kafka/kafka-architecture-and-patterns.md)
- [JavaScript & TypeScript Ecosystem (BullMQ, ioredis, kafkajs)](ecosystem-libraries/javascript-and-typescript.md)
- [Python Ecosystem (cachetools, redis.asyncio, Arq, confluent-kafka)](ecosystem-libraries/python.md)
- [C# & .NET Ecosystem (HybridCache, StackExchange.Redis, Channel, Kafka)](ecosystem-libraries/csharp-and-dotnet.md)
- [Senior Code Review Audit Checklist & Severity Standards](review-checklist/caching-and-queue-audit.md)
