# developer-productivity-skills

A collection of reusable AI skills stored in `.github/skills/`, compatible with **Claude Code** and **GitHub Copilot**. These skills provide ready-made workflows for common development tasks — invoke them by typing a trigger phrase in your AI session.

## Skills

### `scan-repo-readme`
Efficiently locate and extract information from repository README files. Uses a lightweight subagent to perform dual-phase search (keyword + semantic) and writes results to a timestamped file under `.scan-readme-results/`. When no query is provided, returns a full summary of all README files found.

**Trigger phrases:** "scan the readme", "read the repo readme", "check the project documentation", "search the readme for X", "what does the readme say about Y", "summarize the readme", "find readme", "look up X in the readme"

---

### `trace-code-context`
Generates a rich, ground-truth Markdown context file for any source code file — covering defined symbols, imports, callers, callees, a Mermaid call graph, and a business-readable description. Uses a Python script for AST/parser-validated symbol extraction (ground truth) and a subagent for business context. Skips regeneration if the source file has not changed since the last run. Output is written to `.code-context/` mirroring the source file structure.

**Trigger phrases:** "trace code context", "analyze this file", "show callers and callees", "generate a code context file", "map dependencies for X", "what calls this file", "what does this file call", "document this code file", "create a mermaid diagram for this code", "explain what this module does"

**Supported languages:** Python, Java, JavaScript, TypeScript, Go, C#, Ruby, Rust, C++, C

---

### `scan-halucinated-tests`
Cross-validates a test file against its real source code to detect LLM hallucinations — phantom functions, non-existent properties, wrong import paths, fabricated constants, bad mock targets, and incorrect exception types. Uses `trace-code-context` to extract authoritative ground truth from the source, a parser script to extract all references from the test, then a subagent to cross-reference the two. Results are written to `.scan-test-results/` as a timestamped Markdown report with severity-graded findings.

**Trigger phrases:** "scan for hallucinated tests", "check if my tests are hallucinated", "validate tests against source", "verify test accuracy", "find fake test assertions", "audit tests for hallucinations", "test hallucination scan", "verify tests match source code"

**Supported languages:** Python (AST), Java (JUnit/Mockito), C# (xUnit/NUnit/MSTest/Moq), JavaScript/TypeScript (Jest/Vitest)

---

### `skill-creator`
Scaffolds and writes new skills following established conventions. Handles both reference/knowledge skills (rich documentation) and task/action skills (step-by-step workflows with scripts). Includes a Python script that generates the folder and boilerplate files.

**Trigger phrases:** "create a new skill", "add a skill", "write a skill", "scaffold a skill", "build a skill"

---

### `python-linter`
Runs ruff (lint + format) and optionally mypy (type checking) on Python code. Auto-fixes what it can and reports remaining issues with file and line references.

**Trigger phrases:** "lint python", "run the linter", "fix linting errors", "run ruff", "format python code", "check types", "run mypy"

**Prerequisites:** Python on PATH — skill creates `.venv` and installs `ruff`/`mypy` automatically

---

### `github-security-scanner-hook`
Scans staged files for secrets and code-level security vulnerabilities before every git commit. Language-agnostic — works with Python, JavaScript, Go, Ruby, and more. Uses `detect-secrets` for credential/key detection and `semgrep` with 20 bundled rules for injection flaws, XSS, path traversal, and other OWASP patterns. Can install a git pre-commit hook to automate scanning on every commit.

**Trigger phrases:** "scan for security vulnerabilities", "check for secrets in code", "set up a pre-commit security hook", "scan staged files for secrets", "check for hardcoded credentials", "detect leaked API keys", "scan for SQL injection", "check for XSS vulnerabilities"

**Prerequisites:** Python on PATH — skill creates `.venv` and installs `detect-secrets` and `semgrep` automatically

---

### `sync-github-forks`
Syncs all your GitHub forked repositories — clones missing ones and pulls existing ones. Uses the `gh` CLI for authentication, no token config needed.

**Trigger phrases:** "sync github forks", "sync forks", "pull all my forks"

**Prerequisites:** `gh` CLI (authenticated), `jq`, `git`, SSH key added to GitHub

## Usage

### Claude Code
Skills are loaded automatically from `.github/skills/`. Invoke them by using any trigger phrase above in your Claude Code session.

### GitHub Copilot
Skills in `.github/skills/` are picked up as custom instructions by Copilot Chat. Use the same trigger phrases in Copilot Chat, or reference a skill by name (e.g. `@workspace /python-linter`).

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
    ├── trace-code-context/
    │   ├── SKILL.md
    │   ├── references/
    │   │   └── trace-code-context-reference.md
    │   └── scripts/
    │       └── trace-context.py
    ├── scan-halucinated-tests/
    │   ├── SKILL.md
    │   ├── references/
    │   │   └── scan-halucinated-tests-reference.md
    │   └── scripts/
    │       └── parse-test-refs.py
    ├── skill-creator/
    │   ├── SKILL.md
    │   ├── references/
    │   │   └── skill-anatomy.md
    │   └── scripts/
    │       └── scaffold-skill.py
    ├── python-linter/
    │   ├── SKILL.md
    │   └── references/
    │       └── python-linter-reference.md
    ├── github-security-scanner-hook/
    │   ├── SKILL.md
    │   ├── references/
    │   │   └── github-security-scanner-hook-reference.md
    │   ├── rules/
    │   │   └── security.yml
    │   └── scripts/
    │       ├── scan-staged.py
    │       └── install-hook.py
    └── sync-github-forks/
        ├── SKILL.md
        └── scripts/
            ├── setup-ssh.sh
            └── sync-forks.sh
```
