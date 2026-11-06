#!/usr/bin/env python3
"""
extract-signals.py

Deterministic structural extractor for the detect-overengineering skill.
Analyzes source code files for structural signals and anti-pattern smells of
over-engineering, premature abstraction, layer bloat, and accidental complexity.

Supports:
  .py                -> Python (AST-based, highest precision)
  .ts .tsx .js .jsx  -> TypeScript / JavaScript (structural regex)
  .java              -> Java (structural regex)
  .cs                -> C# (structural regex)
  .go                -> Go (structural regex)
  Other languages    -> Fallback structural scanner

Modes:
  Single file:  extract-signals.py <file-path> [--force]
  Directory:    extract-signals.py --dir <dir-path> [--force]
  Repo-wide:    extract-signals.py --all [--force]

Output (stdout): JSON object with metrics, signals, smells, and complexity score.
"""

from __future__ import annotations

import argparse
import ast
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple


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
    ".code-context",
    ".scan-test-results",
    ".pattern-analysis",
    ".overengineering-analysis",
}

SOURCE_EXTENSIONS = {
    ".py",
    ".ts",
    ".tsx",
    ".js",
    ".jsx",
    ".java",
    ".cs",
    ".go",
}

LANGUAGE_MAP = {
    ".py": "python",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".js": "javascript",
    ".jsx": "javascript",
    ".java": "java",
    ".cs": "csharp",
    ".go": "go",
}

OUTPUT_DIR = ".overengineering-analysis"


def find_repo_root(start: Path) -> Path:
    """Walk up from start until a .git directory or marker is found."""
    current = start.resolve()
    while True:
        if (current / ".git").exists():
            return current
        parent = current.parent
        if parent == current:
            return start.resolve()
        current = parent


def compute_output_path(repo_root: Path, source_path: Path) -> Path:
    """Mirror source path under .overengineering-analysis/ with .md extension."""
    try:
        relative = source_path.resolve().relative_to(repo_root.resolve())
    except ValueError:
        relative = Path(source_path.name)
    return repo_root / OUTPUT_DIR / relative.with_suffix(".md")


def is_stale(source: Path, output: Path) -> bool:
    """Return True if output is missing or source is newer than output."""
    if not output.exists():
        return True
    return source.stat().st_mtime > output.stat().st_mtime


def scan_source_files(base_dir: Path, repo_root: Path) -> List[str]:
    """Scan base_dir and return relative paths of all source files."""
    found: List[str] = []
    for dirpath, dirnames, filenames in os.walk(base_dir):
        dirnames[:] = [
            d for d in dirnames if d not in SKIP_DIRS and not d.startswith(".")
        ]
        for fname in filenames:
            ext = Path(fname).suffix.lower()
            if ext in SOURCE_EXTENSIONS:
                full = Path(dirpath) / fname
                try:
                    rel = full.relative_to(repo_root)
                    found.append(str(rel).replace("\\", "/"))
                except ValueError:
                    found.append(str(full).replace("\\", "/"))
    return sorted(found)


# ---------------------------------------------------------------------------
# Python AST Extractor
# ---------------------------------------------------------------------------

