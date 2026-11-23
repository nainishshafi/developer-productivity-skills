# API Security Audit Checklist & AppSec Review Rubric

A standardized audit checklist for senior security reviewers and automated AI code review agents evaluating authentication, authorization, and cryptographic boundaries.

---

## 1. The 6-Dimension API Security Audit Matrix

### Dimension 1: Token & Secret Storage Hygiene
- [ ] **No Hardcoded Secrets**: Are private keys, HMAC secrets, and database credentials loaded strictly from external environment variables or secret managers (AWS Secrets Manager, Vault)?
- [ ] **Hashed API Keys**: Are B2B API keys stored as one-way cryptographic hashes (`SHA-256`) rather than plaintext?
- [ ] **No Plaintext Tokens in Logs**: Are `Authorization` headers, session cookies, and API keys scrubbed from application access logs?
- [ ] **No Secrets in URLs**: Are access tokens passed via HTTP `Authorization: Bearer <token>` headers instead of query parameters (`?token=...`), which leak in browser history and proxy logs?

### Dimension 2: JWT Security & Verification
- [ ] **Explicit Algorithm Whitelist**: Does the token verification logic enforce an explicit whitelist (e.g. `algorithms=["RS256"]`), blocking `alg: "none"` and asymmetric-symmetric key confusion?
- [ ] **Strict Expiration Checking**: Is the token's `exp` claim verified, and are access tokens constrained to short lifetimes (5–15 minutes)?
- [ ] **Issuer & Audience Validation**: Does the verifier strictly match `iss` and `aud` claims against the calling context?
- [ ] **No PII in Claims**: Is the payload free of sensitive passwords, credit cards, or confidential PII?

### Dimension 3: Session & Cookie Defense
- [ ] **`HttpOnly` Flag Enabled**: Are session cookies marked `HttpOnly` to prevent XSS-based cookie theft?
- [ ] **`Secure` Flag Enabled**: Are session cookies marked `Secure` to ensure transmission strictly over HTTPS?
- [ ] **`SameSite` Attribute Set**: Is `SameSite=Lax` or `SameSite=Strict` configured on all session cookies?
- [ ] **Session Fixation Rotation**: Is the session ID regenerated immediately upon user login or privilege elevation?

### Dimension 4: Webhook & Signature Verification
- [ ] **HMAC Signature Check**: Do incoming webhooks verify `HMAC-SHA256` signatures using a pre-shared secret before processing payload data?
- [ ] **Constant-Time Comparison**: Are signature comparisons performed using constant-time equality checks (e.g. `crypto.timingSafeEqual`, `hmac.compare_digest`) to prevent timing side-channel attacks?
- [ ] **Replay Defense**: Does the webhook verification reject requests with timestamp drift exceeding 300 seconds?

### Dimension 5: Authorization & BOLA/IDOR Defense
- [ ] **Broken Object Level Authorization (BOLA)**: Does every endpoint verify that the authenticated subject (`current_user.id` or `tenant_id`) actually owns the requested resource ID, rather than assuming possessing a valid token grants universal access?
- [ ] **Role & Scope Enforcement**: Are administrative routes guarded by explicit role or scope checks (`require_role("admin")`)?

### Dimension 6: CORS & Cross-Origin Boundaries
- [ ] **No Wildcard with Credentials**: Is `Access-Control-Allow-Origin: *` strictly avoided whenever `Access-Control-Allow-Credentials: true` is enabled?

---

## 2. Severity Classification Standards

| Severity | Definition | Action Required |
|---|---|---|
| **`[P0 - Critical Blocker]`** | Hardcoded private keys/secrets; plaintext API key storage; `alg: "none"` accepted; missing signature verification on webhooks; session cookies lacking `HttpOnly` in production. | **Block deployment immediately.** |
| **`[P1 - Major Vulnerability]`** | Long-lived stateless JWTs (> 2 hours) without revocation mechanism; missing replay defense on webhooks; BOLA/IDOR vulnerability allowing cross-user data access; session fixation on login. | Must fix before production release. |
| **`[P2 - Minor Risk]`** | Naive string comparison (`==`) for HMAC hashes risking timing attacks; overly permissive CORS origins; missing secret scanner prefix (`sk_live_`). | Remediate in next release sprint. |
| **`[P3 - Hardening]`** | Missing `aud` claim verification; lack of structured audit logging for failed authentication attempts. | Recommended security polish. |

---

## 3. High-Impact Vulnerability Code Diffs

### Anti-Pattern 1: Timing Attack on HMAC Signature Comparison
```python
# ❌ VULNERABLE: Standard equality operator terminates early on first mismatched byte (Timing Attack)
if computed_signature == received_signature:
    process_webhook(payload)

# ✅ SECURE: Constant-time comparison takes identical time regardless of character matches
import hmac

if hmac.compare_digest(computed_signature, received_signature):
    process_webhook(payload)
```

### Anti-Pattern 2: Broken Object-Level Authorization (BOLA)
```typescript
// ❌ VULNERABLE: Any authenticated user can view order #1234 by guessing the URL ID!
app.get('/orders/:id', authenticateToken, async (req, res) => {
  const order = await db.orders.findUnique({ where: { id: req.params.id } });
  res.json(order);
});

// ✅ SECURE: Scopes query to the authenticated user's tenant or ID
app.get('/orders/:id', authenticateToken, async (req, res) => {
  const order = await db.orders.findFirst({
    where: { 
      id: req.params.id, 
      userId: req.user.id // BOLA Defense: Enforces ownership!
    }
  });
  if (!order) return res.status(404).json({ error: "Order not found" });
  res.json(order);
});
```
