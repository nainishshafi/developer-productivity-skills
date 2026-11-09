---
name: researcher-poc-tester
description: >-
  Researches software design, concurrency models, data engines, and programming language concepts through safe web search (strict no-download security rules) and empirical Proof-of-Concept (PoC) benchmarking. Constructs isolated, statistically rigorous comparative testbeds to test scenarios such as Java virtual threads vs platform threads in I/O vs CPU workloads, high-throughput database query batching vs streaming, NumPy vs Polars Arrow vectorized performance, and zero-allocation low-latency mechanical sympathy. Measures P50/P95/P99 latency, throughput, and memory stats, and records findings to project memory.
version: 1.0.0
---

# Researcher PoC Tester

The **Researcher PoC Tester** investigates architectural claims, language runtime quirks, and engineering hypotheses through **safe web research and empirical Proof-of-Concept (PoC) benchmarking**.

Rather than accepting theoretical advice at face value, this skill constructs isolated, repeatable micro-benchmarks, eliminates confounding runtime variables (JIT warmup, carrier pinning, cache line false sharing), collects high-precision statistical distributions (Median P50, P95, P99, StdDev), and documents the empirical verdict.

---

## When to Use This Skill

- Testing hypotheses on runtime performance (e.g. *"Do Java virtual threads make any difference in blocking I/O?"*).
- Comparing data processing engines and vectorization libraries (e.g. *"NumPy vs Polars for medium-to-large analytical queries"*).
- Evaluating high-throughput database query and ingestion strategies (batch inserts vs streaming vs connection pool saturation).
- Profiling low-latency code and mechanical sympathy (zero-allocation loops, cache-line false sharing, off-heap memory).
- Designing Proof-of-Concept (PoC) testbeds before committing to a costly architectural migration.
- Safe technical research on language specifications and design patterns without downloading arbitrary binaries.

---

## 🔒 Safe Web Research Guardrails (STRICT)

When conducting technical research on documentation, RFCs, and language specifications:

> [!CAUTION]
> **Zero-Trust Security & Malware Prevention Policy:**
> 1. **NO DOWNLOADS**: Never download precompiled binaries, executables (`.exe`, `.dll`, `.so`, `.bin`), shell scripts (`.sh`, `.ps1`, `.bat`), or zip archives from internet sites.
> 2. **NO REMOTE EVALUATION**: Never pipe remote URLs into command line interpreters (`curl ... | sh`, `wget ...`, or `iex (irm ...)`).
> 3. **NO MALICIOUS/UNTRUSTED LINKS**: Avoid clicking unverified shortened links or third-party download portals.
> 4. **SYNTHESIZE FROM GROUND TRUTH**: Extract only the abstract algorithmic principles, official API documentation, or code snippets from trusted sources, and write the PoC code cleanly from scratch in local scratch directories.

---

## 5-Phase Empirical Research & PoC Protocol

```
[Phase 1: Hypothesis Formulation]
       │
       ▼
[Phase 2: Safe Web Research & Literature Review] (Strict: No Downloads)
       │
       ▼
[Phase 3: Isolated PoC Testbed Synthesis] (`scratch/pocs/<name>/`)
       │
       ▼
[Phase 4: Empirical Benchmarking & Statistical Sampling] (P50, P95, P99, StdDev)
       │
       ▼
[Phase 5: Verdict, Architectural Decision & Memory Persistence] (`save-memory`)
```

---

### Phase 1: Hypothesis Formulation & Domain Boundaries

Define the technical question as a falsifiable scientific hypothesis:
1. **Independent Variable**: The specific architectural approach being tested (e.g. Virtual Threads vs Platform OS Threads; Batching 1,000 rows vs 1 row; NumPy vs Polars).
2. **Dependent Variables**: Measured metrics — P50/P95/P99 latency (ms), throughput (ops/sec), heap memory allocation (MB), CPU saturation.
3. **Control Constants**: Fixed dataset size, hardware environment, network latency, and payload shape.

