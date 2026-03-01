#!/usr/bin/env python3
"""
parse-test-refs.py

Multi-language test reference extractor for the scan-halucinated-tests skill.

Supports:
  .py              → Python    (AST-based, most accurate)
  .java            → Java      (regex-based, JUnit 4/5 + Mockito)
  .cs              → C#        (regex-based, xUnit/NUnit/MSTest + Moq)
  .js .jsx .ts .tsx → JavaScript/TypeScript (regex-based, Jest/Vitest)

Auto-detects language from file extension. Outputs a uniform JSON shape
regardless of language, so the haiku subagent can use the same cross-
reference logic across all supported languages.

Output (stdout): single JSON object
Errors: stderr, exit 1 on detection/parse failure

Usage:
  .venv/Scripts/python .github/skills/scan-halucinated-tests/scripts/parse-test-refs.py <test-file>
  .venv/bin/python     .github/skills/scan-halucinated-tests/scripts/parse-test-refs.py <test-file>
"""

from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# Language detection
# ---------------------------------------------------------------------------

LANGUAGE_MAP: dict[str, str] = {
    ".py":   "python",
    ".java": "java",
    ".cs":   "csharp",
    ".js":   "javascript",
    ".jsx":  "javascript",
    ".ts":   "javascript",
    ".tsx":  "javascript",
}


def detect_language(path: Path) -> str | None:
    return LANGUAGE_MAP.get(path.suffix.lower())


# ---------------------------------------------------------------------------
# Shared utilities
# ---------------------------------------------------------------------------

def _line_of(source: str, pos: int) -> int:
    """Return 1-based line number for a character position in source."""
    return source.count("\n", 0, pos) + 1


def deduplicate_by(items: list[dict], key: str) -> list[dict]:
    """Remove duplicates by `key` field, keeping the first occurrence."""
    seen: set = set()
    result: list[dict] = []
    for item in items:
        val = item.get(key)
        if val not in seen:
            seen.add(val)
            result.append(item)
    return result


def _empty_result() -> dict:
    return {
        "imports": [],
        "symbol_calls": [],
        "mock_targets": [],
        "attribute_accesses": [],
        "exception_refs": [],
        "kwarg_calls": [],
        "constant_refs": [],
    }


# ---------------------------------------------------------------------------
# Source file inference — language-aware
# ---------------------------------------------------------------------------

_PY_TEST_CATEGORY_DIRS = frozenset({
    "unit", "integration", "functional", "e2e", "acceptance",
})

_JAVA_TEST_CATEGORY_DIRS = frozenset({
    "unit", "integration", "functional", "e2e", "acceptance",
    "component", "contract",
})

_CS_TEST_DIRS = frozenset({
    "tests", "test", "specs", "spec",
})

_JS_TEST_CATEGORY_DIRS = frozenset({
    "unit", "integration", "e2e", "spec", "specs",
})


