# Skill Anatomy Reference

Complete reference for writing Claude Code skills. Use this alongside the `skill-creator` workflow.

---

## 1. Frontmatter Field Reference

Every `SKILL.md` begins with YAML frontmatter between `---` markers.

```yaml
---
name: my-skill
description: When and why to use this skill, with trigger phrases
version: 1.0.0
---
```

### Required Fields

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Skill identifier. Becomes the `/slash-command`. Lowercase kebab-case, max 64 chars. Defaults to folder name if omitted. |
| `description` | string | **Most important field.** Claude uses this to decide when to auto-invoke the skill. Include trigger phrases and scenarios. |
| `version` | string | Semantic version (e.g., `1.0.0`). Increment on updates. |

### Optional Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `allowed-tools` | string | none | Comma-separated tools Claude may use without permission prompts (e.g., `Read, Grep, Bash`) |
| `model` | string | inherited | Model to use when skill is active (`haiku`, `sonnet`, `opus`) |
| `context` | string | none | Set to `fork` to run skill in isolated subagent context |
| `agent` | string | `general-purpose` | Subagent type when `context: fork` — options: `Explore`, `Plan`, `general-purpose` |
| `user-invocable` | boolean | `true` | Set to `false` to hide from `/` menu (Claude still knows about it) |
| `disable-model-invocation` | boolean | `false` | Set to `true` to prevent auto-invocation (use for safety-sensitive actions like deploy, commit) |
| `argument-hint` | string | none | Autocomplete hint shown to users (e.g., `[issue-number]`, `[component-name]`) |

---

## 2. Skill Type Templates

### Template A — Reference / Knowledge Skill

Use when the skill provides patterns, conventions, or domain knowledge (no actions or scripts needed).

```yaml
---
name: my-reference-skill
description: Provides [domain] patterns and conventions. Use when [scenario], [scenario], or the user asks about [topic].
version: 1.0.0
---

# My Reference Skill

One-line summary of what this skill provides.

## When to Use This Skill

- Scenario 1
- Scenario 2
- Scenario 3 (be specific — list real situations)

## Core Concepts

### Concept 1

Explanation of the concept with why it matters.

\```code example\```

### Concept 2

...

## Implementation Patterns

### Pattern Name

When to use this pattern and why.

\```code
complete working example
\```

## Best Practices

- Do X because Y
- Avoid Z because it causes W

## Common Pitfalls

### Pitfall Name
**Problem:** What goes wrong.
**Solution:** How to fix it.

## Resources

- [Name](url)
```

**Folder layout:**
```
my-reference-skill/
└── SKILL.md   ← all content here, aim for 300–1000 lines
```

---

### Template B — Task / Action Skill

Use when the skill performs specific actions: runs scripts, executes steps, interacts with APIs.

```yaml
---
name: my-task-skill
description: Use when the user asks to "[action phrase]", "[action phrase]", or wants to [outcome].
version: 1.0.0
---

# My Task Skill

One-line summary of what this skill does.

## Prerequisites

- Tool 1 installed and authenticated
- Tool 2 available on PATH
- [Other requirement]

## Workflow

### Step 1 — [Action]

[Instructions for Claude]

\```bash
# Command to run
\```

### Step 2 — [Action]

[Instructions]

### Step 3 — [Action]

[Instructions]

## Additional Resources

- **`references/my-task-skill-reference.md`** — [what it contains]
- **`scripts/my-script.py`** — [what it does]
```

**Folder layout:**
```
my-task-skill/
├── SKILL.md
├── references/
│   └── my-task-skill-reference.md
└── scripts/
    ├── my-script.py
    └── helper.sh
```

---

## 3. Description Writing Guide

The `description` field is **the single most important field** — Claude uses it to decide when to auto-invoke your skill.

### What Makes a Good Description

**List exact trigger phrases** (what users actually type):
```yaml
description: Use when the user asks to "scan the readme", "read the repo readme",
  "check the project documentation", "search the readme for X", or wants to find
  information from repository README files.
```

