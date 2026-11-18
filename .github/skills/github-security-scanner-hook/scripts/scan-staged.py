#!/usr/bin/env python3
"""
scan-staged.py — Scan git staged files (or entire repo) for security vulnerabilities.

Uses:
  - detect-secrets  (hardcoded credentials, API keys, tokens — any language, any file type)
  - semgrep         (SQLi, NoSQLi, command injection, XSS, SSTI, prompt injection,
                     unsafe deserialization, SSRF, weak crypto, path traversal)
  - built-in rules  (zero-dependency fallback when detect-secrets or semgrep is absent,
                     plus generic prompt-injection & stealth-Unicode checks)

Usage:
    python scan-staged.py               # scan staged files only (default)
    python scan-staged.py --staged-only # same as default
    python scan-staged.py --full-repo   # scan all tracked files in the repo

Exit codes:
    0 — no findings (clean)
    1 — one or more HIGH severity findings (would block commit)
    2 — only MEDIUM or LOW severity findings (warnings only)
"""

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# Severity mapping for detect-secrets plugin types
# Must stay in sync with references/github-security-scanner-hook-reference.md
# ---------------------------------------------------------------------------
DETECT_SECRETS_SEVERITY: dict[str, str] = {
    # HIGH — direct credential or secret exposure
    "AWS Access Key": "HIGH",
    "AWS Secret Access Key": "HIGH",
    "Artifactory Credentials": "HIGH",
    "Azure Storage Account access key": "HIGH",
    "Cloudant Credentials": "HIGH",
    "Discord Bot Token": "HIGH",
    "GitHub Token": "HIGH",
    "GitLab Token": "HIGH",
    "Hex High Entropy String": "HIGH",
    "IBM Cloud IAM Key": "HIGH",
    "IBM COS HMAC Credentials": "HIGH",
    "JSON Web Token": "HIGH",
    "NPM tokens": "HIGH",
    "OpenAI Token": "HIGH",
    "Private Key": "HIGH",
    "PyPI Token": "HIGH",
    "SendGrid API Key": "HIGH",
    "Slack Token": "HIGH",
    "Slack Webhook": "HIGH",
    "SoftLayer Credentials": "HIGH",
    "Square OAuth Secret": "HIGH",
    "Stripe Access Key": "HIGH",
    "Telegram Bot Token": "HIGH",
    "Twilio API Key": "HIGH",
    # MEDIUM — probable secrets that require human review
    "Base64 High Entropy String": "MEDIUM",
    "Basic Auth Credentials": "MEDIUM",
    "Mailchimp Access Key": "MEDIUM",
    "Public IP (ipv4)": "MEDIUM",
    "Secret Keyword": "MEDIUM",
}

SEMGREP_SEVERITY: dict[str, str] = {
    "ERROR": "HIGH",
    "WARNING": "MEDIUM",
    "INFO": "LOW",
}

# Tuple schema:
# (rule_id, tool_label, severity, file_suffixes, exclude_parts, compiled_regex, detail)
FallbackRule = tuple[str, str, str, tuple[str, ...] | None, tuple[str, ...], re.Pattern[str], str]

_PY_EXT = (".py",)
_JS_EXT = (".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs")
_WEB_EXT = _PY_EXT + _JS_EXT
_GO_EXT = (".go",)
_CS_EXT = (".cs",)
_PS_EXT = (".ps1", ".psm1", ".psd1")

_SCANNER_EXCLUDES = ("github-security-scanner-hook", ".venv", "node_modules", ".git")
_PROMPT_EXCLUDES = ("github-security-scanner-hook", "rag-pipeline", "tests", "test", ".venv", "node_modules", ".git")
_PATH_EXCLUDES = ("github-security-scanner-hook", "tests", "test", ".venv", "node_modules", ".git")

