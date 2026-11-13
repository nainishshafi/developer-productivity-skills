# Playwright Configuration & Multi-Language Setup

Tooling setups, configuration files, and project layouts for Microsoft Playwright across TypeScript/Node.js, Python, Java, and C# / .NET.

---

## 1. TypeScript / Node.js (`@playwright/test`)

### Project Directory Layout
```text
tests/
├── e2e/                         # Native Playwright .spec.ts test files
│   ├── auth.spec.ts
│   └── checkout.spec.ts
├── pages/                       # Page Object Models
│   ├── BasePage.ts
│   ├── LoginPage.ts
│   └── CheckoutPage.ts
├── fixtures/                    # Custom Playwright test fixtures & state
│   └── testFixtures.ts
├── setup/                       # Auth setup projects (storageState)
│   └── auth.setup.ts
└── playwright.config.ts         # Playwright configuration
```

### Configuration: `playwright.config.ts`
```typescript
import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './tests/e2e',
  timeout: 30_000,
  expect: { timeout: 5_000 },
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 4 : undefined,
  reporter: [
    ['html', { open: 'never' }],
    ['json', { outputFile: 'test-results/results.json' }],
    ['list'],
  ],
  use: {
    baseURL: process.env.BASE_URL || 'http://localhost:3000',
    trace: 'on-first-retry',       // Record full zip trace on failed attempts
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
    actionTimeout: 10_000,
  },
  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
    { name: 'firefox', use: { ...devices['Desktop Firefox'] } },
    { name: 'webkit', use: { ...devices['Desktop Safari'] } },
  ],
});
```

---

## 2. Python (`pytest-playwright`)

For Python codebases, use the official `pytest-playwright` plugin:

### Configuration: `pytest.ini`
```ini
[pytest]
testpaths = tests
addopts = --browser chromium --screenshot only-on-failure --tracing retain-on-failure
```

### Test Spec (`tests/test_checkout.py`):
```python
from playwright.sync_api import Page, expect

def test_checkout_flow(page: Page):
    page.goto("/checkout")
    page.get_by_label("Shipping Address").fill("123 Main St")
    page.get_by_role("button", name="Place Order").click()
    expect(page.getByRole("dialog", name="Order Placed")).to_be_visible()
```

---

## 3. Java (`com.microsoft.playwright`)

### Dependencies (`pom.xml`):
```xml
<dependencies>
    <dependency>
        <groupId>com.microsoft.playwright</groupId>
        <artifactId>playwright</artifactId>
        <version>1.49.0</version>
        <scope>test</scope>
    </dependency>
</dependencies>
```

---

## 4. C# / .NET (`Microsoft.Playwright`)

### NuGet Packages (`.csproj`):
```xml
<ItemGroup>
  <PackageReference Include="Microsoft.Playwright" Version="1.49.0" />
  <PackageReference Include="Microsoft.Playwright.NUnit" Version="1.49.0" />
</ItemGroup>
```

