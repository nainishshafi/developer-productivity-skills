#!/usr/bin/env python3
"""
trace-context.py

Validates symbols and imports for a source file using AST or structured parsers,
performs a full-repo source file scan, and checks whether the context file is stale.

Output (stdout): single JSON object
Errors: stderr, exit 1 on failure

Usage:
  .venv/Scripts/python .github/skills/trace-code-context/scripts/trace-context.py <file-path>
  .venv/bin/python     .github/skills/trace-code-context/scripts/trace-context.py <file-path>
"""

from __future__ import annotations

import argparse
import ast
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

SKIP_DIRS = {
    ".git",
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
    ".code-context",  # don't scan our own output folder
}

SOURCE_EXTENSIONS = {
    ".py", ".java",
    ".js", ".ts", ".jsx", ".tsx",
    ".go",
    ".cs",
    ".rb",
    ".cpp", ".c",
    ".rs",
}

LANGUAGE_MAP = {
    ".py": "python",
    ".java": "java",
    ".js": "javascript",
    ".ts": "typescript",
    ".jsx": "javascript",
    ".tsx": "typescript",
    ".go": "go",
    ".cs": "csharp",
    ".rb": "ruby",
    ".cpp": "cpp",
    ".c": "c",
    ".rs": "rust",
}

OUTPUT_DIR = ".code-context"


# ---------------------------------------------------------------------------
# Repo root detection
# ---------------------------------------------------------------------------

def find_repo_root(start: Path) -> Path:
    """Walk up from start until a .git directory is found; fallback = start."""
    current = start.resolve()
    while True:
        if (current / ".git").exists():
            return current
        parent = current.parent
        if parent == current:
            # Reached filesystem root without finding .git
            return start.resolve()
        current = parent


# ---------------------------------------------------------------------------
# Output path computation
# ---------------------------------------------------------------------------

def compute_output_path(repo_root: Path, source_path: Path) -> Path:
    """Mirror the source path under .code-context/ with a .md extension."""
    try:
        relative = source_path.resolve().relative_to(repo_root.resolve())
    except ValueError:
        # source is outside repo root — use filename only
        relative = Path(source_path.name)
    return repo_root / OUTPUT_DIR / relative.with_suffix(".md")


# ---------------------------------------------------------------------------
# Staleness check
# ---------------------------------------------------------------------------

def is_stale(source: Path, output: Path) -> bool:
    """Return True if output is missing or source is newer than output."""
    if not output.exists():
        return True
    return source.stat().st_mtime > output.stat().st_mtime


# ---------------------------------------------------------------------------
# Full-repo source file scan
# ---------------------------------------------------------------------------

def scan_source_files(repo_root: Path) -> list[str]:
    """Walk repo and return relative paths of all source files."""
    found: list[str] = []
    for dirpath, dirnames, filenames in os.walk(repo_root):
        dirnames[:] = [
            d for d in dirnames
            if d not in SKIP_DIRS and not d.startswith(".")
        ]
        for fname in filenames:
            if Path(fname).suffix in SOURCE_EXTENSIONS:
                full = Path(dirpath) / fname
                try:
                    rel = full.relative_to(repo_root)
                    found.append(str(rel).replace("\\", "/"))
                except ValueError:
                    found.append(str(full).replace("\\", "/"))
    return sorted(found)


# ---------------------------------------------------------------------------
# Symbol/import extraction
# ---------------------------------------------------------------------------

def extract_python(source_path: Path) -> tuple[list[str], list[str], str]:
    """Extract symbols and imports from a Python file using ast."""
    symbols: list[str] = []
    imports: list[str] = []
    try:
        tree = ast.parse(source_path.read_text(encoding="utf-8", errors="replace"))
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                # Only top-level or class-level (not nested inside functions)
                symbols.append(node.name)
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                for alias in node.names:
                    imports.append(f"{module}.{alias.name}" if module else alias.name)
        return sorted(set(symbols)), sorted(set(imports)), "ast"
    except SyntaxError as e:
        print(f"Warning: AST parse failed for {source_path}: {e}", file=sys.stderr)
        return [], [], "ast"


def extract_java(source_path: Path) -> tuple[list[str], list[str], str]:
    """Extract symbols and imports from a Java file using structured regex."""
    text = source_path.read_text(encoding="utf-8", errors="replace")
    symbols: list[str] = []
    imports: list[str] = []

    # Types: class, interface, enum, record
    for m in re.finditer(r"\b(?:class|interface|enum|record)\s+(\w+)", text):
        symbols.append(m.group(1))

    # Method signatures: <modifiers> <ReturnType> <methodName>(
    # Matches patterns like: public void doSomething(, private String buildQuery(
    for m in re.finditer(
        r"(?:public|protected|private|static|final|abstract|synchronized|native|default)"
        r"(?:\s+(?:public|protected|private|static|final|abstract|synchronized|native|default))*"
        r"\s+\w[\w<>\[\],\s]*\s+(\w+)\s*\(",
        text,
    ):
        name = m.group(1)
        if name not in {"if", "while", "for", "switch", "catch"}:
            symbols.append(name)

    # Imports
    for m in re.finditer(r"^import\s+([\w.]+)\s*;", text, re.MULTILINE):
        imports.append(m.group(1))

    return sorted(set(symbols)), sorted(set(imports)), "java-regex"


