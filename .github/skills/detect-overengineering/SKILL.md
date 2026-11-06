---
name: detect-overengineering
description: Use when the user asks to "check for over-engineering", "detect over-engineering", "find over-engineered code", "simplify this code", "audit for over-engineering", "check yagni violations", "reduce accidental complexity", "eliminate premature abstractions", "check code bloat", "is this over-engineered", "refactor for simplicity", or wants to analyze source files or projects for unnecessary layers, trampoline indirection, and design pattern overkill.
version: 1.0.0
---

# Detect Over-Engineering

Analyze source files and architectures to detect over-engineering, premature abstractions, speculative generality (YAGNI violations), layer bloat, trampoline pass-through methods, and pattern overkill. Uses deterministic structural extraction (Python AST for Python, structural regex for TS/JS, Java, C#, Go) coupled with contextual reasoning to calculate an over-engineering risk score and provide concrete, simplified refactoring diffs.

---

## When to Use This Skill

- User asks whether a piece of code or architecture is over-engineered.
- Code review / refactoring tasks focused on code simplification and reduction.
- Identifying YAGNI violations, single-implementation interfaces, and pass-through delegation.
- Auditing new or legacy codebases for accidental complexity before adding features.
- Quantifying boilerplates, builder ceremony, and anemic DTO layers.

---

## Prerequisites

- Python 3.8+ available on PATH or in `.venv`
- Target source file or directory path

---

## Workflow — Single-File Mode

### Step 1 — Run extract-signals.py

Run the deterministic extractor with the target file path:

```bash
[ -d .venv ] || python -m venv .venv
PYTHON=$(if [ -f .venv/Scripts/python ]; then echo .venv/Scripts/python; else echo .venv/bin/python; fi)
$PYTHON .github/skills/detect-overengineering/scripts/extract-signals.py "<file-path>" --pretty
```

*On Windows (PowerShell):*
```powershell
python .github/skills/detect-overengineering/scripts/extract-signals.py "<file-path>" --pretty
```

To force re-analysis even if the report is up to date, pass `--force`:
```bash
python .github/skills/detect-overengineering/scripts/extract-signals.py "<file-path>" --force --pretty
```

The script outputs a JSON object with:
- `source_path` — relative path to source file
- `language` — detected language
- `output_path` — output report location under `.overengineering-analysis/`
- `stale` — boolean whether report needs regeneration
- `overengineering_score` — 0 to 100 risk score
- `severity` — `clean`, `low`, `moderate`, `high`, or `extreme`
- `metrics` — counts of classes, interfaces, pass-through methods, builder methods, custom exceptions, etc.
- `signals` — structural boolean flags
- `smells` — automated smell detections with line numbers and explanations

### Step 2 — Read Source & Analyze Context

1. If `stale: false` and the user did not specify `--force`, read the existing report at `output_path` and present the findings.
2. If `stale: true`, read the source file content and cross-reference the extracted `smells` and `signals` against the **Taxonomy of Over-Engineering** (see `references/detect-overengineering-reference.md`):
   - **Premature Abstraction**: Single-implementer interfaces, empty protocols, generic parameters where concrete types suffice.
   - **Layer Bloat & Trampoline Indirection**: Methods that only forward calls without business rules, validation, or transformation.
   - **Speculative Generality (YAGNI)**: Unused arguments (`*args, **kwargs`, `options: dict`), no-op hook methods (`pass`), dynamic plugin structures for static requirements.
   - **Design Pattern Overkill**: Builder patterns for 2-3 fields, Strategy/Factory for 2 branches, Command pattern for sequential execution.
   - **Premature Optimization**: Custom caches, manual bitmasks, async/thread pools in simple batch paths.
   - **DTO / Model Churn**: Redundant classes mirroring database records with 1:1 identical fields.
   - **Exception Proliferation**: 5+ custom exception classes in small modules where standard exceptions suffice.

### Step 3 — Generate Simplification Plan

Formulate concrete simplification recommendations:
- What can be deleted? (unused interfaces, pass-through methods, empty hooks)
- What can be collapsed? (merge 3 layers into 1, replace class with a function or dataclass/record)
- Estimated LOC and file reduction percentage.

### Step 4 — Write Analysis Report

Write a markdown report to the path indicated by `output_path` (`.overengineering-analysis/<path>.md`):

```markdown
# Over-Engineering Analysis: <source_path>

**Risk Score:** `<score>/100` | **Severity:** `<severity>` | **Language:** `<language>`

## Executive Summary
<2-3 sentences summarizing the degree of over-engineering and highest-impact simplifications>

## Structural Metrics
- **Total LOC:** `<total_loc>`
- **Classes:** `<total_classes>` | **Interfaces / Protocols:** `<total_interfaces>`
- **Pass-Through Trampoline Methods:** `<pass_through_count>`
- **Custom Exceptions:** `<exceptions_count>`

## Detected Over-Engineering Smells

### 1. <Smell Name> (Line <line_number>)
- **Location:** `<symbol / class / method>`
- **Problem:** <Explanation of accidental complexity>
- **YAGNI / KISS Violation:** <Why this is unnecessary>
- **Recommendation:** <Concrete simplification instruction>

## Proposed Simplification (Before vs After)

### Before (Over-Engineered)
```<lang>
<existing complex snippet>
```

### After (Simplified)
```<lang>
<clean, idiomatic replacement>
```

**Net Code Impact:** <e.g., -45 LOC (-65%), eliminated 2 interfaces, removed 3 indirection layers>
```

### Step 5 — Present Findings to the User

Output a concise summary in the conversation:
1. Severity badge & Risk score (`Clean`, `Low`, `Moderate`, `High`, `Extreme`)
2. Top 2-3 over-engineering smells detected
3. Before/After simplification code snippet
4. Link to the detailed report at `[Report](file:///<repo_root>/.overengineering-analysis/<path>.md)`

---

## Workflow — Directory / Repo-Wide Mode

### Step 1 — Run Repo-Wide Extraction

```bash
python .github/skills/detect-overengineering/scripts/extract-signals.py --all --pretty
```

Or for a specific subsystem:
```bash
python .github/skills/detect-overengineering/scripts/extract-signals.py --dir "src/services" --pretty
```

### Step 2 — Triage High-Risk Files

Filter the JSON output for files with `severity: high` or `severity: extreme` (or `overengineering_score >= 65`).

### Step 3 — Write Summary Index

Create `.overengineering-analysis/_summary.md` detailing:
- Total files scanned, clean count, high-risk count
- Top 5 most over-engineered files in the repository
- Repository-wide systemic anti-patterns (e.g., global 1:1 interface paranoia, excessive DTO mapping layers)
- Prioritized refactoring roadmap

---

## Additional Resources

- **`references/detect-overengineering-reference.md`** — Comprehensive taxonomy, decision trees (Do I need an interface? Do I need a pattern?), quantitative thresholds, and before/after code examples across Python, TypeScript, and Java.
- **`scripts/extract-signals.py`** — Deterministic AST and structural signal extraction script.