def infer_source_path(test_path: Path, language: str) -> str:
    """
    Infer the source file path from the test file path, language-aware.
    Returns a relative path string (may not exist on disk).
    """
    parent_str = str(test_path.parent).replace("\\", "/").lstrip("./").rstrip("/")
    stem = test_path.stem
    suffix = test_path.suffix

    if language == "python":
        # Strip test_ prefix or _test suffix
        if stem.startswith("test_"):
            source_stem = stem[5:]
        elif stem.endswith("_test"):
            source_stem = stem[:-5]
        else:
            source_stem = stem
        source_name = source_stem + suffix

        if parent_str in ("tests", "test", ""):
            return f"src/{source_name}" if parent_str else source_name
        elif parent_str.startswith(("tests/", "test/")):
            sub = parent_str.split("/", 1)[1]
            parts = sub.split("/")
            filtered = [p for p in parts if p.lower() not in _PY_TEST_CATEGORY_DIRS]
            base = "/".join(filtered)
            return f"src/{base}/{source_name}" if base else f"src/{source_name}"
        else:
            return f"{parent_str}/{source_name}" if parent_str else source_name

    elif language == "java":
        # Maven/Gradle: src/test/java/com/example/AuthTest.java
        #             → src/main/java/com/example/Auth.java
        # Strip Test/Tests suffix from class name
        if stem.endswith("Tests"):
            source_stem = stem[:-5]
        elif stem.endswith("Test"):
            source_stem = stem[:-4]
        elif stem.startswith("Test"):
            source_stem = stem[4:]
        else:
            source_stem = stem
        source_name = source_stem + suffix

        # src/test/java/... → src/main/java/...
        if "src/test/java" in parent_str:
            return parent_str.replace("src/test/java", "src/main/java") + f"/{source_name}"
        # test/java/... → main/java/...
        if parent_str.startswith("test/java"):
            return parent_str.replace("test/java", "main/java", 1) + f"/{source_name}"
        # Flat or unknown — strip test dir, return with same package path
        parts = parent_str.split("/")
        filtered = [
            p for p in parts
            if p.lower() not in _JAVA_TEST_CATEGORY_DIRS
            and p.lower() not in ("test", "tests")
        ]
        if filtered and filtered != parts:
            return "/".join(filtered) + f"/{source_name}"
        return f"src/main/java/{source_name}" if parent_str else source_name

    elif language == "csharp":
        # Strip Tests/Test suffix from filename
        if stem.endswith("Tests"):
            source_stem = stem[:-5]
        elif stem.endswith("Test"):
            source_stem = stem[:-4]
        else:
            source_stem = stem
        source_name = source_stem + suffix

        # MyProject.Tests/ → src/ or MyProject/
        parts = parent_str.split("/")
        filtered = [
            p for p in parts
            if not any(t in p.lower() for t in ("test", "tests", "spec", "specs"))
        ]
        if filtered and filtered != parts:
            base = "/".join(filtered)
            return f"{base}/{source_name}" if base else source_name
        return f"src/{source_name}" if parent_str else source_name

    elif language == "javascript":
        # Strip .test or .spec infix: auth.test.ts → auth.ts, auth.spec.js → auth.js
        # Also handles: __tests__/auth.ts → src/auth.ts
        for infix in (".test", ".spec"):
            if infix in stem:
                source_stem = stem.replace(infix, "")
                break
        else:
            source_stem = stem
        source_name = source_stem + suffix

        # __tests__/ directory → src/
        if "__tests__" in parent_str:
            cleaned = parent_str.replace("__tests__/", "").replace("/__tests__", "").replace("__tests__", "")
            cleaned = cleaned.strip("/")
            if cleaned:
                return f"src/{cleaned}/{source_name}"
            return f"src/{source_name}"
        if parent_str in ("tests", "test", "__tests__"):
            return f"src/{source_name}"
        if parent_str.startswith(("tests/", "test/")):
            sub = parent_str.split("/", 1)[1]
            parts = sub.split("/")
            filtered = [p for p in parts if p.lower() not in _JS_TEST_CATEGORY_DIRS]
            base = "/".join(filtered)
            return f"src/{base}/{source_name}" if base else f"src/{source_name}"
        # Same dir or src/X: keep the directory, just change filename
        return f"{parent_str}/{source_name}" if parent_str else source_name

    return str(test_path)  # fallback: unchanged


# ===========================================================================
# PYTHON PARSER (AST-based)
# ===========================================================================

def _node_to_str(node: ast.expr) -> str:
    """Convert a simple AST expression to a dotted string. Python 3.8 safe."""
    if isinstance(node, ast.Name):
        return node.id
    elif isinstance(node, ast.Attribute):
        obj = _node_to_str(node.value)
        return f"{obj}.{node.attr}" if obj else node.attr
    elif isinstance(node, ast.Constant):
        return repr(node.value)
    return "<complex>"


def _is_patch_func(f: ast.expr) -> bool:
    if isinstance(f, ast.Name) and f.id == "patch":
        return True
    if isinstance(f, ast.Attribute) and f.attr == "patch":
        return True
    return False


def _is_patch_object_func(f: ast.expr) -> bool:
    if not isinstance(f, ast.Attribute) or f.attr != "object":
        return False
    v = f.value
    if isinstance(v, ast.Name) and v.id == "patch":
        return True
    if isinstance(v, ast.Attribute) and v.attr == "patch":
        return True
    return False


def _is_pytest_raises(f: ast.expr) -> bool:
    return (
        isinstance(f, ast.Attribute)
        and f.attr == "raises"
        and isinstance(f.value, ast.Name)
        and f.value.id == "pytest"
    )


_MOCK_ATTRS = frozenset({
    "called", "call_count", "call_args", "call_args_list",
    "return_value", "side_effect", "assert_called", "assert_called_once",
    "assert_called_with", "assert_called_once_with", "assert_any_call",
    "assert_not_called", "reset_mock", "mock_calls", "method_calls",
    "configure_mock",
})

_PY_BUILTINS = frozenset({
    "len", "str", "int", "float", "bool", "list", "dict", "set", "tuple",
    "type", "isinstance", "issubclass", "hasattr", "getattr", "setattr",
    "delattr", "vars", "dir", "id", "hash", "repr", "print", "open",
    "range", "enumerate", "zip", "map", "filter", "sorted", "reversed",
    "min", "max", "sum", "abs", "round", "any", "all", "next", "iter",
    "super", "object", "property", "classmethod", "staticmethod",
    "callable", "chr", "ord", "hex", "oct", "bin", "format", "eval",
    "exec", "compile", "input", "breakpoint",
    "True", "False", "None",
    "patch", "MagicMock", "Mock", "AsyncMock", "PropertyMock", "call",
    "TestCase", "setUp", "tearDown",
})


