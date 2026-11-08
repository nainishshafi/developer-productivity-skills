# Python Code Review Checklist

Staff-level review guidelines and checklist for modern Python (3.11+) applications.

---

## 1. Type Safety & Typing Discipline

- [ ] **Type Annotations**: Are all function signatures, parameters, and return types fully typed (`int`, `str`, `list[str]`, `dict[str, Any]`)?
- [ ] **Nullable Types**: Are nullable values explicitly annotated with `T | None` (or `Optional[T]`) rather than assuming non-null?
- [ ] **Collection Generics**: Are collections using standard generics (`list[T]`, `dict[K, V]`, `set[T]`) rather than deprecated `typing.List` or `typing.Dict`?
- [ ] **Protocols & Duck Typing**: Are structural interfaces defined using `typing.Protocol` rather than rigid ABC hierarchies when multiple unrelated implementations exist?
- [ ] **Any & Type Casts**: Are `Any` and `cast(...)` avoided unless strictly necessary for third-party boundary interop? Flag unvalidated `cast()` as `[P1]`.

---

## 2. Core Idioms & Language Traps

- [ ] **Mutable Default Arguments**: Are function default arguments strictly immutable?
  ```python
  # BAD: Mutable default is shared across calls
  def append_item(item: str, target: list[str] = []) -> list[str]: ...

  # GOOD:
  def append_item(item: str, target: list[str] | None = None) -> list[str]:
      target = target if target is not None else []
  ```
- [ ] **Late Binding in Closures**: Are loop variables captured by value in lambda/closures (`lambda x, i=i: ...`) rather than reference?
- [ ] **Dictionary Lookups**: Are lookups using `.get(key, default)` or guarded with `if key in d:`, avoiding uncaught `KeyError`?
- [ ] **Comprehensions vs. Generators**: Are large transformations using generator expressions `(x for x in ...)` rather than constructing unnecessary intermediate lists `[x for x in ...]`?
- [ ] **String Formatting**: Are f-strings used consistently instead of `%` or `.format()`? (Except logging where lazy evaluation is preferred: `logger.info("msg %s", val)`).

---

## 3. Error Handling & Resilience

- [ ] **Specific Exceptions**: Are exceptions specific (`ValueError`, `KeyError`, custom domain exceptions) rather than bare `except:` or `except Exception:`?
- [ ] **Exception Chaining**: Are re-raised exceptions properly chained using `raise CustomError(...) from err` to preserve stack traces?
- [ ] **Context Managers**: Are all file handles, sockets, database sessions, and locks managed using `with` or `async with`?
- [ ] **Silent Suppression**: Are `try/except: pass` blocks forbidden unless explicitly documented with a rationale? Flag undocumented silent suppression as `[P0]`.

---

## 4. Testing & Code Quality

- [ ] **Test Coverage**: Are happy path, edge cases (empty list, 0, negative values, `None`), and error branches covered in `pytest`?
- [ ] **Fixture Hygiene**: Are fixtures scoped appropriately (`function`, `module`, `session`) without leaking test state?
- [ ] **Mock Verification**: Are mocks authentic AST symbols (`spec=Service`) rather than unconstrained magic mocks?
- [ ] **Linter & Formatter**: Does the code pass `ruff check` and `ruff format` cleanly?

