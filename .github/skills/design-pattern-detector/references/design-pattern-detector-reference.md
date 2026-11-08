# Design Pattern Detector Reference

Reference guide for the `design-pattern-detector` skill — pattern catalog, detection heuristics, anti-pattern definitions, confidence scoring, per-language extraction notes, and output conventions.

---

## Supported Languages and Parsers

| Language | Extensions | Parse Method | Accuracy |
|----------|-----------|--------------|----------|
| Python | `.py` | `ast` | High — full AST extraction of classes, methods, fields, decorators |
| Java | `.java` | `java-regex` | Medium — regex for class/method/field declarations |
| JavaScript | `.js` `.jsx` | `js-regex` | Medium — regex for class/function/constructor patterns |
| TypeScript | `.ts` `.tsx` | `js-regex` | Medium — same as JS with TS syntax awareness |
| Go | `.go` | `go-regex` | Medium — regex for struct/interface/func declarations |
| C# | `.cs` | `csharp-regex` | Medium — regex for class/method/property declarations |
| Ruby | `.rb` | `regex-fallback` | Low — basic class/def detection only |
| C/C++ | `.c` `.cpp` | `regex-fallback` | Low — basic class/function detection only |
| Rust | `.rs` | `regex-fallback` | Low — basic struct/fn detection only |

---

## Design Pattern Catalog

### 1. Singleton

**Intent:** Ensure a class has exactly one instance and provide a global access point.

**Structural signals:**
- `has_private_constructor` — non-public constructor prevents external instantiation
- `has_static_instance_field` — class stores its own instance at class level
- `has_get_instance_method` — static/class method named `get_instance`, `getInstance`, or `instance`

**Confidence scoring:**
- **HIGH:** all 3 signals present
- **MEDIUM:** 2 of 3 signals
- **LOW:** 1 signal + class-level instance storage visible in source

**Per-language idioms:**

| Language | Private Constructor | Static Instance | Get Instance |
|----------|-------------------|-----------------|-------------|
| Python | `__new__` override or convention | `_instance = None` class var | `get_instance()` classmethod |
| Java | `private ClassName()` | `private static ClassName instance` | `public static getInstance()` |
| C# | `private ClassName()` | `private static ClassName _instance` | `public static Instance` property or `GetInstance()` |
| JS/TS | `private constructor()` (TS) or closure | `static #instance` or `static instance` | `static getInstance()` |
| Go | unexported struct + package-level `var` | `sync.Once` + package variable | Exported `GetInstance()` function |

---

### 2. Factory

**Intent:** Define an interface for creating objects, letting subclasses or methods decide which concrete type to instantiate.

**Structural signals:**
- `has_create_methods` — methods named `create_*`, `build_*`, `make_*`, `new_*`, `from_*`

**Confidence scoring:**
- **HIGH:** create/build methods returning abstract/interface types, multiple creation methods
- **MEDIUM:** create methods returning concrete types with polymorphic usage
- **LOW:** static creation methods without clear type hierarchy, or top-level factory functions

**Variants:** Simple Factory, Factory Method, Abstract Factory

---

### 3. Observer

**Intent:** Define a one-to-many dependency so that when one object changes state, all dependents are notified.

**Structural signals:**
- `has_subscribe_notify` — methods named `subscribe`/`unsubscribe`/`notify`/`emit`/`on`/`off`/`add_listener`/`remove_listener`/`addEventListener`/`dispatch`/`register`/`unregister`

**Confidence scoring:**
- **HIGH:** subscribe + notify + listener collection all present
- **MEDIUM:** event emission pattern (`emit`/`on`) without explicit subscription management
- **LOW:** callback parameter pattern only

**Per-language idioms:**

| Language | Subscribe | Notify | Collection |
|----------|-----------|--------|------------|
| Python | `add_observer()`, `subscribe()` | `notify()`, `emit()` | `self._observers: list` |
| Java | `addObserver()`, `addEventListener()` | `notifyObservers()`, `fireEvent()` | `List<Observer>` field |
| C# | `event EventHandler Changed;` | `Changed?.Invoke()` | Built-in `event` keyword |
| JS/TS | `on()`, `addEventListener()` | `emit()`, `dispatch()` | `this.listeners = new Map()` |
| Go | `Register()`, `Subscribe()` | `Notify()`, `Emit()` | `[]Observer` field |

