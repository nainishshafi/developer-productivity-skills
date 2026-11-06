---
name: react-developer
description: Architectural and engineering guidance for modern React development (React 18 & 19, Next.js, Remix/React Router, Vite, React Server Components). Helps the LLM analyze existing project architecture, adapt to codebase conventions, and apply clean frontend architecture, state management, custom hook composition, component design, and performance patterns pragmatically without imposing dogmatic hard rules. Use when designing, writing, reviewing, or refactoring React components and applications, or when the user asks to "write react code", "develop react component", "react architecture best practices", "nextjs server components", or "refactor react frontend".
version: 1.0.0
---

# React Developer Skill

An architectural guidance framework for modern React (React 18+, React 19, Next.js App Router, Vite, and Remix/React Router v7). This skill is **not an inflexible rulebook**; it guides the LLM to inspect, discover, and adapt to the project's existing frontend architecture while applying clean component architecture, state management discipline, and UI resilience principles.

---

## 1. Adaptive Architectural Discovery (Find First, Then Align)

Before generating or modifying React code, the LLM must **inspect the project context**:

1. **Detect Toolchain, Runtime & Framework Baseline**:
   - Check `package.json`, `tsconfig.json`, and lockfiles (`pnpm-lock.yaml`, `package-lock.json`, `yarn.lock`, `bun.lockb`).
   - Identify the framework/bundler:
     - **Next.js**: App Router (`app/` directory with Server Components) vs Pages Router (`pages/`).
     - **Vite / SPA**: Client-side single page application (`src/main.tsx`, `index.html`).
     - **Remix / React Router v7**: Route-based loaders, actions, and nested routes.
     - **TanStack Start / Astro / Gatsby**: Specialized modern SSR/SSG architectures.
   - Detect React version:
     - **React 19**: Actions (`useActionState`, `useFormStatus`, `useOptimistic`), `use()` hook, native ref passing without `forwardRef`.
     - **React 18**: `useTransition`, `useDeferredValue`, Suspense for data fetching.
   - Never introduce dependencies, hooks, or syntax incompatible with the project's React version or bundler.

2. **Identify the Architecture Style & Directory Layout**:
   - **Feature-Based / Feature-Sliced** (`src/features/<feature>/` containing `components/`, `hooks/`, `api/`, `types/`): Common in enterprise and scalable modular apps.
   - **Layered / Type-Based** (`src/components/`, `src/hooks/`, `src/services/`, `src/pages/`): Standard in small to mid-sized SPAs.
   - **Vertical Slice / App Router** (`app/(routes)/`, `components/ui/`, `actions/`): Common in full-stack Next.js applications.
   - *Rule:* Follow existing layout conventions. Do not create isolated `features/` folders if the project consistently organizes by `components/` and `hooks/`.

3. **Assess Conventions & Libraries**:
   - **Server State / Data Fetching**: TanStack Query (React Query), SWR, RTK Query, Apollo Client, or Server Components + Server Actions.
   - **Client State**: Zustand, Jotai, Redux Toolkit, Context API + `useReducer`, or XState.
   - **Form Management & Validation**: React Hook Form, Formik, native React 19 actions, paired with Zod, Valibot, or Yup.
   - **Styling & UI Components**: Tailwind CSS, CSS Modules, Styled Components / Emotion, Radix UI / Shadcn UI, Mantine, Ant Design, or MUI.
   - **Routing & URL State**: TanStack Router, React Router, Next.js Navigation, `nuqs` (URL search params).
   - **Testing**: React Testing Library + Vitest / Jest, Playwright, Cypress, Storybook.

---

## 2. Core Architectural Principles in React

