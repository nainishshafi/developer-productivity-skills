# Python Closures, Scope Hygiene & Function Traps

Prevent common closure bugs, scope retention, and mutable state traps in Python functions.

---

## 1. Late-Binding Closure Bug in Loops

In Python, closures bind variables by name (reference), not by value. When creating functions or lambdas in a loop, all closures look up the variable when called, resulting in all instances evaluating to the *final* value of the loop.

```python
# ❌ ANTI-PATTERN: Late-binding closure captures loop variable reference
# All functions return 4 when invoked!
handlers = [lambda: i for i in range(5)]
print([h() for h in handlers])  # [4, 4, 4, 4, 4]

# ✅ BEST PRACTICE 1: Capture value at definition time using default parameter
handlers = [lambda i=i: i for i in range(5)]
print([h() for h in handlers])  # [0, 1, 2, 3, 4]

# ✅ BEST PRACTICE 2: Use functools.partial
from functools import partial

def identify(val: int) -> int:
    return val

handlers = [partial(identify, i) for i in range(5)]
```

---

## 2. Mutable Default Arguments Trap

Default arguments in Python functions are evaluated **once at module import / function definition time**, not each time the function is called. Mutating a default argument permanently leaks state across all callers of that function.

```python
# ❌ ANTI-PATTERN: Mutable default list shared across all calls
def append_entry(entry: str, log: list[str] = []) -> list[str]:
    log.append(entry)
    return log

print(append_entry("first"))   # ["first"]
print(append_entry("second"))  # ["first", "second"] -> Memory & state pollution!

# ✅ BEST PRACTICE: Use None as default and instantiate internally
def append_entry(entry: str, log: list[str] | None = None) -> list[str]:
    target = log if log is not None else []
    target.append(entry)
    return target
```

---

## 3. Accidental Scope Retention in Decorators

Decorators create closures. If a decorator captures a large object from an outer function scope, that object is kept alive for the entire lifespan of the decorated function.

```python
# ❌ ANTI-PATTERN: Decorator closure retains large configuration payload
def with_audit(large_context: ContextWithBuffers):
    def decorator(fn):
        def wrapper(*args, **kwargs):
            # large_context is retained forever in the wrapper's __closure__!
            logger.info("Auditing action: %s", large_context.action_name)
            return fn(*args, **kwargs)
        return wrapper
    return decorator

# ✅ BEST PRACTICE: Extract only the needed string or primitive before closing over
def with_audit(large_context: ContextWithBuffers):
    action_name = large_context.action_name  # Extract primitive
    def decorator(fn):
        def wrapper(*args, **kwargs):
            logger.info("Auditing action: %s", action_name)
            return fn(*args, **kwargs)
        return wrapper
    return decorator
```

