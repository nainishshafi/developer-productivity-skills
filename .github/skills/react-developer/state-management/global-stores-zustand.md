# React Global State Management with Zustand

Enterprise patterns for managing client-side global state using Zustand without re-render cascades.

---

## 1. Why Zustand over Redux / Plain Context

- **Zero Provider Wrapping**: Stores live outside the React fiber tree, preventing root re-renders.
- **Selective Subscriptions**: Components re-render *only* when the specific slice of state they select changes.
- **Boilerplate-Free**: No actions, reducers, dispatchers, or boilerplate ceremonies.
- **Middleware Ecosystem**: Built-in `persist`, `devtools`, `immer`, and `subscribeWithSelector`.

---

## 2. Enterprise Slice Pattern for Modular Stores

For large applications, divide state into distinct slices and merge them into a single unified store:

```typescript
// features/auth/authSlice.ts
import { StateCreator } from 'zustand';

export interface AuthSlice {
  user: { id: string; name: string; role: string } | null;
  token: string | null;
  setAuth: (user: AuthSlice['user'], token: string) => void;
  logout: () => void;
}

export const createAuthSlice: StateCreator<AuthSlice & CartSlice, [], [], AuthSlice> = (set) => ({
  user: null,
  token: null,
  setAuth: (user, token) => set({ user, token }),
  logout: () => set({ user: null, token: null }),
});

// features/cart/cartSlice.ts
export interface CartItem {
  id: string;
  name: string;
  price: number;
  qty: number;
}

export interface CartSlice {
  items: CartItem[];
  addItem: (item: Omit<CartItem, 'qty'>) => void;
  removeItem: (id: string) => void;
  clearCart: () => void;
}

export const createCartSlice: StateCreator<AuthSlice & CartSlice, [], [], CartSlice> = (set) => ({
  items: [],
  addItem: (item) =>
    set((state) => {
      const existing = state.items.find((i) => i.id === item.id);
      if (existing) {
        return {
          items: state.items.map((i) =>
            i.id === item.id ? { ...i, qty: i.qty + 1 } : i
          ),
        };
      }
      return { items: [...state.items, { ...item, qty: 1 }] };
    }),
  removeItem: (id) =>
    set((state) => ({ items: state.items.filter((i) => i.id !== id) })),
  clearCart: () => set({ items: [] }),
});

// shared/stores/useAppStore.ts
import { create } from 'zustand';
import { devtools, persist } from 'zustand/middleware';

export type AppStore = AuthSlice & CartSlice;

export const useAppStore = create<AppStore>()(
  devtools(
    persist(
      (...a) => ({
        ...createAuthSlice(...a),
        ...createCartSlice(...a),
      }),
      {
        name: 'app-storage',
        partialize: (state) => ({ token: state.token, items: state.items }), // Persist only token & items
      }
    )
  )
);
```

---

## 3. Selector Optimization & `useShallow`

Selecting multiple state properties using object destructuring causes unnecessary re-renders whenever *any* unrelated state changes unless `useShallow` is used:

```tsx
// ❌ ANTI-PATTERN: Returns a new object reference on EVERY store update!
// Component re-renders when `token` changes, even though it only uses `items` and `user`
const { items, user } = useAppStore((state) => ({ items: state.items, user: state.user }));

// ✅ BEST PRACTICE 1: Granular atomic selectors (Best for single values)
const items = useAppStore((state) => state.items);
const user = useAppStore((state) => state.user);

// ✅ BEST PRACTICE 2: useShallow for multiple properties (Zustand 4.5+)
import { useShallow } from 'zustand/react/shallow';

const { items, addItem } = useAppStore(
  useShallow((state) => ({ items: state.items, addItem: state.addItem }))
);
```

---

## 4. Reading / Writing State Outside React Components

Zustand stores can be accessed and mutated directly inside non-React utilities, Axios interceptors, or background workers without hooks:

```typescript
// lib/apiClient.ts
import { useAppStore } from '@/shared/stores/useAppStore';

apiClient.interceptors.request.use((config) => {
  // Read state outside React
  const token = useAppStore.getState().token;
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

apiClient.interceptors.response.use(
  (res) => res,
  (error) => {
    if (error.response?.status === 401) {
      // Mutate state outside React
      useAppStore.getState().logout();
    }
    return Promise.reject(error);
  }
);
```

