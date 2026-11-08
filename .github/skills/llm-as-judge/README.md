# LLM-as-Judge Skill - Agent-Native Evaluation

## Overview

The `llm-as-judge` skill enables Copilot (or any Claude-running agent) to evaluate and compare LLM responses directly within the agent context, with **no external API calls or scripts required**.

## What It Is

An **agent-native skill** that adds evaluation capabilities to Claude/Copilot:
- Compare two or more responses to determine which is better
- Score responses on quality dimensions (accuracy, clarity, relevance, etc.)
- Detect hallucinations (unsupported claims)
- Verify RAG response grounding
- Review code quality
- Evaluate instruction compliance
- Run multiple agents sequentially for consensus verdicts
- **NEW:** Evaluator Archetypes (Pessimist, Contrarian, Pragmatist, Specialist) for multi-perspective technical audits

## How It Works

```
You (in Copilot): "Compare these responses. Which is better? A: [response_a] B: [response_b]"
↓
Claude (agent): Uses internal reasoning without external calls
↓
Claude: "Winner: A because... [reasoning]"
```

**That's it.** No scripts, no API calls, no setup.

## When to Use

Invoke this skill by asking Copilot questions like:

- "Compare these two Python functions"
- "Is this RAG response grounded in the context?"
- "Check this code for quality issues"
- "Score this response 1-5 on clarity, accuracy, completeness"
- "Does this SQL query follow the requirements?"
- "Which model response is better?"

## Files in This Skill

```
.github/skills/llm-as-judge/
├── SKILL.md                          Main skill documentation
├── CHANGELOG.md                      Version history
└── references/
    ├── evaluation-frameworks.md      Evaluation approaches reference
    ├── judge-templates.md            Reusable prompt templates
    └── use-cases.md                  Real-world scenarios
```

## Quick Start Examples

### Example 1: Compare Responses

```
You: "Compare these two solutions to 'fizzbuzz'.

Option A:
for i in range(1, 101):
    print("fizz" if i % 3 == 0 else "buzz" if i % 5 == 0 else i)

Option B:
for i in range(1, 101):
    output = ""
    if i % 3 == 0: output += "fizz"
    if i % 5 == 0: output += "buzz"
    print(output or i)

Which is better on: readability, correctness, performance?"
```

### Example 2: Hallucination Check

```
You: "Check this for hallucinations.

Context: Python released in 1991, created by Guido van Rossum. Version 3.8 released in 2019.

Response: Python was released in 1990 and is maintained by the Python Foundation. 
The latest version is 4.0, released in 2024.

Identify unsupported claims."
```

### Example 3: Quality Scoring

```
You: "Score this job description on:
1. Clarity (is role clear?)
2. Completeness (all needed info?)
3. Tone (professional?)
4. Fairness (inclusive language?)

[Job description text]"
```

## Key Features

✓ **Agent-native** — Runs within Copilot/Claude  
✓ **No external APIs** — No API keys, no internet calls  
✓ **No setup** — Works immediately  
✓ **Transparent reasoning** — You see the agent's evaluation logic  
✓ **Flexible criteria** — Define your own evaluation dimensions  
✓ **Fast** — Instant results, no latency  
✓ **Multi-agent consensus** — Spin up multiple agents sequentially for higher confidence  

## Multi-Agent Evaluation (NEW)

For critical decisions, invoke multiple agents sequentially:

```
You: "Evaluate this with 3 agents (Claude Sonnet, GPT-5.4, Gemini Pro) for consensus"

Agent 1 (Claude Sonnet): Score: 8.5/10 → Verdict: PASS
Agent 2 (GPT-5.4): Score: 8.0/10 → Verdict: PASS  
Agent 3 (Gemini Pro): Score: 7.5/10 → Verdict: PASS

Consensus: 8.0/10, PASS (3/3 agree)
Confidence: HIGH
```

**Why multiple agents?**
- Catches issues single agents miss
- High agreement (3/3) = high confidence
- Model disagreement reveals edge cases
- Audit trail of independent verdicts

## Sub-Agent Prompt Improvements (v1.3)

Each agent uses **enhanced reasoning prompts** for deeper analysis:

- **Agent 1 (Claude Sonnet):** Definitive first evaluation with 7-step process
- **Agent 2 (GPT-5.4):** Independent perspective with comparative notes
- **Agent 3 (Gemini Pro):** Two-phase verification (evaluate, then verify consistency)

**Better outputs:**
- Confidence scores (0-1) for each verdict
- Edge cases explicitly flagged
- Severity levels (CRITICAL/MAJOR/MINOR) on weaknesses
- Hidden assumptions revealed
- Predicted disagreements highlighted

**Better aggregation:**
- Per-criterion analysis (where agents agree/diverge)
- Unique insights from each agent
- Conditional next steps (if PASS, do X; if FAIL, do Y)
- Confidence reasoning (why HIGH/MEDIUM/LOW)

