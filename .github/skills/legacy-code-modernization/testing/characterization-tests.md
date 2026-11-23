# Characterization Tests & Pinning Existing Behavior

Freeze observable legacy behavior before changing a single line of code using Pinning Tests and the Golden Master Pattern.

---

## 1. What is a Characterization Test?

> **Characterization Test:** A test that documents the **actual, existing behavior** of a piece of software, rather than what the specification says it *should* do.

### The Golden Rule of Modernization:
Never fix bugs or "improve" behavior while writing characterization tests.
- If legacy code outputs an incorrect date format (`"02-30-2023"`), your characterization test must assert `"02-30-2023"`.
- Why? Because existing upstream systems or database triggers may rely on that exact quirk. Fixing bugs belongs in the modern implementation, not during characterization pinning.

---

## 2. The Golden Master / Approval Testing Pattern

When dealing with complex legacy algorithms with dozens of hidden branching paths, writing individual unit tests for every branch is too slow. Use the **Golden Master** pattern:

1. **Feed a Matrix of Inputs**: Generate hundreds of varied input combinations (combinatorial inputs).
2. **Capture the Output Stream**: Execute the legacy code and record all outputs (return values, generated JSON, database writes) into a baseline snapshot file.
3. **Assert against the Master**: On every refactoring change, re-run the input matrix against the baseline snapshot. Any diff indicates an accidental regression.

---

## 3. Language Implementation Patterns

### TypeScript / Vitest / Jest (Snapshot Pinning)
```typescript
import { describe, it, expect } from 'vitest';
import { legacyTaxCalculator } from './legacy-tax-calculator';

describe('LegacyTaxCalculator (Characterization)', () => {
  const testInputs = [
    { country: 'US', state: 'CA', amount: 100, isExempt: false },
    { country: 'US', state: 'NY', amount: 0, isExempt: false },
    { country: 'CA', state: 'ON', amount: 50.5, isExempt: true },
    { country: 'UNKNOWN', state: '', amount: -10, isExempt: false },
  ];

  it('preserves golden master behavior for all input combinations', () => {
    const results = testInputs.map(input => ({
      input,
      output: legacyTaxCalculator(input.country, input.state, input.amount, input.isExempt)
    }));

    // Freezes actual behavior into snapshot file
    expect(results).toMatchSnapshot();
  });
});
```

### Python (Approval / Golden Master with pytest)
```python
import pytest
from legacy_engine import calculate_discount

INPUT_MATRIX = [
    (0, "STANDARD", False),
    (100, "VIP", False),
    (500, "VIP", True),
    (-50, "STANDARD", True),
    (1000, "EXPIRED", False),
]

def test_characterize_discount_engine():
    recorded_outputs = []
    for order_total, tier, is_first_order in INPUT_MATRIX:
        result = calculate_discount(order_total, tier, is_first_order)
        recorded_outputs.append({
            "inputs": (order_total, tier, is_first_order),
            "discount": result
        })

    # Assert against known pinned baseline
    assert recorded_outputs == [
        {"inputs": (0, "STANDARD", False), "discount": 0.0},
        {"inputs": (100, "VIP", False), "discount": 15.0},
        {"inputs": (500, "VIP", True), "discount": 75.0},
        {"inputs": (-50, "STANDARD", True), "discount": 0.0},
        {"inputs": (1000, "EXPIRED", False), "discount": 0.0},
    ]
```

---

## 4. When to Retire Characterization Tests

Characterization tests are **scaffolding**. Once:
1. The new modern component is fully built via TDD,
2. The legacy code is decommissioned,
3. Parity is proven,

The characterization tests can either be archived or replaced with domain-level acceptance tests.
