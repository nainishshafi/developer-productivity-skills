# TypeScript Concurrency & Throttling

Control asynchronous concurrency, prevent socket/connection exhaustion, and implement robust async orchestration.

---

## 1. Unbounded `Promise.all` Pitfall

`Promise.all` launches all promises concurrently. If an array has 5,000 items, it spawns 5,000 simultaneous network requests or database queries, causing:
- Database connection pool exhaustion (`Too many connections`).
- File descriptor exhaustion (`EMFILE`).
- Severe memory spikes.

```typescript
// ❌ ANTI-PATTERN: Spawns 10,000 simultaneous network/database connections
await Promise.all(recordIds.map(id => syncRecord(id)));

// ✅ BEST PRACTICE: Pool concurrency with p-limit
import pLimit from 'p-limit';

export async function processBatchConcurrently<T, R>(
  items: T[],
  fn: (item: T) => Promise<R>,
  concurrency = 10
): Promise<R[]> {
  const limit = pLimit(concurrency);
  return Promise.all(items.map(item => limit(() => fn(item))));
}
```

---

## 2. Partial Success with `Promise.allSettled`

When executing multiple independent operations where one failure should not abort the others, use `Promise.allSettled`:

```typescript
export async function sendBulkNotifications(userIds: string[], message: string) {
  const results = await Promise.allSettled(
    userIds.map(id => notificationClient.send(id, message))
  );

  const failures = results
    .filter((r): r is PromiseRejectedResult => r.status === 'rejected')
    .map(r => r.reason);

  if (failures.length > 0) {
    logger.warn(`Failed to deliver ${failures.length} notifications`, { failures });
  }
}
```

---

## 3. Sequential Async Iteration vs Concurrent

When operations must happen in strict sequence (e.g. database transactions or state-dependent migrations), use a standard `for...of` loop:

```typescript
// Executes sequentially, awaiting each step before starting next
for (const step of migrationSteps) {
  await executeMigrationStep(step);
}
```

