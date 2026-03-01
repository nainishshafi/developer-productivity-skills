---
name: trace-code-context
description: Use when the user asks to "trace code context", "analyze this file",
  "show callers and callees", "generate a code context file", "map dependencies for X",
  "what calls this file", "what does this file call", "document this code file",
  "create a mermaid diagram for this code", "explain what this module does",
  or wants a ground-truth context document for a source file.
version: 1.0.0
---

# Trace Code Context

Generate a rich, ground-truth Markdown context file for any source code file — covering callers, callees, a Mermaid call graph, and a business-readable description. Skips regeneration if the source file hasn't changed since the last run.

**Extraction approach:** A Python script independently validates symbols and imports using AST or structured parsers (ground truth), then a subagent reads the source for business context and uses the script's output as the authoritative symbol list.

## Prerequisites

- Python 3.8+ available (`.venv` will be created automatically if missing)
- The skill requires a `<file-path>` argument — the relative or absolute path to the source file to analyze

## Workflow

### Skill Step 1 — Run trace-context.py

Run this exact Bash command with the user-specified file path:

```bash
[ -d .venv ] || python -m venv .venv
PYTHON=$(if [ -f .venv/Scripts/python ]; then echo .venv/Scripts/python; else echo .venv/bin/python; fi)
$PYTHON .github/skills/trace-code-context/scripts/trace-context.py "<file-path>"
```

To force regeneration even when context is already up to date, add `--force`:

```bash
$PYTHON .github/skills/trace-code-context/scripts/trace-context.py --force "<file-path>"
```

Replace `<file-path>` with the actual path provided by the user (e.g., `src/api/auth.py`).

The script prints a single JSON object to stdout:

```json
{
  "stale": true,
  "repo_root": "/home/user/myproject",
  "output_path": ".code-context/src/api/auth.md",
  "source_path": "src/api/auth.py",
  "language": "python",
  "symbols": ["login", "logout", "AuthError"],
  "imports": ["os", "hashlib", "models.user"],
  "parse_method": "ast",
  "repo_source_files": ["src/api/auth.py", "src/routes/auth_routes.py", "tests/test_auth.py"]
}
```

**Fields:**
- `stale` — `true` if context needs regeneration, `false` if already up to date
- `repo_root` — absolute path to the repository root; use as the base for all Read/Write/Grep operations
- `output_path` — where the context file will be written, relative to `repo_root`
- `source_path` — normalized relative path to the source file, relative to `repo_root`
- `language` — detected language (`python`, `java`, `javascript`, `typescript`, `go`, etc.)
- `symbols` — AST/parser-validated list of defined functions, classes, and methods
- `imports` — AST/parser-validated list of imports and dependencies
- `parse_method` — how symbols were extracted (`ast`, `java-regex`, `js-regex`, `go-regex`, `ctags`, `regex-fallback`)
- `repo_source_files` — complete list of source files across all project folders (for caller grep scope)

**If `stale: false`** → skip to Skill Step 3. Report "Context is up to date" and present the existing file at `{repo_root}/{output_path}`.

### Skill Step 2 — Launch Subagent

Use the Agent tool with:
- **subagent_type**: `"general-purpose"`
- **model**: `"haiku"`
- **description**: `"Trace code context for <source_path>"`

Construct the prompt using the JSON output from Step 1:

````
You are a code context generator. Your task is to produce a detailed context document for a source file.

## Target File
- Repo root: {repo_root}
- Source path: {source_path}  (relative to repo root)
- Output path: {output_path}  (relative to repo root)
- Language: {language}
- Parse method: {parse_method}

## Validated Extraction (treat as authoritative)
Symbols defined in this file:
{symbols as bulleted list}

Imports/dependencies:
{imports as bulleted list}

## Repo Source Files (your grep scope for caller search)
{repo_source_files as bulleted list}

_(If the list exceeds 100 files, use Grep with `path` set to `{repo_root}` and a file-type filter instead of iterating per-file.)_

---

## Your Instructions

1. **Read the source file** using the Read tool at absolute path `{repo_root}/{source_path}`.
   Understand the business logic, purpose, and how the code works.

2. **Cross-reference** your reading with the validated symbols and imports above.
   The script-provided symbol list is authoritative — use it as-is in the output.
   Use your reading to add descriptions and business context.

3. **Find callers** by grepping each file in the repo source files list for references
   to this module's name and exported symbols. Use the Grep tool with each symbol name
   as the pattern, scoped to the repo_source_files list. Collect file path and line number
   for each match, skipping self-references (matches inside {source_path} itself).
   Caller grep patterns by language:
   - Python: `import {module_name}`, `from {module_name} import`
   - Java: `import {package}.{ClassName}`, `new {ClassName}(`, `{ClassName}.`
   - JS/TS: `require('{module}')`, `from '{module}'`, `import {Symbol}`
   - Go: `"{package_path}"`, `{package}.{Symbol}`

4. **Write the output** using the Write tool to `{repo_root}/{output_path}`.
   Create parent directories first using Bash: `mkdir -p "$(dirname "{repo_root}/{output_path}")"`.

## Output Format

Write a Markdown file at `{repo_root}/{output_path}` with this exact structure:

```markdown
# Code Context: `{filename}`
_Generated: {today's date} | Source: `{source_path}` | Language: {language} | Parsed via: {parse_method}_

## Overview
<1-3 sentence business description of what this file does and why it exists>

## Defined Symbols
| Symbol | Type | Description |
|--------|------|-------------|
| `{symbol}` | function/class/method | <what it does> |

## Dependencies (Calls Out)
- `{import}` — stdlib/external/internal: <brief description of what it provides>

## Callers (References Found)
- `{file_path}:{line_number}` — <what the caller does with this module/symbol>
- _(none found)_ if no callers exist

## Call Graph
```mermaid
graph TD
    {source_node}["{filename}"]
    {dep1_node}["{dep1}"]
    {caller1_node}["{caller1}"]

    {source_node} --> {dep1_node}
    {caller1_node} --> {source_node}
```

## Business Context
<2-4 sentence explanation of this module's role in the broader system architecture>

## File Metadata
- Last modified: <file modification timestamp>
- Size: <file size in bytes> bytes
- Parse method: {parse_method}
```

**Mermaid node naming rules:**
- Replace `/`, `.`, `-` with `_` in node IDs
- Use the filename (without path) as the display label in quotes
- Example: `src/api/auth.py` → node ID `src_api_auth_py`, label `"auth.py"`

Write the file and confirm completion.
````

### Skill Step 3 — Present Results

1. Read the file at `{repo_root}/{output_path}` (both values from the Step 1 JSON)
2. Present to the user:
   - The **Overview** section
   - The **Mermaid call graph**
   - A note on the full output file path: "Full context written to `{repo_root}/{output_path}`"

## Additional Resources

- **`references/trace-code-context-reference.md`** — extraction hierarchy, per-language patterns, output path convention, Mermaid naming rules, staleness logic, subagent reconciliation guidance
- **`scripts/trace-context.py`** — runs symbol/import extraction and full-repo source scan; outputs JSON to stdout
