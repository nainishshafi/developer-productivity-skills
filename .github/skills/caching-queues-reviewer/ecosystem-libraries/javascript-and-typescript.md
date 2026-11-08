# JavaScript & TypeScript: Caching & Queue Ecosystem

Comprehensive architectural guidance for Node.js (20+), Bun, and TypeScript when integrating in-memory caches, Redis clients, distributed job queues, and Apache Kafka.

---

## 1. Library Selection Matrix

| Category | Recommended Library | Alternative | When to Choose What |
|---|---|---|---|
| **In-Memory Cache (L1)** | **`lru-cache`** (v10+) | `quick-lru` | `lru-cache` provides size-based eviction, TTL, abort signals, and high throughput. Use `quick-lru` for smaller, lightweight dependency footprints. |
| **Redis Client** | **`ioredis`** | `redis` (node-redis) | `ioredis` is the industry standard for production TypeScript: first-class Redis Cluster & Sentinel support, automatic transparent `EVALSHA` Lua script caching, built-in pipelining, and connection event observables. |
| **Distributed Job Queue** | **`BullMQ`** | `bee-queue` / `agenda` | `BullMQ` is built on modern Redis Streams and Lua scripts. Supports parent-child job workflows, delayed jobs, rate-limited queues, exponential backoff retries, and worker concurrency throttling. |
| **Apache Kafka Client** | **`kafkajs`** | `@confluentinc/kafka-javascript` | `kafkajs` is pure TypeScript/JS with zero native compilation requirements; ideal for microservices and cloud runtimes. Use Confluent's wrapper when maximum multi-gigabit throughput with C `librdkafka` is needed. |

---

## 2. In-Memory Caching with `lru-cache`

```typescript
import { LRUCache } from 'lru-cache';

interface UserSession {
  userId: string;
  role: string;
  permissions: string[];
}

export const sessionCache = new LRUCache<string, UserSession>({
  max: 10_000, // Maximum items in memory
  ttl: 1000 * 60 * 15, // 15 minutes TTL
  updateAgeOnGet: true, // Sliders: extend TTL on access
  allowStale: false,
});
```

---

## 3. High-Performance Redis & Lua Execution with `ioredis`

```typescript
import Redis from 'ioredis';

export const redis = new Redis({
  host: process.env.REDIS_HOST ?? '127.0.0.1',
  port: Number(process.env.REDIS_PORT ?? 6379),
  maxRetriesPerRequest: null, // Required for BullMQ
  enableReadyCheck: true,
  lazyConnect: true,
});

// Define and register a custom atomic Lua script (preloaded with EVALSHA)
redis.defineCommand('releaseLock', {
  numberOfKeys: 1,
  lua: `
    if redis.call("GET", KEYS[1]) == ARGV[1] then
      return redis.call("DEL", KEYS[1])
    else
      return 0
    end
  `,
});

// TypeScript declaration merging for custom command
declare module 'ioredis' {
  interface Redis {
    releaseLock(key: string, ownerToken: string): Promise<number>;
  }
}

// Pipeline example (sub-millisecond batch execution)
export async function batchIncrementViews(productIds: string[]): Promise<void> {
  const pipeline = redis.pipeline();
  for (const id of productIds) {
    pipeline.hincrby(`product:${id}:stats`, 'views', 1);
    pipeline.expire(`product:${id}:stats`, 86400);
  }
  await pipeline.exec();
}
```

---

## 4. Distributed Background Job Processing with `BullMQ`

```typescript
import { Queue, Worker, Job } from 'bullmq';
import { redis } from './redis.js';

interface EmailJobData {
  to: string;
  template: string;
  variables: Record<string, string>;
}

// Producer Queue
export const emailQueue = new Queue<EmailJobData>('email-delivery', {
  connection: redis,
  defaultJobOptions: {
    attempts: 5,
    backoff: {
      type: 'exponential',
      delay: 2000,
    },
    removeOnComplete: 1000,
    removeOnFail: 5000,
  },
});

// Consumer Worker with Bounded Concurrency
export const emailWorker = new Worker<EmailJobData>(
  'email-delivery',
  async (job: Job<EmailJobData>) => {
    // Business logic
    await sendEmailService(job.data.to, job.data.template, job.data.variables);
  },
  {
    connection: redis,
    concurrency: 10, // Process up to 10 jobs in parallel per process
    limiter: {
      max: 50, // Max 50 jobs per second (rate limit defense)
      duration: 1000,
    },
  }
);
```

---

## 5. Kafka Event Consumer with Manual Offset Commit in `kafkajs`

```typescript
import { Kafka, logLevel } from 'kafkajs';

const kafka = new Kafka({
  clientId: 'order-service',
  brokers: (process.env.KAFKA_BROKERS ?? 'localhost:9092').split(','),
  logLevel: logLevel.WARN,
});

const consumer = kafka.consumer({
  groupId: 'order-processing-group',
  // Disable auto-commit to prevent data loss or duplicate processing
});

export async function startOrderConsumer(): Promise<void> {
  await consumer.connect();
  await consumer.subscribe({ topic: 'orders.v1', fromBeginning: false });

  await consumer.run({
    autoCommit: false, // Manual commit control
    eachBatch: async ({ batch, resolveOffset, heartbeat, commitOffsetsIfNecessary }) => {
      for (const message of batch.messages) {
        if (!message.value) continue;

        try {
          const order = JSON.parse(message.value.toString());
          await processOrderTransaction(order);

          // Mark message resolved and update offset checkpoint
          resolveOffset(message.offset);
          await heartbeat(); // Keep consumer alive during long batches
        } catch (err) {
          console.error(`Poison pill in offset ${message.offset}:`, err);
          await routeToDeadLetterQueue(message);
          resolveOffset(message.offset);
        }
      }
      // Commit once per batch of successfully processed messages
      await commitOffsetsIfNecessary();
    },
  });
}
```