class PythonOverengineeringVisitor(ast.NodeVisitor):
    def __init__(self, source_code: str):
        self.source_code = source_code
        self.lines = source_code.splitlines()
        self.total_loc = len(self.lines)

        self.classes: List[Dict[str, Any]] = []
        self.interfaces: List[Dict[str, Any]] = []
        self.custom_exceptions: List[Dict[str, Any]] = []
        self.functions: List[Dict[str, Any]] = []

        self.pass_through_methods: List[Dict[str, Any]] = []
        self.speculative_params: List[Dict[str, Any]] = []
        self.empty_hooks: List[Dict[str, Any]] = []
        self.typevars_count = 0
        self.generic_classes_count = 0
        self.builder_methods_count = 0

        self.current_class: Optional[Dict[str, Any]] = None
        self.logic_statement_count = 0
        self.boilerplate_statement_count = 0

    def visit_Assign(self, node: ast.Assign):
        # Check TypeVar / ParamSpec
        if isinstance(node.value, ast.Call):
            func_name = getattr(node.value.func, "id", "")
            if func_name in ("TypeVar", "ParamSpec", "TypeVarTuple", "NewType"):
                self.typevars_count += 1
                self.boilerplate_statement_count += 1
                return
        self.logic_statement_count += 1
        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef):
        base_names: List[str] = []
        for b in node.bases:
            if isinstance(b, ast.Name):
                base_names.append(b.id)
            elif isinstance(b, ast.Attribute):
                base_names.append(b.attr)
            elif isinstance(b, ast.Subscript):
                if isinstance(b.value, ast.Name):
                    base_names.append(b.value.id)
                elif isinstance(b.value, ast.Attribute):
                    base_names.append(b.value.attr)

        is_interface = any(b in ("Protocol", "ABC", "ABCMeta") for b in base_names)
        is_generic = any("Generic" in b for b in base_names)
        if is_generic:
            self.generic_classes_count += 1

        is_exception = any("Exception" in b or "Error" in b for b in base_names)

        loc = (node.end_lineno or node.lineno) - node.lineno + 1

        class_info: Dict[str, Any] = {
            "name": node.name,
            "line": node.lineno,
            "loc": loc,
            "bases": base_names,
            "methods": [],
            "fields": [],
            "is_interface": is_interface,
            "is_generic": is_generic,
            "is_exception": is_exception,
            "decorators": [
                getattr(d, "id", getattr(d, "attr", str(d)))
                for d in node.decorator_list
            ],
        }

        prev_class = self.current_class
        self.current_class = class_info

        if is_interface:
            self.interfaces.append(class_info)
        elif is_exception:
            self.custom_exceptions.append(class_info)
        else:
            self.classes.append(class_info)

        self.generic_visit(node)
        self.current_class = prev_class

    def visit_FunctionDef(self, node: ast.FunctionDef):
        self._analyze_function(node, is_async=False)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        self._analyze_function(node, is_async=True)

    def _analyze_function(self, node: Any, is_async: bool):
        loc = (node.end_lineno or node.lineno) - node.lineno + 1
        decorators = [
            getattr(d, "id", getattr(d, "attr", str(d)))
            for d in node.decorator_list
        ]

        # Check for pass-through / trampoline methods:
        # A method that only calls another method forwarding identical or near-identical args
        is_pass_through = False
        target_call = ""
        body_nodes = [
            n for n in node.body if not (isinstance(n, ast.Expr) and isinstance(n.value, ast.Constant))
        ]

        if len(body_nodes) == 1:
            stmt = body_nodes[0]
            call_node = None
            if isinstance(stmt, ast.Return) and isinstance(stmt.value, ast.Call):
                call_node = stmt.value
            elif isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call):
                call_node = stmt.value

            if call_node:
                # E.g. self._inner.method(...)
                if isinstance(call_node.func, ast.Attribute):
                    target_call = f"{getattr(call_node.func.value, 'id', getattr(call_node.func.value, 'attr', 'obj'))}.{call_node.func.attr}"
                    is_pass_through = True
                elif isinstance(call_node.func, ast.Name):
                    target_call = call_node.func.id
                    is_pass_through = True

        # Check for empty hook / no-op method
        is_empty_hook = False
        if len(body_nodes) == 1:
            stmt = body_nodes[0]
            if isinstance(stmt, ast.Pass):
                is_empty_hook = True
            elif isinstance(stmt, ast.Return) and stmt.value is None:
                is_empty_hook = True
            elif isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Constant) and stmt.value.value is Ellipsis:
                is_empty_hook = True

        # Check speculative / catch-all parameters (*args, **kwargs on simple domain methods)
        has_vararg = bool(node.args.vararg)
        has_kwarg = bool(node.args.kwarg)
        if has_kwarg and node.name not in ("__init__", "__new__", "__call__", "dispatch", "wrapper"):
            self.speculative_params.append({
                "function": node.name,
                "class": self.current_class["name"] if self.current_class else None,
                "param": f"**{node.args.kwarg.arg}",
                "line": node.lineno,
            })

        # Check builder method pattern: returns self
        returns_self = False
        for n in ast.walk(node):
            if isinstance(n, ast.Return) and isinstance(n.value, ast.Name) and n.value.id == "self":
                returns_self = True
                break
        if returns_self and self.current_class:
            self.builder_methods_count += 1

        func_info: Dict[str, Any] = {
            "name": node.name,
            "line": node.lineno,
            "loc": loc,
            "is_async": is_async,
            "decorators": decorators,
            "is_pass_through": is_pass_through,
            "is_empty_hook": is_empty_hook,
            "has_vararg": has_vararg,
            "has_kwarg": has_kwarg,
            "params": [a.arg for a in node.args.args],
        }

        if is_pass_through:
            self.pass_through_methods.append({
                "method": node.name,
                "class": self.current_class["name"] if self.current_class else None,
                "target": target_call,
                "line": node.lineno,
            })

        if is_empty_hook and "abstractmethod" not in decorators:
            self.empty_hooks.append({
                "method": node.name,
                "class": self.current_class["name"] if self.current_class else None,
                "line": node.lineno,
            })

        if self.current_class:
            self.current_class["methods"].append(func_info)
        else:
            self.functions.append(func_info)

        self.generic_visit(node)


