# Python Data Structures & Data Engines: NumPy, Polars & Collection Selection

Comprehensive architectural guide for selecting the optimal data structures and processing engines in modern Python (Python 3.10–3.13): from standard library collections to high-performance vectorized numerical arrays (NumPy) and multi-threaded columnar DataFrames (Polars).

---

## 1. High-Performance Data Engines: NumPy vs. Polars vs. Pandas

When processing more than a few thousand records, pure Python loops incur massive interpreter overhead. Selecting between **NumPy**, **Polars**, and **Pandas** determines throughput, memory footprint, and CPU parallelism.

### Engine Decision Matrix

| Engine | Primary Data Model | Core Strength | Best For | When NOT to Use / Alternative | Memory Footprint | Parallelism |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **NumPy** | N-Dimensional homogeneous array (`ndarray`) | Hardware SIMD vectorized math, contiguous C/Fortran memory, low-level linear algebra | Matrix operations, tensor math, signal processing, ML feature arrays, numerical simulations | Tabular data with mixed types (strings + numbers + dates). Relational joins or group-by (use Polars). | **Minimal** (raw contiguous byte buffers) | Single-threaded (BLAS/LAPACK threads for matrix operations) |
| **Polars** | Apache Arrow columnar table (`DataFrame`, `LazyFrame`) | Written in Rust; multi-threaded query optimization; lazy execution; streaming out-of-core | Tabular ETL, CSV/Parquet processing, multi-million-row joins and aggregations, modern Pandas replacement | Pure matrix math, linear algebra (eigenvalues, SVD), or micro-datasets (< 100 rows) where DataFrame setup overhead dominates | **Optimal** (zero-copy Arrow chunking, string cache) | **Full multi-core** (Rust Rayon thread pool, GIL-free) |
| **Pandas** | Row/column tabular DataFrame (`DataFrame`, `Series`) | Massive legacy ecosystem, deep integration with legacy scikit-learn / matplotlib | Legacy codebases, small exploratory Jupyter notebooks with legacy plotting libraries | New production data pipelines, large datasets (> 100K rows), or multi-threaded servers (use Polars) | **Heavy** (high Python object overhead, frequent copying) | Single-threaded (blocks the GIL) |
| **Standard Library** | `list`, `dict`, `set`, `deque`, `array` | Zero external dependencies, pure Python object lifecycle | Business logic, API payloads, domain entities, internal service state | Heavy analytical processing, millions of numbers, or complex tabular queries | **High per item** (boxed PyObject overhead) | Single-threaded (GIL bound) |

---

### Deep Dive: NumPy (Vectorized Numerical Computing)

NumPy stores data in **contiguous blocks of memory** with a fixed C data type (`float64`, `int32`), completely eliminating Python `PyObject` header overhead (which is 28 bytes per integer in CPython).

#### When to Use NumPy:
1. **Homogeneous Numerical Data**: Coordinate points, audio buffers, image pixels ($H \times W \times C$), mathematical vectors.
2. **Matrix Algebra**: Dot products, matrix inversions, Fourier transforms (`np.fft`), eigenvalues.
3. **Broadcasting Operations**: Applying mathematical formulas across multidimensional arrays without Python `for` loops:

```python
import numpy as np

# Vectorized Euclidean distance calculation on 1,000,000 3D points
points = np.random.randn(1_000_000, 3)

# FAST: Computes via C SIMD instructions without Python loop overhead
distances = np.sqrt(np.sum(points ** 2, axis=1))
```

#### NumPy Anti-Patterns:
- **`dtype=object`**: Storing strings or mixed Python objects in a NumPy array degrades it to a list of pointers, losing all C-speed and SIMD advantages.
- **Dynamic appending (`np.append`)**: Unlike Python lists, NumPy arrays have fixed sizes. Calling `np.append()` inside a loop allocates a brand-new array and copies all elements every iteration ($O(n^2)$ complexity). Always pre-allocate with `np.empty()` or `np.zeros()`.

---

### Deep Dive: Polars (High-Throughput Columnar DataFrames)

Polars is designed from the ground up on the **Apache Arrow** columnar format and implemented in Rust. It utilizes **all available CPU cores** without Python GIL contention.

