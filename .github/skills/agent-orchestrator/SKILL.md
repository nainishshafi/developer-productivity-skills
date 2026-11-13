---
name: agent-orchestrator
description: >-
  Orchestrates an end-to-end multi-agent development lifecycle across seven quality stages: plan -> develop -> codereview -> complexitychecks -> architecturechecks -> halucinationchecks -> securitychecks. Coordinates sub-agent handoffs, manages stage-isolated context, embeds automated detect-overengineering checks in the loop (develop, codereview, architecturechecks, and defect remediation), tracks sub-agent outputs via save-memory (ledger, sidecar, journal), selectively loads relevant context across quality gates via load-memory, provides structured verification guidance, and integrates isolated testbed remediation (troubleshoot-and-fix). Use when asked to "orchestrate a feature", "run full development pipeline", "plan-develop-review", "agent orchestrator", "orchestrate subagents", or "run full lifecycle checks".
version: 1.4.0
---

# Agent Orchestrator

The **Agent Orchestrator** is an automated multi-agent workflow conductor that coordinates specialized skills across the seven phases of modern software engineering:

```
[1. Plan] ──> [2. Develop] ──> [3. Code Review] ──> [4. Complexity Checks] ──> [5. Architecture Checks] ──> [6. Hallucination Checks] ──> [7. Security Checks]
    │               │                 │                      │                           │                         │                          │
    │         ┌─────┴───────────┐     │                      │                 ┌─────────┴──────────┐              │                          │
    │         │ OE Self-Checks  │     │                      │                 │ Simplification Loop│              │                          │
    │         └─────────────────┘     │                      │                 └────────────────────┘              │                          │
    ▼               ▼                 ▼                      ▼                           ▼                         ▼                          ▼
┌──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                   PROJECT MEMORY BUS (project-memory MCP via save-memory & load-memory)                                          │
│  • ledger: Architectural truths, interface contracts, schema strategies, and non-negotiable security invariants                                 │
│  • sidecar: Active task state, sub-agent WIP handoffs, modified files list, and pending defect fixes                                            │
│  • journal: Stage execution recaps containing BOTH distilled work summary AND mandatory learnings / traps avoided                                │
└──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘
                                                                             │
                                                                             ▼
                                                           [Remediation: troubleshoot-and-fix]
                                                                             │
                                                                             ▼
                                                           [Anti-Fix-Bloat Over-Engineering Gate]
```

At each stage, the orchestrator invokes the specialized domain sub-agent, packages bounded context, embeds **`detect-overengineering`** checks directly into the development and remediation loops, tracks sub-agent outputs via **`save-memory`**, selectively retrieves useful context for downstream agents via **`load-memory`**, and evaluates explicit quality gates before proceeding.

> [!TIP]
> For autonomous end-to-end execution across all **37 skills** and **3 MCP servers** (`project-memory`, `sql-connector`, `nodejs-executor`), invoke the repository's [Software Factory Agent](file:///.github/agents/software-factory-agent.md).

---

## When to Use This Skill

- Building a new feature, service, or refactoring task requiring comprehensive verification.
- Running multi-agent workflows where sub-agents require strictly scoped context (preventing context pollution).
- Embedding automated **`detect-overengineering`** checks in the loop (across development, PR review, architecture gates, and bug fixes).
- Keeping track of sub-agent outputs, architectural decisions, and intermediate WIP using **`save-memory`**.
- Selectively loading useful upstream decisions, contracts, and past bug learnings for downstream agents using **`load-memory`** and hybrid search.
- Auditing algorithmic time and space complexity ($O(1) \dots O(2^n)$) and eliminating hidden quadratic loops or $O(N)$ database table scans.
- Enforcing architectural standards, anti-pattern detection, and YAGNI compliance on generated code.
- Verifying unit tests and mocks against source code to catch LLM hallucinations.
- Running pre-delivery security, secret audits, and API authentication/cryptographic reviews before code commits.
- Isolating and verifying bug fixes using standalone testbeds when quality gates fail.

---

## The 7 Pipeline Stages & Skill Mapping

