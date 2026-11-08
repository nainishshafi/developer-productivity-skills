# API Authentication Strategies: Architectural Decision Matrix

Selecting an authentication mechanism is a foundational architectural decision that dictates scalability, latency, client complexity, and security posture. There is no single "best" authentication mechanism; the correct choice depends on client trust, network boundaries, and revocation requirements.

---

## 1. High-Level Comparison Matrix

| Strategy | Client Type | State / Storage | Revocation Speed | Latency Overhead | Key Strength | Primary Risk / Trade-Off |
|---|---|---|---|---|---|---|
| **Stateless JWT (Bearer)** | Mobile apps, SPAs, cross-domain microservices | Stateless (Self-contained signature) | Difficult (Requires Redis blacklist or token version epoch) | Zero DB/Cache lookup on verify (< 0.1 ms) | Scalable horizontally across thousands of services without database bottleneck. | Token cannot be revoked instantly without central state; payload size overhead (~500B–2KB per request). |
| **OAuth 2.0 / OIDC** | Third-party integrations, enterprise SSO, mobile/SPA delegation | Centralized Identity Provider (Auth0, Okta, Keycloak) | Fast via IdP / Introspection | Low with cached JWKS; high if full introspection per request | Delegated authorization, standard federation, granular scopes. | High implementation complexity; requires managing grants, redirects, and JWKS key rotation. |
| **Stateful Session Token** | First-party web apps, SSR frontends (Next.js, Django, Rails) | Stateful (Session ID in DB or Redis) | **Instant** (Delete key from Redis/DB) | 0.5–2.0 ms (Redis/DB lookup per request) | Instant revocation, simple client management, protected from XSS via `HttpOnly`. | Sensitive to CSRF; requires central session store (Redis) to scale horizontally. |
| **API Keys** | Server-to-server B2B integrations, developer APIs (Stripe, GitHub) | Hashed key in database/cache | Instant (Set key status = `revoked`) | 0.5–1.0 ms (Lookup hashed key in cache/DB) | Simple client developer experience (header `Authorization: Bearer sk_...`); easily scoped and metered. | Susceptible to leakage if logged or hardcoded; client cannot safely store secret on frontend. |
| **mTLS (Mutual TLS)** | Internal service-to-service, zero-trust microservice meshes | Cryptographic (X.509 certificates verified in TLS handshake) | Fast via CRL / OCSP stapling | Zero application layer overhead (handled at TLS termination) | Cryptographic identity verification at transport layer; completely immune to token replay and phishing. | Complex PKI / certificate lifecycle management (issuance, rotation, expiration). |
| **HMAC Request Signatures** | Webhooks, high-security B2B financial APIs (AWS SigV4, Stripe) | Shared secret + cryptographic signature over payload | Instant (Revoke shared secret) | < 0.1 ms (Local HMAC calculation in memory) | Guarantees payload integrity and non-repudiation; immune to replay attacks via timestamp and nonce. | Requires canonical request string serialization on both client and server; sensitive to whitespace drift. |

---

## 2. Decision Tree: Choosing the Right Strategy

```mermaid
flowchart TD
    Start[Who is the caller / client?] --> ClientType{Caller Category}

    ClientType -->|First-party Browser SPA / SSR| SameDomain{Same domain as API?}
    SameDomain -- Yes --> SessionCookie[Stateful Session Cookie<br>HttpOnly, Secure, SameSite=Lax]
    SameDomain -- No / Multi-Domain --> JWT_Auth[Short-Lived JWT + Refresh Token<br>or OAuth2 PKCE]

    ClientType -->|Mobile / Native App| MobileFlow[OAuth 2.1 Authorization Code with PKCE<br>Token in OS Secure Enclave / Keyring]

    ClientType -->|Third-Party Developer / B2B| B2BType{Integration Pattern}
    B2BType -- Standard Developer API --> HashedAPIKey[Hashed API Keys<br>Prefix: sk_live_...<br>Stored as SHA-256 hash]
    B2BType -- Webhook Delivery / Notification --> HMACSig[HMAC Signature with Timestamp & Secret<br>e.g. Stripe-Signature header]

    ClientType -->|Internal Service-to-Service Microservices| MeshType{Infrastructure Mesh}
    MeshType -- Zero-Trust Service Mesh / Kubernetes --> mTLS[mTLS with SPIFFE/X.509 Certs]
    MeshType -- Cloud Microservices without Mesh --> ClientCreds[OAuth 2.0 Client Credentials Grant<br>M2M Signed JWT]
```

---

## 3. Defense-in-Depth Authentication Architecture

In enterprise architectures, multiple authentication mechanisms are often layered:

```mermaid
flowchart LR
    subgraph Public_Clients["External Ingress"]
        Browser[Browser SPA] -->|Session Cookie / PKCE| APIGateway[API Gateway / Ingress]
        Mobile[Mobile App] -->|OAuth2 Bearer JWT| APIGateway
        B2BPartner[B2B Partner] -->|API Key + HMAC Signature| APIGateway
    end

    subgraph Internal_Mesh["Internal Zero-Trust Mesh"]
        APIGateway -->|Translate to Internal Signed JWT + mTLS| OrderService[Order Service]
        OrderService -->|mTLS + Service Identity| PaymentService[Payment Service]
        PaymentService -->|mTLS| LedgerService[Ledger Service]
    end
```
