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

## 3. JVM Tuning & Garbage Collection (Java 21+)

### Collector Comparison
| GC Algorithm | Typical Pauses | Max Throughput | Generational Model | Best For | JVM Flags |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **G1 GC** (Default) | 10–50 ms | Highest | Generational (Region-based) | General web apps & microservices | `-XX:+UseG1GC` |
| **Generational ZGC** (Java 21+) | **< 1 ms** | ~95–98% of G1 | Generational (Young/Old separated) | Latency-critical, SLA-bound APIs, heaps > 8 GB | `-XX:+UseZGC -XX:+ZGenerational` |
| **Shenandoah** | 5–15 ms | Moderate | Generational in Java 21+ | Low-pause alternative on non-x86 or mixed environments | `-XX:+UseShenandoahGC` |

---

### Generational ZGC Tuning (Java 21 - JEP 439)

Java 21 introduces **Generational ZGC**, separating memory into young and old generations. It collects young objects frequently and concurrently without pausing application threads, resolving previous non-generational ZGC allocation stalls.

```bash
# Enable Generational ZGC in Java 21 / 22 (Default in Java 23+)
-XX:+UseZGC -XX:+ZGenerational

# Dynamic Heap Sizing (uncommits unused memory back to OS)
-XX:SoftMaxHeapSize=8g

# Allocation Burst Protection (factor to absorb traffic spikes, default 2.0)
-XX:ZAllocationSpikeTolerance=3.0
```
- **Do not tune generations manually**: Generational ZGC automatically dynamically sizes Eden/Old based on learned allocation rates.
- **When to Choose**: Microservices where sub-millisecond p99/p999 latency matters more than a 2–3% CPU throughput tradeoff.

---

### G1 GC Generational Tuning (Throughput & Predictability)

G1 divides the heap into equal regions (1 MB – 32 MB) dynamically designated as Eden, Survivor, or Old.

```bash
# 1. Target Pause Goal (Soft target; default 200ms)
-XX:MaxGCPauseMillis=100

# 2. Young Generation Boundaries (Reserve 10-50% for young gen)
-XX:G1NewSizePercent=10
-XX:G1MaxNewSizePercent=50

# 3. Dynamic Old-Gen Threshold (Adaptive IHOP prevents allocation failures)
-XX:+G1UseAdaptiveIHOP
-XX:InitiatingHeapOccupancyPercent=45

# 4. Humongous Allocation Tuning
# Objects > 50% region size bypass Young Gen directly to Old Gen, triggering early GCs.
# If logs show frequent humongous allocations, increase region size:
-XX:G1HeapRegionSize=16m
```

---

### Essential Production Flags (Containers & Cloud)
```bash
# Container Memory Awareness (Respects K8s/Docker cgroup limits)
-XX:MaxRAMPercentage=75.0
-XX:InitialRAMPercentage=75.0

# Automatic Diagnostics on Out-Of-Memory
-XX:+HeapDumpOnOutOfMemoryError
-XX:HeapDumpPath=/var/log/java/oom.hprof

# Print Unified GC Activity (Diagnose allocation spikes and pauses)
-Xlog:gc*,gc+phases=debug:file=/var/log/java/gc.log:time,uptime,pid:filecount=5,filesize=50M
```

