# Troubleshoot and Fix Reference Guide

A deep-dive technical reference on bug taxonomy, mock data synthesis, isolated reproduction patterns, and root-cause resolution techniques across programming languages.

---

## 1. Bug Taxonomy & Root Cause Diagnostic Matrix

| Defect Category | Common Symptoms | Root Cause Mechanism | Isolated Reproduction Strategy |
|---|---|---|---|
| **Null / Undefined Dereference** | `TypeError: Cannot read properties of undefined`, `NullPointerException`, `AttributeError: 'NoneType' object has no attribute`. | Optional field missing, unhandled API response shape, unexpected null in collection. | Pass mock payload with `null`, `undefined`, or omitted keys for all nullable schema properties. |
| **Off-by-One / Boundary Errors** | Array index out of bounds, missing last item in pagination, duplicated boundary records. | `<` vs `<=`, slice range end-exclusion, 0-indexed vs 1-indexed conversion. | Create mock array of sizes: `[0]`, `[1]`, `[limit - 1]`, `[limit]`, `[limit + 1]`. |
| **Async Race Condition** | Intermittent flakiness, out-of-order writes, stale data overwriting fresh data. | Unawaited promises, concurrent writes without locks, non-deterministic network arrival. | Create synthetic async delay generator (`delay(ms)`) to simulate slow responses overtaking fast responses. |
| **Stale State / Closure Trap** | React component or closure reads old variable values after updates. | Closure capturing initial render state, missing dependency in hook array. | Simulate sequential calls with intermediate state mutations in a standalone loop or harness. |
| **Floating-Point Imprecision** | `0.1 + 0.2 === 0.30000000000000004`, financial calculation discrepancies. | IEEE 754 binary representation of decimal fractions. | Test with currency amounts requiring exact precision; verify using integer cents or `Decimal` libraries. |
| **Resource & Memory Leaks** | Gradual slowdown, `EMFILE: too many open files`, out of memory crashes. | Unclosed DB connections, lingering event listeners, uncancelled interval timers. | Repeatedly invoke the extracted logic in a high-iteration loop (`10_000` cycles) and monitor resource handles. |

---

## 2. Isolated Extraction Playbook

When an issue occurs inside a large or coupled system, follow these steps to slice the code cleanly into an isolated testbed:

```
[Full Application]
   ├── Route Handler (HTTP / Express / FastAPI / Spring)  <-- DISCARD
   ├── Middleware / Auth / CORS                           <-- DISCARD
   ├── Database ORM / External Network Clients           <-- REPLACE WITH IN-MEMORY STUB
   └── Core Business Logic / Calculation / Transformation <-- EXTRACT TO SCRATCH TESTBED
```

### Extraction Principles
1. **Strip Framework Dependencies**: Remove framework imports (`@Controller`, `req: Request`, `res: Response`, `fastapi.Depends`). Convert function signatures to accept plain data parameters.
2. **Replace I/O with In-Memory Mocks**:
   - Database queries (`db.users.find()`) → Plain arrays (`[{ id: '1', ... }]`).
   - Network API calls (`fetch('https://api.stripe.com/...')`) → Synchronous or immediate Promise resolution with mock JSON.
   - System clock (`Date.now()`, `datetime.utcnow()`) → Injectable parameter or fixed timestamp.
3. **Keep the Pure Logic Intact**: Ensure the extracted algorithm, data parser, or conditional tree is character-for-character identical to the production version before making fixes.

---

## 3. Mock Data Synthesis Cookbook

### Boundary Value Matrix
When generating synthetic data for isolated testing, always include these boundary test vectors:

| Data Type | Standard Value | Boundary & Stress Vectors |
|---|---|---|
| **Strings** | `"John Doe"` | `""` (empty), `" "` (whitespace), `"  \n\t"`, very long string (10,000 chars), special chars (`<script>`, `' OR 1=1`), emojis (`🔥`), surrogate pairs. |
| **Numbers / Integers** | `42` | `0`, `-1`, `1`, `Number.MAX_SAFE_INTEGER`, `Number.MIN_SAFE_INTEGER`, `NaN`, `Infinity`, `-Infinity`. |
| **Decimals / Floats** | `19.99` | `0.0`, `-0.01`, `0.0000001`, `0.1 + 0.2`, large exponents (`1e20`). |
| **Arrays / Collections**| `[1, 2, 3]` | `[]` (empty), `[null]`, `[undefined]`, single element `[x]`, large array (100k items), duplicates `[x, x]`. |
| **Objects / Dictionaries**| `{ id: 1 }` | `{}` (empty), deeply nested `{ a: { b: { c: null } } }`, unexpected additional keys, circular references. |
| **Dates / Timestamps** | `"2026-11-06T12:00:00Z"` | Leap year (`2028-02-29`), DST transition hours, timezone offset (`+14:00`, `-12:00`), epoch `0`, malformed string. |

---

## 4. Multi-Language Isolation Templates