---

### 4. Strategy

**Intent:** Define a family of interchangeable algorithms, encapsulate each one, and make them interchangeable at runtime.

**Structural signals:**
- `has_delegation_pattern` — constructor stores an interface/abstract parameter and methods delegate to it

**Confidence scoring:**
- **HIGH:** constructor stores interface + methods delegate to the stored strategy object
- **MEDIUM:** constructor accepts callable/function parameter for behavior injection
- **LOW:** method accepts strategy-like parameter without storage

**Key indicator:** A class's constructor accepts an interface or abstract type, stores it in a field, and one or more methods call through that field.

---

### 5. Builder

**Intent:** Separate construction of a complex object from its representation, allowing the same construction process to create different representations.

**Structural signals:**
- `has_fluent_api` — methods that return `self`/`this` (enabling method chaining)
- `has_build_method` — method named `build()`

**Confidence scoring:**
- **HIGH:** fluent setters + `build()` method + many optional parameters
- **MEDIUM:** fluent API without `build()`, or `build()` without fluent setters
- **LOW:** method chaining for a different purpose (not object construction)

---

### 6. Decorator

**Intent:** Attach additional responsibilities to an object dynamically, providing a flexible alternative to subclassing.

**Structural signals:**
- `has_same_type_wrapping` — constructor accepts a parameter of the same base/interface type
- `has_delegation_pattern` — methods delegate to the wrapped object

**Confidence scoring:**
- **HIGH:** wraps same type + delegates all/most methods + adds behavior
- **MEDIUM:** wraps same type + partial delegation
- **LOW:** composition with same interface but unclear delegation

**Note:** Python `@decorator` syntax is a different concept (function decorators) — the GoF Decorator pattern is about wrapping objects of the same interface. The signal looks for constructor-parameter-based wrapping, not `@` syntax.

---

### 7. Repository

**Intent:** Mediate between the domain and data mapping layers using a collection-like interface for accessing domain objects.

**Structural signals:**
- `has_crud_methods` — methods named `get`/`find`/`save`/`delete`/`update`/`create`/`remove`/`insert`/`upsert`/`fetch`/`store`/`put`/`patch`, plus prefixed variants like `findById`, `getAll`, `deleteBy`

**Confidence scoring:**
- **HIGH:** all 4 CRUD groups (read + create + update + delete) present
- **MEDIUM:** 3 of 4 CRUD groups present
- **LOW:** 2 of 4 CRUD groups, or naming hints (e.g., "Repository" in class name)

---

### 8. Command

**Intent:** Encapsulate a request as an object, allowing parameterization of clients with different requests, queuing, logging, and undoable operations.

**Structural signals:**
- `has_execute_undo` — class has an `execute()` method paired with `undo()`, `redo()`, `rollback()`, or `unexecute()`

**Confidence scoring:**
- **HIGH:** `execute()` + `undo()` pair, class encapsulates a single action with state for reversal
- **MEDIUM:** `execute()` present + command-style naming (`*Command`, `*Action`) but no undo method
- **LOW:** `execute()` alone without undo or command-style naming

**Per-language idioms:**

| Language | execute | undo/redo | Note |
|----------|---------|-----------|------|
| Python | `def execute(self)` | `def undo(self)` | Often stored in a list for history |
| Java | `void execute()` | `void undo()` | `Command` interface common |
| C# | `Execute()` | `Undo()` | Often used with ICommand |
| JS/TS | `execute()` | `undo()` | Common in editor/game patterns |
| Go | `Execute()` | `Undo()` | Interface-based |

---

### 9. Template Method

**Intent:** Define the skeleton of an algorithm in a base class, deferring some steps to subclasses without changing the algorithm's structure.

**Structural signals:**
- `has_abstract_template_steps` — abstract/base class with `@abstractmethod` hook methods AND at least one concrete method that provides the algorithm structure

