# Skill Evolution Rubric

Decision framework used by **`skill-doctor`** to turn raw `project-memory` entries (`journal` and `ledger`) into high-signal, non-bloated skill improvements.

---

## 1. Triage Classification Matrix

| Signal in Memory (`learnings` + `summary` + `tags`) | Classification | Target Action |
|---|---|---|
| Documents a repeatable pitfall, shell/OS trap, library quirk, security hazard, or architectural rule missing from an existing skill | `UPDATE_EXISTING_SKILL` | Edit the matching skill's submodule or `references/` (or `SKILL.md` for non-modular skills), bump `version`, mark `promoted`. |
| Same pitfall/rule is already explicitly covered in the matched skill's files | `SKIP_TRANSIENT` (`ALREADY_COVERED`) | Leave skill untouched to prevent duplication bloat; mark `skipped` with `targetSkill` set to the covering skill. |
| Narrow one-off implementation detail (e.g., specific ticket ID, temporary file name, transient feature WIP) | `SKIP_TRANSIENT` | Do not pollute general-purpose skills; mark `skipped` with `targetSkill: "none"`. |
| An established reusable workflow lacks a suitable owning skill | `CREATE_NEW_SKILL` | Scaffold a focused skill via `skill-creator`, register and validate it, then mark `promoted` with `targetSkill: "new:<skill-name>"`; do not wait for another learning. |

---

## 2. Target File Routing Rules (Anti-Bloat)

1. **Modular Developer Skills (`SKILL.md` <= 60 lines)**:
   - Never append code blocks, pitfalls, or checklists directly into a modular `SKILL.md` router (`java-developer`, `python-developer`, `typescript-developer`, `react-developer`, `csharp-developer`, `powershell-writer`, `python-api-writer`).
   - Route learnings to the appropriate topical file:
     - Memory leaks / GC / closures -> `runtime-and-memory/` or `memory/`
     - Async / threads / event loop -> `concurrency/`
     - Auth / injection / secrets -> `security/`
     - Tests / fixtures / mocks -> `testing/`
     - Architecture / DI / patterns -> `core/` or `architecture/`
2. **Task / Orchestration Skills**:
   - Place operational steps in `SKILL.md` (`## Workflow` or `## Common Pitfalls`) and deep checklists in `references/*.md`.
   - When a trap can be prevented deterministically (e.g., validation check), prefer updating an existing script in `scripts/` over adding long prose warnings.
3. **Deduplication Check**:
   - Before editing, search the target skill directory for the core keywords of the learning. If the exact rule is already enforced, classify as `ALREADY_COVERED` and mark `skipped`.

---

## 3. Semantic Versioning Rules

| Edit Scope | Bump | Example |
|---|---|---|
| Typo fix, clarified pitfall, updated command flag | `PATCH` | `1.0.0` -> `1.0.1` |
| New pitfall subsection, new checklist item, script enhancement | `MINOR` | `1.0.0` -> `1.1.0` |
| Breaking workflow change or skill restructure | `MAJOR` | `1.1.0` -> `2.0.0` |

---

## 4. Immediate Learning Promotion

Process each learning as soon as the task establishes sufficient evidence. Update the owning skill for novel reusable rules, validate the patch and global visibility, then mark the memory promoted. Recording memory alone does not complete promotion; do not wait for three memories or a later delivery.

Use `ALREADY_COVERED` for rules already enforced and `SKIP_TRANSIENT` for task-specific details. An end-of-task pending-memory check catches omissions; it does not replace immediate promotion. Disclose blocked updates and their targets rather than marking them complete.

---

## 5. Skill Quality & Optimization Checklist (Mode B)

When auditing an existing skill (`SKILL.md`, `references/`, `scripts/`), diagnose and patch these four weakness categories:

| Weakness | Symptoms | Targeted Patch |
|---|---|---|
| **Vague Trigger `description`** | Under ~80 chars, generic verb ("helps with X"), no quoted user trigger phrases or `Use when...` scenarios. | Expand `description` with 5–8 realistic quoted trigger phrases and concrete invocation scenarios. |
| **Bloated / Noisy Instructions** | Modular `SKILL.md` router `> 65` lines; monolithic `SKILL.md` `> 1,000` lines; duplicated examples; orphan files in `references/` or `scripts/`. | Move deep content into `references/` or topical submodules; link or remove orphan assets. |
| **Edge-Case Blind Spots** | Bare `python`/`py` commands, unquoted PowerShell `$` strings, missing Windows/POSIX notes, or scripts scoring `>= 40` on `check-overengineering`. | Switch to `.venv` Python paths, add OS/quoting caveats, and simplify bloated script helpers. |
| **Missing Verification Steps** | Task skill executes `scripts/` or mutates files without stating how to verify success (expected stdout, exit codes, or validator command). | Add a concise verification step with exact command and expected pass criteria. |
