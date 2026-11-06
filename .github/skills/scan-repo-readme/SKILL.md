---
name: scan-repo-readme
description: This skill should be used when the user asks to "scan the readme", "read the repo readme", "check the project documentation", "search the readme for X", "what does the readme say about Y", "summarize the readme", "find readme", "look up X in the readme", or wants to find relevant information from repository documentation files using keyword and semantic search.
version: 1.1.0
---

# Scan Repo README

Efficiently locate and extract information from repository README files using dual-phase search (keyword + semantic), writing results to a timestamped report file and presenting concise findings to the user.

> **⚠️ IMPORTANT — always use `--root-only` by default.**  
> Running `find-readmes.py` without `--root-only` performs a full recursive walk and returns every nested README (including `.venv`, vendor packages, and large example trees), producing noisy, slow, and unreliable results.  
> Only omit `--root-only` when you deliberately need a full repository audit.

## Quick Start

**Windows (PowerShell):**
```powershell
if (-not (Test-Path .venv)) { python -m venv .venv }
$PYTHON = if (Test-Path .venv\Scripts\python.exe) { ".venv\Scripts\python" } else { "python3" }
& $PYTHON .github/skills/scan-repo-readme/scripts/find-readmes.py --root-only
```

**Unix/macOS (Bash):**
```bash
[ -d .venv ] || python -m venv .venv
PYTHON=$(if [ -f .venv/Scripts/python ]; then echo .venv/Scripts/python; else echo .venv/bin/python; fi)
$PYTHON .github/skills/scan-repo-readme/scripts/find-readmes.py --root-only
```

Then take the output path (line 1) + file list (lines 2+) and pass them to the subagent (see Step 2).

## Workflow

### Step 1 — Find README Files

**Windows (PowerShell):**

```powershell
if (-not (Test-Path .venv)) { python -m venv .venv }
$PYTHON = if (Test-Path .venv\Scripts\python.exe) { ".venv\Scripts\python" } else { "python3" }

# RECOMMENDED — root-only scan (top-level + immediate child directories only)
& $PYTHON .github/skills/scan-repo-readme/scripts/find-readmes.py --root-only

# Full recursive scan — use only for broad audits; expect many noisy results
# & $PYTHON .github/skills/scan-repo-readme/scripts/find-readmes.py

# Include .github/skills SKILL.md files in the listing
# & $PYTHON .github/skills/scan-repo-readme/scripts/find-readmes.py --root-only --include-skills
```

**Unix/macOS (Bash):**

```bash
[ -d .venv ] || python -m venv .venv
PYTHON=$(if [ -f .venv/Scripts/python ]; then echo .venv/Scripts/python; else echo .venv/bin/python; fi)

# RECOMMENDED — root-only
$PYTHON .github/skills/scan-repo-readme/scripts/find-readmes.py --root-only

# Full recursive scan (noisy — use only for repo-wide audits)
# $PYTHON .github/skills/scan-repo-readme/scripts/find-readmes.py

# Include SKILL.md files
# $PYTHON .github/skills/scan-repo-readme/scripts/find-readmes.py --root-only --include-skills
```

The script prints to stdout:
- **Line 1**: output file path (e.g., `.scan-readme-results/readme-scan-20240315-143022.md`)
- **Line 2+**: absolute paths of all README files found

If Bash is unavailable, use Glob with patterns `**/README.md`, `**/readme.md`, `**/README.rst`, `**/README.txt`, `**/README` and build the output path manually from the current timestamp.

### Step 2 — Perform Dual-Phase Search (Direct or Subagent)

If `--root-only` returned a small set of README files (1–3 files), perform the dual-phase scan directly in-context or delegate to a subagent (`invoke_subagent` in Antigravity or `Agent` in Claude Code). For large multi-README audits, delegate to a subagent to keep the main context window clean.

Agent parameters (when using a subagent):
- `subagent_type`: `"general-purpose"` (or `"research"` / `"self"`)
- `model`: `"haiku"` / `"flash"` / `"inherit"`
- `description`: `"Scan README files"`

Provide the subagent with a compact prompt containing only the file list, the output path, and the user query (no conversation history). Example prompt payload:

Files to scan:
{paste file paths from Step 1, one per line}

Output file path: {paste output path from Step 1}

User query: {user's search term, or "full summary" if no query provided}

The subagent must perform the dual-phase search described below and write the final Markdown report to the provided output file. Do not return the report text in the agent response.

Dual-phase scan (subagent behavior):

- Phase 1 — Keyword search:
  - Expand the user's query using synonym groups from `references/search-patterns.md`.
  - Grep all listed files for these keywords, recording file path, line number, and ±3 lines of context.

- Phase 2 — Semantic search:
  - Split files into sections by Markdown headings (H2/H3 preferred).
  - Score each section as HIGH / MEDIUM / LOW for relevance to the query.

- Combine results (priority order): HIGH keyword+semantic → HIGH semantic-only → keyword-only. Quote directly from sources, include file path and heading, and deduplicate overlapping excerpts.

Report format (Markdown, written to the output path):

- H1: `# Repository Scan Report` (include query, date, file count)
- H2: file path of each README scanned
- H3: relevance tier (HIGH / MEDIUM / LOW) when a query is provided
- Body: direct quotes with surrounding context

Note: the subagent must create the output file at the provided path. If you run this skill in an environment that cannot launch `haiku`, configure the agent to use the session-inherited model and allow write access.

### Root-only mode (default recommendation)

Use `--root-only` when the user's intent is limited to top-level project documentation. This avoids excessive noise from nested examples, vendored packages, and virtualenvs. The full recursive scan is available for broad repo-wide audits but will include many irrelevant README files in large monorepos — validate and trim the file list before launching downstream scans.

### Step 3 — Read and Present

Read the timestamped output file and present the findings clearly and concisely to the user.

## Additional Resources

- **`references/search-patterns.md`** — README filename patterns, synonym groups, relevance scoring criteria, output format spec
- **`scripts/find-readmes.py`** — Locate README files and print the output path + file list. Supports `--root-only` and opt-in `--include-skills`.