**Confidence scoring:**
- **HIGH:** inherits from ABC + `@abstractmethod` hooks present + concrete non-init methods act as the template
- **MEDIUM:** inherits from ABC/abstract base + mix of abstract and concrete methods (template step unclear)
- **LOW:** class named `Abstract*` or `Base*` with concrete methods but no detected abstract hooks

**Per-language idioms:**

| Language | Abstract base | Abstract hooks | Template method |
|----------|--------------|----------------|----------------|
| Python | `class Foo(ABC)` | `@abstractmethod def step(self)` | concrete `def run(self)` calling `self.step()` |
| Java | `abstract class Foo` | `abstract void step()` | `final void run()` calling `step()` |
| C# | `abstract class Foo` | `abstract void Step()` | `void Run()` calling `Step()` |
| JS/TS | No native abstract; convention-based | Method throws `new Error('abstract')` | Concrete method in base |
| Go | Interface defines hooks; struct implements template | Interface methods | Exported function calling interface |

---

### 10. Facade

**Intent:** Provide a unified, simplified interface to a set of interfaces or sub-modules in a subsystem, hiding complex inter-component orchestration.

**Structural signals:**
- `has_facade_pattern` — module predominantly aggregates and re-exports multiple sub-modules (`export { ... } from '...'`), or a class/object provides a simplified interface delegating to 2 or more distinct subsystem components.

**Confidence scoring:**
- **HIGH:** module or class re-exports or wraps 2+ internal sub-modules/services with a simplified unified API
- **MEDIUM:** class coordinates multiple distinct sub-services with delegation methods
- **LOW:** single re-export or thin wrapper around a single dependency

---

### 11. Dependency Injection (Inversion of Control)

**Intent:** Decouple components by passing dependencies into a class/function (typically via constructor) rather than letting the class instantiate them directly (`new Component()`).

