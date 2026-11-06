# React State Architecture & Decision Matrix

Categorize and manage state cleanly across server, global, URL, and local boundaries.

---

## 1. State Management Decision Matrix

```text
Is the state originating from a remote server (API, Database)?
  ├── YES ──> Use Server State:
  │             - TanStack Query (React Query)
  │             - SWR
  │             - React Server Components + Next.js fetch cache
  │
  └── NO ───> Is it needed across many unrelated routes or screens?
                ├── YES ──> Use Global Client State:
                │             - Zustand (recommended default for global state)
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

---

## 2. Eliminate Redundant & Derived State

Never duplicate state into `useState` and synchronize it via `useEffect`. Compute derived values directly in render:

```tsx
// ❌ ANTI-PATTERN: Redundant state synced with useEffect
const [items, setItems] = useState<Item[]>([]);
const [total, setTotal] = useState(0);

useEffect(() => {
  setTotal(items.reduce((acc, item) => acc + item.price, 0));
}, [items]); // Causes an unnecessary extra render pass!

// ✅ BEST PRACTICE: Derived state computed directly during render
const [items, setItems] = useState<Item[]>([]);
const total = items.reduce((acc, item) => acc + item.price, 0);
// Wrap with useMemo only if calculations exceed 1ms in production profiling
```

---

## 3. Lightweight Global Stores with Zustand

When global client state is truly required (e.g. user session, shopping cart, theme), use Zustand:

```typescript
// shared/stores/useCartStore.ts
import { create } from 'zustand';

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
}

export const useCartStore = create<CartState>((set) => ({
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
}));
```