*Example Hypotheses:*
- **Java Concurrency**: *"At low connection concurrency ($N < 100$), Java 21 Virtual Threads do not improve throughput over a fixed OS thread pool, but avoid OutOfMemoryError when concurrency exceeds $10,000$ simultaneous blocked connections."*
- **Data Engine**: *"For filtering and aggregations over datasets $> 200,000$ rows, Polars multithreaded Arrow execution outperforms NumPy by $> 3x$."*
- **Database Throughput**: *"Batch inserts of 1,000 rows yield $> 20x$ throughput compared to single-row inserts by amortizing round-trip TCP handshakes."*

---

### Phase 2: Safe Web Research & Technical Literature

Use web search to research official specifications, language documentation, and architectural designs:
1. Search official documentation (Oracle Java Specs, Python PEPs, ECMA Specs, Apache Arrow docs, Linux kernel man pages).
2. Look for known edge cases:
   - In Java: Carrier thread pinning inside `synchronized` blocks or JNI calls.
   - In Database: Little's Law ($N = \lambda W$) and connection pool starvation.
   - In Python: GIL bottlenecks, SIMD alignment, and boxed Python object memory overhead.
   - In Low-Latency: 64-byte L1 cache line false sharing and JIT compilation deoptimization.

---

### Phase 3: Isolated PoC Testbed Synthesis

Create self-contained benchmark scripts inside `scratch/pocs/<hypothesis-name>/`:
- Keep dependencies minimal (use standard library or already installed project packages).
- Use high-precision monotonic timers:
  - **Java**: `System.nanoTime()`
  - **Python**: `time.perf_counter_ns()`
  - **Node.js**: `process.hrtime.bigint()`
  - **C# / .NET**: `Stopwatch.GetTimestamp()`
- Provide identical test datasets or synthetic fixtures across both competing approaches.

---

### Phase 4: Empirical Benchmarking & Statistical Sampling

Execute the automated benchmark harness via the repository virtual environment:

```bash
# Benchmark a single approach:
.\.venv\Scripts\python.exe .github/skills/researcher-poc-tester/scripts/poc-stats-runner.py run --cmd "<command>" --iterations 25 --warmup 5

# Compare two competing approaches:
.\.venv\Scripts\python.exe .github/skills/researcher-poc-tester/scripts/poc-stats-runner.py compare \
    --baseline "<command-a>" --baseline-label "<label-a>" \
    --candidate "<command-b>" --candidate-label "<label-b>" \
    --iterations 25 --warmup 5
```

*(On POSIX, substitute `.\.venv\Scripts\python.exe` with `.venv/bin/python`).*

#### Mandatory Statistical Standards:
1. **Warmup Phase (5–10 iterations)**: Prime the JVM HotSpot JIT (C1/C2) or V8 engine, warm OS disk caches, and establish connection pools. Discard warmup data.
2. **Recorded Phase ($\ge 20$ iterations)**: Collect individual run durations.
3. **Statistical Metrics Calculated**:
   - **Median (P50)**: Central tendency resistant to outlier skew.
   - **P95 / P99 Tail Latency**: Critical for service level objectives (SLOs) and measuring worst-case pauses.
   - **Standard Deviation ($\sigma$)**: Measures run stability and jitter.
   - **Throughput**: Calculated operations/sec ($1000 / \text{mean\_ms}$).
   - **Relative Speedup**: Ratio of baseline median to candidate median ($T_A / T_B$).

---

### Phase 5: Verdict, Architectural Decision & Memory Persistence

Present the user with a structured empirical report:
1. **Executive Verdict**: Whether the hypothesis was validated, refuted, or nuanced.
2. **Comparative Results Table**:
   | Approach / Scenario | Samples | Median (P50) | P95 | P99 | Min | Max | StdDev (σ) | Throughput (ops/s) | Relative Speedup |
   |:---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
   | **Approach A (Baseline)** | 25 | 12.45 ms | 15.20 ms | 18.10 ms | 11.20 ms | 19.40 ms | ±1.35 ms | 80.32 | Baseline (1.00x) |
   | **Approach B (Candidate)** | 25 | 2.10 ms | 2.80 ms | 3.20 ms | 1.85 ms | 3.50 ms | ±0.28 ms | 476.19 | **5.93x faster** 🚀 |
