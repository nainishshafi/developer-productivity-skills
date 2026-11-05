# DRY, KISS & SOLID in Java

## 1. DRY (Don't Repeat Yourself)
- Extract common algorithms or validation logic into pure utility functions or shared domain components.
- Do not duplicate data contracts across services; centralize shared types or use generic specifications where appropriate.
- *Caution*: Do not force DRY on unrelated code that merely looks similar by coincidence.

## 2. KISS (Keep It Simple, Stupid)
- Write code for humans first. Avoid obscure bitwise tricks, excessive reflection, or over-nested streams.
- If a simple `for-each` loop is clearer than a multi-stage stream pipeline, prefer the simple loop.
- Avoid premature optimization. Write clean, readable code; profile before optimizing.

## 3. SOLID Principles

- **S - Single Responsibility Principle (SRP)**:
  - Each class must have only one reason to change.
  - Separate business rules from persistence, serialization, and presentation.

- **O - Open/Closed Principle (OCP)**:
  - Design classes to be open for extension, closed for modification.
  - Use interfaces or strategy patterns to introduce new behavior without mutating existing tested classes.

- **L - Liskov Substitution Principle (LSP)**:
  - Subtypes must be substitutable for their base types without altering program correctness.
  - Avoid throwing `UnsupportedOperationException` in interface implementations.

- **I - Interface Segregation Principle (ISP)**:
  - Prefer small, focused interfaces over large "god" interfaces.
  - Clients should not be forced to depend on methods they do not use.

- **D - Dependency Inversion Principle (DIP)**:
  - High-level modules should depend on abstractions (interfaces), not concrete implementations.
  - Supply dependencies via constructors, never instantiate dependencies inside domain services directly (`new ServiceImpl()`).

