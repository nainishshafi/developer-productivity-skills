---
name: github-security-scanner-hook
description: Use when the user asks to "scan for security vulnerabilities", "check for secrets in code", "set up a pre-commit security hook", "install security scanning", "scan staged files for secrets", "check for hardcoded credentials", "run a security scan before commit", "detect leaked API keys", "add a git commit hook for security", "security check before push", "scan for SQL injection", "check for XSS vulnerabilities", "check for prompt injection", "scan for SSTI", "check for unsafe deserialization", "scan for SSRF", "detect weak cryptography", "detect injection flaws", "check for command injection", "audit subprocess security", or wants to prevent committing security issues to git.
version: 1.4.0
---

# GitHub Security Scanner Hook

Scan staged files for secrets, prompt injection, and code-level security vulnerabilities before every git commit.
Works with any language or file type — `detect-secrets` finds hardcoded credentials and API keys; `semgrep` (plus built-in fallback rules) finds **XSS & SSTI**, **Prompt Injection & Stealth Unicode (OWASP LLM01/LLM02/LLM06)**, **SQL/NoSQL injection**, **command/shell injection**, **code injection & unsafe deserialization**, **path traversal & destructive filesystem deletion**, **SSRF & open redirects**, **weak cryptography & TLS verification bypass**, **subprocess secret leaks**, and **hardcoded personal paths / PII** across Python, JavaScript/TypeScript, Go, C#, PowerShell, Markdown, and configs.
Can run as a one-off manual scan or install as an automated git pre-commit hook.

## Prerequisites

- Python 3.8+ available (via local `.venv`)
- Git repository (any language — Python, JS/TS, Go, C#, PowerShell, Markdown, etc.)
- Staged files to scan, or `--full-repo` to scan everything
- Internet access on first run only if installing optional `detect-secrets` and `semgrep` packages (`scan-staged.py` also runs zero-dependency built-in fallback rules offline)
- Write access to `.git/hooks/` (for hook installation only)

## Workflow

### Step 1 — Set Up `.venv` and Install Tools

Always use `.venv` — create it if it does not exist, then optionally install `detect-secrets` and `semgrep`:

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

Both `detect-secrets` and `semgrep` are optional independently — if either is missing (e.g., offline environments), `scan-staged.py` automatically falls back to its built-in secret, OWASP code, and prompt-injection rules. When `semgrep` is installed, it uses the bundled rules in `rules/security.yml` (no login or network access required).

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
4. **For XSS & SSTI:** Use `textContent` / `insertAdjacentText()`, sanitise HTML with DOMPurify before `innerHTML`/`outerHTML`/`dangerouslySetInnerHTML`, replace Flask `Markup()` / Django `mark_safe()` with `format_html()`, use `render_template()` instead of `render_template_string()`, and enable `autoescape=select_autoescape()` in Jinja2
5. **For Prompt Injection & Stealth Unicode:** Remove adversarial override phrases or hidden HTML comments, strip bidirectional control characters (`U+202A–U+202E`, `U+2066–U+2069`), keep LLM `system` prompts static, and isolate untrusted user/RAG text inside passive `<sources>` XML delimiters
6. **For SQL/NoSQL, Command/Code Injection & Unsafe Deserialization:** Use parameterized queries (`?` / `$1` / `ExecuteSqlInterpolated`), replace MongoDB `$where`, use `subprocess.run([...], shell=False)` / `execFile()` / `spawn(..., { shell: false })`, eliminate `Invoke-Expression`, remove `eval()`/`exec()`/`new Function()`, and replace `pickle.loads()`/`yaml.load()` with JSON or `yaml.safe_load()`
7. **For SSRF, Open Redirects, Weak Crypto & TLS Bypass:** Allowlist HTTPS schemes/hosts and block private/link-local IPs for outbound requests and redirects, replace MD5/SHA-1 with SHA-256 or argon2/bcrypt/scrypt, and remove `verify=False` / `rejectUnauthorized: false` / `NODE_TLS_REJECT_UNAUTHORIZED=0`
8. **For hardcoded personal filesystem paths / PII & env leaks:** Scrub `process.env`/`os.environ` before spawning subprocesses, constrain paths inside allowed base directories, and replace machine-specific user directory paths with portable relative paths (`./`) or generic placeholders (`/path/to/...`)
9. **For false positives:** Add secrets to `.secrets.baseline` using `$PYTHON -m detect_secrets audit .secrets.baseline`, or suppress reviewed code patterns inline with `# nosemgrep`
10. Re-stage the fixed files and re-run Step 2 to confirm all HIGH findings are resolved

## Audit Guardrails

- Never rely solely on manual visual inspection for security sign-off; always execute `scan-staged.py` (running `detect-secrets`, bundled `semgrep` rules, or built-in fallback rules) against the actual staged files or git diff.

## Additional Resources

- **`references/github-security-scanner-hook-reference.md`** — Full severity classification table, detect-secrets plugin mapping, all semgrep & fallback vulnerability types with remediation examples (XSS/SSTI, Prompt Injection, Deserialization, SSRF, Weak Crypto/TLS, SQLi/Command Injection), `.secrets.baseline` workflow, false-positive handling, CI/CD integration YAML, `--no-verify` warning, and secret rotation checklist
- **`rules/security.yml`** — Bundled Semgrep rules (53 rules) covering SQL/NoSQL injection, command/shell injection, XSS & SSTI, prompt injection & stealth Unicode, code injection & unsafe deserialization, path traversal & destructive FS, SSRF & open redirects, weak crypto & TLS bypass, subprocess env leaks, and hardcoded personal paths across Python, JS/TS, Go, C#, PowerShell, and generic files
- **`scripts/scan-staged.py`** — Scans staged (or all tracked) files using `detect-secrets`, `semgrep`, and zero-dependency built-in fallback/prompt-injection rules; outputs structured JSON with findings and severity summary
- **`scripts/install-hook.py`** — Installs or extends the git pre-commit hook to automate scanning on every future commit