| # | Stage | Assigned Skill | Sub-Agent Role | Primary Responsibilities, Memory Tracking & In-The-Loop Checks |
|---|---|---|---|---|
| **1** | `plan` | `architectural-planning` | Architecture & Planning Specialist | BDD-first `.feature` acceptance specs (`bdd-gherkin-tester`), requirements decomposition, tech stack alignment, interface contracts, ADR creation. Supported by `bdd-gherkin-tester`, `llm-as-judge`, `researcher-poc-tester`, `rag-pipeline`, `api-security`, `caching-queues-reviewer`, `sql-executor`, `scan-repo-readme`.<br>**Memory**: Load existing constraints via `load-memory`; track contracts in `ledger` & planning learnings in `journal` via `save-memory`. |
| **2** | `develop` | Language developer (`python-developer`, `typescript-developer`, `react-developer`, `java-developer`, `csharp-developer`, `python-api-writer`, `powershell-writer`) | Core Implementation Engineer | Production implementation against Stage 1 BDD specs, step definitions (`bdd-gherkin-tester`), Playwright POM/E2E specs (`playwright-tester`), unit/integration tests, error handling, self-checks. Supported by `bdd-gherkin-tester`, `playwright-tester`, `rag-pipeline`, `detect-overengineering`, `legacy-code-modernization`, `troubleshoot-and-fix`, `test-data-creator`, `sql-connector` (ephemeral SQLite `:memory:`), `nodejs-executor`.<br>**In-The-Loop**: Developer Over-Engineering Self-Check before submitting handoff.<br>**Memory**: Load contracts from `ledger` & active task from `sidecar`; track WIP in `sidecar` & implementation learnings in `journal`. |
| **3** | `codereview` | `code-reviewer` | Senior Code Reviewer | Multi-dimension code review (correctness, resilience, edge cases, clean code). Supported by `detect-overengineering`, `python-linter`, `react-developer` (8-dim FP/Clean Code checklist), and `caching-queues-reviewer`.<br>**In-The-Loop**: Run `check-overengineering` on modified files in diff.<br>**Memory**: Load WIP diff context from `sidecar`; search past review traps; track review findings in `journal`. |
| **4** | `complexitychecks` | `algorithmic-complexity-analyzer` | Algorithmic Complexity Auditor | Asymptotic Big-O time and space complexity ($O(1) \dots O(2^n)$), hidden quadratic loops (`.includes()`, `in list`), recursion depth traps, empirical `nodejs-executor` / `researcher-poc-tester` benchmarks, and `sql-executor` (`explain_query`) for query execution plan complexity ($O(N)$ table scans).<br>**Memory**: Search memory for known query bottlenecks; record algorithmic efficiency learnings in `journal`. |
| **5** | `architecturechecks` | `detect-overengineering` | Principal Architecture Auditor | Over-engineering detection, speculative generality (YAGNI), layer bloat, anti-patterns (`design-pattern-detector`), and language-specialist over-engineering self-checks.<br>**In-The-Loop**: Automated Simplification Refactoring Loop when score $\ge 40$.<br>**Memory**: Load architecture rules from `ledger`; record approved structural invariants in `ledger` & YAGNI learnings in `journal`. |
| **6** | `halucinationchecks` | `scan-halucinated-tests` | Ground-Truth Verification Auditor | Cross-validating test assertions, mocks, and imports against real AST symbols (`trace-code-context`), E2E Playwright/Gherkin verification (`playwright-tester`, `bdd-gherkin-tester`), and 5-layer RAG evaluation (`rag-pipeline`).<br>**Memory**: Load verified interface contracts from `ledger`; record mock drift corrections in `journal`. |
| **7** | `securitychecks` | `github-security-scanner-hook`, `api-security` | Application Security Auditor | Secret/credential scanning (`detect-secrets`), OWASP pattern analysis (`semgrep`), API auth audit (JWT/OAuth 2.1/mTLS), and `sql-connector` (`audit_query_safety` firewall).<br>**Memory**: Load security baselines from `ledger`; persist permanent security rules in `ledger` & vulnerabilities avoided in `journal`. |

---

## In-The-Loop Over-Engineering Detection & Simplification

