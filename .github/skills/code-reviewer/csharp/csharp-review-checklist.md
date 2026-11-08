# C# (.NET) Code Review Checklist

Senior-level review checklist for modern C# (12+) and .NET (8/9) applications, cross-referencing [`csharp-developer`](file:///.github/skills/csharp-developer/SKILL.md).

---

## 1. Modern C# Language Idioms

- [ ] **Nullable Reference Types (NRT)**:
  - Is `#nullable enable` active? Are nullable types explicitly annotated (`string?`)?
  - Are null-forgiving operators (`!`) avoided unless justified by a runtime invariant check?
- [ ] **Record Types for Immutability**:
  - Are DTOs, events, and value objects defined as `public record class` or `public readonly record struct` with init-only properties?
- [ ] **Primary Constructors**:
  - Are primary constructors used on classes and records to reduce constructor boilerplate?
- [ ] **Pattern Matching**:
  - Are complex conditional branches modeled using switch expressions and property patterns (`user is { IsActive: true, Role: "Admin" }`)?

---

## 2. Async / Await Discipline

- [ ] **No `async void`**:
  - Are all async methods returning `Task` or `Task<T>`? Flag `async void` as `[P0 - Blocker]` (except top-level UI event handlers in WPF/MAUI).
  - Uncaught exceptions in `async void` crash the entire process.
- [ ] **`ValueTask<T>` vs. `Task<T>`**:
  - Is `ValueTask<T>` used when a method frequently completes synchronously (e.g. from an in-memory cache) to eliminate heap allocations?
- [ ] **`ConfigureAwait(false)` in Libraries**:
  - If developing reusable class libraries, is `.ConfigureAwait(false)` used to prevent synchronization context deadlocks?

---

## 3. LINQ & Collection Hygiene

- [ ] **Multiple Enumeration of `IEnumerable<T>`**:
  - Is an `IEnumerable<T>` iterated multiple times without materializing with `.ToList()` or `.ToArray()`?
  - Flag multiple enumeration as `[P1 - Major]` when the source is an external query or heavy generator.
- [ ] **Any() vs. Count()**:
  - Is `.Any()` used to test for existence rather than `.Count() > 0`?
- [ ] **Collection Expressions**:
  - Are modern collection expressions `[1, 2, 3]` used consistently?
