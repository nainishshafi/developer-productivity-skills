# Component, State (Query/Zustand), React 19 & RSC Testing Patterns

Concrete testing recipes for provider wrappers, TanStack Query caches, Zustand stores, React 19 form actions, `<Suspense>`/`<ErrorBoundary>`, Next.js Server Components, and automated accessibility checks.

---

## 1. Reusable `renderWithProviders` Test Harness

Never share a singleton `QueryClient` across tests—cached entries and background retries will leak state and cause flaky ordering bugs. Create a fresh `QueryClient` per render with `retry: false` and `gcTime: 0`.

```tsx
// tests/test-utils.tsx
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, type RenderOptions } from '@testing-library/react';
import type { ReactElement, ReactNode } from 'react';
import { MemoryRouter, type MemoryRouterProps } from 'react-router-dom';

interface ProviderOptions extends Omit<RenderOptions, 'wrapper'> {
  initialEntries?: MemoryRouterProps['initialEntries'];
}

export function createTestQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false, gcTime: 0 },
      mutations: { retry: false },
    },
  });
}

export function renderWithProviders(
  ui: ReactElement,
  { initialEntries = ['/'], ...renderOptions }: ProviderOptions = {}
) {
  const queryClient = createTestQueryClient();

  function Wrapper({ children }: { children: ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={initialEntries}>{children}</MemoryRouter>
      </QueryClientProvider>
    );
  }

  return {
    queryClient,
    ...render(ui, { wrapper: Wrapper, ...renderOptions }),
  };
}
```

---

## 2. Testing TanStack Query & Optimistic Rollbacks

Pair `renderWithProviders` with MSW v2 overrides to test loading $\to$ success $\to$ optimistic update $\to$ server rollback:

```tsx
import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { server } from '../mocks/server';
import { renderWithProviders } from '../test-utils';
import { TodoList } from './TodoList';

test('rolls back optimistic toggle when PATCH fails', async () => {
  const user = userEvent.setup();
  server.use(
    http.get('/api/todos', () =>
      HttpResponse.json([{ id: '1', title: 'Write tests', completed: false }])
    ),
    http.patch('/api/todos/1', () =>
      HttpResponse.json({ message: 'Server error' }, { status: 500 })
    )
  );

  renderWithProviders(<TodoList />);

  const checkbox = await screen.findByRole('checkbox', { name: /write tests/i });
  expect(checkbox).not.toBeChecked();

  await user.click(checkbox);

  // Optimistic update flips immediately, then rolls back after 500 + error alert
  expect(await screen.findByRole('alert')).toHaveTextContent(/failed to update/i);
  expect(screen.getByRole('checkbox', { name: /write tests/i })).not.toBeChecked();
});
```

---

## 3. Testing Zustand Stores Deterministically

Run component tests against the **real** Zustand store instead of mocking `useStore` hooks, and reset the store snapshot between tests:

```typescript
// stores/cartStore.test.ts
import { beforeEach, expect, test } from 'vitest';
import { useCartStore } from './cartStore';

const initialState = useCartStore.getInitialState();

beforeEach(() => {
  // Replace state completely (second arg `true`) while preserving store actions
  useCartStore.setState(initialState, true);
});

test('adds item and computes total price', () => {
  useCartStore.getState().addItem({ id: 'sku-1', price: 25, qty: 2 });
  expect(useCartStore.getState().items).toHaveLength(1);
  expect(useCartStore.getState().total()).toBe(50);
});
```

---

## 4. Testing React 19 Actions, `<Suspense>`, and `<ErrorBoundary>`

### Form Actions (`useActionState` / `useOptimistic`)
Test pending states by controlling an unresolved promise inside the mocked action or MSW handler, then resolving it:

```tsx
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ProfileNameForm } from './ProfileNameForm';

test('disables submit button while action is pending and renders server result', async () => {
  const user = userEvent.setup();
  let resolveAction!: (msg: string) => void;
  const updateName = vi.fn(
    () => new Promise<string>((res) => { resolveAction = res; })
  );

  render(<ProfileNameForm action={updateName} />);

  await user.type(screen.getByLabelText(/display name/i), 'Ada');
  await user.click(screen.getByRole('button', { name: /save/i }));

  expect(screen.getByRole('button', { name: /saving/i })).toBeDisabled();

  resolveAction('Saved Ada');
  expect(await screen.findByText('Saved Ada')).toBeInTheDocument();
});
```

### `<Suspense>` & `<ErrorBoundary>` Fallbacks
- **`<Suspense>`**: Assert fallback renders first (`screen.getByText(/loading/i)`), then await `waitForElementToBeRemoved(() => screen.queryByText(/loading/i))` or `await screen.findByText(...)`.
- **`<ErrorBoundary>`**: React logs caught boundary errors to `console.error`. Spy and silence `console.error` *only inside that test* and restore it immediately via `vi.restoreAllMocks()` so real failures are never hidden.

```tsx
test('renders ErrorBoundary fallback when child throws', () => {
  const errorSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
  const Bomb = () => { throw new Error('Boom'); };

  render(
    <AppErrorBoundary>
      <Bomb />
    </AppErrorBoundary>
  );

  expect(screen.getByRole('alert')).toHaveTextContent(/something went wrong/i);
  errorSpy.mockRestore();
});
```

---

## 5. Testing Next.js App Router, RSC & Server Actions

| Target | Recommended Test Strategy |
|---|---|
| **Async React Server Component (RSC)** | Invoke directly as an `async` function and pass resolved JSX to `render(...)` |
| **Client Component using `next/navigation`** | Mock `useRouter`, `useSearchParams`, and `usePathname` in test setup (`vi.mock('next/navigation', ...)`) |
| **Server Actions (`'use server'`)** | Test as pure async server functions with in-memory/test DB fixtures, validating `FormData` parsing, auth checks, and `revalidatePath` calls |
| **Streaming RSC, Cookies, Middleware & Redirects** | Test in a real browser via Playwright ([`playwright-bdd-tester`](file:///.github/skills/playwright-bdd-tester/SKILL.md)) |

```tsx
// app/users/[id]/page.test.tsx
import { render, screen } from '@testing-library/react';
import { expect, test, vi } from 'vitest';
import UserProfilePage from './page';

vi.mock('@/lib/users', () => ({
  getUserById: vi.fn().mockResolvedValue({ id: '1', name: 'Grace Hopper' }),
}));

test('renders async Server Component output', async () => {
  const jsx = await UserProfilePage({ params: Promise.resolve({ id: '1' }) });
  render(jsx);

  expect(screen.getByRole('heading', { name: /grace hopper/i })).toBeInTheDocument();
});
```

---

## 6. Automated Accessibility (`vitest-axe`) & Dialog Focus Contracts

Add automated WCAG checks to interactive components (forms, dialogs, menus, tabs) alongside keyboard interaction tests:

```tsx
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { axe } from 'vitest-axe';
import { ConfirmModal } from './ConfirmModal';

test('modal has no axe violations and closes on Escape', async () => {
  const user = userEvent.setup();
  const onClose = vi.fn();

  const { container } = render(
    <ConfirmModal open title="Delete workspace?" onClose={onClose} onConfirm={vi.fn()} />
  );

  const dialog = screen.getByRole('dialog', { name: /delete workspace\?/i });
  expect(dialog).toHaveAttribute('aria-modal', 'true');
  expect(await axe(container)).toHaveNoViolations();

  await user.keyboard('{Escape}');
  expect(onClose).toHaveBeenCalledTimes(1);
});
```

