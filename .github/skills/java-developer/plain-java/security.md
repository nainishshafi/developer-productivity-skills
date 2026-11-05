# Java Application Security Guidelines

Directives for writing secure Java code, preventing OWASP Top 10 vulnerabilities, and handling sensitive data safely.

---

## 1. Injection Prevention

- **SQL Injection**: Always use parameterized queries (PreparedStatement or Spring Data JPA). Never concatenate strings into queries.
  ```java
  // Correct: Parameterized
  var query = entityManager.createQuery("SELECT u FROM User u WHERE u.email = :email", User.class);
  query.setParameter("email", email);
  ```
- **Path Traversal**: Validate and normalize user-supplied file paths to prevent directory traversal (`../`).
  ```java
  Path normalized = baseDir.resolve(userInputPath).normalize();
  if (!normalized.startsWith(baseDir)) {
      throw new SecurityException("Unauthorized path access");
  }
  ```
- **Log Injection (CRLF)**: Sanitize user input before logging to prevent fake log injection or exploit payloads (replace `\r` and `\n`).
- **SSRF**: Never fetch user-supplied URLs directly; allowlist hosts/schemes and block internal/metadata addresses.
- **Command Injection**: Avoid `Runtime.exec` with user input; if unavoidable, use `ProcessBuilder` with an argument list (never a shell string).

## 2. Authentication & Authorization

- Use Spring Security (or the framework's standard mechanism); never hand-roll auth, session, or JWT validation.
- Enforce authorization server-side on every request, including object ownership checks (prevent IDOR) — e.g., `@PreAuthorize` on service methods.
- Validate all input at the boundary (Bean Validation); deny by default.
- Return generic error messages to clients; never leak stack traces or internal details.

---

## 3. Sensitive Data & Secrets Management

- **Memory Sanitization for Passwords**:
  - Prefer `char[]` over `String` for passwords and API tokens. `String` is immutable and lingers in the JVM string pool/heap until GC; `char[]` can be explicitly zeroed after use (`Arrays.fill(password, '\0')`).
- **No Hardcoded Secrets**: Load secrets via environment variables or secret vaults (HashiCorp Vault, AWS Secrets Manager).
- **Log Masking**: Mask sensitive fields in `toString()` (override it on records holding secrets) or exclude them (e.g., `@ToString.Exclude`).

---

## 4. Serialization & Parsing Safety

- **Avoid Java Native Serialization**: Java standard serialization (`ObjectInputStream`) is inherently unsafe and a primary vector for remote code execution (RCE). Use JSON, Protocol Buffers, or Jackson.
- **Secure Jackson Configuration**: Avoid global default typing (`enableDefaultTyping()`) which allows arbitrary polymorphic deserialization.
- **XXE Prevention**: Disable external entity resolution (DTD) when parsing XML documents using `DocumentBuilderFactory` or `SAXParser`.

---

## 5. Cryptography Standards

- **Random Numbers**: Always use `java.security.SecureRandom` for cryptographic keys, tokens, and salts. Never use `java.util.Random` or `Math.random()`.
- **Password Hashing**: Use modern adaptive hashing algorithms: **Argon2id** (preferred), **BCrypt**, or **PBKDF2**. Never use MD5, SHA-1, or plain SHA-256 for passwords.
- **Symmetric Encryption**: Use authenticated encryption like **AES-GCM** (256-bit) rather than vulnerable modes like AES-CBC or AES-ECB.

---

## 6. Dependency & Supply Chain Hygiene

- Run automated vulnerability checks during CI/CD builds (e.g., OWASP Dependency-Check, Snyk, or GitHub Dependabot).
- Keep third-party dependencies updated to patch CVEs promptly.

