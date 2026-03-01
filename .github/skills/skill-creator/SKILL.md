---
name: skill-creator
description: Use when the user asks to "create a new skill", "add a skill", "write a skill", "scaffold a skill", "make a claude skill", "build a skill", or wants to create a reusable Claude Code skill from scratch. Also use when the user describes a repeatable workflow they want to package as a skill.
version: 1.0.0
---

# Skill Creator

Scaffold and write new Claude Code skills following established conventions. Handles both **reference/knowledge skills** (rich documentation that Claude loads as context) and **task/action skills** (step-by-step workflows with scripts).

## When to Use This Skill

- User wants to package a repeatable workflow as a skill
- User asks to "create", "add", "write", or "scaffold" a skill
- User describes something they want Claude to do consistently across sessions
- User wants to share a skill across projects or with others

## Workflow

### Step 1 — Classify the Skill Type

Ask the user:
1. **What should the skill do?** (one sentence)
2. **Does it perform an action or provide knowledge?**
   - *Action*: runs scripts, executes steps, interacts with tools → **Task skill**
   - *Knowledge*: patterns, templates, conventions, reference material → **Reference skill**

**Decision:**
- **Reference skill** → single rich `SKILL.md` only (no scripts required)
- **Task skill** → `SKILL.md` + `references/` + `scripts/`

### Step 2 — Gather Details

Collect from the user:
- **Skill name** — kebab-case, lowercase (e.g., `lint-python`, `deploy-staging`)
- **Trigger phrases** — what will the user say to invoke it? (list 5–8 examples)
- **Target location** — `.github/skills/` (this project) or `~/.claude/skills/` (all projects)
- **For reference skills**: topic areas, frameworks, code patterns to cover
- **For task skills**: step-by-step actions, prerequisites, scripts needed (bash or python?)

### Step 3 — Scaffold the Folder

Run the scaffold script to create the directory structure and boilerplate:

```bash
PYTHON=$(if [ -f .venv/Scripts/python ]; then echo .venv/Scripts/python; elif [ -f .venv/bin/python ]; then echo .venv/bin/python; else echo python3; fi) && $PYTHON .github/skills/skill-creator/scripts/scaffold-skill.py <skill-name> [base-path]
```

- Default `base-path` is `.github/skills/`
- Script outputs created file paths to stdout (one per line)
- If the skill folder already exists, the script exits with a warning — do not overwrite

### Step 4 — Populate the Files

Use `references/skill-anatomy.md` as your writing guide.

**For a reference skill**, write a rich `SKILL.md` with these sections:
1. **When to Use This Skill** — bullet list of scenarios
2. **Core Concepts** — fundamental ideas with explanations
3. **Implementation Patterns** — named patterns with code examples (3–10+ patterns)
4. **Best Practices** — do's and don'ts
5. **Common Pitfalls** — what to avoid and why
6. **Resources** — links and further reading

**For a task skill**, write:
- `SKILL.md` — frontmatter + step-by-step workflow (reference `references/` and `scripts/` by path)
- `references/<skill-name>-reference.md` — supporting documentation, patterns, and specs
- `scripts/<script>.py` or `scripts/<script>.sh` — executable logic with error handling

Confirm all created files with the user before finishing.

## Additional Resources

- **`references/skill-anatomy.md`** — Complete frontmatter field reference, skill type templates, description writing guide, script conventions, naming rules
- **`scripts/scaffold-skill.py`** — Creates folder structure and boilerplate files for a new skill
