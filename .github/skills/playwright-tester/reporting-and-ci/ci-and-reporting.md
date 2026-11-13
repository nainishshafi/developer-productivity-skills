# CI Execution, Sharding & Trace Viewer Diagnostics

Run Playwright suites at scale in CI/CD pipelines, parallelize with sharding, and debug failures using the Playwright Trace Viewer.

---

## 1. CLI Commands & Workflow

```bash
# Run all Playwright tests
npx playwright test

# Run a single spec file in headed mode
npx playwright test tests/e2e/checkout.spec.ts --headed

# Open interactive UI mode for local debugging
npx playwright test --ui

# Filter tests by title
npx playwright test -g "completes checkout"
```

---

## 2. Inspecting Failures with Playwright Trace Viewer

When a test fails in CI, Playwright generates a complete recorded execution trace zip file (`trace: 'on-first-retry'`).

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

Distribute large Playwright test suites across multiple parallel CI runners:

```yaml
# .github/workflows/e2e-tests.yml
name: E2E Playwright Tests
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

      - name: Run Playwright Shard
        run: npx playwright test --shard=${{ matrix.shardIndex }}/${{ matrix.shardTotal }}

      - uses: actions/upload-artifact@v4
        if: always()
        with:
          name: playwright-report-shard-${{ matrix.shardIndex }}
          path: playwright-report/
          retention-days: 14
```

