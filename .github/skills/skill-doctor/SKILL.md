---
name: skill-doctor
description: >-
  Reads unprocessed learnings from project-memory (journal and ledger), triages whether each lesson should update an existing skill, scaffold a new skill via skill-creator, or be skipped, applies anti-bloat edits to the right skill module, validates frontmatter/links, and marks learnings as promoted so they are not re-processed. Runs periodically inside software-factory-agent or on demand. Use when asked to "skill doctor", "run skill doctor", "update skills from memory", "evolve skills from learnings", "heal skills", "promote learnings to skills", or "audit skill health".
version: 1.0.0
---

# Skill Doctor

Closed-loop continuous improvement skill that converts hard-won `project-memory` learnings into durable repository skills—updating existing skill modules, creating new skills when recurring capability gaps emerge, and auditing all skill health.

---

## When to Use This Skill

- Periodically at the end of a `software-factory-agent` run (when `>= 3` unprocessed learnings accumulate or Phase 8 remediation was triggered).
- After debugging a tricky platform, security, framework, or tooling trap that future sessions must not repeat.
- When asked to `"run skill doctor"`, `"update skills from memory"`, `"evolve skills from learnings"`, `"promote learnings to skills"`, or `"audit skill health"`.

---

## Workflow

### Step 1 — Harvest Unprocessed Learnings

Retrieve pending `journal` and `ledger` learnings via the `project-memory` MCP tool `get_unprocessed_learnings`, or run the diagnostic CLI:

```powershell
.\.venv\Scripts\python.exe .github/skills/skill-doctor/scripts/skill-doctor.py diagnose
```

*(On POSIX, substitute `.\.venv\Scripts\python.exe` with `.venv/bin/python`.)*

If `0` pending learnings exist, run `audit-skills` to verify repository health and exit cleanly.

---

### Step 2 — Triage & Route Each Learning

Consult [references/skill-evolution-rubric.md](references/skill-evolution-rubric.md) and classify each pending memory into one of three actions:

| Classification | Criteria | Action |
|---|---|---|
| **`UPDATE_EXISTING_SKILL`** | Matches an existing skill domain and adds a reusable pitfall, guardrail, command convention, or pattern not yet documented. | Edit the target skill module (or `SKILL.md` / `references/`) and mark `promoted`. |
| **`CREATE_NEW_SKILL`** | `>= 2` learnings cluster around a repeatable technology, workflow, or domain not covered by any existing skill. | Scaffold via `skill-creator`, populate modules, register in factory/orchestrator/README, and mark `promoted`. |
| **`SKIP_TRANSIENT`** | Already documented in the target skill (`ALREADY_COVERED`) or one-off task/ticket state (`SKIP_TRANSIENT`). | Do not bloat skills; mark `skipped` so it is not re-triaged. |

---

### Step 3 — Apply Skill Updates Safely (Anti-Bloat Guardrails)

1. **Modular Knowledge-Pack Skills** (e.g., `java-developer`, `python-developer`, `typescript-developer`, `react-developer`, `csharp-developer`, `powershell-writer`):
   - **NEVER bloat the lean `SKILL.md` router** (keep under 60 lines).
   - Add new pitfalls, patterns, or guardrails to the matching topical submodule (`core/`, `runtime-and-memory/`, `concurrency/`, `security/`, `testing/`, etc.) or `references/`.
2. **Task / Reference Skills**:
   - Update the relevant section (`## Workflow`, `## Common Pitfalls`, or `references/*.md`), or harden helper scripts in `scripts/`.
3. **Zero Personal Paths & Secret Hygiene**:
   - Never embed local user directory paths (`C:\Users\...`, `/home/...`) or secrets in skill docs or scripts.
4. **Bump Semantic Version**:
   - Increment `version` in the updated `SKILL.md` frontmatter (`PATCH` for pitfalls/clarifications; `MINOR` for new sections or scripts).

---

### Step 4 — Scaffold New Skills (When Warranted)

When `CREATE_NEW_SKILL` is selected:
1. Run `skill-creator` scaffolding:
   ```powershell
   node .github/skills/skill-creator/scripts/scaffold-skill.js <skill-name> .github/skills [--modular]
   ```
2. Populate `SKILL.md` (with 5–8 realistic trigger phrases in `description`) and supporting modules/references/scripts using the harvested learnings.
3. Register the new skill in:
   - `.github/agents/software-factory-agent.md` (skill count + routing matrix)
   - `.github/skills/agent-orchestrator/scripts/orchestrator-context-manager.py` (stage mapping if applicable)
   - `README.md` (Skills Catalog table, category section, and directory tree)

---

### Step 5 — Validate & Mark Learnings Promoted

1. Run the skill health audit:
   ```powershell
   .\.venv\Scripts\python.exe .github/skills/skill-doctor/scripts/skill-doctor.py audit-skills
   ```
2. Validate all `SKILL.md` frontmatter and YAML files:
   ```powershell
   npm run validate:skills --prefix mcp/sql-connector
   ```
3. If any Python/JS/TS scripts were created or modified, verify low over-engineering risk (`score < 40`):
   ```powershell
   .\.venv\Scripts\python.exe .github/skills/agent-orchestrator/scripts/orchestrator-context-manager.py check-overengineering --file <modified-script>
   ```
4. Mark processed memory IDs via `project-memory` MCP `mark_learning_promoted` (or CLI `skill-doctor.py mark --ids <id1,id2> --status promoted --target-skill <skill>`).

---

## Additional Resources

- [Skill Evolution Rubric](references/skill-evolution-rubric.md) — Triage decision matrix, deduplication rules, modular router protection, and versioning guide.
- [Skill Doctor CLI](scripts/skill-doctor.py) — Automated diagnostic, schema migration, skill audit, and promotion-marking script.

