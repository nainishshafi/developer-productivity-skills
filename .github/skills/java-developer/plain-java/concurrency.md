# Java Concurrency: Virtual Threads & CompletableFuture

## 1. Quick Decision Matrix

| Mechanism | Primary Use Case | Programming Style | Thread Model |
| :--- | :--- | :--- | :--- |
| **Virtual Threads (Java 21+)** | High-volume blocking I/O (HTTP, DB queries) | Synchronous / imperative (`thread-per-task`) | Lightweight JVM-managed |
| **`CompletableFuture`** | Fan-out/fan-in aggregation & async pipelines | Asynchronous / reactive chaining | Callback & promise-based |
| **Platform Threads** | Long-running CPU-bound computation | Task pools | 1:1 OS thread mapping |

---

## 2. Virtual Threads (Project Loom)

### When to Use
- High-concurrency I/O-bound operations (e.g., handling thousands of concurrent REST or database calls).
- When you want clean, readable, synchronous code without the cognitive load of reactive chains.
- Spawning short-lived tasks using `Executors.newVirtualThreadPerTaskExecutor()`.

### What to Avoid
- **Never pool virtual threads**: Creating a pool defeats their design. Allocate them freely per task.
- **Limit concurrency with a `Semaphore`, not a pool**: Unbounded virtual threads can overwhelm downstream resources (DB connection pools, rate-limited APIs).
- **Avoid for CPU-heavy tasks**: Virtual threads do not make compute faster; use standard thread pools sized to available CPU cores for compute workloads.
- **Avoid heavy `ThreadLocal` usage**: Spawning hundreds of thousands of virtual threads with large `ThreadLocal` data can quickly exhaust heap memory. Prefer `ScopedValue` (final in Java 25) for request context.

### Carrier Thread Pinning
When a virtual thread cannot be unmounted from its underlying OS "carrier" thread during a blocking operation, it is **pinned**. This degrades system throughput.
- **Java 21–23**: Blocking inside `synchronized` pins. Replace `synchronized` blocks that guard blocking I/O with `ReentrantLock`:
  ```java
  private final ReentrantLock lock = new ReentrantLock();
  public void execute() {
      lock.lock();
      try { blockingIoCall(); }
      finally { lock.unlock(); }
  }
  ```
- **Java 24+**: `synchronized` no longer pins (JEP 491); no rewrite needed. Native/JNI calls still pin.
- **Detect pinning** with the JFR event `jdk.VirtualThreadPinned` (`-Djdk.tracePinnedThreads` was removed in Java 24).

### Executor Lifecycle
`ExecutorService` is `AutoCloseable` (Java 19+); scope executors with try-with-resources so tasks complete and threads are released:
```java
try (var executor = Executors.newVirtualThreadPerTaskExecutor()) {
    ids.forEach(id -> executor.submit(() -> fetch(id)));
} // waits for all tasks
```

### Thread-Safety Basics
- Prefer immutability and confinement over locking.
- Use `AtomicInteger` / `LongAdder` for counters, `ConcurrentHashMap` for shared maps.
- Never share mutable non-thread-safe objects (`SimpleDateFormat`, `HashMap`) across threads; use `DateTimeFormatter` and concurrent collections.

---

## 3. `CompletableFuture`

### When to Use
- Aggregating or combining results from multiple independent async tasks (fan-out / fan-in):
  ```java
  var userFuture = CompletableFuture.supplyAsync(() -> userService.getUser(id), executor);
  var orderFuture = CompletableFuture.supplyAsync(() -> orderService.getOrders(id), executor);
  var combined = userFuture.thenCombine(orderFuture, DashboardDto::new);
  ```
- Event-driven or callback pipelines (`thenApply`, `thenCompose`, `thenAccept`). For end-to-end pipeline design, see [Functional Programming Guide](functional-programming.md).
- Integrating with asynchronous event buses or non-blocking external libraries.

### What to Avoid
- **Avoid `ForkJoinPool.commonPool()` for blocking I/O**: The default pool is sized for CPU tasks. Always supply a dedicated executor (`supplyAsync(task, ioExecutor)`).
- **Avoid premature `.get()` or `.join()`**: Calling `.join()` immediately blocks the thread, destroying the async benefit. Chain transformations instead.
- **Do not ignore errors**: Always handle failures via `.exceptionally()` or `.handle()`.
- **Always set timeouts** on remote calls: `.orTimeout(2, SECONDS)` or `.completeOnTimeout(fallback, 2, SECONDS)`.

---

## 4. Summary: Which to Choose?

1. Need to perform independent blocking calls sequentially or in simple loops? **Use Virtual Threads** with standard structured code.
2. Need to fire off 3 parallel API calls and merge their JSON responses into one? **Use `CompletableFuture.allOf()`** or `thenCombine` (or Virtual Threads with `StructuredTaskScope` — still preview as of Java 25).
3. Streaming infinite real-time events or building edge gateways? **Use Reactive Streams (`Flux` / `Mono`)** — see [Reactor Patterns Guide](reactor-pattern.md).
4. Running matrix multiplication or crypto hashing? **Use Platform Thread Pools** (`Executors.newFixedThreadPool(Runtime.getRuntime().availableProcessors())`).

