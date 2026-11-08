# LLM-as-Judge Skill — Agent-Native Evaluation Framework

## Overview

The `llm-as-judge` skill enables AI agents (Antigravity, Claude Code, GitHub Copilot) to evaluate, audit, and compare outputs, architectural designs, RAG responses, code quality, and technical proposals directly within reasoning context—**requiring zero external API calls or third-party scripts**.

---

## What It Is

An **agent-native evaluation engine** that provides structured judgment protocols:
- **Critique-First Ordering**: Evidence extraction and chain-of-thought always precede numerical scores to prevent autoregressive bias.
- **Bi-Directional Pairwise Comparisons**: Neutralizes position, recency, and verbosity bias when comparing two candidates.
- **Anchored 1–5 Scoring Scales**: Concrete behavioral anchors (`5=Exemplary` to `1=Broken`) with automatic `[CRITICAL]` blocker gates.
- **Claim-Level Grounding & RAG Audits**: Decomposes responses into atomic claims verified against retrieved source context.
- **3-Model Consensus Checks (Pattern 6)**: Arbitrates high-stakes decisions across 3 independent models/lenses (`Claude Sonnet`, `GPT-5.4`, `Gemini Pro`).
- **Engineering Evaluator Archetypes (Pattern 7)**: Stress-tests proposals through specialized operational mindsets (`Pessimist`, `Contrarian`, `Pragmatist`, `Specialist`).

---

## 3-Model Consensus Check & Multi-Agent Evaluation

For critical decisions (architectural selection, security audits, ambiguous requirements), invoke **3 independent models or evaluator lenses** to eliminate single-model blind spots:

```
You: "Evaluate this implementation with 3 models (Claude Sonnet, GPT-5.4, Gemini Pro) for consensus"

Agent 1 (Claude Sonnet — First-Principles Lens): Score: 4.5/5 → Verdict: PASS
Agent 2 (GPT-5.4 — Pragmatic Systems Lens):     Score: 4.0/5 → Verdict: PASS  
Agent 3 (Gemini Pro — Adversarial Verifier):    Score: 3.5/5 → Verdict: PARTIAL (flags unhandled connection timeout)

Consensus: Score: 4.0/5, PASS with remediation (Confidence: MEDIUM)
Unique Insight (Agent 3): Socket timeout unhandled during connection handshake
```

### Why the 3-Model Check?
- **Cross-Model Family Diversity**: Evaluating across distinct model families (Anthropic Claude, OpenAI GPT, Google Gemini) catches blind spots that a single model rationalizes.
- **3 Orthogonal Evaluator Lenses**:
  - **Judge 1 (Claude Sonnet — First-Principles & Completeness)**: Audits requirement satisfaction, logical soundness, and specification completeness from first principles.
  - **Judge 2 (GPT-5.4 — Pragmatic Systems & Edge Cases)**: Audits runtime failure modes, operational risks, boundary conditions, and maintainability.
  - **Judge 3 (Gemini Pro — Adversarial Verifier & Consistency)**: Executes two-phase verification—first evaluating independently, then stress-testing hidden assumptions and verifying internal score consistency.
- **Execution Modes**:
  1. **Subagent Panel Mode** (Antigravity / Claude Code with subagents): Spawns 3 isolated subagents in parallel with distinct lenses, collects JSON assessments, and synthesizes.
  2. **Sequential Turn Mode** (Single-thread chat / Copilot): Invokes each evaluator persona sequentially using identical criteria before running the aggregator.
- **Consensus Metrics**:
  - **Unanimous Agreement (3/3 same verdict, score spread $\le 1.5$)**: `HIGH` confidence.
  - **Majority Agreement (2/3 same verdict, no unmitigated `[CRITICAL]` blocker)**: `MEDIUM` confidence; surfaces the dissenting judge's exact finding.
  - **Split Decision or Conflicting `[CRITICAL]` Flag**: `LOW` confidence; gates merge until human or orchestrator resolution.

---

## Engineering Evaluator Archetypes & Styles

When evaluating system proposals, architecture design records (ADRs), or complex code changes, generalist evaluations can overlook operational edge cases or delivery velocity trade-offs. The judge adopts 4 specialized engineering lenses:

| Style | Their Immediate Reaction to the PR | Core Focus & Verification Lens |
|---|---|---|
| **Pessimist** | *"When that remote API goes down, what stops this worker from thread-starving the entire service? Where is the fallback and bulkhead?"* | Worst-case failure modes, cascading dependency failures, circuit breaking, bulkheads, thread pool exhaustion, retry amplification. |
| **Contrarian** | *"Why are we gatekeeping this feature in review for 3 days? Put it behind a toggle, run canary traffic, and check the telemetry."* | Velocity vs. gatekeeping, blast-radius containment, canary rollouts, feature flags, observability/telemetry instrumentation. |
| **Pragmatist** | *"Does this schema update require downtime? If the DB rollback script isn't backwards-compatible, this cannot merge."* | Zero-downtime deployments, non-blocking schema evolution (expand-and-contract), rollback scripts, operational maintainability. |
| **Specialist** | *"The API call is fine, but you're calling it inside an active database transaction. You're holding a connection lease during socket I/O."* | Deep subsystem traps, resource contention, database transactions, connection pool exhaustion, blocking socket I/O. |

---

## When to Use

Invoke this skill by asking your agent prompts such as:
- *"Run a 3-model consensus check (Claude Sonnet, GPT-5.4, Gemini Pro) on this architectural change"*
- *"Judge this implementation using the 4 Evaluator Archetypes (Pessimist, Contrarian, Pragmatist, Specialist)"*
- *"Compare these two algorithms head-to-head with position bias checks"*
- *"Is this RAG response grounded in the retrieved context? Identify unsupported claims."*
- *"Score this technical proposal 1–5 on correctness, efficiency, and security with anchored rubrics"*
- *"Audit instruction and negative constraint compliance on this output"*

---

## Files in This Skill

```
.github/skills/llm-as-judge/
├── SKILL.md                          Core skill documentation, heuristics & patterns
├── CHANGELOG.md                      Version release history (v1.0.0 – v1.5.0)
├── README.md                         Quickstart guide, archetype reference & FAQ
└── references/
    ├── evaluation-frameworks.md      Pattern decision matrix & pointwise vs pairwise guide
    ├── judge-templates.md            9 ready-to-use critique-first prompt templates
    └── use-cases.md                  End-to-end worked transcripts across real tasks
```

---

## Quick Start Examples

### Example 1: 3-Model Consensus Check
```text
You: "Run a 3-model consensus evaluation on this database migration design:
- Judge 1 (Claude Sonnet Lens): First-principles correctness & specification completeness
- Judge 2 (GPT-5.4 Lens): Pragmatic runtime failure modes & edge cases
- Judge 3 (Gemini Pro Lens): Adversarial verification & hidden assumptions
Synthesize findings into consensus metrics and verdict."
```

### Example 2: Evaluator Archetypes Audit
```text
You: "Audit this proposed database worker change using the 4 Evaluator Archetypes:
[paste code change or ADR]
Evaluate through: Pessimist, Contrarian, Pragmatist, Specialist."
```

### Example 3: Bi-Directional Pairwise Comparison
```text
You: "Compare Option A and Option B for rate-limiting middleware.
Perform a bi-directional check to eliminate position and length bias.
Option A: [code_a]
Option B: [code_b]"
```

### Example 4: Claim-Level Hallucination & RAG Grounding Audit
```text
You: "Audit this generated answer for hallucinations against the retrieved context:
Context: [source documents]
Answer: [candidate answer]
Decompose into atomic claims and classify each as SUPPORTED, CONTRADICTED, or UNSUPPORTED."
```

### Example 5: Atomic Rubric Evaluation
```text
You: "Score this TypeScript function using 4 atomic binary rubrics (YES / PARTIAL / NO):
1. Does it guard against null/empty inputs?
2. Is time complexity O(n) or better?
3. Are open file streams cleanly closed?
4. Are credentials kept out of logs?"
```

---

## Standard Anchored 1–5 Scoring Scale

| Score | Label | Behavioral Anchor Definition |
|:---:|---|---|
| **5** | **Exemplary** | Fully satisfies all criteria; accurate, concise, handles edge cases, zero defects. |
| **4** | **Proficient** | Meets core requirements cleanly; only `[MINOR]` non-blocking omissions. |
| **3** | **Acceptable** | Achieves primary goal but has noticeable gaps or suboptimal edge-case handling. |
| **2** | **Deficient** | Fails one or more `[MAJOR]` requirements, contains partial inaccuracies, requires rework. |
| **1** | **Broken / Unacceptable** | Contains `[CRITICAL]` defects, hallucinations, security flaws, or fails prompt. |