def extract_python_signals(source: str, file_path: str) -> Dict[str, Any]:
    try:
        tree = ast.parse(source, filename=file_path)
    except SyntaxError as e:
        return {
            "parse_method": "ast_error",
            "error": str(e),
            "metrics": {"total_loc": len(source.splitlines())},
            "signals": {},
            "smells": [],
        }

    visitor = PythonOverengineeringVisitor(source)
    visitor.visit(tree)

    total_classes = len(visitor.classes)
    total_interfaces = len(visitor.interfaces)
    total_exceptions = len(visitor.custom_exceptions)
    total_methods = sum(len(c["methods"]) for c in visitor.classes) + sum(len(i["methods"]) for i in visitor.interfaces)
    total_functions = len(visitor.functions)
    total_pass_through = len(visitor.pass_through_methods)
    total_empty_hooks = len(visitor.empty_hooks)
    total_speculative = len(visitor.speculative_params)

    # Detect DTO / Anemic data classes
    anemic_classes = []
    for c in visitor.classes:
        non_init_methods = [m for m in c["methods"] if m["name"] not in ("__init__", "__repr__", "__str__", "__eq__")]
        if len(c["methods"]) > 0 and len(non_init_methods) == 0:
            anemic_classes.append(c["name"])

    # Detect single-method interfaces (or empty interfaces)
    shallow_interfaces = []
    for i in visitor.interfaces:
        if len(i["methods"]) <= 1:
            shallow_interfaces.append({"name": i["name"], "methods_count": len(i["methods"]), "line": i["line"]})

    # Deep inheritance
    deep_inheritance_classes = []
    for c in visitor.classes:
        if len(c["bases"]) >= 3:
            deep_inheritance_classes.append({"name": c["name"], "bases": c["bases"], "line": c["line"]})

    metrics = {
        "total_loc": visitor.total_loc,
        "total_classes": total_classes,
        "total_interfaces": total_interfaces,
        "total_exceptions": total_exceptions,
        "total_methods": total_methods,
        "total_functions": total_functions,
        "pass_through_methods_count": total_pass_through,
        "empty_hooks_count": total_empty_hooks,
        "speculative_params_count": total_speculative,
        "typevars_count": visitor.typevars_count,
        "builder_methods_count": visitor.builder_methods_count,
        "anemic_classes_count": len(anemic_classes),
        "shallow_interfaces_count": len(shallow_interfaces),
    }

    # Signals
    signals = {
        "has_single_method_interface": len(shallow_interfaces) > 0,
        "has_pass_through_indirection": total_pass_through > 0,
        "has_excessive_exceptions": (total_exceptions >= 3 and visitor.total_loc < 300) or total_exceptions >= 5,
        "has_speculative_params": total_speculative > 0,
        "has_empty_hook_methods": total_empty_hooks > 0,
        "has_typevar_generics_sprawl": visitor.typevars_count >= 3,
        "has_builder_pattern_boilerplate": visitor.builder_methods_count >= 3,
        "has_anemic_class_churn": len(anemic_classes) >= 2,
        "has_deep_multiple_bases": len(deep_inheritance_classes) > 0,
    }

    # Smells list
    smells = []
    if shallow_interfaces:
        for s in shallow_interfaces:
            smells.append({
                "type": "premature_interface_abstraction",
                "severity": "medium",
                "line": s["line"],
                "target": s["name"],
                "description": f"Interface/Protocol '{s['name']}' has only {s['methods_count']} method(s). In Python, duck typing or a simple Callable is often simpler than a dedicated Protocol.",
            })

    if total_pass_through >= 2:
        for pt in visitor.pass_through_methods:
            smells.append({
                "type": "trampoline_pass_through_method",
                "severity": "medium",
                "line": pt["line"],
                "target": f"{pt['class'] or ''}.{pt['method']}",
                "description": f"Pass-through method delegates straight to '{pt['target']}' without transformation, adding indirection without value.",
            })

    if total_exceptions >= 3 and visitor.total_loc < 300:
        smells.append({
            "type": "custom_exception_proliferation",
            "severity": "low",
            "line": visitor.custom_exceptions[0]["line"] if visitor.custom_exceptions else 1,
            "target": f"{total_exceptions} exceptions in {visitor.total_loc} LOC",
            "description": f"Defined {total_exceptions} custom exceptions in a small file. Standard exceptions (ValueError, TypeError, KeyError) are often sufficient.",
        })

    if total_empty_hooks > 0:
        for eh in visitor.empty_hooks:
            smells.append({
                "type": "speculative_empty_hook",
                "severity": "low",
                "line": eh["line"],
                "target": f"{eh['class'] or ''}.{eh['method']}",
                "description": f"No-op hook method '{eh['method']}' provided for hypothetical future subclass extension (YAGNI).",
            })

    if visitor.builder_methods_count >= 3:
        smells.append({
            "type": "builder_pattern_ceremony",
            "severity": "medium",
            "line": visitor.classes[0]["line"] if visitor.classes else 1,
            "target": f"{visitor.builder_methods_count} builder chaining methods",
            "description": "Fluent builder chaining in Python is usually verbose compared to keyword arguments with dataclasses.",
        })

    return {
        "parse_method": "python_ast",
        "classes": visitor.classes,
        "interfaces": visitor.interfaces,
        "custom_exceptions": visitor.custom_exceptions,
        "functions": visitor.functions,
        "pass_through_methods": visitor.pass_through_methods,
        "metrics": metrics,
        "signals": signals,
        "smells": smells,
    }


