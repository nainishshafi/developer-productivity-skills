# Strangler Fig, Branch by Abstraction & Safe Migration

Patterns for safely shifting production traffic from legacy systems to modern replacements with zero downtime.

---

## 1. Branch by Abstraction (In-Codebase Migration)

When modernizing an internal module or service inside a monolithic repository:

```
Step 1: Legacy State
Caller ───────────────────────────────> [Legacy Implementation]

Step 2: Introduce Abstraction & Route Caller Through It
Caller ──────────> [Abstraction / Port]
                         │
                         ▼
                [Legacy Implementation]

Step 3: Build Modern Implementation & Wire Feature Flag
Caller ──────────> [Abstraction / Port]
                         │
        ┌────────────────┴────────────────┐
        ▼ (Flag = false)                  ▼ (Flag = true)
[Legacy Implementation]           [Modern Implementation]

Step 4: Decommission Legacy & Simplify
Caller ──────────> [Modern Implementation]
```

---

## 2. Strangler Fig Pattern (Service & API Boundaries)

When modernizing a legacy backend or migrating endpoints to a modern service:

```
[Incoming Request]
        │
        ▼
┌───────────────────────────────┐
│     Strangler Routing Proxy   │
└───────────────┬───────────────┘
                │
        ┌───────┴───────┐
        ▼               ▼
  [Modern Route]  [Legacy Route]
  (/api/v2/auth)  (/cgi-bin/auth)
```
- Route new or refactored endpoints to the modern service first.
- Leave unrefactored endpoints routing to legacy.
- As more endpoints are strangled, the legacy service shrinks until it can be turned off entirely.

---

## 3. Dark Launching & Shadow Execution (Parity Verification)

Before switching 100% of user traffic to a modern component, run both implementations in parallel:

```typescript
export class ShadowPricingProxy implements PricingServicePort {
  constructor(
    private legacy: LegacyPricingService,
    private modern: ModernPricingEngine,
    private logger: AuditLogger
  ) {}

  async calculatePrice(order: Order): Promise<PriceResult> {
    // 1. Always execute legacy (source of truth during shadow phase)
    const legacyResult = await this.legacy.calculate(order);

    // 2. Asynchronously execute modern implementation
    try {
      const modernResult = await this.modern.calculate(order);

      // 3. Compare parity diffs
      if (modernResult.totalCents !== legacyResult.totalCents) {
        this.logger.warn('Parity discrepancy detected', {
          orderId: order.id,
          legacy: legacyResult.totalCents,
          modern: modernResult.totalCents,
        });
      }
    } catch (err) {
      this.logger.error('Modern pricing failed during shadow execution', { error: err });
    }

    // Return legacy result to user
    return legacyResult;
  }
}
```

---

## 4. Decommissioning & Cleanup Protocol

Once modern implementation achieves 100% parity across a predetermined validation window (e.g. 7 days with zero discrepancy alerts):
1. **Remove Feature Flag / Proxy Routing**: Point callers directly to modern implementation.
2. **Delete Legacy Files**: Remove legacy classes, unused dead code, and obsolete helper libraries.
3. **Delete Dead Dependencies**: Remove old database drivers, legacy ORMs, or unmaintained npm/pip packages from project manifests.
4. **Run Security & Hallucination Scans**: Verify no dangling references or orphaned imports remain.
