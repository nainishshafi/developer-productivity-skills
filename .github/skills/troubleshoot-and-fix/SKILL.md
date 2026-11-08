---
name: troubleshoot-and-fix
description: Universal, language-independent framework for diagnosing, troubleshooting, and fixing software bugs, exceptions, regressions, and performance issues. Refers to language-specific developer skills (python-developer, typescript-developer, react-developer, java-developer, csharp-developer) for runtime idioms and conventions. Enforces a strict 3-iteration circuit breaker to prevent infinite token-burning retry loops, providing an empirical diagnostic escalation summary when options are exhausted. When direct reproduction is blocked by heavy dependencies or environment limits, it systematically extracts the problematic logic, generates realistic mock fixtures, and executes an isolated reproduction harness (via nodejs-executor MCP or standalone scratch scripts) to verify the fix before porting it back. Use when asked to "troubleshoot and fix", "debug this error", "fix this bug", "solve runtime exception", "diagnose issue", "reproduce and fix bug", or "debug failing code".
version: 1.2.0
---

# Troubleshoot and Fix Skill

A universal, language-independent troubleshooting and repair framework. This skill provides an empirical, evidence-driven methodology to diagnose root causes, isolate failures, synthesize mock testbeds, verify fixes without guessing, prevent regressions, and enforce a **strict 3-iteration circuit breaker** to prevent runaway token expenditure.

---

## 1. Language-Independent Architecture & Skill Delegation

This skill defines the **diagnostic and verification process**, but delegates language idioms, runtime baselines, and architectural patterns to the dedicated developer skills:

