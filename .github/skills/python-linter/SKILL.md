---
name: python-linter
description: Use when the user asks to "lint python", "run the linter", "fix linting errors", "check python code style", "run ruff", "format python code", "fix imports", "check types", "run mypy", or wants to find and fix Python code quality issues using ruff and mypy.
version: 1.0.0
---

# Python Linter

Run ruff (lint + format) and optionally mypy (type checking) on Python code. Auto-fixes what it can and reports what needs manual attention.

## Prerequisites

- Python project with `.py` files
- `ruff` installed — `pip install ruff` or via `uv add --dev ruff`
- `mypy` installed (optional) — `pip install mypy` or via `uv add --dev mypy`

If not installed, offer to install them before proceeding.

## Workflow

### Step 1 — Check Tooling

Verify ruff is available:

```bash
ruff --version
```

If missing, install:

```bash
pip install ruff
# or with uv:
uv add --dev ruff
```

Check for an existing `pyproject.toml` or `ruff.toml` config. If neither exists, offer to create a sensible default (see `references/python-linter-reference.md` for the recommended config).

### Step 2 — Run Ruff Lint (with auto-fix)

```bash
ruff check --fix .
```

- `--fix` auto-corrects safe issues (unused imports, style violations, etc.)
- Note any remaining violations that require manual fixes
- If the user wants to see all issues first without fixing:
  ```bash
  ruff check .
  ```

### Step 3 — Run Ruff Format

```bash
ruff format .
```

- Formats all `.py` files in place (replaces black + isort)
- To preview changes without applying:
  ```bash
  ruff format --diff .
  ```

### Step 4 — Run Type Checking (optional)

Ask the user if they want type checking. If yes:

```bash
mypy .
```

Or for stricter checking:

```bash
mypy --strict .
```

See `references/python-linter-reference.md` for mypy configuration options.

### Step 5 — Report Results

Summarise:
- How many lint issues were auto-fixed
- Any remaining issues that need manual attention (with file + line references)
- Formatting changes applied
- Type errors found (if mypy was run)

If issues remain, explain each one clearly and offer to fix them.

## Additional Resources

- **`references/python-linter-reference.md`** — Recommended ruff/mypy configs, rule sets, pyproject.toml templates, CI integration
