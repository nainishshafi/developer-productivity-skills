#!/usr/bin/env python3
"""
extract-patterns.py

Multi-language structural extractor for the design-pattern-detector skill.

Supports:
  .py              -> Python    (AST-based, most accurate)
  .java            -> Java      (regex-based)
  .js .jsx .ts .tsx -> JavaScript/TypeScript (regex-based)
  .go              -> Go        (regex-based)
  .cs              -> C#        (regex-based)
  .rb .cpp .c .rs  -> Fallback  (generic regex)

Auto-detects language from file extension. Outputs a uniform JSON shape
regardless of language, with classes, functions, metrics, and structural
signals for design pattern detection.

Modes:
  Single file:  extract-patterns.py <file-path> [--force]
  Repo-wide:    extract-patterns.py --all [--force]

Output (stdout): single JSON object (single file) or JSON object with
                 "files" array (repo-wide)
Errors: stderr, exit 1 on failure

Usage:
  .venv/Scripts/python .github/skills/design-pattern-detector/scripts/extract-patterns.py <file-path>
  .venv/bin/python     .github/skills/design-pattern-detector/scripts/extract-patterns.py <file-path>
"""

from __future__ import annotations

import argparse
import ast
import json
import os
import re
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
    ".code-context",
    ".scan-test-results",
    ".pattern-analysis",
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

OUTPUT_DIR = ".pattern-analysis"


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
            return start.resolve()
        current = parent


# ---------------------------------------------------------------------------
# Output path computation
# ---------------------------------------------------------------------------

def compute_output_path(repo_root: Path, source_path: Path) -> Path:
    """Mirror the source path under .pattern-analysis/ with a .md extension."""
    try:
        relative = source_path.resolve().relative_to(repo_root.resolve())
    except ValueError:
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
# Source file scanning (for --all mode)
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
# Shared types
# ---------------------------------------------------------------------------

def _empty_extraction() -> dict:
    """Return an empty extraction result."""
    return {
        "classes": [],
        "functions": [],
        "metrics": {
            "total_classes": 0,
            "total_methods": 0,
            "total_functions": 0,
            "total_loc": 0,
            "max_method_loc": 0,
            "avg_method_loc": 0.0,
        },
        "structural_signals": _empty_signals(),
        "parse_method": "unknown",
    }


def _empty_signals() -> dict:
    return {
        "has_private_constructor": False,
        "has_static_instance_field": False,
        "has_get_instance_method": False,
        "has_create_methods": False,
        "has_subscribe_notify": False,
        "has_fluent_api": False,
        "has_build_method": False,
        "has_crud_methods": False,
        "has_delegation_pattern": False,
        "has_same_type_wrapping": False,
        "has_execute_undo": False,
        "has_abstract_template_steps": False,
        "has_facade_pattern": False,
    }


# ---------------------------------------------------------------------------
# Signal computation (language-agnostic, works on extracted structure)
# ---------------------------------------------------------------------------

_SINGLETON_METHOD_NAMES = {"get_instance", "getinstance", "instance"}
_CREATE_PREFIXES = ("create", "build", "make", "new_", "from_")
_OBSERVER_NAMES = {
    "subscribe", "unsubscribe", "notify", "emit", "on", "off",
    "add_listener", "remove_listener", "add_observer", "remove_observer",
    "add_handler", "remove_handler", "register", "unregister",
    "addEventListener", "removeEventListener", "dispatch",
}
_CRUD_NAMES = {
    "get", "find", "save", "delete", "update", "create", "remove",
    "insert", "upsert", "fetch", "store", "put", "patch",
    "find_by", "find_all", "get_by", "get_all", "delete_by",
    "findById", "findAll", "getById", "getAll", "deleteById",
    "FindById", "FindAll", "GetById", "GetAll", "DeleteById",
}


