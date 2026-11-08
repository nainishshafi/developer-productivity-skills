# TypeScript Async & Concurrency Review Guide

Audit guide for asynchronous patterns, Promises, concurrency limits, and cancellation in TypeScript.

---

## 1. Floating Promises & Await Traps

- [ ] **Floating Promises**:
  - Are promises invoked without `await`, `.catch()`, or `void` operator?
  - Flag unhandled floating promises as `[P1 - Major]`. They can silently fail without triggering error handlers.
- [ ] **Sequential Await Bottlenecks**:
  - Are independent async calls awaited sequentially inside loops?
  ```typescript
  // BAD: Sequential delay
  for (const id of ids) {
    await fetchItem(id);
  }

  // GOOD: Concurrent with bounded throttle
  await pLimit(5)(ids.map(id => () => fetchItem(id)));
  ```
- [ ] **`Promise.all` Failure Semantics**:
  - If one promise fails in `Promise.all()`, the whole batch rejects immediately.
  - If partial success is desired, use `Promise.allSettled()` and inspect each result's `status === 'fulfilled'`.

---

## 2. Concurrency Throttling

- [ ] **Unbounded `Promise.all`**:
  - Does code execute `Promise.all(largeArray.map(...))` on hundreds or thousands of items?
  - This exhausts file descriptors, database connections, and memory.
  - **Resolution**: Bound concurrency using `p-limit` or batch chunks:
  ```typescript
  import pLimit from 'p-limit';
  const limit = pLimit(10);
  const results = await Promise.all(items.map(item => limit(() => processItem(item))));
  ```

---

## 3. Cancellation & Timeout Propagation

- [ ] **`AbortController` & `AbortSignal`**:
  - Do long-running fetch requests or child processes accept an `AbortSignal`?
  - Are timeouts enforced via `AbortSignal.timeout(ms)`?
  ```typescript
  const response = await fetch(url, { signal: AbortSignal.timeout(5000) });
  ```
- [ ] **Cleanup on Cancellation**:
  - Do async listeners unbind and cleanup pending work when `signal.aborted` fires?

