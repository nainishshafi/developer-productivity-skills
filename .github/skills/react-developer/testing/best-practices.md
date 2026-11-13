# React Testing Strategy, Trophy & Best Practices

Comprehensive testing guidance for modern React applications (React 18 & 19) using **Vitest**, **React Testing Library (RTL)**, and **Mock Service Worker (MSW v2)**.

---

## 1. The Frontend Testing Trophy & Decision Matrix

Focus testing effort on realistic component integration tests rather than brittle shallow unit tests or slow full-browser E2E suites for every branch.

| Layer | Tools | Scope & Speed | What to Test Here |
|---|---|---|---|
| **Static Analysis** | TypeScript (`strict`), ESLint (`react-hooks`, `jsx-a11y`) | Instant (IDE/CI) | Props contracts, hook dependency rules, missing alt/ARIA attributes |
| **Pure Unit Tests** | Vitest / Jest | Sub-millisecond | Formatters, reducers, Zod schemas, complex state selectors, math/date helpers |
| **Component & Hook Integration** | Vitest + React Testing Library + `userEvent` + MSW v2 | Fast (~5–50 ms/test) | Observable DOM behavior, form validation, custom hooks, TanStack Query/Zustand flows, loading/error states |
| **End-to-End Browser** | Playwright ([`playwright-bdd-tester`](file:///.github/skills/playwright-bdd-tester/SKILL.md)) | Seconds | Auth cookies/redirects, multi-page navigation, streaming RSC hydration, CSS layout/scroll virtualization |

---

## 2. Accessible Query Priority & Query Variants

Query the DOM the way a user or screen reader finds elements—never by brittle CSS classes or internal DOM structure:

1. **`getByRole`** *(Preferred)*: `screen.getByRole('button', { name: /save changes/i })` — simultaneously verifies interactive semantics and accessible naming.
2. **`getByLabelText`**: Form controls (`input`, `select`, `textarea`) associated via `<label>`.
3. **`getByPlaceholderText`**: Only when no `<label>` exists.
4. **`getByText`**: Non-interactive text content (headings, paragraphs, status banners).
5. **`getByDisplayValue`**: Current value of filled form inputs.
6. **`getByTestId`** *(Last Resort)*: Dynamic IDs or non-semantic containers where accessible roles do not apply.

### Choosing the Right Query Prefix (`getBy` vs `queryBy` vs `findBy`)

| Query Variant | Missing Element | Async Waiting | Use Case |
|---|---|---|---|
| **`getBy*` / `getAllBy*`** | Throws immediately | No | Element is already present synchronously |
| **`queryBy*` / `queryAllBy*`** | Returns `null` / `[]` | No | **Only** for asserting non-existence (`expect(screen.queryByRole('alert')).not.toBeInTheDocument()`) |
| **`findBy*` / `findAllBy*`** | Rejects after timeout | Yes (polls DOM) | Element appears after async fetch, state update, or `<Suspense>` resolution |

---

## 3. Realistic User Interaction (`@testing-library/user-event`)

Always prefer `userEvent.setup()` over raw `fireEvent`. `userEvent` simulates full browser event sequences (`pointerDown` $\to$ `focus` $\to$ `click`, keystrokes, tab order, disabled-button guards) rather than dispatching a single synthetic DOM event.

```tsx
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { LoginForm } from './LoginForm';

test('submits credentials and shows accessible validation errors', async () => {
  const user = userEvent.setup();
  const onSubmit = vi.fn();
  render(<LoginForm onSubmit={onSubmit} />);

  // Trigger client validation first
  await user.click(screen.getByRole('button', { name: /sign in/i }));
  expect(screen.getByRole('alert')).toHaveTextContent(/email is required/i);
  expect(onSubmit).not.toHaveBeenCalled();

  // Fill fields via keyboard typing and submit
  await user.type(screen.getByLabelText(/email/i), 'alice@example.com');
  await user.type(screen.getByLabelText(/password/i), 'correct-horse-battery');
  await user.click(screen.getByRole('button', { name: /sign in/i }));

  expect(onSubmit).toHaveBeenCalledWith({
    email: 'alice@example.com',
    password: 'correct-horse-battery',
  });
});
```

- **File Uploads**: Use `await user.upload(screen.getByLabelText(/upload avatar/i), file)` instead of mutating `input.files`.
- **Keyboard Navigation**: Use `await user.tab()` and `await user.keyboard('{Escape}')` to verify focus order and modal dismissal.

---

## 4. Testing Custom Hooks with `renderHook`

Test simple hooks indirectly through the components that use them. Reach for `renderHook` when building shared library hooks that manage complex state transitions, context consumers (`wrapper`), prop changes (`rerender`), or unmount cleanup (`unmount`).

```tsx
import { renderHook, act } from '@testing-library/react';
import { useEffect, useState } from 'react';

function useEventListenerCount(target: EventTarget) {
  const [count, setCount] = useState(0);
  useEffect(() => {
    const onPing = () => setCount((c) => c + 1);
    target.addEventListener('ping', onPing);
    return () => target.removeEventListener('ping', onPing);
  }, [target]);
  return count;
}

test('subscribes to events and removes listener on unmount', () => {
  const target = new EventTarget();
  const { result, unmount } = renderHook(() => useEventListenerCount(target));

  act(() => {
    target.dispatchEvent(new Event('ping'));
  });
  expect(result.current).toBe(1);

  unmount();

  // Dispatching after unmount must not trigger state updates or warnings
  target.dispatchEvent(new Event('ping'));
  expect(result.current).toBe(1);
});
```

---

## 5. Network Boundary Mocking with MSW v2 (`msw/node`)

Never stub `global.fetch` or mock Axios internals per test—doing so bypasses URL parsing, HTTP status handling, and serialization bugs. Intercept traffic at the HTTP boundary using **Mock Service Worker (MSW v2)**:

```typescript
// tests/mocks/server.ts
import { http, HttpResponse } from 'msw';
import { setupServer } from 'msw/node';

export const handlers = [
  http.get('/api/users/:id', ({ params }) => {
    return HttpResponse.json({ id: params.id, name: 'Alice', role: 'admin' });
  }),
];

export const server = setupServer(...handlers);
```

```typescript
// tests/setup.ts
import '@testing-library/jest-dom/vitest';
import { afterAll, afterEach, beforeAll } from 'vitest';
import { server } from './mocks/server';

// Fail tests loudly on unexpected/unmocked network calls
beforeAll(() => server.listen({ onUnhandledRequest: 'error' }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());
```

### Per-Test Error & Latency Overrides
```tsx
import { http, HttpResponse, delay } from 'msw';
import { server } from '../mocks/server';

test('displays retry banner when API returns 503', async () => {
  server.use(
    http.get('/api/users/:id', async () => {
      await delay(50);
      return HttpResponse.json({ error: 'Upstream unavailable' }, { status: 503 });
    })
  );

  render(<UserProfile userId="42" />);
  expect(await screen.findByRole('alert')).toHaveTextContent(/unavailable/i);
});
```

---

## 6. Fake Timers + `userEvent` Integration

Using `vi.useFakeTimers()` with default `userEvent.setup()` causes tests to hang because `userEvent` schedules internal macrotasks. Always wire `advanceTimers` explicitly:

```tsx
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, expect, test, vi } from 'vitest';

beforeEach(() => vi.useFakeTimers());
afterEach(() => vi.useRealTimers());

test('debounces search query by 300ms before calling API', async () => {
  const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
  const onSearch = vi.fn();
  render(<SearchInput onSearch={onSearch} delayMs={300} />);

  await user.type(screen.getByRole('searchbox'), 'react');
  expect(onSearch).not.toHaveBeenCalled();

  vi.advanceTimersByTime(300);
  expect(onSearch).toHaveBeenCalledTimes(1);
  expect(onSearch).toHaveBeenCalledWith('react');
});
```

---

## 7. React Testing Anti-Patterns Checklist

1. **Snapshot Bloat (`toMatchSnapshot`)**: Large JSX snapshots pass blindly on refactors and fail on trivial class changes. Assert specific visible text, roles, and attributes instead.
2. **Mocking Child Components Unnecessarily**: Mocking sibling/child UI components hides broken prop wiring and ARIA regressions. Render real child trees unless a child embeds a heavy canvas/WebGL/video widget.
3. **Redundant `act()` Wrapping**: RTL `render`, `userEvent`, and `findBy*` already wrap updates in `act()`. Manual `act()` is only needed for imperative hook mutations or external event emitters.
4. **Testing Internal State / CSS Classes**: Never assert React state hooks directly or `expect(el).toHaveClass('bg-red-500')` to prove an error occurred; assert `role="alert"` or `aria-invalid="true"`.
5. **Cross-Verify Generated Tests**: Run [`scan-halucinated-tests`](file:///.github/skills/scan-halucinated-tests/SKILL.md) to verify imported component names, props, and API endpoints match real source symbols.
