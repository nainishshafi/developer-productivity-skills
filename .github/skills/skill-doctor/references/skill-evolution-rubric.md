# Skill Evolution Rubric

Decision framework used by **`skill-doctor`** to turn raw `project-memory` entries (`journal` and `ledger`) into high-signal, non-bloated skill improvements.

---

## 1. Triage Classification Matrix

| Signal in Memory (`learnings` + `summary` + `tags`) | Classification | Target Action |
|---|---|---|
| Documents a repeatable pitfall, shell/OS trap, library quirk, security hazard, or architectural rule missing from an existing skill | `UPDATE_EXISTING_SKILL` | Edit the matching skill's submodule or `references/` (or `SKILL.md` for non-modular skills), bump `version`, mark `promoted`. |
| Same pitfall/rule is already explicitly covered in the matched skill's files | `SKIP_TRANSIENT` (`ALREADY_COVERED`) | Leave skill untouched to prevent duplication bloat; mark `skipped` with `targetSkill` set to the covering skill. |
| Narrow one-off implementation detail (e.g., specific ticket ID, temporary file name, transient feature WIP) | `SKIP_TRANSIENT` | Do not pollute general-purpose skills; mark `skipped` with `targetSkill: "none"`. |
| `>= 2` unprocessed learnings share an unmapped domain/tag cluster (e.g., `graphql`, `terraform`, `kafka-streams`) with no covering skill | `CREATE_NEW_SKILL` | Scaffold a new skill via `skill-creator`, author focused modules, register in factory/README, mark `promoted` with `targetSkill: "new:<skill-name>"`. |

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

## 4. Periodic Software Factory Cadence

`skill-doctor` should run at the end of `software-factory-agent` delivery when **any** of these triggers hold:
1. **Batch Threshold**: `>= 3` memories in `.project-memory/memory.db` have `skill_status = 'pending'`.
2. **Remediation Trigger**: Phase 8 (`troubleshoot-and-fix`) was activated during the pipeline run (meaning a real defect was diagnosed and fixed).
3. **Explicit Request**: User asks to run `skill-doctor`, evolve skills, or audit skill health.

