#!/usr/bin/env python3
"""
install-hook.py — Install (or extend) a git pre-commit hook that runs scan-staged.py.

Behaviour:
  1. Verifies the current directory is inside a git repo (.git/ directory present).
  2. Resolves the absolute path to scan-staged.py (sibling of this script).
  3. Resolves the correct Python interpreter (.venv or sys.executable).
  4. If .git/hooks/pre-commit does not exist: creates it fresh.
  5. If pre-commit exists and already contains our stanza: prints "already installed".
  6. If pre-commit exists without our stanza: shows contents, offers Append / Overwrite / Skip.
  7. Makes the hook executable (chmod +x — silent no-op on Windows).

Usage:
    python install-hook.py          # interactive: prompts if hook already exists
    python install-hook.py --force  # overwrite existing hook without prompting
    python install-hook.py --append # always append (no prompt)
"""

import argparse
import os
import stat
import sys
from pathlib import Path


HOOK_SHEBANG = "#!/usr/bin/env bash\n"

# Marker used to detect whether our stanza is already present
HOOK_MARKER = "github-security-scanner-hook"


def build_hook_stanza(scan_script: str, python_path: str) -> str:
    """
    Return the shell stanza added to .git/hooks/pre-commit.

    Paths are embedded as absolute values at install time so the hook works
    regardless of the shell's PATH. Forward slashes are used throughout so
    Git Bash on Windows can read the paths correctly.
    """
    # Normalise to forward slashes for Git Bash on Windows
    scan_script_fwd = scan_script.replace("\\", "/")
    python_path_fwd = python_path.replace("\\", "/")

    return f"""
# --- {HOOK_MARKER} (installed by install-hook.py) ---
SCAN_SCRIPT="{scan_script_fwd}"
SCAN_PYTHON="{python_path_fwd}"

if [ -f "$SCAN_SCRIPT" ]; then
    "$SCAN_PYTHON" "$SCAN_SCRIPT"
    SCAN_EXIT=$?
    if [ "$SCAN_EXIT" -eq 1 ]; then
        echo ""
        echo "COMMIT BLOCKED: HIGH severity security findings detected."
        echo "Fix the issues above, then re-stage and commit."
        echo "Emergency bypass (use with caution): git commit --no-verify"
        echo "---------------------------------------------------------------"
        exit 1
    elif [ "$SCAN_EXIT" -eq 2 ]; then
        echo ""
        echo "WARNING: MEDIUM/LOW severity security findings detected."
        echo "Review the findings above. Press Enter to commit anyway, or Ctrl+C to abort."
        read -r _CONFIRM || true   # non-interactive (CI): auto-continue
    fi
fi
# --- end {HOOK_MARKER} ---
"""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def find_git_dir() -> Path:
    """Walk up from cwd to find the .git directory. Exit if not in a git repo."""
    current = Path.cwd()
    for directory in [current, *current.parents]:
        git_dir = directory / ".git"
        if git_dir.is_dir():
            return git_dir
    print("Error: not inside a git repository (.git/ not found).", file=sys.stderr)
    sys.exit(1)


def resolve_python() -> str:
    """Return the .venv Python interpreter as a string path."""
    candidates = [
        Path.cwd() / ".venv" / "Scripts" / "python",  # Windows
        Path.cwd() / ".venv" / "bin" / "python",       # Unix / macOS
    ]
    for candidate in candidates:
        if candidate.exists():
            return str(candidate)
    return sys.executable  # fallback to the running interpreter


def resolve_scan_script() -> str:
    """
    Find scan-staged.py relative to this installer script.
    Both scripts live in the same scripts/ directory.
    """
    scripts_dir = Path(__file__).resolve().parent
    scan_script = scripts_dir / "scan-staged.py"
    if not scan_script.exists():
        print(
            f"Error: scan-staged.py not found at expected path:\n  {scan_script}",
            file=sys.stderr,
        )
        sys.exit(1)
    return str(scan_script)


def make_executable(path: Path) -> None:
    """Add executable bits to a file. Silent no-op on Windows."""
    try:
        mode = path.stat().st_mode
        path.chmod(mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    except (OSError, NotImplementedError):
        pass  # Windows: git runs hooks via its bundled bash regardless


def write_hook(path: Path, content: str) -> None:
    """Write hook content to path with Unix line endings."""
    path.write_text(content, encoding="utf-8", newline="\n")
    make_executable(path)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Install or extend the git pre-commit hook for security scanning."
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--force",
        action="store_true",
        help="Overwrite an existing pre-commit hook without prompting",
    )
    group.add_argument(
        "--append",
        action="store_true",
        help="Append the security scanner to an existing hook without prompting",
    )
    args = parser.parse_args()

    git_dir = find_git_dir()
    hooks_dir = git_dir / "hooks"
    hooks_dir.mkdir(exist_ok=True)

    hook_path = hooks_dir / "pre-commit"
    scan_script = resolve_scan_script()
    python_path = resolve_python()
    stanza = build_hook_stanza(scan_script, python_path)

    # -----------------------------------------------------------------------
    # Case 1: hook does not exist — create fresh
    # -----------------------------------------------------------------------
    if not hook_path.exists():
        write_hook(hook_path, HOOK_SHEBANG + stanza)
        print(f"Installed pre-commit hook at:\n  {hook_path}")
        print("Every future commit will be scanned for security issues.")
        return

    # -----------------------------------------------------------------------
    # Case 2: hook exists
    # -----------------------------------------------------------------------
    existing = hook_path.read_text(encoding="utf-8")

    # Guard: our stanza is already present — nothing to do
    if HOOK_MARKER in existing:
        print(
            f"Notice: the security scanner is already installed in:\n  {hook_path}\n"
            "Nothing changed."
        )
        return

    # Show the existing hook so the user can make an informed choice
    print(f"Warning: a pre-commit hook already exists at:\n  {hook_path}")
    print("\n--- existing hook content ---")
    preview = existing[:600] + ("\n...(truncated)" if len(existing) > 600 else "")
    print(preview)
    print("----------------------------\n")

    if args.force:
        action = "overwrite"
    elif args.append:
        action = "append"
    else:
        print("Options:")
        print("  [A] Append the security scanner to the existing hook (recommended)")
        print("  [O] Overwrite the existing hook entirely")
        print("  [S] Skip — do not modify the hook")
        try:
            choice = input("Choice [A/o/s]: ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print()
            choice = "s"

        if choice in ("o", "overwrite"):
            action = "overwrite"
        elif choice in ("s", "skip"):
            print("Skipped. Hook not modified.")
            return
        else:
            # Default (Enter or 'a') → append
            action = "append"

    if action == "overwrite":
        write_hook(hook_path, HOOK_SHEBANG + stanza)
        print(f"Overwrote pre-commit hook at:\n  {hook_path}")
    else:
        new_content = existing.rstrip("\n") + "\n" + stanza
        write_hook(hook_path, new_content)
        print(f"Appended security scanner to existing hook at:\n  {hook_path}")

    print("Every future commit will be scanned for security issues.")
    print("Emergency bypass: git commit --no-verify  (see reference for caveats)")


if __name__ == "__main__":
    main()
