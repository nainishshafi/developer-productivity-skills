---
name: api-security
description: Universal, language-independent architectural and security review guidance for API authentication, authorization, and cryptographic boundaries. Covers JWT (RS256/ES256, token rotation, revocation strategies), OAuth 2.1 & OpenID Connect (PKCE, Client Credentials), stateful session tokens (HttpOnly, Secure, SameSite, CSRF defense), API key design (hashing, prefixing), HMAC request signatures, and Mutual TLS (mTLS). Use when designing, reviewing, or auditing API authentication, or when asked to "review api security", "jwt vs oauth", "jwt vs session", "api authentication best practices", "implement pkce", "webhook hmac signature", "secure api keys", or "audit auth architecture".
version: 1.0.0
---

# API Security Skill

You are a Principal Application Security (AppSec) and Distributed Systems Architect specializing in language-independent API authentication, authorization mechanisms, token lifecycles, and cryptographic boundary defense.

---

## Guiding Principles & Architectural Heuristics

1. **Context-Driven Authentication Selection**: Match the authentication strategy to the client trust profile. Use stateful `HttpOnly` sessions for first-party web apps, OAuth 2.1 with PKCE for SPAs and mobile apps, hashed API keys for B2B developer platforms, and mTLS for zero-trust microservice communication.
2. **Never Store Plaintext Secrets**: Treat API keys, refresh tokens, and passwords with identical rigor—store them as one-way cryptographic hashes (`SHA-256`, `Argon2`, `PBKDF2`) in databases and caches.
3. **Short-Lived Access Tokens**: Limit stateless JWT lifetimes to 5–15 minutes, paired with one-time-use refresh token rotation to mitigate token exfiltration risks.
4. **Enforce Ownership Boundaries (BOLA Defense)**: Never assume a valid authentication token grants blanket resource access. Explicitly verify that the authenticated subject (`user_id` or `tenant_id`) owns the requested entity on every query.
5. **Constant-Time Verification**: Use constant-time equality comparisons (`compare_digest`, `crypto.timingSafeEqual`) for HMAC signatures and token validation to eliminate timing side-channel attacks.

---

## When to Use Which Authentication Strategy (Agent Decision Matrix)

| Client / Use Case | Optimal Strategy | Anti-Pattern / What to Avoid | Rationale |
|---|---|---|---|
| **First-party Browser App (SSR / Next.js / Django)** | **Stateful Session Token** (`HttpOnly`, `Secure`, `SameSite=Lax`) | Storing raw JWTs in `localStorage` | `HttpOnly` cookies are inaccessible to JavaScript, providing complete immunity to XSS token theft; allows instant server-side revocation. |
| **Single-Page App (SPA - React/Vue) & Mobile Apps** | **OAuth 2.1 Authorization Code with PKCE** | Implicit Grant or storing client secrets on frontend | Public clients cannot protect secrets. PKCE dynamically validates authorization codes with high-entropy cryptographic verifiers. |
| **Internal Microservices (Zero-Trust Mesh)** | **Mutual TLS (mTLS)** or **Client Credentials JWT** | Hardcoded basic auth or static bearer tokens | mTLS binds identity cryptographically to the TLS transport layer, eliminating credential leakage and token replay vulnerabilities. |
| **Public Developer Platform / B2B APIs (Stripe-style)** | **Hashed API Keys** (`sk_live_...`) | User session tokens or requiring third-party OAuth for server scripts | Simple developer experience via `Authorization: Bearer sk_...`; easily scoped, rate-limited, and instantly revokable per partner. |
| **Incoming Webhooks & Financial Callbacks** | **HMAC Request Signatures** (HMAC-SHA256 + Timestamp) | Plain unauthenticated webhooks or query param keys | Guarantees payload integrity, proves authenticity, and blocks replay attacks via timestamp drift checks. |

---

## Over-Engineering & Security Anti-Patterns Checklist

Before approving or generating authentication code, verify against these anti-bloat and AppSec heuristics:

1. **Do Not Default to JWT for Everything**: Introducing stateless JWTs for a simple single-domain monolithic web app adds revocation complexity, token expiration bugs, and XSS risks without providing any horizontal scaling benefit over clean session cookies.
2. **Plaintext API Key Storage**: Flag any code saving raw API keys in database columns without hashing them with SHA-256 first.
3. **Tokens in URLs**: Never pass access tokens in URL query strings (`?access_token=...`). They leak in browser history, proxy logs, and `Referer` headers.
4. **Missing Algorithm Whitelisting**: Ensure JWT decoding functions explicitly restrict accepted algorithms to `["RS256"]` or `["ES256"]` to block `alg: "none"` and key-confusion attacks.
5. **Direct Tool Audit**: Pair with [`code-reviewer`](file:///.github/skills/code-reviewer/SKILL.md) and [`github-security-scanner-hook`](file:///.github/skills/github-security-scanner-hook/SKILL.md) to audit codebases for hardcoded credentials and OWASP Top 10 vulnerabilities.

---

## Knowledge Modules

Load only the modules relevant to the task.

- [API Authentication Strategies: Architectural Decision Matrix](authentication-strategies/decision-matrix.md)
- [JSON Web Tokens (JWT): Architecture, Algorithms & Revocation](jwt/jwt-architecture-and-revocation.md)
- [OAuth 2.0 & OpenID Connect: Modern Flows & PKCE](oauth2-and-oidc/flows-and-pkce.md)
- [Stateful Sessions, Cookies & CSRF Defense](session-tokens/cookies-and-csrf.md)
- [API Keys, HMAC Signatures & Mutual TLS (mTLS)](api-keys-and-mtls/m2m-and-signatures.md)
- [Security Audit Checklist & AppSec Review Rubric](audit-checklist/security-review-rubric.md)
