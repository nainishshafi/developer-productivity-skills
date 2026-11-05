# Modern Java Design Patterns

Apply patterns pragmatically without unnecessary boilerplate. Introduce a pattern only when it removes real complexity — not in anticipation of it.

## 1. Creational Patterns

- **Builder Pattern**: For objects with many optional parameters. Use `@Builder` (Lombok) or static inner builder class.
- **Factory Method**: Prefer static factory methods over overloaded constructors to give meaningful names:
  ```java
  public static User ofGuest() { ... }
  public static User ofRegistered(UUID id, String email) { ... }
  ```
- **Singleton**: Prefer dependency injection frameworks or single-element `enum` types for singletons over double-checked locking.

## 2. Structural Patterns

- **Adapter**: Translate third-party APIs or legacy data structures to internal domain boundaries.
- **Decorator / Wrapper**: Extend functionality dynamically without modifying original classes (e.g., cached or logged repository wrappers).
- **Facade**: Provide a unified, simple interface to a complex subsystem.
- **Composite**: Treat individual objects and groups uniformly via a shared interface (e.g., tree structures, composite validators).

## 3. Behavioral Patterns

- **Strategy Pattern**: Replace large `if-else` branching with functional interfaces or polymorphism:
  ```java
  public interface PaymentStrategy {
      PaymentResult pay(BigDecimal amount);
  }
  ```
  In Spring, inject all implementations as `Map<String, PaymentStrategy>` or `List<PaymentStrategy>` and select by key — no `switch` needed.
- **Template Method**: Abstract common workflow execution in a base class while letting subclasses override specific steps. Prefer composition (passing a lambda) when only one step varies.
- **Observer / Event-Driven**: Decouple components using domain events or reactive publishers.
- **Visitor → Sealed Types**: For operations over a closed hierarchy, prefer `sealed` interfaces + pattern-matching `switch` over the classic Visitor.