class _PyExtractor(ast.NodeVisitor):
    def __init__(self) -> None:
        self.imports: list[dict] = []
        self.symbol_calls: list[dict] = []
        self.mock_targets: list[dict] = []
        self.attribute_accesses: list[dict] = []
        self.exception_refs: list[dict] = []
        self.kwarg_calls: list[dict] = []
        self.constant_refs: list[dict] = []
        self._imported: set[str] = set()
        self._dec_patch_lines: set[int] = set()

    def visit_Import(self, node: ast.Import) -> None:
        for a in node.names:
            local = a.asname or a.name.split(".")[-1]
            self.imports.append({"module": a.name, "names": [local],
                                 "line": node.lineno, "import_style": "import"})
            self._imported.add(local)
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        mod = node.module or ""
        names = [a.name for a in node.names]
        self.imports.append({"module": mod, "names": names,
                              "line": node.lineno, "import_style": "from"})
        for a in node.names:
            self._imported.add(a.asname or a.name)
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._scan_decs(node.decorator_list)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._scan_decs(node.decorator_list)
        self.generic_visit(node)

    def _scan_decs(self, decs: list[ast.expr]) -> None:
        for dec in decs:
            if not isinstance(dec, ast.Call):
                continue
            f = dec.func
            if _is_patch_func(f):
                if dec.args and isinstance(dec.args[0], ast.Constant):
                    t = dec.args[0].value
                    if isinstance(t, str):
                        self.mock_targets.append(
                            {"target": t, "line": dec.lineno, "style": "decorator"})
                        self._dec_patch_lines.add(dec.lineno)
            elif _is_patch_object_func(f) and len(dec.args) >= 2:
                obj = _node_to_str(dec.args[0])
                meth = (dec.args[1].value if isinstance(dec.args[1], ast.Constant)
                        else _node_to_str(dec.args[1]))
                self.mock_targets.append(
                    {"target": f"{obj}.{meth}", "line": dec.lineno, "style": "patch.object"})
                self._dec_patch_lines.add(dec.lineno)

    def visit_Call(self, node: ast.Call) -> None:
        line = node.lineno
        f = node.func
        if _is_patch_func(f) and line not in self._dec_patch_lines:
            if node.args and isinstance(node.args[0], ast.Constant):
                t = node.args[0].value
                if isinstance(t, str):
                    self.mock_targets.append({"target": t, "line": line, "style": "inline"})
        elif _is_patch_object_func(f) and line not in self._dec_patch_lines:
            if len(node.args) >= 2:
                obj = _node_to_str(node.args[0])
                meth = (node.args[1].value if isinstance(node.args[1], ast.Constant)
                        else _node_to_str(node.args[1]))
                self.mock_targets.append(
                    {"target": f"{obj}.{meth}", "line": line, "style": "patch.object.inline"})
        elif _is_pytest_raises(f):
            if node.args:
                exc = _node_to_str(node.args[0])
                if exc and exc != "<complex>":
                    self.exception_refs.append({"name": exc, "line": line})
        else:
            name = obj = None
            style = "direct"
            if isinstance(f, ast.Name):
                name = f.id
            elif isinstance(f, ast.Attribute):
                name = f.attr
                obj = _node_to_str(f.value)
                style = "attribute"
            if name and name not in _PY_BUILTINS:
                entry: dict = {"name": name, "line": line, "call_style": style}
                if obj:
                    entry["object"] = obj
                self.symbol_calls.append(entry)
            if name and node.keywords:
                kwargs = [kw.arg for kw in node.keywords if kw.arg is not None]
                if kwargs:
                    self.kwarg_calls.append(
                        {"function": name, "kwargs": kwargs, "line": line})
        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute) -> None:
        if node.attr in _MOCK_ATTRS:
            self.generic_visit(node)
            return
        if node.attr.startswith("__") and node.attr.endswith("__"):
            self.generic_visit(node)
            return
        obj = _node_to_str(node.value)
        if obj and obj != "<complex>":
            self.attribute_accesses.append(
                {"object": obj, "attribute": node.attr, "line": node.lineno})
        self.generic_visit(node)

    def visit_Name(self, node: ast.Name) -> None:
        if (re.match(r"^[A-Z][A-Z0-9_]{2,}$", node.id)
                and node.id not in self._imported
                and node.id not in _PY_BUILTINS):
            self.constant_refs.append({"name": node.id, "line": node.lineno})
        self.generic_visit(node)