LLMs inherently suffer from speculative bias: they frequently introduce premature abstractions, 1:1 single-implementation interfaces, deep DTO mapping chains, and redundant builder patterns. Waiting until the end of the SDLC to check for bloat forces expensive, disruptive rewrites.

The Orchestrator embeds **`detect-overengineering`** directly into the active engineering loops across **four critical checkpoints**:

```
[Checkpoint 1: Develop Loop]     ──► Developer runs Over-Engineering Self-Checks on newly written files.
                                      Inlines 1:1 interfaces and drops speculative parameters immediately.
                                      │
[Checkpoint 2: Code Review Loop] ──► Reviewer executes `check-overengineering` on the PR diff.
                                      Accidental complexity or trampoline indirection blocks the review.
                                      │
[Checkpoint 3: Architecture Gate]──► If score >= 40 (Moderate/High/Extreme), enters the Simplification Loop:
                                      1. Extract structural signals (pass-throughs, empty hooks, builder bloat).
                                      2. Apply refactoring diff (collapse layers, replace class with function).
                                      3. Re-verify score < 40 before advancing.
                                      │
[Checkpoint 4: Remediation Loop] ──► When `troubleshoot-and-fix` patches a bug, it verifies the fix patch
                                      with `check-overengineering` to prevent "Fix Bloat" (wrapper sprawl).
```

### CLI Command for In-The-Loop Verification:

Run using the repository virtual environment:
```bash
# Audit a single newly modified file
.\.venv\Scripts\python.exe .github/skills/agent-orchestrator/scripts/orchestrator-context-manager.py check-overengineering --file "<path-to-file>"

# Audit an entire subsystem directory with custom threshold
.\.venv\Scripts\python.exe .github/skills/agent-orchestrator/scripts/orchestrator-context-manager.py check-overengineering --dir "src/services" --max-score 35

# Full repository scan
.\.venv\Scripts\python.exe .github/skills/agent-orchestrator/scripts/orchestrator-context-manager.py check-overengineering --all
```

*(On POSIX, substitute `.\.venv\Scripts\python.exe` with `.venv/bin/python`).*

---

## Sub-Agent Memory Tracking & Selective Context Loading

Monolithic agent sessions suffer from context pollution: thousands of tokens of intermediate trial-and-error outputs degrade the model's reasoning. The Orchestrator resolves this by treating the **`project-memory`** MCP server as a **shared memory bus**:

```
                       ┌──────────────────────────────────────────────┐
                       │          Orchestrator Execution Hub          │
                       └──────────────┬────────────────┬──────────────┘
                                      │                │
            save_memory(output)       ▼                ▼       load_memory(useful)
       ┌─────────────────────────────────┐          ┌─────────────────────────────────┐
       │      Sub-Agent Output Track     │          │    Selective Stage Loading      │
       │                                 │          │                                 │
       │  • ledger: Architectural truths │          │  • category: "ledger"           │
       │  • sidecar: Active task state   │          │  • category: "sidecar"          │
       │  • journal: Recaps + Learnings  │          │  • hybrid search (40% semantic) │
       └─────────────────────────────────┘          └─────────────────────────────────┘
```

### 1. Tracking Sub-Agent Outputs (`save-memory`)

Every sub-agent saves distilled, high-signal results into one of 3 strict categories:

1. **`ledger` (Permanent Architectural Truths & Contracts)**:
   - Persisted primarily during `plan`, `architecturechecks`, and `securitychecks`.
   - Records non-negotiable constraints, database schema definitions, API signature contracts, authentication topologies, and security rules.
   - Example:
     ```json
     {
       "name": "save_memory",
       "arguments": {
         "category": "ledger",
         "title": "ADR: User Authentication & Token Signature Standards",
         "summary": "Mandated asymmetric RS256 JWT tokens with public key rotation, HttpOnly SameSite=Strict session cookies, and PKCE on OAuth 2.1 authorization code flow.",
         "learnings": "Symmetric HS256 secrets in multi-service architectures increase leak blast radius; RS256 enables verification without sharing signing keys.",
         "tags": ["architecture", "auth", "jwt", "adr", "security"]
       }
     }
     ```

