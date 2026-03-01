#!/usr/bin/env python3
"""
find-readmes.py

Locates all README files and SKILL.md files in the current repository and
prepares a timestamped output file path for the scan-repo-readme skill.

Output (stdout):
  Line 1:  Output file path  (e.g. .scan-readme-results/readme-scan-20240315-143022.md)
  Line 2+: Absolute path of each README or SKILL.md file found, one per line

Usage:
  .venv/Scripts/python .github/skills/scan-repo-readme/scripts/find-readmes.py   # Windows
  .venv/bin/python     .github/skills/scan-repo-readme/scripts/find-readmes.py   # Unix
  python3              .github/skills/scan-repo-readme/scripts/find-readmes.py   # fallback
"""

import os
import sys
from datetime import datetime
from pathlib import Path

# README filenames to match (case-sensitive check first, then case-insensitive fallback)
README_NAMES = {
    "readme.md",
    "readme.rst",
    "readme.txt",
    "readme.adoc",
    "readme.org",
    "readme",
}

# Directories to skip entirely
SKIP_DIRS = {
    ".git",
    ".github",
    "node_modules",
    "__pycache__",
    ".venv",
    "venv",
    ".env",
    "dist",
    "build",
    ".next",
    ".nuxt",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".tox",
    "coverage",
    ".coverage",
}

OUTPUT_DIR = ".scan-readme-results"


def resolve_python() -> str:
    """Return the best available Python interpreter path."""
    candidates = [
        Path(".venv") / "Scripts" / "python",  # Windows venv
        Path(".venv") / "bin" / "python",  # Unix venv
    ]
    for candidate in candidates:
        if candidate.exists():
            return str(candidate)
    return "python3"


def find_readmes(root: Path) -> list[Path]:
    """Walk the repo and return paths of all README files."""
    found: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(root):
        # Prune directories in-place to skip noise
        dirnames[:] = [
            d for d in dirnames if d not in SKIP_DIRS and not d.startswith(".")
        ]
        for fname in filenames:
            if fname.lower() in README_NAMES:
                found.append(Path(dirpath) / fname)
    return sorted(found)


def find_skills(root: Path) -> list[Path]:
    """Find all SKILL.md files under .github/skills/."""
    if ".github" in SKIP_DIRS:
        return []
    skills_dir = root / ".github" / "skills"
    if not skills_dir.is_dir():
        return []
    return sorted(skills_dir.glob("*/SKILL.md"))


def main() -> None:
    root = Path.cwd()

    # Create output directory and build timestamped output path
    output_dir = root / OUTPUT_DIR
    output_dir.mkdir(exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    output_path = output_dir / f"readme-scan-{ts}.md"

    # Print output path as line 1
    print(output_path)

    # Find and print README file paths
    readmes = find_readmes(root)
    for readme in readmes:
        print(readme)

    # Find and print SKILL.md file paths
    skills = find_skills(root)
    for skill in skills:
        print(skill)

    if not readmes and not skills:
        # Print a warning to stderr so it doesn't pollute the stdout protocol
        print("Warning: No README or SKILL.md files found in the repository.", file=sys.stderr)


if __name__ == "__main__":
    main()