### A. Separation of Concerns & Hook Abstraction
- **Presentational UI (Dumb Components)**: Focus strictly on visual rendering and layout. Receive data and callbacks via props; contain minimal to no business logic.
- **Container / Screen Components (Smart Components)**: Wire custom hooks, query client data, handle route navigation, and compose presentational pieces.
- **Custom Hooks for Behavioral Abstraction**: Extract complex stateful logic, API orchestrations, or browser event listeners into reusable custom hooks (`useCart()`, `useAuth()`, `useDebounce()`). Keep components declarative:
  ```tsx
  // Good: Component declares intent; hook handles implementation
  export function ProfileEditor({ userId }: { userId: string }) {
    const { profile, isSaving, updateProfile, errors } = useUserProfile(userId);

    if (!profile) return <ProfileSkeleton />;
    return <ProfileForm data={profile} isSubmitting={isSaving} onSubmit={updateProfile} errors={errors} />;
  }
  ```

### B. State Architecture & Colocation
- **Colocate State**: Keep state as close to where it is consumed as possible. Lift state up only when multiple sibling components genuinely require synchronization.
- **Avoid Redundant & Derived State**: Compute values on the fly during render instead of storing derived state in `useState` or syncing with `useEffect`:
  ```tsx
  // Avoid: Redundant state synced via effect
  const [items, setItems] = useState<Item[]>([]);
  const [total, setTotal] = useState(0);
  useEffect(() => { setTotal(items.reduce((s, i) => s + i.price, 0)); }, [items]);

  // Prefer: Compute during render (wrap with useMemo only if calculation is measurably heavy)
  const [items, setItems] = useState<Item[]>([]);
  const total = items.reduce((s, i) => s + i.price, 0);
  ```
- **Distinguish State Categories**:
  - *Server State*: Cached remote data (TanStack Query, SWR, RSC cache).
  - *Client State*: Transient UI state (modals, active tabs, theme).
  - *URL State*: Search queries, filters, pagination (belong in URL query params for shareability).
  - *Form State*: Intermediate input values and field validation states.

### C. Component Composition over Prop Drilling
- Avoid deep prop drilling by composing components via `children`, slots, or the **Compound Component Pattern** with context:
  ```tsx
  // Prefer composition over boolean flags and deep props
  <Card>
    <Card.Header title="Billing Details" action={<Button variant="ghost">Edit</Button>} />
    <Card.Content>
      <PaymentMethodList methods={paymentMethods} />
    </Card.Content>
  </Card>
  ```

### D. Server Components (RSC) vs Client Components
When working with Next.js App Router or RSC environments:
- **Default to Server Components**: Fetch data directly on the server, access databases or backend APIs without exposing secrets, and reduce client JavaScript bundle size.
- **Push `'use client'` to the Leaves**: Keep client components focused solely on interactive boundaries (buttons, form inputs, animations, hooks like `useState`/`useEffect`).
- **Pass Server Components as Children to Client Wrappers**: Maintain server-rendered performance while enabling client interactivity (e.g., interactive modal or collapse containers).

### E. Side-Effect Discipline & Resilience
- **`useEffect` is for Synchronization Only**: Use effects exclusively for synchronizing with external non-React systems (DOM APIs, WebSockets, third-party widgets). Never use effects for user-initiated mutations or simple data transformation.
- **Always Clean Up Subscriptions**: Return cleanup functions from effects for listeners, timers, and abortable fetches (`AbortController`).
- **Boundary Defense with Error Boundaries & Suspense**: Wrap asynchronous UI regions in `ErrorBoundary` (e.g. `react-error-boundary`) and `<Suspense>` fallbacks to prevent a single component failure from crashing the entire view.

---

## 3. Practical Architecture Patterns

### Pattern 1: Feature-Sliced / Modular Frontend Structure
```text
src/
├── features/
│   ├── authentication/
│   │   ├── components/       # LoginCard, SignupForm, AuthGuard
│   │   ├── hooks/            # useAuth, useSessionTimeout
│   │   ├── api/              # authApi.ts, queries.ts, mutations.ts
│   │   ├── types/            # auth.types.ts
│   │   └── index.ts          # Public feature interface
│   └── product-catalog/
├── shared/
│   ├── components/           # Button, Modal, Input (Design system primitives)
│   ├── hooks/                # useMediaQuery, useDebounce, useLocalStorage
│   ├── lib/                  # apiClient, queryClient, utils
│   └── types/                # common.types.ts
```

