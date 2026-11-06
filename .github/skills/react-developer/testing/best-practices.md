# React Testing Best Practices

Testing observable user behavior with React Testing Library and MSW (Mock Service Worker).

---

## 1. Test Observable Behavior, Not Implementation Details

Never test internal state, private hooks, or component instance variables. Test what the user sees and interacts with:

```tsx
// ❌ ANTI-PATTERN: Testing internal state
expect(wrapper.state('isOpen')).toBe(true);

// ✅ BEST PRACTICE: Test visible DOM output and accessible roles
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Accordion } from './Accordion';

test('expands accordion content on click', async () => {
  const user = userEvent.setup();
  render(
    <Accordion>
      <Accordion.Item id="item-1" title="FAQ Title">
        Hidden FAQ Answer
      </Accordion.Item>
    </Accordion>
  );

  expect(screen.queryByText(/hidden faq answer/i)).not.toBeInTheDocument();

  await user.click(screen.getByRole('button', { name: /faq title/i }));

  expect(screen.getByText(/hidden faq answer/i)).toBeInTheDocument();
});
```

---

## 2. Testing Custom Hooks with `renderHook`

```tsx
import { renderHook, act } from '@testing-library/react';
import { useCounter } from './useCounter';

test('increments counter value', () => {
  const { result } = renderHook(() => useCounter(0));

  expect(result.current.count).toBe(0);

  act(() => {
    result.current.increment();
  });

  expect(result.current.count).toBe(1);
});
```

---

## 3. Mock Service Worker (MSW) for API Contracts

Instead of stubbing `global.fetch` or mocking Axios instances with brittle return values, intercept network requests at the HTTP boundary with MSW:

```typescript
import { http, HttpResponse } from 'msw';
import { setupServer } from 'msw/node';

export const server = setupServer(
  http.get('/api/user', () => {
    return HttpResponse.json({ id: '1', name: 'Alice' });
  })
);
```

