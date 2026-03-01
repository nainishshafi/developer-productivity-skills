# Scan Hallucinated Tests Reference

Reference guide for the `scan-halucinated-tests` skill — hallucination pattern catalog across Python, Java, C#, and JavaScript, source file inference rules, cross-reference heuristics, severity scoring, known false-positive categories, and output path convention.

---

## Supported Languages and Parsers

| Language | Extensions | Parse method | Test framework(s) covered |
|----------|-----------|-------------|--------------------------|
| Python | `.py` | AST (most accurate) | pytest, unittest |
| Java | `.java` | Regex | JUnit 4/5, Mockito, EasyMock |
| C# | `.cs` | Regex | xUnit, NUnit, MSTest, Moq, NSubstitute |
| JavaScript/TypeScript | `.js` `.jsx` `.ts` `.tsx` | Regex | Jest, Vitest |

---

## Hallucination Pattern Catalog

Seven categories with examples in each supported language.

---

### Category 1 — Phantom Functions / Classes

**What it is:** The test calls a function, method, or instantiates a class that does not exist in the source module.

**Python example:**
```python
result = auth.authenticate_user(username="alice")
# Hallucinated — source defines `login`, not `authenticate_user`
```

**Java example:**
```java
AuthToken token = authService.authenticateUser(username, password);
// Hallucinated — source defines `login()`, not `authenticateUser()`
```

**C# example:**
```csharp
var result = _authService.AuthenticateUser(username, password);
// Hallucinated — source defines `Login()`, not `AuthenticateUser()`
```

**JavaScript example:**
```javascript
const result = authenticateUser({ username: 'alice' });
// Hallucinated — source exports `login`, not `authenticateUser`
```

**Detection:** `symbol_calls[].name` not in `trace-context symbols[]`.

**Severity:** CRITICAL — `AttributeError` / `NoSuchMethodError` / `MissingMethodException` / `TypeError` at runtime.

---

### Category 2 — Wrong Imports

**What it is:** The test imports from a path that doesn't match the real module location, or imports a name not exported by that module.

**Python example:**
```python
from auth.utils import validate_token   # Wrong — real module is `src.auth.utils`
from src.auth import authenticate_user  # Wrong name — real function is `login`
```

**Java example:**
```java
import com.example.security.AuthHelper;  // Wrong package — real package is com.example.auth
```

**C# example:**
```csharp
using MyApp.Security.AuthHelpers;  // Wrong namespace — real namespace is MyApp.Auth
```

**JavaScript example:**
```javascript
import { validateToken } from './authUtils';
// Wrong name — ./authUtils exports `checkToken`, not `validateToken`
```

**Detection:** Module path doesn't correspond to the source file's real location; imported names not in source `symbols[]`.

**Severity:** HIGH — `ImportError` / `ClassNotFoundException` / namespace resolution failure / module not found.

---

### Category 3 — Wrong Mock Targets

**What it is:** Mock setup uses a path, class, or method name that doesn't match where the real object is defined or imported. The mock doesn't intercept the real call — tests pass without validating actual behavior.

**Python example:**
```python
@patch("auth.db.connection")          # Wrong — real attribute is `conn`, not `connection`
@patch("utils.auth.login")            # Wrong prefix — real path is `src.auth.login`
```

**Java example:**
```java
when(authService.validateCredentials(any(), any())).thenReturn(token);
// Hallucinated — source only exposes `login()`, not `validateCredentials()`
verify(authService).processLogin(username);
// Hallucinated — source method is `login()`, not `processLogin()`
```

**C# example:**
```csharp
_mockAuth.Setup(x => x.ValidateCredentials(It.IsAny<string>())).Returns(token);
// Hallucinated — interface only has `Login()`, not `ValidateCredentials()`
```

**JavaScript example:**
```javascript
jest.mock('./authService');         // Wrong — real file is at ./services/auth
vi.spyOn(authModule, 'validateUser');
// Hallucinated — exported function is `login`, not `validateUser`
```

**Detection:** Mock target refers to a name not in source `symbols[]`, or a path that doesn't resolve to the source file.

**Severity:** HIGH — mock doesn't intercept the real call; test passes silently without testing anything.

---

### Category 4 — Phantom Attributes

**What it is:** Test accesses a property or field on the result of a source call that doesn't exist on the returned type.

**Python example:**
```python
result = login(username="alice", password="secret")
assert result.session_id   # Hallucinated — login() returns a dict, not an object with session_id
```

**Java example:**
```java
AuthResult result = authService.login(username, password);
assertNotNull(result.getSessionToken());
// Hallucinated — AuthResult only has getToken(), not getSessionToken()
```

