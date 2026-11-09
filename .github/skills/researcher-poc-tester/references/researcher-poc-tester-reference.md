# Researcher PoC Tester Reference Guide

An architectural and operational handbook for conducting rigorous technical research, formulating falsifiable engineering hypotheses, and executing statistically sound Proof-of-Concept (PoC) benchmarks.

---

## 1. Scientific PoC Methodology

Every technical Proof-of-Concept must adhere to the scientific method to prevent confirmation bias, cherry-picked benchmarks, and misleading architectural conclusions:

```
┌─────────────────────────────────┐
│ 1. Formulate Hypothesis (H0/H1) │ ──► Define independent variable, expected delta, and failure criteria
└────────────────┬────────────────┘
                 │
                 ▼
┌─────────────────────────────────┐
│ 2. Safe Web Research & Literature│ ──► Survey official specs & RFCs (STRICT: no untrusted downloads)
└────────────────┬────────────────┘
                 │
                 ▼
┌─────────────────────────────────┐
│ 3. Isolated PoC Harness Design  │ ──► Scratch directory (`scratch/pocs/<name>/`), isolate confounding factors
└────────────────┬────────────────┘
                 │
                 ▼
┌─────────────────────────────────┐
│ 4. Statistically Rigorous Run   │ ──► Warmup rounds, high-precision timers, P50/P95/P99, StdDev
└────────────────┬────────────────┘
                 │
                 ▼
┌─────────────────────────────────┐
│ 5. Memory Persistence & Report  │ ──► Save empirical findings to `ledger` and lessons to `journal`
└─────────────────────────────────┘
```

### Isolating Confounding Variables

1. **JIT & Dynamic Runtime Warmup**:
   - Modern runtimes (JVM HotSpot C1/C2, V8 in Node.js, PyPy) compile and optimize hot code paths dynamically.
   - **Rule**: Never record metrics during the first 5–10 iterations. Discard warmup runs to measure steady-state performance.
2. **Timer Precision & Drift**:
   - Never use wall-clock time (`Date.now()`, `time.time()`) which can drift backwards due to NTP synchronization.
   - Always use monotonic, high-resolution timers:
     - **Java**: `System.nanoTime()`
     - **Python**: `time.perf_counter_ns()`
     - **Node.js**: `process.hrtime.bigint()`
     - **C# / .NET**: `Stopwatch.GetTimestamp()`
3. **Garbage Collection (GC) & Memory Allocations**:
   - Triggering full GC sweeps during a benchmark skews P99 and max latency.
   - Measure heap allocation delta before and after runs. In low-latency PoCs, monitor zero-allocation steady states.
4. **OS Page Cache & Disk I/O**:
   - For database and file I/O tests, differentiate between "cold disk" reads and OS page cache hits. Use controlled fixture generation or clear OS caches where relevant.

---

## 2. Deep-Dive Scenarios & Empirical Benchmarks

### Scenario A: Java Virtual Threads vs. Platform OS Threads vs. Reactive

#### The Common Myth:
*"Virtual threads make every Java application 10x faster."* Or conversely: *"Virtual threads make no difference in I/O operations."*

#### The Empirical Reality:
- **Low Concurrency ($N < 200$)**: Virtual threads provide **zero performance benefit** compared to an optimized platform thread pool (`Executors.newFixedThreadPool(CPU_CORES * 2)`). The OS kernel thread scheduler is already hyper-optimized.
- **High Concurrency ($N > 10,000$ concurrent blocked connections)**: Platform threads fail with `OutOfMemoryError: unable to create native thread` because each OS thread allocates a $1\text{MB}$ stack reservation. Virtual threads have shallow initial stacks ($\sim 1\text{KB}$) stored on the heap, allowing $100,000+$ simultaneous blocked connections without exhausting system memory.
- **CPU-Bound Tasks**: Virtual threads provide **no speedup** and incur slight scheduler context-switch overhead ($\approx 1\text{--}5\%$ slower).
- **The Carrier Pinning Trap**:
  ```java
  // CRITICAL FAILURE: Virtual thread cannot unmount from carrier thread!
  synchronized (lock) {
      blockingIoOperation(); // Pins underlying ForkJoin carrier OS thread!
  }
  // CORRECT SOLUTION: ReentrantLock allows virtual thread to unmount cleanly
  lock.lock();
  try {
      blockingIoOperation();
  } finally {
      lock.unlock();
  }
  ```
- **Database Connection Pool Bottleneck**:
  - Spawning 10,000 virtual threads to query a database with an 80-connection pool (`HikariCP`) does **not** increase query throughput. The threads spend their time blocked waiting for database connections. Little's Law ($N = \lambda W$) proves throughput is bounded by database execution time, not client concurrency.

---

### Scenario B: High-Throughput Database Querying & Ingestion

#### The Core Variables:
1. **Batching vs. Single-Row Round Trips**:
   - Network latency is typically $0.5\text{ms} \dots 5\text{ms}$ per round trip.
   - Inserting 10,000 rows one by one: $10,000 \times 1\text{ms} = 10\text{ seconds}$.
   - Multi-row chunked batch (`INSERT ... VALUES (...), (...)` in chunks of 1,000): $10 \times 3\text{ms} = 30\text{ms}$ (**330x faster**).
