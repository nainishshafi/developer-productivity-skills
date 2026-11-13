# React Code Review, Functional Programming & Clean Code Audit

Senior-level code review rubric for modern React (React 18 & 19, Next.js App Router, Vite) emphasizing **Functional Programming discipline ($\text{UI} = f(\text{state})$)**, **Clean Code principles (SOLID, DRY, KISS, YAGNI)**, hooks hygiene, state boundaries, security, accessibility, and test rigor.

---

## 1. The 8-Dimension React Code Review Matrix

### Dimension 1: Functional Programming & Anti-Procedural Discipline ($\text{UI} = f(\text{state})$)
- [ ] **Referential Transparency in Render**: Is the component body a pure function of `props` and `state` with zero side effects (`fetch`, timers, `localStorage.setItem`, DOM mutations) executed directly during render?
- [ ] **Zero In-Place Array/Object Mutations**: Are mutating methods (`.sort()`, `.reverse()`, `.splice()`, `.push()`, direct prop/state property assignment) banned in favor of ES2023 immutable operations (`.toSorted()`, `.toReversed()`, `.toSpliced()`, `.with()`, object/array spreads)?
- [ ] **No Procedural `let` Accumulator Ladders**: Are imperative `let result = ...; if (...) { result = ... }` reassignment chains replaced with pure expressions, `Record<K, V>` lookup maps, or exhaustive `switch` helpers (`assertNever`)?
- [ ] **Declarative Collection Pipelines**: Are imperative `for` loops pushing into temporary arrays inside JSX components extracted into pure, composable selector functions (`filter`, `map`, `Object.groupBy`) outside the component?
- [ ] **Functional Core, Imperative Shell**: Are sequential `useEffect` state-mutation chains eliminated? Pure domain calculations and state transitions (`(state, action) => nextState`) live in the Functional Core; I/O and navigation live explicitly in event handlers (`onClick`, `onSubmit`).

### Dimension 2: Clean Code Principles (SOLID, DRY, KISS, YAGNI)
- [ ] **Single Responsibility Principle (SRP)**: Does each component/hook own one cohesive responsibility? Extract business/async orchestration into focused custom hooks and keep visual components under ~200 lines—while avoiding pointless 10-line micro-component splitting.
- [ ] **Open/Closed Principle (Composition Over Flag Soup)**: Instead of adding 6+ boolean props (`hasHeader`, `isCompact`, `showFooterActions`), does the component extend cleanly via `children`, slot props, or Compound Components?
- [ ] **Zero "Prop Drilling Hell" (No Trampoline Pass-Through Props)**: Are props passed through $\le 2$ component levels? If intermediate components accept props solely to forward them to children without using them, refactor using **Inversion of Control (`children` / `ReactNode` slots)**, TanStack Query key colocation, scoped Context, or atomic store selectors.
- [ ] **Shallow Nesting & Early Returns**: Are loading, empty, error, and guard states handled via early returns at the top of the component rather than deeply nested ternary chains inside JSX?
- [ ] **Consistent Naming & Intent**:
  - Callback props named `on*` (`onSubmit`, `onFilterChange`); internal event handlers named `handle*` (`handleSubmit`).
  - Boolean props/state prefixed with `is`/`has`/`can`/`should` (`isPending`, `hasAccess`), avoiding double negatives (`!isNotDisabled`).
  - Custom hooks prefixed with `use*` only when encapsulating React hook lifecycles; pure functions without hooks kept as plain functions (`formatCurrency`, `selectActiveUsers`).
