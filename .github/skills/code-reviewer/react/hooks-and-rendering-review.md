# React Hooks & Rendering Performance Review Guide

Audit guide for React hooks, closures, re-rendering bottlenecks, and memoization.

---

## 1. Hooks Rules & Dependency Arrays

- [ ] **Exhaustive Dependencies**:
  - Do `useEffect`, `useCallback`, and `useMemo` declare all referenced props and state in their dependency arrays?
  - Never disable `eslint-plugin-react-hooks/exhaustive-deps` without an explicit comment explaining why.
- [ ] **Stale Closures**:
  - Does an effect or async callback capture stale state instead of using functional state updaters (`setCount(prev => prev + 1)`)?
- [ ] **Derived State Over Synchronization**:
  - Is `useEffect` being misused to sync state that could be computed during render?
  ```typescript
  // BAD: Redundant state and extra re-render
  const [fullName, setFullName] = useState('');
  useEffect(() => {
    setFullName(`${firstName} ${lastName}`);
  }, [firstName, lastName]);

  // GOOD: Compute directly during render
  const fullName = `${firstName} ${lastName}`;
  ```

---

## 2. Unnecessary Re-renders & Memoization

- [ ] **Object & Array Instantiation in Render**:
  - Are new object/array literals or inline arrow functions created inside render and passed down to `React.memo` components, breaking shallow equality?
- [ ] **Targeted Memoization**:
  - Is `useMemo` reserved for expensive computations (e.g. sorting large lists, complex formatting) rather than trivial primitive derivations?
- [ ] **Context Over-subscription**:
  - Does a monolithic React Context trigger whole-tree re-renders when only a single property changes?
  - **Resolution**: Split contexts by update frequency or use Zustand stores with selective selectors.

---

## 3. Memory Leaks & Cleanup in Effects

- [ ] **Effect Teardown**:
  - Do effects that register event listeners, WebSocket connections, intervals (`setInterval`), or observers (`ResizeObserver`, `IntersectionObserver`) return a cleanup function?
  ```typescript
  useEffect(() => {
    const controller = new AbortController();
    fetchData({ signal: controller.signal });
    return () => controller.abort();
  }, [id]);
  ```

---

## 4. Virtualization & Large Lists

- [ ] **DOM Node Explosion**:
  - Does the UI render lists with > 100 items directly without virtualization?
  - **Resolution**: Use TanStack Virtual (`@tanstack/react-virtual`) or `react-window` for large lists or tables.