def parse_python(source: str, test_path: Path) -> tuple[dict, str | None]:
    """
    Parse a Python test file using AST. Returns (refs_dict, parse_error_or_None).
    """
    try:
        tree = ast.parse(source, filename=str(test_path))
    except SyntaxError as e:
        return _empty_result(), f"SyntaxError at line {e.lineno}: {e.msg}"

    ex = _PyExtractor()
    ex.visit(tree)
    return {
        "imports":            ex.imports,
        "symbol_calls":       ex.symbol_calls,
        "mock_targets":       deduplicate_by(ex.mock_targets, "target"),
        "attribute_accesses": ex.attribute_accesses,
        "exception_refs":     deduplicate_by(ex.exception_refs, "name"),
        "kwarg_calls":        ex.kwarg_calls,
        "constant_refs":      deduplicate_by(ex.constant_refs, "name"),
    }, None


# ===========================================================================
# JAVA PARSER (regex-based, JUnit 4/5 + Mockito/EasyMock)
# ===========================================================================

# Imports: import com.example.Auth; or import static com.example.Auth.method;
_JAVA_IMPORT    = re.compile(r"^\s*import\s+(static\s+)?([\w.]+)(?:\.\*)?\s*;", re.MULTILINE)
# Class instantiation: new ClassName( or new ClassName<
_JAVA_NEW       = re.compile(r"\bnew\s+([A-Z][A-Za-z0-9_]*)\s*[(<]")
# Static method / field call: ClassName.something(
_JAVA_STATIC_CALL = re.compile(r"\b([A-Z][A-Za-z0-9_]+)\.([a-zA-Z][A-Za-z0-9_]*)\s*\(")
# Mockito.mock(ClassName.class) or mock(ClassName.class)
_JAVA_MOCK_CALL = re.compile(r"\bmock\s*\(\s*([A-Z][A-Za-z0-9_<>]*?)\.class\s*\)")
# @Mock annotation field: @Mock private AuthService authService;
_JAVA_MOCK_FIELD = re.compile(
    r"@(?:Mock|Spy|InjectMocks|Captor)\b[^;]*?\s([A-Z][A-Za-z0-9_<>,\s]*?)\s+\w+\s*;",
    re.DOTALL)
# when(obj.method(...)) stubbing — extract method name
_JAVA_WHEN       = re.compile(r"\bwhen\s*\(\s*\w+\.([a-zA-Z][A-Za-z0-9_]*)\s*\(")
# doReturn/doThrow.when(obj).method()
_JAVA_DO_WHEN    = re.compile(
    r"\bdo(?:Return|Throw|Nothing|Answer|CallRealMethod)\s*\([^)]*\)"
    r"\.when\s*\([^)]+\)\.([a-zA-Z][A-Za-z0-9_]*)\s*\(")
# verify(obj[, ...]).method()
_JAVA_VERIFY     = re.compile(r"\bverify\s*\([^)]+\)\s*\.([a-zA-Z][A-Za-z0-9_]*)\s*\(")
# assertThrows(ExceptionClass.class, ...)
_JAVA_ASSERT_THROWS = re.compile(r"\bassertThrows\s*\(\s*([A-Z][A-Za-z0-9_]*)\.class")
# @Test(expected = ExceptionClass.class)
_JAVA_TEST_EXPECTED = re.compile(r"expected\s*=\s*([A-Z][A-Za-z0-9_]*)\.class")
# Constants: UPPER_CASE or UPPER_CASE_2 (min 3 chars to avoid single abbreviations)
_JAVA_CONST      = re.compile(r"\b([A-Z][A-Z0-9_]{2,})\b")
# Annotations to skip for symbol_calls (test framework annotations)
_JAVA_SKIP_CLASSES = frozenset({
    "Test", "Before", "After", "BeforeEach", "AfterEach", "BeforeAll", "AfterAll",
    "BeforeClass", "AfterClass", "RunWith", "ExtendWith", "DisplayName",
    "ParameterizedTest", "ValueSource", "CsvSource", "MethodSource", "Nested",
    "Disabled", "Tag", "Timeout", "Mock", "Spy", "InjectMocks", "Captor",
    "Override", "SuppressWarnings", "FunctionalInterface", "Deprecated",
    "Nullable", "NotNull", "NonNull",
    # JUnit assertion classes — not source symbols
    "Assertions", "Assert", "Mockito", "ArgumentMatchers",
    "ArgumentCaptor", "InOrder",
    # Java stdlib
    "String", "Integer", "Long", "Double", "Float", "Boolean", "Object",
    "List", "Map", "Set", "Optional", "Arrays", "Collections", "Stream",
    "System", "Math", "Thread", "Class", "Enum", "Number",
})