**Structural signals:**
- `has_delegation_pattern` — constructor parameters match internal fields/properties
- Constructor takes interface/protocol types; absence of internal `new ConcreteDependency()` instantiation
- Framework annotations: `@Inject`, `@Autowired`, `@Component`, `@Service` (Java/TS), `[FromKeyedServices]` (C#), `Depends()` (Python)

**Confidence scoring:**
- **HIGH:** Constructor receives 2+ interface/protocol parameters and assigns them to private/final fields; zero direct concrete instantiations
- **MEDIUM:** Single interface dependency injected via constructor or factory function
- **LOW:** Setter or property injection without immutability

**Per-language idioms:**

| Language | Constructor Style | Injection Mechanism | Annotation / Convention |
| :--- | :--- | :--- | :--- |
| **Java** | `public Service(Repo repo)` | Spring IoC, Jakarta CDI | `@Service`, `@RequiredArgsConstructor` |
| **C#** | `public class Service(IRepo repo)` | `Microsoft.Extensions.DI` | Primary constructor, `[FromServices]` |
| **TS/JS** | `constructor(private repo: IRepo)` | NestJS, TSyringe, Pure DI | `@Injectable()`, Composition Root |
| **Python** | `def __init__(self, repo: Protocol)` | FastAPI `Depends`, Pure DI | Structural Subtyping (`typing.Protocol`) |
| **Go** | `func NewService(repo Repo) *Service` | Pure DI, Google Wire | Constructor function passing interface |

---

## Anti-Pattern Catalog

### 1. God Object / God File

**Definition:** A class or source file that has taken on too many responsibilities, violating the Single Responsibility Principle (SRP).

**Detection thresholds:**

| Target | Metric | Warning (MEDIUM) | Severe (HIGH) |
|--------|--------|-------------------|---------------|
| **Class-based** | Method count | >15 | >20 |
| | Field count | >10 | >15 |
| | Total LOC | >300 | >500 |
| **Module / File-based** | Top-level function count | >8 | >12 |
| *(TS, JS, Go, Python)* | Total file LOC | >300 | >500 |
| | Domain cohesion | Spans 2+ distinct responsibilities | Spans 3+ unrelated domains (e.g. process + crypto + CLI + IO) |

---

### 2. Long Method

**Definition:** A method that is too long, making it hard to understand, maintain, and test.

**Detection thresholds:**

| Metric | Warning (MEDIUM) | Severe (HIGH) |
|--------|-------------------|---------------|
| Method LOC | >50 | >80 |

Flagged from `metrics.max_method_loc`. The subagent should identify which specific method(s) exceed the threshold.

---

### 3. Feature Envy

**Definition:** A method that uses another class's data more than its own, suggesting it belongs in the other class.

**Detection:** Cannot be reliably detected by the script — requires the subagent to read the source and count references to external objects vs. `self`/`this` references within a method.

**Confidence scoring:**
- **MEDIUM:** method clearly operates primarily on external object data
- **LOW:** method has some external access patterns

---

## Structural Signal Definitions

| Signal | What It Detects | Used By |
|--------|----------------|---------|
| `has_private_constructor` | Non-public constructor, `__new__` override | Singleton |
| `has_static_instance_field` | Class stores own-type instance at class level | Singleton |
| `has_get_instance_method` | Method named `get_instance` / `getInstance` / `instance` | Singleton |
| `has_create_methods` | Methods named `create_*` / `build_*` / `make_*` / `new_*` / `from_*` | Factory |
| `has_subscribe_notify` | `subscribe`/`notify`/`emit`/`on`/`off`/`add_listener` and variants | Observer |
| `has_fluent_api` | Methods returning `self`/`this` (method chaining) | Builder |
| `has_build_method` | Method named `build()` | Builder |
| `has_crud_methods` | `get`/`find`/`save`/`delete`/`update` and prefixed variants | Repository |
| `has_delegation_pattern` | Constructor stores interface param, methods delegate | Strategy, Decorator |
| `has_same_type_wrapping` | Constructor accepts own base/interface type | Decorator |
| `has_execute_undo` | `execute()` + `undo()`/`redo()`/`rollback()` method pair | Command |
| `has_abstract_template_steps` | Abstract base with `@abstractmethod` hooks + concrete non-init methods | Template Method |
| `has_facade_pattern` | Module re-exports multiple sub-modules (`export ... from`), or class delegates to 2+ distinct subsystems | Facade |

---

## Confidence Scoring Summary

| Level | General Criteria |
|-------|-----------------|
| **HIGH** | >=3 structural signals match + source reading confirms intent |
| **MEDIUM** | 2 signals match, or signals match but source reading is ambiguous |
| **LOW** | 1 signal matches, or pattern inferred from naming/structure only |

The subagent should favor precision over recall — only flag patterns it has strong structural evidence for. When in doubt, downgrade to a lower confidence rather than omitting.

---

## Output Path Convention

Pattern analysis reports are written to `.pattern-analysis/` at the repo root, mirroring the source structure with `.md` extension:

| Source Path | Output Path |
|-------------|-------------|
| `src/api/auth.py` | `.pattern-analysis/src/api/auth.md` |
| `com/example/Auth.java` | `.pattern-analysis/com/example/Auth.md` |
| `internal/db/store.go` | `.pattern-analysis/internal/db/store.md` |
| `components/Button.tsx` | `.pattern-analysis/components/Button.md` |

Repo-wide index: `.pattern-analysis/_index.md`

---

## Staleness Check Logic

```python
stale = not output.exists() or source.stat().st_mtime > output.stat().st_mtime
```

- **Stale** (`true`): output file missing, or source modified after last analysis
- **Fresh** (`false`): output exists and source hasn't changed since last run

Use `--force` to override the staleness check and regenerate.

---

## Script Compatibility Notes

- `extract-patterns.py` uses **Python standard library only** — no pip installs needed
- Python extractor uses `ast.parse` — accurate, handles decorators, type annotations, async
- Java/C#/JS/TS/Go extractors use regex — covers common patterns; complex generics, anonymous classes, and metaprogramming may be incomplete
- For regex-based languages, the subagent should cross-check signals by reading the source file
- Go structs are mapped to the `classes` array with their associated methods (matched by receiver type)
- The `loc` field for methods is only accurate for Python (uses `end_lineno`); regex-based extractors set `loc: 0`

**Exit codes:**
- `0` — successful extraction
- `1` — file not found, unreadable, or missing arguments
