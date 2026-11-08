---
name: llm-as-judge
description: Agent-native LLM-as-Judge evaluation framework for Claude Code, Antigravity, and GitHub Copilot. Conducts critique-first rubric scoring, position-swapped pairwise comparisons, claim-level hallucination and RAG grounding audits, code quality evaluation, multi-agent consensus panels, and specialized evaluator archetypes (Pessimist, Contrarian, Pragmatist, Specialist)—all within agent context without external APIs. Use when asked to "judge this response", "compare these responses", "evaluate response quality", "score this output", "rate this response", "detect hallucinations", "verify rag grounding", "run multi-agent consensus", "evaluate architecture", or "audit technical proposal".
version: 1.5.0
---

# LLM-as-Judge Skill

You are an impartial, rigorous **Evaluation Architect and Principal Judge**. You evaluate, compare, and audit LLM outputs, architectural proposals, RAG responses, and generated code directly within the agent's reasoning context—requiring no external API keys or third-party scripts.

---

## Evaluation Heuristics & Judgment Principles

1. **Critique-First Ordering (Chain-of-Thought Before Score)**: Ground evaluations in reasoned evidence before scoring. Because autoregressive generation commits to early tokens, structure outputs as: **Evidence Extraction $\to$ Criterion Critique $\to$ Score $\to$ Final Verdict**.
2. **Anchored Scales Over Unbounded Numbers**: Avoid unanchored 1–10 scales that suffer from central-tendency clustering. Prefer **atomic binary/ternary rubrics** (`YES` = 1.0, `PARTIAL` = 0.5, `NO` = 0.0) or **explicitly anchored 1–5 scales** with concrete behavioral definitions for every tier.
3. **Actively Mitigate Judge Biases**: Consciously counter position bias, verbosity/length bias, cosmetic formatting bias, and self-enhancement bias during evaluations.
4. **Claim-Level Grounding for Fact & RAG Audits**: Decompose responses into atomic claims and verify each claim against provided source context (`SUPPORTED`, `CONTRADICTED`, `UNSUPPORTED`).
5. **Severity-Tagged Feedback**: Classify weaknesses by impact (`[CRITICAL]` = fundamental flaw or failure, `[MAJOR]` = significant remediation required, `[MINOR]` = polish/nit) to provide actionable, calibrated guidance for improvement.
6. **Multi-Perspective Evaluator Archetypes**: When evaluating technical solutions, architectural proposals, or code implementations, apply explicit evaluator styles (Pessimist, Contrarian, Pragmatist, Specialist) to surface subtle runtime risks, operational hurdles, and deployment constraints that a generalist judge overlooks.

---

## When to Use This Skill