**List scenario bullets** (what situations apply):
```yaml
description: Master advanced Git workflows. Use when cleaning up commit history
  before merging, applying specific commits across branches, finding commits that
  introduced bugs, or working on multiple features simultaneously.
```

### Good vs Bad Examples

| Bad | Good |
|-----|------|
| `"Does stuff with files"` | `"Finds and extracts information from README files using keyword and semantic search"` |
| `"Utility skill"` | `"Use when the user asks to 'sync forks', 'pull all my forks', or wants to clone/update all GitHub forks"` |
| `"Git helper"` | `"Master advanced Git workflows including rebasing, cherry-picking, bisect, and reflog"` |

### Tips

- Include 5–8 trigger phrases in quotes for task skills
- Include 5–8 bullet scenarios for reference skills
- Use natural language users would actually say
- Mention domain keywords (e.g., "GitHub", "README", "TypeScript")
- Be specific, not generic — "Deploy to staging via SSH" not just "Deploy"

---

## 4. Reference Skill Content Structure

The standard 6-section format used in well-written reference skills:

```
# Skill Title

One-line summary.

## When to Use This Skill     ← bullet list of real scenarios
## Core Concepts              ← foundational ideas with explanations
## Implementation Patterns   ← named patterns with code examples (3–10+)
## Best Practices            ← do's and don'ts
## Common Pitfalls           ← what breaks and how to fix it
## Resources                 ← links and further reading
```

Keep `SKILL.md` between **300–1000 lines**. For very detailed content, split into supporting files in `references/`.

---

## 5. Script Conventions

### Bash Scripts

```bash
#!/usr/bin/env bash
set -euo pipefail   # exit on error, undefined vars, pipe failures

# Dependency check upfront
for cmd in gh jq git; do
  if ! command -v "$cmd" &>/dev/null; then
    echo "Error: '$cmd' is required but not found on PATH" >&2
    exit 1
  fi
done

# Print errors to stderr
echo "Something failed" >&2

# Print results to stdout
echo "$result"
```

### Python Scripts

```python
#!/usr/bin/env python3
import sys

def main():
    if len(sys.argv) < 2:
        print("Usage: script.py <arg>", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
```

### Cross-Platform Python Resolver

Use this pattern to auto-detect the right Python interpreter on both Windows and Unix:

```bash
PYTHON=$(if [ -f .venv/Scripts/python ]; then echo .venv/Scripts/python; \
  elif [ -f .venv/bin/python ]; then echo .venv/bin/python; \
  else echo python3; fi) && $PYTHON path/to/script.py
```

### Output Format Convention

Following the `scan-repo-readme` pattern:
- **Line 1**: key result (output path, primary value)
- **Lines 2+**: supporting data (file paths, records, etc.)

This allows Claude to read stdout line-by-line cleanly.

---

## 6. Naming & Versioning Conventions

### Skill Name Rules

- Lowercase kebab-case: `my-skill-name`
- Only letters, numbers, hyphens
- No uppercase, spaces, underscores, or special chars
- Max 64 characters
- Descriptive: `sync-github-forks` not `syncer`

### Versioning

Use semantic versioning: `MAJOR.MINOR.PATCH`

| Change type | Example | Version bump |
|-------------|---------|-------------|
| Bug fix | Fix broken script | `1.0.0` → `1.0.1` |
| New feature | Add new step | `1.0.0` → `1.1.0` |
| Breaking change | Rename args | `1.0.0` → `2.0.0` |
| First release | Initial publish | `1.0.0` |

### Folder Layout

```
.github/skills/          ← project-level skills
~/.claude/skills/        ← personal skills (all projects)

<skill-name>/
├── SKILL.md             ← required
├── references/          ← optional: supporting docs
│   └── *.md
└── scripts/             ← optional: executable utilities
    ├── *.py
    └── *.sh
```
