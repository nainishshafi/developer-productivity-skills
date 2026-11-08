# Low-Latency Java & Mechanical Sympathy

Architectural guidance for writing ultra-low-latency, zero-allocation, high-throughput systems on modern Java runtimes.

---

## 1. Mechanical Sympathy & CPU Cache Architecture

"Mechanical sympathy" (coined by Martin Thompson) means designing software that aligns with the underlying CPU and memory hardware rather than fighting it.

### CPU Cache Hierarchy & 64-Byte Cache Lines
Modern CPUs access data through hierarchical caches (L1 $\approx 1$ ns, L2 $\approx 3$ ns, L3 $\approx 10$ ns) before main RAM ($\approx 60$–$100$ ns).
- Memory is loaded from RAM into CPU caches in discrete chunks called **Cache Lines** (typically **64 bytes**).
- **Spatial Locality**: Storing data sequentially in memory (e.g. primitive arrays `long[]`) ensures that loading one element brings the next several elements into L1 cache for free.
- **Pointer Chasing Penalty**: Linked structures (`LinkedList`, node-based trees, boxed objects with references) scatter memory across the heap. Each dereference incurs a cache miss ($\approx 60$ ns latency stall).

### False Sharing & Cache-Line Contention
**False sharing** occurs when two independent variables accessed by different threads reside within the same 64-byte cache line:
```text
Thread 1 (Core 1) writes variable A ──┐
                                     ├──> Same 64-byte Cache Line
Thread 2 (Core 2) writes variable B ──┘    (Core 1 invalidates Core 2's L1/L2 cache!)
```
Even though the threads never access the same variable, Core 1's write forces Core 2's CPU to invalidate its cache line, generating constant bus traffic and catastrophic throughput collapse.

#### Mitigating False Sharing
1. **JVM `@Contended` Annotation (JEP 142)**:
   Pads the field or class with 128 bytes to isolate it into its own cache line:
   ```java
   public class SequenceHolder {
       // Requires JVM flag: -XX:-RestrictContended
       @jdk.internal.vm.annotation.Contended
       private volatile long value;
   }
   ```
2. **Explicit Long Padding (Portable across all JVMs)**:
   Pad variables with 7 unused `long` variables ($7 \times 8 = 56$ bytes) surrounding the target variable:
   ```java
   public class PaddedAtomicSequence {
       // Pre-padding (56 bytes)
       private long p1, p2, p3, p4, p5, p6, p7;
       // Target value (8 bytes) -> 64 bytes total
       private volatile long sequence = 0L;
       // Post-padding (56 bytes)
       private long p8, p9, p10, p11, p12, p13, p14;

       public long get() { return sequence; }
       public void set(long val) { this.sequence = val; }
   }
   ```

---

## 2. Zero-Allocation Steady State in Hot Paths

Even modern low-pause collectors (Generational ZGC, Shenandoah) introduce minor CPU overhead and memory bandwidth contention. For ultra-low-latency workloads (financial trading, real-time telemetry, market feeds), the steady-state execution path must allocate **zero bytes on the heap**.

### Core Zero-Allocation Rules
1. **Never Allocate in the Ingestion Loop**:
   Pre-allocate a fixed pool of mutable message objects at startup and reuse them via a ring buffer.
2. **Avoid Auto-Boxing**:
   Never use boxed primitives (`Integer`, `Long`, `Double`) in latency-critical loops. Use native arrays (`long[]`), specialized primitive collections (FastUtil, Eclipse Collections), or `LongConsumer` / `LongPredicate`.
3. **Avoid Capturing Lambdas & Closures**:
   ```java
   // BAD: Captures 'threshold', allocating a new lambda instance on every call
   int threshold = getLimit();
   list.removeIf(item -> item.value() > threshold);

   // GOOD: Use reusable static predicate or traditional indexed loop
   for (int i = 0; i < size; i++) {
       if (array[i] > threshold) { /* in-place swap / compact */ }
   }
   ```
4. **Pre-Size Collections and StringBuffers**:
   Never rely on auto-resizing collections (`ArrayList`, `StringBuilder`, `HashMap`). Always specify capacity upfront to avoid array allocations and `System.arraycopy` during execution.

---

## 3. Off-Heap Memory: Foreign Function & Memory (FFM) API

Java 22+ introduces the **Foreign Function & Memory API (JEP 454)**, providing standard, safe, and zero-overhead off-heap memory access that completely replaces unsafe hacks (`sun.misc.Unsafe`) and bulky `ByteBuffer.allocateDirect()`.

### Why Off-Heap?
- Off-heap memory is completely invisible to the JVM Garbage Collector.
- Store multi-gigabyte caches or continuous event buffers without increasing GC pause times or heap footprint.

