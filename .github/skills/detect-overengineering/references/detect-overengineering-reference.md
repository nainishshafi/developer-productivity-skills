# Detect Over-Engineering Reference Guide

Comprehensive guide, taxonomy, and refactoring playbook for identifying and dismantling over-engineering, premature abstraction, layer bloat, and accidental complexity in software systems.

---

## 1. Core Principles of Simplicity

Over-engineering occurs when software is designed to solve hypothetical problems that do not yet exist, uses unnecessary layers of indirection, or introduces excessive ceremony where simple, direct code suffices.

### Foundational Laws

1. **YAGNI (You Aren't Gonna Need It)**: Always implement things when you actually need them, never when you just foresee that you might need them.
2. **KISS (Keep It Simple, Stupid)**: Simple code is easier to read, test, debug, and replace than flexible code.
3. **The Rule of Three**: Do not introduce an abstraction until you have duplicated logic in at least three distinct places with identical semantic meaning.
4. **Gall's Law**: A complex system that works is invariably found to have evolved from a simple system that worked. A complex system designed from scratch never works and cannot be patched up to make it work.
5. **Accidental vs. Essential Complexity**:
   - *Essential Complexity*: Inherent to the business problem (e.g., calculating tax laws, cryptographic hashing).
   - *Accidental Complexity*: Introduced by developer choices (e.g., 6 layers of DTOs, single-implementer interfaces, custom dependency injection containers).

---

## 2. Taxonomy of Over-Engineering Smells

### Smell 1: Premature Abstraction & Interface Paranoia

**Definition:** Introducing interfaces, abstract base classes, or generic contracts when there is only one concrete implementation and no realistic prospect of a second.

**Symptoms:**
- Files named `IUserService.ts` and `UserService.ts` (or `UserService.java` and `UserServiceImpl.java`).
- Single-method interfaces or Python `Protocol` classes where a simple callable or concrete function would suffice.
- Generic type explosion: `class BaseHandler<TRequest, TResponse, TContext extends Context<TRequest>>`.
- Abstract Factory classes that only instantiate a single product family.

**Rule of Thumb:**
> If an interface has exactly one implementation and that implementation is not swapped in unit tests via mock injection, delete the interface and use the concrete class directly.

---

### Smell 2: Layer Bloat & Trampoline Indirection

**Definition:** Passing data through multiple structural layers that perform no translation, validation, or business logic—merely forwarding calls.

**Symptoms:**
- Call stack: `Controller` -> `Service` -> `Manager` -> `Engine` -> `Repository` -> `DAO` for a simple database read.
- Trampoline / Pass-Through methods: A method whose sole line is `return this.inner.doSomething(arg1, arg2);`.
- High cyclomatic indirection with low cyclomatic complexity (lots of files jumped through, but each file has a cyclomatic complexity of 1).

**Rule of Thumb:**
> If a layer neither enriches data, handles errors, manages transactions, nor enforces domain rules, collapse it into the caller.

---

### Smell 3: Speculative Generality (YAGNI Extensibility)

**Definition:** Adding parameters, hooks, plugin architectures, or configuration options for "future flexibility" that no current user or system requires.

**Symptoms:**
- Python functions with `*args, **kwargs` or `options: Optional[Dict[str, Any]] = None` where options are never documented or validated.
- Empty hook methods (`def on_before_process(self): pass`) waiting for future subclasses that never materialize.
- Dynamically loaded plugin frameworks for features that have only 1 fixed implementation.
- Configuration flags stored in YAML/JSON for values that have never changed since the repository was initialized.

**Rule of Thumb:**
> Write for today's concrete requirements. When requirements change, refactor with unit tests backing you. Refactoring a simple system is 10x faster than maintaining an over-generalized system.

---

### Smell 4: Design Pattern Overkill (Enterprise Astronautics)

**Definition:** Applying Gang of Four design patterns to trivial logic where simple language constructs (functions, dictionaries, records) are significantly clearer.

**Symptoms:**
- **Builder Pattern** for an immutable object with only 2 or 3 attributes.
- **Strategy Pattern** (3 classes + context + factory) to replace a 2-branch `if/else` statement.
- **Command Pattern** (invoker, command interface, 4 command objects) for a synchronous sequential script.
- **Singleton Pattern** with thread-safe locks in Python or TypeScript where a module-level variable or plain object provides natural singleton behavior.

**Rule of Thumb:**
> If a pattern introduces more than 2x the lines of code compared to a straightforward function or switch expression, it is accidental complexity.

---

### Smell 5: Premature Optimization

**Definition:** Sacrificing code clarity, maintainability, and idioms for micro-optimizations without profiling data demonstrating a bottleneck.

**Symptoms:**
- Custom in-memory caching layers with manual invalidation for datasets containing fewer than 100 items.
- Bitwise masks and manual memory pooling in high-level languages (Python, JS, Java).
- Concurrency constructs (worker pools, async locks, mutexes) introduced for single-threaded CLI tools or low-throughput endpoints.

**Rule of Thumb:**
> Make it work, make it right, make it fast—in that order. Profile before optimizing.

---

### Smell 6: DTO Churn & Anemic Translation

**Definition:** Creating separate classes for the same data structure across adjacent layers and writing tedious mapping functions between them.

**Symptoms:**
- `DatabaseEntity` -> `DomainModel` -> `ServiceDTO` -> `ApiResponseDTO` with identical field names and types.
- 50 lines of boilerplate copying `dto.firstName = entity.firstName` over and over without business transformation.

**Rule of Thumb:**
> Use language records, dataclasses, or plain types. Only introduce a transformation DTO at external system boundaries (API input/output or database boundary).

---

### Smell 7: Exception & Configuration Sprawl

**Definition:** Defining massive exception class hierarchies for every possible edge case or externalizing simple internal logic into dynamic config files.

**Symptoms:**
- 10 custom exception classes (`UserNotFoundException`, `InvalidUserAgeException`, `EmptyUserNameException`) for a 60-line script.
- Complex expression evaluators or mini-DSL engines written to avoid writing 3 lines of standard code.

**Rule of Thumb:**
> Built-in standard exceptions (`ValueError`, `KeyError`, `IllegalArgumentException`, `Error`) with clear error messages are usually better than custom exception hierarchies.

---

## 3. Before & After Refactoring Examples

### Example 1 — Python: Strategy Pattern vs. Function Dictionary

#### Before (Over-Engineered — 65 LOC, 4 classes, 1 interface)
```python
from abc import ABC, abstractmethod
from typing import Dict

class DiscountStrategy(ABC):
    @abstractmethod
    def calculate(self, price: float) -> float:
        pass

class PercentageDiscountStrategy(DiscountStrategy):
    def __init__(self, percent: float):
        self.percent = percent

    def calculate(self, price: float) -> float:
        return price * (1.0 - self.percent / 100.0)

class FixedDiscountStrategy(DiscountStrategy):
    def __init__(self, discount: float):
        self.discount = discount

    def calculate(self, price: float) -> float:
        return max(0.0, price - self.discount)

class DiscountStrategyFactory:
    @staticmethod
    def create(strategy_type: str, value: float) -> DiscountStrategy:
        if strategy_type == "percentage":
            return PercentageDiscountStrategy(value)
        elif strategy_type == "fixed":
            return FixedDiscountStrategy(value)
        raise ValueError(f"Unknown strategy: {strategy_type}")

class PricingService:
    def __init__(self, strategy_factory: DiscountStrategyFactory):
        self.factory = strategy_factory

    def get_final_price(self, price: float, discount_type: str, value: float) -> float:
        strategy = self.factory.create(discount_type, value)
        return strategy.calculate(price)
```

#### After (Clean & Idiomatic — 12 LOC, 0 classes)
```python
def calculate_discounted_price(price: float, discount_type: str, value: float) -> float:
    """Calculate discounted price given a discount type ('percentage' or 'fixed')."""
    if discount_type == "percentage":
        return price * (1.0 - value / 100.0)
    elif discount_type == "fixed":
        return max(0.0, price - value)
    raise ValueError(f"Unknown discount type: {discount_type}")
```
*Result: 81% code reduction, 0 indirection layers, 100% easier to test.*

---

### Example 2 — TypeScript: 1:1 Interface & Builder Overkill

#### Before (Over-Engineered — 52 LOC)
```typescript
interface IUserQueryOptions {
  limit?: number;
  offset?: number;
  status?: string;
}

interface IUserQueryOptionsBuilder {
  withLimit(limit: number): IUserQueryOptionsBuilder;
  withOffset(offset: number): IUserQueryOptionsBuilder;
  withStatus(status: string): IUserQueryOptionsBuilder;
  build(): IUserQueryOptions;
}

export class UserQueryOptionsBuilder implements IUserQueryOptionsBuilder {
  private limit?: number;
  private offset?: number;
  private status?: string;

  withLimit(limit: number): this {
    this.limit = limit;
    return this;
  }
  withOffset(offset: number): this {
    this.offset = offset;
    return this;
  }
  withStatus(status: string): this {
    this.status = status;
    return this;
  }
  build(): IUserQueryOptions {
    return { limit: this.limit, offset: this.offset, status: this.status };
  }
}
```

#### After (Clean & Idiomatic — 6 LOC)
```typescript
export interface UserQueryOptions {
  limit?: number;
  offset?: number;
  status?: string;
}

// In callers: plain object literals provide full type-checking and autocomplete!
// const options: UserQueryOptions = { limit: 10, status: "active" };
```
*Result: 88% code reduction, eliminates 30 lines of boilerplate builder code.*

---

### Example 3 — Java: Pass-Through Layers & Single Impl

#### Before (Over-Engineered — 4 files, 60 LOC)
```java
// UserService.java
public interface UserService {
    UserDto getUser(String id);
}

// UserServiceImpl.java
@Service
public class UserServiceImpl implements UserService {
    private final UserRepository userRepository;
    public UserServiceImpl(UserRepository repo) { this.userRepository = repo; }
    
    @Override
    public UserDto getUser(String id) {
        return userRepository.findById(id);
    }
}

// UserController.java
@RestController
public class UserController {
    private final UserService userService;
    public UserController(UserService service) { this.userService = service; }

    @GetMapping("/users/{id}")
    public UserDto getUser(@PathVariable String id) {
        return userService.getUser(id);
    }
}
```

#### After (Clean & Idiomatic — 1 file, 18 LOC)
```java
@RestController
@RequestMapping("/users")
public class UserController {
    private final UserRepository userRepository;

    public UserController(UserRepository userRepository) {
        this.userRepository = userRepository;
    }

    @GetMapping("/{id}")
    public ResponseEntity<UserDto> getUser(@PathVariable String id) {
        return userRepository.findById(id)
            .map(ResponseEntity::ok)
            .orElseGet(() -> ResponseEntity.notFound().build());
    }
}
```
*Result: Eliminates useless interface and pass-through service layer that did no business logic.*

---

## 4. Decision Trees for Simplicity

### Decision 1: Do I Need an Interface?
```
Do you currently have multiple production implementations?
  ├── YES -> Keep the interface.
  └── NO
       ├── Is it swapped in unit tests, AND impossible to mock concretely?
       │    ├── YES -> Keep interface.
       │    └── NO  -> DELETE INTERFACE. Use concrete class.
```

### Decision 2: Do I Need a Design Pattern?
```
Can the problem be solved with a pure function, dict, or switch?
  ├── YES -> USE THE SIMPLE CONSTRUCT. Avoid patterns.
  └── NO
       ├── Are there >= 3 distinct variations that change independently?
       │    ├── YES -> Apply targeted pattern (Strategy / Factory).
       │    └── NO  -> Use simple conditional branches.
```

### Decision 3: Do I Need a New Layer / DTO?
```
Does this layer translate formats, validate data, or execute business rules?
  ├── YES -> Keep the layer.
  └── NO
       └── Does it merely pass arguments through to the next layer?
            ├── YES -> COLLAPSE LAYER. Call downstream directly.
            └── NO  -> Keep if it enforces a security or transaction boundary.
```

---

## 5. Quantitative Heuristic Scorecard

| Metric | Normal Range | Over-Engineering Warning |
|--------|--------------|--------------------------|
| **Interfaces to Classes Ratio** | 0.0 - 0.4 | > 0.8 (1:1 interface paranoia) |
| **Pass-Through / Trampoline Methods** | 0 | >= 2 methods forwarding calls untouched |
| **Builder Methods per Class** | 0 (or records/kwargs) | >= 4 setter/with chaining methods |
| **Custom Exceptions per 100 LOC** | 0 - 1 | >= 3 custom exception classes |
| **Inheritance Tree Depth** | 1 - 2 | >= 3 base classes |
| **Empty Hook Methods** | 0 | >= 2 no-op placeholder methods |
| **Ceremony to Logic Ratio** | < 0.5 | > 1.5 (more boilerplate than logic) |
