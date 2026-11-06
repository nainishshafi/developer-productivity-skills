# React Developer Architectural Reference Guide

Deep-dive architectural patterns, trade-off matrices, state management decision trees, and reference implementations for modern React codebases.

---

## 1. Architectural Style Comparison Matrix

| Architecture Style | Ideal When | Drawbacks / Risks | Primary Building Blocks |
|---|---|---|---|
| **Feature-Sliced / Modular** | Mid-to-large applications, multi-team codebases, domain-rich applications. | Potential risk of over-fragmentation for trivial screens; requires discipline on inter-feature imports. | `src/features/<feature>/` (`components/`, `hooks/`, `api/`, `types/`, `index.ts`). |
| **Layered / Type-Based** | Small-to-medium SPAs, early-stage MVPs, internal admin tooling. | Can become unmanageable as `components/` and `hooks/` directories swell with hundreds of files. | `src/components/`, `src/hooks/`, `src/services/`, `src/pages/`, `src/types/`. |
| **Fullstack RSC / App Router** | Content-heavy platforms, SEO-critical apps, high-performance dashboards with server data access. | Mental model shift regarding server vs client execution boundaries; hydration caveats; vendor lock-in. | `app/(routes)/`, `components/ui/`, `actions/`, Server Components, Client Components (`'use client'`). |
| **Micro-Frontends / Monorepo** | Enterprise organizations where independent sub-teams deploy parts of the app independently. | Complex orchestration, bundler federation overhead, version mismatches, duplicated bundles. | Turborepo / Nx, Module Federation, standalone packages (`@org/ui`, `@org/feature-billing`). |

---

## 2. State Management Decision Matrix

```
Is the state originating from a remote server (API, DB)?
  ├── YES ──> Use Server State:
  │             - TanStack Query (React Query)
  │             - SWR
  │             - React Server Components + Next.js fetch cache
  │
  └── NO ───> Is it needed across many unrelated routes or screens?
                ├── YES ──> Use Global Client State:
                │             - Zustand (recommended for general global state)
                │             - Jotai / Recoil (atomic state for fine-grained dependency graphs)
                │             - Redux Toolkit (legacy compatibility or highly formalized event architectures)
                │
                └── NO ───> Does it represent URL params / search / filters?
                              ├── YES ──> Use URL State:
                              │             - nuqs / useSearchParams
                              │             - Router state (TanStack Router / React Router)
                              │
                              └── NO ───> Is it used within a component subtree?
                                            ├── YES ──> Use React Context + useState / useReducer
                                            └── NO ───> Use Local State: useState / useReducer
```

### Lightweight Global Store Example (Zustand)
```typescript
// shared/stores/useCartStore.ts
import { create } from 'zustand';
import { devtools, persist } from 'zustand/middleware';

export interface CartItem {
  id: string;
  name: string;
  price: number;
  quantity: number;
}

interface CartState {
  items: CartItem[];
  addItem: (item: Omit<CartItem, 'quantity'>) => void;
  removeItem: (id: string) => void;
  clearCart: () => void;
}

export const useCartStore = create<CartState>()(
  devtools(
    persist(
      (set) => ({
        items: [],
        addItem: (item) =>
          set((state) => {
            const existing = state.items.find((i) => i.id === item.id);
            if (existing) {
              return {
                items: state.items.map((i) =>
                  i.id === item.id ? { ...i, quantity: i.quantity + 1 } : i
                ),
              };
            }
            return { items: [...state.items, { ...item, quantity: 1 }] };
          }),
        removeItem: (id) =>
          set((state) => ({ items: state.items.filter((i) => i.id !== id) })),
        clearCart: () => set({ items: [] }),
      }),
      { name: 'cart-storage' }
    )
  )
);
```

---

## 3. Server Components (RSC) vs Client Components

