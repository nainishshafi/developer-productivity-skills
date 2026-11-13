# React Component Architecture & Composition

Clean component design, separation of concerns, and composition patterns in modern React (React 18 & 19).

---

## 1. Presentational UI vs Container Components

- **Presentational UI (Dumb Components)**: Pure visual rendering and layout. Receive data and callbacks via props; contain minimal to zero business logic. Easy to test and preview in Storybook.
- **Container / Screen Components (Smart Components)**: Wire custom hooks, query server data, orchestrate navigation, and compose presentational pieces.

---

## 2. Custom Hooks for Behavioral Abstraction

Extract complex stateful logic, browser event listeners, or asynchronous workflows into custom hooks. Keep components declarative (for full built-in & React 19 hook guidance, see [Hooks Architecture, React 19 Hooks & Custom Hook Patterns](hooks-architecture-and-patterns.md)):

```tsx
// ❌ ANTI-PATTERN: Bloated component with mixed API logic and state
export function UserProfile({ userId }: { userId: string }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  useEffect(() => { ... }, [userId]);
  // 100 lines of API handlers and DOM markup...
}

// ✅ BEST PRACTICE: Declarative component powered by a custom hook
export function UserProfile({ userId }: { userId: string }) {
  const { user, isLoading, updateProfile, errors } = useUserProfile(userId);

  if (isLoading) return <ProfileSkeleton />;
  if (!user) return <NotFoundBanner />;

  return <ProfileForm user={user} onSubmit={updateProfile} errors={errors} />;
}
```

---

## 3. Eliminating "Prop Drilling Hell" (Inversion of Control & 4-Tier Resolution)

**Prop Drilling Hell** occurs when intermediate components act as passive "trampolines"—accepting props (`user`, `notificationsCount`, `onLogout`) solely to pass them down 3–6 levels to a deeply nested leaf component that actually consumes them.

### Why Prop Drilling Hell Hurts Architecture
- **Middleman Coupling**: Adding or renaming one leaf prop forces interface and JSX edits across every intermediate layout component in the chain.
- **Unnecessary Re-Render Cascades**: Updating a drilled prop invalidates and re-renders intermediate layout wrappers that never read the prop.
- **Bloated Component Contracts**: Layout components (`AppShell`, `Sidebar`, `Card`) become tightly coupled to domain entities (`User`, `BillingPlan`) instead of staying reusable.

```tsx
// ❌ ANTI-PATTERN: Prop Drilling Hell (3 middlemen accept & forward unused props)
function DashboardPage({ user, unreadCount, onLogout }: Props) {
  return <AppLayout user={user} unreadCount={unreadCount} onLogout={onLogout} />;
}
function AppLayout({ user, unreadCount, onLogout }: Props) {
  return <TopNavbar user={user} unreadCount={unreadCount} onLogout={onLogout} />;
}
function TopNavbar({ user, unreadCount, onLogout }: Props) {
  return <UserMenuTrigger user={user} unreadCount={unreadCount} onLogout={onLogout} />;
}
```

### The 4-Tier Resolution Hierarchy (Apply in Order)

| Priority | Strategy | When to Use | Why It Beats Reaching Straight for Global State |
|---|---|---|---|
| **1. Inversion of Control (`children` & Named Slots)** | Pass pre-rendered JSX (`userSlot={<UserMenuTrigger ... />}`) from the parent owner | **Default fix** for layout shells, navbars, sidebars, and cards | Zero providers, zero store boilerplate; intermediate layouts stay 100% domain-agnostic |
| **2. Server-State Colocation (TanStack Query / RSC)** | Call `useQuery({ queryKey: ['me'] })` directly in the leaf, or fetch in an RSC leaf | Drilled props originate from a backend API | TanStack Query deduplicates requests automatically; RSC eliminates client prop serialization |
| **3. Scoped Subtree Context / Compound Components** | `createContext` scoped to `<Accordion>`, `<Tabs>`, or a feature subtree | Multiple sibling leaves inside one widget share state | Avoids polluting global state while keeping widget internals encapsulated |
| **4. Atomic Store Selectors (Zustand)** | `useUIStore((s) => s.sidebarOpen)` | High-frequency cross-route client state (cart, theme, modals) | Prevents both Prop Drilling Hell and "Context Provider Wrapper Hell" |

```tsx
// ✅ TIER 1 FIX: Inversion of Control via Named Slots & children (Zero Prop Drilling)
export function DashboardPage({ user, unreadCount, onLogout }: Props) {
  return (
    <AppLayout
      navbar={
        <TopNavbar
          rightSlot={
            <UserMenuTrigger
              badge={<AvatarBadge user={user} unreadCount={unreadCount} />}
              onLogout={onLogout}
            />
          }
        />
      }
    >
      <DashboardContent />
    </AppLayout>
  );
}

// AppLayout and TopNavbar know NOTHING about `user`, `unreadCount`, or `onLogout`!
function AppLayout({ navbar, children }: { navbar: ReactNode; children: ReactNode }) {
  return (
    <div className="min-h-screen flex flex-col">
      {navbar}
      <main className="flex-1">{children}</main>
    </div>
  );
}
```

---

## 4. Compound Component Pattern with Context

Provide flexible, accessible UI widgets without rigid configuration objects:

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
  const toggle = (id: string) => setActiveId(prev => (prev === id ? null : id));

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

## 5. React 19 `ref` as a Standard Prop (Replacing `forwardRef`)

In React 19, function components receive `ref` as a regular prop alongside other component props, eliminating `React.forwardRef` boilerplate:

```tsx
import type { ComponentProps } from 'react';

// ✅ React 19: Accept ref directly as a prop
export function TextInput({ label, ref, ...props }: ComponentProps<'input'> & { label: string }) {
  return (
    <label className="flex flex-col gap-1">
      <span>{label}</span>
      <input ref={ref} className="border rounded px-3 py-2" {...props} />
    </label>
  );
}
```

