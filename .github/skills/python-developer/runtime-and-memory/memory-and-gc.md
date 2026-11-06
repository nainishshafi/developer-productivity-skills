# Python Memory Safety, Garbage Collection & Optimization

Prevent memory leaks, manage reference cycles, and optimize high-throughput memory usage in CPython runtimes.

---

## 1. Circular References & The Garbage Collector

CPython uses reference counting as its primary memory management mechanism, supplemented by a cyclic garbage collector (gc) to detect cycles.
- When two objects reference each other (`parent.child = child; child.parent = parent`), their reference count never drops to zero.
- They remain in memory until the cyclic GC runs (which can take a significant time or cause GC pause spikes under heavy load).
- If objects in a cycle define a legacy `__del__` method, CPython cannot determine a safe destruction order, potentially leaking them permanently.

### Breaking Cycles with `weakref`
```python
# ✅ BEST PRACTICE: Parent-child relationship without circular reference memory leak
import weakref

class Node:
    def __init__(self, name: str) -> None:
        self.name = name
        self.children: list[Node] = []
        self._parent: weakref.ReferenceType[Node] | None = None

    def add_child(self, child: "Node") -> None:
        child._parent = weakref.ref(self)
        self.children.append(child)

    @property
    def parent(self) -> "Node | None":
        return self._parent() if self._parent else None
```

---

## 2. Unbounded Caching (`lru_cache` and Global Dictionaries)

Using `@functools.lru_cache(maxsize=None)` creates an infinite in-memory cache that will eventually trigger an Out of Memory (OOM) kill under continuous production load.

```python
# ❌ ANTI-PATTERN: Cache grows without bound
from functools import lru_cache

@lru_cache(maxsize=None)
def get_user_profile(user_id: str):
    ...

# ✅ BEST PRACTICE: Explicit maxsize bound and clearable during teardown
@lru_cache(maxsize=2048)
def get_user_profile(user_id: str):
    ...
```

---

## 3. Generators vs Eager List Materialization

Reading millions of database rows, large CSVs, or log files into a Python list in memory consumes gigabytes of heap RAM.

```python
# ❌ ANTI-PATTERN: Reading 10 million rows into a list in RAM consumes gigabytes
def fetch_all_logs() -> list[dict]:
    return [row for row in db.execute("SELECT * FROM audit_logs")]

# ✅ BEST PRACTICE: Generator stream yields row by row with minimal constant memory
from typing import Iterator

def stream_audit_logs() -> Iterator[dict]:
    for row in db.execute_streaming("SELECT * FROM audit_logs"):
        yield row
```

---

## 4. Drastic Memory Reduction with `__slots__`

For classes instantiated millions of times (e.g. data points, token streams, ledger rows), defining `__slots__` saves 40–60% of memory per instance by eliminating `__dict__`:

```python
class Measurement:
    __slots__ = ("timestamp", "sensor_id", "value")

    def __init__(self, timestamp: float, sensor_id: str, value: float) -> None:
        self.timestamp = timestamp
        self.sensor_id = sensor_id
        self.value = value
```
*(Or use `@dataclass(slots=True)` which automatically builds `__slots__` for you).*