def parse_java(source: str, _test_path: Path) -> tuple[dict, str | None]:
    res = _empty_result()

    # Imports
    for m in _JAVA_IMPORT.finditer(source):
        is_static = bool(m.group(1))
        fqn = m.group(2)
        parts = fqn.split(".")
        class_name = parts[-1]
        package = ".".join(parts[:-1])
        res["imports"].append({
            "module": package or fqn,
            "names": [class_name],
            "line": _line_of(source, m.start()),
            "import_style": "static" if is_static else "import",
        })

    # @Mock field declarations
    for m in _JAVA_MOCK_FIELD.finditer(source):
        raw_type = m.group(1).strip()
        # Strip generic: List<X> → List
        type_name = raw_type.split("<")[0].strip()
        if type_name and type_name not in _JAVA_SKIP_CLASSES:
            res["mock_targets"].append({
                "target": type_name,
                "line": _line_of(source, m.start()),
                "style": "field-annotation",
            })

    # mock(ClassName.class)
    for m in _JAVA_MOCK_CALL.finditer(source):
        t = m.group(1).split("<")[0].strip()
        if t:
            res["mock_targets"].append({
                "target": t,
                "line": _line_of(source, m.start()),
                "style": "mock-call",
            })

    # when(obj.method(...))
    for m in _JAVA_WHEN.finditer(source):
        res["mock_targets"].append({
            "target": m.group(1),
            "line": _line_of(source, m.start()),
            "style": "when-stub",
        })

    # doReturn(...).when(obj).method()
    for m in _JAVA_DO_WHEN.finditer(source):
        res["mock_targets"].append({
            "target": m.group(1),
            "line": _line_of(source, m.start()),
            "style": "do-when-stub",
        })

    # verify(obj).method()
    for m in _JAVA_VERIFY.finditer(source):
        res["mock_targets"].append({
            "target": m.group(1),
            "line": _line_of(source, m.start()),
            "style": "verify",
        })

    res["mock_targets"] = deduplicate_by(res["mock_targets"], "target")

    # new ClassName(
    for m in _JAVA_NEW.finditer(source):
        cls = m.group(1)
        if cls not in _JAVA_SKIP_CLASSES:
            res["symbol_calls"].append({
                "name": cls,
                "line": _line_of(source, m.start()),
                "call_style": "new",
            })

    # ClassName.method(
    for m in _JAVA_STATIC_CALL.finditer(source):
        cls, method = m.group(1), m.group(2)
        if cls not in _JAVA_SKIP_CLASSES:
            res["symbol_calls"].append({
                "name": method,
                "object": cls,
                "line": _line_of(source, m.start()),
                "call_style": "static-or-instance",
            })

    # assertThrows
    for m in _JAVA_ASSERT_THROWS.finditer(source):
        res["exception_refs"].append({
            "name": m.group(1),
            "line": _line_of(source, m.start()),
        })

    # @Test(expected = ...)
    for m in _JAVA_TEST_EXPECTED.finditer(source):
        res["exception_refs"].append({
            "name": m.group(1),
            "line": _line_of(source, m.start()),
        })

    res["exception_refs"] = deduplicate_by(res["exception_refs"], "name")

    # Constants (UPPER_CASE)
    imported_names = {e["names"][0] for e in res["imports"]}
    for m in _JAVA_CONST.finditer(source):
        name = m.group(1)
        if name not in imported_names and name not in _JAVA_SKIP_CLASSES:
            res["constant_refs"].append({
                "name": name,
                "line": _line_of(source, m.start()),
            })

    res["constant_refs"] = deduplicate_by(res["constant_refs"], "name")
    return res, None


# ===========================================================================
# C# PARSER (regex-based, xUnit/NUnit/MSTest + Moq/NSubstitute)
# ===========================================================================

# using Namespace.Type; or using static Namespace.Type;
_CS_USING = re.compile(r"^\s*using\s+(static\s+)?([\w.]+)\s*;", re.MULTILINE)
# new TypeName( or new TypeName<T>(
_CS_NEW   = re.compile(r"\bnew\s+([A-Z][A-Za-z0-9_]*(?:\s*<[^>]+>)?)\s*[({]")
# Mock<IInterface> or Mock<ConcreteType>
_CS_MOCK_TYPE = re.compile(r"\bMock\s*<\s*([A-Z][A-Za-z0-9_.]*)\s*>")
# .Setup(x => x.Method or .Setup(x => x.Property
_CS_SETUP  = re.compile(r"\.Setup\s*\([^=]+=>\s*\w+\.([A-Za-z][A-Za-z0-9_]*)\s*[.(]")
# .Verify(x => x.Method
_CS_VERIFY = re.compile(r"\.Verify\s*\([^=]+=>\s*\w+\.([A-Za-z][A-Za-z0-9_]*)\s*[.(]")
# Assert.Throws<ExceptionType> or Assert.ThrowsAsync<ExceptionType>
_CS_ASSERT_THROWS = re.compile(r"\bAssert\.Throws(?:Async)?\s*<\s*([A-Z][A-Za-z0-9_.]*)\s*>")
# ClassName.Method( — static calls and instance calls on known types
_CS_TYPE_CALL = re.compile(r"\b([A-Z][A-Za-z0-9_]+)\.([A-Za-z][A-Za-z0-9_]*)\s*\(")
# Named arguments: methodName(paramName: value)
_CS_NAMED_ARG = re.compile(r"\b(\w+)\s*\((?:[^()]*\b([a-z][A-Za-z0-9_]*)\s*:[^,)]+)+\)")
# Constants: UPPER_CASE (min 3 chars)
_CS_CONST = re.compile(r"\b([A-Z][A-Z0-9_]{2,})\b")

