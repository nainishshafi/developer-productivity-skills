---
name: architectural-planning
description: Use when the user asks to "plan my architecture", "design system architecture",
  "create an architecture document", "help me choose a tech stack", "what technologies
  should I use", "generate an architecture diagram", "plan my project structure",
  "recommend a database for my project", "design my API layer", "create a system design",
  "architecture planning", "tech stack recommendation", or wants interactive guidance
  to design and document a software system's architecture with technology recommendations.
version: 1.1.0
---

# Architectural Planning

Interactively guide the user through architectural decisions for a new or existing software project. Asks structured questions to understand requirements, recommends compatible technologies for each layer, and generates a comprehensive architecture document with Mermaid diagrams, component breakdowns, and a recommended project directory layout.

**Approach:** Step-by-step interactive questionnaire using your environment's question tool (`ask_question` in Antigravity, `AskUserQuestion` in Claude Code, or structured multiple-choice prompts in Copilot Chat), with technology-specific suggestions informed by the compatibility matrices in `references/architectural-planning-reference.md`. When evaluating competing architecture trade-offs, pair with [`llm-as-judge`](file:///.github/skills/llm-as-judge/SKILL.md). Once a stack is selected, delegate implementation conventions to the matching language specialist skill ([`java-developer`](file:///.github/skills/java-developer/SKILL.md), [`typescript-developer`](file:///.github/skills/typescript-developer/SKILL.md), [`python-developer`](file:///.github/skills/python-developer/SKILL.md), [`react-developer`](file:///.github/skills/react-developer/SKILL.md), [`csharp-developer`](file:///.github/skills/csharp-developer/SKILL.md)).

## Prerequisites

- No tools or dependencies required
- Works for any project type (greenfield or existing)
- Interactive session (`ask_question` / `AskUserQuestion` or conversational choice)

## Workflow

### Step 1 — Understand the Project

Use AskUserQuestion to ask the following. Ask both questions in a single AskUserQuestion call (multi-question).

**Question 1 — Project Type:**
> What type of project are you building?

Options:
1. **API / Backend only** — REST API, GraphQL server, or gRPC service with no UI
2. **Frontend only** — SPA or static site consuming an existing API
3. **Full-stack web application** — Backend + frontend in one project
4. **Microservices** — Multiple independent services communicating via APIs or events
5. **CLI tool / Library** — Command-line application or reusable package
6. **Mobile backend** — API optimized for mobile clients (BFF pattern)

**Question 2 — Expected Scale:**
> What is the expected scale of this project?

Options:
1. **Small / Personal** — Single developer, <1K users, simple deployment
2. **Startup / Team** — 2-10 developers, 1K-100K users, need to iterate fast
3. **Enterprise / Large** — 10+ developers, 100K+ users, high availability required

Store both answers as `project_type` and `project_scale` — these determine which follow-up steps to ask and which technologies to recommend.

---

### Step 2 — Choose Backend Stack

**Skip this step if `project_type` is "Frontend only".**

Read `references/architectural-planning-reference.md` Section 1 (Backend Stack Matrix) for detailed comparison.

Use AskUserQuestion:

> Which backend technology stack do you prefer?

Options (include "Best for" from the reference):
1. **Java / Spring Boot 3+ (Java 21/25 LTS)** — Enterprise-grade, virtual threads, strong typing, huge ecosystem. Best for: large teams, microservices, enterprise integrations (see `java-developer`).
2. **TypeScript / Node.js 22+ (Fastify / NestJS / Express)** — Fast iteration, unified TS stack, massive npm ecosystem. Best for: startups, real-time apps, full-stack TS teams (see `typescript-developer`).
3. **Python 3.12+ / FastAPI or Django** — Modern async APIs (FastAPI) or batteries-included web/ORM (Django). Best for: APIs, ML/AI pipelines, data-heavy services (see `python-developer`).
4. **C# 12/13 / .NET 8/9 ASP.NET Core** — High-performance cross-platform runtime, Minimal APIs, built-in DI and Polly resilience. Best for: high-throughput enterprise APIs and cloud-native services (see `csharp-developer`).

Present the remaining options if the user selects "Other" or based on scale:
- **Go** — High performance, built-in concurrency, small static binaries. Best for: microservices, infrastructure tools, high-throughput networking.
- **Rust / Axum or Actix-web** — Maximum performance and memory safety without GC. Best for: latency-critical systems programming.

Store as `backend_stack`.

---

### Step 3 — Choose Frontend Stack

**Skip this step if `project_type` is "API / Backend only", "CLI tool / Library", or "Mobile backend".**

For "Microservices", ask if any service has a frontend before presenting options.

Use AskUserQuestion:

> Which frontend framework do you prefer?

Options:
1. **React** — Component-based, largest ecosystem, flexible. Pairs with: Next.js (SSR), Vite (SPA).
2. **Vue.js** — Gentle learning curve, progressive framework. Pairs with: Nuxt (SSR), Vite.
3. **Angular** — Full framework, TypeScript-first, strong opinions. Best for: enterprise, large teams.
4. **Svelte / SvelteKit** — Compile-time framework, minimal runtime. Best for: performance-focused apps.