- [ ] **YAGNI & Anti-Bloat Audit**: Are single-use helper hooks, redundant context wrappers, and premature generic factories avoided? Run [`detect-overengineering`](file:///.github/skills/detect-overengineering/SKILL.md) on large frontend PRs.

### Dimension 3: Hooks Architecture & Lifecycle Hygiene (React 18 & 19)
- [ ] **"You Might Not Need an Effect"**: Is `useEffect` absent for derived state, prop-change state resets (use `key={entityId}` instead), and user-triggered mutations?
- [ ] **Exhaustive Dependencies & Stale Closures**: Are ESLint `react-hooks/exhaustive-deps` rules honored without disabling comments, using functional updaters (`setCount(c => c + 1)`) or Latest-Ref patterns rather than suppressing missing dependencies?
- [ ] **Mandatory Cleanup Teardown**: Do `useEffect` hooks clean up in-flight `fetch` calls (`AbortController`), intervals/timeouts, DOM observers, and third-party canvas/map instances on unmount?
- [ ] **React 19 Idioms**: Are new React 19 components accepting `ref` directly as a prop (instead of legacy `forwardRef`) and leveraging `useActionState`/`useFormStatus`/`useOptimistic` where appropriate for progressive form actions?

### Dimension 4: State Architecture & Immutability
- [ ] **Impossible States Made Unrepresentable**: Are coupled flags (`isLoading && isError`) replaced with discriminated union state (`{ status: 'idle' | 'loading' | 'success' | 'error' }`)?
- [ ] **Server vs. Client State Boundary**: Is remote API data managed via TanStack Query / RSC rather than duplicated manually into Zustand or global Redux stores?
- [ ] **Atomic Store Selectors**: Do Zustand/Redux consumers select minimal atomic slices (`useStore((s) => s.count)` or `useShallow`) instead of subscribing to the entire store object?

### Dimension 5: Rendering Performance & Concurrent React
- [ ] **Stable List `key`s**: Are list `key` props stable, unique domain IDs (`item.id`) rather than array indexes (`key={index}`) on dynamic/sortable/filterable lists?
- [ ] **Concurrent Responsiveness**: Are expensive filtering, tab switches, or heavy visual updates wrapped in `useTransition` / `useDeferredValue` without wrapping controlled `<input>` state?
- [ ] **Pragmatic Memoization & Virtualization**: Are lists exceeding ~100 complex rows virtualized (`@tanstack/react-virtual`), and is `useMemo`/`useCallback` reserved for measured bottlenecks or memoized child/effect stability rather than trivial primitives?

### Dimension 6: Server Components (RSC) & Next.js Boundaries
- [ ] **Leaf `'use client'` Placement**: Are `'use client'` directives pushed down to interactive leaves rather than placed on entire route layouts or data-fetching pages?
- [ ] **Zero Secret Leakage**: Are database clients, API keys, and server-only modules isolated to Server Components / Server Actions and never imported or serialized into `'use client'` props?
- [ ] **Streaming & Resilience**: Are slow async subtrees wrapped in `<Suspense fallback={...}>` and `<ErrorBoundary>` so one failing widget does not crash the entire page?

### Dimension 7: Security, Accessibility (WCAG) & SSR Safety
- [ ] **XSS & URL Protocol Defense**: Is `dangerouslySetInnerHTML` forbidden unless sanitized via DOMPurify, and are dynamic `href`/`src` values validated against `javascript:` / `data:` injection?
- [ ] **Semantic Interactive Elements**: Are clickable actions implemented with `<button type="button">` or `<a href>` (never clickable `<div onClick>`) with visible focus rings and accessible labels (`aria-label` / `<label>`)?
- [ ] **SSR & Hydration Determinism**: Are `window`/`localStorage` reads guarded or deferred out of initial SSR render, and are `aria-labelledby`/`htmlFor` IDs generated with `useId()` rather than `Math.random()`?

### Dimension 8: Testing Quality & Ground Truth
- [ ] **Behavior-First RTL Queries**: Do component tests use `getByRole`/`getByLabelText` and `userEvent.setup()` instead of `fireEvent`, CSS class selectors, or snapshot bloat?
- [ ] **Isolated Harness & MSW v2**: Are `QueryClient` instances created fresh per test (`retry: false, gcTime: 0`), Zustand stores reset in `beforeEach`, and HTTP boundaries mocked via MSW v2 (`onUnhandledRequest: 'error'`)?
- [ ] **Hallucination Check**: Cross-check generated frontend tests against source symbols with [`scan-halucinated-tests`](file:///.github/skills/scan-halucinated-tests/SKILL.md).

---

## 2. Severity Classification Standards

| Severity | React Examples | Action Required |
|---|---|---|
| **`[P0 - Blocker]`** | Unsanitized `dangerouslySetInnerHTML`; server secrets passed into `'use client'` props; in-place prop mutation corrupting shared state; infinite `useEffect` fetch loop; missing `AbortController`/cleanup causing active leak/race condition. | **Block merge** — fix immediately. |
| **`[P1 - Major Issue]`** | Procedural `useEffect` chains syncing derived state; Prop Drilling Hell ($\ge 3$ pass-through layers of unused trampoline props); `key={index}` on dynamic/reorderable lists; boolean flag soup allowing impossible UI states; `let` accumulator ladders; clickable `<div>` instead of `<button>`; `getByTestId` / `fireEvent` bypassing accessibility checks. | **Must fix** before PR approval. |
| **`[P2 - Minor Optimization]`** | Missing `useTransition` on heavy filter lists; unvirtualized > 200-row table; blanket `useMemo`/`useCallback` on primitive values; 2-level prop forwarding where slots/composition read cleaner; legacy `forwardRef` in React 19 codebases. | **Recommended** cleanup. |
| **`[P3 - Nit]`** | Handler naming (`onClickBtn` vs `handleClick`); minor JSX readability or early-return polish. | **Optional** polish. |

---

## 3. High-Impact Code Review Refactoring Diffs

### Diff 1: Procedural Impure Component $\to$ Functional & Clean Component
```tsx
// ❌ BEFORE ([P0] in-place .sort() mutation + [P1] let ladder + boolean flag soup)
function TaskPanel({ tasks, filter, showHeader, isDense }: any) {
  let visible = tasks.sort((a: any, b: any) => a.priority - b.priority);
  let headerClass = 'p-4';
  if (isDense) {
    headerClass = 'p-2';
  }
  let emptyText = 'No tasks';
  if (filter === 'mine') {
    emptyText = 'You have no assigned tasks';
  }

  return (
    <div className={headerClass}>
      {showHeader && <h2>Tasks</h2>}
      {visible.length === 0 ? <p>{emptyText}</p> : visible.map((t: any, idx: number) => (
        <div key={idx} onClick={() => selectTask(t.id)}>{t.title}</div>
      ))}
    </div>
  );
}

// ✅ AFTER (Pure selector, lookup map, early return, semantic button, stable key)
const EMPTY_MESSAGES: Record<TaskFilter, string> = {
  all: 'No tasks',
  mine: 'You have no assigned tasks',
};

const selectSortedTasks = (tasks: readonly Task[]): Task[] =>
  tasks.toSorted((a, b) => a.priority - b.priority);

export function TaskPanel({
  tasks,
  filter,
  density = 'comfortable',
  header,
  onSelectTask,
}: TaskPanelProps) {
  const sortedTasks = selectSortedTasks(tasks);
  const paddingClass = density === 'compact' ? 'p-2' : 'p-4';

  if (sortedTasks.length === 0) {
    return (
      <section className={paddingClass}>
        {header}
        <p>{EMPTY_MESSAGES[filter]}</p>
      </section>
    );
  }

  return (
    <section className={paddingClass}>
      {header}
      <ul>
        {sortedTasks.map((task) => (
          <li key={task.id}>
            <button type="button" onClick={() => onSelectTask(task.id)}>
              {task.title}
            </button>
          </li>
        ))}
      </ul>
    </section>
  );
}
```

### Diff 2: Procedural `useEffect` Chain $\to$ Functional Core + Imperative Shell
```tsx
// ❌ BEFORE ([P1] Derived state synced in useEffect + boolean soup)
const [items, setItems] = useState<CartItem[]>([]);
const [tax, setTax] = useState(0);
const [isLoading, setIsLoading] = useState(false);
const [isError, setIsError] = useState(false);

useEffect(() => {
  setTax(items.reduce((sum, i) => sum + i.price, 0) * 0.08);
}, [items]);

// ✅ AFTER (Pure render derivation + discriminated union state at event boundary)
const subtotal = items.reduce((sum, i) => sum + i.price, 0);
const tax = subtotal * 0.08;
// Checkout state modeled as: { status: 'idle' } | { status: 'submitting' } | { status: 'error'; message: string }
```

### Diff 3: Prop Drilling Hell $\to$ Inversion of Control (`children` & Named Slots)
```tsx
// ❌ BEFORE ([P1] Trampoline props threaded through AppShell -> HeaderBar -> UserMenu)
function Page({ user, onLogout }: Props) {
  return <AppShell user={user} onLogout={onLogout}><Content /></AppShell>;
}
function AppShell({ user, onLogout, children }: ShellProps) {
  return <div><HeaderBar user={user} onLogout={onLogout} />{children}</div>;
}

// ✅ AFTER (Inversion of Control via slot prop; AppShell & HeaderBar stay domain-agnostic)
function Page({ user, onLogout }: Props) {
  return (
    <AppShell header={<HeaderBar right={<UserMenu user={user} onLogout={onLogout} />} />}>
      <Content />
    </AppShell>
  );
}
```

