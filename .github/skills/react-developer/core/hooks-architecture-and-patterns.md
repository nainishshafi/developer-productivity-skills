# React Hooks Architecture, React 19 Hooks & Custom Hook Patterns

Practical architectural guidance for React 18 & 19 built-in hooks, eliminating unnecessary `useEffect` chains, concurrent rendering hooks, and designing clean custom hook contracts.

---

## 1. React 18 & 19 Hooks Decision Matrix

| Hook | Primary Purpose | Anti-Pattern / When NOT to Use |
|---|---|---|
| **`useState`** | Independent local UI state (toggles, form drafts, modal open state) | Derived values from props/state, or 4+ interdependent booleans (`isLoading` + `isError`) |
| **`useReducer`** | Finite state machines with coupled transitions & discriminated actions | Simple single boolean or primitive toggle |
| **`useEffect`** | Synchronizing with **external systems** (network, timers, WebSockets, DOM observers) | Computing derived state, resetting state on prop change, or handling user click actions |
| **`useLayoutEffect`** | Synchronous DOM measurement/mutation *before* browser paint (tooltips, popovers) | Data fetching or heavy CPU logic (blocks visual painting; triggers SSR warning) |
| **`useRef`** | Mutable instance values across renders (`AbortController`, timer IDs, DOM nodes) without triggering re-renders | Storing UI state that should trigger a re-render when updated |
| **`useImperativeHandle`** | Exposing a minimal, explicit imperative API (`focus()`, `scrollTo()`) via `ref` | Exposing internal state getters/setters to bypass props |
| **`useMemo` / `useCallback`** | Referential stability for memoized children/`useEffect` deps, or expensive > 1 ms transforms | Wrapping trivial math, string formatting, or handlers on native DOM elements |
| **`useTransition`** | Marking state updates you *trigger* as non-urgent so typing/clicks stay responsive | Wrapping controlled `<input value={...}>` updates (causes typing lag) |
| **`useDeferredValue`** | Deferring re-renders of an expensive child tree fed by a prop/value you *receive* | Debouncing network requests (still triggers on every value unless paired with memoized query/debounce) |
| **`useSyncExternalStore`** | Subscribing safely to external stores/browser APIs (`navigator.onLine`, Redux/Zustand) without tearing | Internal React component state |
| **`useId`** | Generating SSR-safe unique IDs for `aria-labelledby`, `htmlFor`, and `aria-describedby` | List `key` props (always use stable entity IDs) |
| **`use()`** *(React 19)* | Reading Promises (with `<Suspense>`) or Context conditionally inside loops/`if` blocks | Creating promises inside render without caching/memoization (causes infinite re-suspend loops) |
| **`useActionState`** *(React 19)* | Managing form/async action state, `isPending`, and server/client validation errors | Simple synchronous local state |
| **`useFormStatus`** *(React 19)* | Reading pending status of a parent `<form action={...}>` from a child submit button | Called in the same component that renders `<form>` (must live in a child component) |
| **`useOptimistic`** *(React 19)* | Instant optimistic UI projection while an async Transition/Action is in flight, with automatic rollback | Permanent client state (reverts automatically once the action settles) |

---

## 2. State Hooks: Lazy Initialization & `useReducer` State Machines

### Lazy Initializers in `useState`
Passing a function reference (`() => ...`) executes only on initial mount instead of re-parsing JSON or reading `localStorage` on every re-render:

```tsx
// ❌ ANTI-PATTERN: Parses localStorage on every single render
const [prefs, setPrefs] = useState(() => JSON.parse(localStorage.getItem('prefs') ?? '{}')); // OK ONLY with arrow!
const [badPrefs] = useState(JSON.parse(localStorage.getItem('prefs') ?? '{}')); // Runs every render!

// ✅ BEST PRACTICE: Lazy initializer function
const [prefs, setPrefs] = useState<UserPrefs>(() => {
  const raw = typeof window !== 'undefined' ? localStorage.getItem('prefs') : null;
  return raw ? (JSON.parse(raw) as UserPrefs) : DEFAULT_PREFS;
});
```

### Discriminated-Union `useReducer` Over Boolean Soup
When multiple `useState` booleans can drift into impossible combinations (`isLoading: true` and `error: 'Failed'`), model explicit states with a discriminated union:

```tsx
type AsyncState<T> =
  | { status: 'idle' }
  | { status: 'loading' }
  | { status: 'success'; data: T }
  | { status: 'error'; message: string };

type Action<T> =
  | { type: 'START' }
  | { type: 'SUCCESS'; payload: T }
  | { type: 'ERROR'; message: string }
  | { type: 'RESET' };

function asyncReducer<T>(state: AsyncState<T>, action: Action<T>): AsyncState<T> {
  switch (action.type) {
    case 'START':
      return { status: 'loading' };
    case 'SUCCESS':
      return { status: 'success', data: action.payload };
    case 'ERROR':
      return { status: 'error', message: action.message };
    case 'RESET':
      return { status: 'idle' };
  }
}
```

---

## 3. "You Might Not Need an Effect" (`useEffect` Discipline)

`useEffect` is an escape hatch for synchronizing with external systems—**not** a general-purpose event bus or state-sync mechanism.

| Anti-Pattern (`useEffect` Misuse) | Correct React Idiom | Why |
|---|---|---|
| Computing derived values (`useEffect` calling `setTotal`) | Compute directly during render (`const total = ...`) | Eliminates redundant second render pass and stale intermediate frames |
| Resetting form/draft state when `userId` prop changes | Pass `key={userId}` on the component (`<ProfileEditor key={userId} />`) | React cleanly unmounts old state and mounts fresh state in one pass |
| Executing API mutations or analytics inside `useEffect([submitted])` | Execute directly inside the `onSubmit` / `onClick` event handler | Keeps cause-and-effect explicit and prevents accidental re-fires on StrictMode or re-renders |
| Adjusting state when a prop changes | Store the minimal source-of-truth ID (`selectedId`) and derive the item (`items.find(...)`) | Zero sync lag and zero cascading effects |

### Synchronous DOM Measurement with `useLayoutEffect`
Use `useLayoutEffect` *only* when measuring DOM geometry (`getBoundingClientRect()`) to position a tooltip, popover, or menu before the browser paints, preventing visual flicker:

```tsx
function Tooltip({ anchorRef, label }: { anchorRef: RefObject<HTMLElement | null>; label: string }) {
  const tipRef = useRef<HTMLDivElement>(null);
  const [coords, setCoords] = useState({ top: 0, left: 0 });

  useLayoutEffect(() => {
    const anchor = anchorRef.current;
    const tip = tipRef.current;
    if (!anchor || !tip) return;
    const rect = anchor.getBoundingClientRect();
    setCoords({ top: rect.bottom + 8, left: rect.left });
  }, [anchorRef, label]);

  return (
    <div ref={tipRef} role="tooltip" style={{ position: 'fixed', top: coords.top, left: coords.left }}>
      {label}
    </div>
  );
}
```

---

## 4. Concurrent Rendering Hooks (`useTransition` & `useDeferredValue`)

### `useTransition`: Keep Typing/Navigation Responsive During Heavy Updates
```tsx
import { useState, useTransition } from 'react';

export function FilterableCatalog({ items }: { items: CatalogItem[] }) {
  const [query, setQuery] = useState('');
  const [filtered, setFiltered] = useState(items);
  const [isPending, startTransition] = useTransition();

  function handleChange(nextQuery: string) {
    // Urgent: update the controlled input immediately
    setQuery(nextQuery);

    // Non-urgent: interruptible background render for heavy list filtering
    startTransition(() => {
      const q = nextQuery.toLowerCase();
      setFiltered(items.filter((item) => item.name.toLowerCase().includes(q)));
    });
  }

  return (
    <div>
      <input value={query} onChange={(e) => handleChange(e.target.value)} aria-label="Filter catalog" />
      {isPending && <span aria-live="polite">Updating results...</span>}
      <CatalogGrid items={filtered} />
    </div>
  );
}
```

### `useDeferredValue`: Defer Expensive Child Re-Renders on Props You Don't Own
When a parent passes a rapidly changing `query` prop into a heavy chart or virtualized table, defer the prop inside the child and memoize the heavy subtree (`React.memo`):

```tsx
const HeavyChart = memo(function HeavyChart({ query }: { query: string }) {
  // Expensive rendering skipped while deferredQuery lags behind urgent input updates
  return <ChartCanvas data={computeSeries(query)} />;
});

export function AnalyticsPanel({ query }: { query: string }) {
  const deferredQuery = useDeferredValue(query);
  const isStale = query !== deferredQuery;

  return (
    <div style={{ opacity: isStale ? 0.7 : 1 }}>
      <HeavyChart query={deferredQuery} />
    </div>
  );
}
```

