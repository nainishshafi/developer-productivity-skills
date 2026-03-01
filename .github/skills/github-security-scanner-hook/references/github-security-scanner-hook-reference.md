# GitHub Security Scanner Hook — Reference

Supporting documentation for the `github-security-scanner-hook` skill.
Covers tool configurations, severity levels, vulnerability types, false-positive handling,
CI/CD integration, and common remediations.

---

## 1. Supported Tools

### detect-secrets

- **What it detects:** Hardcoded credentials, API keys, tokens, and high-entropy strings — works across any language and file type (Python, JavaScript, Go, Ruby, YAML, JSON, shell scripts, etc.)
- **How it works:** Regex-based plugin architecture; each plugin targets a specific secret type
- **Install:** `pip install detect-secrets`
- **Invoke:** `python -m detect_secrets scan [files...]` — outputs JSON
- **Module name:** `detect_secrets` (underscore), **package name:** `detect-secrets` (hyphen)
- **Project:** https://github.com/Yelp/detect-secrets

### semgrep

- **What it detects:** Code-level security vulnerabilities — SQL injection, XSS, command injection, path traversal, insecure deserialization, open redirects, and other OWASP Top 10 patterns
- **How it works:** AST-based pattern matching using a declarative rule language; rules are language-aware and understand code structure, not just text
- **Languages:** Python, JavaScript/TypeScript, Go, Java, Ruby, PHP, C/C++, Kotlin, Scala, and 30+ more
- **Ruleset used:** `p/owasp-top-ten` — curated rules for the OWASP Top 10 categories
- **Install:** `pip install semgrep`
- **Invoke:** `semgrep --config p/owasp-top-ten --json [files...]`
- **First-run note:** Downloads rules from the Semgrep registry on first use and caches them locally (~/.semgrep/cache)
- **Project:** https://semgrep.dev

---

## 2. Severity Classification System

| Severity | Meaning | Commit action |
|----------|---------|---------------|
| **HIGH** | Direct exposure of a secret or critical vulnerability — must not be committed | Block commit (exit 1) |
| **MEDIUM** | Probable issue requiring human review before committing | Warn, prompt to confirm |
| **LOW** | Possible issue or informational — usually safe to proceed | Mention briefly, do not prompt |

### detect-secrets plugin → severity mapping

This table mirrors the `DETECT_SECRETS_SEVERITY` dict in `scripts/scan-staged.py`. Both must stay in sync.

| detect-secrets plugin | Severity | Rationale |
|----------------------|----------|-----------|
| `AWSKeyDetector` | HIGH | AWS credentials grant cloud access |
| `AzureStorageKeyDetector` | HIGH | Azure storage account keys |
| `CloudantDetector` | HIGH | IBM Cloudant database credentials |
| `GitHubTokenDetector` | HIGH | GitHub PAT — grants repo read/write |
| `HexHighEntropyString` | HIGH | High-entropy hex strings are almost always real secrets |
| `JwtTokenDetector` | HIGH | JWT tokens carry identity claims |
| `NpmDetector` | HIGH | npm authentication tokens |
| `PrivateKeyDetector` | HIGH | RSA / EC / DSA / PEM private keys |
| `SendGridDetector` | HIGH | SendGrid API key |
| `SlackDetector` | HIGH | Slack bot / webhook tokens |
| `SoftlayerDetector` | HIGH | IBM SoftLayer API credentials |
| `SquareOAuthDetector` | HIGH | Square OAuth access tokens |
| `StripeDetector` | HIGH | Stripe secret keys |
| `TwilioKeyDetector` | HIGH | Twilio auth tokens |
| `Base64HighEntropyString` | MEDIUM | May be encoded secrets — or benign data (images, fixtures) |
| `BasicAuthDetector` | MEDIUM | HTTP basic auth credentials embedded in URLs |
| `KeywordDetector` | MEDIUM | Generic keywords like `password=`, `passwd=`, `secret=` |
| `MailchimpDetector` | MEDIUM | Mailchimp API keys |
| `SecretKeywordDetector` | MEDIUM | Similar to KeywordDetector — broader pattern matching |

### semgrep severity

semgrep reports `ERROR`, `WARNING`, or `INFO` natively. `scan-staged.py` maps these as:

| semgrep severity | Our severity |
|-----------------|-------------|
| `ERROR` | HIGH |
| `WARNING` | MEDIUM |
| `INFO` | LOW |

---

## 3. Common Vulnerability Types

### 3.1 Hardcoded Secrets and Credentials

**Examples:**
```python
# BAD — hardcoded API key in source
API_KEY = "sk-prod-abc123xyz987"

# BAD — password in database connection string
db = connect("postgresql://admin:SuperSecret99@db.prod.example.com/mydb")
```

**Remediation — use environment variables:**
```python
import os
API_KEY = os.environ["API_KEY"]
db = connect(os.environ["DATABASE_URL"])
```

**Remediation — use a secrets manager:**
```python
import boto3
secret = boto3.client("secretsmanager").get_secret_value(SecretId="prod/api-key")
```

---

### 3.2 Private Keys in Source

**What it looks like:** PEM blocks beginning with `-----BEGIN RSA PRIVATE KEY-----`, SSH private key files (`id_rsa`, `id_ed25519`), or PKCS8 key files.

**Remediation:**
1. Remove the key from the file immediately
2. **Revoke and rotate the key** — assume it is compromised the moment it touches git history
3. Store the new key in a secrets manager (AWS Secrets Manager, HashiCorp Vault, GitHub Secrets)
4. Add the key file pattern to `.gitignore`:
   ```
   id_rsa
   id_ed25519
   *.pem
   *.key
   ```

---

### 3.3 High-Entropy Strings

Strings of 20+ random characters that score above the Shannon entropy threshold.
These are often real secrets but occasionally benign (UUIDs, test fixtures, base64-encoded images).

**If real:** Replace with an environment variable reference.
**If false positive:** Add to `.secrets.baseline` (see Section 5).

### 3.4 Injection Vulnerabilities (semgrep — OWASP A03)

Semgrep detects injection patterns across many languages by understanding code structure:

| Pattern | Languages | Example |
|---------|-----------|---------|
| SQL injection | Python, JS, Go, Java, Ruby, PHP | String-formatted SQL queries with user input |
| Command injection | Python, JS, Go | `os.system(user_input)`, `exec(user_input)` |
| Path traversal | Python, JS, Go, Java | Unsanitised user input in file paths |
| Server-side template injection | Python (Jinja2/Mako), JS | `render_template_string(user_input)` |

### 3.5 Cross-Site Scripting / XSS (semgrep — OWASP A03)

Detects places where user-controlled data is rendered into HTML without escaping:

```javascript
// BAD — user input injected directly into DOM
document.getElementById("output").innerHTML = req.query.name;

// GOOD — use textContent (escapes HTML) or sanitise first
document.getElementById("output").textContent = req.query.name;
```

### 3.6 Insecure Direct Object References / Open Redirects (semgrep — OWASP A01/A10)

Detects redirects built from unvalidated user input:

```python
# BAD — open redirect
return redirect(request.args.get("next"))

# GOOD — validate the URL is on the same host
from urllib.parse import urlparse
next_url = request.args.get("next", "/")
if urlparse(next_url).netloc:
    next_url = "/"
return redirect(next_url)
```

### 3.7 Semgrep False Positives

Semgrep rules can flag code that is safe in context. To suppress a finding:

**Inline — add a `# nosemgrep` comment on the flagged line:**
```python
result = subprocess.run(cmd)  # nosemgrep: dangerous-subprocess-use
```

**Or use the rule ID:**
```python
query = build_query(user_id)  # nosemgrep: python.django.security.injection.tainted-sql-string
```

**Project-wide — create `.semgrepignore`** to exclude paths:
```
tests/
docs/examples/
*.test.js
```

---

## 4. detect-secrets Baseline (`.secrets.baseline`)

The `.secrets.baseline` file is detect-secrets' allowlist for known false positives. It records hashed values of reviewed findings so they are not re-flagged on every scan.

### Generate a baseline for the entire repo

```bash
python -m detect_secrets scan > .secrets.baseline
```

### Add a single false positive via interactive audit

```bash
python -m detect_secrets audit .secrets.baseline
```

The audit prompts for each unreviewed secret — answer `n` (not a secret) to add it to the allowlist.

### Pass the baseline during scanning