2. **`sidecar` (Active WIP & Sub-Agent Handoff State)**:
   - Persisted during `develop`, `codereview`, and `troubleshoot-and-fix`.
   - Records current WIP status, modified files list, open review items, or active bug reproduction status.
   - Keeps immediate downstream sub-agents informed without dragging raw logs into the prompt.

3. **`journal` (Stage Recaps with Mandatory Learnings)**:
   - Persisted at the completion of **every** stage.
   - **Strict Requirement**: Must include **both** `summary` (what the stage accomplished) and **`learnings`** (specific traps discovered or mistakes avoided).
   - Example:
     ```json
     {
       "name": "save_memory",
       "arguments": {
         "category": "journal",
         "title": "Stage 4 (complexitychecks): Optimized Batch Membership Lookup",
         "summary": "Detected and resolved O(N^2) quadratic loop in batch permission validator by replacing array.includes() with a Set lookup.",
         "learnings": "Array.prototype.includes() inside loops turns O(N) operations into O(N^2); always convert lookups over large lists into Set or Map before iterating.",
         "tags": ["complexity", "quadratic-loop", "stage-4", "big-o", "learnings"]
       }
     }
     ```

### 2. Selectively Loading Useful Context (`load-memory`)

Downstream sub-agents must never receive raw upstream transcripts. Instead, the orchestrator selectively queries memory:

1. **Targeted Category Retrieval**:
   - Call `load_memory(category="ledger")` to retrieve core architecture rules and interface contracts before implementation (`develop`) or architecture checks (`architecturechecks`).
   - Call `load_memory(category="sidecar")` to pick up active WIP details before reviewing (`codereview`) or remediating (`troubleshoot-and-fix`).

2. **Domain-Specific Hybrid Search (40% Semantic + 60% Lexical)**:
   - Call `search_memory(query="...", limit=5)` to pull domain-specific past lessons and mistakes avoided on demand:
     - In `develop`: `search_memory("sqlite in-memory fixtures testbed")`
     - In `codereview`: `search_memory("cache stampede redis distributed lock")`
     - In `complexitychecks`: `search_memory("quadratic loop includes scan explain_query")`
     - In `architecturechecks`: `search_memory("premature abstraction 1:1 interface yagni")`
     - In `halucinationchecks`: `search_memory("phantom mock symbols ground truth")`
     - In `securitychecks`: `search_memory("child_process spawn shell command injection")`
     - In `troubleshoot-and-fix`: `search_memory("<error message or exception name>")`

3. **Post-Pipeline WIP Flush**:
   - Once all 7 stages pass and final delivery is verified, call `clear_sidecar` via `manage-memory` / `load-memory` to purge transient task state while preserving permanent `ledger` and `journal` entries.

---

## Context Handoff Protocol

Sub-agents are executed in isolated contexts. State and bounded handoff payloads are managed by the Context Manager.

> [!IMPORTANT]
> **Always run the Context Manager using the repository virtual environment:**
> - Windows: `.\.venv\Scripts\python.exe .github/skills/agent-orchestrator/scripts/orchestrator-context-manager.py <command>`
> - POSIX: `.venv/bin/python .github/skills/agent-orchestrator/scripts/orchestrator-context-manager.py <command>`

```bash
# Initialize a new pipeline run
.\.venv\Scripts\python.exe .github/skills/agent-orchestrator/scripts/orchestrator-context-manager.py init --task "<task-description>"

# Generate bounded context handoff payload for a stage
.\.venv\Scripts\python.exe .github/skills/agent-orchestrator/scripts/orchestrator-context-manager.py handoff --stage <stage-name>

# Run in-the-loop over-engineering audit on modified files
.\.venv\Scripts\python.exe .github/skills/agent-orchestrator/scripts/orchestrator-context-manager.py check-overengineering --file <path>

# Record stage completion and quality gate verdict
.\.venv\Scripts\python.exe .github/skills/agent-orchestrator/scripts/orchestrator-context-manager.py record --stage <stage-name> --status PASSED --summary "<summary>"

# Inspect pipeline status
.\.venv\Scripts\python.exe .github/skills/agent-orchestrator/scripts/orchestrator-context-manager.py status

# Generate final delivery report
.\.venv\Scripts\python.exe .github/skills/agent-orchestrator/scripts/orchestrator-context-manager.py report

# Periodically diagnose pending learnings for skill evolution
.\.venv\Scripts\python.exe .github/skills/agent-orchestrator/scripts/orchestrator-context-manager.py skill-doctor
```

