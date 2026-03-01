# github-skills

A collection of Claude Code skills stored in `.github/skills/`, providing reusable workflows for common development tasks.

## Skills

### `scan-repo-readme`
Efficiently locate and extract information from repository README files. Uses a lightweight subagent to perform dual-phase search (keyword + semantic) and writes results to a timestamped file.

**Trigger phrases:** "scan the readme", "search the readme for X", "what does the readme say about Y", "summarize the readme"

### `sync-github-forks`
Syncs all your GitHub forked repositories — clones missing ones and pulls existing ones. Uses the `gh` CLI for authentication, no token config needed.

**Trigger phrases:** "sync github forks", "sync forks", "pull all my forks"

**Prerequisites:** `gh` CLI (authenticated), `jq`, `git`, SSH key added to GitHub

### `skill-creator`
Scaffolds and writes new Claude Code skills following established conventions. Handles both reference/knowledge skills (rich documentation) and task/action skills (step-by-step workflows with scripts). Includes a Python script that generates the folder and boilerplate files.

**Trigger phrases:** "create a new skill", "add a skill", "write a skill", "scaffold a skill", "build a skill"

### `python-linter`
Runs ruff (lint + format) and optionally mypy (type checking) on Python code. Auto-fixes what it can and reports remaining issues with file and line references.

**Trigger phrases:** "lint python", "run the linter", "fix linting errors", "run ruff", "format python code", "check types", "run mypy"

**Prerequisites:** `ruff` (required), `mypy` (optional)

## Usage

These skills are loaded automatically by Claude Code from `.github/skills/`. Invoke them by using any of the trigger phrases above in your Claude Code session.

## Structure

```
.github/
└── skills/
    ├── scan-repo-readme/
    │   ├── SKILL.md
    │   ├── references/
    │   │   └── search-patterns.md
    │   └── scripts/
    │       └── find-readmes.py
    ├── sync-github-forks/
    │   ├── SKILL.md
    │   └── scripts/
    │       ├── setup-ssh.sh
    │       └── sync-forks.sh
    ├── skill-creator/
    │   ├── SKILL.md
    │   ├── references/
    │   │   └── skill-anatomy.md
    │   └── scripts/
    │       └── scaffold-skill.py
    └── python-linter/
        ├── SKILL.md
        └── references/
            └── python-linter-reference.md
```
