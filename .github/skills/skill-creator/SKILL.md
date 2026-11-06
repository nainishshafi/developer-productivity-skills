---
name: skill-creator
description: Use when the user asks to "create a new skill", "add a skill", "write a skill", "scaffold a skill", "make a claude skill", "build a skill", or wants to create a reusable Claude Code skill from scratch. Handles modular knowledge-pack developer skills, task/action skills with scripts, and lightweight reference skills.
version: 1.1.0
---

# Skill Creator

Scaffold and write new Claude Code skills following established repository conventions. Supports three archetypes:
1. **Modular Knowledge-Pack Skills** — High-depth developer skills (e.g. `java-developer`, `typescript-developer`, `python-developer`) featuring a lean router `SKILL.md` (< 45 lines) and topical markdown modules loaded selectively to keep context windows lean.
2. **Task / Action Skills** — Step-by-step operational workflows with automated scripts (`SKILL.md` + `scripts/` + `references/`).
3. **Lightweight Reference Skills** — Focused single-topic reference guides.

## When to Use This Skill

- User wants to package a repeatable workflow or domain guide as a skill
- User asks to "create", "add", "write", or "scaffold" a skill
- User wants to build a language or framework developer skill
- User describes something they want Claude to do consistently across sessions

## Workflow

### Step 1 — Classify the Skill Archetype

Determine the archetype:
1. **Modular Knowledge-Pack Skill (Recommended for Languages & Frameworks)**:
   - For language specialists, runtime engines, or multi-topic engineering domains (e.g., `go-developer`, `rust-developer`, `vue-developer`).
   - Structure: Lean `SKILL.md` router + topic folders (`core/`, `runtime-and-memory/`, `concurrency/`, `security/`, `testing/`).
   - Rule: Never bloat `SKILL.md` or dump everything into a monolithic reference file.
2. **Task / Action Skill**:
   - Executes shell/python scripts, runs automated linters/scaffolding, or mutates repository code.
   - Structure: `SKILL.md` workflow + `scripts/` + `references/`.
3. **Lightweight Reference Skill**:
   - Small, single-topic cheatsheet or conventions doc without multiple sub-domains.

### Step 2 — Gather Details

Collect from the user:
- **Skill name** — kebab-case, lowercase (e.g., `rust-developer`, `sync-github-forks`)
- **Trigger phrases** — what will the user say to invoke it? (list 5–8 examples)
- **Target location** — `.github/skills/` (this repository) or `~/.claude/skills/` (global)
- **For modular skills**: domain folders to generate (architecture, memory/runtime, concurrency, security, testing)
- **For task skills**: step-by-step actions, prerequisites, automation scripts needed

### Step 3 — Scaffold the Folder

Run the scaffold script using Node.js (available in this environment) or Python:

```bash
# Using Node.js (Recommended in this environment):
node .github/skills/skill-creator/scripts/scaffold-skill.js <skill-name> [base-path] --modular

# Or using Python (if Python runtime is installed):
python .github/skills/skill-creator/scripts/scaffold-skill.py <skill-name> [base-path] --modular
```

- Default `base-path` is `.github/skills/`
- Script outputs created file paths to stdout
- If the skill directory already exists, the script halts safely without overwriting

### Step 4 — Populate the Files

Use `references/skill-anatomy.md` as your architectural guide.

**For a Modular Knowledge-Pack Skill:**
1. Keep `SKILL.md` as a clean router (< 45 lines) containing:
   - Metadata frontmatter
   - 4–6 Core Directives
   - `## Knowledge Modules` with markdown links to each sub-module: *"Load only the modules relevant to the task."*
2. Write deep, single-responsibility topic documents under their respective subdirectories:
   - `core/architecture.md` (Domain modeling, architecture styles, error design)
   - `runtime-and-memory/memory-and-closures.md` (Closure traps, leak prevention, caches, GC/lifecycles)
   - `concurrency/concurrency.md` (Non-blocking event loop, threading, throttling, backpressure)
   - `security/security.md` (Defensive typing, sanitization, injection prevention)
   - `testing/best-practices.md` (Testing pyramid, mock isolation, testcontainers)

**For a Task Skill:**
- `SKILL.md` — workflow steps referencing scripts
- `scripts/<script>.py` or `.sh` — executable logic with error handling

## Additional Resources

- **`references/skill-anatomy.md`** — Frontmatter specification, archetype templates, anti-bloat guidelines, and naming rules
- **`scripts/scaffold-skill.py`** — Boilerplate scaffolding utility supporting both standard and `--modular` modes