def compute_signals(classes: list[dict], functions: list[dict]) -> dict:
    """Compute structural signals from extracted classes and functions."""
    signals = _empty_signals()
    all_method_names: set[str] = set()
    all_class_names = {c["name"] for c in classes}

    for cls in classes:
        cls_name = cls["name"]
        bases = set(cls.get("bases", []))
        methods = cls.get("methods", [])
        fields = cls.get("fields", [])
        method_names = {m["name"] for m in methods}
        all_method_names.update(method_names)

        # --- Singleton signals ---
        for m in methods:
            name_lower = m["name"].lower()
            mods = set(m.get("modifiers", []))
            # Private constructor
            if name_lower in ("__init__", "__new__") and "private" in mods:
                signals["has_private_constructor"] = True
            if m["name"] == "__new__":
                signals["has_private_constructor"] = True
            # getInstance method
            if name_lower in _SINGLETON_METHOD_NAMES:
                signals["has_get_instance_method"] = True
            if "static" in mods and name_lower in _SINGLETON_METHOD_NAMES:
                signals["has_get_instance_method"] = True

        for f in fields:
            f_type = f.get("type", "")
            mods = set(f.get("modifiers", []))
            # Static field of own type
            if f_type == cls_name or f_type in bases:
                if "static" in mods or "class_var" in mods:
                    signals["has_static_instance_field"] = True
            # Also check _instance pattern
            if f["name"].lower() in ("_instance", "instance", "__instance"):
                signals["has_static_instance_field"] = True

        # --- Factory signals ---
        for m in methods:
            name_lower = m["name"].lower()
            if any(name_lower.startswith(p) for p in _CREATE_PREFIXES):
                signals["has_create_methods"] = True
            if "static" in set(m.get("modifiers", [])) and any(
                name_lower.startswith(p) for p in _CREATE_PREFIXES
            ):
                signals["has_create_methods"] = True

        # --- Observer signals ---
        for m in methods:
            if m["name"].lower() in _OBSERVER_NAMES or m["name"] in _OBSERVER_NAMES:
                signals["has_subscribe_notify"] = True

        # --- Builder signals ---
        for m in methods:
            if m["name"].lower() == "build":
                signals["has_build_method"] = True
            mods = set(m.get("modifiers", []))
            if "returns_self" in mods:
                signals["has_fluent_api"] = True

        # --- Repository / CRUD signals ---
        for m in methods:
            name_lower = m["name"].lower()
            if name_lower in _CRUD_NAMES or m["name"] in _CRUD_NAMES:
                signals["has_crud_methods"] = True
            # Also check prefixes: findBy*, getBy*, deleteBy*
            if any(name_lower.startswith(p) for p in (
                "find_by", "get_by", "delete_by", "findby", "getby", "deleteby"
            )):
                signals["has_crud_methods"] = True

        # --- Strategy / Delegation signals ---
        # Constructor stores an interface/abstract param and methods reference it
        constructor_params = []
        for m in methods:
            if m["name"].lower() in ("__init__", cls_name.lower(), "constructor"):
                constructor_params = m.get("params", [])
                break

        field_types = {f.get("type", "") for f in fields}
        field_names = {f["name"] for f in fields}

        # Check if constructor params match field types (delegation pattern)
        for param in constructor_params:
            param_name = param.split(":")[0].strip().lstrip("_")
            if param_name in ("self", "this", "cls"):
                continue
            # Check if a field stores this param (by name match)
            for f in fields:
                f_name_clean = f["name"].lstrip("_")
                if f_name_clean == param_name or f_name_clean == param_name.lower():
                    # Field stores a constructor param — potential delegation
                    signals["has_delegation_pattern"] = True

        # --- Decorator / Same-type wrapping ---
        for param in constructor_params:
            param_type = ""
            if ":" in param:
                param_type = param.split(":", 1)[1].strip()
            param_name = param.split(":")[0].strip().lstrip("_")
            if param_name in ("self", "this", "cls"):
                continue
            # Check if param type matches a base class or the class itself
            if param_type and (param_type in bases or param_type == cls_name):
                signals["has_same_type_wrapping"] = True
            # Or check field type matches base
            for f in fields:
                if f.get("type", "") in bases and bases:
                    signals["has_same_type_wrapping"] = True

    # Also check top-level functions for factory/create patterns
    for fn in functions:
        name_lower = fn["name"].lower()
        if any(name_lower.startswith(p) for p in _CREATE_PREFIXES):
            signals["has_create_methods"] = True

    # --- Command signals ---
    for cls in classes:
        method_names_lower = {m["name"].lower() for m in cls.get("methods", [])}
        if "execute" in method_names_lower and any(
            n in method_names_lower for n in ("undo", "redo", "unexecute", "rollback")
        ):
            signals["has_execute_undo"] = True

    # --- Template Method signals ---
    _ABSTRACT_BASES = {"ABC", "ABCMeta"}
    for cls in classes:
        bases = set(cls.get("bases", []))
        methods = cls.get("methods", [])
        is_abstract_class = bool(bases & _ABSTRACT_BASES) or any(
            "Abstract" in b or "Base" in b for b in bases
        )
        abstract_methods = [m for m in methods if "abstract" in m.get("modifiers", [])]
        concrete_methods = [
            m for m in methods
            if "abstract" not in m.get("modifiers", [])
            and m["name"] not in ("__init__", "__new__", "constructor")
        ]
        if abstract_methods and concrete_methods:
            signals["has_abstract_template_steps"] = True
        elif is_abstract_class and len(methods) >= 2 and concrete_methods:
            signals["has_abstract_template_steps"] = True

    return signals


# ===========================================================================
# PYTHON EXTRACTOR (AST-based)
# ===========================================================================

