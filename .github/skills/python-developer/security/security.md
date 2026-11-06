# Python Security Guidelines & Defensive Programming

Defend against common Python vulnerabilities, unsafe deserialization, SQL injection, and path traversal.

---

## 1. Unsafe Deserialization (Pickle & YAML)

Never deserialize untrusted user input using `pickle`, `shelve`, or `yaml.load()` without a safe loader. An attacker can construct payloads that execute arbitrary shell commands on your server.

```python
# ❌ CRITICAL SECURITY VULNERABILITY: Arbitrary code execution
import pickle
user_data = pickle.loads(untrusted_request_bytes)

# ❌ VULNERABLE: Unsafe PyYAML loader
import yaml
config = yaml.load(untrusted_yaml_string)

# ✅ SECURE: Always use yaml.safe_load or Pydantic JSON parsing
import yaml
config = yaml.safe_load(untrusted_yaml_string)
```

---

## 2. Parameterized SQL Queries

Never interpolate user input into raw SQL strings via f-strings or `.format()`. Always use query parameter bindings provided by the database driver or ORM:

```python
# ❌ CRITICAL VULNERABILITY: SQL Injection
query = f"SELECT * FROM users WHERE email = '{user_input}'"
await db.execute(query)

# ✅ SECURE: Parameterized binding
query = "SELECT * FROM users WHERE email = :email"
await db.execute(query, {"email": user_input})
```

---

## 3. Path Traversal Defense

When reading or saving files uploaded by users, always sanitize file paths using `pathlib.Path.resolve()` to ensure paths cannot escape the target storage directory:

```python
from pathlib import Path

BASE_STORAGE = Path("/var/app/uploads").resolve()

def get_safe_file_path(filename: str) -> Path:
    # Resolve relative to base storage
    target = (BASE_STORAGE / filename).resolve()
    # Ensure resolved path is strictly inside BASE_STORAGE
    if not target.is_relative_to(BASE_STORAGE):
        raise ValueError("Invalid file path: path traversal attempted")
    return target
```

