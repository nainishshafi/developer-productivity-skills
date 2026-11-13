# Functional Programming Paradigm in React & Anti-Procedural Patterns

React is built on a declarative, functional mental model: **$\text{UI} = f(\text{state})$**. Writing procedural code inside React components—mutating arrays in place, reassigning `let` variables through branching ladders, orchestrating step-by-step state mutations across `useEffect` chains, or issuing imperative DOM/control-flow steps—fights React's reconciliation engine and produces subtle stale-render and double-execution bugs.

---

## 1. Procedural vs. Functional React (Decision Matrix)

| Dimension | Procedural Anti-Pattern (Imperative) | Functional React Idiom (Declarative) | Why It Matters |
|---|---|---|---|
| **Render Computation** | Mutating props/arrays (`items.sort()`, `list.push(...)`) inside render | Pure expressions & ES2023 immutable methods (`items.toSorted(...)`) | Preserves referential transparency; prevents React StrictMode double-render bugs and broken `Object.is` memoization |
| **Branching & Mapping** | `let label = ''; if (...) { label = ... } else ...` reassignment chains | Pure lookup maps (`STATUS_VIEW[status]`) or exhaustive `switch` helpers | Eliminates uninitialized/partially overwritten variable states |
| **Collection Processing** | `for` loops with `result.push(...)` inside JSX components | Extracted pure selector functions (`filter`, `map`, `Object.groupBy`, `reduce`) | Keeps components declarative and lets domain transformations be unit-tested without rendering a DOM |
| **State Transitions** | Multiple `useState` flags mutated across sequential `useEffect` hooks | **Functional Core** (`(state, action) => nextState` reducer) + **Imperative Shell** (event handlers) | Eliminates impossible state combinations and cascading re-render waterfalls |
| **Side Effects** | Mixing `fetch`, `localStorage`, and analytics calls inside render or effect chains | Isolate side effects strictly at event boundaries (`onClick`/`onSubmit`) or external-sync hooks | Keeps rendering deterministic and predictable under concurrent rendering |
| **State Modeling** | Boolean soup (`isLoading`, `isError`, `isSuccess`, `data`) | Discriminated union ADTs (`{ status: 'idle' \| 'loading' \| 'success' \| 'error' }`) | Makes invalid states unrepresentable at compile time |

---

## 2. Referential Transparency & Pure Render Functions

In functional programming, a pure function given the same inputs always returns the same output and causes **zero observable side effects**. React relies on this invariant: in development StrictMode and Concurrent rendering, React may invoke component functions twice or discard in-progress renders.

### Ban In-Place Mutations During Render or State Updates
In JavaScript, `.sort()`, `.reverse()`, `.splice()`, and `.push()` **mutate the array in place** and return the *same* array reference—silently corrupting props and tricking React into skipping re-renders (`Object.is(prev, next) === true`).

```tsx
// ❌ PROCEDURAL ANTI-PATTERN: Mutates props array in place during render
export function Leaderboard({ players }: { players: Player[] }) {
  const ranked = players.sort((a, b) => b.score - a.score); // Mutates caller's array!
  ranked.push({ id: 'summary', name: 'Average', score: 50 }); // Appends duplicate on every render!

  return (
    <ul>
      {ranked.map((p) => <li key={p.id}>{p.name}: {p.score}</li>)}
    </ul>
  );
}

// ✅ FUNCTIONAL REACT IDIOM: Pure, non-mutating ES2023 transforms
export function Leaderboard({ players }: { players: readonly Player[] }) {
  const ranked = players.toSorted((a, b) => b.score - a.score);

  return (
    <ul>
      {ranked.map((p) => <li key={p.id}>{p.name}: {p.score}</li>)}
    </ul>
  );
}
```

### Prefer ES2023 Non-Mutating Array Operations
| Mutating (Ban in React) | Immutable Functional Replacement |
|---|---|
| `arr.sort(cmp)` | `arr.toSorted(cmp)` |
| `arr.reverse()` | `arr.toReversed()` |
| `arr.splice(i, count, ...items)` | `arr.toSpliced(i, count, ...items)` |
| `arr[i] = nextVal` | `arr.with(i, nextVal)` |
| `arr.push(item)` | `[...arr, item]` |
| `arr.pop()` / `arr.shift()` | `arr.slice(0, -1)` / `arr.slice(1)` |