class _PyClassVisitor(ast.NodeVisitor):
    """Extract class structure from Python AST."""

    def __init__(self, source_lines: list[str]) -> None:
        self.classes: list[dict] = []
        self.functions: list[dict] = []
        self._source_lines = source_lines

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        bases = []
        for base in node.bases:
            if isinstance(base, ast.Name):
                bases.append(base.id)
            elif isinstance(base, ast.Attribute):
                bases.append(self._attr_to_str(base))

        methods: list[dict] = []
        fields: list[dict] = []
        seen_fields: set[str] = set()

        # Class-level assignments (class variables)
        for item in node.body:
            if isinstance(item, (ast.Assign, ast.AnnAssign)):
                self._extract_class_var(item, node.name, fields, seen_fields)

        for item in node.body:
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                method_info = self._extract_method(item, node.name)
                methods.append(method_info)

                # Extract fields from __init__
                if item.name == "__init__":
                    self._extract_init_fields(item, fields, seen_fields)

        self.classes.append({
            "name": node.name,
            "bases": bases,
            "methods": methods,
            "fields": fields,
        })
        # Don't recurse into nested classes
        # self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        # Only capture top-level functions (not methods inside classes)
        # This method is called for module-level FunctionDef only because
        # we don't call generic_visit inside visit_ClassDef
        self.functions.append(self._extract_function(node))

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self.functions.append(self._extract_function(node))

    def _extract_method(self, node: ast.FunctionDef | ast.AsyncFunctionDef,
                        class_name: str) -> dict:
        params = []
        for arg in node.args.args:
            param_str = arg.arg
            if arg.annotation:
                ann = self._annotation_to_str(arg.annotation)
                if ann:
                    param_str += f": {ann}"
            params.append(param_str)

        modifiers = []
        for dec in node.decorator_list:
            if isinstance(dec, ast.Name):
                if dec.id == "staticmethod":
                    modifiers.append("static")
                elif dec.id == "classmethod":
                    modifiers.append("classmethod")
                elif dec.id == "property":
                    modifiers.append("property")
                elif dec.id == "abstractmethod":
                    modifiers.append("abstract")
            elif isinstance(dec, ast.Attribute) and dec.attr == "setter":
                modifiers.append("property-setter")

        if node.name.startswith("__") and not node.name.endswith("__"):
            modifiers.append("private")
        elif node.name.startswith("_"):
            modifiers.append("private")

        # Check if method returns self (fluent API)
        if self._returns_self(node):
            modifiers.append("returns_self")

        method_loc = 0
        if hasattr(node, "end_lineno") and node.end_lineno and node.lineno:
            method_loc = node.end_lineno - node.lineno + 1

        return {
            "name": node.name,
            "params": params,
            "modifiers": modifiers,
            "line": node.lineno,
            "loc": method_loc,
        }

    def _extract_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> dict:
        params = []
        for arg in node.args.args:
            param_str = arg.arg
            if arg.annotation:
                ann = self._annotation_to_str(arg.annotation)
                if ann:
                    param_str += f": {ann}"
            params.append(param_str)

        modifiers = []
        if node.name.startswith("_"):
            modifiers.append("private")

        func_loc = 0
        if hasattr(node, "end_lineno") and node.end_lineno and node.lineno:
            func_loc = node.end_lineno - node.lineno + 1

        return {
            "name": node.name,
            "params": params,
            "modifiers": modifiers,
            "line": node.lineno,
            "loc": func_loc,
        }

    def _extract_init_fields(self, node: ast.FunctionDef,
                             fields: list[dict], seen: set[str]) -> None:
        """Extract self.x = ... assignments from __init__."""
        for child in ast.walk(node):
            if isinstance(child, ast.Assign):
                for target in child.targets:
                    if (isinstance(target, ast.Attribute)
                            and isinstance(target.value, ast.Name)
                            and target.value.id == "self"):
                        fname = target.attr
                        if fname not in seen:
                            seen.add(fname)
                            mods = []
                            if fname.startswith("__") and not fname.endswith("__"):
                                mods.append("private")
                            elif fname.startswith("_"):
                                mods.append("private")
                            fields.append({
                                "name": fname,
                                "type": self._infer_field_type(child.value),
                                "modifiers": mods,
                            })
            elif isinstance(child, ast.AnnAssign):
                if (isinstance(child.target, ast.Attribute)
                        and isinstance(child.target.value, ast.Name)
                        and child.target.value.id == "self"):
                    fname = child.target.attr
                    if fname not in seen:
                        seen.add(fname)
                        mods = []
                        if fname.startswith("__") and not fname.endswith("__"):
                            mods.append("private")
                        elif fname.startswith("_"):
                            mods.append("private")
                        ftype = self._annotation_to_str(child.annotation) if child.annotation else ""
                        fields.append({
                            "name": fname,
                            "type": ftype,
                            "modifiers": mods,
                        })

    def _extract_class_var(self, node: ast.Assign | ast.AnnAssign,
                           class_name: str, fields: list[dict],
                           seen: set[str]) -> None:
        """Extract class-level variable assignments."""
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            fname = node.target.id
            if fname not in seen:
                seen.add(fname)
                ftype = self._annotation_to_str(node.annotation) if node.annotation else ""
                mods = ["class_var"]
                if fname.startswith("_"):
                    mods.append("private")
                # Check if type matches class name (singleton pattern)
                fields.append({
                    "name": fname,
                    "type": ftype,
                    "modifiers": mods,
                })
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    fname = target.id
                    if fname not in seen:
                        seen.add(fname)
                        mods = ["class_var"]
                        if fname.startswith("_"):
                            mods.append("private")
                        fields.append({
                            "name": fname,
                            "type": self._infer_field_type(node.value),
                            "modifiers": mods,
                        })

    def _returns_self(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
        """Check if a method returns self."""
        for child in ast.walk(node):
            if isinstance(child, ast.Return) and child.value:
                if isinstance(child.value, ast.Name) and child.value.id == "self":
                    return True
        return False

    def _infer_field_type(self, value_node: ast.expr) -> str:
        """Try to infer the type from a value node."""
        if isinstance(value_node, ast.Constant):
            if value_node.value is None:
                return ""
            return type(value_node.value).__name__
        elif isinstance(value_node, ast.Name):
            return value_node.id
        elif isinstance(value_node, ast.Call):
            if isinstance(value_node.func, ast.Name):
                return value_node.func.id
            elif isinstance(value_node.func, ast.Attribute):
                return self._attr_to_str(value_node.func)
        elif isinstance(value_node, ast.List):
            return "list"
        elif isinstance(value_node, ast.Dict):
            return "dict"
        elif isinstance(value_node, ast.Set):
            return "set"
        return ""

    def _annotation_to_str(self, node: ast.expr) -> str:
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return self._attr_to_str(node)
        elif isinstance(node, ast.Constant):
            return str(node.value)
        elif isinstance(node, ast.Subscript):
            base = self._annotation_to_str(node.value)
            return base
        return ""

    def _attr_to_str(self, node: ast.Attribute) -> str:
        if isinstance(node.value, ast.Name):
            return f"{node.value.id}.{node.attr}"
        elif isinstance(node.value, ast.Attribute):
            return f"{self._attr_to_str(node.value)}.{node.attr}"
        return node.attr


def extract_python(source_path: Path) -> dict:
    """Extract class structure from Python using AST."""
    try:
        text = source_path.read_text(encoding="utf-8", errors="replace")
        tree = ast.parse(text)
    except SyntaxError as e:
        print(f"Warning: AST parse failed for {source_path}: {e}", file=sys.stderr)
        return _empty_extraction()

    lines = text.splitlines()
    visitor = _PyClassVisitor(lines)
    visitor.visit(tree)

    classes = visitor.classes
    functions = visitor.functions
    metrics = compute_metrics(classes, functions, len(lines))
    signals = compute_signals(classes, functions)

    return {
        "classes": classes,
        "functions": functions,
        "metrics": metrics,
        "structural_signals": signals,
        "parse_method": "ast",
    }


# ===========================================================================
# JAVA EXTRACTOR (regex-based)
# ===========================================================================

# Class/interface/enum/record with extends/implements
_JAVA_TYPE_DECL = re.compile(
    r"(?:(?:public|protected|private|abstract|static|final)\s+)*"
    r"(?:class|interface|enum|record)\s+(\w+)"
    r"(?:\s+extends\s+(\w+))?"
    r"(?:\s+implements\s+([\w,\s]+))?",
)

# Method: modifiers ReturnType methodName(params)
_JAVA_METHOD = re.compile(
    r"^\s*((?:(?:public|protected|private|static|final|abstract|synchronized|native|default)\s+)+)"
    r"([\w<>\[\],?\s]+?)\s+(\w+)\s*\(([^)]*)\)\s*(?:throws\s+[\w,\s]+)?\s*[{;]",
    re.MULTILINE,
)

# Field: modifiers Type fieldName;
_JAVA_FIELD = re.compile(
    r"^\s*((?:(?:public|protected|private|static|final|volatile|transient)\s+)+)"
    r"([\w<>\[\],?\s]+?)\s+(\w+)\s*[;=]",
    re.MULTILINE,
)


def extract_java(source_path: Path) -> dict:
    """Extract class structure from Java using regex."""
    text = source_path.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()
    classes: list[dict] = []
    functions: list[dict] = []

    # Find all type declarations
    for m in _JAVA_TYPE_DECL.finditer(text):
        cls_name = m.group(1)
        extends = m.group(2) or ""
        implements_raw = m.group(3) or ""
        bases = []
        if extends:
            bases.append(extends)
        if implements_raw:
            bases.extend(i.strip() for i in implements_raw.split(",") if i.strip())

        methods: list[dict] = []
        fields: list[dict] = []

        # Find methods
        for mm in _JAVA_METHOD.finditer(text):
            mods_str = mm.group(1).strip()
            return_type = mm.group(2).strip()
            method_name = mm.group(3)
            params_raw = mm.group(4).strip()

            if method_name in ("if", "while", "for", "switch", "catch"):
                continue

            modifiers = []
            if "private" in mods_str:
                modifiers.append("private")
            if "static" in mods_str:
                modifiers.append("static")
            if "abstract" in mods_str:
                modifiers.append("abstract")
            if "public" in mods_str:
                modifiers.append("public")

            # Check if this is a constructor
            if method_name == cls_name:
                modifiers.append("constructor")

            params = [p.strip() for p in params_raw.split(",") if p.strip()] if params_raw else []

            methods.append({
                "name": method_name,
                "params": params,
                "modifiers": modifiers,
                "line": text[:mm.start()].count("\n") + 1,
                "loc": 0,
            })

        # Find fields
        for fm in _JAVA_FIELD.finditer(text):
            mods_str = fm.group(1).strip()
            field_type = fm.group(2).strip()
            field_name = fm.group(3)

            modifiers = []
            if "private" in mods_str:
                modifiers.append("private")
            if "static" in mods_str:
                modifiers.append("static")
            if "final" in mods_str:
                modifiers.append("final")

            fields.append({
                "name": field_name,
                "type": field_type,
                "modifiers": modifiers,
            })

        classes.append({
            "name": cls_name,
            "bases": bases,
            "methods": methods,
            "fields": fields,
        })

    metrics = compute_metrics(classes, functions, len(lines))
    signals = compute_signals(classes, functions)

    return {
        "classes": classes,
        "functions": functions,
        "metrics": metrics,
        "structural_signals": signals,
        "parse_method": "java-regex",
    }


# ===========================================================================
# JAVASCRIPT / TYPESCRIPT EXTRACTOR (regex-based)
# ===========================================================================

# class Name extends Base {
_JS_CLASS = re.compile(
    r"(?:export\s+(?:default\s+)?)?class\s+(\w+)"
    r"(?:\s+extends\s+(\w+))?"
    r"(?:\s+implements\s+([\w,\s]+))?",
)

# Method inside class: name(params) { or async name(params) {
_JS_METHOD = re.compile(
    r"^\s*(?:(static|async|get|set|private|protected|public)\s+)*"
    r"(?:(async)\s+)?(\w+)\s*\(([^)]*)\)\s*[{:]",
    re.MULTILINE,
)

# Top-level function: function name( or export function name( or const name = (
_JS_FUNC = re.compile(
    r"(?:export\s+(?:default\s+)?)?(?:async\s+)?function\s+(\w+)\s*\(",
)

# Arrow or const function: const name = (...) => or const name = function(
_JS_CONST_FUNC = re.compile(
    r"(?:export\s+)?(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?(?:\([^)]*\)\s*=>|function)",
)


def extract_js_ts(source_path: Path) -> dict:
    """Extract class structure from JS/TS using regex."""
    text = source_path.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()
    classes: list[dict] = []
    functions: list[dict] = []

    for m in _JS_CLASS.finditer(text):
        cls_name = m.group(1)
        extends = m.group(2) or ""
        implements_raw = m.group(3) or ""
        bases = []
        if extends:
            bases.append(extends)
        if implements_raw:
            bases.extend(i.strip() for i in implements_raw.split(",") if i.strip())

        # Find the class body region (approximate)
        class_start = m.end()
        brace_depth = 0
        class_end = len(text)
        found_open = False
        for i in range(class_start, len(text)):
            if text[i] == "{":
                brace_depth += 1
                found_open = True
            elif text[i] == "}":
                brace_depth -= 1
                if found_open and brace_depth == 0:
                    class_end = i
                    break

        class_body = text[class_start:class_end]
        methods: list[dict] = []
        fields: list[dict] = []

        for mm in _JS_METHOD.finditer(class_body):
            mod1 = mm.group(1) or ""
            mod2 = mm.group(2) or ""
            method_name = mm.group(3)
            params_raw = mm.group(4).strip()

            modifiers = []
            for mod in (mod1, mod2):
                if mod in ("static", "async", "get", "set", "private", "protected", "public", "abstract"):
                    modifiers.append(mod)

            if method_name == "constructor":
                modifiers.append("constructor")
                # Extract constructor params as potential fields
                if params_raw:
                    for p in params_raw.split(","):
                        p = p.strip()
                        if not p:
                            continue
                        parts = p.split(":")
                        p_name = parts[0].strip().lstrip("_")
                        p_type = parts[1].strip() if len(parts) > 1 else ""
                        # Skip if it's a visibility modifier param (TS)
                        for vis in ("private", "protected", "public", "readonly"):
                            p_name = p_name.replace(vis, "").strip()
                        if p_name:
                            fields.append({
                                "name": p_name,
                                "type": p_type,
                                "modifiers": [],
                            })

            # Check if method returns this (fluent API)
            # Simple heuristic: look for "return this" in method body
            method_start = mm.end()
            method_brace = 0
            method_end_pos = method_start
            for i in range(method_start, len(class_body)):
                if class_body[i] == "{":
                    method_brace += 1
                elif class_body[i] == "}":
                    method_brace -= 1
                    if method_brace == 0:
                        method_end_pos = i
                        break
            method_body = class_body[method_start:method_end_pos]
            if "return this" in method_body:
                modifiers.append("returns_self")

            method_loc = max(1, class_body[method_start:method_end_pos].count("\n") + 1)
            params = [p.strip() for p in params_raw.split(",") if p.strip()] if params_raw else []
            methods.append({
                "name": method_name,
                "params": params,
                "modifiers": modifiers,
                "line": text[:class_start + mm.start()].count("\n") + 1,
                "loc": method_loc,
            })

        classes.append({
            "name": cls_name,
            "bases": bases,
            "methods": methods,
            "fields": fields,
        })

    def _find_js_func_loc(start_pos: int) -> int:
        open_brace = text.find("{", start_pos)
        if open_brace == -1:
            return 1
        brace_depth = 0
        for i in range(open_brace, len(text)):
            if text[i] == "{":
                brace_depth += 1
            elif text[i] == "}":
                brace_depth -= 1
                if brace_depth == 0:
                    return max(1, text[open_brace:i].count("\n") + 1)
        return 1

    # Top-level functions
    for m in _JS_FUNC.finditer(text):
        fn_loc = _find_js_func_loc(m.end())
        functions.append({
            "name": m.group(1),
            "params": [],
            "modifiers": [],
            "line": text[:m.start()].count("\n") + 1,
            "loc": fn_loc,
        })

    for m in _JS_CONST_FUNC.finditer(text):
        fn_name = m.group(1)
        if fn_name not in {f["name"] for f in functions}:
            fn_loc = _find_js_func_loc(m.end())
            functions.append({
                "name": fn_name,
                "params": [],
                "modifiers": [],
                "line": text[:m.start()].count("\n") + 1,
                "loc": fn_loc,
            })

    metrics = compute_metrics(classes, functions, len(lines))
    signals = compute_signals(classes, functions)

    # Detect Facade pattern in JS/TS: Module predominantly re-exporting multiple internal sub-modules
    reexport_matches = len(re.findall(r"export\s+(\*|{[^}]+})\s+from\s+['\"][^'\"]+['\"]", text))
    if reexport_matches >= 2:
        signals["has_facade_pattern"] = True

    return {
        "classes": classes,
        "functions": functions,
        "metrics": metrics,
        "structural_signals": signals,
        "parse_method": "js-regex",
    }


# ===========================================================================
# GO EXTRACTOR (regex-based)
# ===========================================================================

# type Name struct {
_GO_STRUCT = re.compile(r"^type\s+(\w+)\s+struct\s*\{", re.MULTILINE)

# type Name interface {
_GO_INTERFACE = re.compile(r"^type\s+(\w+)\s+interface\s*\{", re.MULTILINE)

# func (r *Type) Name(params) returns {
_GO_METHOD = re.compile(
    r"^func\s+\(\s*\w+\s+\*?(\w+)\s*\)\s+(\w+)\s*\(([^)]*)\)",
    re.MULTILINE,
)

# func Name(params) returns {
_GO_FUNC = re.compile(
    r"^func\s+(\w+)\s*\(([^)]*)\)",
    re.MULTILINE,
)

# Struct field: Name Type (inside struct body)
_GO_FIELD = re.compile(r"^\s+(\w+)\s+([\w.*\[\]]+)", re.MULTILINE)


def extract_go(source_path: Path) -> dict:
    """Extract class structure from Go using regex."""
    text = source_path.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()
    classes: list[dict] = []
    functions: list[dict] = []

    # Structs become "classes"
    for m in _GO_STRUCT.finditer(text):
        struct_name = m.group(1)
        # Find struct body
        body_start = m.end()
        brace_depth = 1
        body_end = body_start
        for i in range(body_start, len(text)):
            if text[i] == "{":
                brace_depth += 1
            elif text[i] == "}":
                brace_depth -= 1
                if brace_depth == 0:
                    body_end = i
                    break

        struct_body = text[body_start:body_end]
        fields: list[dict] = []
        bases: list[str] = []

        for fm in _GO_FIELD.finditer(struct_body):
            field_name = fm.group(1)
            field_type = fm.group(2)
            # Embedded types act as "bases"
            if field_name[0].isupper() and field_type == "":
                bases.append(field_name)
            else:
                fields.append({
                    "name": field_name,
                    "type": field_type.lstrip("*"),
                    "modifiers": [],
                })

        # Check for embedded types (single word on a line, no type following)
        for line in struct_body.splitlines():
            stripped = line.strip()
            if re.match(r"^\*?([A-Z]\w+)$", stripped):
                embedded = stripped.lstrip("*")
                if embedded not in bases:
                    bases.append(embedded)

        # Find methods for this struct
        methods: list[dict] = []
        for mm in _GO_METHOD.finditer(text):
            if mm.group(1) == struct_name:
                method_name = mm.group(2)
                params_raw = mm.group(3).strip()
                params = [p.strip() for p in params_raw.split(",") if p.strip()] if params_raw else []
                modifiers = []
                if method_name[0].islower():
                    modifiers.append("private")
                methods.append({
                    "name": method_name,
                    "params": params,
                    "modifiers": modifiers,
                    "line": text[:mm.start()].count("\n") + 1,
                    "loc": 0,
                })

        classes.append({
            "name": struct_name,
            "bases": bases,
            "methods": methods,
            "fields": fields,
        })

    # Top-level functions (not methods)
    method_starts = {mm.start() for mm in _GO_METHOD.finditer(text)}
    for m in _GO_FUNC.finditer(text):
        if m.start() not in method_starts:
            fn_name = m.group(1)
            params_raw = m.group(2).strip()
            params = [p.strip() for p in params_raw.split(",") if p.strip()] if params_raw else []
            modifiers = []
            if fn_name[0].islower():
                modifiers.append("private")
            functions.append({
                "name": fn_name,
                "params": params,
                "modifiers": modifiers,
                "line": text[:m.start()].count("\n") + 1,
                "loc": 0,
            })

    metrics = compute_metrics(classes, functions, len(lines))
    signals = compute_signals(classes, functions)

    return {
        "classes": classes,
        "functions": functions,
        "metrics": metrics,
        "structural_signals": signals,
        "parse_method": "go-regex",
    }


# ===========================================================================
# C# EXTRACTOR (regex-based)
# ===========================================================================

# class/interface/struct Name : Base, IInterface
_CS_TYPE_DECL = re.compile(
    r"(?:(?:public|protected|private|internal|abstract|sealed|static|partial)\s+)*"
    r"(?:class|interface|struct|record)\s+(\w+)"
    r"(?:\s*:\s*([\w\s,<>.]+))?",
)

# Method: modifiers ReturnType Name(params) or async Task<T> Name(params)
_CS_METHOD = re.compile(
    r"^\s*((?:(?:public|protected|private|internal|static|virtual|override|abstract|async|sealed|new)\s+)+)"
    r"([\w<>\[\],?\s]+?)\s+(\w+)\s*\(([^)]*)\)\s*",
    re.MULTILINE,
)

# Property: modifiers Type Name { get; set; }
_CS_PROPERTY = re.compile(
    r"^\s*((?:(?:public|protected|private|internal|static|virtual|override|abstract)\s+)+)"
    r"([\w<>\[\],?\s]+?)\s+(\w+)\s*\{",
    re.MULTILINE,
)

# Field: modifiers Type name;
_CS_FIELD = re.compile(
    r"^\s*((?:(?:public|protected|private|internal|static|readonly|const|volatile)\s+)+)"
    r"([\w<>\[\],?\s]+?)\s+(\w+)\s*[;=]",
    re.MULTILINE,
)

# event keyword
_CS_EVENT = re.compile(r"\bevent\s+(\w+(?:<[\w,\s<>]+>)?)\s+(\w+)\s*;", re.MULTILINE)


def extract_csharp(source_path: Path) -> dict:
    """Extract class structure from C# using regex."""
    text = source_path.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()
    classes: list[dict] = []
    functions: list[dict] = []

    for m in _CS_TYPE_DECL.finditer(text):
        cls_name = m.group(1)
        bases_raw = m.group(2) or ""
        bases = [b.strip() for b in bases_raw.split(",") if b.strip()] if bases_raw else []
        # Clean generic params from base names
        bases = [re.sub(r"<.*>", "", b).strip() for b in bases]

        methods: list[dict] = []
        fields: list[dict] = []

        for mm in _CS_METHOD.finditer(text):
            mods_str = mm.group(1).strip()
            return_type = mm.group(2).strip()
            method_name = mm.group(3)
            params_raw = mm.group(4).strip()

            modifiers = []
            if "private" in mods_str:
                modifiers.append("private")
            if "static" in mods_str:
                modifiers.append("static")
            if "abstract" in mods_str:
                modifiers.append("abstract")
            if "virtual" in mods_str:
                modifiers.append("virtual")
            if "override" in mods_str:
                modifiers.append("override")

            if method_name == cls_name:
                modifiers.append("constructor")

            params = [p.strip() for p in params_raw.split(",") if p.strip()] if params_raw else []
            methods.append({
                "name": method_name,
                "params": params,
                "modifiers": modifiers,
                "line": text[:mm.start()].count("\n") + 1,
                "loc": 0,
            })

        for fm in _CS_FIELD.finditer(text):
            mods_str = fm.group(1).strip()
            field_type = fm.group(2).strip()
            field_name = fm.group(3)
            modifiers = []
            if "private" in mods_str:
                modifiers.append("private")
            if "static" in mods_str:
                modifiers.append("static")
            if "readonly" in mods_str:
                modifiers.append("readonly")
            fields.append({
                "name": field_name,
                "type": field_type,
                "modifiers": modifiers,
            })

        # Check for event declarations (Observer pattern signal)
        for em in _CS_EVENT.finditer(text):
            fields.append({
                "name": em.group(2),
                "type": f"event {em.group(1)}",
                "modifiers": ["event"],
            })

        classes.append({
            "name": cls_name,
            "bases": bases,
            "methods": methods,
            "fields": fields,
        })

    metrics = compute_metrics(classes, functions, len(lines))
    signals = compute_signals(classes, functions)

    return {
        "classes": classes,
        "functions": functions,
        "metrics": metrics,
        "structural_signals": signals,
        "parse_method": "csharp-regex",
    }


# ===========================================================================
# FALLBACK EXTRACTOR (generic regex)
# ===========================================================================

_FALLBACK_CLASS = re.compile(
    r"^(?:(?:public|private|protected|export|abstract|static)\s+)*"
    r"class\s+(\w+)"
    r"(?:\s+(?:extends|inherits|<)\s+(\w+))?",
    re.MULTILINE,
)

_FALLBACK_FUNC = re.compile(
    r"^(?:(?:pub|fn|def|function|sub|proc|procedure|method|fun|func)\s+)(\w+)\s*\(",
    re.MULTILINE | re.IGNORECASE,
)


def extract_fallback(source_path: Path) -> dict:
    """Generic regex extraction for unsupported languages."""
    text = source_path.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()
    classes: list[dict] = []
    functions: list[dict] = []

    for m in _FALLBACK_CLASS.finditer(text):
        cls_name = m.group(1)
        bases = [m.group(2)] if m.group(2) else []
        classes.append({
            "name": cls_name,
            "bases": bases,
            "methods": [],
            "fields": [],
        })

    for m in _FALLBACK_FUNC.finditer(text):
        functions.append({
            "name": m.group(1),
            "params": [],
            "modifiers": [],
            "line": text[:m.start()].count("\n") + 1,
            "loc": 0,
        })

    metrics = compute_metrics(classes, functions, len(lines))
    signals = compute_signals(classes, functions)

    return {
        "classes": classes,
        "functions": functions,
        "metrics": metrics,
        "structural_signals": signals,
        "parse_method": "regex-fallback",
    }


# ===========================================================================
# Metrics computation
# ===========================================================================

def compute_metrics(classes: list[dict], functions: list[dict],
                    total_loc: int) -> dict:
    """Compute code metrics from extracted structure."""
    total_classes = len(classes)
    total_methods = sum(len(c.get("methods", [])) for c in classes)
    total_functions = len(functions)

    method_locs = []
    for cls in classes:
        for m in cls.get("methods", []):
            loc = m.get("loc", 0)
            if loc > 0:
                method_locs.append(loc)
    for fn in functions:
        loc = fn.get("loc", 0)
        if loc > 0:
            method_locs.append(loc)

    max_method_loc = max(method_locs) if method_locs else 0
    avg_method_loc = round(sum(method_locs) / len(method_locs), 1) if method_locs else 0.0

    return {
        "total_classes": total_classes,
        "total_methods": total_methods,
        "total_functions": total_functions,
        "total_loc": total_loc,
        "max_method_loc": max_method_loc,
        "avg_method_loc": avg_method_loc,
    }


# ===========================================================================
# Language dispatch
# ===========================================================================

def extract_structure(source_path: Path, language: str) -> dict:
    """Dispatch to the appropriate language extractor."""
    if language == "python":
        return extract_python(source_path)
    elif language == "java":
        return extract_java(source_path)
    elif language in ("javascript", "typescript"):
        return extract_js_ts(source_path)
    elif language == "go":
        return extract_go(source_path)
    elif language == "csharp":
        return extract_csharp(source_path)
    else:
        return extract_fallback(source_path)


# ===========================================================================
# Single-file extraction
# ===========================================================================

def extract_single_file(source_path: Path, force: bool) -> dict:
    """Extract patterns from a single file and return result dict."""
    source_path = source_path.resolve()

    suffix = source_path.suffix.lower()
    language = LANGUAGE_MAP.get(suffix, "unknown")

    repo_root = find_repo_root(source_path.parent)

    try:
        rel_source = source_path.relative_to(repo_root)
    except ValueError:
        rel_source = Path(source_path.name)
    rel_source_str = str(rel_source).replace("\\", "/")

    output_path = compute_output_path(repo_root, source_path)
    output_path_str = str(output_path.relative_to(repo_root)).replace("\\", "/")

    stale = force or is_stale(source_path, output_path)

    extraction = extract_structure(source_path, language)

    return {
        "source_path": rel_source_str,
        "language": language,
        "parse_method": extraction["parse_method"],
        "repo_root": str(repo_root).replace("\\", "/"),
        "output_path": output_path_str,
        "stale": stale,
        "classes": extraction["classes"],
        "functions": extraction["functions"],
        "metrics": extraction["metrics"],
        "structural_signals": extraction["structural_signals"],
    }


# ===========================================================================
# Repo-wide extraction (--all mode)
# ===========================================================================

def extract_all_files(force: bool) -> dict:
    """Extract patterns from all source files in the repo."""
    repo_root = find_repo_root(Path.cwd())
    source_files = scan_source_files(repo_root)

    results: list[dict] = []
    for rel_path in source_files:
        full_path = repo_root / rel_path
        if not full_path.is_file():
            continue

        try:
            result = extract_single_file(full_path, force)
            results.append(result)
        except Exception as e:
            print(f"Warning: failed to extract {rel_path}: {e}", file=sys.stderr)

    index_output = str((repo_root / OUTPUT_DIR / "_index.md")).replace("\\", "/")

    return {
        "repo_root": str(repo_root).replace("\\", "/"),
        "index_output_path": f"{OUTPUT_DIR}/_index.md",
        "total_files": len(results),
        "stale_files": sum(1 for r in results if r["stale"]),
        "files": results,
    }


# ===========================================================================
# Main
# ===========================================================================

def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Extract structural patterns (classes, methods, fields, signals) "
            "from source files for design pattern detection."
        )
    )
    parser.add_argument(
        "file_path",
        nargs="?",
        help="Path to the source file to analyze (omit for --all mode)",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Scan all source files in the repo",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force regeneration even if analysis is already up to date",
    )
    args = parser.parse_args()

    if args.all:
        result = extract_all_files(args.force)
        print(json.dumps(result, indent=2))
        return

    if not args.file_path:
        print("Error: provide a file path or use --all", file=sys.stderr)
        sys.exit(1)

    source_path = Path(args.file_path)

    if not source_path.exists():
        print(f"Error: file not found: {args.file_path}", file=sys.stderr)
        sys.exit(1)

    if not source_path.is_file():
        print(f"Error: not a file: {args.file_path}", file=sys.stderr)
        sys.exit(1)

    result = extract_single_file(source_path, args.force)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