---

## Step-by-Step Execution Workflow

### Step 1: Initialize Pipeline
1. Run `.\.venv\Scripts\python.exe .github/skills/agent-orchestrator/scripts/orchestrator-context-manager.py init --task "<task>"`.
2. Inspect workspace conventions and relevant memories:
   - Call `load_memory(category="ledger")` to retrieve permanent architectural rules.
   - Call `load_memory(category="sidecar")` to check for active WIP or recent task handoffs.

### Step 2: Stage 1 — `plan`
1. **Load Context**: Retrieve existing architecture decisions via `load_memory(category="ledger")` and past planning traps via `load_memory(category="journal", limit=3)`.
2. **Execute**: Invoke sub-agent with role `Architecture & Planning Specialist` and skill `architectural-planning`.
   - Produce system design, interface contracts, and list of files to create/modify.
   - Enforce KISS and YAGNI: reject speculative abstractions, unnecessary microservices, and unneeded caching layers during planning.
   - Consult `api-security` for auth topologies, `caching-queues-reviewer` for queue/cache resilience, `sql-executor` for indexing and schemas, and `llm-as-judge` for trade-off evaluation.
3. **Save Sub-Agent Output**:
   - Save interface contracts to `ledger`: `save_memory(category="ledger", title="ADR: ...", summary="...", learnings="...")`.
   - Record planning learnings to `journal`: `save_memory(category="journal", title="Stage 1 (plan) Recap", summary="...", learnings="...")`.
4. **Record Gate**:
   ```bash
   .\.venv\Scripts\python.exe .github/skills/agent-orchestrator/scripts/orchestrator-context-manager.py record --stage plan --status PASSED --summary "Plan approved: contracts defined" --artifact "plan.md"
   ```

### Step 3: Stage 2 — `develop`
1. **Load Context**: Generate handoff payload (`handoff --stage develop`).
   - Call `load_memory(category="ledger")` to pull the interface contracts and schema requirements established in `plan`.
   - Call `search_memory("<target-technology> gotchas pitfalls")` to retrieve past mistakes avoided.
2. **Execute**: Activate language developer skill (`python-developer`, `typescript-developer`, `react-developer`, `java-developer`, `csharp-developer`, `python-api-writer`, or `powershell-writer`).
   - For database fixtures, use `sql-connector` with ephemeral SQLite (`:memory:`) to seed fixtures without external dependencies.
   - Write production code and automated tests.
3. **In-The-Loop Over-Engineering Check**:
   - Run `check-overengineering` on all newly modified source files:
     ```bash
     .\.venv\Scripts\python.exe .github/skills/agent-orchestrator/scripts/orchestrator-context-manager.py check-overengineering --file "<modified-file>"
     ```
   - If over-engineering smells are detected (single-implementation interface, layer depth > 3, trampoline methods), inline or simplify them before proceeding.
4. **Save Sub-Agent Output**:
   - Save active state to `sidecar`: `save_memory(category="sidecar", title="WIP: Feature Implementation", summary="Touched files: [...]. All unit tests passing.", learnings="...")`.
   - Save implementation lessons to `journal`: `save_memory(category="journal", title="Stage 2 (develop) Recap", summary="...", learnings="...")`.
5. **Record Gate**:
   ```bash
   .\.venv\Scripts\python.exe .github/skills/agent-orchestrator/scripts/orchestrator-context-manager.py record --stage develop --status PASSED --summary "All unit tests passing, over-engineering checks clean"
   ```

### Step 4: Stage 3 — `codereview`
1. **Load Context**: Generate handoff payload (`handoff --stage codereview`).
   - Call `load_memory(category="sidecar")` to inspect the list of modified files and implementation notes.
   - Call `search_memory("code review patterns edge cases")` to review past review misses.