def extract_js_ts(source_path: Path) -> tuple[list[str], list[str], str]:
    """Extract symbols and imports from JS/TS files using regex."""
    text = source_path.read_text(encoding="utf-8", errors="replace")
    symbols: list[str] = []
    imports: list[str] = []

    # Exported symbols: export function/class/const/async function
    for m in re.finditer(
        r"export\s+(?:default\s+)?(?:async\s+)?(?:function|class|const|let|var)\s+(\w+)",
        text,
    ):
        symbols.append(m.group(1))

    # Non-exported top-level function/class declarations
    for m in re.finditer(r"^(?:async\s+)?(?:function|class)\s+(\w+)", text, re.MULTILINE):
        symbols.append(m.group(1))

    # ES6 imports: import ... from '...'
    for m in re.finditer(r"""from\s+['"]([^'"]+)['"]""", text):
        imports.append(m.group(1))

    # CommonJS require
    for m in re.finditer(r"""require\s*\(\s*['"]([^'"]+)['"]\s*\)""", text):
        imports.append(m.group(1))

    return sorted(set(symbols)), sorted(set(imports)), "js-regex"


def extract_go(source_path: Path) -> tuple[list[str], list[str], str]:
    """Extract symbols and imports from Go files using regex."""
    text = source_path.read_text(encoding="utf-8", errors="replace")
    symbols: list[str] = []
    imports: list[str] = []

    # Top-level functions and methods
    for m in re.finditer(r"^func\s+(?:\(\w+\s+\*?\w+\)\s+)?(\w+)\s*\(", text, re.MULTILINE):
        symbols.append(m.group(1))

    # Type declarations (struct, interface, type alias)
    for m in re.finditer(r"^type\s+(\w+)\s+(?:struct|interface|\w)", text, re.MULTILINE):
        symbols.append(m.group(1))

    # Imports — handle both single and block imports
    # Single: import "path"
    for m in re.finditer(r'^import\s+"([^"]+)"', text, re.MULTILINE):
        imports.append(m.group(1))

    # Block: import ( ... )
    block_match = re.search(r"import\s*\(([^)]+)\)", text, re.DOTALL)
    if block_match:
        for m in re.finditer(r'"([^"]+)"', block_match.group(1)):
            imports.append(m.group(1))

    return sorted(set(symbols)), sorted(set(imports)), "go-regex"


def extract_fallback(source_path: Path) -> tuple[list[str], list[str], str]:
    """Generic regex extraction for unsupported languages."""
    text = source_path.read_text(encoding="utf-8", errors="replace")
    symbols: list[str] = []

    for m in re.finditer(
        r"^(?:function|def|class|func|sub|proc|procedure|method)\s+(\w+)",
        text,
        re.MULTILINE | re.IGNORECASE,
    ):
        symbols.append(m.group(1))

    return sorted(set(symbols)), [], "regex-fallback"


def extract_with_ctags(source_path: Path) -> tuple[list[str], list[str], str]:
    """Use ctags to extract symbols if available."""
    result = subprocess.run(
        ["ctags", "--output-format=json", "-f", "-", str(source_path)],
        capture_output=True,
        text=True,
        timeout=10,
    )
    symbols: list[str] = []
    for line in result.stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            entry = json.loads(line)
            name = entry.get("name", "")
            if name:
                symbols.append(name)
        except json.JSONDecodeError:
            # ctags may emit non-JSON lines; skip them
            pass
    return sorted(set(symbols)), [], "ctags"


def extract_symbols_and_imports(
    source_path: Path, language: str
) -> tuple[list[str], list[str], str]:
    """
    Extract symbols and imports. Try ctags first if available,
    then fall through to language-specific extractors.
    """
    if shutil.which("ctags"):
        try:
            syms, imps, method = extract_with_ctags(source_path)
            if syms:  # only use ctags if it found something
                return syms, imps, method
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            pass

    if language == "python":
        return extract_python(source_path)
    elif language == "java":
        return extract_java(source_path)
    elif language in ("javascript", "typescript"):
        return extract_js_ts(source_path)
    elif language == "go":
        return extract_go(source_path)
    else:
        return extract_fallback(source_path)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Extract validated symbols/imports and check staleness for a source file."
    )
    parser.add_argument("file_path", help="Path to the source file to analyze")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force regeneration even if context is already up to date",
    )
    args = parser.parse_args()

    source_path = Path(args.file_path)

    if not source_path.exists():
        print(f"Error: file not found: {args.file_path}", file=sys.stderr)
        sys.exit(1)

    if not source_path.is_file():
        print(f"Error: not a file: {args.file_path}", file=sys.stderr)
        sys.exit(1)

    source_path = source_path.resolve()

    # Detect language
    suffix = source_path.suffix.lower()
    language = LANGUAGE_MAP.get(suffix, "unknown")

    # Find repo root
    repo_root = find_repo_root(source_path.parent)

    # Compute relative source path (for output and display)
    try:
        rel_source = source_path.relative_to(repo_root)
    except ValueError:
        rel_source = Path(source_path.name)
    rel_source_str = str(rel_source).replace("\\", "/")

    # Compute output path
    output_path = compute_output_path(repo_root, source_path)
    output_path_str = str(output_path.relative_to(repo_root)).replace("\\", "/")

    # Staleness check
    stale = args.force or is_stale(source_path, output_path)

    # Full-repo source scan (always — subagent needs this even if stale=false)
    repo_source_files = scan_source_files(repo_root)

    # Symbol/import extraction
    symbols, imports, parse_method = extract_symbols_and_imports(source_path, language)

    result = {
        "stale": stale,
        "repo_root": str(repo_root).replace("\\", "/"),
        "output_path": output_path_str,
        "source_path": rel_source_str,
        "language": language,
        "symbols": symbols,
        "imports": imports,
        "parse_method": parse_method,
        "repo_source_files": repo_source_files,
    }

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
