---
name: agent-orchestrator
description: Orchestrates an end-to-end multi-agent development lifecycle across six rigorous quality stages: plan -> develop -> codereview -> architecturechecks -> halucinationchecks -> securitychecks. Coordinates sub-agent handoffs, manages stage-isolated context, and enforces deterministic quality gates. Use when asked to "orchestrate a feature", "run full development pipeline", "plan-develop-review", "agent orchestrator", "orchestrate subagents", or "run full lifecycle checks".
version: 1.0.0
---

# Agent Orchestrator

The **Agent Orchestrator** is an automated multi-agent workflow conductor that coordinates specialized skills across the six phases of modern software engineering:

```
[1. Plan] ──> [2. Develop] ──> [3. Code Review] ──> [4. Architecture Checks] ──> [5. Hallucination Checks] ──> [6. Security Checks]
```

At each stage, the orchestrator invokes the correct domain skill, packages bounded context for the specialized sub-agent, and evaluates explicit quality gates before proceeding.

---

## When to Use This Skill

- Building a new feature, service, or refactoring task requiring comprehensive verification.
- Running multi-agent workflows where sub-agents require strictly scoped context (preventing context pollution).
- Enforcing architectural standards, anti-pattern detection, and YAGNI compliance on generated code.
- Verifying unit tests and mocks against source code to catch LLM hallucinations.
- Running pre-delivery security and secret audits before code commits or pull requests.

---

## The 6 Pipeline Stages & Skill Mapping

| # | Stage | Assigned Skill | Sub-Agent Role | Primary Responsibilities |
|---|---|---|---|---|
| **1** | `plan` | `architectural-planning` | Architecture & Planning Specialist | Requirements decomposition, tech stack alignment, interface contracts, ADR creation. |
| **2** | `develop` | Language developer (`python-developer`, `typescript-developer`, `react-developer`, `java-developer`) | Core Implementation Engineer | Production implementation, unit and integration tests, error handling. |
| **3** | `codereview` | `code-reviewer` | Senior Code Reviewer | Multi-dimension code review (correctness, resilience, edge cases, clean code). Supported by linters. |
| **4** | `architecturechecks` | `detect-overengineering` | Principal Architecture Auditor | Over-engineering detection, speculative generality (YAGNI), layer bloat, anti-patterns. |
| **5** | `halucinationchecks` | `scan-halucinated-tests` | Ground-Truth Verification Auditor | Cross-validating test assertions, mocks, and imports against real AST symbols. |
| **6** | `securitychecks` | `github-security-scanner-hook` | Application Security Auditor | Secret/credential scanning (`detect-secrets`), OWASP pattern analysis (`semgrep`). |

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

---

## Step-by-Step Execution Workflow

### Step 1: Initialize Pipeline
1. Run `orchestrator-context-manager.py init --task "<task>"` to generate a run directory under `.orchestrator/runs/<run-id>/`.
2. Inspect workspace conventions and relevant memories (`load-memory` if available).

### Step 2: Stage 1 — `plan`
1. Invoke sub-agent with role `Architecture & Planning Specialist`.
2. Activate skill `architectural-planning`.
3. Produce system design, interface contracts, and list of files to create/modify.
4. Record verdict:
   ```bash
   python .github/skills/agent-orchestrator/scripts/orchestrator-context-manager.py record --stage plan --status PASSED --summary "Plan approved: contract defined" --artifact "plan.md"
   ```

### Step 3: Stage 2 — `develop`
1. Generate handoff context: `orchestrator-context-manager.py handoff --stage develop`.
2. Pass bounded context (contracts, specifications, target files) to the implementation sub-agent.
3. Activate relevant language skill (`python-developer`, `typescript-developer`, `java-developer`).
4. Write production code and automated tests. Run test runner to verify green test status.
5. Record verdict:
   ```bash
   python .github/skills/agent-orchestrator/scripts/orchestrator-context-manager.py record --stage develop --status PASSED --summary "All unit tests passing"
   ```

### Step 4: Stage 3 — `codereview`
1. Generate handoff context: `orchestrator-context-manager.py handoff --stage codereview`.
2. Invoke reviewer sub-agent to inspect git diff or modified files.
3. Activate skill `code-reviewer` (supported by `python-linter` or relevant language linters).
4. Review against the 7 dimensions: logic correctness, error boundaries, edge cases, test quality, security, performance, and style.
5. Record verdict:
   ```bash
   python .github/skills/agent-orchestrator/scripts/orchestrator-context-manager.py record --stage codereview --status PASSED --summary "Clean code review: 0 blocking issues"
   ```

### Step 5: Stage 4 — `architecturechecks`
1. Generate handoff context: `orchestrator-context-manager.py handoff --stage architecturechecks`.
2. Activate skill `detect-overengineering` and `design-pattern-detector`.
3. Check for premature abstractions, layer bloat, trampoline methods, and YAGNI violations.
4. Verify over-engineering risk score is LOW (< 40).
5. Record verdict:
   ```bash
   python .github/skills/agent-orchestrator/scripts/orchestrator-context-manager.py record --stage architecturechecks --status PASSED --summary "Low over-engineering risk: score 12/100"
   ```

### Step 6: Stage 5 — `halucinationchecks`
1. Generate handoff context: `orchestrator-context-manager.py handoff --stage halucinationchecks`.
2. Activate skill `scan-halucinated-tests`.
3. Cross-reference all test imports, assertions, method calls, and mocks against real ground truth.
4. Verify 0 phantom symbols or hallucinated methods exist.
5. Record verdict:
   ```bash
   python .github/skills/agent-orchestrator/scripts/orchestrator-context-manager.py record --stage halucinationchecks --status PASSED --summary "0 hallucinated symbols detected"
   ```

### Step 7: Stage 6 — `securitychecks`
1. Generate handoff context: `orchestrator-context-manager.py handoff --stage securitychecks`.
2. Activate skill `github-security-scanner-hook`.
3. Run `detect-secrets` scan for credentials, private keys, and tokens.
4. Run `semgrep` scan for OWASP injection flaws (command injection, path traversal, SQLi, XSS).
5. Record verdict:
   ```bash
   python .github/skills/agent-orchestrator/scripts/orchestrator-context-manager.py record --stage securitychecks --status PASSED --summary "Security gate passed: 0 secrets, 0 vulnerabilities"
   ```

### Step 8: Final Delivery & Reporting
1. Run `python .github/skills/agent-orchestrator/scripts/orchestrator-context-manager.py report`.
2. Present the user with the consolidated stage audit report and verified deliverables.

---

## Remediation Feedback Loop

If any gate fails (`FAILED` or `BLOCKED`):
1. The orchestrator records the failure with specific line numbers and error diagnostics.
2. The orchestrator routes the failure delta directly back to the `develop` sub-agent:
   - Example: *"Hallucination check detected `getUserProfile()` does not exist on `UserService`. Update test to use `findUserById()`."*
3. The `develop` sub-agent resolves the defect.
4. Re-run verification stages until all gates pass.

---

## References

- [Agent Orchestrator Reference Guide](file:///.github/skills/agent-orchestrator/references/agent-orchestrator-reference.md) — Architectural patterns, sub-agent prompts, and gate policies.
- Context Manager Script: `.github/skills/agent-orchestrator/scripts/orchestrator-context-manager.py`