Additional options if needed:
- **Next.js (React)** — Full-stack React with SSR/SSG/ISR. Best for: SEO, marketing sites.
- **HTMX + server templates** — Minimal JavaScript, server-rendered. Best for: simple UIs.
- **Server-rendered templates only** — Jinja2, Thymeleaf, Razor, etc. (no separate frontend)

Store as `frontend_stack`. If skipped, set to "N/A".

---

### Step 4 — Choose Database and Data Layer

**Skip this step if `project_type` is "Frontend only".**

Read `references/architectural-planning-reference.md` Section 2 (Database Compatibility Matrix) to present options compatible with `backend_stack`.

Use AskUserQuestion:

> What are your data storage needs?

Options:
1. **PostgreSQL** — Relational, ACID, JSON support, full-text search. The safe default for most projects.
2. **MySQL / MariaDB** — Relational, widely supported, simpler than PostgreSQL.
3. **MongoDB** — Document store, flexible schema. Good for rapid prototyping and varied data shapes.
4. **SQL Server** — Enterprise relational, deep .NET integration, strong BI tooling.

Additional options:
- **DynamoDB** — AWS-native NoSQL, auto-scaling. Best for: serverless, high-scale key-value.
- **SQLite** — Embedded, zero-config, single-file. Best for: small apps, local-first, testing.
- **Redis (as primary)** — In-memory data store for specific use cases (sessions, leaderboards).
- **Multiple** — Need both relational and NoSQL

After the user chooses, **immediately recommend the compatible ORM / data-access library** from the reference file's Database Compatibility Matrix for their `backend_stack + database` combination. Present it as an informational message, e.g.:

> For **Spring Boot + PostgreSQL**, the recommended data access stack is:
> - **ORM:** Spring Data JPA + Hibernate
> - **Connection pool:** HikariCP (included by default)
> - **Migrations:** Flyway
>
> These are the standard choices and work seamlessly together.

Also recommend the migration tool from the Migration Tools table.

Store as `database`, `data_access_library`, and `migration_tool`.

---

### Step 5 — Choose Caching Strategy

Use AskUserQuestion:

> Do you need a caching layer?

Options:
1. **Redis** — Distributed cache, pub/sub, data structures. Industry standard for multi-instance apps.
2. **Memcached** — Simple distributed cache, fast, lightweight. Best for: pure key-value caching.
3. **In-memory only** — Application-level cache (e.g., Caffeine for Java, node-cache for Node.js, lru_cache for Python). Best for: single-instance apps.
4. **No caching needed** — Skip for now

Additional options:
- **CDN caching** — Edge caching for static assets and API responses (CloudFront, Cloudflare, Fastly).
- **Multi-layer** — Combine in-memory + distributed + CDN

After the user chooses, recommend the specific library from `references/architectural-planning-reference.md` Section 3 (Caching Library Matrix) for their `backend_stack + caching` combination.

Store as `caching_strategy` and `cache_library`.

---

### Step 6 — Choose Authentication and Authorization

**Skip this step if `project_type` is "CLI tool / Library".**

Use AskUserQuestion:

> How will you handle authentication?

Options:
1. **JWT tokens** — Stateless auth, good for APIs and SPAs. Implement with framework-native libraries.
2. **Session-based** — Server-side sessions with cookies. Traditional, simpler for server-rendered apps.
3. **OAuth 2.0 / OpenID Connect** — Delegate to identity providers (Google, GitHub, etc.).
4. **Managed service (Auth0 / Firebase / Cognito)** — Offload auth complexity entirely.

Additional options:
- **Keycloak** — Self-hosted identity server. Best for: enterprise, on-prem, full control.
- **API keys** — Simple key-based auth for service-to-service or public APIs.
- **Framework built-in** — Use the framework's native auth (Django Auth, Spring Security, ASP.NET Identity)

After the user chooses, recommend the specific library from `references/architectural-planning-reference.md` Section 4 (Authentication Library Matrix) for their `backend_stack + auth` combination.

Store as `auth_approach` and `auth_library`.

---

### Step 7 — Choose Messaging and Events

**Skip this step if `project_scale` is "Small / Personal" AND `project_type` is NOT "Microservices".**

Use AskUserQuestion:

> Do you need asynchronous messaging or event-driven communication?

Options:
1. **Apache Kafka** — High-throughput event streaming, durable log. Best for: event sourcing, data pipelines.
2. **RabbitMQ** — Traditional message broker, flexible routing. Best for: task queues, RPC patterns.
3. **AWS SQS / SNS** — Managed queues and pub/sub. Best for: AWS-native, serverless.
4. **No messaging needed** — Skip for now

Additional options:
- **Redis Pub/Sub** — Lightweight pub/sub for simple real-time notifications.
- **NATS** — Lightweight, high-performance. Best for: microservices, cloud-native.

Store as `messaging`. If skipped, set to "None".

---

### Step 8 — Choose Deployment Strategy

