# React Code Review Checklist

Senior-level review checklist for React (v18 & v19) applications, cross-referencing [`react-developer`](file:///.github/skills/react-developer/SKILL.md).

---

## 1. Component Architecture & Principles

- [ ] **Single Responsibility Principle**:
  - Does the component do one thing well? Components exceeding 200–250 lines should usually be decomposed into focused subcomponents or custom hooks.
- [ ] **Pure Component Behavior**:
  - Are component render bodies pure functions free from side effects (no DOM mutations, network requests, or timer creation during render)?
- [ ] **Prop Drilling vs. Composition**:
  - If props are passed through more than 2–3 intermediary components, is component composition (`children` or slot props) or state stores (Zustand) utilized instead?
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