# ---------------------------------------------------------------------------
# TypeScript / JavaScript / Java / C# Regex Structural Extractor
# ---------------------------------------------------------------------------

def extract_regex_signals(source: str, file_path: str, language: str) -> Dict[str, Any]:
    lines = source.splitlines()
    total_loc = len(lines)

    # Interface detection
    interface_matches = list(re.finditer(r"\b(?:interface)\s+([A-Z][A-Za-z0-9_]*)(?:<[^>]+>)?\s*(?:extends\s+([^{]+))?\{", source))
    abstract_class_matches = list(re.finditer(r"\babstract\s+class\s+([A-Z][A-Za-z0-9_]*)", source))
    class_matches = list(re.finditer(r"\bclass\s+([A-Z][A-Za-z0-9_]*)(?:<[^>]+>)?\s*(?:extends\s+([A-Za-z0-9_<>,\s]+))?(?:\s*implements\s+([A-Za-z0-9_<>,\s]+))?", source))

    # Custom exception / error matches
    error_class_matches = list(re.finditer(r"\bclass\s+([A-Z][A-Za-z0-9_]*)\s+extends\s+(?:Error|Exception|RuntimeException|BaseException)\b", source))

    # Pass-through delegation methods: e.g. return this.service.doSomething(...);
    pass_through_matches = list(re.finditer(
        r"(?:(?:public|private|protected|async)\s+)*([a-zA-Z0-9_]+)\s*\([^)]*\)(?::\s*[^\{]+)?\s*\{\s*(?:return\s+)?(?:this\.|_\w+\.)([a-zA-Z0-9_]+)\s*\([^)]*\)\s*;\s*\}",
        source
    ))

    # Builder pattern setter chaining: return this;
    builder_matches = list(re.finditer(r"(?:with[A-Z]\w*|set[A-Z]\w*)\s*\([^)]*\)[^{]*\{\s*this\.\w+\s*=\s*\w+;\s*return\s+this;\s*\}", source))

    # Speculative generic type parameters: <T, U, V, K, R>
    generic_decl_matches = list(re.finditer(r"<([A-Z](?:,\s*[A-Z]){2,})>", source))

    # Empty hook methods: e.g. onX() {} or protected void onX() {}
    empty_hook_matches = list(re.finditer(r"(?:void|[a-zA-Z0-9_]+)\s+(?:on|before|after|handle)([A-Z][a-zA-Z0-9_]*)\s*\([^)]*\)\s*\{\s*\}", source))

    total_classes = len(class_matches)
    total_interfaces = len(interface_matches) + len(abstract_class_matches)
    total_exceptions = len(error_class_matches)
    total_pass_through = len(pass_through_matches)
    total_builder = len(builder_matches)
    total_empty_hooks = len(empty_hook_matches)

    metrics = {
        "total_loc": total_loc,
        "total_classes": total_classes,
        "total_interfaces": total_interfaces,
        "total_exceptions": total_exceptions,
        "pass_through_methods_count": total_pass_through,
        "builder_methods_count": total_builder,
        "empty_hooks_count": total_empty_hooks,
        "speculative_generics_count": len(generic_decl_matches),
    }

    signals = {
        "has_pass_through_indirection": total_pass_through > 0,
        "has_excessive_exceptions": (total_exceptions >= 3 and total_loc < 300) or total_exceptions >= 5,
        "has_builder_pattern_boilerplate": total_builder >= 3,
        "has_empty_hook_methods": total_empty_hooks > 0,
        "has_heavy_interface_ratio": total_interfaces > 0 and (total_interfaces >= total_classes),
        "has_speculative_generics": len(generic_decl_matches) > 0,
    }

    smells = []
    if total_interfaces > 0 and total_classes > 0 and total_interfaces >= total_classes:
        smells.append({
            "type": "one_to_one_interface_paranoia",
            "severity": "medium",
            "line": 1,
            "target": f"{total_interfaces} interfaces for {total_classes} classes",
            "description": f"Found {total_interfaces} interfaces alongside {total_classes} classes (1:1 ratio). Creating an interface for every single concrete class adds indirection without flexibility.",
        })

    if total_pass_through >= 2:
        for m in pass_through_matches[:5]:
            line_no = source[:m.start()].count("\n") + 1
            smells.append({
                "type": "trampoline_pass_through_method",
                "severity": "medium",
                "line": line_no,
                "target": m.group(1) if m.groups() else "method",
                "description": "Method does nothing except delegate to another object without translating or augmenting parameters.",
            })

    if total_builder >= 3:
        smells.append({
            "type": "builder_pattern_ceremony",
            "severity": "low",
            "line": 1,
            "target": f"{total_builder} builder methods",
            "description": "Repetitive builder methods. Consider using parameter objects, object literals, or records/dataclasses.",
        })

    if total_empty_hooks > 0:
        for m in empty_hook_matches[:4]:
            line_no = source[:m.start()].count("\n") + 1
            smells.append({
                "type": "speculative_empty_hook",
                "severity": "low",
                "line": line_no,
                "target": m.group(0).strip(),
                "description": "Empty hook method for speculative future extensibility (violates YAGNI).",
            })

    return {
        "parse_method": f"{language}_regex",
        "metrics": metrics,
        "signals": signals,
        "smells": smells,
        "pass_through_methods": [{"method": m.group(1), "line": source[:m.start()].count("\n") + 1} for m in pass_through_matches],
    }