_CS_SKIP_TYPES = frozenset({
    "Fact", "Theory", "Test", "TestMethod", "TestCase", "SetUp", "TearDown",
    "OneTimeSetUp", "OneTimeTearDown", "TestFixture", "TestClass",
    "ClassInitialize", "ClassCleanup", "TestInitialize", "TestCleanup",
    "InlineData", "MemberData", "ClassData", "Skip",
    "Mock", "It", "Times", "Moq", "NSubstitute",
    "Assert", "Xunit", "NUnit",
    "String", "Int32", "Int64", "Boolean", "Double", "Object",
    "List", "Dictionary", "Array", "Task", "Exception", "Type",
    "Guid", "DateTime", "TimeSpan", "Enum",
    "Console", "Math", "Convert", "Environment",
})


def parse_csharp(source: str, _test_path: Path) -> tuple[dict, str | None]:
    res = _empty_result()

    # Using statements
    for m in _CS_USING.finditer(source):
        is_static = bool(m.group(1))
        ns = m.group(2)
        parts = ns.split(".")
        type_name = parts[-1]
        namespace = ".".join(parts[:-1])
        res["imports"].append({
            "module": namespace or ns,
            "names": [type_name],
            "line": _line_of(source, m.start()),
            "import_style": "using-static" if is_static else "using",
        })

    # Mock<IType> declarations
    for m in _CS_MOCK_TYPE.finditer(source):
        t = m.group(1).strip()
        res["mock_targets"].append({
            "target": t,
            "line": _line_of(source, m.start()),
            "style": "mock-type",
        })

    # .Setup(x => x.Method)
    for m in _CS_SETUP.finditer(source):
        res["mock_targets"].append({
            "target": m.group(1),
            "line": _line_of(source, m.start()),
            "style": "setup",
        })

    # .Verify(x => x.Method)
    for m in _CS_VERIFY.finditer(source):
        res["mock_targets"].append({
            "target": m.group(1),
            "line": _line_of(source, m.start()),
            "style": "verify",
        })

    res["mock_targets"] = deduplicate_by(res["mock_targets"], "target")

    # Assert.Throws<ExceptionType>
    for m in _CS_ASSERT_THROWS.finditer(source):
        res["exception_refs"].append({
            "name": m.group(1),
            "line": _line_of(source, m.start()),
        })

    res["exception_refs"] = deduplicate_by(res["exception_refs"], "name")

    # new TypeName(
    for m in _CS_NEW.finditer(source):
        raw = m.group(1).strip()
        type_name = re.sub(r"\s*<.*", "", raw).strip()
        if type_name and type_name not in _CS_SKIP_TYPES:
            res["symbol_calls"].append({
                "name": type_name,
                "line": _line_of(source, m.start()),
                "call_style": "new",
            })

    # Type.Method(
    for m in _CS_TYPE_CALL.finditer(source):
        cls, method = m.group(1), m.group(2)
        if cls not in _CS_SKIP_TYPES:
            res["symbol_calls"].append({
                "name": method,
                "object": cls,
                "line": _line_of(source, m.start()),
                "call_style": "type-call",
            })

    # Named args: method(paramName: value)
    for m in _CS_NAMED_ARG.finditer(source):
        func = m.group(1)
        kwargs_raw = re.findall(r"\b([a-z][A-Za-z0-9_]*)\s*:", m.group(0))
        if func and kwargs_raw:
            res["kwarg_calls"].append({
                "function": func,
                "kwargs": kwargs_raw,
                "line": _line_of(source, m.start()),
            })

    # Constants
    imported_names = {e["names"][0] for e in res["imports"]}
    for m in _CS_CONST.finditer(source):
        name = m.group(1)
        if name not in imported_names and name not in _CS_SKIP_TYPES:
            res["constant_refs"].append({
                "name": name,
                "line": _line_of(source, m.start()),
            })

    res["constant_refs"] = deduplicate_by(res["constant_refs"], "name")
    return res, None


# ===========================================================================
# JAVASCRIPT / TYPESCRIPT PARSER (regex-based, Jest/Vitest)
# ===========================================================================