#### Why Polars Supersedes Pandas for Production:
1. **Lazy Evaluation (`LazyFrame`)**: Optimizes queries before executing:
   - **Predicate Pushdown**: Applies `.filter()` as early as possible (e.g. at the Parquet reader level), reading only relevant chunks from disk.
   - **Projection Pushdown**: Reads only the required columns, avoiding memory consumption for unused fields.
2. **Streaming Engine**: Can process datasets **larger than physical RAM** via `collect(streaming=True)`.
3. **No Index Complexity**: Unlike Pandas, Polars has no confusing row index (`MultiIndex`, `.loc` vs `.iloc`); columns are explicit Arrow arrays.

```python
import polars as pl

# High-Performance Lazy ETL Pipeline
def process_large_telemetry(file_path: str) -> pl.DataFrame:
    # 1. Scan lazily (does not load file into RAM immediately)
    lazy_query = (
        pl.scan_parquet(file_path)
        # Predicate pushdown: filtered directly at Parquet scan level
        .filter(pl.col("status") == "ERROR")
        .filter(pl.col("timestamp") >= pl.date(2026, 1, 1))
        # GroupBy and aggregation executed in parallel across all CPU cores
        .group_by("service_name")
        .agg([
            pl.count().alias("error_count"),
            pl.col("latency_ms").mean().alias("avg_latency"),
            pl.col("latency_ms").quantile(0.99).alias("p99_latency"),
        ])
        .sort("error_count", descending=True)
    )

    # 2. Execute with multi-threaded engine (optionally streaming if memory is tight)
    return lazy_query.collect(streaming=True)
```

#### When to Use Polars over NumPy:
- Mixed data types: combining timestamps, user IDs, categorical strings, and numerical metrics.
- Grouping, filtering, sorting, and windowing operations across columns.
- Reading/writing CSV, Parquet, JSON, and Iceberg/Delta lake tables.

---

## 2. Python Built-In Data Structures Selection Matrix

For general application code and business logic, selecting the correct standard library data structure guarantees optimal asymptotic runtime ($O(1)$ vs $O(n)$) and prevents memory bloat.

| Data Structure | Module | Lookup / Search | Insert / Add | Delete / Remove | Best For | When NOT to Use / Pitfall |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **`list`** | Built-in | Index: $O(1)$<br>Search: $O(n)$ | End: amortized $O(1)$<br>Middle/Start: $O(n)$ | End: $O(1)$<br>Middle/Start: $O(n)$ | Ordered sequential items, random index access, stack (LIFO) | **Queue (FIFO)**: `list.pop(0)` is $O(n)$ because it shifts all remaining elements in memory! Use `deque`. |
| **`collections.deque`** | `collections` | Index: $O(n)$ | Head/Tail: $O(1)$ | Head/Tail: $O(1)$ | **FIFO queues**, sliding windows (`maxlen=K`), BFS search traversal | Random access by index (`dq[i]` is slow $O(n)$). |
| **`set`** | Built-in | $O(1)$ average | $O(1)$ average | $O(1)$ average | Deduplication, uniqueness, membership tests (`x in my_set`), set algebra | Preserving insertion order or accessing items by index. |
| **`dict`** | Built-in | $O(1)$ average | $O(1)$ average | $O(1)$ average | Key-value mapping, fast lookup by ID, caching (insertion order preserved in Python 3.7+) | When keys are simple incremental integers (use a `list`). |
| **`collections.defaultdict`** | `collections` | $O(1)$ | $O(1)$ | $O(1)$ | Grouping items, accumulating values without verbose `if key not in d:` checks | When missing keys should raise a `KeyError` to flag programming errors. |
| **`collections.Counter`** | `collections` | $O(1)$ | $O(1)$ | $O(1)$ | Frequency maps, counting occurrences, finding top-$K$ frequent elements (`most_common(k)`) | General key-value lookups unrelated to tallies or frequencies. |
| **`heapq`** | `heapq` | Min: $O(1)$ (`h[0]`) | Push: $O(\log n)$ | Pop Min: $O(\log n)$ | **Priority queues**, scheduling, streaming top-$K$ smallest/largest elements | Full sorting when all elements are known upfront (use `list.sort()`). |
| **`bisect`** | `bisect` | $O(\log n)$ (Binary search) | Insert: $O(n)$ | N/A | Fast range queries, lookup tables, and searching in pre-sorted lists | Unsorted lists or frequent insertions where overhead of maintaining sort order is high. |
| **`array.array`** | `array` | Index: $O(1)$ | End: $O(1)$ | End: $O(1)$ | **Compact C-primitive storage** without third-party dependencies (integers, floats) | Heterogeneous objects or multidimensional matrix operations (use NumPy). |