**C# example:**
```csharp
var result = _authService.Login(username, password);
Assert.NotNull(result.SessionIdentifier);
// Hallucinated — LoginResult only has SessionId, not SessionIdentifier
```

**JavaScript example:**
```javascript
const result = login({ username: 'alice', password: 'secret' });
expect(result.sessionToken).toBeDefined();
// Hallucinated — login() returns { token: string }, not { sessionToken: string }
```

**Detection:** Limited — only flag when the object is clearly a typed return value and the attribute demonstrably doesn't exist on any plausible return type.

**Severity:** MEDIUM — may pass silently when mocked; fails on real integration.

---

### Category 5 — Phantom Exceptions

**What it is:** Test asserts a specific exception type that is not defined in or importable from the source.

**Python example:**
```python
with pytest.raises(AuthenticationError):   # Wrong — source defines `AuthError`
    login("bad", "creds")
```

**Java example:**
```java
assertThrows(AuthenticationException.class, () -> authService.login("", ""));
// Hallucinated — source throws `AuthException`, not `AuthenticationException`
```

**C# example:**
```csharp
Assert.Throws<AuthenticationException>(() => _service.Login("", ""));
// Hallucinated — source throws `AuthException`, not `AuthenticationException`
```

**JavaScript example:**
```javascript
expect(() => login()).toThrow(AuthenticationError);
// Hallucinated — source throws `AuthError`, not `AuthenticationError`
```

**Detection:** Exception name not in source `symbols[]` and not a known standard-library exception for that language.

**Severity:** CRITICAL — either the exception class doesn't exist (`NameError`/`ClassNotFoundException`) or the test never catches the right type.

---

### Category 6 — Wrong Argument Names

**What it is:** Test calls a real function with parameter names that don't match the actual signature.

**Python example:**
```python
login(user="alice", pass_word="secret")
# Hallucinated — real signature: login(username: str, password: str)
```

**C# example:**
```csharp
_service.Login(userName: "alice", pwd: "secret");
// Hallucinated — real signature: Login(string username, string password)
```

**Detection:** `kwarg_calls[].kwargs` don't match real parameter names in the source function definition.

**Note:** Not extracted for Java (no named arguments in standard Java calls) or JavaScript (options objects require deeper analysis).

**Severity:** HIGH if function uses strict params; MEDIUM if variadic.

---

### Category 7 — Fabricated Constants

**What it is:** Test references an ALL_CAPS constant or enum value that doesn't exist in the source.

**Python example:**
```python
assert response.status == auth.STATUS_ACTIVE
# Hallucinated — source has no STATUS_ACTIVE
```

**Java example:**
```java
assertEquals(HttpStatus.ACCEPTED, response.getStatus());
// Hallucinated (if ACCEPTED doesn't exist in the enum the source uses)
```

**C# example:**
```csharp
Assert.Equal(AuthStatus.Active, result.Status);
// Hallucinated — enum only has AuthStatus.LoggedIn
```

**JavaScript example:**
```javascript
expect(result.status).toBe(STATUS_ACTIVE);
// Hallucinated — source exports STATUS_AUTHENTICATED, not STATUS_ACTIVE
```

**Detection:** Constant name not in source `symbols[]` and not found in raw source text search.

**Severity:** CRITICAL — `AttributeError` / field access exception at runtime.

---

## Source File Inference Rules

### Python

| Test path pattern | Inferred source path |
|------------------|---------------------|
| `tests/test_<name>.py` | `src/<name>.py` |
| `tests/unit/test_<name>.py` | `src/<name>.py` |
| `tests/api/test_<name>.py` | `src/api/<name>.py` |
| `test_<name>.py` (root) | `<name>.py` |
| `<name>_test.py` | `<name>.py` |

Strip `test_` prefix or `_test` suffix. Replace `tests/` with `src/`. Drop test-category subdirs: `unit`, `integration`, `functional`, `e2e`, `acceptance`.

### Java

| Test path pattern | Inferred source path |
|------------------|---------------------|
| `src/test/java/com/ex/AuthTest.java` | `src/main/java/com/ex/Auth.java` |
| `src/test/java/com/ex/AuthTests.java` | `src/main/java/com/ex/Auth.java` |
| `AuthTest.java` (flat) | `Auth.java` |
| `TestAuth.java` (Test prefix) | `Auth.java` |

Replace `src/test/java` → `src/main/java`. Strip `Test`/`Tests` suffix or `Test` prefix from class name.

### C#

| Test path pattern | Inferred source path |
|------------------|---------------------|
| `Tests/AuthTests.cs` | `src/Auth.cs` |
| `Tests/AuthTest.cs` | `src/Auth.cs` |
| `MyProject.Tests/AuthServiceTests.cs` | `MyProject/AuthService.cs` |
| `AuthTests.cs` (root) | `Auth.cs` |

