# TypeScript Code Review Checklist

Senior-level review checklist for TypeScript codebases.

---

## 1. Type Safety & Strictness

- [ ] **No `any`**: Is `any` completely forbidden? Flag `any` as `[P1 - Major]`.
  - Use `unknown` when input is truly unverified, requiring type guards (`typeof`, `instanceof`, Zod/Valibot) before consumption.
- [ ] **Type Assertions (`as Type`)**: Are forced type casts avoided unless interacting with untyped libraries?
  - Unchecked `as TargetType` circumvents compile-time safety and causes runtime `TypeError`.
- [ ] **Non-Null Assertions (`!`)**: Are exclamation marks (`user!.id`) forbidden in production code unless preceded by an explicit runtime invariant check?
- [ ] **Nullish Coalescing vs. Logical OR**:
  - Is `??` used instead of `||` when default values should only apply to `null` and `undefined` (allowing `0` and `""` to pass)?
- [ ] **Discriminated Unions**: Are complex state representations modeled with discriminated unions (`type State = { status: 'idle' } | { status: 'loading' } | { status: 'success'; data: T }`) rather than optional property bags?

---

## 2. Generics & Utility Types

- [ ] **Generic Constraints**: Are generics properly constrained (`<T extends BaseEntity>`) rather than unconstrained `<T>`?
- [ ] **Readonly Immutability**: Are immutable collections and DTOs marked as `readonly T[]` or `Readonly<T>` to prevent accidental mutation?
- [ ] **Utility Types**: Are standard utility types (`Partial<T>`, `Pick<T, K>`, `Omit<T, K>`, `Record<K, V>`) utilized effectively rather than duplicating interface definitions?

---

## 3. Error Handling & Defensiveness

- [ ] **Unknown Catch Variables**: Are catch blocks typing errors as `unknown` (in TypeScript 4.4+ strict mode)?
  ```typescript
  try {
    await doWork();
  } catch (error: unknown) {
    if (error instanceof DomainError) {
      // handle domain error
    } else {
      throw error;
    }
  }
  ```
- [ ] **Result Pattern vs. Exceptions**: For domain errors, consider returning discriminated result objects (`Result<T, E>`) to make failure states explicit in function signatures.

---

## 4. Linting, Formatting & Testing

- [ ] **ESLint & Prettier**: Does the code conform to strict ESLint configurations (`@typescript-eslint/recommended-type-checked`)?
- [ ] **Test Coverage**: Are unit tests written in Vitest/Jest with high branch coverage?
- [ ] **Mock Legitimacy**: Are test mocks validating against actual interface contracts (e.g. `mock<UserService>()`) rather than untyped objects?

