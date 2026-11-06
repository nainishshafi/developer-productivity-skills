# Algorithmic Complexity Audit Workflow & Severity Rubric

A language-agnostic protocol for auditing source code, assigning severity scores, and proposing optimized algorithms.

---

## 1. The 5-Step Complexity Audit Protocol

### Step 1: Identify Input Parameters & Variables
Determine which variables represent scaling dataset size ($n$, $m$, $k$). Distinguish between fixed configurations (e.g. constant 7 days in a week) and unbounded inputs (user records, log entries).

### Step 2: Trace Loop Structures & Nesting Depths
- Count explicit loops (`for`, `while`, recursion).
- Calculate step progressions: linear step (`i++` $\implies O(n)$), multiplicative step (`i *= 2` $\implies O(\log n)$).

### Step 3: Uncover Hidden $O(n)$ Operations
Scan every line inside loops for implicit linear scans:
- **Membership checks**: `in list`, `.includes()`, `.contains()`, `.indexOf()`.
- **String operations**: `str += char` (immutable copy).
- **Collection mutations**: `list.pop(0)`, `array.shift()`, `slice.insert(0, val)`.
- **Database queries**: SQL calls inside a loop ($N+1$ query multiplication).

### Step 4: Calculate Time & Auxiliary Space Complexity
- Express Worst-Case Time Complexity in Big-O notation.
- Express Auxiliary Space Complexity (excluding input parameters).

### Step 5: Formulate Refactored Strategy
- Can an inner $O(n)$ check be pre-computed into an $O(1)$ Hash Map?
- Can a two-pointer or sliding window eliminate a nested loop?
- Can recursive calls be memoized or converted to bottom-up dynamic programming?

---

## 2. Severity Classification Rubric

| Severity | Definition | Criteria | Action Required |
|---|---|---|---|
| **[P0 - Critical Complexity Blocker]** | Unbounded exponential/quadratic algorithm guaranteed to hang or crash in production. | $O(2^n)$ or $O(n!)$ recursion on inputs $> 25$; $O(n^2)$ or $N+1$ queries on tables $> 2,000$ rows. | Immediate blocker; must refactor before deployment. |
| **[P1 - Major Suboptimality]** | Avoidable quadratic or high polynomial multiplier in non-trivial code paths. | $O(n^2)$ hidden loop scan via `includes`/`contains`; array `.shift()` queue drain; string `+=` in loops. | Strongly recommended fix; merge blocked on high-traffic paths. |
| **[P2 - Optimization Opportunity]** | Suboptimal constant factor or intermediate memory allocation. | Chained `.map().filter()` creating multiple transient arrays; linear scan instead of binary search on sorted data. | Recommended improvement for memory/speed hygiene. |
| **[P3 - Complexity Nit]** | Theoretical or cosmetic complexity nuance with negligible practical difference. | Micro-optimizing loops where $n \le 10$ guaranteed. | Optional advisory note. |

---

## 3. Standard Audit Output Template

Structure complexity findings clearly:

```markdown
### Algorithmic Complexity Findings

#### [P0 - Critical Complexity Blocker] Quadratic Nested Collection Scan
- **Location:** `src/services/billing.ts:84`
- **Current Complexity:**
  - **Time:** $O(n \cdot m) \implies O(n^2)$ (where $n$ is invoice items, $m$ is tax rates)
  - **Auxiliary Space:** $O(1)$
- **Identified Bottleneck:**
  Line 86 calls `taxRates.find(r => r.code === item.taxCode)` inside a `for` loop over `invoiceItems`. For an invoice with 5,000 items, this performs $25,000,000$ equality checks.
- **Optimized Complexity:**
  - **Time:** $O(n + m)$ (Linear time)
  - **Auxiliary Space:** $O(m)$ (Hash Map for tax rates)
- **Proposed Optimization Diff:**
```typescript
- for (const item of invoiceItems) {
-   const rate = taxRates.find(r => r.code === item.taxCode);
-   totalTax += item.amount * (rate?.percentage ?? 0);
- }
+ const rateMap = new Map(taxRates.map(r => [r.code, r.percentage]));
+ for (const item of invoiceItems) {
+   const percentage = rateMap.get(item.taxCode) ?? 0;
+   totalTax += item.amount * percentage;
+ }
```
```