Strip `Tests` or `Test` suffix. Remove `.Tests` from parent directory name.

### JavaScript / TypeScript

| Test path pattern | Inferred source path |
|------------------|---------------------|
| `auth.test.ts` | `auth.ts` |
| `auth.spec.js` | `auth.js` |
| `__tests__/auth.ts` | `src/auth.ts` |
| `src/__tests__/auth.js` | `src/auth.js` |
| `tests/auth.test.ts` | `src/auth.ts` |

Strip `.test` or `.spec` infix from filename. Replace `__tests__/` with `src/`.

### Critical Rule (all languages)

If the inferred path does not exist on disk, **stop and ask the user** to provide `<source-file>` explicitly. Never guess further — monorepos, custom layouts, and multi-source tests all require user input.

---

## Cross-Reference Heuristics

### Python: Mock Target Validation

Given `@patch("src.auth.db_connection")`:
1. Derive expected module path from `source_path`: `src/auth.py` → `src.auth`
2. Split target: prefix = `src.auth`, last segment = `db_connection`
3. Prefix must equal source module path
4. Last segment must be a name in the source (import, symbol, module-level var)

Common hallucination patterns: wrong prefix, wrong attribute name, non-existent attribute.

### Java: Mock Method Validation

For `when(authService.validateCredentials(...))`  →  `target = "validateCredentials"`:
1. `validateCredentials` must be in source `symbols[]`
2. Check the source file for the method definition to confirm signature

For `mock(FakeService.class)` → `target = "FakeService"`:
1. `FakeService` must be imported by the test
2. The import's package path must correspond to a real class the source depends on

### C#: Setup/Verify Validation

For `.Setup(x => x.ValidateCredentials(...))` → `target = "ValidateCredentials"`:
1. `ValidateCredentials` must be in source `symbols[]`
2. The mocked type (`Mock<IAuthService>`) must correspond to an interface/class the source depends on

### JavaScript: Module Path Validation

For `jest.mock('./authService')`:
1. Resolve `./authService` relative to the test file's directory
2. Check if `authService.ts`, `authService.js`, or `authService/index.ts` exists
3. If not → wrong mock path

For `vi.spyOn(authModule, 'login')`:
1. `authModule` must be an imported name (namespace import of the source module)
2. `login` must be in source `symbols[]`

---

## Severity Scoring Criteria

| Severity | Runtime behavior | Confidence requirement |
|----------|-----------------|------------------------|
| **CRITICAL** | Always fails — symbol doesn't exist | Symbol demonstrably absent from source |
| **HIGH** | Likely fails or tests wrong code path | Wrong mock path, wrong import, wrong strict param |
| **MEDIUM** | May silently pass but tests wrong behavior | Attribute on Mock, param on variadic fn |
| **LOW** | Cannot confirm from static analysis | Generic return type, third-party object attribute |

### Overall Verdict Thresholds

| Verdict | Condition |
|---------|-----------|
| **CLEAN** | 0 findings |
| **MINOR ISSUES** | Only LOW/MEDIUM, total ≤ 3 |
| **SIGNIFICANT HALLUCINATIONS** | Any HIGH, or MEDIUM count > 3 |
| **HEAVILY HALLUCINATED** | Any CRITICAL, or total findings > 6 |

---

## Known False-Positive Categories

### Python

- **Stdlib exceptions:** `ValueError`, `TypeError`, `KeyError`, `RuntimeError`, `OSError`, `IOError`, `AttributeError`, `IndexError`, `StopIteration`, `Exception`, `BaseException`, `NotImplementedError`, `PermissionError`, `FileNotFoundError`, `ImportError`, `ModuleNotFoundError`, `NameError`, `RecursionError`, `MemoryError`, `OverflowError`, `ZeroDivisionError`, `UnicodeError`, `AssertionError`, `SystemExit`, `KeyboardInterrupt`, `ConnectionError`, `TimeoutError`.
- **pytest fixtures:** `capsys`, `capfd`, `tmp_path`, `tmp_path_factory`, `tmpdir`, `monkeypatch`, `mocker`, `client`, `app`, `db`, `session`, `caplog`, `recwarn`, `request`, `cache`. Also names defined in `conftest.py`.
- **unittest.mock internals:** `.called`, `.call_count`, `.call_args`, `.return_value`, `.side_effect`, `.assert_called`, `.assert_called_once_with`, `.reset_mock`, `.mock_calls`.
- **Third-party packages:** `requests`, `flask`, `django`, `sqlalchemy`, `pydantic`, etc. — any import without relative path.
- **Dunder methods:** `__init__`, `__str__`, `__repr__`, `__eq__`, `__enter__`, `__exit__`, etc.
- **Names defined in the test file itself** (helpers, fixtures, local classes).

