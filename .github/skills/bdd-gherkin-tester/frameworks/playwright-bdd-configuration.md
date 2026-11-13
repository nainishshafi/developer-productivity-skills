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

---

## 4. Java Ecosystem: Playwright Java + Cucumber-JVM

In Java, combine Microsoft Playwright (`com.microsoft.playwright:playwright`) with Cucumber-JVM:

### Dependencies (`pom.xml`):
```xml
<dependencies>
    <!-- Microsoft Playwright for Java -->
    <dependency>
        <groupId>com.microsoft.playwright</groupId>
        <artifactId>playwright</artifactId>
        <version>1.49.0</version>
        <scope>test</scope>
    </dependency>
    <!-- Cucumber Java & JUnit Platform Engine -->
    <dependency>
        <groupId>io.cucumber</groupId>
        <artifactId>cucumber-java</artifactId>
        <version>7.20.1</version>
        <scope>test</scope>
    </dependency>
    <dependency>
        <groupId>io.cucumber</groupId>
        <artifactId>cucumber-junit-platform-engine</artifactId>
        <version>7.20.1</version>
        <scope>test</scope>
    </dependency>
</dependencies>
```

### Cucumber Test Runner (`RunCucumberTest.java`):
```java
package com.example.bdd;

import org.junit.platform.suite.api.ConfigurationParameter;
import org.junit.platform.suite.api.IncludeEngines;
import org.junit.platform.suite.api.SelectClasspathResource;
import org.junit.platform.suite.api.Suite;

import static io.cucumber.junit.platform.engine.Constants.GLUE_PROPERTY_NAME;
import static io.cucumber.junit.platform.engine.Constants.PLUGIN_PROPERTY_NAME;

@Suite
@IncludeEngines("cucumber")
@SelectClasspathResource("features")
@ConfigurationParameter(key = GLUE_PROPERTY_NAME, value = "com.example.bdd.steps")
@ConfigurationParameter(key = PLUGIN_PROPERTY_NAME, value = "pretty, html:target/cucumber-report.html")
public class RunCucumberTest {}
```

---

## 5. C# / .NET Ecosystem: Playwright .NET + Reqnroll (SpecFlow Successor)

In .NET, use **Reqnroll** (the modern open-source successor to SpecFlow) paired with `Microsoft.Playwright`:

### NuGet Packages (`.csproj`):
```xml
<ItemGroup>
  <PackageReference Include="Microsoft.Playwright" Version="1.49.0" />
  <PackageReference Include="Microsoft.Playwright.NUnit" Version="1.49.0" />
  <PackageReference Include="Reqnroll.NUnit" Version="2.2.1" />
</ItemGroup>
```

### Configuration (`reqnroll.json`):
```json
{
  "$schema": "https://schemas.reqnroll.net/reqnroll-config-latest.json",
  "language": {
    "feature": "en"
  }
}
```

---

## 6. Generating & Filtering BDD Specs (`bddgen`)

`playwright-bdd` generates `.spec.js` test wrappers from `.feature` files before test execution:

```bash
# Step 1: Generate spec files from Gherkin feature files
npx bddgen

# Step 2: Execute Playwright tests (or combined: "bddgen && playwright test")
npx playwright test

# Filter scenarios using boolean tag expressions
npx bddgen --tags "@smoke" && npx playwright test
npx bddgen --tags "@regression and not (@flaky or @wip)" && npx playwright test
```

For CI parallel sharding (`--shard`) and Trace Viewer diagnostics (`show-trace`), see [`playwright-tester`](../../playwright-tester/reporting-and-ci/ci-and-reporting.md).

