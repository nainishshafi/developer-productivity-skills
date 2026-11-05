# Plain Java Guidelines & Best Practices

## 1. Modern Language Features (Java 17 / 21+)

- **Records**: Use records for immutable data carriers and DTOs instead of boilerplate classes.
  ```java
  public record OrderDto(UUID id, BigDecimal amount, OrderStatus status) {}
  ```
- **Pattern Matching & Switch Expressions**: Prefer exhaustive switch expressions over chained `if-else`.
  ```java
  return switch (status) {
      case PENDING -> processOrder(order);
      case COMPLETED, CANCELLED -> noOp();
  };
  ```
- **Sealed Types + Record Patterns (Java 21)**: Model closed hierarchies with `sealed` interfaces; switch over them exhaustively without a `default` branch so the compiler flags missing cases.
  ```java
  sealed interface Shape permits Circle, Square {}
  record Circle(double r) implements Shape {}
  record Square(double side) implements Shape {}

  double area(Shape s) {
      return switch (s) {
          case Circle(var r) -> Math.PI * r * r;
          case Square(var side) -> side * side;
      };
  }
  ```
- **Text Blocks**: Use `"""` for multi-line JSON, SQL, or template strings.
- **`var`**: Use for local variables when the type is obvious from the right-hand side; avoid when it hides meaning.
- **Virtual Threads (Java 21+)**: Prefer virtual threads (`Executors.newVirtualThreadPerTaskExecutor()`) for I/O-bound throughput over heavy thread pools. See [Concurrency Guide](concurrency.md) for pinning and thread models.

## 2. Immutability & Defensive Design

- Make fields `private final` by default.
- Return unmodifiable collections (`List.copyOf(...)`, `Map.of(...)`) to prevent accidental external mutation. See [Collections Guide](collections.md) for data structure selection and performance.
- Avoid returning `null`. Return `Optional<T>` for single optional values or empty collections (`List.of()`).
- Use `Optional` only as a return type — not for fields, parameters, or collection elements. Never call `.get()` without a check; prefer `orElseThrow()`, `map()`, `orElse()`.
- Validate constructor/method arguments early (`Objects.requireNonNull`, compact record constructors).

## 3. Resource & Exception Management

- Always manage I/O streams and database connections using `try-with-resources`.
  ```java
  try (var stream = Files.lines(path)) {
      stream.forEach(System.out::println);
  }
  ```
- Catch specific exceptions; never catch bare `Throwable` or `Exception` unless at global boundary handlers.
- Never swallow exceptions with empty catch blocks. Always log or wrap into custom domain exceptions, preserving the cause (`new DomainException("msg", e)`).
- Prefer unchecked domain exceptions for business errors; reserve checked exceptions for recoverable conditions the caller must handle.
- Restore the interrupt flag when catching `InterruptedException` (`Thread.currentThread().interrupt()`).

## 4. Logging

- Use SLF4J with parameterized messages: `log.info("Order {} placed", id)` — never string concatenation.
- Log an exception once, at the boundary that handles it; pass it as the last argument to keep the stack trace.
- Never log secrets or PII.

## 5. Testing

- JUnit 5 + AssertJ (`assertThat(...)`) + Mockito. Name tests by behavior (`shouldRejectExpiredCoupon`).
- Use `@ParameterizedTest` for input variations instead of copy-pasted tests.
- Test behavior through public APIs; don't mock value objects or the class under test.
- No `Thread.sleep` in tests — use Awaitility or inject a `Clock` for time-dependent logic.