2. **Execute**: Invoke reviewer sub-agent with skill `code-reviewer` (supported by `detect-overengineering`, `python-linter`, `design-pattern-detector`).
   - Run `check-overengineering` on changed files in the diff to verify zero accidental complexity.
   - If PR touches queues or cache, activate `caching-queues-reviewer` to audit stampede protection and consumer idempotency.
   - Review against the 7 dimensions: logic correctness, error boundaries, edge cases, test quality, security, performance, and clean code.
3. **Save Sub-Agent Output**:
   - Save review findings to `journal`: `save_memory(category="journal", title="Stage 3 (codereview) Findings", summary="...", learnings="...")`.
4. **Record Gate**:
   ```bash
   .\.venv\Scripts\python.exe .github/skills/agent-orchestrator/scripts/orchestrator-context-manager.py record --stage codereview --status PASSED --summary "Clean code review: 0 blocking issues"
   ```

### Step 5: Stage 4 — `complexitychecks`
1. **Load Context**: Generate handoff payload (`handoff --stage complexitychecks`).
   - Call `search_memory("quadratic loop complexity bottleneck full table scan")` to recall relevant algorithmic traps.
2. **Execute**: Activate skill `algorithmic-complexity-analyzer`.
   - Audit worst-case Big-O time and space complexity ($O(1) \dots O(2^n)$).
   - Check for hidden quadratic loops (`array.includes()`, `in list` inside loops).
   - Check for array `.shift()` / queue-draining antipatterns and recursion depth traps.
   - Inspect database queries with `sql-executor` (`explain_query`) for unindexed $O(N)$ table scans.
3. **Save Sub-Agent Output**:
   - Save complexity optimizations to `journal`: `save_memory(category="journal", title="Stage 4 (complexitychecks) Audit", summary="...", learnings="...")`.
4. **Record Gate**:
   ```bash
   .\.venv\Scripts\python.exe .github/skills/agent-orchestrator/scripts/orchestrator-context-manager.py record --stage complexitychecks --status PASSED --summary "Complexity verified: O(n) time, O(1) auxiliary space"
   ```

### Step 6: Stage 5 — `architecturechecks` & Simplification Loop
1. **Load Context**: Generate handoff payload (`handoff --stage architecturechecks`).
   - Call `load_memory(category="ledger")` to compare implemented classes against architectural contracts and layering rules.
2. **Execute & In-The-Loop Simplification**:
   - Run `check-overengineering` across the target directory:
     ```bash
     .\.venv\Scripts\python.exe .github/skills/agent-orchestrator/scripts/orchestrator-context-manager.py check-overengineering --dir "<target-dir>" --max-score 40
     ```
   - **The Simplification Loop**: If over-engineering score is $\ge 40$:
     1. Analyze smells from `.overengineering-analysis/` report (trampoline methods, 1:1 interfaces, speculative params).
     2. Refactor code to collapse unnecessary layers and delete pass-through abstractions.
     3. Re-run `check-overengineering` until score is verified LOW (< 40).
3. **Save Sub-Agent Output**:
   - Save accepted structural conventions to `ledger`: `save_memory(category="ledger", title="Architectural Standard: ...", summary="...", learnings="...")`.
   - Save YAGNI learnings to `journal`: `save_memory(category="journal", title="Stage 5 (architecturechecks) Audit", summary="...", learnings="...")`.
4. **Record Gate**:
   ```bash
   .\.venv\Scripts\python.exe .github/skills/agent-orchestrator/scripts/orchestrator-context-manager.py record --stage architecturechecks --status PASSED --summary "Low over-engineering risk: score 12/100"
   ```

### Step 7: Stage 6 — `halucinationchecks`
1. **Load Context**: Generate handoff payload (`handoff --stage halucinationchecks`).
   - Call `load_memory(category="ledger")` to retrieve verified contracts and symbol declarations from `plan` and `develop`.
2. **Execute**: Activate skill `scan-halucinated-tests` (supported by `trace-code-context`).
   - Cross-reference all test imports, assertions, method calls, and mocks against ground-truth AST source symbols.
   - Verify 0 phantom symbols or hallucinated methods exist.
