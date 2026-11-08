# Java Concurrency, Virtual Threads & JVM Memory Review Guide

Audit guide for Java 21+ Virtual Threads (Project Loom), concurrency, and JVM resource hygiene.

---

## 1. Virtual Threads & Carrier Thread Pinning

- [ ] **Carrier Thread Pinning**:
  - Do virtual threads execute blocking I/O inside `synchronized` blocks or native methods?
  - Pinning a virtual thread prevents the carrier thread (OS thread) from unmounting, defeating the scalability of virtual threads.
  - **Resolution**: Replace `synchronized` with `java.util.concurrent.locks.ReentrantLock` when performing I/O.
- [ ] **Thread Pooling of Virtual Threads**:
  - Are virtual threads pooled in an `ExecutorService` with fixed size? (Anti-pattern; virtual threads should be created per-task via `Executors.newVirtualThreadPerTaskExecutor()`, never pooled).
- [ ] **ThreadLocal Bloat**:
  - Are massive `ThreadLocal` structures used with millions of virtual threads?
  - **Resolution**: Use `ScopedValue` (Preview in Java 21+) for lightweight, immutable context passing.

---

## 2. Concurrency Primitives & Synchronization

- [ ] **Atomic Variables & Locks**:
  - Are counters using `AtomicInteger` or `LongAdder` rather than raw volatile variables or heavy synchronized methods?
- [ ] **Deadlock Hazards**:
  - Are multiple locks acquired in a globally consistent order across all threads?

---

## 3. JVM Memory Leaks & Resource Cleanup

- [ ] **ThreadLocal Cleanup in Thread Pools**:
  - Are `ThreadLocal.remove()` calls guaranteed inside a `finally` block when using platform thread pools? Leaked thread locals cause permanent heap retention.
- [ ] **Static Collection Accumulation**:
  - Are `static Map` or `static List` objects growing indefinitely without eviction?
  - **Resolution**: Use Guava `CacheBuilder` or Caffeine with size/time limits.
- [ ] **Non-Static Inner Classes**:
  - Do inner classes hold an implicit reference to an outer class instance, preventing outer class garbage collection?