---

## 3. Practical Data Structure Patterns

### Queue (FIFO): Always `collections.deque` over `list`
```python
from collections import deque

# ❌ ANTI-PATTERN: List as a queue (O(n) per pop!)
queue = []
queue.append(item)
task = queue.pop(0) # SLOW: shifts all remaining memory elements!

# ✅ BEST PRACTICE: Deque as a queue (O(1) popleft)
queue = deque()
queue.append(item)
task = queue.popleft() # Instant: O(1) pointer update
```

### Sliding Window / Fixed-Size Buffer: `deque(maxlen=K)`
When maintaining the last $K$ events (e.g. rate limiters, moving averages), `deque(maxlen=K)` automatically drops the oldest items when new items arrive with zero manual slicing overhead:
```python
# Automatically discards oldest element when capacity exceeds 100
recent_events = deque(maxlen=100)
for event in event_stream:
    recent_events.append(event)
```

### Fast Membership Checks: `set` vs `list`
```python
# ❌ ANTI-PATTERN: Linear scan inside loop -> O(N * M) Quadratic disaster!
banned_users = ["user1", "user2", ...] # 50,000 items
for txn in transactions:
    if txn.user_id in banned_users: # O(N) linear scan on EVERY transaction!
        flag(txn)

# ✅ BEST PRACTICE: Hash set lookup -> O(1)
banned_users_set = set(banned_users) # O(N) once upfront
for txn in transactions:
    if txn.user_id in banned_users_set: # O(1) constant time!
        flag(txn)
```

### Priority Queues & Top-$K$ with `heapq`
To find the top 10 largest transactions from a stream of 10,000,000 items, never sort the entire list ($O(n \log n)$). Use a bounded min-heap of size $K$ ($O(n \log k)$):
```python
import heapq

class TopKTracker:
    def __init__(self, k: int = 10) -> None:
        self.k = k
        self.heap: list[tuple[float, str]] = [] # stores (amount, txn_id)

    def add(self, amount: float, txn_id: str) -> None:
        if len(self.heap) < self.k:
            heapq.heappush(self.heap, (amount, txn_id))
        elif amount > self.heap[0][0]:
            heapq.heapreplace(self.heap, (amount, txn_id))

    def get_top_k(self) -> list[tuple[float, str]]:
        return sorted(self.heap, reverse=True)
```

---

## 4. Domain Modeling & Record Storage: Memory Comparison

When instantiating millions of domain objects, the storage mechanism drastically affects memory consumption and GC overhead:

| Storage Type | Mutability | Runtime Validation | Memory Overhead (per 1M instances) | Field Access Speed | Best For |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Standard Class (`class`)** | Mutable | Manual | $\approx 150$ MB (includes `__dict__`) | Moderate | Stateful domain entities with complex behaviors |
| **`@dataclass(slots=True)`** | Mutable / Frozen | Manual type hints | $\approx 48$ MB (eliminates `__dict__`) | **Fastest** (direct C struct pointer) | **Default choice** for internal domain models & services |
| **`NamedTuple`** | Immutable | None | $\approx 48$ MB (tuple structure) | Fast | Lightweight coordinate or SQL query tuples |
| **`Pydantic BaseModel`** | Configurable | **Automatic strict coercion** | $\approx 220$ MB (validation metadata) | Moderate | **API request/response boundaries**, JSON/YAML deserialization |
| **`dict`** | Mutable | None | $\approx 230$ MB | Fast | Dynamic schema-free JSON payloads |

> **Production Rule**: Use **Pydantic v2** at the API edge to validate incoming JSON payloads, but convert immediately to `@dataclass(slots=True, frozen=True)` for internal business domain processing to cut memory footprint by $4\times$.

