---
name: github-security-scanner-hook
description: Use when the user asks to "scan for security vulnerabilities", "check for secrets in code", "set up a pre-commit security hook", "install security scanning", "scan staged files for secrets", "check for hardcoded credentials", "run a security scan before commit", "detect leaked API keys", "add a git commit hook for security", "security check before push", "scan for SQL injection", "check for XSS vulnerabilities", "detect injection flaws", "check for command injection", "audit subprocess security", or wants to prevent committing security issues to git.
version: 1.2.0
---

# GitHub Security Scanner Hook

Scan staged files for secrets and code-level security vulnerabilities before every git commit.
Works with any language or file type — `detect-secrets` finds hardcoded credentials and API keys; `semgrep` finds injection flaws, command injection, shell execution risks, XSS, path traversal, destructive filesystem operations, and OWASP Top 10 patterns across Python, JavaScript/TypeScript, Go, Ruby, Java, C#, and more.
Can run as a one-off manual scan or install as an automated git pre-commit hook.

## Prerequisites

- Python 3.8+ available on PATH (to create the `.venv`)
- Git repository (any language — Python, JS/TS, Go, Ruby, Java, C#, etc.)
- Staged files to scan, or `--full-repo` to scan everything
- Internet access on first run only (to pip-install `detect-secrets` and `semgrep`)
- Write access to `.git/hooks/` (for hook installation only)

## Workflow

### Step 1 — Set Up `.venv` and Install Tools

Always use `.venv` — create it if it does not exist, then install `detect-secrets` and `semgrep`:

**Windows (PowerShell):**
```powershell
if (-not (Test-Path .venv)) { python -m venv .venv }
$PYTHON = if (Test-Path .venv\Scripts\python.exe) { ".venv\Scripts\python.exe" } else { "python" }
& $PYTHON -m pip show detect-secrets *> $null; if ($LASTEXITCODE -ne 0) { & $PYTHON -m pip install detect-secrets }
& $PYTHON -m pip show semgrep *> $null; if ($LASTEXITCODE -ne 0) { & $PYTHON -m pip install semgrep }
```

**Unix / macOS (Bash):**
```bash
[ -d .venv ] || python -m venv .venv
PYTHON=$(if [ -f .venv/Scripts/python ]; then echo .venv/Scripts/python; else echo .venv/bin/python; fi)
$PYTHON -m pip show detect-secrets > /dev/null 2>&1 || $PYTHON -m pip install detect-secrets
$PYTHON -m pip show semgrep > /dev/null 2>&1 || $PYTHON -m pip install semgrep
```

Both tools are optional independently — if `semgrep` is not installed the scan still runs with `detect-secrets` only. Semgrep uses the bundled rules in `rules/security.yml` (no login or network access required).

### Step 2 — Run Security Scan on Staged Files

Run `scan-staged.py` to check all currently staged files:

```bash
$PYTHON .github/skills/github-security-scanner-hook/scripts/scan-staged.py
```

To scan the entire repository instead of only staged files:

```bash
$PYTHON .github/skills/github-security-scanner-hook/scripts/scan-staged.py --full-repo
```

The script prints a JSON summary to stdout and exits with:
- **Exit code 0** — no findings (clean)
- **Exit code 1** — one or more HIGH severity findings (would block the commit)
- **Exit code 2** — only MEDIUM or LOW severity findings (warnings, no block)

### Step 3 — Review and Present Findings

Parse the JSON output and present findings grouped by severity:

- **HIGH** — Must be fixed before committing. Identify the flagged file and line, explain what was found (e.g., "AWS secret key on line 14 of `config.py`"), why it is dangerous, and the specific remediation steps.
- **MEDIUM** — Warn the user with a clear explanation and ask whether they want to fix it first or proceed.
- **LOW** — Mention briefly and move on unless the user asks for detail.

For each finding include: file path, line number, finding type, severity, and a plain-English explanation.
Consult `references/github-security-scanner-hook-reference.md` for the full severity table, finding types, and remediation guidance.

If the scan is clean (exit code 0), confirm clearly: "No security issues found in staged files."

### Step 4 — Install Pre-Commit Hook (Optional)

Ask the user: "Would you like to install this as a git pre-commit hook so every future commit is scanned automatically?"

If yes:

```bash
$PYTHON .github/skills/github-security-scanner-hook/scripts/install-hook.py
```

The installer:
1. Detects whether `.git/hooks/pre-commit` already exists — if it does, it offers to Append (default), Overwrite, or Skip rather than silently destroying existing hooks
2. Creates or extends the hook to call `scan-staged.py` before every commit
3. Makes the hook executable
4. Prints the hook path and a confirmation message

After installation, remind the user:
- The hook lives in `.git/hooks/pre-commit` — this directory is **not tracked by git**, so each contributor must run `install-hook.py` themselves to opt in
- HIGH severity findings block the commit; MEDIUM/LOW prompt a confirmation
- Emergency bypass: `git commit --no-verify` — see the reference for important caveats

### Step 5 — Remediate Issues

For each HIGH or MEDIUM finding the user wants to fix:

1. Open the flagged file at the reported line number
2. **For hardcoded credentials:** Replace with an environment variable (`os.environ["KEY_NAME"]`) or a secrets manager call
3. **For private keys:** Remove the key, revoke it immediately (assume it is compromised), generate a new one, and add the key file pattern to `.gitignore`
4. **For code vulnerabilities & weak cryptography (semgrep):** Fix injection vectors (use parameterized queries, `subprocess.run([...], shell=False)`) and replace insecure hashes (`hashlib.md5` → `hashlib.sha256`, `random` → `secrets`)
5. **For false positives:** Add to the `.secrets.baseline` allowlist using `python -m detect_secrets audit .secrets.baseline`
6. Re-stage the fixed files and re-run Step 2 to confirm all HIGH findings are resolved

## Additional Resources

- **`references/github-security-scanner-hook-reference.md`** — Full severity classification table, detect-secrets plugin mapping, semgrep vulnerability types with remediation examples, `.secrets.baseline` workflow, false-positive handling, CI/CD integration YAML, `--no-verify` warning, and secret rotation checklist
- **`rules/security.yml`** — Bundled semgrep rules covering SQL injection, command injection, path traversal, XSS, eval/exec, and open redirects across Python, JavaScript/TypeScript, and Go
- **`scripts/scan-staged.py`** — Scans staged (or all tracked) files using detect-secrets and semgrep; outputs structured JSON with findings and severity summary
- **`scripts/install-hook.py`** — Installs or extends the git pre-commit hook to automate scanning on every future commit