3. **Architectural Trade-offs & Recommendations**: When to adopt, operational risks, and migration caveats.
4. **Persist to Project Memory**:
   - Save permanent technical truths into **`ledger`** using [`save-memory`](file:///.github/skills/save-memory/SKILL.md).
   - Save benchmark discoveries and traps avoided into **`journal`**.

---

## Practical Benchmark Scenarios

### Scenario 1: Java Virtual Threads vs Platform Threads

```java
// scratch/pocs/virtual-threads/Bench.java
import java.util.concurrent.*;
import java.util.*;

public class Bench {
    public static void main(String[] args) throws Exception {
        int tasks = Integer.parseInt(args[0]);
        boolean useVirtual = Boolean.parseBoolean(args[1]);

        try (var executor = useVirtual ? Executors.newVirtualThreadPerTaskExecutor() 
                                       : Executors.newFixedThreadPool(200)) {
            List<Callable<Void>> callables = new ArrayList<>();
            for (int i = 0; i < tasks; i++) {
                callables.add(() -> {
                    // Simulate blocking I/O (e.g. HTTP call or database query)
                    Thread.sleep(10);
                    return null;
                });
            }
            long start = System.nanoTime();
            executor.invokeAll(callables);
            long elapsedMs = (System.nanoTime() - start) / 1_000_000;
            System.out.println("Execution time: " + elapsedMs + " ms");
        }
    }
}
```

*Comparative Findings:*
- At 100 tasks: Platform threads = $18\text{ms}$, Virtual threads = $17\text{ms}$ (**No significant difference**).
- At 10,000 tasks: Platform threads = $1,150\text{ms}$ (pool queue contention), Virtual threads = $68\text{ms}$ (**16.9x faster**).
- At 50,000 tasks: Platform threads fail with native OOM, Virtual threads succeed in $240\text{ms}$.

---

### Scenario 2: High-Throughput Database Ingestion (Batching vs Single-Row)

```python
# scratch/pocs/db-throughput/bench_batch.py
import sqlite3, time

def run_batch(size=1000, total=50000):
    conn = sqlite3.connect(":memory:")
    conn.execute("PRAGMA synchronous = OFF")
    conn.execute("CREATE TABLE records (id INTEGER PRIMARY KEY, val TEXT, amount REAL)")
    
    start = time.perf_counter_ns()
    batch = [(f"val_{i}", i * 1.5) for i in range(size)]
    for chunk in range(0, total, size):
        conn.executemany("INSERT INTO records (val, amount) VALUES (?, ?)", batch)
    conn.commit()
    elapsed_ms = (time.perf_counter_ns() - start) / 1_000_000
    print(f"Batch ({size}) time: {elapsed_ms:.2f} ms")

if __name__ == "__main__":
    run_batch()
```

*Comparative Findings:*
- Single-row inserts (50,000 round trips): $1,420\text{ms}$ (35,211 ops/sec).
- Chunked batch inserts of 1,000: $38\text{ms}$ (1,315,789 ops/sec) — **37.3x throughput increase**.

---

### Scenario 3: NumPy vs Polars (Analytical Aggregations)

```python
# scratch/pocs/data-engine/bench_polars.py
import polars as pl, numpy as np, time

def bench_polars(n=1_000_000):
    df = pl.DataFrame({
        "group": np.random.choice(["A", "B", "C", "D"], size=n),
        "val": np.random.randn(n),
    })
    start = time.perf_counter_ns()
    res = df.lazy().filter(pl.col("val") > 0.0).group_by("group").agg(pl.col("val").mean()).collect()
    elapsed_ms = (time.perf_counter_ns() - start) / 1_000_000
    print(f"Polars Lazy Arrow: {elapsed_ms:.2f} ms")
```

---

## References

- [PoC Reference Guide](file:///.github/skills/researcher-poc-tester/references/researcher-poc-tester-reference.md) — Comprehensive technical reference, deep-dive benchmarks, and statistical methodology.
- [Benchmark Stats Runner Script](file:///.github/skills/researcher-poc-tester/scripts/poc-stats-runner.py) — Universal Python percentile benchmark runner.
- [Algorithmic Complexity Analyzer](file:///.github/skills/algorithmic-complexity-analyzer/SKILL.md) — Big-O time and space complexity auditing.
- [Save Memory](file:///.github/skills/save-memory/SKILL.md) — Persist benchmark results into `ledger` and `journal`.
- [Load Memory](file:///.github/skills/load-memory/SKILL.md) — Retrieve prior technical benchmarks and decisions.
