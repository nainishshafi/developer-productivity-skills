---
name: scan-halucinated-tests
description: Use when the user asks to "scan for hallucinated tests", "check if my
  tests are hallucinated", "validate tests against source", "verify test accuracy",
  "find fake test assertions", "audit tests for hallucinations", "test hallucination
  scan", "verify tests match source code", "check java tests", "validate c# tests",
  or "check javascript tests for hallucinations". Also use when the user wants to
  cross-check a test file against real source code to detect phantom symbols,
  wrong imports, bad mock targets, or fabricated constants — in any supported language.
version: 1.1.0
---

# Scan Hallucinated Tests

Cross-validate a test file against the real source code it tests. Detects phantom functions, non-existent classes and attributes, wrong mock targets, bad imports, fabricated exceptions, incorrect argument names, and invented constants — all hallucinations common when LLMs write tests.

**Supported languages:** Python (`.py`), Java (`.java`), C# (`.cs`), JavaScript/TypeScript (`.js`, `.jsx`, `.ts`, `.tsx`)

**Analysis approach:** A multi-language parser (`parse-test-refs.py`) extracts every external reference the test file makes using AST for Python and regex for Java/C#/JS. The `trace-code-context` skill's script provides the authoritative list of what *actually* exists in the source. A haiku subagent cross-references both to produce a scored hallucination report.

## Prerequisites

- Python 3.8+ available (`.venv` will be created automatically if missing)
- The skill requires a `<test-file>` argument — relative or absolute path to the test file (`.py`, `.java`, `.cs`, `.js`, `.ts`, etc.)
- Optional: `<source-file>` argument — if omitted, the source path is inferred from the test filename

## Workflow

### Skill Step 1 — Gather Inputs and Infer Source Path

Accept two arguments from the user:
- `<test-file>` (required) — path to the test file
- `<source-file>` (optional) — path to the source file being tested

**If `<source-file>` is not provided**, infer it using language-specific conventions (see `references/scan-halucinated-tests-reference.md` for the full table):

| Language | Test path example | Inferred source path |
|----------|------------------|---------------------|
| Python | `tests/test_auth.py` | `src/auth.py` |
| Python | `tests/unit/test_auth.py` | `src/auth.py` |
| Java | `src/test/java/com/example/AuthTest.java` | `src/main/java/com/example/Auth.java` |
| Java | `AuthTest.java` (flat) | `Auth.java` |
| C# | `Tests/AuthTests.cs` | `src/Auth.cs` |
| C# | `AuthService.Tests/AuthServiceTests.cs` | `AuthService/AuthService.cs` |
| JavaScript | `auth.test.ts` | `auth.ts` |
| JavaScript | `__tests__/auth.js` | `src/auth.js` |

If the inferred path does not exist on disk, tell the user and ask for `<source-file>` explicitly before continuing.

### Skill Step 2 — Run trace-context.py on the Source File

Set up the `.venv` and run `trace-context.py` with `--force` to guarantee fresh ground truth:

```bash
[ -d .venv ] || python -m venv .venv
PYTHON=$(if [ -f .venv/Scripts/python ]; then echo .venv/Scripts/python; else echo .venv/bin/python; fi)
$PYTHON .github/skills/trace-code-context/scripts/trace-context.py --force "<source-file>"
```

The script prints a single JSON object to stdout:

```json
{
  "stale": true,
  "repo_root": "/home/user/myproject",
  "output_path": ".code-context/src/auth.md",
  "source_path": "src/auth.py",
  "language": "python",
  "symbols": ["login", "logout", "AuthError"],
  "imports": ["os", "hashlib", "models.user"],
  "parse_method": "ast",
  "repo_source_files": ["src/auth.py", "tests/test_auth.py"]
}
```

Capture: `repo_root`, `source_path`, `output_path`, `language`, `symbols`, `imports`, `parse_method`.

**Stop and report to the user if:** the script exits non-zero, the output contains no valid JSON, or the `symbols` list is empty (cross-reference would be meaningless).

### Skill Step 3 — Run parse-test-refs.py on the Test File

The script auto-detects the language from the file extension.

```bash
$PYTHON .github/skills/scan-halucinated-tests/scripts/parse-test-refs.py "<test-file>"
```

The script prints a single JSON object to stdout. The shape is uniform across all languages:

```json
{
  "test_file": "tests/test_auth.py",
  "inferred_source": "src/auth.py",
  "language": "python",
  "imports": [
    {"module": "src.auth", "names": ["login", "logout"], "line": 1, "import_style": "from"}
  ],
  "symbol_calls": [
    {"name": "login", "line": 15, "call_style": "direct"}
  ],
  "mock_targets": [
    {"target": "src.auth.db_connection", "line": 10, "style": "decorator"}
  ],
  "attribute_accesses": [
    {"object": "result", "attribute": "token", "line": 18}
  ],
  "exception_refs": [
    {"name": "AuthError", "line": 22}
  ],
  "kwarg_calls": [
    {"function": "login", "kwargs": ["username", "password"], "line": 15}
  ],
  "constant_refs": [
    {"name": "MAX_RETRY_COUNT", "line": 30}
  ],
  "parse_error": null
}
```

**Language-specific `mock_targets` styles:**
- Python: `"style": "decorator"` / `"inline"` / `"patch.object"` — `target` is a dotted string path like `src.auth.db`
- Java: `"style": "field-annotation"` / `"mock-call"` / `"when-stub"` / `"verify"` — `target` is a class name or method name
- C#: `"style": "mock-type"` / `"setup"` / `"verify"` — `target` is a type name or method name
- JavaScript: `"style": "module-mock"` / `"spy-on"` — `target` is a module path or `object.method`

**Stop and report to the user if:** `parse_error` is non-null, or the script exits with code 1 (display stderr).

### Skill Step 4 — Launch Haiku Subagent for Cross-Reference Analysis

Use the Agent tool with:
- **subagent_type**: `"general-purpose"`
- **model**: `"haiku"`
- **description**: `"Scan hallucinated tests for <test-file>"`

Compute the output file timestamp (current date-time in `YYYYMMDD-HHMMSS` format). The output path is:
```
.scan-test-results/scan-<timestamp>.md
```

Construct the following prompt using the JSON values from Steps 2 and 3, replacing all `{...}` placeholders with real values before sending:

````
You are a test hallucination auditor. Cross-reference what a test file *claims* exists against what *actually* exists in the source code, then write a scored hallucination report.

## Inputs

### Ground Truth — Source File (from trace-context.py)
- Repo root: {repo_root}
- Source path: {source_path}
- Context doc path: {output_path}
- Language: {language}
- Parse method: {parse_method}
- Defined symbols:
{symbols as bulleted list}
- Source imports:
{imports as bulleted list}

### Test File References (from parse-test-refs.py)
- Test file: {test_file}
- Test language: {test_language from parse-test-refs output}
- Imports by test:
{imports list formatted as: "  - `{module}` imports {names} (line {line}, {import_style})"}
- Symbol calls:
{symbol_calls list formatted as: "  - `{name}` (line {line}, {call_style})"}
- Mock targets:
{mock_targets list formatted as: "  - `{target}` (line {line}, style={style})"}
- Attribute accesses:
{attribute_accesses list formatted as: "  - `{object}.{attribute}` (line {line})"}
- Exception refs:
{exception_refs list formatted as: "  - `{name}` (line {line})"}
- Keyword arg / named param calls:
{kwarg_calls list formatted as: "  - `{function}({kwargs joined with ', '})` (line {line})"}
- Constant refs:
{constant_refs list formatted as: "  - `{name}` (line {line})"}

## Output File
{repo_root}/.scan-test-results/scan-{timestamp}.md

---

## Your Instructions

1. **Read the source file** at `{repo_root}/{source_path}` using the Read tool.
   This is authoritative ground truth of what exists. Read the full file carefully.

2. **Read the context doc** at `{repo_root}/{output_path}` using the Read tool.
   Use the Defined Symbols table and Dependencies section as a quick-reference index.

3. **Read the test file** at `{repo_root}/{test_file}` using the Read tool.
   Understand the full structure: test class/functions, mocks, stubs, assertions.