# import { A, B } from './module'
_JS_IMPORT_NAMED   = re.compile(r"\bimport\s+\{([^}]+)\}\s+from\s+['\"]([^'\"]+)['\"]")
# import Default from './module'
_JS_IMPORT_DEFAULT = re.compile(r"\bimport\s+(\w+)\s+from\s+['\"]([^'\"]+)['\"]")
# import * as ns from './module'
_JS_IMPORT_NS      = re.compile(r"\bimport\s+\*\s+as\s+(\w+)\s+from\s+['\"]([^'\"]+)['\"]")
# const { A, B } = require('./module')
_JS_REQ_DESTRUCT   = re.compile(r"\bconst\s+\{([^}]+)\}\s*=\s*require\s*\(['\"]([^'\"]+)['\"]\)")
# const mod = require('./module')
_JS_REQ_DEFAULT    = re.compile(r"\bconst\s+(\w+)\s*=\s*require\s*\(['\"]([^'\"]+)['\"]\)")
# jest.mock('./module') or vi.mock('./module')
_JS_MOCK_MODULE    = re.compile(r"\b(?:jest|vi)\.mock\s*\(['\"]([^'\"]+)['\"]")
# jest.spyOn(obj, 'method') or vi.spyOn(obj, 'method')
_JS_SPY_ON         = re.compile(r"\b(?:jest|vi)\.spyOn\s*\(\s*(\w+)\s*,\s*['\"]([^'\"]+)['\"]")
# .toThrow(ErrorClass) or .toThrowError(ErrorClass)
_JS_TO_THROW       = re.compile(r"\.toThrow(?:Error)?\s*\(\s*([A-Z][A-Za-z0-9_]*)\s*\)")
# new ClassName(
_JS_NEW            = re.compile(r"\bnew\s+([A-Z][A-Za-z0-9_]*)\s*\(")
# Regular function calls: funcName(  (lower camelCase)
_JS_FUNC_CALL      = re.compile(r"\b([a-z][A-Za-z0-9_]*)\s*\(")
# Constants: UPPER_CASE
_JS_CONST          = re.compile(r"\b([A-Z][A-Z0-9_]{2,})\b")

_JS_SKIP_FUNCS = frozenset({
    "describe", "it", "test", "expect", "beforeEach", "afterEach",
    "beforeAll", "afterAll", "fit", "xit", "xtest", "xdescribe",
    "fdescribe", "ftest",
    # jest/vitest
    "jest", "vi", "mock", "fn", "spyOn", "clearAllMocks", "resetAllMocks",
    "restoreAllMocks", "useFakeTimers", "useRealTimers", "runAllTimers",
    "runAllTicks", "advanceTimersByTime", "clearAllTimers",
    # console
    "log", "error", "warn", "info",
    # JS builtins
    "require", "import", "Promise", "resolve", "reject",
    "setTimeout", "setInterval", "clearTimeout", "clearInterval",
    "JSON", "Math", "Object", "Array", "String", "Number", "Boolean",
    "Error", "TypeError", "RangeError", "parse", "stringify",
    "console", "process",
})

_JS_SKIP_CLASSES = frozenset({
    "Array", "Object", "String", "Number", "Boolean", "Promise",
    "Error", "TypeError", "RangeError", "ReferenceError", "SyntaxError",
    "Map", "Set", "WeakMap", "WeakSet", "Date", "RegExp", "Symbol",
    "Function", "Proxy", "Reflect", "JSON", "Math",
    "describe", "it", "test",
})


