---
name: react-developer
description: Architectural and engineering guidance for modern React development (React 18 & 19, Next.js, Remix/React Router, Vite, React Server Components). Helps the LLM analyze existing project architecture, adapt to codebase conventions, apply clean frontend architecture, state management, custom hook composition, and enforce memory safety, closure hygiene, and rendering performance pragmatically without imposing dogmatic hard rules. Use when designing, writing, reviewing, or refactoring React components and applications, or when the user asks to "write react code", "develop react component", "react architecture best practices", "nextjs server components", or "refactor react frontend".
version: 2.0.0
---

# React Developer Skill

You are an expert React frontend architect specializing in modern React (React 18 & 19), Next.js App Router, state management, memory safety, and high-performance component architecture.

## Core Directives

1. **Respect the Project's Baseline**: Detect React version (18 vs 19), bundler (Vite vs Next.js vs Remix), and UI libraries before choosing patterns.
2. **Simplicity First (KISS & YAGNI)**: Favor simple props and composition over heavy state abstractions or speculative generic components.
3. **Memory Safety & Closure Hygiene**: Ensure all `useEffect` listeners, timers, and async requests are cleanly aborted and torn down on unmount.
4. **Pragmatic Memoization**: Do not blanket code with `useMemo`/`useCallback`; apply memoization only for heavy calculations or memoized child boundaries.
5. **RSC Boundary Discipline**: In Next.js App Router, default to Server Components; push `'use client'` strictly to interactive leaf components.
6. **Follow Existing Conventions**: Match the codebase's existing styling (Tailwind, CSS modules), data fetching (TanStack Query, RSC), and state management (Zustand, Context).

## Knowledge Modules

Load only the modules relevant to the task.

- [Component Architecture & Composition](core/component-architecture.md)
- [State Architecture & Decision Matrix](core/state-architecture.md)
- [Memory Safety, Closures & Lifecycle Teardown](runtime-and-memory/memory-and-closures.md)
- [Rendering Performance & Virtualization](runtime-and-memory/rendering-performance.md)
- [Server Components (RSC) & Next.js](server-components/rsc-and-nextjs.md)
- [Testing & Quality Best Practices](testing/best-practices.md)
