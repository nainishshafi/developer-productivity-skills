#!/usr/bin/env python3
"""
scaffold-skill.py — Create boilerplate directory structure for a new Claude Code skill.

Usage:
    python scaffold-skill.py <skill-name> [base-path]

Arguments:
    skill-name   Required. Lowercase kebab-case name for the skill (e.g., lint-python).
    base-path    Optional. Root directory where skills live. Default: .github/skills

Output:
    Prints each created file path to stdout, one per line.
    Errors are printed to stderr and exit with code 1.
"""

import os
import re
import sys


SKILL_NAME_PATTERN = re.compile(r"^[a-z][a-z0-9-]+$")

SKILL_MD_TEMPLATE = """\
---
name: {skill_name}
description: TODO — describe when and why to use this skill, with trigger phrases.
version: 1.0.0
---

# {skill_title}

TODO — one-line summary.

## When to Use This Skill

- TODO

## Core Concepts

### Concept 1

TODO

## Implementation Patterns

### Pattern 1

TODO

## Best Practices

- TODO

## Common Pitfalls

### Pitfall 1
**Problem:** TODO
**Solution:** TODO

## Resources

- TODO
"""

REFERENCE_MD_TEMPLATE = """\
# {skill_title} Reference

TODO — supporting reference material for the {skill_name} skill.

## Section 1

TODO

## Section 2

TODO
"""


def skill_title(skill_name: str) -> str:
    """Convert kebab-case skill name to Title Case for display."""
    return " ".join(word.capitalize() for word in skill_name.split("-"))


def validate_skill_name(name: str) -> None:
    """Validate skill name against naming conventions. Exits on failure."""
    if not SKILL_NAME_PATTERN.match(name):
        print(
            f"Error: '{name}' is not a valid skill name.\n"
            "Skill names must:\n"
            "  - Start with a lowercase letter\n"
            "  - Contain only lowercase letters, digits, and hyphens\n"
            "  - Be at least 2 characters long\n"
            "Example: lint-python, deploy-staging, sync-github-forks",
            file=sys.stderr,
        )
        sys.exit(1)

    if len(name) > 64:
        print(
            f"Error: skill name '{name}' is {len(name)} characters long. "
            "Maximum allowed is 64 characters.",
            file=sys.stderr,
        )
        sys.exit(1)


def check_not_exists(skill_dir: str, skill_name: str) -> None:
    """Exit with a warning if the skill directory already exists."""
    if os.path.exists(skill_dir):
        print(
            f"Warning: skill directory already exists at '{skill_dir}'.\n"
            f"Refusing to overwrite existing skill '{skill_name}'.\n"
            "If you want to recreate it, remove the directory first.",
            file=sys.stderr,
        )
        sys.exit(1)


def write_file(path: str, content: str) -> None:
    """Write content to path, creating parent directories as needed."""
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(content)
    except OSError as exc:
        print(f"Error: could not write '{path}': {exc}", file=sys.stderr)
        sys.exit(1)


def touch_file(path: str) -> None:
    """Create an empty file (and its parent directories) if it does not exist."""
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "a", encoding="utf-8"):
            pass
    except OSError as exc:
        print(f"Error: could not create '{path}': {exc}", file=sys.stderr)
        sys.exit(1)


def main() -> None:
    if len(sys.argv) < 2:
        print(
            "Usage: scaffold-skill.py <skill-name> [base-path]\n"
            "\n"
            "Arguments:\n"
            "  skill-name   Lowercase kebab-case name (e.g., lint-python)\n"
            "  base-path    Root skills directory (default: .github/skills)",
            file=sys.stderr,
        )
        sys.exit(1)

    skill_name = sys.argv[1]
    base_path = sys.argv[2] if len(sys.argv) >= 3 else ".github/skills"

    # Validate inputs
    validate_skill_name(skill_name)

    skill_dir = os.path.join(base_path, skill_name)
    check_not_exists(skill_dir, skill_name)

    title = skill_title(skill_name)

    # Define output paths
    skill_md_path = os.path.join(skill_dir, "SKILL.md")
    reference_md_path = os.path.join(skill_dir, "references", f"{skill_name}-reference.md")
    gitkeep_path = os.path.join(skill_dir, "scripts", ".gitkeep")

    # Write files
    write_file(skill_md_path, SKILL_MD_TEMPLATE.format(skill_name=skill_name, skill_title=title))
    write_file(reference_md_path, REFERENCE_MD_TEMPLATE.format(skill_name=skill_name, skill_title=title))
    touch_file(gitkeep_path)

    # Report created paths to stdout (one per line)
    print(skill_md_path)
    print(reference_md_path)
    print(gitkeep_path)


if __name__ == "__main__":
    main()