| Target Ecosystem | Delegated Developer Skill | Domain Focus Delegated to Skill |
|---|---|---|
| **Python** (3.10–3.13) | [`python-developer`](file:///.github/skills/python-developer/SKILL.md) | Asyncio event loops, `typing.Protocol`, Pydantic validation, pytest fixtures, memory leaks. |
| **TypeScript / Node.js** | [`typescript-developer`](file:///.github/skills/typescript-developer/SKILL.md) | ESM/CommonJS quirks, TS strictness, async/await promises, Prisma/Drizzle ORM boundaries, Vitest/Jest. |
| **React** (18 & 19, RSC) | [`react-developer`](file:///.github/skills/react-developer/SKILL.md) | Hook dependency arrays, stale closures, infinite re-render loops, Server vs Client Component boundaries. |
| **Java / Spring Boot** | [`java-developer`](file:///.github/skills/java-developer/SKILL.md) | JVM threading, null safety, Spring dependency injection cycles, transaction boundaries, JUnit 5. |
| **C# / .NET** (8 & 9) | [`csharp-developer`](file:///.github/skills/csharp-developer/SKILL.md) | DI lifetime validation (captive dependencies), async/await deadlocks, EF Core tracking/split queries, Span memory safety, xUnit. |
| **Other (Go, Rust, C++, etc.)** | Standard toolchain | Identify language version, package manager, and native test runner via discovery. |

---

## 2. When to Use This Skill

- Investigating runtime crashes, unhandled exceptions, and 500 errors.
- Fixing logic defects where code runs without crashing but yields incorrect calculations or corrupt state.
- Troubleshooting intermittent or flaky failures (race conditions, async timing issues, cache staleness).
- Resolving build failures, transpilation errors, or dependency conflicts.
- **Tightly coupled or blocked environments**: When reproducing the bug inside the full project is blocked by missing cloud credentials, heavy databases, slow build cycles, or monolithic architecture.

---

## 3. Circuit Breaker & Token-Budget Guardrail (Max 3 Hypotheses)

To prevent infinite trial-and-error loops, runaway token consumption, and speculative code churn, agents executing this skill must adhere to the **3-Iteration Circuit Breaker**:

1. **Iteration Budget**:
   - **Attempt 1**: Test primary hypothesis based on initial stack trace and symptom analysis.
   - **Attempt 2**: If Attempt 1 fails, step back, re-evaluate assumptions, and test an alternative hypothesis.
   - **Attempt 3**: If Attempt 2 fails, isolate the minimal invariant or probe environmental/configuration boundaries.
2. **Circuit Breaker Trip & Immediate Halt**:
   - If after **3 distinct attempts** the defect is not cleanly resolved and verified, **STOP IMMEDIATELY**.
   - **Do not guess, brute-force, or make speculative random edits.**
   - **Revert unverified exploratory changes** in the main working tree to prevent workspace corruption (`git restore` or clean scratch code).
   - Preserve reproduction testbeds in `scratch/repro/` so diagnostic artifacts remain available.
   - Output the **Out-of-Options Escalation Summary** immediately.

### Out-of-Options Escalation Summary Template

When the circuit breaker trips, present this structured post-mortem to the user:

```markdown
## 🛑 Troubleshooting Circuit Breaker: Out of Options Summary

### 1. Defect & Reproduction Baseline
- **Symptom / Error**: `<Exact error message or incorrect output>`
- **Failing Location**: `<File path & line number>`
- **Reproduction Testbed**: `scratch/repro/repro_<issue>.<ext>` (Status: Reproduced in isolation)

### 2. Hypotheses Tested & Ruled Out
| Attempt | Hypothesis / Suspected Root Cause | Action Taken | Empirical Outcome / Why It Failed |
|:---:|---|---|---|
| **1** | e.g. Null dereference in `calcTax()` | Added optional chaining `item?.tax` | Failed: Upstream API returned string `"null"` instead of primitive `null`. |
| **2** | e.g. String-to-number type coercion | Added `Number(item.tax)` parsing | Failed: Handled tax, but caused NaN in downstream aggregation `calcTotal()`. |
| **3** | e.g. Schema mismatch in payload parser | Coerced in DTO mapper | Failed: Broke existing serialization contract on line 88. |

### 3. What Was Ruled Out vs. Remaining Unknowns
- **Ruled Out**: e.g., The issue is not an async race condition or DB lock; it is deterministic data transformation.
- **Remaining Unknowns**: e.g., Why the upstream service sends string `"null"` instead of omitting the key.

### 4. Environmental & External Blockers Identified
- e.g., Unable to verify upstream service schema without access to staging environment or external third-party webhook logs.

### 5. Recommended Next Steps for Developer
1. Inspect the upstream webhook payload contract at the API gateway level.
2. Add a runtime schema sanitizer before the payload enters the domain layer.
3. Review reproduction testbed in `scratch/repro/repro_<issue>.<ext>`.
```

---

## 4. The 5-Phase Troubleshoot & Fix Protocol

```
[Phase 1: Ingestion & Triage]
       │
       ▼
[Phase 2: Direct Reproduction Assessment]
       ├── (Can reproduce directly in project?) ──► [Direct Fix & Test] ──┐
       │                                                                   │
       └── (BLOCKED / Complex / Missing deps?)                             │
              │                                                            │
              ▼                                                            │
       [Phase 3: Isolated Extraction & Mocking]                            │
              ├── Step 1: Slice minimal code unit                          │
              ├── Step 2: Synthesize mock data & boundary fixtures         │
              ├── Step 3: Run standalone harness & confirm failure         │
              └── Step 4: Fix and verify in isolation                      │
                               │                                           │
                               ▼                                           ▼
       [Phase 4: Backporting & Integration Verification] <─────────────────┘
                               │
                               ▼
       [Phase 5: Regression Proofing & Blast Radius Audit]
```

---

### Phase 1: Symptom & Error Triage

Before touching code, collect concrete ground truth:
1. **Classify the Defect**:
   - *Crash / Panic*: Uncaught exception, null pointer, segmentation fault, out-of-memory.
   - *Logic / State Corruption*: Wrong output, off-by-one, silent truncation, incorrect aggregation.
   - *Concurrency / Timing*: Race condition, deadlocks, stale closures, unhandled promise rejection.
   - *Boundary / Interface*: Type mismatch between client and server, schema desynchronization.
2. **Collect Evidence**:
   - Exact error message and full stack trace (filename, line number, call stack).
   - Expected behavior vs. actual observed behavior.
   - Minimal input payload triggering the failure.

---

### Phase 2: Direct Reproduction Assessment

Determine if the bug can be reproduced cleanly in the current project environment:

- **Check Project Test Suite**: Can a test be run or added directly via `pytest`, `npm test`, `vitest`, `mvn test`?
- **Assess Environmental Blockers**:
  - Does reproduction require live AWS/GCP/Azure credentials not available in sandbox?
  - Does it require spinning up multiple microservices, Docker containers, or live databases?
  - Does the full build or test suite take 10+ minutes to execute a single iteration?
- **Decision Rule**:
  - If reproduction is fast and direct → Reproduce directly in the project and proceed to Phase 4.
  - If reproduction is **blocked, slow, or tightly coupled** → Immediately proceed to **Phase 3 (Isolated Extraction & Mocking)**.

---

### Phase 3: The Isolated Extraction & Mocking Strategy

When direct execution is blocked, extract the logic into a standalone, runnable testbed to achieve **sub-second feedback loops**.

#### Step 1: Slice the Minimal Code Unit
Extract strictly the function, algorithm, class, or state transition containing the suspected defect into a scratch directory (`scratch/repro/`):
- Eliminate framework wrappers, HTTP controllers, and ORM decorators.
- Turn database queries into plain array operations or in-memory map lookups.
- Keep only the pure business calculation or state machine logic.

#### Step 2: Synthesize Realistic Mock Data & Boundary Fixtures
Create synthetic data fixtures covering both the baseline and the failure trigger:
- **Baseline Input**: Valid input where the logic is expected to succeed.
- **Trigger Input**: The exact edge-case payload triggering the defect (e.g. `null`, `undefined`, empty list `[]`, negative number, unicode string, malformed timestamp).
- **Mock Dependencies**: Stub out external services (mock HTTP responses, fake storage, deterministic clock/timer).

#### Step 3: Scaffold and Execute the Standalone Harness

**Option A — In-Memory Sandbox Execution via `nodejs-executor` MCP (Fastest for JS/TS):**
When connected to the `nodejs-executor` MCP server, execute the extracted logic and mock fixtures directly in `strict` sandbox mode without creating temporary files:
```json
{
  "name": "execute_code",
  "arguments": {
    "language": "typescript",
    "sandboxMode": "strict",
    "code": "import assert from 'node:assert/strict';\n// Extracted logic + mock fixtures here"
  }
}
```

**Option B — Standalone Scratch Harness Script (All Languages):**
Use the included helper script or create a standalone script:

```bash
# Initialize isolated harness (Node.js or Python)
node .github/skills/troubleshoot-and-fix/scripts/isolate-runner.js init --name <issue-slug> --lang <ts|js|python|java|csharp>
# or
python .github/skills/troubleshoot-and-fix/scripts/isolate-runner.py init --name <issue-slug> --lang <python|ts|js|java|csharp>
```

Execute the standalone file directly:
- **Python**: `python scratch/repro/repro_<issue>.py`
- **TypeScript**: `node --experimental-strip-types scratch/repro/repro_<issue>.ts` (or `npx tsx scratch/repro/repro_<issue>.ts`)
- **JavaScript**: `node scratch/repro/repro_<issue>.js`
- **Java**: `java scratch/repro/Repro_<issue>.java`
- **C#**: `dotnet script scratch/repro/Repro_<issue>.cs` (or `dotnet test`)

> [!IMPORTANT]
> **Confirm Failure First**: The harness must fail with the *exact same error or incorrect output* as observed in production. Never modify the logic until reproduction is confirmed.

#### Step 4: Fix and Verify in Isolation
- Iterate on the extracted code inside the standalone testbed with a **hard budget of 3 attempts**:
  1. **Attempt 1**: Test primary hypothesis. If verified, proceed to Phase 4.
  2. **Attempt 2**: If Attempt 1 fails, reformulate assumptions and test alternative hypothesis.
  3. **Attempt 3**: If Attempt 2 fails, isolate boundary conditions or minimal invariants.
  4. **Circuit Breaker Halt**: If all 3 attempts fail, **do not continue looping**. Stop, revert working tree changes, keep `scratch/repro/` artifacts, and deliver the **Out-of-Options Escalation Summary**.
- Re-run the standalone harness until:
  1. The failing edge-case test passes.
  2. The baseline happy-path test still passes (no regression).
  3. Additional boundary conditions (e.g. empty inputs, zeroes, large payloads) pass.

---

### Phase 4: Backporting & Integration Verification

Once proven in isolation, port the verified solution back to the source codebase:

1. **Respect Existing Code Conventions**:
   - Refer to the respective developer skill ([`python-developer`](file:///.github/skills/python-developer/SKILL.md), [`typescript-developer`](file:///.github/skills/typescript-developer/SKILL.md), [`react-developer`](file:///.github/skills/react-developer/SKILL.md), [`java-developer`](file:///.github/skills/java-developer/SKILL.md), [`csharp-developer`](file:///.github/skills/csharp-developer/SKILL.md)) to ensure the ported fix matches project idiomatic patterns (e.g. error types, immutability, async style).
2. **Apply Minimal Diff**:
   - Modify only what is necessary to solve the defect. Avoid unnecessary refactoring or style churning in the fix commit.
3. **Verify with Ground Truth**:
   - Run type checks (`tsc --noEmit`, `mypy`, `pyright`).
   - Run existing unit/integration tests to confirm no secondary regressions.

---

### Phase 5: Regression Proofing & Blast Radius Audit

1. **Add Permanent Regression Test**:
   - Convert the mock fixture from Phase 3 into a permanent unit or integration test in the project's native test directory.
2. **Audit Blast Radius**:
   - Search the codebase for similar vulnerable patterns (e.g., using `grep` or pattern detection).
   - If a null-check was missing in `calcTax()`, check `calcDiscount()` and `calcShipping()`.
3. **Document Root Cause**:
   - Provide a clear post-mortem summary: *What failed*, *Why it failed (root cause)*, and *How it was resolved and verified*.

---

## 4. Practical Example: Extraction & Mocking Walkthrough

### Scenario:
A Node.js backend throws `TypeError: Cannot read properties of undefined (reading 'price')` inside a complex GraphQL resolver connected to AWS DynamoDB and Stripe. Direct local reproduction is blocked because AWS credentials and live Stripe webhooks are required.

### Step 1 & 2: Extract to Standalone Scratch File
Extract the calculation function into `scratch/repro/repro_cart_total.ts` and generate mock fixtures:

```typescript
// scratch/repro/repro_cart_total.ts
import assert from 'node:assert/strict';

// Extracted logic
interface CartItem {
  id: string;
  sku: string;
  pricing?: { price: number; currency: string } | null;
}

function calculateSubtotal(items: CartItem[]): number {
  // BUGGY CODE: items[i].pricing might be undefined or null for discontinued items
  return items.reduce((acc, item) => acc + item.pricing.price, 0);
}

// Mock Data
const mockDiscontinuedCart: CartItem[] = [
  { id: '1', sku: 'A1', pricing: { price: 50, currency: 'USD' } },
  { id: '2', sku: 'DISCONTINUED', pricing: null }, // Trigger
];

// Execution
try {
  const total = calculateSubtotal(mockDiscontinuedCart);
  assert.equal(total, 50);
  console.log('✔ Test Passed');
} catch (err) {
  console.error('❌ Reproduced exact crash in isolation:', err.message);
}
```

### Step 3: Run & Confirm Failure
```bash
npx tsx scratch/repro/repro_cart_total.ts
# Output: ❌ Reproduced exact crash in isolation: Cannot read properties of null (reading 'price')
```

### Step 4: Fix and Validate in Isolation
Update the extracted function:
```typescript
function calculateSubtotal(items: CartItem[]): number {
  return items.reduce((acc, item) => acc + (item.pricing?.price ?? 0), 0);
}
```
Re-run harness → `✔ Test Passed`.

### Step 5: Backport to Actual Resolver
Safely apply the optional chaining and nullish coalescing back to the production file with complete confidence.

---

## References

- [Troubleshoot and Fix Reference Guide](file:///.github/skills/troubleshoot-and-fix/references/troubleshoot-and-fix-reference.md) — Bug taxonomy, mock data generation cookbook, concurrency debugging patterns, and isolation templates across languages.