2. **Cursor Streaming vs. Offset Pagination**:
   ```sql
   -- DEGRADES AS OFFSET GROWS: O(N) scan through 1,000,000 discarded rows
   SELECT * FROM orders ORDER BY id LIMIT 50 OFFSET 1000000;

   -- CONSTANT TIME: O(log N) B-Tree seek via Keyset Pagination
   SELECT * FROM orders WHERE id > 1000000 ORDER BY id LIMIT 50;
   ```
3. **SQLite Throughput Knobs (Ephemeral Testbeds)**:
   - Default SQLite disk writes require full `fsync` disk flushes per transaction.
   - Tuning for $100,000+$ writes/sec in PoCs:
     ```sql
     PRAGMA journal_mode = WAL;
     PRAGMA synchronous = NORMAL;
     PRAGMA temp_store = MEMORY;
     PRAGMA cache_size = -64000; -- 64MB memory cache
     ```

---

### Scenario C: NumPy vs. Polars vs. Pandas (Data Engine Benchmark)

#### Architecture Comparison:

| Feature | Pandas | NumPy | Polars |
|---|---|---|---|
| **Memory Model** | Boxed Python objects / 1D NumPy arrays | Contiguous C/Fortran numeric buffers | Apache Arrow Columnar (Zero-Copy) |
| **Execution** | Single-threaded, GIL locked | Single-threaded C vectorized loops (SIMD) | Multithreaded Rust query engine, parallel chunk processing |
| **Query Planning** | Eager execution only | Eager array slicing | Lazy evaluation with Predicate & Projection Pushdown |
| **String Operations** | Slow Python string pointers | Fixed-width or object arrays | Arrow string view dictionary encoding |

#### Empirical Rules of Thumb:
- **Small Math Vectors ($N < 50,000$)**: NumPy is faster because Polars thread-pool dispatch and Arrow chunk overhead is unnecessary.
- **Medium/Large Datasets ($N > 200,000$) with GroupBy, Filter, Join**: Polars is **5x to 30x faster** than Pandas and 3x faster than raw NumPy, while consuming 60% less RAM due to memory chunk reuse and SIMD Arrow kernels.

---

### Scenario D: Low-Latency Systems & Mechanical Sympathy

#### 1. Cache-Line False Sharing:
Modern CPU architectures cache memory in **64-byte cache lines**. If Thread 1 on Core A writes to `counterA` and Thread 2 on Core B writes to `counterB`, and both counters reside in the same 64-byte segment, the hardware MESI cache coherence protocol forces constant cache-line invalidation between cores:

```
[ Cache Line: 64 Bytes ]
┌──────────────────────────────┬──────────────────────────────┐
│  Core A: counterA (8 bytes)  │  Core B: counterB (8 bytes)  │  <── FALSE SHARING!
└──────────────────────────────┴──────────────────────────────┘
```

**Remediation**:
- In Java: `@jdk.internal.vm.annotation.Contended` or manual 128-byte object padding (`long p1, p2, p3, p4, p5, p6, p7;`).
- In C#: `[StructLayout(LayoutKind.Explicit)]` with `[FieldOffset(64)]`.

#### 2. Zero-Allocation Steady States:
In high-frequency trading (HFT) and ultra-low-latency microservices, object allocation in hot paths triggers young-generation GC pauses.
- **Techniques**: Ring buffers (LMAX Disruptor), primitive arrays instead of wrapper objects, reusable buffers (`ArrayPool<T>` in C#, `ByteBuffer.allocateDirect` / FFM `Arena` in Java 22+).

---

## 3. Safe Web Research Security Protocol (STRICT)

When researching technical documentation, language specs, and architectural trade-offs:

> [!CAUTION]
> **Strict Anti-Malware & Safety Guardrail:**
> 1. **NO DOWNLOADS**: Never download arbitrary binaries, precompiled executables (`.exe`, `.dll`, `.so`), shell scripts (`.sh`, `.ps1`), or zip archives from internet sites.
> 2. **NO BLIND EVALUATION**: Never pipe remote URLs into command evaluators (`curl ... | sh` or `iex (irm ...)`).
> 3. **NO MALICIOUS/UNTRUSTED LINKS**: Never click unverified shortened links or visit software distribution repositories with poor reputation.
> 4. **SYNTHESIZE LOCALLY**: Extract purely abstract algorithmic principles, official API documentation, or code snippets from verified sources, and implement the PoC code cleanly from scratch inside the repository sandbox.

### Approved Research Sources:
- Official Language & Vendor Specifications (Oracle OpenJDK docs, Python PEPs, ECMA specifications, Microsoft .NET docs, Rust RFCs).
- Reputable Engineering Blogs (Netflix TechBlog, Cloudflare Blog, Uber Engineering, Meta Engineering, Martin Fowler).
- Peer-Reviewed Computer Science Literature (ACM, IEEE, Usenix).

---

## 4. Benchmark Runner Integration

Use the automated Python benchmark harness `poc-stats-runner.py`:

```powershell
# Benchmark single scenario:
.\.venv\Scripts\python.exe .github/skills/researcher-poc-tester/scripts/poc-stats-runner.py run `
    --cmd "node scratch/pocs/virtual-threads/test.mjs" `
    --iterations 25 --warmup 5

# Compare two approaches:
.\.venv\Scripts\python.exe .github/skills/researcher-poc-tester/scripts/poc-stats-runner.py compare `
    --baseline "python scratch/pocs/engine/numpy_test.py" --baseline-label "NumPy Vectorized" `
    --candidate "python scratch/pocs/engine/polars_test.py" --candidate-label "Polars Arrow" `
    --iterations 30 --warmup 5
```