### Using `Arena` and `MemorySegment` (Java 22+)
```java
import java.lang.foreign.*;
import java.lang.invoke.VarHandle;

public class OffHeapRingBuffer implements AutoCloseable {
    private final Arena arena;
    private final MemorySegment segment;
    private final long capacity;
    private static final ValueLayout.OfLong LONG_LAYOUT = ValueLayout.JAVA_LONG;

    public OffHeapRingBuffer(long numElements) {
        this.capacity = numElements;
        // Allocate deterministic off-heap memory bound to this arena's lifecycle
        this.arena = Arena.ofShared();
        this.segment = arena.allocate(numElements * LONG_LAYOUT.byteSize(), LONG_LAYOUT.byteAlignment());
    }

    public void write(long index, long value) {
        long offset = (index % capacity) * LONG_LAYOUT.byteSize();
        segment.set(LONG_LAYOUT, offset, value);
    }

    public long read(long index) {
        long offset = (index % capacity) * LONG_LAYOUT.byteSize();
        return segment.get(LONG_LAYOUT, offset);
    }

    @Override
    public void close() {
        // Releases native off-heap memory immediately without waiting for GC
        arena.close();
    }
}
```

### Memory-Mapped Files with FFM
Zero-copy persistence directly mapped to operating system virtual memory:
```java
import java.lang.foreign.*;
import java.nio.channels.FileChannel;
import java.nio.file.Path;
import java.nio.file.StandardOpenOption;

public class MemoryMappedJournal {
    public static void mapJournal(Path path, long sizeBytes) throws Exception {
        try (var channel = FileChannel.open(path, StandardOpenOption.READ, StandardOpenOption.WRITE, StandardOpenOption.CREATE)) {
            try (var arena = Arena.ofConfined()) {
                // Maps file directly into off-heap memory
                MemorySegment mapped = channel.map(FileChannel.MapMode.READ_WRITE, 0, sizeBytes, arena);
                
                // Fast binary writes without Java heap buffers
                mapped.set(ValueLayout.JAVA_LONG, 0, 100_000_001L);
                mapped.force(); // Flush dirty pages to disk
            }
        }
    }
}
```

---

## 4. Low-Latency Inter-Thread Messaging: LMAX Disruptor Pattern

The **LMAX Disruptor** is a lock-free, zero-allocation inter-thread messaging library designed for high-throughput, sub-microsecond financial order execution.

```text
Producer(s) ──> [ RingBuffer: Pre-allocated circular array ] ──> Consumer(s)
                           │
                Sequence & SequenceBarriers (CAS & volatile)
```

### Core Architecture Principles
1. **Circular RingBuffer**:
   - Size must be a power of 2 ($2^N$).
   - Sequence calculation uses fast bitwise masking: `index = sequence & (bufferSize - 1)`, avoiding expensive CPU division (`%`).
2. **Lock-Free Sequencing**:
   - Uses atomic sequence numbers and memory barriers instead of mutexes (`synchronized`, `ReentrantLock`), avoiding thread context switches and kernel transitions.
3. **Pre-allocated Event Objects**:
   - The ring buffer is pre-populated with empty event instances at boot. Producers claim a sequence number, populate the event in place, and publish the sequence.

### Disruptor Wait Strategies

| Wait Strategy | Latency | CPU Utilization | Use Case |
| :--- | :--- | :--- | :--- |
| **`BusySpinWaitStrategy`** | Lowest (sub-microsecond) | 100% of dedicated CPU core | Critical trading engines with dedicated core pinning. |
| **`YieldingWaitStrategy`** | Ultra-low ($\approx 1 \mu s$) | High (spins then calls `Thread.yield()`) | Low-latency services sharing cores with other tasks. |
| **`SleepingWaitStrategy`** | Low ($\approx 5$–$10 \mu s$) | Moderate (spins, yields, then parks) | Asynchronous loggers and non-critical event dispatchers. |
| **`BlockingWaitStrategy`** | Moderate ($\approx 20$–$50 \mu s$) | Minimal (uses `ReentrantLock.Condition`) | Throughput-focused batch systems where CPU conservation matters. |

---

## 5. Chronicle Queue & High-Performance IPC

For ultra-fast communication between independent JVM processes on the same machine, network sockets (`localhost:8080`) introduce kernel transitions, TCP stack overhead, and serialization costs.

### Chronicle Queue Architecture
- Uses **memory-mapped files (`/dev/shm` on Linux)** as an off-heap, lock-free, zero-copy IPC journal.
- **Microsecond Latency**: Writing a message takes $< 100$ nanoseconds; reading takes $< 100$ nanoseconds.
- **Persistence for Free**: Because the queue is mapped directly to a file, every message is inherently recorded to disk while remaining in OS page cache.
- **Multi-Process Sharing**: One JVM writes to the queue; another JVM tail-reads it immediately via shared memory without network serialization.

