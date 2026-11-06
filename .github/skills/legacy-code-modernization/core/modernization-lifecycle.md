# Legacy Code Modernization Lifecycle

A battle-tested, 4-stage engineering framework for refactoring, extracting, and modernizing legacy codebases across any programming language without breaking production contracts.

---

## 1. The Core Philosophy

> *"To me, legacy code is simply code without tests."* — Michael Feathers (*Working Effectively with Legacy Code*)

Modernizing legacy code without automated tests is gambling. Blindly rewriting large modules leads to the **Second System Syndrome**: missed edge cases, regression bugs, lost domain knowledge, and project delays.

The modernization lifecycle is an **iterative, non-destructive 4-stage pipeline**:

```
┌────────────────────────┐      ┌──────────────────────────┐
│  1. EXTRACT & ISOLATE  │ ───> │ 2. CHARACTERIZATION TESTS│
│  (Find Seams & Inputs) │      │   (Pin Golden Master)    │
└────────────────────────┘      └────────────┬─────────────┘
                                             │
┌────────────────────────┐      ┌────────────▼─────────────┐
│ 4. DEVELOP & MIGRATE   │ <─── │  3. TDD TARGET CONTRACT  │
│ (Strangler Fig & Swap) │      │  (Red -> Green -> Factor)│
└────────────────────────┘      └──────────────────────────┘
```

---

## 2. The 4 Modernization Stages

| Stage | Name | Core Objective | Key Deliverables |
|---|---|---|---|
| **Stage 1** | **Extract & Isolate** | Identify boundaries (seams), untangle global dependencies, and extract target logic into isolated call paths. | Extracted target unit, identified inputs/outputs, severed static/global side-effects. |
| **Stage 2** | **Characterization Tests** | Freeze existing observable behavior using Pinning Tests (Golden Master / Approval tests) before modifying logic. | Suite of regression safety tests capturing actual runtime behavior (including quirks/bugs). |
| **Stage 3** | **TDD Target Architecture** | Define modern domain interfaces (Ports & Adapters) and write failing unit tests (Red) specifying clean behavior. | Clean domain contract, failing test suite reflecting desired architecture. |
| **Stage 4** | **Develop & Migrate** | Implement modern component (Green), verify parity with legacy, route traffic via Strangler Fig / Branch by Abstraction. | Fully tested modern service, feature flag/router, decommissioned legacy code. |

---

## 3. Decision Framework: Rewrite vs Strangler Migration

| Strategy | When to Use | Risks | Recommended Approach |
|---|---|---|---|
| **Big-Bang Rewrite** | Almost never (only for trivial standalone scripts < 200 lines). | Catastrophic failure, lost business rules, multi-month delivery delays. | **Avoid**. |
| **Branch by Abstraction** | Refactoring internal modules within a single monolithic codebase. | Temporary indirection layer in code. | **Recommended for monoliths**. |
| **Strangler Fig Pattern** | Modernizing coarse-grained backend services or microservice extractions. | Network latency during parallel routing; data synchronization. | **Recommended for services & APIs**. |
