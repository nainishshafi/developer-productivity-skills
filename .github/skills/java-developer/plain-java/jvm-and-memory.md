# JVM, Memory Safety & Performance Optimization

Guidance for writing memory-safe code, diagnosing memory leaks, tuning the JVM, and optimizing execution on modern HotSpot runtimes.

---

## 1. Memory Safety & Leak Prevention

Although Java has automatic garbage collection, memory leaks occur when objects remain reachable through accidental references.

### Common Memory Leak Sources & Fixes
- **Unbounded Static Collections**: Caches stored in `static Map` grow indefinitely.
  - *Fix*: Use bounded caches with size/TTL limits (e.g., Caffeine). `WeakHashMap` only fits key-identity metadata, not general caching.
- **Dangling `ThreadLocal`**: In thread pools, worker threads are reused; a forgotten `ThreadLocal` retains its value across requests.
  - *Fix*: Always clear inside a `finally` block (`threadLocal.remove()`).
- **Unclosed OS Resources**: File handles, sockets, database connections.
  - *Fix*: Strictly enforce `try-with-resources`.
- **Non-Static Inner Classes**: Retain an implicit reference to the outer class instance, preventing outer class collection.
  - *Fix*: Use `static` nested classes or Java `record`.

### Escape Analysis & Stack Allocation
- The HotSpot JIT uses **Escape Analysis** to determine if an object's lifetime is confined to a method.
- If an object does not "escape", the JVM allocates its fields directly to CPU registers or the stack, eliminating heap allocation and GC overhead entirely.
- *Best practice*: Keep methods focused and avoid passing temporary objects outside their local scope when not needed.

---

## 2. Performance & JIT Optimization

- **Measure First**: Profile with JFR (`-XX:StartFlightRecording`) or async-profiler before optimizing; benchmark micro-optimizations with JMH, never with `System.currentTimeMillis()` loops.
- **JIT Inlining**: C2 always inlines tiny methods (`MaxInlineSize` = 35 bytes of bytecode) and hot methods up to a larger limit. Keep methods short and focused.
- **Avoid Reflection in Hot Paths**: Reflection bypasses JIT optimizations and incurs boxing/lookup penalties. Use MethodHandles, code generation, or lambdas instead.
- **Loops & String Building**:
  - String concatenation with `+` outside loops is optimized via `invokedynamic`.
  - Inside loops, always use `StringBuilder` with an estimated capacity to prevent repeated internal array resizing.
- **Exceptions as Control Flow**: Instantiating `Exception` is expensive because it captures the entire thread stack trace. Never use exceptions for normal business branching; use boolean flags, `Optional`, or result objects.

---

## 3. JVM Tuning & Garbage Collection (Java 17 / 21+)

### Garbage Collector Selection
| GC Algorithm | Primary Characteristic | Ideal Use Case | JVM Flag |
| :--- | :--- | :--- | :--- |
| **G1 GC** | Balanced throughput and predictable pause times. **(Default)** | General web applications and microservices. | `-XX:+UseG1GC` |
| **Generational ZGC** (Java 21+) | **Ultra-low latency (< 1ms pauses)**, scales to terabytes. | High-throughput, latency-critical trading or streaming systems. | `-XX:+UseZGC` (Java 23+ generational by default; add `-XX:+ZGenerational` on 21–22) |
| **Shenandoah** | Concurrent, low-pause alternative to ZGC. | Systems needing low latency without tuning overhead. | `-XX:+UseShenandoahGC` |

### Essential Production Flags (Containers & Cloud)
```bash
# Container Memory Awareness (Respects K8s/Docker cgroup limits)
-XX:MaxRAMPercentage=75.0
-XX:InitialRAMPercentage=75.0

# Automatic Diagnostics on Out-Of-Memory
-XX:+HeapDumpOnOutOfMemoryError
-XX:HeapDumpPath=/var/log/java/oom.hprof

# Print GC Activity without Third-Party Agents
-Xlog:gc*,gc+phases=debug:file=/var/log/java/gc.log:time,uptime,pid:filecount=5,filesize=50M
```