# ---------------------------------------------------------------------------
# Severity & Overengineering Score Calculator
# ---------------------------------------------------------------------------

def calculate_overengineering_score(metrics: Dict[str, Any], signals: Dict[str, Any], smells: List[Dict[str, Any]]) -> Tuple[int, str]:
    """
    Compute an over-engineering risk score (0 - 100) and severity rating:
      0 - 19: Minimal / Clean
      20 - 39: Low
      40 - 64: Moderate
      65 - 84: High
      85 - 100: Extreme
    """
    score = 0

    # Smell penalties
    severity_weights = {"low": 8, "medium": 15, "high": 25}
    for smell in smells:
        score += severity_weights.get(smell.get("severity", "low"), 10)

    # Pass-through indirection penalty
    pt_count = metrics.get("pass_through_methods_count", 0)
    if pt_count >= 3:
        score += 15
    elif pt_count >= 1:
        score += 8

    # Empty hooks / YAGNI penalty
    eh_count = metrics.get("empty_hooks_count", 0)
    if eh_count >= 2:
        score += 12

    # Ratio penalty: shallow interfaces
    if signals.get("has_single_method_interface") or signals.get("has_heavy_interface_ratio"):
        score += 15

    # Cap score at 100
    score = min(100, score)

    if score < 20:
        severity = "clean"
    elif score < 40:
        severity = "low"
    elif score < 65:
        severity = "moderate"
    elif score < 85:
        severity = "high"
    else:
        severity = "extreme"

    return score, severity


# ---------------------------------------------------------------------------
# File Analyzer Entry Point
# ---------------------------------------------------------------------------