### Decision Guide
| Requirement | Server Component (Default) | Client Component (`'use client'`) |
|---|:---:|:---:|
| Fetch data from DB or backend directly | ✅ | ❌ |
| Keep sensitive tokens / API keys secure on server | ✅ | ❌ |
| Reduce client JavaScript bundle size | ✅ | ❌ |
| Use `useState`, `useReducer`, or `useEffect` | ❌ | ✅ |
| Attach event listeners (`onClick`, `onChange`, `onSubmit`) | ❌ | ✅ |
| Access browser-only APIs (`localStorage`, `window`, `navigator`) | ❌ | ✅ |
| Use client-only custom hooks | ❌ | ✅ |

### Pattern: Composition Across the Server/Client Boundary
Pass server-rendered content as `children` into a client container so client state does not force children to re-render or become client-side bundles:

```tsx
// app/components/CollapsibleContainer.tsx ('use client')
'use client';

import { useState, type ReactNode } from 'react';

export function CollapsibleContainer({
  title,
  children,
}: {
  title: string;
  children: ReactNode;
}) {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <div className="border rounded-md p-4">
      <button onClick={() => setIsOpen((prev) => !prev)} className="font-semibold">
        {title} {isOpen ? '▲' : '▼'}
      </button>
      {isOpen && <div className="mt-4">{children}</div>}
    </div>
  );
}

// app/dashboard/page.tsx (Server Component)
import { CollapsibleContainer } from '@/components/CollapsibleContainer';
import { db } from '@/lib/db';

export default async function DashboardPage() {
  // Direct server DB call - zero bundle footprint on client
  const serverMetrics = await db.metrics.findMany();

  return (
    <main>
      <h1>Server-Rendered Dashboard</h1>
      <CollapsibleContainer title="Show Advanced Analytics">
        {/* Rendered on server, passed as children into client container */}
        <AnalyticsTable data={serverMetrics} />
      </CollapsibleContainer>
    </main>
  );
}
```

---

## 4. Modern React 19 Patterns

### A. Server Action with Optimistic Updates (`useOptimistic`)
```tsx
'use client';

import { useOptimistic, useTransition } from 'react';
import { updateTodoAction } from '@/actions/todoActions';

interface Todo {
  id: string;
  text: string;
  completed: boolean;
}

export function TodoItem({ todo }: { todo: Todo }) {
  const [isPending, startTransition] = useTransition();
  const [optimisticTodo, setOptimisticTodo] = useOptimistic(
    todo,
    (state, update: Partial<Todo>) => ({ ...state, ...update })
  );

  const handleToggle = () => {
    const nextCompleted = !optimisticTodo.completed;
    startTransition(async () => {
      setOptimisticTodo({ completed: nextCompleted });
      await updateTodoAction(optimisticTodo.id, { completed: nextCompleted });
    });
  };

  return (
    <li className={`flex items-center gap-2 ${optimisticTodo.completed ? 'line-through text-gray-400' : ''}`}>
      <input
        type="checkbox"
        checked={optimisticTodo.completed}
        disabled={isPending}
        onChange={handleToggle}
      />
      <span>{optimisticTodo.text}</span>
    </li>
  );
}
```

### B. Form Action Handling with `useActionState` (React 19)
```tsx
'use client';

import { useActionState } from 'react';
import { createUserAction, type FormState } from '@/actions/userActions';

const initialState: FormState = { success: false, errors: {} };

export function UserCreationForm() {
  const [state, formAction, isPending] = useActionState(createUserAction, initialState);

  return (
    <form action={formAction} className="space-y-4 max-w-sm">
      <div>
        <label htmlFor="email" className="block text-sm font-medium">Email</label>
        <input id="email" name="email" type="email" required className="border p-2 w-full rounded" />
        {state.errors?.email && <p className="text-red-500 text-xs mt-1">{state.errors.email}</p>}
      </div>

      <button type="submit" disabled={isPending} className="bg-blue-600 text-white px-4 py-2 rounded">
        {isPending ? 'Creating...' : 'Create Account'}
      </button>

      {state.success && <p className="text-green-600 text-sm">Account created successfully!</p>}
    </form>
  );
}
```

---

