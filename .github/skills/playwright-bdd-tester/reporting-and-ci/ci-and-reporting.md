# CI Execution, Sharding & Trace Viewer Diagnostics

Run Gherkin Playwright suites at scale in CI/CD pipelines, parallelize with sharding, and debug failures using the Playwright Trace Viewer.

---

## 1. CLI Commands & Workflow

### Generating & Executing Tests (`playwright-bdd`)
`playwright-bdd` generates `.spec.js` test wrappers from `.feature` files before test execution:

```bash
# Step 1: Generate spec files from Gherkin feature files
npx bddgen

# Step 2: Execute Playwright tests
npx playwright test

# Or run both in a single step (npm test script):
npm run test:e2e # configured as: "bddgen && playwright test"
```

### Running Scenarios by Tags
Filter scenarios using standard boolean tag expressions:

```bash
# Run only @smoke scenarios
npx bddgen --tags "@smoke" && npx playwright test

# Run all @regression tests excluding @flaky or @wip
npx bddgen --tags "@regression and not (@flaky or @wip)" && npx playwright test
```

---

## 2. Inspecting Failures with Playwright Trace Viewer

When a scenario fails in CI, Playwright generates a complete recorded execution trace zip file (`trace: 'on-first-retry'`).

The trace captures:
- Full DOM snapshot before and after every action.
- Network requests, responses, and payload timing.
- Console logs and JavaScript errors.
- Visual filmstrip showing exact pixel rendering at every millisecond.

```bash
# Open trace viewer locally from CI artifact
npx playwright show-trace test-results/checkout-chromium-retry1/trace.zip
```

---

## 3. Parallel Sharding in GitHub Actions CI

Distribute large Gherkin test suites across multiple parallel CI runners:

```yaml
# .github/workflows/e2e-tests.yml
name: E2E Playwright BDD Tests
on: [push, pull_request]

jobs:
  e2e:
    strategy:
      fail-fast: false
      matrix:
        shardIndex: [1, 2, 3, 4]
        shardTotal: [4]
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: 22
          cache: 'pnpm'

      - run: pnpm install
      - run: pnpm exec playwright install --with-deps chromium

      - name: Generate BDD Specs & Run Shard
        run: |
          npx bddgen
          npx playwright test --shard=${{ matrix.shardIndex }}/${{ matrix.shardTotal }}

      - uses: actions/upload-artifact@v4
        if: always()
        with:
          name: playwright-report-shard-${{ matrix.shardIndex }}
          path: playwright-report/
          retention-days: 14
```

