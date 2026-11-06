# Playwright BDD Configuration & Architecture

Tooling setups, configuration files, and project layouts for integrating Gherkin feature files with the native Playwright test runner.

---

## 1. Modern Architecture: `playwright-bdd` (TypeScript / Node.js)

The recommended standard for TypeScript is **`playwright-bdd`**. Unlike traditional standalone Cucumber, `playwright-bdd` translates Gherkin scenarios into native `@playwright/test` specs at build time.
- **Full Playwright Features**: Native parallel execution, worker isolation, sharding, HTML reports, and trace recording.
- **Playwright Fixtures**: Directly access `page`, `request`, `context`, and custom fixtures in Gherkin step definitions.

### Project Directory Layout
```text
tests/
├── features/                    # Pure Gherkin .feature specifications
│   ├── auth.feature
│   └── checkout.feature
├── steps/                       # Gherkin step definitions
│   ├── auth.steps.ts
│   └── checkout.steps.ts
├── pages/                       # Page Object Models
│   ├── BasePage.ts
│   ├── LoginPage.ts
│   └── CheckoutPage.ts
├── fixtures/                    # Custom Playwright test fixtures & state
│   └── testFixtures.ts
└── playwright.config.ts         # Playwright & BDD configuration
```

---

## 2. Configuration: `playwright.config.ts`

```typescript
import { defineConfig, devices } from '@playwright/test';
import { defineBddConfig } from 'playwright-bdd';

// Configure Gherkin feature files and step definition locations
const testDir = defineBddConfig({
  features: 'tests/features/**/*.feature',
  steps: ['tests/steps/**/*.ts', 'tests/fixtures/**/*.ts'],
});

export default defineConfig({
  testDir,
  timeout: 30_000,
  expect: { timeout: 5_000 },
  fullyParallel: true,
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

## 3. Python Alternative: `pytest-bdd` + `playwright`

For Python codebases, use `pytest-bdd` paired with the `playwright` pytest plugin:

### Configuration: `pytest.ini`
```ini
[pytest]
testpaths = tests
bdd_features_base_dir = tests/features
addopts = --browser chromium --screenshot only-on-failure --tracing retain-on-failure
```

### Feature Glue Spec (`tests/test_checkout.py`):
```python
from pytest_bdd import scenarios
from tests.steps.checkout_steps import *

# Binds all scenarios in checkout.feature to pytest runner
scenarios("checkout.feature")
```
