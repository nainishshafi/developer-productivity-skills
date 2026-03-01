# Python Linter Reference

Supporting reference for the `python-linter` skill — ruff and mypy configs, rule sets, and CI integration.

---

## Recommended `pyproject.toml` Config

```toml
[tool.ruff]
line-length = 120
target-version = "py312"  # adjust to your project's minimum Python version

[tool.ruff.lint]
select = [
    "E",    # pycodestyle errors
    "W",    # pycodestyle warnings
    "F",    # pyflakes (unused imports, undefined names)
    "I",    # isort (import order)
    "B",    # flake8-bugbear (likely bugs and design issues)
    "C4",   # flake8-comprehensions (simplify comprehensions)
    "UP",   # pyupgrade (use modern Python syntax)
    "SIM",  # flake8-simplify (simplifiable code)
    "N",    # pep8-naming
    "RUF",  # ruff-specific rules
]
ignore = [
    "E501",   # line too long — handled by formatter
]

[tool.ruff.lint.isort]
known-first-party = ["myproject"]  # replace with your package name

[tool.ruff.format]
quote-style = "double"
indent-style = "space"
line-ending = "auto"

[tool.mypy]
python_version = "3.12"
strict = true
warn_return_any = true
warn_unused_ignores = true
disallow_untyped_defs = true
disallow_incomplete_defs = true

[[tool.mypy.overrides]]
module = "tests.*"
disallow_untyped_defs = false
```

---

## Ruff Rule Sets

| Code | Plugin | What it catches |
|------|--------|-----------------|
| `E` / `W` | pycodestyle | PEP 8 style violations |
| `F` | pyflakes | Undefined names, unused imports |
| `I` | isort | Import ordering |
| `B` | bugbear | Likely bugs (mutable defaults, bare `except`, etc.) |
| `C4` | comprehensions | Unnecessary list/set/dict comprehensions |
| `UP` | pyupgrade | Old-style syntax (use f-strings, `|` unions, etc.) |
| `SIM` | simplify | Verbose conditions, redundant code |
| `N` | pep8-naming | Naming convention violations |
| `RUF` | ruff | Ruff-specific rules |
| `ANN` | annotations | Missing type annotations (use with mypy) |
| `PT` | pytest-style | pytest best practices |
| `S` | bandit | Security issues |

### Strict Rule Set (for mature codebases)

```toml
[tool.ruff.lint]
select = ["ALL"]
ignore = [
    "E501",    # line length
    "D",       # docstrings (add separately if needed)
    "ANN101",  # self annotation
    "ANN102",  # cls annotation
    "COM812",  # trailing comma (conflicts with formatter)
    "ISC001",  # single-line implicit concat (conflicts with formatter)
]
```

---

## Common ruff Commands

```bash
# Check for issues (no fix)
ruff check .

# Check and auto-fix safe issues
ruff check --fix .

# Check and fix ALL issues (including unsafe fixes)
ruff check --fix --unsafe-fixes .

# Format code (replaces black)
ruff format .

# Preview formatting changes without applying
ruff format --diff .

# Check a single file
ruff check path/to/file.py

# Show which rule triggered each violation
ruff check --show-source .

# List all available rules
ruff rule --all
```

---

## Common mypy Commands

```bash
# Check entire project
mypy .

# Strict mode (enables all optional checks)
mypy --strict .

# Check a single file
mypy path/to/file.py

# Show error codes (useful for adding inline ignores)
mypy --show-error-codes .

# Generate a baseline to ignore existing errors
mypy . --ignore-missing-imports
```

### Inline Suppression

```python
x = some_untyped_function()  # type: ignore[no-untyped-call]
```

---

## CI Integration

### GitHub Actions

```yaml
name: Lint

on: [push, pull_request]

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install ruff mypy
      - run: ruff check .
      - run: ruff format --check .
      - run: mypy .
```

### Pre-commit Hooks

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.4.0
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format
```

Install: `pip install pre-commit && pre-commit install`

---

## Tool Decision Guide

| Need | Tool |
|------|------|
| Lint + auto-fix style issues | `ruff check --fix .` |
| Format code consistently | `ruff format .` |
| Check type correctness | `mypy .` or `pyright` |
| All-in-one fast option | `ruff` (replaces flake8, black, isort) |
| Type stubs for third-party libs | `pip install types-<package>` |

---

## Fixing Common Violations

| Code | Violation | Fix |
|------|-----------|-----|
| `F401` | Unused import | Remove or add `# noqa: F401` if re-exported |
| `F841` | Local variable assigned but never used | Remove variable or use `_` |
| `E711` | Comparison to `None` using `==` | Use `is None` / `is not None` |
| `B006` | Mutable default argument | Use `None` default + assign in body |
| `UP007` | Use `X \| Y` instead of `Optional[X]` | Update to Python 3.10+ union syntax |
| `I001` | Import order | Let ruff fix automatically with `--fix` |
| `N806` | Variable in function should be lowercase | Rename variable |
