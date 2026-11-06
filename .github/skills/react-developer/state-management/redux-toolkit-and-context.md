# Redux Toolkit, Normalized State & Context API Boundaries

When to choose Redux Toolkit vs Zustand vs React Context, avoiding Context re-render traps, and normalizing state.

---

## 1. State Store Architecture Comparison

| Mechanism | Ideal When | Re-render Behavior | Setup Cost |
|---|---|---|---|
| **Zustand** | General client state, modals, carts, UI settings. | Granular (only subscribed selector re-renders). | Zero (no provider). |
| **Redux Toolkit (RTK)** | Complex enterprise apps with strict action tracing, time-travel debugging, large multi-team codebases. | Granular via `useSelector`. | Moderate (Store Provider, slices). |
| **Context + useReducer** | Compound UI components, themes, localized subtrees. | Coarse (ALL consumer components re-render on *any* context value change). | Low. |

---

## 2. Preventing React Context Re-render Cascades

React Context triggers a re-render on **every component that calls `useContext`**, even if the component only cares about a property that did not change.

### The Fix: Split Dispatch from State
```tsx
// ❌ ANTI-PATTERN: Single monolithic context
interface UserContextType {
  user: User | null;
  theme: string;
  login: (u: User) => void;
  toggleTheme: () => void;
}
// Any change to `theme` forces re-rendering of all components reading `user`!

// ✅ BEST PRACTICE: Split State Context from Action/Dispatch Context
const UserStateContext = createContext<User | null>(null);
const UserDispatchContext = createContext<{ login: (u: User) => void; logout: () => void } | null>(null);

export function UserProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);

  // Stable callbacks wrapped in useCallback or useMemo
  const actions = useMemo(() => ({
    login: (u: User) => setUser(u),
    logout: () => setUser(null),
  }), []);

  return (
    <UserDispatchContext.Provider value={actions}>
      <UserStateContext.Provider value={user}>
        {children}
      </UserStateContext.Provider>
    </UserDispatchContext.Provider>
  );
}
```

---

## 3. Redux Toolkit (RTK) & Normalized State

For complex relational client data, avoid deeply nested arrays. Use `createEntityAdapter` to store items by ID:

```typescript
// features/users/usersSlice.ts
import { createSlice, createEntityAdapter, PayloadAction } from '@reduxjs/toolkit';

export interface UserEntity {
  id: string;
  name: string;
  email: string;
}

// Normalized adapter manages { ids: string[], entities: Record<string, UserEntity> }
const usersAdapter = createEntityAdapter<UserEntity>({
  selectId: (user) => user.id,
  sortComparer: (a, b) => a.name.localeCompare(b.name),
});

export const usersSlice = createSlice({
  name: 'users',
  initialState: usersAdapter.getInitialState({
    isLoading: false,
    error: null as string | null,
  }),
  reducers: {
    userAdded: usersAdapter.addOne,
    userUpdated: usersAdapter.updateOne,
    userRemoved: usersAdapter.removeOne,
    usersReceived(state, action: PayloadAction<UserEntity[]>) {
      usersAdapter.setAll(state, action.payload);
      state.isLoading = false;
    },
  },
});

export const { selectAll: selectAllUsers, selectById: selectUserById } =
  usersAdapter.getSelectors((state: any) => state.users);
```