3. **Save Sub-Agent Output**:
   - Save mock verification learnings to `journal`: `save_memory(category="journal", title="Stage 6 (halucinationchecks) Audit", summary="...", learnings="...")`.
4. **Record Gate**:
   ```bash
   .\.venv\Scripts\python.exe .github/skills/agent-orchestrator/scripts/orchestrator-context-manager.py record --stage halucinationchecks --status PASSED --summary "0 hallucinated symbols detected"
   ```

### Step 8: Stage 7 — `securitychecks`
1. **Load Context**: Generate handoff payload (`handoff --stage securitychecks`).
   - Call `load_memory(category="ledger")` to inspect required security invariants and cryptographic baselines.
2. **Execute**: Activate skills `github-security-scanner-hook` and `api-security`.
   - Run `detect-secrets` scan for credentials, private keys, and tokens.
   - Run `semgrep` scan for OWASP injection flaws (command injection, path traversal, SQLi, XSS).
   - Audit API auth and cryptographic hygiene with `api-security` (JWT RS256/ES256, OAuth 2.1 PKCE, session cookie flags, mTLS).
   - Verify database operations with `sql-connector` (`audit_query_safety`) to guarantee zero destructive SQL (`DROP TABLE`, `DELETE *`).
3. **Save Sub-Agent Output**:
   - Save permanent security rules to `ledger`: `save_memory(category="ledger", title="Security Baseline: ...", summary="...", learnings="...")`.
   - Save security scan learnings to `journal`: `save_memory(category="journal", title="Stage 7 (securitychecks) Audit", summary="...", learnings="...")`.
4. **Record Gate**:
   ```bash
   .\.venv\Scripts\python.exe .github/skills/agent-orchestrator/scripts/orchestrator-context-manager.py record --stage securitychecks --status PASSED --summary "Security gate passed: 0 secrets, 0 vulnerabilities"
   ```

### Step 9: Final Delivery, Cleanup & Periodic Skill Evolution
1. Run `.\.venv\Scripts\python.exe .github/skills/agent-orchestrator/scripts/orchestrator-context-manager.py report`.
2. Call `clear_sidecar` via `manage-memory` / `load-memory` to flush transient task WIP, preserving permanent `ledger` and `journal` entries.
3. If the report shows `>= 3` pending unprocessed learnings or remediation ran during delivery, invoke `skill-doctor` (`orchestrator-context-manager.py skill-doctor`) to update or scaffold skills and mark learnings via `mark_learning_promoted`.
4. Present the user with the consolidated stage audit report and verified deliverables.

---

## Remediation Feedback Loop with `troubleshoot-and-fix` & Anti-Fix-Bloat

If any quality gate fails (`FAILED` or `BLOCKED`):
1. **Save Failure State to `sidecar`**: Save the failing stage diagnostics, file paths, and failure messages into `sidecar` so the remediation agent picks up immediate context.
2. **Search for Past Fixes**: Call `search_memory("<error or exception name>")` to check if a similar bug was previously encountered and resolved.
3. **Isolate with `troubleshoot-and-fix`**:
   - Activate **`troubleshoot-and-fix`**. For remote cluster or container integration failures, activate **`remote-pod-log-analyzer`**.
   - Generate an isolated reproduction harness (`scripts/isolate-runner.js` or `scripts/isolate-runner.py`) to systematically reproduce the defect outside monolithic project dependencies.
   - Verify the fix inside the reproduction sandbox.
4. **In-The-Loop Anti-Fix-Bloat Check**:
   - Before porting the fix back to the main repository, run `check-overengineering` on the modified files:
     ```bash
     .\.venv\Scripts\python.exe .github/skills/agent-orchestrator/scripts/orchestrator-context-manager.py check-overengineering --file "<patched-file>"
     ```
   - **Reject Fix Bloat**: Confirm that solving the defect did not introduce speculative wrappers, unnecessary exception hierarchies, or premature design patterns. Apply the minimal diff necessary.
