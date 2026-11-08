# React State Management & Data Fetching Review Guide

Audit guide for client state (Zustand, Redux) and server state (TanStack Query, SWR).

---

## 1. Server State vs. Client State Separation

- [ ] **No Manual Cache in useState**:
  - Are API responses stored in `useState` + `useEffect` with manual loading/error states?
  - **Resolution**: Use TanStack Query (`useQuery`) or SWR to automatically handle caching, deduplication, background refetching, and error states.
- [ ] **Query Keys**:
  - Are query keys comprehensive arrays containing all dependent parameters (`['users', userId, filter]`)?
  - Missing parameters in query keys cause stale cache collisions.

---

## 2. TanStack Query / SWR Best Practices

- [ ] **Stale Time Configuration**:
  - Is `staleTime` tuned appropriately (e.g. `staleTime: 1000 * 60 * 5`) rather than defaulting to `0` which triggers excessive network refetches on every window focus?
- [ ] **Optimistic Updates**:
  - Do mutations with optimistic updates rollback state on failure using `onError(err, variables, context)`?
- [ ] **Query Invalidation**:
  - Are query keys invalidated (`queryClient.invalidateQueries(...)`) after successful mutations?

---

## 3. Global Client State (Zustand / Redux Toolkit)

- [ ] **Atomic Selectors in Zustand**:
  - Are components selecting only the specific slice of state they need?
  ```typescript
  // BAD: Re-renders when ANY property in the store changes
  const { user, theme } = useAppStore();

  // GOOD: Only re-renders when user changes
  const user = useAppStore(state => state.user);
  ```
- [ ] **Redux Toolkit Slice Design**:
  - Are slices normalized using `createEntityAdapter` to prevent nested state mutation traps?