def analyze_file(source_path: Path, repo_root: Path, force: bool = False) -> Dict[str, Any]:
    resolved = source_path.resolve()
    if not resolved.exists():
        raise FileNotFoundError(f"File not found: {source_path}")

    rel_path_str = str(resolved.relative_to(repo_root.resolve())).replace("\\", "/") if repo_root in resolved.parents or repo_root == resolved.parent else resolved.name
    output_path = compute_output_path(repo_root, resolved)
    stale_flag = is_stale(resolved, output_path) or force

    try:
        content = resolved.read_text(encoding="utf-8", errors="replace")
    except Exception as exc:
        return {
            "source_path": rel_path_str,
            "error": f"Failed to read file: {exc}",
            "stale": False,
        }

    ext = resolved.suffix.lower()
    language = LANGUAGE_MAP.get(ext, "unknown")

    if language == "python":
        extracted = extract_python_signals(content, str(resolved))
    else:
        extracted = extract_regex_signals(content, str(resolved), language)

    metrics = extracted.get("metrics", {})
    signals = extracted.get("signals", {})
    smells = extracted.get("smells", [])

    score, severity = calculate_overengineering_score(metrics, signals, smells)

    try:
        rel_output = str(output_path.relative_to(repo_root.resolve())).replace("\\", "/")
    except ValueError:
        rel_output = str(output_path).replace("\\", "/")

    result: Dict[str, Any] = {
        "source_path": rel_path_str,
        "language": language,
        "repo_root": str(repo_root).replace("\\", "/"),
        "output_path": rel_output,
        "stale": stale_flag,
        "overengineering_score": score,
        "severity": severity,
        "metrics": metrics,
        "signals": signals,
        "smells": smells,
        "parse_method": extracted.get("parse_method", "unknown"),
    }

    if "pass_through_methods" in extracted:
        result["pass_through_methods"] = extracted["pass_through_methods"]
    if "custom_exceptions" in extracted:
        result["custom_exceptions"] = [
            {"name": e["name"], "line": e["line"]} for e in extracted["custom_exceptions"]
        ]
    if "interfaces" in extracted:
        result["interfaces"] = [
            {"name": i["name"], "line": i["line"], "methods_count": len(i.get("methods", []))}
            for i in extracted["interfaces"]
        ]

    return result


# ---------------------------------------------------------------------------
# CLI Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Extract structural over-engineering signals from source files."
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("file", nargs="?", help="Path to single source file")
    group.add_argument("--all", action="store_true", help="Analyze all source files in repo")
    group.add_argument("--dir", dest="directory", help="Analyze all source files under directory")

    parser.add_argument(
        "--force",
        action="store_true",
        help="Analyze even if output report is already up to date",
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print JSON output",
    )

    args = parser.parse_args()
    cwd = Path.cwd()
    repo_root = find_repo_root(cwd)

    indent = 2 if args.pretty else None

    if args.file:
        file_path = Path(args.file)
        if not file_path.is_absolute():
            file_path = cwd / file_path
        try:
            res = analyze_file(file_path, repo_root, force=args.force)
            print(json.dumps(res, indent=indent))
        except Exception as e:
            print(json.dumps({"error": str(e)}), file=sys.stderr)
            sys.exit(1)

    elif args.all or args.directory:
        scan_dir = Path(args.directory).resolve() if args.directory else repo_root
        source_files = scan_source_files(scan_dir, repo_root)

        results = []
        clean_count = 0
        moderate_count = 0
        high_risk_count = 0

        for rel in source_files:
            fp = repo_root / rel
            try:
                res = analyze_file(fp, repo_root, force=args.force)
                results.append(res)
                sev = res.get("severity")
                if sev in ("clean", "low"):
                    clean_count += 1
                elif sev == "moderate":
                    moderate_count += 1
                else:
                    high_risk_count += 1
            except Exception:
                continue

        summary = {
            "mode": "repo-wide" if args.all else "directory",
            "base_dir": str(scan_dir.relative_to(repo_root) if scan_dir != repo_root else ".").replace("\\", "/"),
            "total_files_scanned": len(results),
            "clean_or_low_risk": clean_count,
            "moderate_risk": moderate_count,
            "high_or_extreme_risk": high_risk_count,
            "files": results,
        }
        print(json.dumps(summary, indent=indent))


if __name__ == "__main__":
    main()

