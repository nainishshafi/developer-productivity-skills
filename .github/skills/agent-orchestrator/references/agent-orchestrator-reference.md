# Agent Orchestrator Reference Guide

A comprehensive architectural and operational reference for multi-stage software delivery using specialized sub-agents and deterministic quality gates.

---

## 1. Orchestration Philosophy & Architecture

The **Agent Orchestrator** implements a **Hub-and-Spoke Multi-Agent Architecture** designed to execute end-to-end software development lifecycle (SDLC) tasks with high rigor and zero context degradation.

```
                              ┌────────────────────────┐
                              │   Agent Orchestrator   │
                              │     (Hub / State)      │
                              └───────────┬────────────┘
                                          │
       ┌──────────────┬──────────────┬────┴─────────┬──────────────┬──────────────┐
       ▼              ▼              ▼              ▼              ▼              ▼
 ┌───────────┐  ┌───────────┐  ┌───────────┐  ┌───────────┐  ┌───────────┐  ┌───────────┐
 │   PLAN    │  │  DEVELOP  │  │CODEREVIEW │  │ARCH CHECKS│  │HALU CHECKS │  │ SEC CHECKS │
 └─────┬─────┘  └─────┬─────┘  └─────┬─────┘  └─────┬─────┘  └─────┬─────┘  └─────┬─────┘
       ▼              ▼              ▼              ▼              ▼              ▼
 architectural-  language       python-linter  detect-over-   scan-haluci-   github-sec-
 planning        specialist     design-pattern engineering    nated-tests    scanner-hook
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

## 2. The 6-Stage SDLC Pipeline Breakdown

| Stage | Name | Primary Skill | Supporting Skills | Gate Criteria |
|---|---|---|---|---|
| **1** | `plan` | `architectural-planning` | `trace-code-context`, `load-memory` | Clear problem definition, component boundaries, API/contract specs, and test strategy. |
| **2** | `develop` | `python-developer`, `typescript-developer`, `java-developer` | `load-memory`, `save-memory` | Code implements plan contracts, passes unit/integration tests, zero unhandled errors. |
| **3** | `codereview` | `code-reviewer` | `python-linter`, `design-pattern-detector` | Clean code conventions, robust error handling, edge-case coverage, zero P0/P1 issues. |
| **4** | `architecturechecks` | `detect-overengineering` | `design-pattern-detector`, `trace-code-context` | No premature abstractions, zero YAGNI violations, layer depth <= 3, low overengineering risk score. |
| **5** | `halucinationchecks` | `scan-halucinated-tests` | `trace-code-context` | Zero phantom symbols, all test mock targets verified against ground truth, valid imports. |
| **6** | `securitychecks` | `github-security-scanner-hook` | `detect-secrets`, `semgrep` | Zero leaked credentials/API keys, zero high/critical OWASP vulnerabilities. |

---

## 3. Deep Dive into Each Stage

### Stage 1: `plan`
- **Objective:** Establish the technical foundation, architecture decision records (ADRs), interface contracts, and delivery roadmap.
- **Skill:** `architectural-planning`
- **Inputs:** User request, existing codebase conventions, project memory (`load-memory`).
- **Outputs:** `.orchestrator/runs/<run-id>/stages/plan/plan.md`
- **Gate Check:** Must contain explicit component responsibilities, file modification list, and verifiable acceptance criteria.

### Stage 2: `develop`
- **Objective:** Implement production-grade source code and automated tests strictly adhering to the planned contracts.
- **Skill:** Language developer skill (`python-developer`, `typescript-developer`, `java-developer`).
- **Inputs:** `plan.md`, relevant existing source files, test dependencies.
- **Outputs:** Working source code, unit and integration tests, verified test execution logs.
- **Gate Check:** All automated test suites must compile and pass cleanly without skips or mocks of unverified symbols.

### Stage 3: `codereview`
- **Objective:** Scrutinize the implementation for logical correctness, edge cases, error boundary defense, test quality, security, and clean code hygiene.
- **Skill:** `code-reviewer` (supported by `python-linter`, `design-pattern-detector`).
- **Inputs:** Git diff or list of modified/added files from `develop`.
- **Outputs:** `.orchestrator/runs/<run-id>/stages/codereview/review.md`
- **Gate Check:** Zero P0 (Blocker) or P1 (Major) review comments; linter/formatter runs cleanly.

### Stage 4: `architecturechecks`
- **Objective:** Audit the code against over-engineering, unnecessary design patterns, and structural degradation.
- **Skill:** `detect-overengineering`, `design-pattern-detector`, `trace-code-context`
- **Inputs:** Modified classes, inheritance trees, interfaces, call-graphs.
- **Checks:**
  - Speculative generality (classes with 1 implementation and no variation points)
  - Trampoline methods (methods that simply forward to another layer)
  - God objects / God files (> 500 lines or > 15 public methods)
  - Over-engineering risk score < 40 (Low risk)
- **Outputs:** `.orchestrator/runs/<run-id>/stages/architecturechecks/architecture-audit.md`
- **Gate Check:** Overengineering risk score classified as LOW or accepted by lead.

### Stage 5: `halucinationchecks`
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

### Stage 6: `securitychecks`
- **Objective:** Ensure no credentials, tokens, or security flaws are introduced into the repository.
- **Skill:** `github-security-scanner-hook`
- **Inputs:** Staged git files / modified workspace files.
- **Checks:**
  - `detect-secrets` scan for passwords, API tokens, RSA private keys, cloud credentials.
  - `semgrep` scanning for command injection, path traversal, SQL injection, insecure deserialization, unsafe subprocess invocation.
- **Outputs:** `.orchestrator/runs/<run-id>/stages/securitychecks/security-report.md`
- **Gate Check:** Zero secrets detected, zero OWASP high/critical severity alerts.

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
2. Execute the primary skill: {PRIMARY_SKILL}.
3. Record findings using:
   python .github/skills/agent-orchestrator/scripts/orchestrator-context-manager.py record --stage {STAGE} --status PASSED --summary "<summary>"
```

---

## 5. Failure Recovery & Feedback Loops

If a gate fails at any verification stage (`codereview`, `architecturechecks`, `halucinationchecks`, `securitychecks`):

```
┌────────────────────────────────────────────────────────┐
│  Gate Failed (e.g. halucinationchecks: 2 fake methods) │
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────┐
│  Orchestrator records FAILED with actionable summary   │
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────┐
│  Loop back to DEVELOP subagent with remediation delta  │
│  "Fix methods foo() and bar() which do not exist"      │
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────┐
│  Re-run DEVELOP -> re-run failed Gate until PASSED     │
└────────────────────────────────────────────────────────┘
```
This closed-loop feedback guarantees that defects are remediated immediately before code reaches downstream environments.