```bash
python -m detect_secrets scan --baseline .secrets.baseline [files...]
```

When a `.secrets.baseline` exists in the repo root, `scan-staged.py` will automatically pass `--baseline .secrets.baseline` to detect-secrets (v1.1.0 enhancement — manual flag for now).

### Commit the baseline safely

```bash
git add .secrets.baseline
git commit -m "chore: add detect-secrets baseline"
```

The baseline stores only hashed values — it is safe to commit. Anyone who clones the repo will benefit from the same allowlist.

---

## 5. Handling False Positives

### detect-secrets false positives

Common sources:
- High-entropy test fixtures (mock tokens, UUID-based IDs)
- Base64-encoded images or binary blobs
- Example / placeholder values in documentation files
- Randomly generated test data

**Resolution workflow:**
1. Confirm the string is not a real secret (check the source file manually)
2. Run `python -m detect_secrets audit .secrets.baseline`
3. Mark as `n` (not a real secret) when prompted
4. Commit the updated `.secrets.baseline`

**Alternative — exclude specific files from scanning:**
```bash
python -m detect_secrets scan --exclude-files "tests/fixtures/.*" > .secrets.baseline
```

---

## 6. CI/CD Integration

### GitHub Actions — scan on pull requests and pushes

```yaml
name: Security Scan

on:
  pull_request:
    branches: [main, master]
  push:
    branches: [main, master]

jobs:
  security:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Install security tools
        run: pip install detect-secrets semgrep

      - name: Scan for secrets
        run: |
          if [ -f .secrets.baseline ]; then
            python -m detect_secrets scan --baseline .secrets.baseline
          else
            python -m detect_secrets scan
          fi

      - name: Semgrep OWASP scan
        run: semgrep --config p/owasp-top-ten --json --quiet . | tee semgrep-report.json
        continue-on-error: true

      - name: Upload semgrep report
        uses: actions/upload-artifact@v4
        if: always()
        with:
          name: semgrep-report
          path: semgrep-report.json
```

### pre-commit framework integration (alternative)

If the project already uses the `pre-commit` framework, this is the equivalent configuration:

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/Yelp/detect-secrets
    rev: v1.5.0
    hooks:
      - id: detect-secrets
        args: ["--baseline", ".secrets.baseline"]

  - repo: https://github.com/returntocorp/semgrep
    rev: v1.60.0
    hooks:
      - id: semgrep
        args: ["--config", "p/owasp-top-ten", "--error"]
```

`install-hook.py` is a lightweight alternative that does **not** require the `pre-commit` framework to be installed.

---

## 7. Git Hook Bypass Warning

The git pre-commit hook can be bypassed with:

```bash
git commit --no-verify
```

This completely skips **all** pre-commit hooks, including the security scanner.

**Only use `--no-verify` when:**
- Committing to a throwaway or experimental branch that will never be merged to `main`
- The CI pipeline has its own security scanning that will catch any issues (see Section 7)
- There is a genuine emergency requiring an immediate commit and the flagged items are confirmed false positives

**Never use `--no-verify` on commits destined for `main` or `master`.**

CI/CD scanning (see Section 7) acts as the ultimate backstop when local hooks are bypassed.

---

## 8. Secret Rotation Checklist

If a secret is detected that has **already been committed** — even once — assume it is compromised, because it is visible in git history to anyone with repository access, including historical clones.

**Immediate steps:**
1. **Revoke the credential immediately** — API key, token, password, or certificate
2. **Generate a new credential** — do not reuse the exposed one
3. **Store the new credential** in a secrets manager or environment variable (never in source)
4. **Remove the secret from git history** using one of:
   - [`git filter-repo`](https://github.com/newren/git-filter-repo) (recommended):
     ```bash
     git filter-repo --path-glob "*.env" --invert-paths
     ```
   - [BFG Repo Cleaner](https://rtyley.github.io/bfg-repo-cleaner/):
     ```bash
     bfg --replace-text secrets.txt
     ```
5. **Force-push the rewritten history** — coordinate with your team first
6. **Notify affected parties** if the secret had any external exposure (e.g., public repo, shared access)

> Removing a file from the latest commit with `git rm` is **not sufficient**.
> The secret remains accessible in prior commits visible to anyone who clones or has cloned the repo.
