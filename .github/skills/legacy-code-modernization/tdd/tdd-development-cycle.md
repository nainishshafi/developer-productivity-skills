# Test-Driven Development (TDD) for Target Architecture

Design clean, decoupled modern architectures using the Red-Green-Refactor rhythm.

---

## 1. The Red-Green-Refactor Cycle

```
      ┌─────────────┐
      ▼             │
   ┌──────┐         │
   │ RED  │ ──> Write a small, failing unit test defining target behavior
   └──────┘         │
      │             │
      ▼             │
  ┌───────┐         │
  │ GREEN │ ──> Write minimal production code to make the test pass
  └───────┘         │
      │             │
      ▼             │
┌──────────┐        │
│ REFACTOR │ ──> Clean up architecture, eliminate duplication, improve naming
└──────────┘        │
      │             │
      └─────────────┘
```

---

## 2. Defining Target Contracts First (Outside-In TDD)

Before implementing the target class, write tests against the ideal public interface:

```typescript
// 1. RED: Write the test first, specifying clean domain behavior
describe('ModernPricingEngine', () => {
  it('applies 15% VIP discount for orders over $100', () => {
    const engine = new ModernPricingEngine();
    const result = engine.calculate({
      amountCents: 15_000,
      customerTier: CustomerTier.VIP,
    });

    expect(result.discountCents).toBe(2_250);
    expect(result.finalAmountCents).toBe(12_750);
  });
});

// 2. GREEN: Implement minimal clean domain code
export class ModernPricingEngine {
  calculate(request: PricingRequest): PricingResult {
    if (request.customerTier === CustomerTier.VIP && request.amountCents >= 10_000) {
      const discount = Math.round(request.amountCents * 0.15);
      return { discountCents: discount, finalAmountCents: request.amountCents - discount };
    }
    return { discountCents: 0, finalAmountCents: request.amountCents };
  }
}

// 3. REFACTOR: Extract discount rules into strategy or domain policy if complexity grows
```

---

## 3. Test Doubles: Fakes vs Mocks

| Test Double | Purpose | When to Use in TDD |
|---|---|---|
| **Fake** | Working implementation with in-memory state (e.g. `InMemoryUserRepository`). | **Preferred default**: authentic behavior, zero brittle method stubs. |
| **Stub** | Returns canned, hardcoded responses. | Simulating external network errors, timeouts, or specific error states. |
| **Mock** | Verifies method call expectations (`expect(mailer.send).toHaveBeenCalledTimes(1)`). | Use sparingly; over-mocking couples tests to private implementation details. |
