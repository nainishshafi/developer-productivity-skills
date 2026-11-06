# Legacy Code Modernization Audit Checklist & Risk Rubric

A procedural checklist and risk classification rubric for executing safe, incremental code modernizations.

---

## 1. The Step-by-Step Modernization Checklist

### Phase 1: Discovery & Seam Identification
- [ ] Map all entry points and call sites of the target legacy code.
- [ ] Identify hidden inputs: global variables, environment variables, system clocks (`Date.now()`), static singletons.
- [ ] Identify hidden side effects: direct file writes, external API calls, database mutations, unlogged exceptions.
- [ ] Identify suitable seams (Constructor parameterization, Interface extraction, Subclass & override).

### Phase 2: Characterization & Pinning
- [ ] Construct a combinatorial input matrix covering happy paths, boundary numbers, nulls, and error cases.
- [ ] Execute legacy code against the matrix and record baseline snapshot (Golden Master).
- [ ] Verify that characterization tests pass with 100% determinism.
- [ ] Do NOT fix bugs during this phase; pin existing quirks as baseline behavior.

### Phase 3: TDD Specification of Target Architecture
- [ ] Define clean domain interfaces / ports (Dependency Inversion).
- [ ] Write failing unit tests (`Red`) specifying modern domain requirements.
- [ ] Implement minimal modern code to pass tests (`Green`).
- [ ] Refactor modern code for readability, performance, and memory safety (`Refactor`).

### Phase 4: Migration & Shadowing
- [ ] Wire Branch by Abstraction or Strangler routing proxy.
- [ ] (For critical systems) Run shadow execution comparing legacy vs modern results; verify zero discrepancies.
- [ ] Enable feature flag to route 100% of production traffic to modern component.

### Phase 5: Decommissioning & Cleanup
- [ ] Remove routing proxy/abstraction if no longer needed.
- [ ] Delete legacy implementation files, dead utilities, and unused dependencies.
- [ ] Verify that all test suites pass and no dangling references exist.

---

## 2. Modernization Risk Rubric

| Risk Tier | Characteristics | Required Safeguards |
|---|---|---|
| **Tier 1 (High Risk)** | Financial transactions, authorization gates, complex state machines, untracked global state mutations, database trigger dependencies. | Mandatory Golden Master snapshot + Shadow Parallel Run (7+ days zero diff) before traffic cutover. |
| **Tier 2 (Medium Risk)** | Internal business logic, data transformers, batch report generators, CRUD services. | Characterization tests + Branch by Abstraction with instant feature-flag rollback. |
| **Tier 3 (Low Risk)** | Isolated utility functions, string parsers, formatting helpers with zero external I/O. | In-memory characterization tests $\to$ direct TDD replacement. |
