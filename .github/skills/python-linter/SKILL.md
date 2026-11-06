---
name: python-linter
description: Use when the user asks to "lint python", "run the linter", "fix linting errors", "check python code style", "run ruff", "format python code", "fix imports", "check types", "run mypy", or wants to find and fix Python code quality issues using ruff and mypy.
version: 1.1.0
---

# Python Linter

Run `ruff` (lint + format) and optionally `mypy` (type checking) on Python code. Auto-fixes safe lint issues and reports remaining violations that require manual attention.

## Prerequisites

- Python project with `.py` files (`uv` or `.venv` supported)

## Workflow

### Step 1 — Resolve Environment (`uv` or `.venv`)

If the project uses `uv` (`uv.lock` present or `uv` on PATH), run `uv run ruff` and `uv run mypy` directly. Otherwise, use `.venv`:

**Windows (PowerShell):**
```powershell
if (-not (Test-Path .venv)) { python -m venv .venv }
$PYTHON = if (Test-Path .venv\Scripts\python.exe) { ".venv\Scripts\python.exe" } else { "python" }
& $PYTHON -m ruff --version *> $null; if ($LASTEXITCODE -ne 0) { & $PYTHON -m pip install ruff }
& $PYTHON -m mypy --version *> $null; if ($LASTEXITCODE -ne 0) { & $PYTHON -m pip install mypy }
```

**Unix / macOS (Bash):**
```bash
[ -d .venv ] || python -m venv .venv
PYTHON=$(if [ -f .venv/Scripts/python ]; then echo .venv/Scripts/python; else echo .venv/bin/python; fi)
$PYTHON -m ruff --version 2>/dev/null || $PYTHON -m pip install ruff
$PYTHON -m mypy --version 2>/dev/null || $PYTHON -m pip install mypy
```

Check for an existing `pyproject.toml` or `ruff.toml` config. If neither exists, offer to create a sensible default (see `references/python-linter-reference.md` for the recommended config).

### Step 2 — Run Ruff Lint (with auto-fix)

```bash
$PYTHON -m ruff check --fix .
```

- `--fix` auto-corrects safe issues (unused imports, style violations, etc.)
- Note any remaining violations that require manual fixes
- If the user wants to see all issues first without fixing:
  ```bash
  $PYTHON -m ruff check .
  ```

### Step 3 — Run Ruff Format

```bash
$PYTHON -m ruff format .
```

- Formats all `.py` files in place (replaces black + isort)
- To preview changes without applying:
  ```bash
  $PYTHON -m ruff format --diff .
  ```

### Step 4 — Run Type Checking (optional)

Ask the user if they want type checking. If yes:

```bash
$PYTHON -m mypy .
```

Or for stricter checking:

```bash
$PYTHON -m mypy --strict .
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
