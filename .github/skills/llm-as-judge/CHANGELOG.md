# Changelog — llm-as-judge Skill

## Version 1.4.0 — Critique-First Ordering, Bias Mitigation & Anchored Scales

### Core Enhancements
- **Critique-First Schema Invariant**: Updated all evaluation patterns and JSON templates so evidence extraction and criterion critiques always precede numerical scores and verdicts, preventing autoregressive post-hoc rationalization.
- **Cognitive Bias Mitigation Protocol**: Added explicit countermeasures for Position Bias (bi-directional pairwise checks), Verbosity/Length Bias, Cosmetic Formatting Bias, Scale Compression, and Halo/Horn drift.
- **Standard Anchored 1–5 Scoring Scale**: Defined concrete behavioral anchors (`5=Exemplary` to `1=Broken`) and automatic `[CRITICAL]` blocker gate rules.
- **Subagent & Sequential Multi-Agent Panels**: Standardized the 3-judge consensus lenses (`First-Principles`, `Pragmatic Systems`, `Adversarial Verifier`) across both Subagent Panel Mode and Sequential Turn Mode.
- **Documentation & Reference Cleanup**: Fixed broken reference links (`references/evaluation-frameworks.md`), unified pattern/template numbering (`1`–`8`), aligned trigger phrases with repository catalog, and removed duplicate headings in `references/use-cases.md`.

---

## Version 1.3.0 — Improved Sub-Agent Prompts

### Prompt Enhancements
- **Agent 1 (Claude Sonnet):** Added structured 7-step evaluation process
  - Emphasis on independent reasoning (no hedging or prediction)
  - Depth: criterion-by-criterion breakdown with evidence
  - Outputs: confidence scores, edge cases, questions for other agents
  - Goal: Definitive first evaluation from primary agent

- **Agent 2 (GPT-5.4):** Added independent perspective framework
  - Emphasis on different evaluation approach (not matching Agent 1)
  - Depth: comparative analysis and expected divergences
  - Outputs: areas where they likely differ, comparative notes
  - Goal: Fresh perspective from different model family

- **Agent 3 (Gemini Pro):** Added two-phase verification
  - Phase 1: Independent evaluation (forget other agents exist)
  - Phase 2: Verify internal consistency and defendability
  - Depth: consistency checks, hidden assumptions, expected disagreements
  - Outputs: internal contradictions flagged, defendability score
  - Goal: Quality assurance and validation of reasoning

### Output Format Improvements
- **Rich dimension scoring**: Each criterion now includes score + reasoning
- **Severity levels**: Weaknesses tagged as CRITICAL/MAJOR/MINOR
- **Confidence scores**: Each agent provides 0-1 confidence in their verdict
- **Comparative notes**: Agents predict where they'll diverge, why
- **Edge cases**: Explicitly flagged ambiguities and contradictions

### Aggregation Process (Template -1)
- **8-step synthesis process** replacing simple consensus
- **Per-criterion analysis**: How agents agreed/diverged on each criterion
- **Severity breakdown**: Count of critical/major/minor issues
- **Unique insights tracking**: What did each agent catch uniquely?
- **Confidence reasoning**: Why assess confidence as HIGH/MEDIUM/LOW
- **Next steps**: Conditional recommendations (PASS vs PARTIAL vs FAIL)

### Benefits Over Previous Version
- Better catch of edge cases (agents now explicitly flag them)
- More nuanced confidence assessment (variance-based, not just agreement)
- Clearer reasoning for divergences (agents predict likely differences)
- Richer output for debugging (why each agent scored what)
- Better decision support (conditional verdicts and next steps)

---

## Version 1.2.0 — Sequential Multi-Agent Evaluation

### New Features
- **Multi-Agent Evaluation:**
  - Spin up multiple agents sequentially with different models
  - Each agent evaluates independently (Claude Sonnet, GPT-5.4, Gemini Pro, etc.)
  - Build consensus verdicts from multiple perspectives
  - Identify model-specific blind spots

- **Sequential Invocation Pattern:**
  - Not parallel (Copilot serializes anyway) — run agents one at a time
  - Reproducible workflow: Agent 1 → Agent 2 → Agent 3 → Aggregate
  - Each agent uses identical criteria for fair comparison

- **Result Aggregation:**
  - Consensus score (average of agent scores)
  - Agreement matrix (which criteria do agents agree/disagree on?)
  - Confidence level (HIGH/MEDIUM/LOW based on agreement)
  - Divergence analysis (where and why agents differ)

---

## Version 1.1.0 — Rubric-Based Pattern & Local Repo References

### New Content  
- Added Rubric-Based Evaluation Pattern (primary)
- Documented evaluation patterns from local repositories
- Referenced Gemini evaluation, RULER scoring, RAG evaluation, model comparison

---

## Version 1.0.0 — Agent-Native Evaluation

### Initial Release
- Converted to agent-native skill (no external APIs)
- Conversation-based patterns
- Templates for common evaluation scenarios
- Six implementation patterns
