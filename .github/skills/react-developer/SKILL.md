---
name: react-developer
description: Architectural and engineering guidance for modern React development (React 18 & 19, Next.js, Remix/React Router, Vite, React Server Components). Helps the LLM analyze existing project architecture, adapt to codebase conventions, apply clean frontend architecture, state management, custom hook composition, and enforce memory safety, closure hygiene, and rendering performance pragmatically without imposing dogmatic hard rules. Use when designing, writing, reviewing, or refactoring React components and applications, or when the user asks to "write react code", "develop react component", "react architecture best practices", "nextjs server components", or "refactor react frontend".
version: 2.1.0
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

## When to Use Key Features (Agent Decision Matrix)

| Feature / Abstraction | When to Use (Preferred) | When NOT to Use / Alternative | Rationale |
|---|---|---|---|
| **React Server Components (RSC)** | Data fetching, database access, heavy non-interactive rendering, SEO layouts. | Interactive components with event handlers (`onClick`), browser APIs, or React state (`useState`). | Zero client bundle footprint, direct backend resource access, faster First Contentful Paint. |
| **`'use client'` Leaf Components** | Interactive UI elements: buttons, dropdowns, modal controls, form inputs. | Entire page roots or wrapping full layouts unnecessarily. | Keeps JavaScript bundle size small by isolating client hydrate boundaries to interactive leaves. |
| **TanStack Query (React Query)** | Remote server data, polling, caching, optimistic updates, pagination. | Pure local UI toggles (modals, theme selection, form drafts — use Zustand or `useState`). | Handles cache invalidation, deduplication, background re-fetching, and loading/error states out of the box. |
| **Zustand** | Cross-component client state, sidebar toggles, audio players, multi-step wizards. | Deeply localized state used in a single component tree (use local `useState` or prop drilling). | Minimal boilerplate, no Context provider hell, zero unnecessary re-renders via atomic selectors. |
| **`useMemo` / `useCallback`** | Expensive CPU transformations (filtering large arrays), stable dependencies for `useEffect` or `React.memo`. | Trivial string concatenations, primitive computations, or handlers passed to native HTML elements (`<button>`). | Overhead of tracking dependency arrays and closure allocations can exceed the cost of re-computation. |
| **Virtualization (`react-virtual`)** | Long lists, tables, or feeds with > 100 items rendered simultaneously. | Small lists (< 50 items) or simple paginated views. | Keeps DOM node counts constant, preventing browser layout thrashing and memory bloat. |

## Knowledge Modules

Load only the modules relevant to the task.

- [Component Architecture & Composition](core/component-architecture.md)
- [State Architecture & Decision Matrix](core/state-architecture.md)
- [Global Stores with Zustand](state-management/global-stores-zustand.md)
- [Server State & Cache Stores (TanStack Query)](state-management/server-state-tanstack-query.md)
- [Redux Toolkit & Context Boundaries](state-management/redux-toolkit-and-context.md)
- [Memory Safety, Closures & Lifecycle Teardown](runtime-and-memory/memory-and-closures.md)
- [Rendering Performance & Virtualization](runtime-and-memory/rendering-performance.md)
- [Server Components (RSC) & Next.js](server-components/rsc-and-nextjs.md)
- [Testing & Quality Best Practices](testing/best-practices.md)
