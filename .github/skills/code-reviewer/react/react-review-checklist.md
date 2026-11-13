# React Code Review Checklist

Senior-level review checklist for React (v18 & v19) applications, cross-referencing [`react-developer`](file:///.github/skills/react-developer/SKILL.md) and the full [React Code Review, Functional Programming & Clean Code Audit](file:///.github/skills/react-developer/review-checklist/react-code-review-and-clean-code.md).

---

## 1. Functional Programming & Clean Code Principles ($\text{UI} = f(\text{state})$)

- [ ] **Referential Transparency & Zero In-Place Mutations**:
  - Are component render bodies pure functions free from side effects (no DOM mutations, network requests, or timer creation during render)?
  - Are mutating array methods (`.sort()`, `.reverse()`, `.splice()`, `.push()`) banned in render and state updates in favor of ES2023 immutable methods (`.toSorted()`, `.toReversed()`, `.toSpliced()`, `.with()`)? Flag in-place prop/state mutation as `[P0 - Blocker]`.
- [ ] **Eliminate Procedural `let` Ladders & `for` Loops**:
  - Are mutable `let` branching ladders replaced with `Record<K, V>` lookup maps or exhaustive `switch` helpers over discriminated unions?
  - Are imperative `for` loops inside JSX components extracted into pure, testable selector functions (`filter`, `map`, `Object.groupBy`)?
- [ ] **Functional Core, Imperative Shell**:
  - Are sequential `useEffect` state-mutation chains banned? Derived values compute during render, state transitions live in pure reducers/helpers, and side effects execute explicitly in event handlers (`onClick`, `onSubmit`).
- [ ] **SOLID, Composition & Naming Hygiene**:
  - Single Responsibility Principle: Components exceeding 200–250 lines decompose cleanly into focused subcomponents or custom hooks without pointless micro-component splitting.
  - Open/Closed Composition & Zero "Prop Drilling Hell": Prefer `children`, slot props, or Compound Components over 5+ boolean layout flags (`hasHeader`, `isCompact`). Flag trampoline pass-through props threaded across $\ge 3$ intermediate layers as `[P1 - Major]`; resolve via `children`/slots $\to$ TanStack Query/RSC colocation $\to$ scoped Context $\to$ atomic Zustand selectors.
  - Early Returns & Consistent Naming: Guard loading/empty/error states with early returns; use `on*` for callback props, `handle*` for internal handlers, and `is`/`has`/`can` for booleans.
- [ ] **Key Property Hygiene**:
  - Are list keys unique, stable identifiers (e.g., `item.id`)?
  - Flag using array index as `key` (`key={index}`) on dynamic or re-orderable lists as `[P1 - Major]`.

---

## 2. Forms & Controlled vs. Uncontrolled Components

- [ ] **Form State**:
  - For simple forms, are uncontrolled components with `FormData` / Server Actions preferred to reduce re-renders?
  - For complex validated forms, are schema-backed libraries (React Hook Form + Zod) used?
- [ ] **Input Sanitization**:
  - Is `dangerouslySetInnerHTML` forbidden unless strictly sanitized with DOMPurify? Flag unsanitized raw HTML as `[P0 - Blocker]`.

---

## 3. Hydration & SSR Safety

- [ ] **Browser API Access**:
  - Are browser-only globals (`window`, `localStorage`, `document`) guarded against SSR execution by checking `typeof window !== 'undefined'` or executing inside `useEffect`?
- [ ] **Hydration Mismatches**:
  - Are random IDs, timestamps, or locale formatting deterministic between server render and client hydration?

