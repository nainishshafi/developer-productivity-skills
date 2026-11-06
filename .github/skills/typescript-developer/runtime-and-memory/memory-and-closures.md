# TypeScript Memory Safety, Closures & Resource Hygiene

Deep-dive guidelines for diagnosing, preventing, and eliminating memory leaks, closure scope retention, and unmanaged resources in Node.js and TypeScript runtimes.

---

## 1. Closure Memory Retention & Scope Hygiene

### The Pitfall: Accidental Enclosing Scope Capture
In JavaScript/TypeScript, when an inner function is created, it retains a reference to its lexical environment. If that closure is stored in a long-lived structure (e.g. an event bus, cache, global array, or long-lived promise), it holds every variable in that outer scope in RAM, preventing garbage collection.

```typescript
// ❌ ANTI-PATTERN: Closure retains heavy request/context object indefinitely
function registerAuditLogger(req: RequestWithLargeContext) {
  // Long-lived event listener retains `req` (including payload buffers, sockets, and headers)!
  auditQueue.on('drain', () => {
    logger.info(`Audit logged for request ${req.id} from IP ${req.ip}`);
  });
}

// ✅ BEST PRACTICE: Extract only the needed primitives into the closure scope
function registerAuditLogger(req: RequestWithLargeContext) {
  const { id: reqId, ip: clientIp } = req; // primitives extracted
  auditQueue.on('drain', () => {
    logger.info(`Audit logged for request ${reqId} from IP ${clientIp}`);
  });
}
```

---

## 2. Event Listener & Subscription Leaks

### The Pitfall: Forgotten Event Listeners
Attaching listeners to `EventEmitter` or DOM targets in transient or per-request code without removing them is the most common cause of Node.js `MaxListenersExceededWarning` and gradual memory growth.

```typescript
// ❌ ANTI-PATTERN: Accumulates a new listener on every incoming request
export function handleRequest(eventEmitter: EventEmitter, req: Request, res: Response) {
  eventEmitter.on('update', (data) => {
    res.write(JSON.stringify(data));
  });
  // If connection closes without eventEmitter.off(), the closure and `res` socket leak!
}

// ✅ BEST PRACTICE: Use AbortSignal to auto-remove listeners upon task completion
import { EventEmitter } from 'node:events';

export async function waitForSpecificEvent(
  emitter: EventEmitter,
  eventName: string,
  timeoutMs: number
): Promise<unknown> {
  const ac = new AbortController();
  const timer = setTimeout(() => ac.abort(), timeoutMs);

  try {
    return await new Promise((resolve, reject) => {
      // Listener is automatically removed when ac.abort() fires!
      emitter.on(eventName, resolve, { signal: ac.signal });
      ac.signal.addEventListener('abort', () => reject(new Error('Operation timed out')), { once: true });
    });
  } finally {
    clearTimeout(timer);
  }
}
```

---

## 3. Bounded Caches vs Unbounded `Map` / `Set`

Never use a raw `Map` or `Set` as an application-level cache. An unbounded collection will continuously grow until the Node.js V8 heap exhausts its limit (`ERR_WORKER_OUT_OF_MEMORY` / crash).

```typescript
// ❌ ANTI-PATTERN: Unbounded cache grows infinitely
const queryCache = new Map<string, object>();

export function getCachedUser(id: string) {
  if (queryCache.has(id)) return queryCache.get(id);
  // ...
}

// ✅ BEST PRACTICE: Use a bounded LRU Cache with Max Capacity and TTL
import { LRUCache } from 'lru-cache';

export const userCache = new LRUCache<string, User>({
  max: 5000,              // Keep at most 5,000 users in memory
  ttl: 1000 * 60 * 15,    // 15-minute TTL
  allowStale: false,
  updateAgeOnGet: true,
});
```

### Leveraging `WeakMap` & `WeakSet`
When attaching metadata to object instances (e.g. tracking processed requests or transaction metadata), use `WeakMap`. The keys are held weakly: when the object is no longer referenced elsewhere, it and its associated metadata are automatically collected by V8.

```typescript
// ✅ BEST PRACTICE: Metadata is automatically garbage-collected when request finishes
const requestTimings = new WeakMap<Request, number>();

export function markStart(req: Request) {
  requestTimings.set(req, Date.now());
}

export function getDuration(req: Request): number {
  const start = requestTimings.get(req);
  return start ? Date.now() - start : 0;
}
```

---

## 4. Timer & Interval Hygiene

Forgotten `setInterval` timers keep the Node.js process alive and prevent variables captured in their closures from ever being freed.

```typescript
// ✅ BEST PRACTICE: Always store timer reference and clear during teardown
export class HeartbeatService {
  private timer: NodeJS.Timeout | null = null;

  start() {
    if (this.timer) return;
    this.timer = setInterval(() => this.ping(), 30_000);
    // Unref allows the process to exit naturally if only this timer is pending
    this.timer.unref();
  }

  stop() {
    if (this.timer) {
      clearInterval(this.timer);
      this.timer = null;
    }
  }
}
```