4. **Cross-reference each hallucination category.** The validation logic differs by language:

   ---

   ### Python

   **Category 1 — Phantom Functions / Classes** (`symbol_calls`)
   Each `name` must appear in the source's defined symbols. Skip pytest builtins
   (`fixture`, `mark`, `raises`, `approx`), Python builtins (`len`, `str`, `open`, etc.),
   `unittest.mock` names (`MagicMock`, `patch`, etc.), and names defined in the test file itself.

   **Category 2 — Wrong Imports** (`imports`)
   `imports[].module` must map to the source file's dotted module path
   (`source_path` with `/` → `.` and `.py` stripped). `imports[].names` must be in `symbols[]`.
   Skip stdlib and third-party imports (`os`, `sys`, `pytest`, `unittest`, `requests`, etc.).

   **Category 3 — Wrong Mock Targets** (`mock_targets`, style=decorator/inline)
   Split the dotted `target` string. The prefix must match the source module's dotted path.
   The final segment must exist as an imported name, defined symbol, or attribute in the source.
   `patch.object` style: first part is an imported name; second part must be in source symbols.

   **Category 4 — Phantom Attributes** (`attribute_accesses`)
   Only flag when the object is clearly a module or class from the source, and the attribute
   demonstrably does not exist. Do NOT flag generic return-value attributes or Mock attrs.

   **Category 5 — Phantom Exceptions** (`exception_refs`)
   The name must be in source `symbols[]` or be a known Python stdlib exception.
   Standard exceptions are NOT hallucinations: `ValueError`, `TypeError`, `KeyError`,
   `RuntimeError`, `OSError`, `AttributeError`, `IndexError`, `NotImplementedError`, etc.

   **Category 6 — Wrong Argument Names** (`kwarg_calls`)
   Find the function definition in the source. Compare kwarg names to real parameter names.
   Skip if the function accepts `**kwargs`.

   **Category 7 — Fabricated Constants** (`constant_refs`)
   ALL_CAPS name must appear in source text as a defined constant. Check raw source, not just symbols.

   ---

   ### Java

   **Category 1 — Phantom Methods / Classes** (`symbol_calls`)
   For `call_style=new`: the class name must be in source `symbols[]` or be an imported class.
   For `call_style=static-or-instance` with an `object`: the `object` class must be imported
   and the method `name` must be in source `symbols[]`. Skip JUnit/Mockito classes
   (`Assert`, `Assertions`, `Mockito`, `ArgumentMatchers`, etc.) and Java stdlib (`String`, `List`, etc.).

   **Category 2 — Wrong Imports** (`imports`)
   The fully-qualified `module` (package) + `name` (class) must correspond to a class
   actually used from the source. If the test imports `com.example.fakepackage.FakeClass`
   that doesn't match any symbol in the source → hallucination.

   **Category 3 — Wrong Mock Targets** (`mock_targets`)
   - `style=field-annotation` or `style=mock-call`: the class being mocked must be imported
     and should correspond to an interface/class the source depends on.
   - `style=when-stub` or `style=verify`: the method name `target` must exist in source `symbols[]`
     (i.e., it's a method the source exposes). A stubbed method that doesn't exist → hallucination.

   **Category 5 — Phantom Exceptions** (`exception_refs`)
   The exception class must be imported in the test or be a standard Java exception:
   `IllegalArgumentException`, `IllegalStateException`, `NullPointerException`,
   `RuntimeException`, `Exception`, `IOException`, `UnsupportedOperationException`, etc.

   **Category 7 — Fabricated Constants** (`constant_refs`)
   ALL_CAPS names must appear in the source as `public static final` fields or enum values.

   ---

   ### C#

   **Category 1 — Phantom Types / Methods** (`symbol_calls`)
   For `call_style=new`: the type name must be in source `symbols[]` or be an imported type.
   For `call_style=type-call` with an `object`: the `object` type must be imported and `name`
   must be in source `symbols[]`. Skip test framework types (`Assert`, `Mock`, `It`, `Times`, etc.)
   and .NET stdlib types (`String`, `List`, `Task`, `Guid`, `DateTime`, etc.).

   **Category 2 — Wrong Imports** (`imports`, style=using)
   The namespace + type name must correspond to a type actually used from the source.
   A `using` for a non-existent namespace → HIGH severity.

   **Category 3 — Wrong Mock Targets** (`mock_targets`)
   - `style=mock-type`: the mocked interface/class must be imported and should be a type
     the source depends on.
   - `style=setup` or `style=verify`: the method name `target` must be in source `symbols[]`.

   **Category 5 — Phantom Exceptions** (`exception_refs`)
   The exception class must be imported or be a standard .NET exception:
   `Exception`, `ArgumentException`, `ArgumentNullException`, `InvalidOperationException`,
   `NotImplementedException`, `NullReferenceException`, `IOException`, `HttpRequestException`, etc.

   **Category 6 — Wrong Named Arguments** (`kwarg_calls`)
   Find the method definition in the source. Named param names must match real parameter names.

   ---

   ### JavaScript / TypeScript

   **Category 1 — Phantom Functions / Classes** (`symbol_calls`)
   For `call_style=new`: the class must be in source `symbols[]` or be a known third-party class.
   For `call_style=direct`: the function name must be in source `symbols[]`.
   Skip test framework functions (`describe`, `it`, `test`, `expect`, `beforeEach`, etc.)
   and JS globals (`Error`, `TypeError`, `JSON`, `Math`, `Promise`, `Array`, `Object`, etc.).

   **Category 2 — Wrong Imports** (`imports`)
   The `module` path (e.g., `./auth`, `../services/auth`) must resolve to a real file in the repo.
   For relative paths: derive the expected file path from the test file's location + the module string.
   `imports[].names` must be exported from that file (check source `symbols[]`).
   Skip third-party package imports (no `./` prefix or relative path) — those are npm packages, not source.

   **Category 3 — Wrong Mock Targets** (`mock_targets`)
   - `style=module-mock`: the module path `target` must resolve to a real file.
   - `style=spy-on`: the `object.method` — `object` must be an imported name and `method`
     must exist in the source as an exported function or class method.

   **Category 5 — Phantom Exceptions** (`exception_refs`)
   The class must be in source `symbols[]` or be a built-in JS error:
   `Error`, `TypeError`, `RangeError`, `ReferenceError`, `SyntaxError`, `URIError`, `EvalError`.

   ---

5. **Score each finding:**
   - **CRITICAL** — Symbol/function/class/constant does not exist at all → will always fail at runtime
   - **HIGH** — Wrong mock path, wrong import path, wrong kwarg name on a strict function
   - **MEDIUM** — May pass silently but tests wrong behavior (attribute on Mock, wrong kwarg on variadic fn)
   - **LOW** — Cannot confirm from static analysis; note as potential issue

6. **Create the output directory:**
   ```bash
   mkdir -p "{repo_root}/.scan-test-results"
   ```

7. **Write the report** using the Write tool to `{repo_root}/.scan-test-results/scan-{timestamp}.md`:

```markdown
# Hallucination Scan Report
**Test file:** `{test_file}`
**Source file:** `{source_path}`
**Test language:** {language}
**Scanned:** {today's date and time}
**Parse method:** {parse_method}

## Summary
| Severity | Count |
|----------|-------|
| CRITICAL | N |
| HIGH     | N |
| MEDIUM   | N |
| LOW      | N |
| **Total**| N |

**Overall verdict:** CLEAN / MINOR ISSUES / SIGNIFICANT HALLUCINATIONS / HEAVILY HALLUCINATED

_Verdict thresholds: CLEAN = 0 | MINOR ISSUES = only LOW/MEDIUM ≤ 3 | SIGNIFICANT = any HIGH or MEDIUM > 3 | HEAVILY HALLUCINATED = any CRITICAL or total > 6_

---

## Findings

### CRITICAL — {short title}

**Category:** {hallucination category name}
**Test file line:** {line number}
**What the test claims:** `{the symbol/call/import as written in the test}`
**What actually exists:** `{what is in the source, or "nothing — not defined"}`
**Why this fails:** {plain-English explanation, 1-2 sentences}
**Fix:** `{exact change needed in the test}`

---

(Repeat for each finding, ordered: CRITICAL → HIGH → MEDIUM → LOW)

---

## Verified (No Issues Found)

- `{symbol}` — confirmed defined in source
- `{import}` — confirmed valid path
(list all checked items that passed)

---

## Cannot Verify (Static Analysis Limit)

- `{item}` — {reason why static analysis cannot confirm or deny}

---

## Remediation Summary

{2-4 sentences summarizing the hallucination pattern and root cause}
```

Write the file, then confirm the absolute path in your response.
````

### Skill Step 5 — Read and Present Report

1. Read the file at `{repo_root}/.scan-test-results/scan-<timestamp>.md`
2. Present to the user:
   - The **Summary table** (severity counts + overall verdict)
   - All **CRITICAL** and **HIGH** findings in full
   - A note on MEDIUM/LOW count with offer to show details
   - The **Remediation Summary** paragraph
   - Full report path: `"Full report written to {repo_root}/.scan-test-results/scan-<timestamp>.md"`

## Additional Resources

- **`references/scan-halucinated-tests-reference.md`** — Hallucination pattern catalog (all languages), source file inference rules, cross-reference heuristics per language, severity scoring, false-positive categories, output path convention
- **`scripts/parse-test-refs.py`** — Multi-language test reference extractor; auto-detects Python/Java/C#/JavaScript from file extension; outputs uniform JSON to stdout