BUILTIN_SECRET_RULES: tuple[FallbackRule, ...] = (
    (
        "AWS Access Key",
        "builtin-secrets",
        "HIGH",
        None,
        _SCANNER_EXCLUDES,
        re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b"),
        "Possible AWS Access Key detected",
    ),
    (
        "GitHub Token",
        "builtin-secrets",
        "HIGH",
        None,
        _SCANNER_EXCLUDES,
        re.compile(r"\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9_]{20,}\b|\bgithub_pat_[A-Za-z0-9_]{22,}\b"),
        "Possible GitHub Token detected",
    ),
    (
        "OpenAI Token",
        "builtin-secrets",
        "HIGH",
        None,
        _SCANNER_EXCLUDES,
        re.compile(r"\bsk-(?:proj-|ant-)?[A-Za-z0-9_-]{20,}\b"),
        "Possible API secret key (sk-...) detected",
    ),
    (
        "Slack Token",
        "builtin-secrets",
        "HIGH",
        None,
        _SCANNER_EXCLUDES,
        re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b"),
        "Possible Slack Token detected",
    ),
    (
        "Private Key",
        "builtin-secrets",
        "HIGH",
        None,
        _SCANNER_EXCLUDES,
        re.compile(r"-----BEGIN (?:RSA |EC |DSA |OPENSSH |PGP )?PRIVATE KEY-----"),
        "Possible Private Key detected",
    ),
    (
        "Basic Auth Credentials",
        "builtin-secrets",
        "MEDIUM",
        None,
        _SCANNER_EXCLUDES,
        re.compile(r"https?://[^:\s/@\"'<>]+:[^:\s/@\"'<>]{3,}@[^\s/\"'<>]+"),
        "Possible Basic Auth credentials embedded in URL detected",
    ),
)

BUILTIN_PROMPT_RULES: tuple[FallbackRule, ...] = (
    (
        "prompt-injection-instruction-override",
        "builtin-rules",
        "HIGH",
        None,
        _PROMPT_EXCLUDES,
        re.compile(
            r"(?i)\b(?:ignore|disregard|forget)\s+(?:all\s+)?"
            r"(?:previous|prior|above|preceding|system|developer)\s+"
            r"(?:instructions|rules|prompts|directions|guidelines|constraints)\b"
        ),
        "Prompt injection risk: instruction-override phrase detected; isolate untrusted text in <sources>.",
    ),
    (
        "prompt-injection-system-override",
        "builtin-rules",
        "HIGH",
        None,
        _PROMPT_EXCLUDES,
        re.compile(
            r"(?i)\b(?:system\s+override|you\s+are\s+now\s+in\s+developer\s+mode|"
            r"enable\s+dan\s+mode|bypass\s+(?:all\s+)?safety\s+(?:filters|guardrails|restrictions)|"
            r"new\s+system\s+prompt\s*:)"
        ),
        "Prompt injection risk: system override or jailbreak directive detected.",
    ),
    (
        "prompt-injection-secret-exfiltration",
        "builtin-rules",
        "HIGH",
        None,
        _PROMPT_EXCLUDES,
        re.compile(
            r"(?i)\b(?:reveal|dump|exfiltrate)\s+(?:the\s+|your\s+|all\s+)?"
            r"(?:system\s+prompt|hidden\s+instructions|api\s+keys?|secrets?|credentials|environment\s+variables)\b"
        ),
        "Prompt injection / exfiltration risk: prompt directive attempting to leak secrets or system prompts.",
    ),
    (
        "prompt-injection-hidden-html-comment",
        "builtin-rules",
        "HIGH",
        None,
        _PROMPT_EXCLUDES,
        re.compile(
            r"(?is)<!--[^>]*?\b(?:ignore\s+(?:all\s+)?(?:previous|prior)|system\s+override|"
            r"disregard\s+(?:all\s+)?(?:previous|prior)|jailbreak|exfiltrate|"
            r"reveal\s+(?:the\s+)?(?:api\s+key|system\s+prompt))\b[^>]*?-->"
        ),
        "Indirect prompt injection risk: hidden adversarial instruction found inside an HTML comment.",
    ),
    (
        "prompt-injection-stealth-unicode",
        "builtin-rules",
        "HIGH",
        None,
        _PROMPT_EXCLUDES,
        re.compile(r"[\u202A-\u202E\u2066-\u2069]"),
        "Stealth Unicode / Trojan Source risk: bidirectional control character detected.",
    ),
    (
        "prompt-injection-python-system-fstring",
        "builtin-rules",
        "MEDIUM",
        _PY_EXT,
        _PROMPT_EXCLUDES,
        re.compile(r"""["']role["']\s*:\s*["']system["']\s*,\s*["']content["']\s*:\s*f["']"""),
        "Prompt injection risk: dynamic data interpolated directly into a system prompt via f-string.",
    ),
    (
        "prompt-injection-js-system-template",
        "builtin-rules",
        "MEDIUM",
        _JS_EXT,
        _PROMPT_EXCLUDES,
        re.compile(r"""role\s*:\s*["']system["']\s*,\s*content\s*:\s*`[^`]*\$\{"""),
        "Prompt injection risk: dynamic data interpolated directly into a system prompt via template literal.",
    ),
)

