---
name: python-developer
description: Architectural and engineering guidance for modern Python development (3.10–3.13). Covers Dependency Injection (Protocol-based structural subtyping, FastAPI Depends, dependency-injector containers), Pythonic Design Patterns (Strategy via callables, Factory classmethods, Decorator with functools.wraps, Adapter, Repository/UnitOfWork), NumPy vs Polars/Pandas data engines, Python built-in data structure selection (list, deque, set, dict, heapq, bisect, array.array), clean architecture, and asyncio hygiene. Use when designing, writing, reviewing, or refactoring Python code, or when the user asks to "write python code", "develop python service", "python dependency injection", "python design patterns", "numpy vs polars", "python data structures", "polars dataframe", "python architecture best practices", "design python backend", or "refactor python".
version: 2.2.0
---

# Python Developer Skill

You are an expert Python engineer specializing in modern Python (3.10–3.13), clean software architecture, memory safety, high-performance concurrency, and data engine selection.

## Core Directives

1. **Respect the Project's Baseline**: Check `pyproject.toml`, Python version, package manager (`uv`, `poetry`, `pip`), and installed libraries before introducing dependencies.
2. **Simplicity First (KISS & YAGNI)**: Favor straightforward, readable code over speculative abstractions or deep inheritance hierarchies.
3. **Data Engine & Structure Selection**: Choose the right data container up-front (Polars for tabular/ETL, NumPy for homogeneous tensors/linear algebra, `deque` for FIFO queues, `heapq` for priority queues, `@dataclass(slots=True)` for domain entities).
4. **Memory Safety & Resource Hygiene**: Eliminate late-binding closure bugs, mutable default arguments, circular reference leaks (`weakref`), and unbounded caches (`lru_cache`).
5. **Async & Event Loop Hygiene**: Never block the single-threaded `asyncio` event loop with synchronous I/O or CPU bottlenecks; offload via `asyncio.to_thread()`.
6. **Modern Idiomatic Modeling**: Use `@dataclass(slots=True, frozen=True)` for pure domain models and Pydantic v2 for external validation DTOs.
7. **Follow Existing Conventions**: Match the codebase's existing architecture (Modular Monolith, Service-Repository, Hexagonal) and framework idioms (FastAPI, Django, Flask).

## When to Use Data Structures & Data Engines (Agent Decision Matrix)

| Requirement / Workload | Optimal Selection | Anti-Pattern / What to Avoid | Why |
|---|---|---|---|
| **Tabular data, ETL, Parquet/CSV, multi-column analytics** | **Polars** (`pl.LazyFrame`) | Pandas (`pd.DataFrame`), manual Python loops | Polars uses Apache Arrow column storage, multi-core Rust parallelism, query optimization, and streaming out-of-core execution without GIL bottleneck. |
| **Homogeneous N-D matrices, linear algebra, ML/tensors** | **NumPy** (`np.ndarray`) | Python nested lists (`[[...]]`), Polars | NumPy executes SIMD-vectorized C/Fortran routines with contiguous memory; ideal for mathematical transforms and coordinate spaces. |
| **FIFO Queue or Sliding Window** | `collections.deque` (`maxlen=K`) | Python `list` (`list.pop(0)`) | `list.pop(0)` is $O(n)$ because all memory slots shift. `deque.popleft()` is $O(1)$ and double-ended. |
| **Membership testing / Deduplication ($O(1)$)** | `set` or `frozenset` | Python `list` (`item in list`) | `item in list` is $O(n)$ linear scan; `item in set` is $O(1)$ average hash-table lookup. |
| **Priority Queue / Streaming Top-$K$ items** | `heapq` (`heappush`, `heappop`) | Sorting the full `list` repeatedly | Sorting a list is $O(n \log n)$; `heapq` maintains min/max-heap in $O(\log n)$ insertion and $O(1)$ min lookup. |
| **Domain Entities & In-Memory Records** | `@dataclass(slots=True, frozen=True)` | Standard `class`, Python `dict` | Eliminates per-instance `__dict__`, cutting memory consumption by ~65% ($48$ bytes vs $152$ bytes per instance). |
| **External API input validation & serialization** | **Pydantic v2** (`BaseModel`) | Manual validation logic, raw dicts | Rust-powered `pydantic-core` gives $5\text{--}10\times$ speedup, type coercion, and JSON schema generation. |

## Knowledge Modules

Load only the modules relevant to the task.

- [Architectural Styles & Layouts](core/architecture-styles.md)
- [Design Patterns & Dependency Injection](core/design-patterns-and-di.md)
- [Data Structures & DataFrames: NumPy vs. Polars](runtime-and-memory/data-structures-and-dataframes.md)
- [Domain Modeling & Immutability](core/domain-modeling.md)
- [Pydantic v2 Architecture & Validation](core/pydantic-and-validation.md)
- [Error Architecture & Resilience](core/error-architecture.md)
- [Memory Safety, Garbage Collection & Optimization](runtime-and-memory/memory-and-gc.md)
- [Closures, Scope Hygiene & Function Traps](runtime-and-memory/closures-and-scope.md)
- [Asyncio, Event Loop Hygiene & Concurrency](concurrency/asyncio-and-multitasking.md)
- [Security Guidelines & Defensive Programming](security/security.md)
- [Testing & Quality Best Practices](testing/best-practices.md)
