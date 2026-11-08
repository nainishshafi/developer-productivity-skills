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
- **Multi-Agent Consensus Panels**: Arbitrates high-stakes decisions across independent evaluator lenses (`First-Principles`, `Pragmatic Systems`, `Adversarial Verifier`).
- **Engineering Evaluator Archetypes (Pattern 7)**: Stress-tests proposals through specialized operational mindsets (Pessimist, Contrarian, Pragmatist, Specialist).

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
- *"Judge this implementation using the 4 Evaluator Archetypes (Pessimist, Contrarian, Pragmatist, Specialist)"*
- *"Compare these two algorithms head-to-head with position bias checks"*
- *"Is this RAG response grounded in the retrieved context? Identify unsupported claims."*
- *"Score this technical proposal 1–5 on correctness, efficiency, and security with anchored rubrics"*
- *"Run a 3-judge multi-agent consensus panel on this architectural change"*
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

### Example 1: Evaluator Archetypes Audit (Technical Proposal / Code)
```text
You: "Audit this proposed database worker change using the 4 Evaluator Archetypes:
[paste code change or ADR]
Evaluate through: Pessimist, Contrarian, Pragmatist, Specialist."
```

### Example 2: Bi-Directional Pairwise Comparison
```text
You: "Compare Option A and Option B for rate-limiting middleware.
Perform a bi-directional check to eliminate position and length bias.
Option A: [code_a]
Option B: [code_b]"
```

### Example 3: Claim-Level Hallucination & RAG Grounding Audit
```text
You: "Audit this generated answer for hallucinations against the retrieved context:
Context: [source documents]
Answer: [candidate answer]
Decompose into atomic claims and classify each as SUPPORTED, CONTRADICTED, or UNSUPPORTED."
```

### Example 4: Atomic Rubric Evaluation
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
- **Template 7**: Multi-Agent Consensus Panel (3 Independent Lenses + Aggregator)
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

## Version History

- **v1.5.0** (November 2026) — Added Pattern 7 Engineering Evaluator Archetypes (Pessimist, Contrarian, Pragmatist, Specialist), Template 9 multi-persona arbitration panels, and repository skill integration links.
- **v1.4.0** (November 2026) — Critique-first output ordering, cognitive bias mitigation protocol (position, verbosity, scale compression), and standard anchored 1–5 scales.
- **v1.3.0** (March 2026) — Improved sub-agent prompts with structured reasoning, confidence scoring, and richer aggregation analysis.
- **v1.2.0** (March 2026) — Multi-agent sequential evaluation for consensus-based verdicts.
- **v1.1.0** (March 2026) — Added rubric-based evaluation (primary), documented local repo sources.
- **v1.0.0** (March 2026) — Initial agent-native evaluation framework without external APIs.