---

## 3. Eliminating Procedural `let` Accumulators & Branching Ladders

Procedural code relies on declaring mutable `let` bindings and overwriting them conditionally. Replace mutable `let` ladders with **data-driven lookup tables** or **pure expression helpers**.

```tsx
// ❌ PROCEDURAL ANTI-PATTERN: Mutable let accumulator + imperative branching
function OrderBadge({ status, isUrgent }: { status: OrderStatus; isUrgent: boolean }) {
  let color = 'gray';
  let text = 'Unknown';
  if (status === 'pending') {
    color = 'yellow';
    text = isUrgent ? 'Pending (Rush)' : 'Pending';
  } else if (status === 'shipped') {
    color = 'blue';
    text = 'Shipped';
  } else if (status === 'delivered') {
    color = 'green';
    text = 'Delivered';
  }
  return <span className={`badge-${color}`}>{text}</span>;
}

// ✅ FUNCTIONAL REACT IDIOM: Declarative lookup table + pure formatting expression
const ORDER_BADGE_CONFIG: Record<OrderStatus, { color: string; label: string }> = {
  pending: { color: 'yellow', label: 'Pending' },
  shipped: { color: 'blue', label: 'Shipped' },
  delivered: { color: 'green', label: 'Delivered' },
  cancelled: { color: 'red', label: 'Cancelled' },
};

export function OrderBadge({ status, isUrgent }: { status: OrderStatus; isUrgent: boolean }) {
  const { color, label } = ORDER_BADGE_CONFIG[status];
  const displayLabel = status === 'pending' && isUrgent ? `${label} (Rush)` : label;
  return <span className={`badge-${color}`}>{displayLabel}</span>;
}
```

### Exhaustive Matching Over Discriminated Unions
```tsx
function assertNever(value: never): never {
  throw new Error(`Unhandled discriminated union member: ${JSON.stringify(value)}`);
}

function renderPaymentState(state: PaymentState) {
  switch (state.status) {
    case 'idle':
      return <PayButton />;
    case 'processing':
      return <Spinner label="Authorizing..." />;
    case 'succeeded':
      return <ReceiptBanner receiptId={state.receiptId} />;
    case 'failed':
      return <ErrorBanner message={state.error} />;
    default:
      return assertNever(state);
  }
}
```

---

## 4. Declarative Collection Pipelines Over Imperative `for` Loops

Never mix imperative `for` loops, temporary arrays, and JSX rendering inside a component body. Extract pure domain transformations outside the component as composable functions:

```tsx
// ❌ PROCEDURAL ANTI-PATTERN: Imperative loop accumulation inside component
export function TeamDirectory({ members, minScore }: { members: Member[]; minScore: number }) {
  const grouped: Record<string, Member[]> = {};
  for (let i = 0; i < members.length; i++) {
    const m = members[i];
    if (!m.active || m.score < minScore) continue;
    if (!grouped[m.department]) {
      grouped[m.department] = [];
    }
    grouped[m.department].push(m);
  }
  // ...imperative Object.keys loop to build JSX
}

// ✅ FUNCTIONAL REACT IDIOM: Pure selector pipeline outside the component
const selectActiveQualifiedByDept = (members: readonly Member[], minScore: number) =>
  Object.groupBy(
    members
      .filter((m) => m.active && m.score >= minScore)
      .toSorted((a, b) => a.name.localeCompare(b.name)),
    (m) => m.department
  );

export function TeamDirectory({ members, minScore }: { members: readonly Member[]; minScore: number }) {
  const byDept = selectActiveQualifiedByDept(members, minScore);

  return (
    <div className="space-y-4">
      {Object.entries(byDept).map(([dept, deptMembers = []]) => (
        <DepartmentSection key={dept} title={dept} members={deptMembers} />
      ))}
    </div>
  );
}
```

*(Note: Pure functions like `selectActiveQualifiedByDept` are trivial to unit test in sub-millisecond Vitest tests with zero DOM setup.)*