### Pattern 2: Headless Custom Hook Data Layer
Decouple view presentation from network protocols and state caching:

```tsx
// features/products/hooks/useProducts.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { fetchProducts, updateProduct, type Product } from '../api/productsApi';

export function useProducts(category?: string) {
  const queryClient = useQueryClient();

  const query = useQuery({
    queryKey: ['products', { category }],
    queryFn: () => fetchProducts(category),
    staleTime: 1000 * 60 * 5, // 5 minutes fresh
  });

  const mutation = useMutation({
    mutationFn: updateProduct,
    onSuccess: (updated) => {
      queryClient.setQueryData<Product[]>(['products', { category }], (old) =>
        old?.map((item) => (item.id === updated.id ? updated : item))
      );
    },
  });

  return {
    products: query.data ?? [],
    isLoading: query.isLoading,
    isError: query.isError,
    error: query.error,
    updateProduct: mutation.mutateAsync,
    isUpdating: mutation.isPending,
  };
}
```

### Pattern 3: Compound Component Pattern with Context
Provide flexible, accessible UI containers without rigid configuration objects:

```tsx
// shared/components/Accordion.tsx
import React, { createContext, useContext, useState, type ReactNode } from 'react';

interface AccordionContextType {
  activeId: string | null;
  toggle: (id: string) => void;
}

const AccordionContext = createContext<AccordionContextType | null>(null);

function useAccordionContext() {
  const ctx = useContext(AccordionContext);
  if (!ctx) throw new Error('Accordion compound components must be rendered inside <Accordion>');
  return ctx;
}

export function Accordion({ children }: { children: ReactNode }) {
  const [activeId, setActiveId] = useState<string | null>(null);
  const toggle = (id: string) => setActiveId((prev) => (prev === id ? null : id));

  return (
    <AccordionContext.Provider value={{ activeId, toggle }}>
      <div className="divide-y divide-gray-200 border rounded-lg">{children}</div>
    </AccordionContext.Provider>
  );
}

Accordion.Item = function AccordionItem({ id, title, children }: { id: string; title: string; children: ReactNode }) {
  const { activeId, toggle } = useAccordionContext();
  const isOpen = activeId === id;

  return (
    <div className="py-2 px-4">
      <button
        type="button"
        className="flex justify-between w-full font-medium text-left"
        onClick={() => toggle(id)}
        aria-expanded={isOpen}
      >
        <span>{title}</span>
        <span>{isOpen ? '−' : '+'}</span>
      </button>
      {isOpen && <div className="mt-2 text-gray-600">{children}</div>}
    </div>
  );
};
```

---

## 4. Architectural Pragmatism (Avoid Over-Engineering)

- **Avoid Premature Memoization**: Do not blanket every callback in `useCallback` or every primitive in `useMemo`. Modern React is optimized for standard renders; only apply memoization when:
  - Passing callbacks/objects to memoized child components (`React.memo`) that re-render expensively.
  - Feeding dependencies into hook dependency arrays (`useEffect`, `useMemo`).
  - Executing heavy computational algorithms (sorting large datasets, complex filtering).
- **Honor Project Simplicity**: If an application has straightforward UI state, do not introduce heavy Redux/Zustand boilerplate when simple `useState` and composition or Context suffices.
- **Match Existing Component Idioms**:
  - If the project uses standard named function components (`export function UserCard()`), do not switch to `const UserCard: React.FC = () =>`.
  - If styling is handled via Tailwind classes, do not introduce inline styles or CSS-in-JS.
  - If data fetching is handled via Server Actions or TanStack Query, match the existing querying pattern.

---

## References

- [React Developer Reference Guide](file:///.github/skills/react-developer/references/react-developer-reference.md) — Comprehensive architecture matrix, state management recipes, RSC decision tree, custom hooks, and testing patterns.
