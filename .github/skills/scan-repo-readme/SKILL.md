---
name: scan-repo-readme
description: This skill should be used when the user asks to "scan the readme", "read the repo readme", "check the project documentation", "search the readme for X", "what does the readme say about Y", "summarize the readme", "find readme", "look up X in the readme", "what skills are available", "list all skills", "scan for existing skills", or wants to find relevant information from repository documentation files or discover available Claude Code skills using keyword and semantic search.
version: 1.0.0
---

# Scan Repo README

Efficiently locate and extract information from repository README files and Claude Code skill files (`SKILL.md`) using a haiku-model agent with minimal context. The agent performs dual-phase search (keyword + semantic), writes results to a timestamped file, and the main agent reads and presents the findings.

## Workflow

### Step 1 — Find README Files

Run this exact Bash command — it auto-detects the `.venv` interpreter before invoking the script:

```bash
[ -d .venv ] || python -m venv .venv
PYTHON=$(if [ -f .venv/Scripts/python ]; then echo .venv/Scripts/python; else echo .venv/bin/python; fi)
$PYTHON .github/skills/scan-repo-readme/scripts/find-readmes.py
```

The script prints to stdout:
- **Line 1**: output file path (e.g., `.scan-readme-results/readme-scan-20240315-143022.md`)
- **Line 2+**: absolute paths of all README files and SKILL.md files found

If Bash is unavailable, use Glob with patterns `**/README.md`, `**/readme.md`, `**/README.rst`, `**/README.txt`, `**/README`, `.github/skills/*/SKILL.md` and build the output path manually from the current timestamp.

### Step 2 — Launch Haiku Subagent

Use the Agent tool with:
- **subagent_type**: `"general-purpose"` (needs Write access to create the output file)
- **model**: `"haiku"` (falls back to inherited session model if unavailable)
- **description**: `"Scan README files"`

Pass only the necessary context — no conversation history. Construct the prompt as follows:

```
You are a repository documentation scanner. Read the listed files and write a structured report to the output file.
For any Python execution, always use `.venv` — create it if missing:
`[ -d .venv ] || python -m venv .venv`
`PYTHON=$(if [ -f .venv/Scripts/python ]; then echo .venv/Scripts/python; else echo .venv/bin/python; fi)`

Files to scan:
{paste file paths from Step 1, one per line}

Output file path: {paste output path from Step 1}

User query: {user's search term, or "full summary" if no query provided}

---

FILES COME IN TWO TYPES — handle each differently:
- README files (README.md, readme.rst, etc.) — project documentation
- SKILL.md files (.github/skills/*/SKILL.md) — available Claude Code skills

---

WHEN A QUERY IS PROVIDED — use dual-phase search:

PHASE 1 — KEYWORD SEARCH:
- Use the Grep tool on all files to find lines containing the query keywords
- Also search for synonym groups from references/search-patterns.md
  (e.g., query "install" → also search "setup", "requirements", "dependencies")
- Collect matching lines with file path, line number, and ±3 lines of surrounding context

PHASE 2 — SEMANTIC SEARCH:
- Split each file into sections by headings (H1/H2/H3)
- For each section, assess semantic relevance to the query (even without exact keyword matches)
- Score: HIGH = directly answers the query, MEDIUM = related context, LOW = tangential

COMBINE RESULTS:
- Priority order: HIGH keyword+semantic → HIGH semantic-only → keyword-only
- Quote directly from source with file path and heading
- Deduplicate overlapping sections

WHEN NO QUERY — provide two sections in the report:

SECTION A — README SUMMARY (one entry per README file):
- Project name and one-line description
- Key features / capabilities
- Installation / setup steps
- Usage examples
- Configuration options
- License

SECTION B — AVAILABLE SKILLS (one entry per SKILL.md file):
- Skill name (from the `name:` frontmatter field)
- One-line description of what it does
- Trigger phrases (from the `description:` frontmatter field — quote ALL of them verbatim, one per line)
- Prerequisites (if any)

WRITE THE REPORT:
Use the Write tool to create the output file directly. Do NOT return the report as a message.
File path: {output path from Step 1}
Format: Markdown
  - H1: "# Repository Scan Report" with query, date, file count
  - H2: "## README Files" and "## Available Skills" (when no query)
  - H2: relevance tier (HIGH / MEDIUM / LOW) when a query is provided
  - H3: file path of each match
  - Body: direct quotes with surrounding context
```

### Step 3 — Read and Present

Read the timestamped output file and present the findings clearly and concisely to the user.

## Additional Resources

- **`references/search-patterns.md`** — README filename patterns, synonym groups, relevance scoring criteria, output format spec
- **`scripts/find-readmes.py`** — Locates all README files recursively across the repository and all SKILL.md files in the repository; prints the output path + file list
