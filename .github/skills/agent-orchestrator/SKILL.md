---
name: agent-orchestrator
description: Orchestrates an end-to-end multi-agent development lifecycle across seven quality stages: plan -> develop -> codereview -> complexitychecks -> architecturechecks -> halucinationchecks -> securitychecks. Coordinates sub-agent handoffs, manages stage-isolated context, provides structured verification guidance across quality gates, and integrates isolated testbed remediation (troubleshoot-and-fix). Use when asked to "orchestrate a feature", "run full development pipeline", "plan-develop-review", "agent orchestrator", "orchestrate subagents", or "run full lifecycle checks".
version: 1.2.0
---

# Agent Orchestrator

The **Agent Orchestrator** is an automated multi-agent workflow conductor that coordinates specialized skills across the seven phases of modern software engineering:

```
[1. Plan] ──> [2. Develop] ──> [3. Code Review] ──> [4. Complexity Checks] ──> [5. Architecture Checks] ──> [6. Hallucination Checks] ──> [7. Security Checks]
                                        │                      │                           │                         │
                                        └──────────────────────┴─────────────┬─────────────┴─────────────────────────┘
                                                                             ▼
                                                           [Remediation: troubleshoot-and-fix]
```

At each stage, the orchestrator invokes the correct domain skill, packages bounded context for the specialized sub-agent, and evaluates explicit quality gates before proceeding.

---

## When to Use This Skill

- Building a new feature, service, or refactoring task requiring comprehensive verification.
- Running multi-agent workflows where sub-agents require strictly scoped context (preventing context pollution).
- Auditing algorithmic time and space complexity ($O(1) \dots O(2^n)$) and eliminating hidden quadratic loops or $O(N)$ database table scans.
- Enforcing architectural standards, anti-pattern detection, and YAGNI compliance on generated code.
- Verifying unit tests and mocks against source code to catch LLM hallucinations.
- Running pre-delivery security, secret audits, and API authentication/cryptographic reviews before code commits.
- Isolating and verifying bug fixes using standalone testbeds when quality gates fail.

---

## The 7 Pipeline Stages & Skill Mapping

| # | Stage | Assigned Skill | Sub-Agent Role | Primary Responsibilities |
|---|---|---|---|---|
| **1** | `plan` | `architectural-planning` | Architecture & Planning Specialist | Requirements decomposition, tech stack alignment, interface contracts, ADR creation. Supported by `llm-as-judge`, `api-security` (auth/topology), `caching-queues-reviewer` (queue/cache architecture), and `sql-executor` (schema/indexing strategy). |
| **2** | `develop` | Language developer (`python-developer`, `typescript-developer`, `react-developer`, `java-developer`, `csharp-developer`, `python-api-writer`, `powershell-writer`) | Core Implementation Engineer | Production implementation, unit and integration tests, error handling, self-checks. Supported by `troubleshoot-and-fix` and `sql-connector` (ephemeral SQLite `:memory:` test fixtures). |
| **3** | `codereview` | `code-reviewer` | Senior Code Reviewer | Multi-dimension code review (correctness, resilience, edge cases, clean code). Supported by linters and `caching-queues-reviewer` (Redis/Kafka/RabbitMQ PR review). |
| **4** | `complexitychecks` | `algorithmic-complexity-analyzer` | Algorithmic Complexity Auditor | Asymptotic Big-O time and space complexity ($O(1) \dots O(2^n)$), hidden quadratic loops (`.includes()`, `in list`), recursion depth traps, and `sql-executor` (`explain_query`) for query execution plan complexity ($O(N)$ table scans). |
| **5** | `architecturechecks` | `detect-overengineering` | Principal Architecture Auditor | Over-engineering detection, speculative generality (YAGNI), layer bloat, anti-patterns (`design-pattern-detector`), and language-specialist over-engineering self-checks. |
| **6** | `halucinationchecks` | `scan-halucinated-tests` | Ground-Truth Verification Auditor | Cross-validating test assertions, mocks, and imports against real AST symbols (`trace-code-context`). |
| **7** | `securitychecks` | `github-security-scanner-hook`, `api-security` | Application Security Auditor | Secret/credential scanning (`detect-secrets`), OWASP pattern analysis (`semgrep`), API auth audit (JWT/OAuth 2.1/mTLS), and `sql-connector` (`audit_query_safety` firewall). |

---

## Context Handoff Protocol

Sub-agents must never be given unbounded raw context. The orchestrator isolates stage execution using the **Context Manager**:

```bash
# Initialize a new pipeline run
python .github/skills/agent-orchestrator/scripts/orchestrator-context-manager.py init --task "<task-description>"

# Generate bounded context handoff payload for a stage
python .github/skills/agent-orchestrator/scripts/orchestrator-context-manager.py handoff --stage <stage-name>

# Record stage completion and quality gate verdict
python .github/skills/agent-orchestrator/scripts/orchestrator-context-manager.py record --stage <stage-name> --status PASSED --summary "<summary>"

# Inspect pipeline status
python .github/skills/agent-orchestrator/scripts/orchestrator-context-manager.py status

# Generate final delivery report
python .github/skills/agent-orchestrator/scripts/orchestrator-context-manager.py report
```

*(Note: In environments with virtualenv configured, run with `.venv/Scripts/python` or `.venv/bin/python`).*

---

## Step-by-Step Execution Workflow

### Step 1: Initialize Pipeline
1. Run `orchestrator-context-manager.py init --task "<task>"` to generate a run directory under `.orchestrator/runs/<run-id>/`.
2. Inspect workspace conventions and relevant memories (`load-memory` if available).

### Step 2: Stage 1 — `plan`
1. Invoke sub-agent with role `Architecture & Planning Specialist`.
2. Activate skill `architectural-planning`.
3. Produce system design, interface contracts, and list of files to create/modify. Consult `api-security` for token/auth architectures, `caching-queues-reviewer` for message broker and cache topologies, and `sql-executor` for data modeling, partitioning, and indexing strategies. Use `llm-as-judge` if evaluating trade-offs between competing architectures.
4. Record verdict:
   ```bash
   python .github/skills/agent-orchestrator/scripts/orchestrator-context-manager.py record --stage plan --status PASSED --summary "Plan approved: contract defined" --artifact "plan.md"
   ```

### Step 3: Stage 2 — `develop`
1. Generate handoff context: `orchestrator-context-manager.py handoff --stage develop`.
2. Pass bounded context (contracts, specifications, target files) to the implementation sub-agent.
3. Activate relevant language skill (`python-developer`, `typescript-developer`, `react-developer`, `java-developer`, `csharp-developer`, `python-api-writer`, or `powershell-writer` for automation scripts and modules). For database testing, utilize `sql-connector` with ephemeral SQLite (`:memory:`) to seed fixtures without external dependencies. Run the language specialist's embedded Over-Engineering Self-Checks.
4. Write production code and automated tests. Run test runner to verify green test status.
5. Record verdict:
   ```bash
   python .github/skills/agent-orchestrator/scripts/orchestrator-context-manager.py record --stage develop --status PASSED --summary "All unit tests passing"
   ```

### Step 4: Stage 3 — `codereview`
1. Generate handoff context: `orchestrator-context-manager.py handoff --stage codereview`.
2. Invoke reviewer sub-agent to inspect git diff or modified files.
3. Activate skill `code-reviewer` (supported by `python-linter` or relevant language linters). When reviewing caching or queue implementations (Redis, Kafka, RabbitMQ), activate `caching-queues-reviewer` to audit cache stampede, consumer idempotency, and partition key distribution.
4. Review against the 7 dimensions: logic correctness, error boundaries, edge cases, test quality, security, performance, and style.
5. Record verdict:
   ```bash
   python .github/skills/agent-orchestrator/scripts/orchestrator-context-manager.py record --stage codereview --status PASSED --summary "Clean code review: 0 blocking issues"
   ```

### Step 5: Stage 4 — `complexitychecks`
1. Generate handoff context: `orchestrator-context-manager.py handoff --stage complexitychecks`.
2. Activate skill `algorithmic-complexity-analyzer`.
3. Audit worst-case time and space complexity:
   - Verify absence of hidden quadratic loops (e.g. `array.includes()` or `in list` inside loops).
   - Check queue operations for array shift antipatterns.
   - Audit recursive functions for stack depth traps and missing memoization.
   - Inspect database queries with `sql-executor` (`explain_query`) to identify $O(N)$ unindexed full table scans, Cartesian joins, and N+1 query patterns.
4. Verify no `[P0]` or `[P1]` complexity blockers exist.
5. Record verdict:
   ```bash
   python .github/skills/agent-orchestrator/scripts/orchestrator-context-manager.py record --stage complexitychecks --status PASSED --summary "Complexity verified: O(n) time, O(1) auxiliary space"
   ```

### Step 6: Stage 5 — `architecturechecks`
1. Generate handoff context: `orchestrator-context-manager.py handoff --stage architecturechecks`.
2. Activate skill `detect-overengineering` and `design-pattern-detector`.
3. Check for premature abstractions, layer bloat, trampoline methods, and YAGNI violations, verifying alignment with language specialist anti-bloat guardrails.
4. Verify over-engineering risk score is LOW (< 40).
5. Record verdict:
   ```bash
   python .github/skills/agent-orchestrator/scripts/orchestrator-context-manager.py record --stage architecturechecks --status PASSED --summary "Low over-engineering risk: score 12/100"
   ```

