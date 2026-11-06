# React Component Architecture & Composition

Clean component design, separation of concerns, and composition patterns in modern React (React 18 & 19).

---

## 1. Presentational UI vs Container Components

- **Presentational UI (Dumb Components)**: Pure visual rendering and layout. Receive data and callbacks via props; contain minimal to zero business logic. Easy to test and preview in Storybook.
- **Container / Screen Components (Smart Components)**: Wire custom hooks, query server data, orchestrate navigation, and compose presentational pieces.

---

## 2. Custom Hooks for Behavioral Abstraction

Extract complex stateful logic, browser event listeners, or asynchronous workflows into custom hooks. Keep components declarative:

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

## 3. Composition over Prop Drilling & Boolean Flags

Avoid passing props down 5 levels or toggling dozens of boolean layout flags (`hasHeader`, `isSidebarCompact`). Use component composition:

```tsx
// ✅ BEST PRACTICE: Component slots via children and named subcomponents
<Card>
  <Card.Header title="Billing Summary" action={<Button variant="ghost">Edit</Button>} />
  <Card.Content>
    <PaymentMethodList methods={paymentMethods} />
  </Card.Content>
</Card>
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