Use AskUserQuestion. Ask both in a single call.

**Question 1 — Deployment:**
> How do you plan to deploy?

Options:
1. **Docker + Kubernetes** — Container orchestration, auto-scaling. Best for: microservices, large-scale.
2. **Docker + Docker Compose** — Simple container deployment. Best for: small teams, single-server.
3. **Serverless** — AWS Lambda / Azure Functions / GCP Cloud Functions. Best for: event-driven, pay-per-use.
4. **PaaS** — Heroku, Railway, Render, Fly.io. Best for: rapid deployment, no infra management.

Additional options:
- **Traditional VM / VPS** — EC2, DigitalOcean, Linode. Best for: full control, predictable costs.
- **Cloud-managed containers** — AWS ECS/Fargate, Azure Container Apps, GCP Cloud Run.
- **Edge deployment** — Cloudflare Workers, Vercel Edge, Deno Deploy.

**Question 2 — Cloud Provider:**
> Which cloud provider (if any)?

Options:
1. **AWS** 2. **Azure** 3. **Google Cloud** 4. **No preference / Self-hosted**

Store as `deployment` and `cloud_provider`.

---

### Step 9 — Choose CI/CD Pipeline

Use AskUserQuestion:

> What CI/CD platform do you prefer?

Options:
1. **GitHub Actions** — Native to GitHub, free for public repos, huge marketplace.
2. **GitLab CI** — Built into GitLab, powerful pipelines, self-hostable.
3. **Jenkins** — Self-hosted, extensible, enterprise standard.
4. **Other / No preference** — CircleCI, AWS CodePipeline, Azure DevOps, etc.

Store as `cicd`.

---

### Step 10 — Choose Monitoring and Observability

Use AskUserQuestion:

> What monitoring and observability tools do you want?

Options:
1. **Datadog** — Full-stack observability (metrics, traces, logs). Enterprise standard.
2. **Prometheus + Grafana** — Open-source metrics and dashboards. Best for: self-hosted, Kubernetes.
3. **Cloud-native** — AWS CloudWatch / Azure Monitor / GCP Cloud Monitoring.
4. **Basic logging only** — Framework-native logging, no external tools for now.

Additional options:
- **ELK Stack** — Open-source log aggregation and analysis.
- **OpenTelemetry + Jaeger** — Vendor-neutral distributed tracing.
- **Sentry** — Error tracking and performance monitoring.
- **Multiple** — Combine (e.g., Prometheus for metrics + ELK for logs + Sentry for errors)

Store as `monitoring`.

---

### Step 11 — Confirm and Generate

**11a. Present the decision summary.** Display a table of all decisions made:

```
| Layer              | Choice                    |
|--------------------|---------------------------|
| Project Type       | {project_type}            |
| Scale              | {project_scale}           |
| Backend            | {backend_stack}           |
| Frontend           | {frontend_stack}          |
| Database           | {database}                |
| ORM / Data Access  | {data_access_library}     |
| Migrations         | {migration_tool}          |
| Caching            | {caching_strategy}        |
| Authentication     | {auth_approach}           |
| Messaging          | {messaging}               |
| Deployment         | {deployment}              |
| Cloud Provider     | {cloud_provider}          |
| CI/CD              | {cicd}                    |
| Monitoring         | {monitoring}              |
```

**11b. Ask for confirmation.** Use AskUserQuestion:

> Here is your architecture summary. What would you like to do?

Options:
1. **Generate the architecture document** — Proceed to output
2. **Change a decision** — Go back and modify a choice
3. **Add more detail** — Discuss specific areas further before generating

If "Change a decision", ask which layer to change and re-run that step.

**11c. Ask for output location.** Use AskUserQuestion:

> Where should I write the architecture document?

Options:
1. **ARCHITECTURE.md** — In the project root (recommended)
2. **.architecture/architecture-{timestamp}.md** — In a dedicated directory
3. **Custom path** — Specify a path

**11d. Generate the document.** Read the output document template from `references/architectural-planning-reference.md` Section 6 and generate the full architecture document:

1. Replace all `{PLACEHOLDER}` values with the user's actual choices
2. Select the appropriate Mermaid diagram from Section 5 based on `project_type` and customize it with actual technology names
3. Select the project structure from Section 7 based on `backend_stack`
4. Build the dependency table from Section 8 (Library Version Reference) for the chosen stack
5. Customize all 11 sections of the document with specific, actionable content
6. Scale the document depth based on `project_scale` — simpler projects get more concise sections, enterprise projects get more detailed coverage

Write the generated document to the chosen path using the Write tool. If using the `.architecture/` directory, create it first.

**11e. Present the result.** Tell the user the document has been written and summarize the key architectural decisions. Offer to dive deeper into any specific section.

## Additional Resources

- **`references/architectural-planning-reference.md`** — Technology compatibility matrices (backend × database, backend × cache, backend × auth), Mermaid diagram templates for monolith/microservices/serverless/deployment topologies, complete output document template with 11 sections, project structure templates per stack, and library version reference
