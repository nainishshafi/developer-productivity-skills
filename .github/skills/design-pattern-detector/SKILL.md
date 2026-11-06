---
name: design-pattern-detector
description: Use when the user asks to "detect design patterns", "find patterns in
  this file", "analyze code for patterns", "check for anti-patterns", "pattern analysis",
  "is this a singleton", "detect god object", "find factory pattern", "detect facade",
  "check for god file", "check for strategy pattern", "scan for design patterns", "what patterns does this code use",
  "find anti-patterns", "pattern audit", or wants to identify design patterns and
  anti-patterns in a source file or across the entire repository.
version: 1.1.0
---

# Design Pattern Detector

Analyze source files to detect common design patterns (Singleton, Factory, Observer, Strategy, Builder, Decorator, Repository, Command, Template Method, Facade) and anti-patterns (God Object / God File, Long Method, Feature Envy). Uses structural extraction for deterministic signal detection and a subagent for contextual reasoning. Language-agnostic with best accuracy for Python (AST), Java, JS/TS, Go, and C# (regex).

**Extraction approach:** A Python script deterministically extracts class structure, method signatures, fields, metrics, and boolean structural signals (ground truth), then a subagent reads the source for business context and uses the signals to classify patterns with confidence scores.

## Prerequisites

- Python 3.8+ available (`.venv` will be created automatically if missing)
- **Single-file mode:** requires a `<file-path>` argument — the path to the source file to analyze
- **Repo-wide mode:** use `--all` flag to scan all source files in the repository

## Workflow — Single-File Mode

### Skill Step 1 — Run extract-patterns.py

Run this exact Bash command with the user-specified file path:

```bash
[ -d .venv ] || python -m venv .venv
PYTHON=$(if [ -f .venv/Scripts/python ]; then echo .venv/Scripts/python; else echo .venv/bin/python; fi)
$PYTHON .github/skills/design-pattern-detector/scripts/extract-patterns.py "<file-path>"
```

To force regeneration even when analysis is already up to date, add `--force`:

```bash
$PYTHON .github/skills/design-pattern-detector/scripts/extract-patterns.py --force "<file-path>"
```

Replace `<file-path>` with the actual path provided by the user.

The script prints a single JSON object to stdout:

```json
{
  "source_path": "src/api/auth_service.py",
  "language": "python",
  "parse_method": "ast",
  "repo_root": "/home/user/myproject",
  "output_path": ".pattern-analysis/src/api/auth_service.md",
  "stale": true,
  "classes": [
    {
      "name": "AuthService",
      "bases": ["BaseService"],
      "methods": [
        {"name": "__init__", "params": ["self", "strategy: AuthStrategy"], "modifiers": ["private"], "line": 10, "loc": 5}
      ],
      "fields": [
        {"name": "_strategy", "type": "AuthStrategy", "modifiers": ["private"]}
      ]
    }
  ],
  "functions": [
    {"name": "create_auth_service", "params": ["config"], "modifiers": [], "line": 50, "loc": 8}
  ],
  "metrics": {
    "total_classes": 1,
    "total_methods": 5,
    "total_functions": 1,
    "total_loc": 200,
    "max_method_loc": 45,
    "avg_method_loc": 13.0
  },
  "structural_signals": {
    "has_private_constructor": false,
    "has_static_instance_field": false,
    "has_get_instance_method": false,
    "has_create_methods": true,
    "has_subscribe_notify": false,
    "has_fluent_api": false,
    "has_build_method": false,
    "has_crud_methods": false,
    "has_delegation_pattern": true,
    "has_same_type_wrapping": false
  }
}
```

**Fields:**
- `source_path` — relative path to the source file
- `language` — detected language (`python`, `java`, `javascript`, `typescript`, `go`, `csharp`, etc.)
- `parse_method` — how structure was extracted (`ast`, `java-regex`, `js-regex`, `go-regex`, `csharp-regex`, `regex-fallback`)
- `repo_root` — absolute path to the repository root
- `output_path` — where the analysis report will be written, relative to `repo_root`
- `stale` — `true` if analysis needs regeneration, `false` if already up to date
- `classes` — extracted class definitions with bases, methods (name, params, modifiers, line, loc), and fields (name, type, modifiers)
- `functions` — top-level functions with same shape
- `metrics` — code metrics (class/method/function counts, LOC stats)
- `structural_signals` — 10 boolean flags indicating potential pattern markers

**If `stale: false`** → skip to Skill Step 3. Report "Analysis is up to date" and present the existing file at `{repo_root}/{output_path}`.

### Skill Step 2 — Launch Subagent

Use the Agent tool with:
- **subagent_type**: `"general-purpose"`
- **model**: `"haiku"`
- **description**: `"Detect design patterns in <source_path>"`

Construct the prompt using the JSON output from Step 1:

````
You are a design pattern analyzer. Your task is to identify design patterns and anti-patterns in a source file, using deterministic structural signals as the primary evidence and your own reading for contextual reasoning.

## Target File
- Repo root: {repo_root}
- Source path: {source_path}  (relative to repo root)
- Output path: {output_path}  (relative to repo root)
- Language: {language}
- Parse method: {parse_method}

## Structural Extraction (treat as authoritative)

### Classes
{classes formatted as structured list — for each class: name, bases, methods with params/modifiers, fields with types}

### Top-Level Functions
{functions formatted as structured list}

### Metrics
{metrics formatted as key-value pairs}

### Structural Signals
{structural_signals formatted as bulleted boolean list, e.g.: "- has_private_constructor: false"}

---

## Your Instructions

1. **Read the source file** using the Read tool at absolute path `{repo_root}/{source_path}`.
   Understand the business logic, purpose, and how each class/function works.

2. **Cross-reference** your reading with the structural signals above.
   The script-provided signals are authoritative — use them as primary evidence.
   Use your reading to validate, add context, and identify patterns the signals may miss.

3. **Detect design patterns** by matching signals to the pattern definitions below.
   Assign a confidence level (HIGH / MEDIUM / LOW) based on how many heuristics match.
   Only report patterns you have structural evidence for — do not hallucinate patterns.

4. **Check for anti-patterns** using the metrics and your source reading.

5. **Write the output** using the Write tool to `{repo_root}/{output_path}`.
   Create parent directories first using Bash: `mkdir -p "$(dirname "{repo_root}/{output_path}")"`.

## Pattern Definitions

### Singleton
- Signals: `has_private_constructor` + `has_static_instance_field` + `has_get_instance_method`
- HIGH: all 3 signals present
- MEDIUM: 2 of 3 signals
- LOW: 1 signal + class-level instance storage visible in source

### Factory
- Signals: `has_create_methods`
- HIGH: create/build methods returning abstract/interface types, multiple creation methods
- MEDIUM: create methods returning concrete types
- LOW: static creation methods without clear type hierarchy

### Observer
- Signals: `has_subscribe_notify`
- HIGH: subscribe + notify + listener collection all present
- MEDIUM: event emission pattern (emit/on) without explicit subscription
- LOW: callback parameter pattern

### Strategy
- Signals: `has_delegation_pattern`
- HIGH: constructor stores interface + methods delegate to it
- MEDIUM: constructor accepts callable/function param for behavior
- LOW: method accepts strategy-like parameter

### Builder
- Signals: `has_fluent_api` + `has_build_method`
- HIGH: fluent setters + build() method + many optional params
- MEDIUM: fluent API without build() or build() without fluent setters
- LOW: method chaining for a different purpose

### Decorator
- Signals: `has_same_type_wrapping` + `has_delegation_pattern`
- HIGH: wraps same type + delegates all methods + adds behavior
- MEDIUM: wraps same type + partial delegation
- LOW: composition with same interface but unclear delegation

### Repository
- Signals: `has_crud_methods`
- HIGH: all 4 CRUD groups present (read + create + update + delete)
- MEDIUM: 3 of 4 CRUD groups present
- LOW: 2 of 4 CRUD groups or "Repository" in class name

### Command
- Signals: `has_execute_undo`
- HIGH: `execute()` + `undo()` (or `redo()`/`rollback()`) pair, command objects encapsulate an action
- MEDIUM: `execute()` present + command-like naming but no undo
- LOW: `execute()` alone on a class named `*Command` or `*Action`

### Template Method
- Signals: `has_abstract_template_steps`
- HIGH: abstract base class + `@abstractmethod` hook methods + at least one concrete method calling those hooks
- MEDIUM: class inherits from ABC/abstract base + mix of abstract and concrete methods
- LOW: class named `Abstract*` or `Base*` + defines some concrete template logic

## Anti-Pattern Definitions

### God Object
- Metrics: total_methods > 15 OR total fields > 10
- HIGH: > 20 methods AND > 10 fields
- MEDIUM: > 15 methods OR > 10 fields
- Also flag if you observe multiple unrelated responsibilities

### Long Method
- Metrics: max_method_loc > 50
- HIGH: method > 80 LOC
- MEDIUM: method > 50 LOC
- Identify which specific method(s) exceed the threshold

### Feature Envy
- Cannot be detected from signals — requires reading the source
- MEDIUM: method clearly operates primarily on external object data
- LOW: method has some external access patterns

## Output Format

Write a Markdown file at `{repo_root}/{output_path}` with this exact structure:

```markdown
# Pattern Analysis: `{filename}`
_Generated: {today's date} | Source: `{source_path}` | Language: {language} | Parsed via: {parse_method}_

## Summary
| Pattern | Confidence | Location |
|---------|-----------|----------|
| {pattern_name} | {HIGH/MEDIUM/LOW} | {class or function name} |

_(If no patterns detected, write: "No design patterns detected.")_

## Detected Patterns

### {Pattern Name} ({confidence} confidence)
- **Where:** `{class/function name}`, line {N}
- **Evidence:** {which structural signals matched + what you observed in source}
- **Intent:** {1-sentence explanation of what this pattern achieves here}

_(Repeat for each detected pattern. Omit this section if no patterns found.)_

## Anti-Pattern Warnings

### {Anti-Pattern Name} ({confidence} confidence)
- **Where:** `{class/function name}`
- **Evidence:** {metrics that triggered it + what you observed}
- **Suggestion:** {concrete refactoring suggestion}

_(If no anti-patterns found, write: "No anti-patterns detected.")_

## Metrics
- Classes: {total_classes} | Methods: {total_methods} | Functions: {total_functions}
- Total LOC: {total_loc}
- Max method length: {max_method_loc} lines | Avg: {avg_method_loc} lines

## File Metadata
- Last modified: {file modification timestamp from source file stat}
- Parse method: {parse_method}
```

**Important:** Only report patterns and anti-patterns you have evidence for. Do not invent patterns that aren't supported by the structural signals or source reading. Prefer false negatives over false positives.

Write the file and confirm completion.
````

### Skill Step 3 — Present Results

1. Read the file at `{repo_root}/{output_path}` (both values from the Step 1 JSON)
2. Present to the user:
   - The **Summary** table
   - Any **Detected Patterns** with their evidence
   - Any **Anti-Pattern Warnings** with suggestions
   - A note: "Full analysis written to `{output_path}`"

---

## Workflow — Repo-Wide Mode

Use this workflow when the user asks to scan the entire repo, all files, or uses `--all`.

### Skill Step 1 — Run extract-patterns.py --all

```bash
[ -d .venv ] || python -m venv .venv
PYTHON=$(if [ -f .venv/Scripts/python ]; then echo .venv/Scripts/python; else echo .venv/bin/python; fi)
$PYTHON .github/skills/design-pattern-detector/scripts/extract-patterns.py --all
```

Add `--force` to force regeneration of all files.

The script prints a JSON object with a `files` array:

```json
{
  "repo_root": "/home/user/myproject",
  "index_output_path": ".pattern-analysis/_index.md",
  "total_files": 25,
  "stale_files": 3,
  "files": [
    { "source_path": "src/auth.py", "stale": true, "classes": [...], ... },
    { "source_path": "src/db.py", "stale": false, "classes": [...], ... }
  ]
}
```

### Skill Step 2 — Filter Stale Files

From the JSON `files` array, collect only entries where `stale: true`.

- If `stale_files` is 0 → skip to Skill Step 4 (present cached index)
- If `stale_files` is > 0 → proceed to Skill Step 3

### Skill Step 3 — Launch Subagent (Batch)

Use the Agent tool with:
- **subagent_type**: `"general-purpose"`
- **model**: `"haiku"`
- **description**: `"Detect design patterns across repo"`

Construct the prompt with ALL stale file extractions from the JSON. The subagent should:

1. For each stale file: read the source, apply pattern detection (same rules as single-file mode), write a per-file report to the file's `output_path`
2. After all per-file reports: write a consolidated `_index.md` at `{repo_root}/.pattern-analysis/_index.md` with this format:

```markdown
# Pattern Analysis Index
_Generated: {today's date} | Files analyzed: {total_files}_

## Summary

| File | Patterns Found | Anti-Patterns | Confidence |
|------|---------------|---------------|-----------|
| `{source_path}` | {pattern names} | {anti-pattern names} | {highest confidence} |

## Pattern Distribution
| Pattern | Count | Files |
|---------|-------|-------|
| Singleton | 2 | `auth.py`, `config.py` |

## Anti-Pattern Hotspots
| Anti-Pattern | Count | Files |
|-------------|-------|-------|
| God Object | 1 | `app_controller.py` |

## Individual Reports
- [`{source_path}`]({output_path}) — {patterns found or "no patterns"}
```

### Skill Step 4 — Present Results

1. Read `{repo_root}/.pattern-analysis/_index.md`
2. Present to the user:
   - The **Summary** table
   - **Pattern Distribution** counts
   - **Anti-Pattern Hotspots** if any
   - A note: "Full index at `.pattern-analysis/_index.md`. Individual reports at `.pattern-analysis/<source-path>.md`"

## Additional Resources

- **`references/design-pattern-detector-reference.md`** — pattern catalog, detection heuristics, confidence scoring, per-language notes, anti-pattern thresholds, structural signal definitions
- **`scripts/extract-patterns.py`** — structural extraction script; outputs JSON with classes, methods, fields, metrics, and structural signals
