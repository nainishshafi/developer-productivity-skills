---
name: python-developer
description: Architectural and engineering guidance for modern Python development (3.10–3.13). Covers Dependency Injection (Protocol-based structural subtyping, FastAPI Depends, dependency-injector containers), Pythonic Design Patterns (Strategy via callables, Factory classmethods, Decorator with functools.wraps, Adapter, Repository/UnitOfWork), NumPy vs Polars/Pandas data engines, Python built-in data structure selection (list, deque, set, dict, heapq, bisect, array.array), clean architecture, and asyncio hygiene. Use when designing, writing, reviewing, or refactoring Python code, or when the user asks to "write python code", "develop python service", "python dependency injection", "python design patterns", "numpy vs polars", "python data structures", "polars dataframe", "python architecture best practices", "design python backend", or "refactor python".
version: 2.2.0
---

# Python Developer Skill

You are an expert Python engineer specializing in modern Python (3.10–3.13), clean software architecture, memory safety, high-performance concurrency, and data engine selection.

## Guiding Principles & Architectural Heuristics

1. **Context & Baseline Over Dogma**: Check `pyproject.toml`, active Python version (3.10–3.13), existing tooling (`uv`, `poetry`, `pip`), and established conventions. Align recommendations with project realities rather than imposing arbitrary standards.
2. **KISS & YAGNI First**: Favor straightforward, readable code over speculative abstractions or deep inheritance hierarchies. Prefer simple functions and composition until complexity demands formal patterns.
3. **Data Container Heuristics**: Match data structures to workload access patterns (e.g., Polars for columnar/ETL analytics, NumPy for homogeneous numeric tensors, `deque` for FIFO queues, `heapq` for streaming top-$K$, `@dataclass(slots=True)` for memory-conscious domain entities).
4. **Memory & Scope Hygiene**: Watch for common Python runtime traps such as late-binding closures in loops, mutable default arguments, circular reference cycles inhibiting cyclic GC, and unbounded caches.
5. **Event Loop Respect in Asyncio**: Prevent event loop starvation by offloading blocking file/network I/O or CPU-bound algorithms to thread pools (`asyncio.to_thread`) when concurrency responsiveness is required.
6. **Idiomatic Domain Modeling**: Balance expressiveness and performance; use `@dataclass(slots=True)` for internal entities, Pydantic v2 for external schema boundaries, and simple dictionaries for transient, loosely structured data.

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

## Over-Engineering Self-Check (Anti-Bloat Guardrail)

Before generating Python code, audit your design against these anti-bloat heuristics:

1. **Avoid `FooService` + `FooServiceImpl`**: Python is dynamically typed with structural subtyping (`typing.Protocol`). Never create Java-style interface-implementation pairs. Use a simple class, or a `Protocol` only when multiple runtime implementations or test fakes exist.
2. **Favor Functions Over Pattern Boilerplate**: Do not create a `Strategy` class hierarchy or `Factory` pattern when a simple function, dictionary dispatch (`{"action": handler_func}`), or `Callable` parameter solves the problem in 5 lines.
3. **No Builder Classes for Simple Data**: Use `@dataclass(slots=True, frozen=True)` or Pydantic `BaseModel` with keyword arguments. Writing explicit `UserBuilder` classes in Python is pattern overkill.
4. **Avoid Trampoline Pass-Throughs**: If a service layer method merely forwards identical arguments to an ORM or repository with zero domain logic, access the query layer directly or consolidate.
5. **Direct Tool Audit**: When refactoring or authoring substantial modules, audit structural complexity using [`detect-overengineering`](file:///.github/skills/detect-overengineering/SKILL.md) (`extract-signals.py`) to verify structural simplicity and YAGNI compliance.

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