---

## 5. Functional Core, Imperative Shell (Eliminating Procedural `useEffect` Chains)

The most damaging procedural anti-pattern in React is treating `useEffect` like sequential imperative steps: *"Step 1: set `submitted = true` $\to$ Step 2: `useEffect` watches `submitted` and sets `discount` $\to$ Step 3: `useEffect` watches `discount` and calls `fetch` $\to$ Step 4: `useEffect` watches `response` and sets `redirect`."*

Apply **Functional Core, Imperative Shell**:
- **Functional Core**: Pure functions & `useReducer` transitions computing `(state, event) => nextState` and derived totals with zero side effects.
- **Imperative Shell**: Thin event handlers (`handleCheckout`) that execute I/O (`fetch`) and dispatch pure outcome actions (`SUCCEEDED` / `FAILED`).

```tsx
// ❌ PROCEDURAL ANTI-PATTERN: Sequential "Rube Goldberg" useEffect state mutations
function CheckoutBad({ cart }: { cart: CartItem[] }) {
  const [coupon, setCoupon] = useState('');
  const [discount, setDiscount] = useState(0);
  const [total, setTotal] = useState(0);
  const [submitted, setSubmitted] = useState(false);

  useEffect(() => {
    setDiscount(coupon === 'SAVE10' ? 0.1 : 0); // Extra render pass #1
  }, [coupon]);

  useEffect(() => {
    const subtotal = cart.reduce((sum, item) => sum + item.price * item.qty, 0);
    setTotal(subtotal * (1 - discount)); // Extra render pass #2
  }, [cart, discount]);

  useEffect(() => {
    if (submitted) void submitOrder(total); // Fires implicitly from effect!
  }, [submitted, total]);
}

// ✅ FUNCTIONAL CORE + IMPERATIVE SHELL: Pure derivation + explicit event boundary
function calculateOrderSummary(cart: readonly CartItem[], coupon: string) {
  const subtotal = cart.reduce((sum, item) => sum + item.price * item.qty, 0);
  const discountRate = coupon.trim().toUpperCase() === 'SAVE10' ? 0.1 : 0;
  return {
    subtotal,
    discountAmount: subtotal * discountRate,
    total: subtotal * (1 - discountRate),
  };
}

export function Checkout({ cart }: { cart: readonly CartItem[] }) {
  const [coupon, setCoupon] = useState('');
  const [submission, setSubmission] = useState<'idle' | 'pending' | 'error'>('idle');

  // Functional Core: pure derivation during render (0 effects, 0 extra render passes)
  const summary = calculateOrderSummary(cart, coupon);

  // Imperative Shell: side effect runs explicitly when the user clicks Submit
  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmission('pending');
    try {
      await submitOrder({ items: cart, total: summary.total });
      setSubmission('idle');
    } catch {
      setSubmission('error');
    }
  }

  return (
    <form onSubmit={handleSubmit}>
      <input value={coupon} onChange={(e) => setCoupon(e.target.value)} aria-label="Coupon" />
      <p>Total: ${summary.total.toFixed(2)}</p>
      {submission === 'error' && <p role="alert">Checkout failed. Please retry.</p>}
      <button type="submit" disabled={submission === 'pending'}>Place Order</button>
    </form>
  );
}
```

---

## 6. Pragmatic FP Anti-Bloat Guardrail

Apply functional programming to make React code **simpler, purer, and easier to trace**—never introduce academic FP ceremony that hurts readability:

1. **Avoid Heavy FP Monad Wrappers (`fp-ts` / Deep `pipe` Chains) Unless Already Standard**: For standard React apps, native TypeScript discriminated unions, pure helper functions, and array methods (`filter`/`map`/`toSorted`) deliver 95% of FP safety with zero learning curve.
2. **Keep Transformations Flat & Named**: Extract a readable named helper (`selectVisibleUsers`) rather than nesting 5 anonymous `.reduce()`/`.flatMap()` callbacks inside JSX.
3. **Reserve `memo` for Measured Hot Paths**: Pure functional components are cheap to execute; only add `React.memo` / `useMemo` when profiling shows measurable > 1 ms render bottlenecks.