> **Evaluation Rule**: A `[CRITICAL]` defect in Accuracy, Grounding, or Security caps the overall verdict at **`FAIL`** regardless of secondary dimension scores.

---

## Prompt Templates Reference

Browse [`references/judge-templates.md`](file:///.github/skills/llm-as-judge/references/judge-templates.md) for ready-to-use critique-first JSON templates:
- **Template 1**: Atomic Rubric-Based Evaluation (Recommended Default)
- **Template 2**: Bi-Directional Pairwise Comparison (Position-Bias Resistant)
- **Template 3**: Claim-Level Hallucination & RAG Grounding Audit
- **Template 4**: Pointwise Quality Dimension Scoring
- **Template 5**: Code Quality & Architectural Merit Evaluation
- **Template 6**: Instruction & Negative Constraint Compliance
- **Template 7**: Multi-Agent Consensus Panel (3 Independent Lenses: Claude, GPT, Gemini + Synthesis Aggregator)
- **Template 8**: Safety, Policy & Toxicity Audit
- **Template 9**: Evaluator Archetypes Panel (Pessimist, Contrarian, Pragmatist, Specialist)

---

## Repository Skill Integrations

- **[Agent Orchestrator](file:///.github/skills/agent-orchestrator/SKILL.md)**: Gatekeep ADR trade-offs and verify quality gates in Stage 1 (`plan`) and Stage 3 (`verify`).
- **[Code Reviewer](file:///.github/skills/code-reviewer/SKILL.md)**: Combine Evaluator Archetypes with standard `[P0]`–`[P3]` priority tags.
- **[Algorithmic Complexity Analyzer](file:///.github/skills/algorithmic-complexity-analyzer/SKILL.md)**: Evaluate $O(n \log n)$ bounds and memory leaks.
- **[SQL Executor](file:///.github/skills/sql-executor/SKILL.md)**: Validate Pragmatist and Specialist findings on zero-downtime migrations and connection pooling.
- **[Caching & Queues Reviewer](file:///.github/skills/caching-queues-reviewer/SKILL.md)**: Verify Pessimist checks on distributed locks, fallback bulkheads, and dead-letter queues.

---

## Frequently Asked Questions (FAQ)

**Q: What is the 3-model check and when should I use it?**  
A: It combines 3 independent evaluations—either across different model families (`Claude Sonnet`, `GPT-5.4`, `Gemini Pro`) or using 3 distinct analytical lenses (`First-Principles`, `Pragmatic Systems`, `Adversarial Verifier`)—to eliminate single-model blind spots. Use it for high-stakes architecture selections, security evaluations, and complex trade-offs.

**Q: How does the 3-model check run if my IDE only runs one model?**  
A: In tools supporting subagents (Antigravity, Claude Code), it spawns 3 isolated subagent tasks concurrently. In single-model chats or GitHub Copilot, it runs in **Sequential Turn Mode**, where the agent sequentially assumes each evaluator lens before aggregating consensus.

**Q: How do the 3-Model Check and the 4 Evaluator Archetypes relate?**  
A: They complement each other:
- The **3-Model Check (Pattern 6)** is an *arbitration protocol* (independent evaluations $\to$ agreement threshold $\to$ synthesis).
- The **4 Evaluator Archetypes (Pattern 7)** are *domain-specific engineering lenses* (`Pessimist`, `Contrarian`, `Pragmatist`, `Specialist`) that provide the exact critical questions to ask when evaluating production code and architectural proposals.

---

## Version History

- **v1.5.0** (November 2026) — Added Pattern 7 Engineering Evaluator Archetypes (Pessimist, Contrarian, Pragmatist, Specialist), Template 9 multi-persona arbitration panels, and repository skill integration links.
- **v1.4.0** (November 2026) — Critique-first output ordering, cognitive bias mitigation protocol (position, verbosity, scale compression), and standard anchored 1–5 scales.
- **v1.3.0** (March 2026) — Improved sub-agent prompts with structured reasoning, confidence scoring, and richer aggregation analysis (Claude Sonnet, GPT-5.4, Gemini Pro).
- **v1.2.0** (March 2026) — Multi-agent sequential evaluation for consensus-based verdicts.
- **v1.1.0** (March 2026) — Added rubric-based evaluation (primary), documented local repo sources.
- **v1.0.0** (March 2026) — Initial agent-native evaluation framework without external APIs.