### Step 7: Stage 6 — `halucinationchecks`
1. Generate handoff context: `orchestrator-context-manager.py handoff --stage halucinationchecks`.
2. Activate skill `scan-halucinated-tests`.
3. Cross-reference all test imports, assertions, method calls, and mocks against real ground truth.
4. Verify 0 phantom symbols or hallucinated methods exist.
5. Record verdict:
   ```bash
   python .github/skills/agent-orchestrator/scripts/orchestrator-context-manager.py record --stage halucinationchecks --status PASSED --summary "0 hallucinated symbols detected"
   ```

### Step 8: Stage 7 — `securitychecks`
1. Generate handoff context: `orchestrator-context-manager.py handoff --stage securitychecks`.
2. Activate skill `github-security-scanner-hook` and `api-security`.
3. Run `detect-secrets` scan for credentials, private keys, and tokens.
4. Run `semgrep` scan for OWASP injection flaws (command injection, path traversal, SQLi, XSS).
5. Audit API authentication and cryptographic hygiene with `api-security` (JWT RS256/ES256, OAuth 2.1 PKCE, session cookie flags, mTLS).
6. Verify database operations with `sql-connector` (`audit_query_safety`) to guarantee zero destructive SQL (`DROP TABLE`, `DELETE *`).
7. Record verdict:
   ```bash
   python .github/skills/agent-orchestrator/scripts/orchestrator-context-manager.py record --stage securitychecks --status PASSED --summary "Security gate passed: 0 secrets, 0 vulnerabilities"
   ```

### Step 9: Final Delivery & Reporting
1. Run `python .github/skills/agent-orchestrator/scripts/orchestrator-context-manager.py report`.
2. Present the user with the consolidated stage audit report and verified deliverables.

---

## Remediation Feedback Loop with `troubleshoot-and-fix`

If any quality gate fails (`FAILED` or `BLOCKED`):
1. **Record the Failure**: The orchestrator records the defect delta with specific file paths, line numbers, and failure diagnostics.
2. **Isolate with `troubleshoot-and-fix`**:
   - For failing tests, runtime exceptions, or broken contracts, activate **`troubleshoot-and-fix`**.
   - Generate an isolated reproduction harness (`scripts/isolate-runner.js` or `scripts/isolate-runner.py`) to systematically reproduce the defect outside monolithic project dependencies.
   - Verify the fix inside the reproduction sandbox before porting the patch back.
3. **Respect the 3-Iteration Circuit Breaker**: If `troubleshoot-and-fix` fails to resolve the defect within its 3-iteration budget, do not loop indefinitely or burn tokens. Halt the pipeline immediately, revert unverified code churn, and surface the **Out of Options Summary** directly to the user for guidance.
4. **Re-evaluate Stages**: Once verified, re-run the affected pipeline stages until all quality gates pass.

---

## References

- [Agent Orchestrator Reference Guide](file:///.github/skills/agent-orchestrator/references/agent-orchestrator-reference.md) — Architectural patterns, sub-agent prompts, and gate policies.
- Context Manager Script: `.github/skills/agent-orchestrator/scripts/orchestrator-context-manager.py`
- [API Security Audit](file:///.github/skills/api-security/SKILL.md) — Universal API authentication, token security, and cryptographic audit.
- [Python API Writer](file:///.github/skills/python-api-writer/SKILL.md) — Production-grade FastAPI, Django, and Django Ninja endpoint engineering.
- [PowerShell Writer](file:///.github/skills/powershell-writer/SKILL.md) — Production-grade PowerShell scripts, advanced cmdlets, modules, and Pester v5 tests.
- [Caching & Queues Reviewer](file:///.github/skills/caching-queues-reviewer/SKILL.md) — Redis, Kafka, and RabbitMQ architecture and code review.
- [SQL Executor](file:///.github/skills/sql-executor/SKILL.md) — Multi-engine SQL query tuning, indexing, and validation.
- [SQL Connector MCP Server](file:///.github/skills/sql-connector/SKILL.md) — Multi-database query and schema inspection with zero-tolerance SQL guardrails.
- [Detect Overengineering](file:///.github/skills/detect-overengineering/SKILL.md) — Anti-bloat heuristics and YAGNI auditing.
- [Troubleshoot and Fix](file:///.github/skills/troubleshoot-and-fix/SKILL.md) — Isolated testbed reproduction and 3-iteration circuit breaker remediation.
