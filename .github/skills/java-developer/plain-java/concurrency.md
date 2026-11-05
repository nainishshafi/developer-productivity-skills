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

### What to Avoid & Limitations

1. **Never Pool Virtual Threads**: Creating a pool defeats their design. Allocate them freely per task (`newVirtualThreadPerTaskExecutor()`).
2. **Limit Downstream Concurrency with a `Semaphore`**: Unbounded virtual threads can spawn 100,000 parallel calls and crush downstream database pools or third-party APIs:
   ```java
   private final Semaphore dbThrottle = new Semaphore(50); // limit concurrent DB queries
   public void queryDb() throws InterruptedException {
       dbThrottle.acquire();
       try { doBlockingQuery(); }
       finally { dbThrottle.release(); }
   }
   ```
3. **Avoid for CPU-Heavy Tasks**: Virtual threads do not make compute faster; use standard platform thread pools sized to available CPU cores (`Runtime.getRuntime().availableProcessors()`).
4. **`ThreadLocal` Memory Bloat**:
   - In platform pools, thousands of requests reuse a few dozen threads. In Java 21, spawning 100,000 virtual threads each holding a `ThreadLocal` copies data 100,000 times, causing rapid heap exhaustion.
   - *Mitigation*: Prefer passing request context explicitly via parameters or use `ScopedValue` (preview in Java 21, final in 25).
   - If a library leaks thread-locals, disable them when spawning:
     ```java
     Thread.ofVirtual().allowSetThreadLocals(false).name("worker-", 0).start(runnable);
     ```

### Carrier Thread Pinning (Java 21)

When a virtual thread cannot be unmounted from its underlying OS "carrier" thread during a blocking operation, it is **pinned**. If all carrier threads become pinned (default pool size = CPU cores), thread starvation occurs and throughput collapses.

#### 1. Primary Cause: `synchronized` Blocks (Java 21–23)
In Java 21, blocking I/O (socket read/write, lock wait) inside a `synchronized` block or method holds the carrier thread:
- **Avoid**:
  ```java
  // Bad in Java 21: pins the carrier thread during network I/O
  public synchronized String fetchRemoteData() {
      return httpClient.get(url);
  }
  ```
- **Fix**: Replace `synchronized` with `ReentrantLock`:
  ```java
  // Good: unmounts cleanly while waiting on lock or I/O
  private final ReentrantLock lock = new ReentrantLock();
  public String fetchRemoteData() {
      lock.lock();
      try { return httpClient.get(url); }
      finally { lock.unlock(); }
  }
  ```
- *Note*: JEP 491 (Java 24+) removes `synchronized` pinning; however, `synchronized` still pins on Java 21 LTS runtimes.

#### 2. Native Code & JNI Pinning
Calling native methods (`JNI`) or C-libraries via Panama FFI inside a virtual thread pins the carrier thread across all Java versions. Offload native calls to a dedicated platform thread pool.

#### 3. Detecting Pinning in Java 21
- **JVM Flag (Java 21–23)**:
  ```bash
  -Djdk.tracePinnedThreads=full   # Prints full stack trace on pinning
  -Djdk.tracePinnedThreads=short  # Prints single-line warning
  ```
- **Java Flight Recorder (JFR)**: Inspect the `jdk.VirtualThreadPinned` event in JDK Mission Control.

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
- **Use `*Async` variants when thread isolation matters**: Non-async callbacks (`thenApply`) run on whichever thread completes the upstream stage (or the caller thread if already complete). Use `thenApplyAsync(fn, executor)` when the callback is expensive or blocking.
- **Avoid premature `.get()` or `.join()`**: Calling `.join()` immediately blocks the thread, destroying the async benefit. Chain transformations instead.
- **Do not ignore errors**: Always handle failures via `.exceptionally()` or `.handle()`.
- **Always set timeouts** on remote calls: `.orTimeout(2, SECONDS)` or `.completeOnTimeout(fallback, 2, SECONDS)`.

---

## 4. Summary: Which to Choose?

1. Need to perform independent blocking calls sequentially or in simple loops? **Use Virtual Threads** with standard structured code.
2. Need to fire off 3 parallel API calls and merge their JSON responses into one? **Use `CompletableFuture.allOf()`** or `thenCombine` (or Virtual Threads with `StructuredTaskScope` — still preview as of Java 25).
3. Streaming infinite real-time events or building edge gateways? **Use Reactive Streams (`Flux` / `Mono`)** — see [Reactor Patterns Guide](reactor-pattern.md).
4. Running matrix multiplication or crypto hashing? **Use Platform Thread Pools** (`Executors.newFixedThreadPool(Runtime.getRuntime().availableProcessors())`).

