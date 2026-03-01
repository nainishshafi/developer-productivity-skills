#!/usr/bin/env python3
"""
scan-staged.py — Scan git staged files (or entire repo) for security vulnerabilities.

Uses:
  - detect-secrets  (hardcoded credentials, API keys, tokens — any language, any file type)
  - semgrep         (injection flaws, XSS, path traversal, insecure patterns — any language)

Usage:
    python scan-staged.py               # scan staged files only (default)
    python scan-staged.py --staged-only # same as default
    python scan-staged.py --full-repo   # scan all tracked files in the repo

Output (JSON to stdout):
    {
        "scanned_files": ["path/to/file.py", ...],
        "findings": [
            {
                "file": "path/to/file.py",
                "line": 42,
                "type": "AWSKeyDetector",
                "tool": "detect-secrets",
                "severity": "HIGH",
                "detail": "Possible AWS key detected"
            },
            ...
        ],
        "summary": {
            "total": 3,
            "HIGH": 1,
            "MEDIUM": 1,
            "LOW": 1
        }
    }

Exit codes:
    0 — no findings (clean)
    1 — one or more HIGH severity findings (would block commit)
    2 — only MEDIUM or LOW severity findings (warnings only)
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# Severity mapping for detect-secrets plugin types
# Must stay in sync with references/github-security-scanner-hook-reference.md
# ---------------------------------------------------------------------------
DETECT_SECRETS_SEVERITY: dict[str, str] = {
    # HIGH — direct credential or secret exposure
    # Keys are the secret_type display names returned by detect-secrets 1.x JSON output
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


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def resolve_python() -> Path:
    """Return the .venv Python interpreter for this platform, falling back to sys.executable."""
    candidates = [
        Path(".venv") / "Scripts" / "python",  # Windows
        Path(".venv") / "bin" / "python",       # Unix / macOS
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return Path(sys.executable)


def run(cmd: list[str]) -> subprocess.CompletedProcess:
    """Run a subprocess and return the result. Never raises on non-zero exit."""
    return subprocess.run(cmd, capture_output=True, text=True)


def ensure_in_git_repo() -> None:
    """Exit with a clear message if not inside a git repository."""
    result = run(["git", "rev-parse", "--git-dir"])
    if result.returncode != 0:
        print("Error: not inside a git repository.", file=sys.stderr)
        sys.exit(1)


def get_staged_files() -> list[str]:
    """Return the list of staged file paths. Excludes deleted files (--diff-filter=ACMR)."""
    result = run(["git", "diff", "--cached", "--name-only", "--diff-filter=ACMR"])
    if result.returncode != 0:
        print("Error: could not read staged files from git.", file=sys.stderr)
        print(result.stderr, file=sys.stderr)
        sys.exit(1)
    return [line for line in result.stdout.splitlines() if line.strip()]


def get_all_tracked_files() -> list[str]:
    """Return all files tracked by git (for --full-repo mode)."""
    result = run(["git", "ls-files"])
    if result.returncode != 0:
        print("Error: could not list tracked files from git.", file=sys.stderr)
        print(result.stderr, file=sys.stderr)
        sys.exit(1)
    return [line for line in result.stdout.splitlines() if line.strip()]


def check_tool(python: Path, package_name: str) -> bool:
    """Return True if the pip package is installed in the current environment."""
    result = run([str(python), "-m", "pip", "show", package_name])
    return result.returncode == 0


def resolve_semgrep() -> Path | None:
    """Return the semgrep binary from the .venv, or None if not installed."""
    candidates = [
        Path(".venv") / "Scripts" / "semgrep.exe",  # Windows (pip installs .exe)
        Path(".venv") / "Scripts" / "semgrep",       # Windows fallback
        Path(".venv") / "bin" / "semgrep",            # Unix / macOS
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


# ---------------------------------------------------------------------------
# detect-secrets scanning
# ---------------------------------------------------------------------------

def run_detect_secrets(python: Path, files: list[str]) -> list[dict]:
    """
    Run detect-secrets scan on the given files.
    Returns a flat list of finding dicts.
    """
    if not files:
        return []

    cmd = [str(python), "-m", "detect_secrets", "scan"]
    if Path(".secrets.baseline").exists():
        cmd += ["--baseline", ".secrets.baseline"]
    cmd += files
    result = run(cmd)

    if result.returncode not in (0, 1):
        print(
            f"Warning: detect-secrets exited with code {result.returncode}",
            file=sys.stderr,
        )
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
            readable_type = (
                plugin_name
                .replace("Detector", "")
                .replace("KeyDetector", " key")
                .strip()
            )
            findings.append({
                "file": filepath,
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

# Semgrep severity → our severity
SEMGREP_SEVERITY: dict[str, str] = {
    "ERROR": "HIGH",
    "WARNING": "MEDIUM",
    "INFO": "LOW",
}


def run_semgrep(semgrep: Path, files: list[str]) -> list[dict]:
    """
    Run semgrep with the bundled security ruleset on the given files.
    Returns a flat list of finding dicts.

    Uses rules/security.yml (sibling of this script's parent directory) —
    no network access or login required.

    Semgrep exit codes: 0 = clean, 1 = findings, 2 = error.
    Semgrep severity: ERROR → HIGH, WARNING → MEDIUM, INFO → LOW.
    """
    if not files:
        return []

    # Resolve bundled rules relative to this script
    rules_file = Path(__file__).resolve().parent.parent / "rules" / "security.yml"
    if not rules_file.exists():
        print(
            f"Warning: bundled semgrep rules not found at {rules_file} — skipping semgrep scan.",
            file=sys.stderr,
        )
        return []

    cmd = [
        str(semgrep),
        "--config", str(rules_file),
        "--json",
        "--quiet",
        "--",
        *files,
    ]
    result = run(cmd)

    if result.returncode not in (0, 1):
        print(
            f"Warning: semgrep exited with code {result.returncode}",
            file=sys.stderr,
        )
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
    for result_item in data.get("results", []):
        extra = result_item.get("extra", {})
        raw_severity = extra.get("severity", "WARNING").upper()
        severity = SEMGREP_SEVERITY.get(raw_severity, "MEDIUM")
        # Trim full path prefix from check_id (e.g. "a.b.rules.sql-injection-python")
        # down to just the rule name after "rules."
        check_id = result_item.get("check_id", "unknown")
        if "rules." in check_id:
            check_id = check_id.split("rules.")[-1]
        findings.append({
            "file": result_item.get("path", "unknown"),
            "line": result_item.get("start", {}).get("line", 0),
            "type": check_id,
            "tool": "semgrep",
            "severity": severity,
            "detail": extra.get("message", "").strip(),
        })
    return findings


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Scan staged (or all tracked) files for security vulnerabilities."
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--staged-only",
        action="store_true",
        help="Scan only staged files (default behaviour)",
    )
    mode.add_argument(
        "--full-repo",
        action="store_true",
        help="Scan all files tracked by git",
    )
    args = parser.parse_args()

    ensure_in_git_repo()

    python = resolve_python()

    # Collect target files
    if args.full_repo:
        files = get_all_tracked_files()
    else:
        files = get_staged_files()

    # No files to scan — exit clean
    if not files:
        output = {
            "scanned_files": [],
            "findings": [],
            "summary": {"total": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0},
        }
        print(json.dumps(output, indent=2))
        sys.exit(0)

    # Filter to files that actually exist on disk (deleted staged files have no content)
    existing_files = [f for f in files if Path(f).exists()]

    # Require detect-secrets
    if not check_tool(python, "detect-secrets"):
        print(
            "Error: detect-secrets is not installed.\n"
            f"Install with: {python} -m pip install detect-secrets",
            file=sys.stderr,
        )
        sys.exit(1)

    # Run scans
    findings: list[dict] = []
    findings.extend(run_detect_secrets(python, existing_files))

    semgrep = resolve_semgrep()
    if semgrep:
        findings.extend(run_semgrep(semgrep, existing_files))
    else:
        print(
            "Info: semgrep is not installed — skipping injection/OWASP checks.\n"
            f"Install with: {python} -m pip install semgrep",
            file=sys.stderr,
        )

    # Tally severity counts
    summary: dict[str, int] = {"total": len(findings), "HIGH": 0, "MEDIUM": 0, "LOW": 0}
    for finding in findings:
        sev = finding.get("severity", "LOW")
        if sev in summary:
            summary[sev] += 1

    # Emit JSON to stdout
    output = {
        "scanned_files": existing_files,
        "findings": findings,
        "summary": summary,
    }
    print(json.dumps(output, indent=2))

    # Exit code drives hook and skill workflow behaviour
    if summary["HIGH"] > 0:
        sys.exit(1)
    elif summary["MEDIUM"] > 0 or summary["LOW"] > 0:
        sys.exit(2)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
