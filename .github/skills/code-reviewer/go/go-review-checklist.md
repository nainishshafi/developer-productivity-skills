# Go (Golang) Code Review Checklist

Senior-level review checklist for modern Go (1.21+) microservices and tooling.

---

## 1. Core Idioms & Project Structure

- [ ] **Accept Interfaces, Return Structs**:
  - Do functions accept narrow interface parameters while concrete constructors return concrete structs (`*Service`)?
- [ ] **Zero Value Usability**:
  - Are structs designed so their zero value is immediately useful without complex initialization (e.g. `sync.Mutex`, `bytes.Buffer`)?
- [ ] **Package Organization**:
  - Is `internal/` used to prevent unauthorized package importation from outside the module?
  - Are package names short, lowercase, and free from underscores or stuttering (`user.UserService` $\to$ `user.Service`)?

---

## 2. Error Handling & Wrapping

- [ ] **Error Wrapping**:
  - Are errors annotated with context using `fmt.Errorf("failed doing x: %w", err)`?
  - Use `%w` to preserve the causal error chain so `errors.Is` and `errors.As` function correctly.
- [ ] **Never Ignore Errors**:
  - Are returned errors checked immediately (`if err != nil { return err }`)?
  - Flag blank identifier error discards (`_ = doSomething()`) as `[P1 - Major]` unless explicitly justified.
- [ ] **Panic Discipline**:
  - Is `panic()` strictly avoided in library or HTTP handler code? Panics should only occur during unrecoverable initialization startup.

---

## 3. Slice, Map & Struct Hygiene

- [ ] **Nil Slices vs. Empty Slices**:
  - Is `var s []string` preferred for zero values (avoids allocation)?
  - Is `s := []string{}` only used when encoding to JSON where `[]` is required instead of `null`?
- [ ] **Pre-allocating Slices & Maps**:
  - When the final count is known in advance, are slices initialized with capacity `make([]T, 0, count)` to eliminate repeated reallocation and copying?
- [ ] **Pointer vs. Value Receiver**:
  - Use pointer receiver `(s *Service)` if the method mutates the struct or if the struct contains synchronization primitives (`sync.Mutex`).
  - Use value receiver `(p Point)` for small, immutable data structures.
  - Maintain consistency across all methods of a given type.
