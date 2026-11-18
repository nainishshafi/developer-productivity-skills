---
name: eval-driven-development
description: Methodology for Eval-Driven Development (EDD) to improve LLM-based system quality through iterative evaluation cycles. Use when building or optimizing RAG, agents, or LLM chains.
---

# Eval-Driven Development (EDD)

Eval-Driven Development (EDD) is a feedback-driven methodology where automated evaluations guide the implementation of LLM-based systems. It shifts the focus from "writing code" to "improving measurable outcomes."

## Core Workflow

1. **Define Ground Truth**:
   - Create a golden dataset (e.g., `tests/evals/ground_truth.json`) containing queries and expected outputs/relevant documents.
   - Use `test-data-creator` to help generate synthetic queries if needed.

2. **Instrument Multi-Level Evaluation**:
   - **Response Level**: End-to-end task completion rate.
   - **Stepwise Level**: Evaluating individual tool calls, planning steps, and reasoning chains.
   - **Trajectory Level**: Analyzing the full multi-step path to identify where logic diverged.
   - Use `llm-as-judge` or **Agent-as-a-Judge** (using System 2 models like o1/o3) for complex scoring.
   - For RAG systems, use `rag-pipeline-eval.py` to measure IR metrics:
     - `.\.venv\Scripts\python.exe .github/skills/rag-pipeline/scripts/rag-pipeline-eval.py evaluate --predictions predictions.json --k 5`

3. **Establish Baseline & Deployment Gates**:
   - Execute the system against ground truth and record metrics (HitRate, NDCG, MRR, pass^k).
   - Treat eval scores as **CI/CD deployment gates** (block deploys if scores drop).

4. **Iterative Refinement & Analysis**:
   - Analyze failures via tracing (LangSmith/Langfuse) and error categorization.
   - Modify prompts, chunking strategies, or tool definitions.
   - Re-run evals to verify fixes and ensure zero regressions.

## Advanced EDD Trends (2025-2026)
- **Closing the 37-Point Gap**: Shifting from simple observability (tracing) to active evaluation (grading).
- **System 2 Reasoning Evals**: Specifically evaluating long-chain reasoning and self-reflection in agents.
- **Pass^k Metrics**: Running the same task $k$ times to ensure reliability and eliminate "lucky" successes.
- **Agent-as-a-Judge**: Moving beyond static LLM scoring to autonomous evaluator agents that can browse, execute code, and verify claims.
- **MCP Integration**: Using standardized Model Context Protocol (MCP) to unify tool evaluation across different models.

## When to use
- Optimizing RAG retrieval quality.
- Tuning LLM prompt sensitivity and agent planning.
- Improving agent tool-selection accuracy and error recovery.
- Comparing different embedding models or LLM providers.
- Building production-grade agent "fleets" that require continuous monitoring.

## Key References
- [rag-pipeline-eval.py](file:///c:/Users/naini/developer-productivity-skills/.github/skills/rag-pipeline/scripts/rag-pipeline-eval.py)
- [llm-as-judge](file:///c:/Users/naini/developer-productivity-skills/.github/skills/llm-as-judge/SKILL.md)
- [researcher-poc-tester](file:///c:/Users/naini/developer-productivity-skills/.github/skills/researcher-poc-tester/SKILL.md)
- [MCP Documentation](https://modelcontextprotocol.io/) (Industry Standard)