The agent can evaluate:

- **Accuracy** — Is information factually correct?
- **Relevance** — Does it answer the question?
- **Clarity** — Is it understandable?
- **Completeness** — Does it cover all aspects?
- **Hallucination** — Are there unsupported claims?
- **Grounding** — Is RAG response based on retrieved facts?
- **Code quality** — Correctness, readability, efficiency
- **Instruction compliance** — Follows requirements?
- **Tone/Safety** — Professional? Harmful content?

## Reference Materials

### Templates
See `references/judge-templates.md` for ready-to-use prompts:
- General quality scoring
- Hallucination detection
- RAG response evaluation
- Code review
- Model comparison
- Instruction checking
- Safety/toxicity assessment

### Use Cases
See `references/use-cases.md` for real-world scenarios:
1. RAG quality assurance
2. Code generation comparison
3. Job description rating
4. Customer response quality
5. SQL requirement compliance

### Evaluation Approaches
See `references/evaluation-frameworks.md` for technical details on agent-native patterns.

## Architecture

```
No External APIs
        ↓
    Copilot/Claude
        ↓
   Internal Reasoning
        ↓
     Evaluation Result
```

**Comparison with previous approaches:**

Old (script-based):
```
You → Script → Anthropic API → JSON → You
```

New (agent-native):
```
You → Agent → Internal Reasoning → You
```

## FAQ

**Q: Do I need to install anything?**  
A: No. The skill works within Copilot/Claude automatically.

**Q: Can I evaluate batch data?**  
A: Yes, provide multiple items in conversation. The agent handles sequential evaluation naturally.

**Q: Is it accurate?**  
A: Agent-native evaluation is as good as Claude's reasoning. For critical decisions, always verify important evaluations.

**Q: What is multi-agent evaluation?**  
A: Invoke 3 evaluators using distinct lenses (`First-Principles`, `Pragmatic Systems`, `Adversarial Verifier`) via subagent panels or sequential turns to evaluate the same input independently. Results are synthesized for consensus and confidence scoring. See Template 7 in `references/judge-templates.md`.

**Q: When should I use multi-agent?**  
A: For high-stakes decisions (code review, compliance), disagreements worth investigating, or when you need audit trail. For quick evaluations, single-agent is faster.

**Q: How do I run multiple agents?**  
A: Invoke them sequentially in conversation:
  1. Ask Agent 1 to evaluate (capture results)
  2. Ask Agent 2 to evaluate same input (capture results)
  3. Ask Agent 3 to evaluate same input (capture results)
  4. Aggregate and compare results

Not parallel — Copilot doesn't efficiently parallelize anyway.

**Q: Which models can I use?**  
A: Any models accessible to your agents. Recommended starting setup:
  - Agent 1: Claude Sonnet (latest) — Advanced reasoning, multi-step evaluation
  - Agent 2: GPT-5.4 or latest — Different perspective, OpenAI approach
  - Agent 3: Gemini Pro (latest) — Google's approach, catches different issues

**Q: Can I use different models?**  
A: Yes. Any combination works. More diversity between models = more interesting disagreements and insights.

**Q: What if evaluation results are inconsistent?**  
A: Use rubrics (define what 1-5 means), provide examples, or ask the agent to re-evaluate.

**Q: Can I customize evaluation criteria?**  
A: Yes! Define your own dimensions, scales, and rubrics in the conversation.

**Q: Is there an API limit?**  
A: No API calls are made, so there are no rate limits. Agent operates within regular Copilot constraints.

## Tips for Best Results

1. **Be specific** — Define exactly what you're evaluating
2. **Provide context** — The more background, the better
3. **Use clear scales** — Explain what 1-5 means
4. **Ask for reasoning** — Request "why" not just scores
5. **Show examples** — Help agent calibrate with good/bad samples
6. **Be consistent** — Use the same format for similar evals

## Version History

- **v1.5.0** (November 2026) — Evaluator archetypes (Pessimist, Contrarian, Pragmatist, Specialist), multi-persona consensus panels, and repository skill integration
- **v1.4.0** (November 2026) — Critique-first output ordering, cognitive bias mitigation protocol, anchored 1–5 scales, and unified template numbering
- **v1.3.0** (March 2026) — Improved sub-agent prompts with structured reasoning, confidence scoring, and richer aggregation analysis
- **v1.2.0** (March 2026) — Multi-agent sequential evaluation for consensus-based verdicts
- **v1.1.0** (March 2026) — Added rubric-based evaluation (primary), documented local repo sources
- **v1.0.0** (March 2026) — Agent-native evaluation, no external APIs

## See Also

- [Claude Documentation](https://docs.anthropic.com/)
- [Copilot in VS Code](https://github.com/features/copilot)