### Python: Standalone Extraction Pattern
```python
# scratch/repro/repro_discount.py
import unittest
from decimal import Decimal
from typing import Optional

# 1. Extracted Logic
def apply_tier_discount(subtotal: Decimal, coupon_code: Optional[str]) -> Decimal:
    if subtotal <= Decimal("0"):
        return Decimal("0")
    
    # Buggy assumption: coupon_code.upper() crashes if coupon_code is None
    # Fix: safely handle None
    if coupon_code and coupon_code.upper() == "SAVE20":
        return subtotal * Decimal("0.80")
    return subtotal

# 2. Reproduction Harness
class TestDiscountRepro(unittest.TestCase):
    def test_null_coupon(self):
        # Reproduces NoneType AttributeError before fix
        res = apply_tier_discount(Decimal("100.00"), None)
        self.assertEqual(res, Decimal("100.00"))

    def test_valid_coupon(self):
        res = apply_tier_discount(Decimal("100.00"), "SAVE20")
        self.assertEqual(res, Decimal("80.00"))

if __name__ == "__main__":
    unittest.main()
```

### TypeScript: Standalone Extraction Pattern
```typescript
// scratch/repro/repro_pagination.ts
import assert from 'node:assert/strict';

interface PaginationInput<T> {
  items: T[];
  page: number;     // 1-indexed
  pageSize: number;
}

// 1. Extracted Logic
function paginateItems<T>({ items, page, pageSize }: PaginationInput<T>): T[] {
  // Off-by-one check: Ensure page <= 0 is safeguarded
  const safePage = Math.max(1, page);
  const start = (safePage - 1) * pageSize;
  const end = start + pageSize;
  return items.slice(start, end);
}

// 2. Harness & Test Cases
function run() {
  const data = ['A', 'B', 'C', 'D', 'E'];

  // Test Case 1: Standard page 1
  assert.deepEqual(paginateItems({ items: data, page: 1, pageSize: 2 }), ['A', 'B']);

  // Test Case 2: Boundary page (past end)
  assert.deepEqual(paginateItems({ items: data, page: 10, pageSize: 2 }), []);

  // Test Case 3: Edge case (page = 0 or negative)
  assert.deepEqual(paginateItems({ items: data, page: 0, pageSize: 2 }), ['A', 'B']);

  console.log('✔ All isolated pagination assertions passed!');
}

run();
```

### React: Isolated Hook or Component Harness
When a React component has an infinite loop or render bug, extract the hook or reducer into a pure JS/TS harness without booting the whole app:

```typescript
// scratch/repro/repro_state_reducer.ts
import assert from 'node:assert/strict';

type Action = 
  | { type: 'INCREMENT' } 
  | { type: 'SET_VALUE'; payload: number } 
  | { type: 'RESET' };

interface State {
  count: number;
  history: number[];
}

// Extracted Reducer logic
function counterReducer(state: State, action: Action): State {
  switch (action.type) {
    case 'INCREMENT':
      return { count: state.count + 1, history: [...state.history, state.count + 1] };
    case 'SET_VALUE':
      return { count: action.payload, history: [...state.history, action.payload] };
    case 'RESET':
      return { count: 0, history: [] };
    default:
      return state;
  }
}

// Harness
let state: State = { count: 0, history: [0] };
state = counterReducer(state, { type: 'INCREMENT' });
assert.equal(state.count, 1);
assert.deepEqual(state.history, [0, 1]);
console.log('✔ Reducer logic verified cleanly in isolation.');
```

---

## 5. Backporting & Verification Checklist

Before marking the issue resolved:

- [ ] **Exact Root Cause Identified**: Can you articulate in one sentence *why* the bug occurred?
- [ ] **Isolated Test Passed**: Did the standalone harness fail first, then pass strictly after the logic fix?
- [ ] **Zero Unintended Diffs**: Did you avoid unnecessary formatting, variable renames, or unrelated refactorings in the production file?
- [ ] **Language Developer Skill Consulted**: Does the fix match idioms from [`python-developer`](file:///.github/skills/python-developer/SKILL.md), [`typescript-developer`](file:///.github/skills/typescript-developer/SKILL.md), [`react-developer`](file:///.github/skills/react-developer/SKILL.md), or [`java-developer`](file:///.github/skills/java-developer/SKILL.md)?
- [ ] **Permanent Regression Test Added**: Is the isolated reproduction test case integrated into the project's native test suite (`tests/`, `__tests__/`, `src/test/`)?
- [ ] **Blast Radius Checked**: Are other occurrences of the same pattern in adjacent modules audited and protected?

---

## 6. Circuit Breaker & Escalation Heuristics

### Why Agents Must Limit Debugging Iterations
In complex distributed or legacy codebases, an agent can easily fall into an infinite trial-and-error cycle:
1. Making speculative edits that mask one symptom while causing another.
2. Accumulating code churn that destabilizes unrelated modules.
3. Consuming excessive tokens and API quota without making real progress.

### The 3-Attempt Rule
- **Attempt 1**: Target the most obvious stack trace or logic failure.
- **Attempt 2**: Re-examine data flow and upstream/downstream boundaries.
- **Attempt 3**: Minimal invariant isolation or environmental probe.
- **Trip**: If unresolved after 3 attempts, halt, revert workspace modifications, keep `scratch/repro/` artifacts, and provide the structured **Out-of-Options Escalation Summary** with concrete hypotheses ruled out and clear next steps for the developer.