### Java

- **Standard exceptions:** `IllegalArgumentException`, `IllegalStateException`, `NullPointerException`, `RuntimeException`, `Exception`, `IOException`, `UnsupportedOperationException`, `IndexOutOfBoundsException`, `ClassCastException`, `ArithmeticException`, `NumberFormatException`.
- **JUnit 5 annotations / framework classes:** `@Test`, `@BeforeEach`, `@AfterEach`, `@BeforeAll`, `@AfterAll`, `@ExtendWith`, `@Disabled`, `@DisplayName`, `@ParameterizedTest`, `@ValueSource`, `@CsvSource`, `@MethodSource`.
- **Mockito framework classes:** `Mockito`, `ArgumentMatchers`, `ArgumentCaptor`, `InOrder`, `@Mock`, `@Spy`, `@InjectMocks`, `@Captor`.
- **JUnit assertion classes:** `Assertions`, `Assert` (JUnit 4).
- **Java stdlib types:** `String`, `Integer`, `Long`, `Double`, `Boolean`, `Object`, `List`, `Map`, `Set`, `Optional`, `Arrays`, `Collections`, `Stream`, `System`, `Math`, `Thread`, `Class`.

### C#

- **Standard exceptions:** `Exception`, `ArgumentException`, `ArgumentNullException`, `ArgumentOutOfRangeException`, `InvalidOperationException`, `NotImplementedException`, `NullReferenceException`, `IOException`, `HttpRequestException`, `OperationCanceledException`, `TaskCanceledException`, `TimeoutException`, `UnauthorizedAccessException`.
- **Test framework annotations/attributes:** `[Fact]`, `[Theory]`, `[Test]`, `[TestMethod]`, `[TestCase]`, `[SetUp]`, `[TearDown]`, `[TestFixture]`, `[TestClass]`, `[ClassInitialize]`, `[InlineData]`, `[MemberData]`.
- **Moq framework types:** `Mock<T>`, `It`, `Times`, `Capture`, `MockBehavior`.
- **.NET stdlib types:** `String`, `Int32`, `Int64`, `Boolean`, `Double`, `Object`, `List<T>`, `Dictionary<K,V>`, `Task`, `Task<T>`, `Guid`, `DateTime`, `TimeSpan`, `Enum`, `Console`, `Math`, `Convert`.

### JavaScript / TypeScript

- **Built-in JS errors:** `Error`, `TypeError`, `RangeError`, `ReferenceError`, `SyntaxError`, `URIError`, `EvalError`.
- **Jest/Vitest globals:** `describe`, `it`, `test`, `expect`, `beforeEach`, `afterEach`, `beforeAll`, `afterAll`, `jest`, `vi`, `mock`.
- **Jest matchers (not source symbols):** `.toBe`, `.toEqual`, `.toBeDefined`, `.toBeNull`, `.toBeTruthy`, `.toHaveBeenCalled`, `.toThrow`, `.resolves`, `.rejects`.
- **Third-party npm packages:** Any import without a `./` or `../` prefix (e.g., `import axios from 'axios'`) — these are external packages, not source symbols.
- **Globals:** `console`, `process`, `setTimeout`, `setInterval`, `Promise`, `JSON`, `Math`, `Object`, `Array`.

---

## Output Path Convention

Scan results are written to `.scan-test-results/` at the repository root:

```
.scan-test-results/scan-20240315-143022.md
```

Timestamp format: `YYYYMMDD-HHMMSS`. Each invocation creates a new timestamped file — previous results are never overwritten.

**Suggested `.gitignore` entry** (suggest this to the user after the first run):
```
.scan-test-results/
```

---

## Script Compatibility Notes

`parse-test-refs.py` uses Python standard library only — no third-party dependencies.

- **Python parser** uses `ast.parse` — accurate, handles all Python test patterns. Python 3.8 safe (uses custom `_node_to_str()` instead of `ast.unparse`).
- **Java parser** uses regex — covers JUnit 4/5, Mockito, EasyMock patterns. Not a full Java parser; complex generics and anonymous classes may produce noise.
- **C# parser** uses regex — covers Moq Setup/Verify lambda syntax, Assert.Throws<T>. Complex LINQ expressions or multi-line lambdas may not be captured fully.
- **JavaScript parser** uses regex — covers Jest and Vitest import/mock/spy/throw patterns. TypeScript generic syntax (`new Service<Config>()`) has the generic stripped to the base type.

For all regex-based languages, the subagent should treat the extracted references as a starting point and use the Read tool on the actual test file to verify edge cases that regex may have missed.

Exit codes:
- `0` — successful extraction
- `1` — unsupported file extension, file not found, unreadable, or Python syntax error
