# Java Code Review Checklist

Senior-level review checklist for modern Java (21+) applications, cross-referencing [`java-developer`](file:///.github/skills/java-developer/SKILL.md).

---

## 1. Modern Java (21+) Idioms & Language Features

- [ ] **Records for DTOs**:
  - Are immutable data-transfer objects defined as Java Records (`public record UserDto(String id, String email)`) instead of boilerplate classes with Lombok `@Data`?
- [ ] **Pattern Matching & Switch Expressions**:
  - Are switch expressions used exhaustively with pattern matching (`switch (shape) { case Circle c -> ...; case Rectangle r -> ...; }`)?
- [ ] **Sealed Classes**:
  - Are restricted domain hierarchies defined using `sealed interface` / `permits` to enforce closed polymorphism?
- [ ] **Text Blocks**:
  - Are multi-line SQL queries, JSON templates, or XML defined using `"""` text blocks rather than string concatenations?

---

## 2. Null Safety & Optional

- [ ] **`Optional` Misuse**:
  - Is `Optional.get()` called without checking `isPresent()`? Flag as `[P1 - Major]`. Use `.orElseThrow()`, `.orElse()`, or `.map()`.
  - Is `Optional` used as a method parameter or class field? (Anti-pattern; `Optional` is intended strictly for return types).
- [ ] **Null Annotations**:
  - Are APIs annotated with `@NonNull` / `@Nullable` (or JSpecify annotations)?

---

## 3. Collections & Streams Hygiene

- [ ] **Immutability by Default**:
  - Are unmodifiable collections created via `List.of()`, `Set.of()`, and `Map.of()` rather than `Arrays.asList()` or mutable `ArrayList`?
- [ ] **Stream Side Effects**:
  - Are Stream operations (`.map()`, `.filter()`) pure and side-effect free? Modifying external state inside streams is prohibited.
- [ ] **Stream Materialization**:
  - Are streams collected with `.toList()` (Java 16+) rather than verbose `.collect(Collectors.toList())`?
- [ ] **Large Datasets**:
  - Are large collections paginated or streamed lazily rather than collected into large heap memory lists?

---

## 4. Exception Handling & Resource Management

- [ ] **Try-with-Resources**:
  - Are all `AutoCloseable` resources (streams, connections, readers) managed with `try-with-resources`?
- [ ] **Catch Specifics**:
  - Are `catch (Exception e)` or `catch (Throwable t)` blocks avoiding swallowing unexpected runtime exceptions?
  - Do rethrown exceptions include the root cause (`throw new ServiceException("msg", e)`)?
