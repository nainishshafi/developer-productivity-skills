# Functional Programming in Java & Project Design

Functional programming (FP) in modern Java emphasizes **immutability**, **pure functions**, and **data pipelines**, separating business rules from side effects.

---

## 1. Core FP Principles in Java

- **Pure Functions**: A function's output depends solely on its inputs with no side effects (no mutating global state, no direct I/O).
- **Immutability**: Model domain state with `record` and unmodifiable collections (`List.copyOf`).
- **Standard Functional Interfaces (`java.util.function`)**:
  - `Function<T, R>`: Transform `T` into `R`.
  - `Predicate<T>`: Test a condition (boolean).
  - `Supplier<T>`: Factory or lazy evaluation.
  - `Consumer<T>`: Terminal sink (handles side effects).

---

## 2. Project Architecture: "Functional Core, Imperative Shell"

Design your services by isolating business logic into pure transformations and keeping I/O at the boundaries:

```text
HTTP / Event Inbound (Shell - I/O)
       │
       ▼
[ Controller / Entry Point ]
       │
       ▼
[ Pure Domain Logic ] ─── (Pure Functions, Records, Transformations)
       │
       ▼
[ Repository / External Clients ] (Shell - DB / Network I/O)
```

1. **Functional Core**: Business rules, tax calculations, validation, and discounts written as pure functions with zero framework dependencies.
2. **Imperative Shell**: Controllers, database adapters, and external HTTP clients that orchestrate side effects and pass results into the core.

---

## 3. Practical Design Example: Async Pipeline with `CompletableFuture`

`CompletableFuture` embodies functional monadic composition:
- `thenApply` (`map`): Transform a value synchronously.
- `thenCompose` (`flatMap`): Chain another asynchronous computation.
- `thenCombine`: Combine two independent futures.
- `exceptionally`: Pure error recovery.

### Minimal Pipeline Example

```java
public CompletableFuture<InvoiceDto> checkout(UUID orderId) {
    return orderRepository.findOrderAsync(orderId)          // 1. Async I/O
        .thenApply(this::validateOrder)                     // 2. Pure function
        .thenCombine(discountClient.getDiscountAsync(),     // 3. Parallel Async I/O
                     Order::applyDiscount)                  // 4. Pure combination
        .thenCompose(invoiceRepository::saveAsync)          // 5. Async I/O persist
        .exceptionally(this::handleCheckoutFailure);        // 6. Functional recovery
}
```

---

## 4. Best Practices & Anti-Patterns

### Best Practices
- **Compose with method references**: Prefer `thenApply(this::validate)` over verbose lambdas `thenApply(order -> validate(order))`.
- **Name pipeline steps**: If a lambda exceeds two lines, extract it into a named private pure method.
- **Fail fast with types**: Return `Optional<T>` or a domain result type (e.g., a sealed `Result<T>` interface — not in the JDK) instead of throwing checked exceptions inside functional pipelines.
- **Collect & reduce correctly**: Use `Stream.toList()` (unmodifiable) by default; `Collectors.groupingBy` / `toMap` (supply a merge function when keys can collide). Use primitive streams (`mapToInt`, `mapToLong`, `mapToDouble`) for numeric reductions to avoid boxing.
- **Stream Gatherers (Java 24+)**: Use `stream.gather(Gatherers.windowFixed(n))`, `windowSliding(n)`, `scan(...)`, or `mapConcurrent(maxConcurrency, fn)` for custom intermediate operations without collecting into intermediate lists.

### Anti-Patterns to Avoid
- **Side effects inside `.map()` or `.filter()`**: Never update database records, mutate collections, or trigger I/O inside mapping operations.
- **`parallelStream()` by default**: Only for large, CPU-bound, stateless workloads after measuring; it uses the shared common pool and must never do blocking I/O.
- **Reusing a stream**: Streams are single-use; recreate from the source.
- **Runaway pipeline chains**: Avoid single monolithic 50-line stream or future chains. Split into readable, intermediate stages.
- **Throwing checked exceptions**: Avoid methods with `throws Exception` inside functional interfaces; wrap them into unchecked domain exceptions or functional result types.

