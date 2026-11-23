---
name: github-security-scanner-hook
description: Use when the user asks to "scan for security vulnerabilities", "check for secrets in code", "set up a pre-commit security hook", "install security scanning", "scan staged files for secrets", "check for hardcoded credentials", "run a security scan before commit", "detect leaked API keys", "add a git commit hook for security", "security check before push", "scan for SQL injection", "check for XSS vulnerabilities", "check for prompt injection", "scan for SSTI", "check for unsafe deserialization", "scan for SSRF", "detect weak cryptography", "detect injection flaws", "check for command injection", "audit subprocess security", or wants to prevent committing security issues to git.
version: 1.4.3
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

### Step 1 — Select Python Venv and Install Tools

Prefer a shared agent venv if configured (e.g., `~/.gemini/agent-venv/Scripts/python.exe` on Windows or `~/.gemini/agent-venv/bin/python` on POSIX) or an existing project `.venv`; otherwise create `.venv` and optionally install `detect-secrets` and `semgrep`:

**Windows (PowerShell):**
```powershell
$SHARED_PY = Join-Path $HOME ".gemini\agent-venv\Scripts\python.exe"
$PYTHON = if (Test-Path $SHARED_PY) { $SHARED_PY } elseif (Test-Path .venv\Scripts\python.exe) { ".venv\Scripts\python.exe" } else { python -m venv .venv; ".venv\Scripts\python.exe" }
& $PYTHON -m pip show detect-secrets *> $null; if ($LASTEXITCODE -ne 0) { & $PYTHON -m pip install detect-secrets }
& $PYTHON -m pip show semgrep *> $null; if ($LASTEXITCODE -ne 0) { & $PYTHON -m pip install semgrep }
```

**Unix / macOS (Bash):**
```bash
SHARED_PY="$HOME/.gemini/agent-venv/bin/python"
if [ -x "$SHARED_PY" ]; then PYTHON="$SHARED_PY"
elif [ -x .venv/bin/python ]; then PYTHON=".venv/bin/python"
else python3 -m venv .venv && PYTHON=".venv/bin/python"; fi
"$PYTHON" -m pip show detect-secrets > /dev/null 2>&1 || "$PYTHON" -m pip install detect-secrets
"$PYTHON" -m pip show semgrep > /dev/null 2>&1 || "$PYTHON" -m pip install semgrep
```

Both `detect-secrets` and `semgrep` are optional independently. If either is unavailable or fails to complete, `scan-staged.py` reports the fallback and runs the corresponding built-in rules. External commands have a 20-second timeout per invocation. A clean fallback means the built-in rules reported no findings; it does not mean the external scanner passed. When `semgrep` is installed (in `.venv`, alongside the selected `python`, or on `PATH`), it uses the bundled rules in `rules/security.yml` (no login or network access required).

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
1. Updates an existing managed scanner block in place, preserving other hook logic. Refuses to edit incomplete or duplicate managed blocks.
2. For a hook without a managed block, offers to Append (default), Overwrite, or Skip.
3. Creates or extends the hook to call `scan-staged.py` before every commit.
4. Makes the hook executable and prints its path.

After installation, remind the user:
- The hook lives in `.git/hooks/pre-commit` — this directory is **not tracked by git**, so each contributor must run `install-hook.py` themselves to opt in
- HIGH severity findings, a missing scanner script, or an unexpected scanner exit status block the commit. MEDIUM/LOW findings prompt only in an interactive terminal; otherwise the hook reports the warning and continues.
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
