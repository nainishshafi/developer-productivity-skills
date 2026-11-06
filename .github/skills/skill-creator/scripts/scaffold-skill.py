#!/usr/bin/env python3
"""
scaffold-skill.py — Create boilerplate directory structure for a new Claude Code skill.

Usage:
    python scaffold-skill.py <skill-name> [base-path] [--modular]

Arguments:
    skill-name   Required. Lowercase kebab-case name for the skill (e.g., lint-python).
    base-path    Optional. Root directory where skills live. Default: .github/skills
    --modular    Optional flag. Scaffolds a modular Knowledge-Pack skill (lean SKILL.md router + topic subdirectories).

Output:
    Prints each created file path to stdout, one per line.
    Errors are printed to stderr and exit with code 1.
"""

import os
import re
import sys


SKILL_NAME_PATTERN = re.compile(r"^[a-z][a-z0-9-]+$")

TASK_SKILL_MD_TEMPLATE = """\
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

MODULAR_SKILL_MD_TEMPLATE = """\
---
name: {skill_name}
description: Expert architectural and engineering guidance for {skill_title}. Helps the LLM analyze architecture, apply clean design, enforce memory/performance hygiene, and adopt testing patterns pragmatically. Use when writing, reviewing, designing, or refactoring {skill_title} code.
version: 1.0.0
---

# {skill_title} Skill

You are an expert software engineer specializing in modern {skill_title}, clean architecture, memory safety, and performance.

## Core Directives

1. **Respect Project Baseline**: Check toolchain, runtime version, and existing libraries before introducing dependencies.
2. **Simplicity First (KISS & YAGNI)**: Favor straightforward, readable code over speculative abstractions.
3. **Memory & Performance Hygiene**: Proactively avoid closure scope leaks, unbounded collections, event loop blocking, and resource leaks.
4. **Follow Established Conventions**: Match codebase patterns over personal stylistic preferences.

## Knowledge Modules

Load only the modules relevant to the task.

- [Architecture & Domain Modeling](core/architecture.md)
- [Memory Safety & Closures](runtime-and-memory/memory-and-closures.md)
- [Performance & Concurrency](concurrency/concurrency.md)
- [Security Guidelines](security/security.md)
- [Testing & Quality Best Practices](testing/best-practices.md)
"""

MODULAR_CORE_MD_TEMPLATE = """\
# {skill_title} Architecture & Domain Modeling

Architectural styles, domain boundaries, and modeling patterns.

---

## 1. Architectural Styles

TODO — describe primary architectures (Layered, Modular Monolith, Hexagonal/Clean).

## 2. Domain Modeling & Invariants

TODO — describe state representation and immutability.
"""

MODULAR_MEMORY_MD_TEMPLATE = """\
# {skill_title} Memory Safety & Closures

Memory leak prevention, scope hygiene, and resource management.

---

## 1. Closure Scope & Lifecycle Retention

TODO — describe closure traps, listener leaks, and unmounted teardown.

## 2. Bounded Collections & Caches

TODO — describe bounded caching (LRU, Weak references).
"""

MODULAR_CONCURRENCY_MD_TEMPLATE = """\
# {skill_title} Concurrency & Performance

Non-blocking execution, concurrency throttling, and runtime efficiency.

---

## 1. Event Loop & Thread Safety

TODO — non-blocking operations and offloading.

## 2. Concurrency Throttling

TODO — bounded async concurrency and backpressure.
"""

MODULAR_SECURITY_MD_TEMPLATE = """\
# {skill_title} Security Guidelines

Input validation, defensive design, and vulnerability prevention.

---

## 1. Input Defense & Boundary Validation

TODO — input sanitization and typing defense.

## 2. Injection & Resource Exhaustion Defense

TODO — avoiding injection risks and DoS vectors.
"""

MODULAR_TESTING_MD_TEMPLATE = """\
# {skill_title} Testing Best Practices

Testing pyramids, mock boundaries, and behavioral verification.

---

## 1. Unit Testing & Invariants

TODO — fast in-memory invariant testing.

## 2. Integration & Boundary Tests

TODO — real adapter testing without flaky mocks.
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
            "Example: lint-python, deploy-staging, typescript-developer",
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
    args = sys.argv[1:]
    is_modular = "--modular" in args or "-m" in args
    clean_args = [a for a in args if a not in ("--modular", "-m")]

    if not clean_args:
        print(
            "Usage: scaffold-skill.py <skill-name> [base-path] [--modular]\n"
            "\n"
            "Arguments:\n"
            "  skill-name   Lowercase kebab-case name (e.g., lint-python)\n"
            "  base-path    Root skills directory (default: .github/skills)\n"
            "  --modular    Scaffold as a modular Knowledge-Pack (like java-developer)",
            file=sys.stderr,
        )
        sys.exit(1)

    skill_name = clean_args[0]
    base_path = clean_args[1] if len(clean_args) >= 2 else ".github/skills"

    validate_skill_name(skill_name)
    skill_dir = os.path.join(base_path, skill_name)
    check_not_exists(skill_dir, skill_name)

    title = skill_title(skill_name)

    if is_modular:
        # Modular Knowledge-Pack structure
        files_to_create = [
            (os.path.join(skill_dir, "SKILL.md"), MODULAR_SKILL_MD_TEMPLATE.format(skill_name=skill_name, skill_title=title)),
            (os.path.join(skill_dir, "core", "architecture.md"), MODULAR_CORE_MD_TEMPLATE.format(skill_title=title)),
            (os.path.join(skill_dir, "runtime-and-memory", "memory-and-closures.md"), MODULAR_MEMORY_MD_TEMPLATE.format(skill_title=title)),
            (os.path.join(skill_dir, "concurrency", "concurrency.md"), MODULAR_CONCURRENCY_MD_TEMPLATE.format(skill_title=title)),
            (os.path.join(skill_dir, "security", "security.md"), MODULAR_SECURITY_MD_TEMPLATE.format(skill_title=title)),
            (os.path.join(skill_dir, "testing", "best-practices.md"), MODULAR_TESTING_MD_TEMPLATE.format(skill_title=title)),
        ]
        for path, content in files_to_create:
            write_file(path, content)
            print(path)
    else:
        # Standard task/action or single-reference skill structure
        skill_md_path = os.path.join(skill_dir, "SKILL.md")
        reference_md_path = os.path.join(skill_dir, "references", f"{skill_name}-reference.md")
        gitkeep_path = os.path.join(skill_dir, "scripts", ".gitkeep")

        write_file(skill_md_path, TASK_SKILL_MD_TEMPLATE.format(skill_name=skill_name, skill_title=title))
        write_file(reference_md_path, REFERENCE_MD_TEMPLATE.format(skill_name=skill_name, skill_title=title))
        touch_file(gitkeep_path)

        print(skill_md_path)
        print(reference_md_path)
        print(gitkeep_path)


if __name__ == "__main__":
    main()
