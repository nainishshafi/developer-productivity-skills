# Python Concurrency, Memory & Runtime Review Guide

Review guidelines for Python asynchronous programming, event loop safety, memory management, and data processing.

---

## 1. Asyncio & Event Loop Safety

- [ ] **Blocking the Event Loop**:
  - Are blocking calls (`time.sleep()`, synchronous I/O, heavy CPU computations) called inside `async def` functions?
  - **Resolution**: Offload blocking operations using `await asyncio.to_thread(func, *args)` or run CPU-heavy tasks in `ProcessPoolExecutor`.
- [ ] **Task Concurrency Bounds**:
  - Is `asyncio.gather(*tasks)` unbounded on user-controlled input?
  - **Resolution**: Throttle concurrent tasks using `asyncio.Semaphore(max_concurrency)`.
- [ ] **Task Cancellation & Shielding**:
  - Are critical persistence steps protected with `asyncio.shield()` where partial execution could corrupt state?
  - Do long-running tasks handle `asyncio.CancelledError` gracefully and clean up background resources?
- [ ] **Fire-and-Forget Task Traps**:
  - Are background tasks created via `asyncio.create_task()` kept in a strong reference set until completion to prevent garbage collection mid-execution?

---

## 2. Memory Hygiene & Garbage Collection

- [ ] **Unbounded In-Memory Caches**:
  - Are dictionaries used as caches without eviction limits or TTLs?
  - **Resolution**: Use `@functools.lru_cache(maxsize=1024)` or bounded cache structures (`cachetools.TTLCache`).
- [ ] **Circular References**:
  - Do parent-child object graphs create strong reference cycles that delay garbage collection?
  - **Resolution**: Use `weakref.ref` or `weakref.proxy` for back-references.
- [ ] **Generator Iteration vs. Materialization**:
  - Are multi-gigabyte files or large DB result sets loaded entirely into memory via `.readlines()` or `.fetchall()`?
  - **Resolution**: Stream using iterators, generators (`yield`), or server-side database cursors.

---

## 3. DataFrames & Scientific Computing (Pandas / Polars / NumPy)

- [ ] **Vectorization vs. Iteration**:
  - Are operations iterating over rows using `.iterrows()` or `.itertuples()` in performance-sensitive paths?
  - **Resolution**: Use vectorized columnar operations, `.apply()`, or Polars expressions.
- [ ] **Downcasting & Categoricals**:
  - Are high-cardinality low-variety string columns converted to `category` dtypes?
  - Are numeric columns downcast (`int64` $\to$ `int32`/`int16`) when memory is constrained?
- [ ] **Copy vs. View Warnings**:
  - Are assignments triggering `SettingWithCopyWarning`? Ensure explicit `.copy()` or indexing via `.loc[row, col] = val`.
- [ ] **Memory Release in Long Batches**:
  - Are large dataframes deleted (`del df`) and garbage collected (`import gc; gc.collect()`) in batch pipelines?

