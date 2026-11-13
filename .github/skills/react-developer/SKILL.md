---
name: react-developer
description: Architectural and engineering guidance for modern React development (React 18 & 19, Next.js, Remix/React Router, Vite, React Server Components), React hooks (useState, useReducer, useEffect, useTransition, useDeferredValue, React 19 use, useActionState, useOptimistic, custom hooks), functional programming in React (pure render UI = f(state), immutability, anti-procedural patterns, Functional Core / Imperative Shell), React code review & clean code audits, and React testing (Vitest, React Testing Library, MSW v2, TanStack Query/Zustand harnesses, RSC, vitest-axe). Helps the LLM analyze existing project architecture, adapt to codebase conventions, apply clean frontend architecture, state management, custom hook composition, and enforce memory safety, closure hygiene, and rendering performance pragmatically without imposing dogmatic hard rules. Use when designing, writing, reviewing, testing, or refactoring React components and applications, or when the user asks to "write react code", "develop react component", "react architecture best practices", "nextjs server components", "refactor react frontend", "react hooks", "custom hook patterns", "useeffect best practices", "react 19 hooks", "functional programming react", "procedural vs functional react", "declarative react patterns", "prop drilling", "prop drilling hell", "react code review", "review react code", "react clean code", "react testing", "react testing library", "test react component", or "msw react test".
version: 2.6.0
---

# React Developer Skill

You are an expert React frontend architect specializing in modern React (React 18 & 19), Next.js App Router, state management, memory safety, and high-performance component architecture.

## Guiding Principles & Architectural Heuristics

1. **Context & Baseline Over Dogma**: Detect React version (18 vs 19), meta-framework (Next.js, Remix, Vite SPA), and existing state/styling patterns. Match codebase idioms rather than enforcing a singular architectural paradigm.
2. **KISS & Composition First**: Favor straightforward props and compound component composition over premature generic abstractions or complex state machines.
3. **Lifecycle & Cleanup Hygiene**: Ensure side-effects in `useEffect` clean up after themselves (aborted `AbortController`, cleared intervals, unregistered window listeners) to avoid memory leaks.
4. **Pragmatic Memoization**: Avoid blanket `useMemo` and `useCallback` on primitive calculations; reserve memoization for heavy computations, stable callbacks passed to memoized children, or custom hook outputs.
5. **RSC & Client Boundary Balance**: In Next.js App Router, leverage React Server Components for data fetching and heavy dependencies, pushing `'use client'` down to interactive leaf nodes.
6. **Separation of Server vs Client State**: Treat server data as an asynchronous cache (via TanStack Query or RSC) and client data as ephemeral UI state (via Zustand, Context, or local state).
7. **Functional Core, Declarative UI (Anti-Procedural Discipline)**: Treat components as pure functions of state (`UI = f(state)`). Ban in-place mutations (`sort`/`push`), mutable `let` branching ladders, and procedural `useEffect` chains; isolate side effects strictly to event handlers and external-sync boundaries.

## When to Use Key Features (Agent Decision Matrix)

