# Flakiness Elimination, Auto-Waiting & Network Interception

Techniques for building rock-solid, deterministic Playwright BDD test suites that never fail spuriously.

---

## 1. Auto-Waiting vs The Sleep Anti-Pattern

Playwright automatically performs **Actionability Checks** before performing any action (`click()`, `fill()`, `check()`):
- Element is attached to the DOM
- Element is visible in viewport
- Element is stable (not animating or sliding)
- Element receives pointer events (not obscured by modal overlay or spinner)
- Element is enabled

### ❌ Strict Rule: BAN `page.waitForTimeout()`
```typescript
// ❌ CRITICAL ANTI-PATTERN: Arbitrary sleep (causes flakiness & slows suite down)
await page.waitForTimeout(5000); // 5 seconds wasted on every run, still flakes under slow CI
await page.getByRole('button', { name: 'Submit' }).click();

// ✅ BEST PRACTICE: Playwright auto-waits for actionability automatically!
await page.getByRole('button', { name: 'Submit' }).click();
```

---

## 2. Web-First Assertions with Auto-Retry

Never extract boolean state and assert against primitives; always use Playwright's **Web-First Assertions**, which continuously poll the DOM until the condition is met or timeout expires.

```typescript
// ❌ WRONG: Non-retrying boolean check (fails instantly if animation is in progress)
const isVisible = await page.getByRole('dialog').isVisible();
expect(isVisible).toBe(true); // Immediate failure!

// ✅ RIGHT: Web-First Assertion (retries continuously up to expect timeout)
await expect(page.getByRole('dialog')).toBeVisible();
await expect(page.getByTestId('cart-badge')).toHaveText('3');
await expect(page.getByRole('button', { name: 'Submit' })).toBeEnabled();
```

---

## 3. Authentication State Reuse (`storageState`)

Logging in through the UI before every single Gherkin scenario slows test runs down by 10x. Use Playwright's `storageState` to log in once during setup, save session cookies/tokens to disk, and share state across scenarios:

```typescript
// tests/setup/auth.setup.ts
import { test as setup, expect } from '@playwright/test';

const authFile = 'playwright/.auth/user.json';

setup('authenticate user once', async ({ page }) => {
  await page.goto('/login');
  await page.getByLabel('Email').fill('user@example.com');
  await page.getByLabel('Password').fill('password123');
  await page.getByRole('button', { name: 'Sign In' }).click();

  await expect(page.getByTestId('user-avatar')).toBeVisible();

  // Save authenticated cookies and localStorage state
  await page.context().storageState({ path: authFile });
});
```

In `playwright.config.ts`, apply `storageState: 'playwright/.auth/user.json'` to projects requiring authenticated state.

---

## 4. Network Mocking & Interception (`page.route`)

Isolate your E2E browser tests from unstable third-party APIs or simulate error status codes:

```typescript
// Mock external payment gateway to guarantee fast, deterministic tests
When('the payment gateway responds with payment approved', async ({ page }) => {
  await page.route('**/api/v1/payments/charge', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ transactionId: 'TX-9988', status: 'CAPTURED' }),
    });
  });
});

// Simulate a 500 error from downstream service
When('the inventory service is temporarily unavailable', async ({ page }) => {
  await page.route('**/api/v1/inventory/**', async (route) => {
    await route.fulfill({ status: 503, body: 'Service Unavailable' });
  });
});
```