BUILTIN_CODE_RULES: tuple[FallbackRule, ...] = (
    (
        "sql-injection-python",
        "builtin-rules",
        "HIGH",
        _PY_EXT,
        _SCANNER_EXCLUDES,
        re.compile(r"""\.execute\(\s*(?:f["']|["'][^"']*["']\s*(?:%|\+|\.format\())"""),
        "SQL injection: non-parameterized string formatting in .execute(); use bound parameters.",
    ),
    (
        "sql-injection-js-template",
        "builtin-rules",
        "HIGH",
        _JS_EXT,
        _SCANNER_EXCLUDES,
        re.compile(r"""\.(?:query|execute)\(\s*`[^`]*\$\{"""),
        "SQL injection: template literal interpolation in SQL query; use parameterized queries.",
    ),
    (
        "sql-injection-go-sprintf",
        "builtin-rules",
        "HIGH",
        _GO_EXT,
        _SCANNER_EXCLUDES,
        re.compile(r"""\.(?:Query|QueryRow|Exec)\(\s*fmt\.Sprintf\("""),
        "SQL injection: fmt.Sprintf used in SQL query; use parameterized queries.",
    ),
    (
        "sql-injection-csharp-raw",
        "builtin-rules",
        "HIGH",
        _CS_EXT,
        _SCANNER_EXCLUDES,
        re.compile(r"""\.(?:ExecuteSqlRaw|FromSqlRaw)\(\s*\$["']"""),
        "SQL injection: interpolated string used in EF Core raw SQL; use FromSqlInterpolated/ExecuteSqlInterpolated.",
    ),
    (
        "nosql-injection-js-where",
        "builtin-rules",
        "HIGH",
        _JS_EXT,
        _SCANNER_EXCLUDES,
        re.compile(r"""\.find\(\s*\{[^}]*\$where\s*:"""),
        "NoSQL injection risk: MongoDB $where executes arbitrary JS; replace with structured operators.",
    ),
    (
        "command-injection-python",
        "builtin-rules",
        "HIGH",
        _PY_EXT,
        _SCANNER_EXCLUDES,
        re.compile(
            r"""\b(?:os\.system|os\.popen)\(\s*(?!["'][^"']*["']\s*\))|"""
            r"""\bsubprocess\.(?:run|Popen)\([^)]*shell\s*=\s*True"""
        ),
        "Command injection risk: shell execution or os.system/os.popen with dynamic input; use shell=False.",
    ),
    (
        "command-injection-js",
        "builtin-rules",
        "HIGH",
        _JS_EXT,
        _SCANNER_EXCLUDES,
        re.compile(
            r"""(?:(?<!\.)\b|child_process\.)(?:exec|execSync)\(\s*(?!["'][^"']*["']\s*[,)])|"""
            r"""(?:(?<!\.)\b|child_process\.)spawn\([^)]*shell\s*:\s*true"""
        ),
        "Command injection risk: child_process exec/execSync or spawn with shell: true; use shell: false.",
    ),
    (
        "command-injection-go-exec-sh",
        "builtin-rules",
        "HIGH",
        _GO_EXT,
        _SCANNER_EXCLUDES,
        re.compile(r"""exec\.Command\(\s*"(?:sh|bash)"\s*,\s*"-c"\s*,"""),
        "Command injection risk: exec.Command invoking shell with -c; pass explicit argument list.",
    ),
    (
        "command-injection-powershell-iex",
        "builtin-rules",
        "HIGH",
        _PS_EXT,
        _PATH_EXCLUDES,
        re.compile(r"""(?i)\b(?:Invoke-Expression|iex)\s+\$[a-zA-Z0-9_]+"""),
        "Command injection risk: Invoke-Expression (iex) called with variable input.",
    ),
    (
        "xss-js-dom-sink",
        "builtin-rules",
        "HIGH",
        _JS_EXT,
        _SCANNER_EXCLUDES,
        re.compile(
            r"""\.(?:innerHTML|outerHTML)\s*=\s*(?!["'][^"']*["']\s*;)|"""
            r"""\bdocument\.write\(\s*(?!["'][^"']*["']\s*\))|"""
            r"""\.insertAdjacentHTML\([^,]+,\s*(?!["'][^"']*["']\s*\))"""
        ),
        "XSS risk: unescaped dynamic HTML written to DOM sink; use textContent or DOMPurify.",
    ),
    (
        "xss-react-dangerously-set-inner-html",
        "builtin-rules",
        "MEDIUM",
        _JS_EXT,
        _SCANNER_EXCLUDES,
        re.compile(r"""dangerouslySetInnerHTML\s*=\s*\{\s*\{\s*__html\s*:\s*(?!["'])"""),
        "XSS risk: React dangerouslySetInnerHTML assigned dynamic HTML; sanitise with DOMPurify.",
    ),
    (
        "xss-python-unsafe-markup",
        "builtin-rules",
        "MEDIUM",
        _PY_EXT,
        _SCANNER_EXCLUDES,
        re.compile(r"""\b(?:flask\.Markup|mark_safe)\(\s*(?!["'][^"']*["']\s*\))"""),
        "XSS risk: Markup()/mark_safe() bypasses auto-escaping on dynamic data.",
    ),
    (
        "ssti-python-render-template-string",
        "builtin-rules",
        "HIGH",
        _PY_EXT,
        _SCANNER_EXCLUDES,
        re.compile(r"""\b(?:flask\.)?render_template_string\(\s*(?!["'][^"']*["']\s*[,)])"""),
        "SSTI risk: render_template_string() called with non-literal template; use render_template().",
    ),
    (
        "ssti-python-jinja2-autoescape-false",
        "builtin-rules",
        "MEDIUM",
        _PY_EXT,
        _SCANNER_EXCLUDES,
        re.compile(r"""\bEnvironment\([^)]*autoescape\s*=\s*False"""),
        "XSS / template safety risk: Jinja2 Environment configured with autoescape=False.",
    ),
    (
        "code-injection-eval-exec",
        "builtin-rules",
        "HIGH",
        _WEB_EXT,
        _SCANNER_EXCLUDES,
        re.compile(
            r"""(?<!\.)\b(?:eval|exec)\(\s*(?!["'][^"']*["']\s*\))|"""
            r"""\bnew\s+Function\(\s*(?!["'][^"']*["']\s*[,)])"""
        ),
        "Code injection risk: dynamic eval()/exec()/new Function() execution.",
    ),
    (
        "unsafe-deserialization-python-pickle",
        "builtin-rules",
        "HIGH",
        _PY_EXT,
        _SCANNER_EXCLUDES,
        re.compile(r"""\bpickle\.loads?\("""),
        "Unsafe deserialization: pickle.load()/loads() executes arbitrary code on untrusted input.",
    ),
    (
        "unsafe-deserialization-python-yaml",
        "builtin-rules",
        "HIGH",
        _PY_EXT,
        _SCANNER_EXCLUDES,
        re.compile(r"""\byaml\.unsafe_load\(|\byaml\.load\((?![^)]*SafeLoader)"""),
        "Unsafe YAML deserialization: use yaml.safe_load() instead of yaml.load()/unsafe_load().",
    ),
    (
        "path-traversal-fs",
        "builtin-rules",
        "MEDIUM",
        _WEB_EXT,
        _SCANNER_EXCLUDES,
        re.compile(
            r"""\bopen\(\s*os\.path\.join\((?!\s*["'][^"']*["']\s*,\s*["'])|"""
            r"""\bfs\.(?:readFile|readFileSync|writeFile|writeFileSync)\(\s*(?!["'])"""
        ),
        "Path traversal risk: filesystem operation on dynamic path; validate resolved base directory.",
    ),
    (
        "destructive-fs-deletion",
        "builtin-rules",
        "MEDIUM",
        _WEB_EXT,
        _SCANNER_EXCLUDES,
        re.compile(
            r"""\bshutil\.rmtree\(\s*(?!["'][^"']*["']\s*[,)])|"""
            r"""\bfs\.(?:promises\.)?rm(?:Sync)?\([^)]*recursive\s*:\s*true|"""
            r"""\bfs\.rmdirSync\("""
        ),
        "Destructive filesystem deletion: recursive delete on dynamic path; constrain allowed boundaries.",
    ),
    (
        "ssrf-python-requests",
        "builtin-rules",
        "MEDIUM",
        _PY_EXT,
        _SCANNER_EXCLUDES,
        re.compile(r"""\b(?:requests\.(?:get|post)|urllib\.request\.urlopen)\(\s*(?!["'])"""),
        "SSRF risk: outbound HTTP request to non-literal URL; validate scheme and host allowlist.",
    ),
    (
        "open-redirect",
        "builtin-rules",
        "MEDIUM",
        _WEB_EXT,
        _SCANNER_EXCLUDES,
        re.compile(
            r"""\bflask\.redirect\(\s*request\.(?:args|form)\.get\(|"""
            r"""\bres\.redirect\(\s*(?!\d{3}\s*,\s*["'])(?!["'])"""
        ),
        "Open redirect risk: redirect target is derived from dynamic/request input.",
    ),
    (
        "weak-crypto-md5-sha1",
        "builtin-rules",
        "MEDIUM",
        _WEB_EXT,
        _SCANNER_EXCLUDES,
        re.compile(r"""\bhashlib\.(?:md5|sha1)\(|\bcrypto\.createHash\(\s*["'](?:md5|sha1)["']\s*\)"""),
        "Weak cryptography: MD5/SHA-1 are collision-prone; use SHA-256 or argon2/scrypt.",
    ),
    (
        "tls-verification-disabled",
        "builtin-rules",
        "HIGH",
        _WEB_EXT,
        _SCANNER_EXCLUDES,
        re.compile(
            r"""\b(?:requests\.(?:get|post)|httpx\.Client)\([^)]*verify\s*=\s*False|"""
            r"""rejectUnauthorized\s*:\s*false|NODE_TLS_REJECT_UNAUTHORIZED\s*=\s*["']0["']"""
        ),
        "TLS verification disabled: disabling certificate validation exposes traffic to MITM.",
    ),
    (
        "secret-leak-env-inheritance",
        "builtin-rules",
        "MEDIUM",
        _WEB_EXT,
        _SCANNER_EXCLUDES,
        re.compile(
            r"""\b(?:subprocess\.(?:run|Popen)|(?:child_process\.)?(?:spawn|exec))\("""
            r"""[^)]*(?:env\s*=\s*os\.environ|env\s*:\s*process\.env)"""
        ),
        "Sensitive credential leak risk: full host environment inherited by child process.",
    ),
    (
        "hardcoded-local-user-path",
        "builtin-rules",
        "MEDIUM",
        None,
        _PATH_EXCLUDES,
        re.compile(r"""(?i)(?:[a-zA-Z]:[\\/]|(?<=[ "'\\/`]))(?:Users|home)[\\/][a-zA-Z0-9_.-]+[\\/]"""),
        "Hardcoded local user directory path detected; replace with relative or placeholder paths.",
    ),
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def resolve_python() -> Path:
    """Return the .venv Python interpreter for this platform, falling back to sys.executable."""
    candidates = [
        Path(".venv") / "Scripts" / "python.exe",
        Path(".venv") / "Scripts" / "python",
        Path(".venv") / "bin" / "python",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return Path(sys.executable)


def run(cmd: list[str]) -> subprocess.CompletedProcess:
    """Run a subprocess and return the result. Never raises on non-zero exit."""
    return subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")


def ensure_in_git_repo() -> None:
    """Exit with a clear message if not inside a git repository."""
    result = run(["git", "rev-parse", "--git-dir"])
    if result.returncode != 0:
        print("Error: not inside a git repository.", file=sys.stderr)
        sys.exit(1)


def get_git_files(full_repo: bool) -> list[str]:
    """Return staged files (default) or all tracked files when full_repo is True."""
    cmd = (
        ["git", "ls-files"]
        if full_repo
        else ["git", "diff", "--cached", "--name-only", "--diff-filter=ACMR"]
    )
    result = run(cmd)
    if result.returncode != 0:
        print("Error: could not list files from git.", file=sys.stderr)
        print(result.stderr, file=sys.stderr)
        sys.exit(1)
    return [line for line in result.stdout.splitlines() if line.strip()]


def check_tool(python: Path, package_name: str) -> bool:
    """Return True if the pip package is installed in the current environment."""
    return run([str(python), "-m", "pip", "show", package_name]).returncode == 0


def resolve_semgrep(python: Path | None = None) -> Path | None:
    """Return the semgrep binary from .venv, the active Python Scripts dir, or PATH."""
    candidates = [
        Path(".venv") / "Scripts" / "semgrep.exe",
        Path(".venv") / "Scripts" / "semgrep",
        Path(".venv") / "bin" / "semgrep",
    ]
    if python is not None:
        candidates.extend([
            python.parent / "semgrep.exe",
            python.parent / "semgrep",
        ])
    for candidate in candidates:
        if candidate.exists():
            return candidate
    which_semgrep = shutil.which("semgrep")
    return Path(which_semgrep) if which_semgrep else None


# ---------------------------------------------------------------------------
# detect-secrets scanning
# ---------------------------------------------------------------------------

def run_detect_secrets(python: Path, files: list[str]) -> list[dict]:
    """Run detect-secrets scan on the given files and return finding dicts."""
    if not files:
        return []

    cmd = [str(python), "-m", "detect_secrets", "scan"]
    if Path(".secrets.baseline").exists():
        cmd += ["--baseline", ".secrets.baseline"]
    cmd += files
    result = run(cmd)

    if result.returncode not in (0, 1):
        print(f"Warning: detect-secrets exited with code {result.returncode}", file=sys.stderr)
        if result.stderr:
            print(result.stderr, file=sys.stderr)
        return []

    if not result.stdout.strip():
        return []

    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        print(f"Warning: could not parse detect-secrets output: {exc}", file=sys.stderr)
        return []

    findings = []
    for filepath, secret_list in data.get("results", {}).items():
        for secret in secret_list:
            plugin_name = secret.get("type", "Unknown")
            severity = DETECT_SECRETS_SEVERITY.get(plugin_name, "MEDIUM")
            readable_type = plugin_name.replace("KeyDetector", " key").replace("Detector", "").strip()
            findings.append({
                "file": filepath.replace("\\", "/"),
                "line": secret.get("line_number", 0),
                "type": plugin_name,
                "tool": "detect-secrets",
                "severity": severity,
                "detail": f"Possible {readable_type} detected",
            })
    return findings


# ---------------------------------------------------------------------------
# semgrep scanning
# ---------------------------------------------------------------------------

def run_semgrep(semgrep: Path, files: list[str]) -> list[dict]:
    """Run semgrep with the bundled rules/security.yml ruleset on the given files."""
    if not files:
        return []

    rules_file = Path(__file__).resolve().parent.parent / "rules" / "security.yml"
    if not rules_file.exists():
        print(f"Warning: bundled semgrep rules not found at {rules_file} — skipping semgrep scan.", file=sys.stderr)
        return []

    cmd = [str(semgrep), "--config", str(rules_file), "--json", "--quiet", "--", *files]
    result = run(cmd)

    if result.returncode not in (0, 1):
        print(f"Warning: semgrep exited with code {result.returncode}", file=sys.stderr)
        if result.stderr:
            print(result.stderr, file=sys.stderr)
        return []

    if not result.stdout.strip():
        return []

    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        print(f"Warning: could not parse semgrep output: {exc}", file=sys.stderr)
        return []

    findings = []
    for item in data.get("results", []):
        extra = item.get("extra", {})
        severity = SEMGREP_SEVERITY.get(extra.get("severity", "WARNING").upper(), "MEDIUM")
        check_id = item.get("check_id", "unknown")
        if "rules." in check_id:
            check_id = check_id.split("rules.")[-1]
        findings.append({
            "file": item.get("path", "unknown").replace("\\", "/"),
            "line": item.get("start", {}).get("line", 0),
            "type": check_id,
            "tool": "semgrep",
            "severity": severity,
            "detail": extra.get("message", "").strip(),
        })
    return findings


# ---------------------------------------------------------------------------
# Built-in fallback & prompt-injection scanning
# ---------------------------------------------------------------------------

def _scan_file_with_rules(filepath: str, rules: tuple[FallbackRule, ...]) -> list[dict]:
    """Apply a tuple of compiled regex rules against a single text file."""
    path_obj = Path(filepath)
    try:
        raw = path_obj.read_bytes()
    except OSError:
        return []
    if b"\x00" in raw[:4096]:
        return []

    text = raw.decode("utf-8", errors="replace")
    lines = text.splitlines()
    norm_path = filepath.replace("\\", "/")
    suffix = path_obj.suffix.lower()
    parts_lower = {p.lower() for p in Path(norm_path).parts}

    file_findings: list[dict] = []
    for rule_id, tool_label, severity, suffixes, excludes, pattern, detail in rules:
        if suffixes is not None and suffix not in suffixes:
            continue
        if excludes and any(ex.lower() in parts_lower for ex in excludes):
            continue
        for match in pattern.finditer(text):
            line_num = text.count("\n", 0, match.start()) + 1
            line_text = lines[line_num - 1] if 0 < line_num <= len(lines) else ""
            if "nosemgrep" in line_text or "allowlist secret" in line_text:
                continue
            file_findings.append({
                "file": norm_path,
                "line": line_num,
                "type": rule_id,
                "tool": tool_label,
                "severity": severity,
                "detail": detail,
            })
    return file_findings


def run_builtin_fallback(files: list[str], rules: tuple[FallbackRule, ...]) -> list[dict]:
    """Run declarative built-in regex rules across files without external dependencies."""
    findings: list[dict] = []
    for filepath in files:
        findings.extend(_scan_file_with_rules(filepath, rules))
    return findings


def deduplicate_findings(findings: list[dict]) -> list[dict]:
    """Deduplicate findings by (file, line, type) while preserving order."""
    seen: set[tuple[str, int, str]] = set()
    unique: list[dict] = []
    for item in findings:
        key = (item.get("file", ""), int(item.get("line", 0)), item.get("type", ""))
        if key not in seen:
            seen.add(key)
            unique.append(item)
    return unique


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Scan staged (or all tracked) files for security vulnerabilities."
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--staged-only", action="store_true", help="Scan only staged files (default behaviour)")
    mode.add_argument("--full-repo", action="store_true", help="Scan all files tracked by git")
    args = parser.parse_args()

    ensure_in_git_repo()
    python = resolve_python()
    files = get_git_files(args.full_repo)

    if not files:
        print(json.dumps({
            "scanned_files": [],
            "findings": [],
            "summary": {"total": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0},
        }, indent=2))
        sys.exit(0)

    existing_files = [f for f in files if Path(f).exists()]
    findings: list[dict] = []

    if check_tool(python, "detect-secrets"):
        findings.extend(run_detect_secrets(python, existing_files))
    else:
        print(
            "Info: detect-secrets is not installed — using built-in secret scanner fallback.\n"
            f"Install full scanner with: {python} -m pip install detect-secrets",
            file=sys.stderr,
        )
        findings.extend(run_builtin_fallback(existing_files, BUILTIN_SECRET_RULES))

    semgrep = resolve_semgrep(python)
    if semgrep:
        findings.extend(run_semgrep(semgrep, existing_files))
        findings.extend(run_builtin_fallback(existing_files, BUILTIN_PROMPT_RULES))
    else:
        print(
            "Info: semgrep is not installed — using built-in security & prompt-injection fallback.\n"
            f"Install full AST scanner with: {python} -m pip install semgrep",
            file=sys.stderr,
        )
        findings.extend(run_builtin_fallback(existing_files, BUILTIN_PROMPT_RULES + BUILTIN_CODE_RULES))

    findings = deduplicate_findings(findings)
    summary: dict[str, int] = {"total": len(findings), "HIGH": 0, "MEDIUM": 0, "LOW": 0}
    for finding in findings:
        sev = finding.get("severity", "LOW")
        if sev in summary:
            summary[sev] += 1

    print(json.dumps({
        "scanned_files": existing_files,
        "findings": findings,
        "summary": summary,
    }, indent=2))

    if summary["HIGH"] > 0:
        sys.exit(1)
    if summary["MEDIUM"] > 0 or summary["LOW"] > 0:
        sys.exit(2)
    sys.exit(0)


if __name__ == "__main__":
    main()