def parse_javascript(source: str, _test_path: Path) -> tuple[dict, str | None]:
    res = _empty_result()
    imported_names: set[str] = set()

    # Named imports: import { A, B } from './module'
    for m in _JS_IMPORT_NAMED.finditer(source):
        raw_names = m.group(1)
        module = m.group(2)
        names = [n.strip().split(" as ")[-1].strip()
                 for n in raw_names.split(",") if n.strip()]
        res["imports"].append({
            "module": module,
            "names": names,
            "line": _line_of(source, m.start()),
            "import_style": "es-named",
        })
        imported_names.update(names)

    # Default imports — only if not already captured by named (check for '{')
    named_positions = {m.start() for m in _JS_IMPORT_NAMED.finditer(source)}
    for m in _JS_IMPORT_DEFAULT.finditer(source):
        if m.start() in named_positions:
            continue
        # Skip "import * as" lines — handled separately
        if m.group(0).startswith("import *"):
            continue
        name = m.group(1)
        module = m.group(2)
        if name not in ("type", "typeof"):
            res["imports"].append({
                "module": module,
                "names": [name],
                "line": _line_of(source, m.start()),
                "import_style": "es-default",
            })
            imported_names.add(name)

    # Namespace imports: import * as ns from './module'
    for m in _JS_IMPORT_NS.finditer(source):
        res["imports"].append({
            "module": m.group(2),
            "names": [m.group(1)],
            "line": _line_of(source, m.start()),
            "import_style": "es-namespace",
        })
        imported_names.add(m.group(1))

    # CommonJS destructure: const { A, B } = require(...)
    for m in _JS_REQ_DESTRUCT.finditer(source):
        names = [n.strip().split(":")[-1].strip()
                 for n in m.group(1).split(",") if n.strip()]
        res["imports"].append({
            "module": m.group(2),
            "names": names,
            "line": _line_of(source, m.start()),
            "import_style": "require-destructure",
        })
        imported_names.update(names)

    # CommonJS default: const mod = require(...)
    for m in _JS_REQ_DEFAULT.finditer(source):
        name = m.group(1)
        res["imports"].append({
            "module": m.group(2),
            "names": [name],
            "line": _line_of(source, m.start()),
            "import_style": "require-default",
        })
        imported_names.add(name)

    # jest.mock / vi.mock
    for m in _JS_MOCK_MODULE.finditer(source):
        res["mock_targets"].append({
            "target": m.group(1),
            "line": _line_of(source, m.start()),
            "style": "module-mock",
        })

    # jest.spyOn / vi.spyOn
    for m in _JS_SPY_ON.finditer(source):
        res["mock_targets"].append({
            "target": f"{m.group(1)}.{m.group(2)}",
            "line": _line_of(source, m.start()),
            "style": "spy-on",
        })

    res["mock_targets"] = deduplicate_by(res["mock_targets"], "target")

    # .toThrow(ErrorClass)
    for m in _JS_TO_THROW.finditer(source):
        res["exception_refs"].append({
            "name": m.group(1),
            "line": _line_of(source, m.start()),
        })

    res["exception_refs"] = deduplicate_by(res["exception_refs"], "name")

    # new ClassName(
    for m in _JS_NEW.finditer(source):
        cls = m.group(1)
        if cls not in _JS_SKIP_CLASSES:
            res["symbol_calls"].append({
                "name": cls,
                "line": _line_of(source, m.start()),
                "call_style": "new",
            })

    # funcName( — lower camelCase
    for m in _JS_FUNC_CALL.finditer(source):
        name = m.group(1)
        if name not in _JS_SKIP_FUNCS and name in imported_names:
            res["symbol_calls"].append({
                "name": name,
                "line": _line_of(source, m.start()),
                "call_style": "direct",
            })

    res["symbol_calls"] = deduplicate_by(res["symbol_calls"], "name")

    # Constants
    for m in _JS_CONST.finditer(source):
        name = m.group(1)
        if name not in imported_names:
            res["constant_refs"].append({
                "name": name,
                "line": _line_of(source, m.start()),
            })

    res["constant_refs"] = deduplicate_by(res["constant_refs"], "name")
    return res, None


# ===========================================================================
# Main entry point
# ===========================================================================

def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Extract external references from a test file (Python/Java/C#/JavaScript). "
            "Auto-detects language from file extension. "
            "Used by the scan-halucinated-tests skill."
        )
    )
    parser.add_argument("test_file", help="Path to the test file to parse")
    args = parser.parse_args()

    test_path = Path(args.test_file)

    if not test_path.exists():
        print(f"Error: file not found: {args.test_file}", file=sys.stderr)
        sys.exit(1)
    if not test_path.is_file():
        print(f"Error: not a regular file: {args.test_file}", file=sys.stderr)
        sys.exit(1)

    language = detect_language(test_path)
    if language is None:
        supported = ", ".join(sorted(LANGUAGE_MAP.keys()))
        print(
            f"Error: unsupported file extension '{test_path.suffix}'. "
            f"Supported: {supported}",
            file=sys.stderr,
        )
        sys.exit(1)

    inferred_source = infer_source_path(test_path, language)

    result: dict = {
        "test_file":       str(test_path).replace("\\", "/"),
        "inferred_source": inferred_source,
        "language":        language,
        "imports":         [],
        "symbol_calls":    [],
        "mock_targets":    [],
        "attribute_accesses": [],
        "exception_refs":  [],
        "kwarg_calls":     [],
        "constant_refs":   [],
        "parse_error":     None,
    }

    try:
        source = test_path.read_text(encoding="utf-8", errors="replace")
    except OSError as e:
        print(f"Error reading file: {e}", file=sys.stderr)
        sys.exit(1)

    parsers = {
        "python":     parse_python,
        "java":       parse_java,
        "csharp":     parse_csharp,
        "javascript": parse_javascript,
    }

    refs, parse_error = parsers[language](source, test_path)

    if parse_error:
        result["parse_error"] = parse_error
        print(json.dumps(result, indent=2))
        sys.exit(1)

    result.update(refs)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
