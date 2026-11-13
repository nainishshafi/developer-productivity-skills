# Agent Orchestrator Reference Guide

A comprehensive architectural and operational reference for multi-stage software delivery using specialized sub-agents and deterministic quality gates.

---

## 1. Orchestration Philosophy & Architecture

The **Agent Orchestrator** implements a **Hub-and-Spoke Multi-Agent Architecture** (automated end-to-end by [Software Factory Agent](file:///.github/agents/software-factory-agent.md)) designed to execute end-to-end software development lifecycle (SDLC) tasks with high rigor and zero context degradation.

```
                               ┌────────────────────────┐
                               │   Agent Orchestrator   │
                               │     (Hub / State)      │
                               └───────────┬────────────┘
                                           │
        ┌──────────────┬──────────────┬────┴─────────┬──────────────┬──────────────┬──────────────┐
        ▼              ▼              ▼              ▼              ▼              ▼              ▼
  ┌───────────┐  ┌───────────┐  ┌───────────┐  ┌───────────┐  ┌───────────┐  ┌───────────┐  ┌───────────┐
  │   PLAN    │  │  DEVELOP  │  │CODEREVIEW │  │COMPLEXITY │  │ARCH CHECKS│  │HALU CHECKS │  │ SEC CHECKS │
  └─────┬─────┘  └─────┬─────┘  └─────┬─────┘  └─────┬─────┘  └─────┬─────┘  └─────┬─────┘  └─────┬─────┘
        ▼              ▼              ▼              ▼              ▼              ▼              ▼
  architectural- language       code-reviewer  algorithmic-   detect-over-   scan-haluci-   github-sec-
  planning       specialists                   complexity     engineering    nated-tests    scanner-hook
```

### Context Isolation vs. Context Pollution

In monolithic agent sessions, long-running workflows accumulate thousands of tokens of intermediate debugging outputs, trial-and-error shell executions, and conversational noise. This causes:
1. **Context Pollution:** Downstream agents get distracted by stale decisions or hallucinated earlier thoughts.
2. **Attention Drift:** The LLM's attention across thousands of tokens weakens, leading to forgotten constraints.
3. **Token Inefficiency:** Paying quadratic cost on bloated context windows.

The Orchestrator solves this through **Bounded Stage Handoffs**:
- Each sub-agent is launched with an isolated, bounded context containing **only** what is necessary for its task.
- Upstream outputs are distilled into crisp stage artifacts (e.g., architectural specs, file diffs, test summaries).
- The Hub (orchestrator) verifies quality gates before advancing to the next stage.

---

## 2. The 7-Stage SDLC Pipeline Breakdown

| Stage | Name | Primary Skill | Supporting Skills & Memory Bus | Gate Criteria |
|---|---|---|---|---|
| **1** | `plan` | `architectural-planning` | `load-memory`, `save-memory`, `trace-code-context`, `bdd-gherkin-tester`, `researcher-poc-tester`, `rag-pipeline`, `llm-as-judge`, `api-security`, `caching-queues-reviewer`, `sql-executor` | BDD-first Gherkin `.feature` acceptance specs, clear problem definition, empirical PoC validation, component boundaries, API/contract specs, cache/queue architecture, and test strategy.<br>**Memory**: `ledger` ADRs + `journal` planning learnings. |
| **2** | `develop` | Language developer (`python-developer`, `typescript-developer`, `react-developer`, `java-developer`, `csharp-developer`, `python-api-writer`, `powershell-writer`) | `bdd-gherkin-tester`, `playwright-tester`, `rag-pipeline`, `detect-overengineering`, `load-memory`, `save-memory`, `troubleshoot-and-fix`, `test-data-creator`, `sql-connector` (ephemeral SQLite `:memory:`), `nodejs-executor` | Code implements plan contracts and Stage 1 BDD specs, step definitions & Playwright POMs authored, synthetic testbeds seeded, passes unit/integration tests, zero unhandled errors, passes in-the-loop over-engineering checks.<br>**Memory**: `sidecar` active WIP + `journal` implementation lessons. |
| **3** | `codereview` | `code-reviewer` | `detect-overengineering`, `load-memory`, `save-memory`, `python-linter`, `design-pattern-detector`, `caching-queues-reviewer`, `react-developer` | Clean code conventions, robust error handling, edge-case coverage, queue/cache resilience, zero accidental complexity, zero P0/P1 issues.<br>**Memory**: `journal` review findings & edge-case traps. |
| **4** | `complexitychecks` | `algorithmic-complexity-analyzer` | `load-memory`, `save-memory`, `trace-code-context`, `nodejs-executor`, `researcher-poc-tester`, `sql-executor` (`explain_query`) | Asymptotic time & space efficiency verified, zero hidden quadratic loops, zero unbounded recursion, zero unindexed $O(N)$ full table scans.<br>**Memory**: `journal` Big-O optimizations. |
| **5** | `architecturechecks` | `detect-overengineering` | `load-memory`, `save-memory`, `design-pattern-detector`, `trace-code-context` | No premature abstractions, zero YAGNI violations, layer depth <= 3, low overengineering risk score (< 40).<br>**Memory**: `ledger` architectural baselines + `journal` YAGNI learnings. |
| **6** | `halucinationchecks` | `scan-halucinated-tests` | `load-memory`, `save-memory`, `trace-code-context`, `playwright-tester`, `bdd-gherkin-tester`, `rag-pipeline`, `llm-as-judge` | Zero phantom symbols, all test mock targets verified against ground truth, valid imports, E2E BDD scenarios and RAG Triad evals passing.<br>**Memory**: `journal` mock corrections. |
| **7** | `securitychecks` | `github-security-scanner-hook`, `api-security` | `load-memory`, `save-memory`, `detect-secrets`, `semgrep`, `sql-connector` (`audit_query_safety`) | Zero leaked credentials/API keys, zero high/critical OWASP vulnerabilities, verified token/cryptographic hygiene, zero destructive SQL.<br>**Memory**: `ledger` security invariants + `journal` vulnerability mitigations. |

---

## 3. Deep Dive into Each Stage

### Stage 1: `plan`
- **Objective:** Establish the technical foundation, architecture decision records (ADRs), interface contracts, and delivery roadmap.
- **Skill:** `architectural-planning` (supported by `llm-as-judge` for architecture arbitration).
- **Domain Consultations:**
  - `api-security`: Authentication topologies, JWT RS256/ES256 asymmetric signing, OAuth 2.1 PKCE flows, session cookie policies (`HttpOnly`, `SameSite=Strict`), and mTLS mutual authentication.
  - `caching-queues-reviewer`: Cache invalidation patterns, stampede prevention (SingleFlight/lock/HybridCache), message broker topologies (Kafka partitioned topics vs. RabbitMQ exchanges), and dead-letter queue (DLQ) strategies.
  - `sql-executor`: Relational schema design, normalization vs. deliberate denormalization, indexing strategy (B-Tree, GIN, BRIN), and partitioning keys.
- **Inputs:** User request, existing codebase conventions, project memory (`load-memory`).
- **Outputs:** `.orchestrator/runs/<run-id>/stages/plan/plan.md`
- **Gate Check:** Must contain explicit component responsibilities, file modification list, and verifiable acceptance criteria.

### Stage 2: `develop`
- **Objective:** Implement production-grade source code and automated tests strictly adhering to the planned contracts.
- **Skill:** Language developer skill (`python-developer`, `typescript-developer`, `react-developer`, `java-developer`, `csharp-developer`, `python-api-writer` for FastAPI/Django/Ninja endpoints, or `powershell-writer` for automation scripts and modules).
- **Testbed & Database Fixtures:** For database-backed components, utilize `sql-connector` with ephemeral SQLite (`:memory:`) to seed fixtures and run migrations in-memory without external infrastructure dependencies.
- **Over-Engineering Self-Checks in the Loop:** Developers run language-specific anti-bloat self-checks and `check-overengineering` on modified files before submitting handoffs (limiting layer depth <= 3, avoiding single-use interfaces, and rejecting premature design patterns).
- **Inputs:** `plan.md`, relevant existing source files, test dependencies.
- **Outputs:** Working source code, unit and integration tests, verified test execution logs.
- **Gate Check:** All automated test suites must compile and pass cleanly without skips or mocks of unverified symbols.

### Stage 3: `codereview`
- **Objective:** Scrutinize the implementation for logical correctness, edge cases, error boundary defense, test quality, security, and clean code hygiene.
- **Skill:** `code-reviewer` (supported by `python-linter`, `design-pattern-detector`).
- **Specialized Queue & Cache Audits:** When PRs touch messaging or distributed caching, activate `caching-queues-reviewer`:
  - Redis: Distributed locking correctness (Lua atomic release), TTL assignment, pipeline batching, and cache stampede protection.
  - Kafka / RabbitMQ: Producer idempotency, transactional outbox pattern, consumer retry/DLQ backoff, and partition key balancing.
- **Inputs:** Git diff or list of modified/added files from `develop`.
- **Outputs:** `.orchestrator/runs/<run-id>/stages/codereview/review.md`
- **Gate Check:** Zero P0 (Blocker) or P1 (Major) review comments; linter/formatter runs cleanly.

### Stage 4: `complexitychecks`
- **Objective:** Audit the code for asymptotic Big-O time and space complexity efficiency.
- **Skill:** `algorithmic-complexity-analyzer` (supported by `sql-executor` for database execution plans).
- **Inputs:** Algorithms, loops, data structures, collection traversals, and SQL queries.
- **Checks:**
  - Hidden quadratic loops (e.g. `arr.includes()`, `in list`, `contains()` inside loops).
  - Array `.shift()` or `list.pop(0)` queue-draining antipatterns.
  - String concatenation in loops (`+=` string copying).
  - Unmemoized recursive branch explosions ($O(2^n)$).
  - High auxiliary space allocations inside hot paths.
  - Database Query Complexity: Run `sql-executor` (`explain_query`) to audit SQL execution plans, catching unindexed $O(N)$ full table scans, Cartesian product joins, and N+1 query antipatterns.
- **Outputs:** `.orchestrator/runs/<run-id>/stages/complexitychecks/complexity-report.md`
- **Gate Check:** No `[P0]` or `[P1]` complexity blockers; algorithms and queries match or exceed theoretical efficiency requirements.

### Stage 5: `architecturechecks`
- **Objective:** Audit the code against over-engineering, unnecessary design patterns, and structural degradation using automated signal extraction.
- **Skill:** `detect-overengineering`, `design-pattern-detector`, `trace-code-context`
- **Inputs:** Modified classes, inheritance trees, interfaces, call-graphs.
- **Checks:**
  - Speculative generality (classes with 1 implementation and no variation points)
  - Trampoline methods (methods that simply forward to another layer)
  - God objects / God files (> 500 lines or > 15 public methods)
  - Over-engineering risk score < 40 (Low risk)
  - Language-specialist anti-bloat guardrails
- **In-The-Loop Simplification:** If score >= 40, triggers the Simplification Loop:
  1. Extract structural signals (`check-overengineering`).
  2. Collapse redundant layers and delete trampoline methods.
  3. Re-verify score < 40 before advancing.
- **Outputs:** `.orchestrator/runs/<run-id>/stages/architecturechecks/architecture-audit.md`
- **Gate Check:** Overengineering risk score classified as LOW (< 40) or accepted by lead.

### Stage 6: `halucinationchecks`
- **Objective:** Cross-validate newly written tests and mocks against the actual ground-truth source code.
- **Skill:** `scan-halucinated-tests`, `trace-code-context`
- **Inputs:** Test files and corresponding source files.
- **Checks:**
  - Non-existent functions or methods invoked in tests.
  - Fabricated constants or parameters that do not exist on the source class.
  - Incorrect import paths or phantom classes.
  - Mock targets that do not match the real signature.
- **Outputs:** `.orchestrator/runs/<run-id>/stages/halucinationchecks/hallucination-report.md`
- **Gate Check:** Zero Critical or High hallucination findings.

### Stage 7: `securitychecks`
- **Objective:** Ensure no credentials, tokens, or security flaws are introduced into the repository.
- **Skill:** `github-security-scanner-hook`, `api-security`
- **Inputs:** Staged git files / modified workspace files.
- **Checks:**
  - `detect-secrets` scan for passwords, API tokens, RSA private keys, cloud credentials.
  - `semgrep` scanning for command injection, path traversal, SQL injection, insecure deserialization, unsafe subprocess invocation.
  - `api-security`: Universal AppSec audit covering JWT signature algorithms (RS256/ES256 vs rejected `none`/HS256 for asymmetric), OAuth 2.1 PKCE verification, CSRF protection, secure cookie flags, and mTLS configuration.
  - `sql-connector`: Query firewall audit (`audit_query_safety`) guaranteeing zero destructive SQL (`DROP TABLE`, `TRUNCATE`, unconstrained `DELETE`).
- **Outputs:** `.orchestrator/runs/<run-id>/stages/securitychecks/security-report.md`
- **Gate Check:** Zero secrets detected, zero OWASP high/critical severity alerts, verified API auth and SQL safety.

---

## 4. Context Handoff Protocol & Subagent Prompts

When handing off work from the Orchestrator to a Sub-Agent, use this exact contract structure:

```markdown
You are acting as the {ROLE} for the {STAGE} stage.

TASK OBJECTIVE:
{TASK_OBJECTIVE}

UPSTREAM STAGE ARTIFACTS:
- Plan: {PLAN_SUMMARY_OR_PATH}
- Changed Files: {CHANGED_FILES}
- Previous Findings: {PREVIOUS_FINDINGS}

BOUNDS & CONSTRAINTS:
1. Focus exclusively on the {STAGE} objectives.
2. Memory:
   - Check useful context: load_memory(category=...) or search_memory(...)
   - Track output & learnings: save_memory(category=..., summary=..., learnings=...)
3. Execute the primary skill: {PRIMARY_SKILL}.
4. Record findings using the repository virtual environment:
   Windows: .\.venv\Scripts\python.exe .github/skills/agent-orchestrator/scripts/orchestrator-context-manager.py record --stage {STAGE} --status PASSED --summary "<summary>"
   POSIX:   .venv/bin/python .github/skills/agent-orchestrator/scripts/orchestrator-context-manager.py record --stage {STAGE} --status PASSED --summary "<summary>"
```

---

## 5. Failure Recovery & Remediation with `troubleshoot-and-fix`

If a gate fails at any verification stage (`codereview`, `complexitychecks`, `architecturechecks`, `halucinationchecks`, `securitychecks`):

```
┌────────────────────────────────────────────────────────┐
│  Gate Failed (e.g. tests failing or hidden O(n^2) loop)│
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────┐
│  Orchestrator records FAILED with actionable summary   │
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────┐
│  Activate `troubleshoot-and-fix` to isolate testbed    │
│  Generate `isolate-runner.js` / `isolate-runner.py`    │
│  Verify reproduction & validate fix in test harness    │
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────┐
│  Port verified patch back to source code               │
│  Run `check-overengineering` to prevent Fix Bloat      │
│  Re-run failed Gates until all stages are PASSED       │
└────────────────────────────────────────────────────────┘
```

### 3-Iteration Circuit Breaker Policy
To prevent token waste, cyclic hallucinations, and churn on insoluble defects:
1. **Budget:** Exactly 3 remediation attempts are permitted for a given defect.
2. **Escalation Gate:** If the defect is not resolved by the 3rd iteration, the orchestrator **must halt execution immediately**, revert speculative changes, and surface an **Out of Options Summary**:
   - **Root Cause Analysis:** Hypotheses tested and why each failed.
   - **Isolated Reproduction Script:** Exact command to run `isolate-runner`.
   - **Escalation Options:** 2–3 concrete architectural decisions for the user to select from.

---

## 6. Integrated Skills & Agent Directory

The orchestrator and [Software Factory Agent](file:///.github/agents/software-factory-agent.md) integrate specialized skills across stages:

- [Save Memory](file:///.github/skills/save-memory/SKILL.md) — Persist high-signal project memory into `project-memory` (`ledger`, `sidecar`, `journal`).
- [Load Memory](file:///.github/skills/load-memory/SKILL.md) — Retrieve project memory and hybrid semantic search without context bloat.
- [Architectural Planning](file:///.github/skills/architectural-planning/SKILL.md) — System design, interface contracts, and ADR creation.
- [RAG Pipeline](file:///.github/skills/rag-pipeline/SKILL.md) — Chunking, hybrid search (BM25 + RRF), reranking, 5-layer testing strategy, and IR evaluation.
- [Researcher PoC Tester](file:///.github/skills/researcher-poc-tester/SKILL.md) — Isolated side-by-side PoC benchmarks (`poc-stats-runner.py`) with P50/P95/P99 statistics.
- [Test Data Creator](file:///.github/skills/test-data-creator/SKILL.md) — Schema-aware SQL batch seeding (`sql-connector`), streaming JSON mocks, and Pareto skew generation.
- [Playwright Tester](file:///.github/skills/playwright-tester/SKILL.md) — Playwright E2E browser verification, POM, locators, and Trace Viewer.
- [BDD & Gherkin Tester](file:///.github/skills/bdd-gherkin-tester/SKILL.md) — Declarative Gherkin BDD scenarios and Playwright BDD adapter integration.
- [API Security](file:///.github/skills/api-security/SKILL.md) — Universal API authentication, token security, and cryptographic audit.
- [Python API Writer](file:///.github/skills/python-api-writer/SKILL.md) — Production-grade FastAPI, Django, and Django Ninja endpoint engineering.
- [PowerShell Writer](file:///.github/skills/powershell-writer/SKILL.md) — Production-grade PowerShell scripts, advanced cmdlets, modules, and Pester v5 tests.
- [Caching & Queues Reviewer](file:///.github/skills/caching-queues-reviewer/SKILL.md) — Redis, Kafka, and RabbitMQ architecture and code review.
- [Algorithmic Complexity Analyzer](file:///.github/skills/algorithmic-complexity-analyzer/SKILL.md) — Big-O time and space complexity auditing.
- [SQL Executor](file:///.github/skills/sql-executor/SKILL.md) — Multi-engine SQL query tuning, indexing, and validation.
- [SQL Connector MCP Server](file:///.github/skills/sql-connector/SKILL.md) — Multi-database query and schema inspection with zero-tolerance SQL guardrails.
- [Detect Overengineering](file:///.github/skills/detect-overengineering/SKILL.md) — Anti-bloat heuristics and YAGNI auditing.
- [Scan Hallucinated Tests](file:///.github/skills/scan-halucinated-tests/SKILL.md) — Ground-truth AST symbol verification for unit tests and mocks.
- [Remote Pod Log Analyzer](file:///.github/skills/remote-pod-log-analyzer/SKILL.md) — Remote Linux and Kubernetes pod log analysis via SSH, kubectl, and streaming toolkit.
- [GitHub Security Scanner Hook](file:///.github/skills/github-security-scanner-hook/SKILL.md) — Secret and OWASP vulnerability scanner.
- [Troubleshoot and Fix](file:///.github/skills/troubleshoot-and-fix/SKILL.md) — Isolated testbed reproduction and 3-iteration circuit breaker remediation.
