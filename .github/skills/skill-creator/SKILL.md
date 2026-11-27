---
name: skill-creator
description: Create, update, install, and synchronize reusable skills. Use for "create a skill", "update a skill", "install skills", "sync skills", or "sync global skills". Preserve existing content during synchronization.
version: 1.3.0
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
- User wants to install existing skills or synchronize repository and global skills

## Synchronizing Existing Skills

1. Resolve the active product's global skills root and inspect both directories before writing. Compare versions, complete relative-file manifests, and substantive diffs; neither location is automatically authoritative. Older versions can still contain unique improvements.
2. Preserve both existing versions in recoverable backups. Merge unique files and nonconflicting improvements, keep user edits, and resolve substantive conflicts from the task context. Do not silently replace a richer skill with a smaller or older copy.
3. Restore every required module and referenced asset before replacing a global copy with a directory junction. Keep global-only skills unless their removal is explicitly requested. A junction is suitable when the repository is the maintained source and its path is stable.
4. Verify the reconciled content retains the improvements from both versions, then check junction targets and relative-path/SHA-256 manifests. Equality after replacement proves synchronization, not preservation. Exclude generated caches from skill-content comparisons.
5. Run the existing metadata validator and targeted checks for changed executable behavior. If a YAML parser is unavailable, use an existing trusted validator or disclose a scoped manual fallback; folded and multiline descriptions are valid YAML. Do not reject them with a single-line-only parser or install dependencies unnecessarily.
6. Report restored versions, backups, and verification coverage. Filesystem visibility does not prove that the IDE refreshed its skill catalog.

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

# Or using the local Python virtual environment (Windows PowerShell):
.\.venv\Scripts\python.exe .github/skills/skill-creator/scripts/scaffold-skill.py <skill-name> [base-path] --modular
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

**For code examples in any skill:**
- Use focused excerpts to teach a pattern. Keep imports for symbols used in the snippet, including framework APIs and application classes; they show dependency provenance. Omit unrelated setup only when it is not the point, and label incomplete snippets as excerpts. Import count alone is never a reason to remove imports.
- For examples meant to be copied and compiled or run, keep all required imports and state the dependencies and version. If setup obscures the pattern, show the excerpt first and link to a complete example. Remove unused imports, not required ones; verify complete examples with the stated toolchain.

## Additional Resources

- **`references/skill-anatomy.md`** — Frontmatter specification, archetype templates, anti-bloat guidelines, and naming rules
- **`scripts/scaffold-skill.py`** — Boilerplate scaffolding utility supporting both standard and `--modular` modes