| Feature / Abstraction | When to Use (Preferred) | When NOT to Use / Alternative | Rationale |
|---|---|---|---|
| **React Server Components (RSC)** | Data fetching, database access, heavy non-interactive rendering, SEO layouts. | Interactive components with event handlers (`onClick`), browser APIs, or React state (`useState`). | Zero client bundle footprint, direct backend resource access, faster First Contentful Paint. |
| **Inversion of Control (`children` & Slots) vs. Prop Drilling Hell** | Layout shells, navbars, sidebars, and cards needing deeply nested domain leaves without coupling middlemen. | Threading trampoline props through 3+ intermediate components, or wrapping the entire app in global Context prematurely. | Eliminates middleman prop coupling and cascading re-renders while keeping layouts domain-agnostic. |
| **`'use client'` Leaf Components** | Interactive UI elements: buttons, dropdowns, modal controls, form inputs. | Entire page roots or wrapping full layouts unnecessarily. | Keeps JavaScript bundle size small by isolating client hydrate boundaries to interactive leaves. |
| **TanStack Query (React Query)** | Remote server data, polling, caching, optimistic updates, pagination. | Pure local UI toggles (modals, theme selection, form drafts — use Zustand or `useState`). | Handles cache invalidation, deduplication, background re-fetching, and loading/error states out of the box. |
| **Zustand** | Cross-component client state, sidebar toggles, audio players, multi-step wizards. | Deeply localized state used in a single component tree (use local `useState` or prop drilling). | Minimal boilerplate, no Context provider hell, zero unnecessary re-renders via atomic selectors. |
| **`useMemo` / `useCallback`** | Expensive CPU transformations (filtering large arrays), stable dependencies for `useEffect` or `React.memo`. | Trivial string concatenations, primitive computations, or handlers passed to native HTML elements (`<button>`). | Overhead of tracking dependency arrays and closure allocations can exceed the cost of re-computation. |
| **`useTransition` / `useDeferredValue`** | Keeping typing/clicks responsive during heavy list filtering, tab switches, or chart updates. | Wrapping controlled `<input value={...}>` updates or debouncing API requests. | Marks expensive renders interruptible so urgent user input never freezes the main thread. |
| **React 19 Hooks (`use`, `useActionState`, `useOptimistic`)** | Progressive async form actions, optimistic UI rollbacks, conditional `use(Context)` / `use(Promise)` with `<Suspense>`. | Simple local toggles or creating un-cached Promises inside render. | Eliminates manual `isSubmitting`/error/rollback boilerplate while integrating natively with `<form>` and Suspense. |
| **Virtualization (`react-virtual`)** | Long lists, tables, or feeds with > 100 items rendered simultaneously. | Small lists (< 50 items) or simple paginated views. | Keeps DOM node counts constant, preventing browser layout thrashing and memory bloat. |

## Over-Engineering Self-Check (Anti-Bloat Guardrail)

Before generating React code, audit your design against these anti-bloat heuristics:

1. **Avoid Micro-Component Splitting**: Do not split a 25-line component into 4 separate files (`ButtonWrapper`, `HeaderContainer`, `LabelText`, `CardFrame`) if they are only rendered together once. Keep local JSX together until reuse or distinct lifecycle concerns demand extraction.
2. **No Premature Global Stores**: Do not reach for Zustand, Redux, or Context API for state that is only shared between two adjacent components or a parent and direct child. Use simple props or state lifting.
3. **Custom Hook Overkill**: A custom hook that merely wraps a single `useState` call adds indirection without value. Write hooks only when bundling multi-step effects, lifecycle subscriptions, or complex state reducers.
4. **Premature Memoization (`useCallback`/`useMemo`)**: Do not wrap every inline function or primitive expression in memoization hooks. The overhead of dependency array comparison and closure allocation often exceeds the render cost of simple elements.
5. **Direct Tool Audit**: For substantial component trees, use [`detect-overengineering`](file:///.github/skills/detect-overengineering/SKILL.md) to inspect component bloat and accidental complexity.

## Knowledge Modules

Load only the modules relevant to the task.

- [Component Architecture & Composition](core/component-architecture.md)
- [Functional Programming Paradigm & Anti-Procedural Patterns](core/functional-programming-and-anti-procedural.md)
- [Hooks Architecture, React 19 Hooks & Custom Hook Patterns](core/hooks-architecture-and-patterns.md)
- [State Architecture & Decision Matrix](core/state-architecture.md)
- [Global Stores with Zustand](state-management/global-stores-zustand.md)
- [Server State & Cache Stores (TanStack Query)](state-management/server-state-tanstack-query.md)
- [Redux Toolkit & Context Boundaries](state-management/redux-toolkit-and-context.md)
- [Memory Safety, Closures & Lifecycle Teardown](runtime-and-memory/memory-and-closures.md)
- [Rendering Performance & Virtualization](runtime-and-memory/rendering-performance.md)
- [Server Components (RSC) & Next.js](server-components/rsc-and-nextjs.md)
- [Testing Strategy, Trophy & Best Practices](testing/best-practices.md)
- [Component, State (Query/Zustand), React 19 & RSC Testing Patterns](testing/component-state-and-rsc-testing.md)
- [React Code Review, Functional Programming & Clean Code Audit](review-checklist/react-code-review-and-clean-code.md)
