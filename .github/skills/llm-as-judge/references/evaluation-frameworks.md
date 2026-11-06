# Evaluation Frameworks & Pattern Selection Matrix

Reference guide for choosing the right agent-native LLM-as-Judge evaluation strategy within Claude Code, Antigravity, or GitHub Copilot.

---

## Decision Matrix: Choosing an Evaluation Pattern

| Evaluation Goal | Recommended Pattern | Primary Output | Bias Risk to Watch |
|---|---|---|---|
| **Grade a single output with high explainability** | **Pattern 1: Atomic Rubric Evaluation** | Binary/ternary (`YES`/`PARTIAL`/`NO`) table + percentage score | Vague rubric questions |
| **Pick the better of two candidate outputs** | **Pattern 2: Bi-Directional Pairwise Comparison** | Per-criterion winner + position-swap check | Position bias & verbosity bias |
| **Verify RAG responses or factual claims** | **Pattern 3: Claim-Level Grounding Audit** | Atomic claim classification (`SUPPORTED`/`CONTRADICTED`/`UNSUPPORTED`) | Missing source context |
| **Audit strict format, length, or negative rules** | **Pattern 4: Instruction Compliance Check** | Constraint pass/fail matrix | Overlooking negative constraints |
| **Review generated code or technical specs** | **Pattern 5: Multi-Dimensional Anchored Scoring** | 1–5 anchored scores + `[CRITICAL]`/`[MAJOR]`/`[MINOR]` defects | Halo effect from clean formatting |
| **High-stakes architecture or PR arbitration** | **Pattern 6: Multi-Agent Consensus Panel** | 3-judge synthesis + confidence level (`HIGH`/`MEDIUM`/`LOW`) | Correlated model blind spots |

---

## Pointwise vs. Pairwise Evaluation

### Pointwise Evaluation (Patterns 1, 3, 4, 5)
- **Mechanism**: Grades a single candidate against an absolute rubric or ground-truth context.
- **Best When**: Enforcing deterministic CI/quality gates (e.g., in `agent-orchestrator`), auditing RAG faithfulness, or checking instruction compliance.
- **Calibration Rule**: Always use binary/ternary rubrics or anchored 1–5 definitions so scores remain stable across sessions.

### Pairwise Evaluation (Pattern 2)
- **Mechanism**: Compares Candidate A and Candidate B head-to-head across shared criteria.
- **Best When**: Selecting between two competing implementations, refactoring options, or architectural designs.
- **Calibration Rule**: Always verify position invariance ($(A, B)$ vs $(B, A)$) and penalize verbose padding.

---

## Critique-First Schema Invariant

Because LLMs generate tokens autoregressively from left to right, **never place `"score"` or `"verdict"` keys at the top of a JSON schema**.

- **Anti-Pattern (Score-First)**:
  ```json
  { "score": 8, "verdict": "PASS", "reasoning": "..." }
  ```
  *Failure Mode*: The model commits to `8` on the first token and rationalizes that number in `"reasoning"`.

- **Best Practice (Critique-First)**:
  ```json
  { "evidence_and_critique": "...", "rubric_breakdown": [...], "score": 0.85, "verdict": "PASS" }
  ```
  *Benefit*: The model completes its analytical chain-of-thought before emitting the score and verdict tokens.