---

## 5. React 19 Hooks & Modern Idioms

### `useActionState`, `useFormStatus` & `useOptimistic`
React 19 unifies async form mutations, pending indicators, and optimistic rollbacks without manual `try/catch/isSubmitting` boilerplate:

```tsx
'use client';
import { useActionState, useOptimistic } from 'react';
import { useFormStatus } from 'react-dom';

function SubmitButton() {
  // Must live in a child component rendered inside <form>
  const { pending } = useFormStatus();
  return (
    <button type="submit" disabled={pending}>
      {pending ? 'Posting...' : 'Post Comment'}
    </button>
  );
}

export function CommentThread({
  comments,
  postCommentAction,
}: {
  comments: Comment[];
  postCommentAction: (prevError: string | null, formData: FormData) => Promise<string | null>;
}) {
  const [optimisticComments, addOptimistic] = useOptimistic(
    comments,
    (state, body: string) => [...state, { id: `temp-${Date.now()}`, body, pending: true }]
  );

  const [error, formAction] = useActionState(async (prev: string | null, formData: FormData) => {
    const body = String(formData.get('body') ?? '').trim();
    if (!body) return 'Comment cannot be empty.';
    addOptimistic(body);
    return postCommentAction(prev, formData);
  }, null);

  return (
    <form action={formAction}>
      <ul>
        {optimisticComments.map((c) => (
          <li key={c.id} style={{ opacity: c.pending ? 0.6 : 1 }}>{c.body}</li>
        ))}
      </ul>
      <input name="body" aria-label="Comment" />
      {error && <p role="alert">{error}</p>}
      <SubmitButton />
    </form>
  );
}
```

### Reading Context & Cached Promises with `use()`
Unlike `useContext`, React 19's `use(Context)` can be called conditionally after early returns:

```tsx
import { use } from 'react';
import { ThemeContext } from './ThemeContext';

export function BrandBadge({ show }: { show: boolean }) {
  if (!show) return null; // Early return BEFORE reading context!
  const theme = use(ThemeContext);
  return <span className={theme.badgeClass}>Pro</span>;
}
```

### React 19 `ref` as a Standard Prop & Cleanup Functions
In React 19, function components accept `ref` directly in props—no `forwardRef` wrapper needed—and callback refs can return a cleanup function:

```tsx
export function AutoFocusInput({ ref, ...props }: React.ComponentProps<'input'>) {
  return <input ref={ref} {...props} />;
}

// Callback ref with React 19 cleanup return
<div
  ref={(node) => {
    if (!node) return;
    const observer = new ResizeObserver(() => { /* measure */ });
    observer.observe(node);
    return () => observer.disconnect();
  }}
/>
```

---

## 6. Custom Hook Engineering & Contract Design

1. **Tuple vs. Object Return Contracts**:
   - Return a **tuple** (`[open, toggle]`) when the hook mirrors `useState` (2 values, caller renames freely).
   - Return a **named object** (`{ data, isPending, error, refetch }`) when returning 3+ values or optional fields so callers destructure only what they need without positional errors.
2. **Stabilize Callback Parameters (Latest-Ref Pattern)**:
   - When writing reusable timer/subscription hooks (`useInterval(cb, delay)`), avoid forcing consumers to wrap `cb` in `useCallback` or triggering teardown/re-subscribe loops on every render:

```tsx
import { useEffect, useRef } from 'react';

export function useInterval(callback: () => void, delayMs: number | null) {
  const latestCallback = useRef(callback);
  latestCallback.current = callback; // Keep ref fresh on render without resetting timer

  useEffect(() => {
    if (delayMs === null) return;
    const id = setInterval(() => latestCallback.current(), delayMs);
    return () => clearInterval(id);
  }, [delayMs]);
}
```

3. **Respect the Rules of Hooks**: Call hooks strictly at the top level of React components or other `use*` custom hooks (never inside loops, conditions, or plain utility functions, except `use()` in React 19).
4. **Anti-Bloat Guardrail**: Do not extract a custom hook that merely wraps a single `useState` call with zero shared effects or invariant logic.