5. **Respect the 3-Iteration Circuit Breaker**: If `troubleshoot-and-fix` fails to resolve the defect within its 3-iteration budget, do not loop indefinitely or burn tokens. Halt the pipeline immediately, revert unverified code churn, and surface the **Out of Options Summary** directly to the user for guidance.
6. **Re-evaluate Stages**: Once verified, re-run the affected pipeline stages until all quality gates pass, and record the remediation learnings in `journal`.

---

## References

- [Software Factory Agent](file:///.github/agents/software-factory-agent.md) — Autonomous end-to-end closed-loop agent coordinating all 37 skills and 3 MCP servers.
- [Skill Doctor](file:///.github/skills/skill-doctor/SKILL.md) — Periodic continuous learning skill that promotes `project-memory` learnings into skill updates or new skills.
- [Detect Overengineering](file:///.github/skills/detect-overengineering/SKILL.md) — Anti-bloat heuristics, YAGNI auditing, and deterministic signal extractor (`extract-signals.py`).
- [Save Memory](file:///.github/skills/save-memory/SKILL.md) — Persist high-signal project memory into `project-memory` (`ledger`, `sidecar`, `journal`).
- [Load Memory](file:///.github/skills/load-memory/SKILL.md) — Retrieve project memory and hybrid semantic search without context bloat.
- [Agent Orchestrator Reference Guide](file:///.github/skills/agent-orchestrator/references/agent-orchestrator-reference.md) — Architectural patterns, sub-agent prompts, and gate policies.
- [Context Manager Script](file:///.github/skills/agent-orchestrator/scripts/orchestrator-context-manager.py) — Stage execution state, in-the-loop over-engineering checker, and handoff manager.
- [Architectural Planning](file:///.github/skills/architectural-planning/SKILL.md) — System design, interface contracts, and ADR creation.
- [RAG Pipeline](file:///.github/skills/rag-pipeline/SKILL.md) — Chunking, hybrid search (BM25 + RRF), reranking, 5-layer testing strategy, and IR evaluation.
- [Researcher PoC Tester](file:///.github/skills/researcher-poc-tester/SKILL.md) — Empirical PoC benchmarking (`poc-stats-runner.py`) with P50/P95/P99 statistics.
- [Test Data Creator](file:///.github/skills/test-data-creator/SKILL.md) — Schema-aware SQL batch seeding (`sql-connector`), streaming JSON mocks, and Pareto skew generation.
- [Playwright Tester](file:///.github/skills/playwright-tester/SKILL.md) — Playwright E2E browser verification, POM, locators, and Trace Viewer.
- [BDD & Gherkin Tester](file:///.github/skills/bdd-gherkin-tester/SKILL.md) — Declarative Gherkin BDD specs and Playwright BDD adapter integration.
- [API Security Audit](file:///.github/skills/api-security/SKILL.md) — Universal API authentication, token security, and cryptographic audit.
- [Python API Writer](file:///.github/skills/python-api-writer/SKILL.md) — Production-grade FastAPI, Django, and Django Ninja endpoint engineering.
- [PowerShell Writer](file:///.github/skills/powershell-writer/SKILL.md) — Production-grade PowerShell scripts, advanced cmdlets, modules, and Pester v5 tests.
- [Caching & Queues Reviewer](file:///.github/skills/caching-queues-reviewer/SKILL.md) — Redis, Kafka, and RabbitMQ architecture and code review.
- [SQL Executor](file:///.github/skills/sql-executor/SKILL.md) — Multi-engine SQL query tuning, indexing, and validation.
- [SQL Connector MCP Server](file:///.github/skills/sql-connector/SKILL.md) — Multi-database query and schema inspection with zero-tolerance SQL guardrails.
- [Scan Hallucinated Tests](file:///.github/skills/scan-halucinated-tests/SKILL.md) — Ground-truth AST symbol verification for unit tests and mocks.
- [Remote Pod Log Analyzer](file:///.github/skills/remote-pod-log-analyzer/SKILL.md) — Remote Linux and Kubernetes pod log analysis via SSH, kubectl, and streaming toolkit.
- [Troubleshoot and Fix](file:///.github/skills/troubleshoot-and-fix/SKILL.md) — Isolated testbed reproduction and 3-iteration circuit breaker remediation.