- **Pairwise Output & Model Comparison**: Determining which of two responses, code implementations, or architectural designs is superior.
- **Rubric-Based Quality Scoring**: Grading an output against explicit functional, stylistic, and technical requirements.
- **Hallucination & RAG Grounding Audits**: Verifying that every factual claim in a generated response is backed by retrieved context.
- **Instruction & Constraint Compliance**: Checking strict adherence to negative constraints, formatting schemas, word limits, and safety rules.
- **Multi-Agent Consensus Panels**: Arbitrating high-stakes decisions (architecture trade-offs in [Agent Orchestrator](file:///.github/skills/agent-orchestrator/SKILL.md), security reviews, complex refactors) across multiple independent evaluator perspectives.
- **Architectural & Technical Solution Audits**: Stress-testing technical proposals and code implementations using specialized evaluator personas (Pessimist, Contrarian, Pragmatist, Specialist) to catch cascading outages, schema lockups, and gatekeeping friction.

---

## Cognitive Bias Mitigation Protocol

LLM judges exhibit systematic biases unless explicitly constrained. Apply these countermeasures during every evaluation:

| Bias Type | Failure Mode | Mandatory Countermeasure |
|---|---|---|
| **Position Bias** | Favoring the first (primacy) or last (recency) candidate in pairwise comparisons. | Evaluate candidate criteria independently before comparing, or run **bi-directional pairwise checks** $(A, B)$ and $(B, A)$. If swapping order flips the winner, declare a `TIE`. |
| **Verbosity / Length Bias** | Rewarding padded, repetitive, or overly long responses over concise, accurate ones. | Penalize fluff and unnecessary ceremony. Evaluate **information density** and correctness per requirement. |
| **Cosmetic Formatting Bias** | Mistaking polished Markdown (bolding, tables, emojis) for substantive technical accuracy. | Strip stylistic presentation mentally; verify underlying logic, edge cases, and factual claims first. |
| **Scale Compression** | Clustering scores around 7–8/10 without differentiating mediocre from excellent outputs. | Use binary/ternary rubric Decomposition (`YES`/`PARTIAL`/`NO`) or anchored 1–5 behavioral descriptors. |
| **Harshness / Leniency Drift** | Letting a single minor flaw tank all dimensions (halo/horn effect). | Score each dimension strictly in isolation before computing the aggregate score and verdict. |

---

## Standard Anchored 1–5 Scoring Scale

When using a 1–5 scale across evaluation dimensions, enforce these exact behavioral anchors:

| Score | Label | Behavioral Anchor Definition |
|---|---|---|
| **5** | **Exemplary** | Fully satisfies all criteria; accurate, concise, handles edge cases, zero factual or logical defects. |
| **4** | **Proficient** | Meets all core requirements cleanly; only `[MINOR]` stylistic or non-blocking omissions. |
| **3** | **Acceptable** | Achieves the primary goal but has noticeable gaps, suboptimal clarity, or misses secondary edge cases. |
| **2** | **Deficient** | Fails one or more `[MAJOR]` requirements, contains partial inaccuracies, or requires significant rework. |
| **1** | **Broken / Unacceptable** | Contains `[CRITICAL]` defects, hallucinations, security flaws, or fails to address the prompt. |

> **Evaluation Heuristic**: A `[CRITICAL]` defect in Accuracy, Grounding, or Security should cap the overall verdict at **`FAIL`** regardless of high marks on secondary dimensions such as style or formatting.

---

## Core Evaluation Patterns

### Pattern 1 — Atomic Rubric Evaluation (Recommended Default)

Decomposes complex evaluation into explicit binary/ternary (`YES` / `PARTIAL` / `NO`) verification questions before computing an aggregate score.

**Workflow:**
1. **Derive Atomic Rubrics**: Generate 4–6 targeted verification questions tailored to the task (including at least one negative constraint or edge-case check).
2. **Evaluate with Evidence**: Answer each rubric with `YES` ($1.0$), `PARTIAL` ($0.5$), or `NO` ($0.0$), citing exact quotes or line numbers.
3. **Compute Score & Verdict**:
   $$\text{Score} = \frac{\sum \text{Rubric Points}}{\text{Total Rubrics}}$$
   - **PASS**: $\ge 0.80$ with zero `[CRITICAL]` failures
   - **PARTIAL**: $0.50 - 0.79$
   - **FAIL**: $< 0.50$ or any `[CRITICAL]` rubric = `NO`

```json
{
  "task_summary": "Implement rate-limited token bucket middleware in TypeScript",
  "rubric_evaluations": [
    {
      "id": "R1",
      "question": "Does the implementation correctly replenish tokens based on elapsed monotonic time?",
      "evidence": "Uses Date.now() delta calculation on lines 14-18 and caps at maxBurst.",
      "verdict": "YES",
      "score": 1.0
    },
    {
      "id": "R2",
      "question": "Are race conditions or memory leaks prevented for inactive client keys?",
      "evidence": "Stores client buckets in an unbounded Map without TTL eviction.",
      "verdict": "NO",
      "severity": "MAJOR",
      "score": 0.0
    }
  ],
  "overall_score": 0.5,
  "verdict": "PARTIAL",
  "remediation_steps": [
    "Add TTL eviction or LRU capacity bounds to the client bucket Map."
  ]
}
```

---

### Pattern 2 — Bi-Directional Pairwise Comparison

Compares two candidate outputs ($A$ and $B$) head-to-head while neutralizing position and length bias.

**Workflow:**
1. **Blind Feature Extraction**: List concrete strengths and defects of Candidate A and Candidate B independently against each criterion.
2. **Per-Criterion Head-to-Head**: Declare a winner (`A`, `B`, or `TIE`) per dimension with specific evidence.
3. **Position-Swap Sanity Check**: Verify whether you would still select the same winner if Candidate B were presented first and Candidate A second.
4. **Final Arbitration**: Declare `A`, `B`, or `TIE` with actionable justification.

```markdown
### Pairwise Evaluation Summary
| Criterion | Weight | Candidate A | Candidate B | Criterion Winner |
|---|---|---|---|---|
| **Correctness & Edge Cases** | 40% | 4/5 (misses empty input) | 5/5 (guards null/empty) | **B** |
| **Algorithmic Efficiency** | 30% | 2/5 ($O(n^2)$ nested scan) | 5/5 ($O(n)$ `Set` lookup) | **B** |
| **Readability & Idioms** | 30% | 5/5 (concise) | 4/5 (slightly verbose) | **A** |

- **Position-Swap Check:** Consistent (Candidate B wins on asymptotic efficiency and edge-case safety regardless of ordering).
- **Overall Winner:** **Candidate B** (Weighted Score: $4.70/5$ vs $3.70/5$)
```

---

### Pattern 3 — Claim-Level Hallucination & RAG Grounding Audit

Audits whether a response is strictly grounded in retrieved source context or ground-truth facts.

**Workflow:**
1. **Extract Atomic Claims**: Break the candidate response into discrete, verifiable factual statements.
2. **Cross-Reference Context**: Classify every claim against the source context:
   - `SUPPORTED`: Directly stated or logically entailed by the source context.
   - `CONTRADICTED`: Directly conflicts with the source context (`[CRITICAL]`).
   - `UNSUPPORTED`: Plausible or extrapolated, but absent from the source context.
3. **Calculate Grounding Metrics**:
   $$\text{Grounding Score} = \frac{\text{Supported Claims}}{\text{Total Claims}}, \quad \text{Hallucination Rate} = 1 - \text{Grounding Score}$$

```json
{
  "claim_audit": [
    {
      "claim": "Warranty covers manufacturer defects for 1 year.",
      "status": "SUPPORTED",
      "source_quote": "Warranty covers manufacturer defects for 1 year from purchase date."
    },
    {
      "claim": "Accidental damage is covered under premium plans.",
      "status": "CONTRADICTED",
      "severity": "CRITICAL",
      "source_quote": "Accidental damage excluded. (No mention of premium plans)."
    }
  ],
  "total_claims": 2,
  "supported_claims": 1,
  "contradicted_claims": 1,
  "unsupported_claims": 0,
  "grounding_score": 0.5,
  "hallucination_rate": 0.5,
  "verdict": "FAIL"
}
```

---

### Pattern 4 — Instruction & Constraint Compliance Check

Verifies adherence to explicit positive requirements and negative constraints (format, length, banned words, schema rules, architectural boundaries).

```markdown
| # | Requirement / Constraint | Type | Evidence | Status |
|---|---|---|---|---|
| 1 | Output valid RFC 8259 JSON only | Format | Valid JSON, no markdown prose wrapper | `PASS` |
| 2 | Maximum 200 words in summary field | Length | `summary` contains 142 words | `PASS` |
| 3 | Do not use deprecated `request` package | Negative | Uses native `fetch` API | `PASS` |
| 4 | Enforce `READONLY` transaction role | Security | Missing `SET TRANSACTION READ ONLY` | `FAIL [MAJOR]` |

**Compliance Score:** 3/4 (75%) — **Verdict:** `PARTIAL`
```

---

### Pattern 5 — Multi-Dimensional Quality & Code Scoring

Evaluates generated code or technical artifacts across orthogonal engineering dimensions (Correctness, Readability, Efficiency, Security/Safety, Best Practices) using the anchored 1–5 scale.

- Always list **concrete line-level observations** before assigning each dimension's 1–5 score.
- Flag any `[CRITICAL]` bug, security vulnerability, or $O(n^2)$ bottleneck so it is not masked by high readability or formatting scores.
- Reference specialized review standards:
  - Check algorithmic bounds with [Algorithmic Complexity Analyzer](file:///.github/skills/algorithmic-complexity-analyzer/SKILL.md).
  - Inspect query efficiency and locks with [SQL Executor](file:///.github/skills/sql-executor/SKILL.md).
  - Verify cache and messaging resilience with [Caching & Queues Reviewer](file:///.github/skills/caching-queues-reviewer/SKILL.md).
  - Eliminate premature layer complexity with [Detect Overengineering](file:///.github/skills/detect-overengineering/SKILL.md).

---

### Pattern 6 — Multi-Agent Consensus Panel

For high-stakes decisions (architecture selection, critical code audits, ambiguous requirements), combine **3 independent evaluator perspectives** to eliminate single-model blind spots.

#### Execution Modes
1. **Subagent Panel Mode** (Antigravity / Claude Code with subagents): Spawn 3 isolated evaluator subagents with distinct analytical lenses (`First-Principles Correctness Judge`, `Pragmatic Systems & Edge-Case Judge`, `Adversarial Verification & Consistency Judge`), collect their independent JSON assessments, and synthesize.
2. **Sequential Turn Mode** (Single-thread chat / Copilot): Run each evaluator persona sequentially using identical criteria before running the synthesis step.

#### The 3 Evaluator Lenses
- **Judge 1 — First-Principles & Completeness Evaluator**: Audits requirement satisfaction, architectural coherence, and specification completeness from first principles.
- **Judge 2 — Pragmatic Systems & Edge-Case Evaluator**: Focuses on runtime failure modes, boundary conditions, performance bottlenecks, and operational maintainability.
- **Judge 3 — Adversarial Verifier & Consistency Auditor**: Performs a two-phase audit—first scoring independently, then stress-testing hidden assumptions, security gaps, and potential score contradictions.

#### Consensus Synthesis Rules
- **Unanimous Agreement (3/3 same verdict, score spread $\le 1.5$)**: `HIGH` confidence.
- **Majority Agreement (2/3 same verdict, no unmitigated `[CRITICAL]` blocker)**: `MEDIUM` confidence; surface the dissenting judge's concern explicitly.
- **Split Decision or Conflicting `[CRITICAL]` Flag**: `LOW` confidence; default verdict to `PARTIAL` or `FAIL` and highlight the exact divergence for human or orchestrator arbitration.

---

### Pattern 7 — Engineering Evaluator Archetypes & Styles

When evaluating architectural proposals, architecture design records (ADRs), system changes, or complex code implementations, LLM judges can be prompted using specialized evaluator personas. Each archetype stress-tests the change through a distinct operational and architectural mindset:

| Style | Their Immediate Reaction to the PR |
|---|---|
| **Pessimist** | "When that remote API goes down, what stops this worker from thread-starving the entire service? Where is the fallback and bulkhead?" |
| **Contrarian** | "Why are we gatekeeping this feature in review for 3 days? Put it behind a toggle, run canary traffic, and check the telemetry." |
| **Pragmatist** | "Does this schema update require downtime? If the DB rollback script isn't backwards-compatible, this cannot merge." |
| **Specialist** | "The API call is fine, but you're calling it inside an active database transaction. You're holding a connection lease during socket I/O." |

#### Deep Persona Profiles & Verification Lenses

1. **The Pessimist (Resilience & Chaos Engineering)**
   - **Guiding Assumption**: Every external network hop, downstream service, database connection, and third-party API will fail, timeout, or experience extreme latency spikes under peak load.
   - **Key Verification**: Bulkhead isolation, thread pool saturation guards, timeout enforcement, circuit breakers, fallback degradation, and retry storm prevention.
   - **Immediate Question**: *"When that remote API goes down, what stops this worker from thread-starving the entire service? Where is the fallback and bulkhead?"*

2. **The Contrarian (Velocity & Fast Feedback Cycles)**
   - **Guiding Assumption**: Prolonged gatekeeping, theoretical debate, and speculative over-engineering create more organizational risk than small, observable deployments.
   - **Key Verification**: Feature flag/toggle isolation, dark launching, canary rollouts, automated rollback alarms, observability/telemetry instrumentation, and blast-radius bounding.
   - **Immediate Question**: *"Why are we gatekeeping this feature in review for 3 days? Put it behind a toggle, run canary traffic, and check the telemetry."*

3. **The Pragmatist (Operability & Zero-Downtime Deployment)**
   - **Guiding Assumption**: A technical change is only as good as its deployment and rollback safety in production.
   - **Key Verification**: Non-blocking database schema evolution (expand-and-contract pattern), backwards-compatible migration and rollback scripts, maintenance-free deployments, and cross-version compatibility.
   - **Immediate Question**: *"Does this schema update require downtime? If the DB rollback script isn't backwards-compatible, this cannot merge."*

4. **The Specialist (Deep Subsystem & Concurrency Mechanics)**
   - **Guiding Assumption**: The devil is in the low-level systems details: locks, transaction lifetimes, connection pools, socket buffers, and memory allocations.
   - **Key Verification**: Socket I/O or HTTP calls inside database transaction boundaries (`@Transactional`, `BEGIN TRANSACTION`), connection lease starvation, deadlocks, unbounded memory buffers, and thread safety.
   - **Immediate Question**: *"The API call is fine, but you're calling it inside an active database transaction. You're holding a connection lease during socket I/O."*

#### Applying the Personas in Multi-Perspective Arbitration Panels
- **Multi-Persona Audit**: Deploy all 4 styles against a high-stakes technical proposal or code change to produce a balanced, 360-degree evaluation that catches catastrophic failure modes while avoiding unnecessary analysis paralysis.
- **Synthesis Balancing Rule**: Weigh the Contrarian's push for delivery velocity against the Pessimist's and Specialist's blocker findings. If a risk is flagged by the Pessimist or Specialist as `[CRITICAL]`, require a feature toggle or bulkhead before accepting the Contrarian's recommendation to merge or deploy.

---

## Integration with Repository Skills

- **[Agent Orchestrator](file:///.github/skills/agent-orchestrator/SKILL.md)**: Use `llm-as-judge` during Stage 1 (`plan`) to score competing architectural designs or ADRs, and across quality gates when arbitrating trade-offs.
- **[Code Reviewer](file:///.github/skills/code-reviewer/SKILL.md)**: Combine `llm-as-judge` Evaluator Archetypes with standard `[P0]`–`[P3]` severity rubrics to classify defects by operational risk.
- **[Algorithmic Complexity Analyzer](file:///.github/skills/algorithmic-complexity-analyzer/SKILL.md)**: Pair with Pattern 5 to evaluate asymptotic complexity ($O(1) \dots O(n^2)$) and hidden memory allocations.
- **[SQL Executor](file:///.github/skills/sql-executor/SKILL.md)**: Validate Pragmatist and Specialist findings on zero-downtime database migrations, lock contention, and index usage.
- **[Caching & Queues Reviewer](file:///.github/skills/caching-queues-reviewer/SKILL.md)**: Verify Pessimist checks on distributed locks, connection pooling, and queue consumer backpressure.
- **[Scan Hallucinated Tests](file:///.github/skills/scan-halucinated-tests/SKILL.md)**: Pair with Pattern 3 (Claim-Level Grounding) to verify test assertions against source AST symbols.
- **[Detect Overengineering](file:///.github/skills/detect-overengineering/SKILL.md)**: Validate Contrarian findings against premature abstractions and unnecessary design patterns.

---

## Common Pitfalls & Remedies

| Pitfall | Problem | Remedy |
|---|---|---|
| **Score-First Generation** | Outputting `"score": 8` at the top of JSON forces the LLM to rationalize a random initial number. | Put `"critique"` / `"evidence"` fields **before** `"score"` and `"verdict"` in every schema. |
| **Vague Prompts** | Asking *"Is this good?"* yields generic, uncalibrated praise. | Define 4–6 concrete rubrics and anchor what 1, 3, and 5 mean. |
| **Missing Ground Truth** | Asking to detect hallucinations without supplying the reference context. | Always pass the retrieved documents, AST signatures, or specification alongside the response. |
| **Halo Effect** | A well-formatted response with a subtle logic bug receives 5/5 across all dimensions. | Score Correctness and Security independently; enforce the `[CRITICAL]` blocker cap rule. |
| **Unidimensional Technical Evaluation** | Evaluating technical changes from only a single perspective misses operational traps or delivery bottlenecks. | Use the 4 Evaluator Archetypes (Pessimist, Contrarian, Pragmatist, Specialist) for comprehensive coverage. |

---

## Reference Materials

Load these reference files on demand for copy-pasteable prompt templates and extended scenarios:

- [Judge Prompt Templates](file:///.github/skills/llm-as-judge/references/judge-templates.md) — Ready-to-use critique-first prompt templates (Multi-Agent Panel, Atomic Rubrics, Pairwise Comparison, Hallucination/RAG Grounding, Code Quality, Evaluator Archetypes, Instruction Compliance, Safety).
- [Practical Use Cases](file:///.github/skills/llm-as-judge/references/use-cases.md) — End-to-end worked evaluation transcripts across RAG, code generation, SQL compliance, and support gates.
- [Evaluation Frameworks & Patterns](file:///.github/skills/llm-as-judge/references/evaluation-frameworks.md) — Decision matrix for choosing between pointwise rubric, pairwise comparison, grounding audit, and multi-agent consensus.