## 5. Custom Hook Design Patterns

### Resilient Event Listener Hook with Proper Cleanup
```typescript
// shared/hooks/useEventListener.ts
import { useEffect, useRef } from 'react';

export function useEventListener<K extends keyof WindowEventMap>(
  eventName: K,
  handler: (event: WindowEventMap[K]) => void,
  element: Window | HTMLElement | null = typeof window !== 'undefined' ? window : null
) {
  // Use savedHandler ref to ensure latest handler is called without re-subscribing
  const savedHandler = useRef(handler);

  useEffect(() => {
    savedHandler.current = handler;
  }, [handler]);

  useEffect(() => {
    if (!element || !element.addEventListener) return;

    const eventListener = (event: Event) => savedHandler.current(event as WindowEventMap[K]);
    element.addEventListener(eventName, eventListener);

    return () => {
      element.removeEventListener(eventName, eventListener);
    };
  }, [eventName, element]);
}
```

### Debounced Value Hook
```typescript
// shared/hooks/useDebounce.ts
import { useState, useEffect } from 'react';

export function useDebounce<T>(value: T, delayMs: number = 300): T {
  const [debouncedValue, setDebouncedValue] = useState<T>(value);

  useEffect(() => {
    const timer = setTimeout(() => setDebouncedValue(value), delayMs);
    return () => clearTimeout(timer);
  }, [value, delayMs]);

  return debouncedValue;
}
```

---

## 6. Testing Patterns with React Testing Library

Prioritize testing user behavior through accessible queries (`getByRole`, `findByRole`) over implementation details or test IDs:

```tsx
// features/authentication/components/LoginForm.test.tsx
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi } from 'vitest';
import { LoginForm } from './LoginForm';

describe('<LoginForm />', () => {
  it('submits valid credentials and triggers onLoginSuccess', async () => {
    const user = userEvent.setup();
    const handleSuccess = vi.fn();

    render(<LoginForm onLoginSuccess={handleSuccess} />);

    const emailInput = screen.getByRole('textbox', { name: /email/i });
    const passwordInput = screen.getByLabelText(/password/i);
    const submitBtn = screen.getByRole('button', { name: /sign in/i });

    await user.type(emailInput, 'developer@example.com');
    await user.type(passwordInput, 'Secret123!');
    await user.click(submitBtn);

    expect(handleSuccess).toHaveBeenCalledWith({
      email: 'developer@example.com',
      password: 'Secret123!',
    });
  });

  it('displays validation errors when fields are empty', async () => {
    const user = userEvent.setup();
    render(<LoginForm onLoginSuccess={vi.fn()} />);

    const submitBtn = screen.getByRole('button', { name: /sign in/i });
    await user.click(submitBtn);

    expect(await screen.findByRole('alert')).toHaveTextContent(/email is required/i);
  });
});
```

---

## 7. Discovery Guide for LLMs

When analyzing an unfamiliar React codebase:

```typescript
// 1. Check package.json:
// - React version: "react": "^18.x" vs "^19.x" (check if Actions / compiler can be used)
// - Framework: "next", "@remix-run/react", "react-router-dom", "vite"
// - Styling: "tailwindcss", "@emotion/react", "styled-components", "@vanilla-extract/css"
// - Component libraries: "@radix-ui/*", "@shadcn/ui", "@mantine/core", "@mui/material"
// - State & Queries: "@tanstack/react-query", "zustand", "jotai", "@reduxjs/toolkit"

// 2. Check directory layout:
// - If `app/` exists with `page.tsx` -> Next.js App Router (RSC rules apply).
// - If `src/features/` exists -> Feature-sliced architecture; place new components under features/<name>.
// - If `src/components/` and `src/hooks/` -> Centralized layered architecture.

// 3. Check existing component patterns:
// - How are props typed? (`interface Props` vs `type Props`)
// - How are components exported? (`export function Component()` vs `export default Component`)
// - What icon library is used? (`lucide-react`, `react-icons`, `@heroicons/react`)
```

