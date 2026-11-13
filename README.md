# Developer Productivity Skills

A curated suite of enterprise-grade AI skills and Model Context Protocol (MCP) servers for **Claude Code**, **Antigravity**, and **GitHub Copilot**. 

Designed as **architectural guidance, decision frameworks, and engineering heuristics for AI agents** — anchored by the autonomous [**`software-factory-agent`**](.github/agents/software-factory-agent.md) — rather than rigid or deterministic rules, empowering agents to respect existing codebase baselines, reason through real-world trade-offs, and deliver high-signal, pragmatic engineering solutions.

> [!TIP]
> **Autonomous End-to-End Delivery**: Use the [**Software Factory Agent**](.github/agents/software-factory-agent.md) (`"run software factory"` — see [details](#software-factory-agent-githubagentssoftware-factory-agentmd)) as a single entry point to orchestrate all repository skills and MCP servers (`project-memory`, `sql-connector`, `nodejs-executor`) across planning, BDD specs, quality gates, self-healing remediation, and periodic `skill-doctor` evolution.

These skills provide ready-made workflows for modern software engineering across ten core engineering disciplines:

- **🏗️ Architectural Planning & Trade-Offs**: Interactive system design, Mermaid modeling, component contracts, and Architecture Decision Records (ADRs) grounded in established literature (Kleppmann, Nygard, Newman, Evans, Fowler).
- **📦 Language-Specific Engineering Packs**: Modular, context-optimized guides for modern runtimes (Java 21/25 Virtual Threads, TypeScript 5+ branded types, Python 3.10–3.13 Pydantic v2, C# 12/13 Minimal APIs, React 19 RSC, PowerShell 7+), each with embedded anti-bloat guardrails.
- **🚀 Multi-Agent SDLC Orchestration**: End-to-end 7-stage pipeline (`plan` $\to$ `develop` $\to$ `codereview` $\to$ `complexitychecks` $\to$ `architecturechecks` $\to$ `halucinationchecks` $\to$ `securitychecks`) enforcing stage-isolated context handoffs to prevent context pollution and attention drift.
- **💾 Project Memory Bus**: Long-term state persistence via SQLite (`.project-memory/memory.db`) with 40% semantic hybrid search, strictly partitioning knowledge into permanent architecture truths (`ledger`), active WIP handoffs (`sidecar`), and stage recaps with mandatory error learnings (`journal`).
- **🧬 Continuous Skill Evolution (`skill-doctor`)**: Periodically harvests unprocessed `journal` and `ledger` learnings from `project-memory`, updates existing skill submodules without router bloat or scaffolds new skills via `skill-creator`, audits frontmatter/links, and marks processed learnings `promoted` or `skipped`.
- **🛡️ In-The-Loop Over-Engineering Defense**: Continuous AST signal extraction (`detect-overengineering`) embedded directly into four loops: developer inner loop, PR review audits, architecture gates (triggering an automated simplification loop when score $\ge 40$), and bug fixes (anti-fix-bloat).
- **⏱️ Asymptotic Big-O Complexity Audits**: Algorithmic time and space profiling ($O(1) \dots O(2^n)$), detecting hidden quadratic collection traps (`.includes()` in loops), and database query execution plan audits ($O(N)$ table scans).
- **🔬 Empirical Research & PoC Benchmarking**: Validates architectural trade-offs through isolated side-by-side testbeds (`scratch/pocs/`) with automated JIT warmup discarding, monotonic timers, and multi-iteration statistical distributions (Median P50, P95, P99, StdDev, ops/sec) to empirically measure real-world performance (e.g., Virtual Threads I/O vs CPU concurrency, Polars Arrow vs NumPy SIMD, DB batching vs cursor streaming).
- **🔍 Isolated Debugging & Circuit Breakers**: Extracting failures into minimal standalone testbeds (`scratch/repro/`) with a strict 3-iteration circuit breaker to eliminate token-burning retry loops.
- **🔐 Pre-Commit Security & Query Firewalls**: Secret scanning (`detect-secrets`), OWASP rule evaluation (`semgrep`), universal API authentication audits (JWT RS256, OAuth 2.1 PKCE, mTLS), and zero-tolerance destructive SQL firewalls (`DROP TABLE`, `DELETE *`).

---

## 📑 Skills Catalog

| Skill | Category | Core Purpose | Primary Trigger Phrase |
|---|---|---|---|
| [`agent-orchestrator`](#agent-orchestrator) | **Orchestration** | 7-stage multi-agent SDLC with memory tracking & in-the-loop over-engineering checks | `"orchestrate a feature"` |
| [`llm-as-judge`](#llm-as-judge) | **Orchestration** | 4 evaluator styles (Pessimist, Contrarian, Pragmatist, Specialist), rubrics & consensus | `"judge this response"` |
| [`typescript-developer`](#typescript-developer) | **Language Specialist** | Node.js, TS 5+, Zod, Drizzle/Prisma, event loop hygiene | `"write typescript code"` |
| [`python-developer`](#python-developer) | **Language Specialist** | Python 3.10–3.13, Pydantic v2, asyncio, memory/GC | `"write python code"` |
| [`python-api-writer`](#python-api-writer) | **Language Specialist** | FastAPI vs. Django, async event loop hygiene, Lifespan, Pydantic v2 | `"write python api"` |
| [`react-developer`](#react-developer) | **Language Specialist** | React 18/19, Next.js RSC, Zustand, TanStack Query | `"write react code"` |
| [`java-developer`](#java-developer) | **Language Specialist** | Java 17/21/25, Spring Boot 3+, Virtual Threads, Low-Latency, Spring Batch | `"write java code"` |
| [`csharp-developer`](#csharp-developer) | **Language Specialist** | C# 12/13, .NET 8/9, Minimal APIs, MVVM/WPF, EF Core | `"write c# code"` |
| [`powershell-writer`](#powershell-writer) | **Language Specialist** | Advanced cmdlets, object pipelines, Set-StrictMode, Pester v5, modules | `"write powershell script"` |
| [`code-reviewer`](#code-reviewer) | **Architecture & Quality** | 7-dimension senior review ([P0] Blocker to [P3] Nit) | `"review code"` |
| [`api-security`](#api-security) | **Architecture & Quality** | JWT, OAuth 2.1 PKCE, session cookies, API keys, mTLS, HMAC | `"review api security"` |
| [`algorithmic-complexity-analyzer`](#algorithmic-complexity-analyzer) | **Architecture & Quality** | Big-O time/space audits ($O(1) \dots O(2^n)$), hidden loop traps | `"check time complexity"` |
| [`caching-queues-reviewer`](#caching-queues-reviewer) | **Architecture & Quality** | Redis, Kafka, Lua scripts, stampede defense, multi-language caching | `"review caching code"` |
| [`sql-executor`](#sql-executor) | **Architecture & Quality** | Cross-engine joins, GIN/GiST/BRIN indexes, CTEs, #temp tables, OLAP cubing, TVFs | `"write a sql join"` |
| [`detect-overengineering`](#detect-overengineering) | **Architecture & Quality** | YAGNI audits, layer bloat, trampoline pass-throughs, in-the-loop checks | `"check for over-engineering"` |
| [`design-pattern-detector`](#design-pattern-detector) | **Architecture & Quality** | Structural AST extraction of design patterns & anti-patterns | `"detect design patterns"` |
| [`architectural-planning`](#architectural-planning) | **Architecture & Quality** | Interactive system design, Mermaid specs, ADRs & foundational book references | `"plan my architecture"` |
| [`rag-pipeline`](#rag-pipeline) | **Architecture & Quality** | End-to-end RAG architecture, hybrid search (BM25 + RRF), chunking, reranking & IR evaluation | `"build rag pipeline"` |
| [`scan-halucinated-tests`](#scan-halucinated-tests) | **Architecture & Quality** | Cross-validates test symbols against AST ground truth | `"scan for hallucinated tests"` |
| [`trace-code-context`](#trace-code-context) | **Architecture & Quality** | AST symbol extraction, callers/callees & Mermaid graph | `"trace code context"` |
| [`playwright-tester`](#playwright-tester) | **Testing & Quality** | End-to-End browser test automation with Microsoft Playwright | `"write playwright tests"` |
| [`bdd-gherkin-tester`](#bdd-gherkin-tester) | **Testing & Quality** | BDD Gherkin & BDD runner integration (`playwright-bdd`, `pytest-bdd`, Cucumber, Reqnroll) | `"write gherkin feature"` |
| [`test-data-creator`](#test-data-creator) | **Testing & Quality** | Schema-aware SQL batching, JSON mocks & high-volume load test data (Pareto 80/20) | `"generate test data"` |
| [`remote-pod-log-analyzer`](#remote-pod-log-analyzer) | **Diagnostics** | Remote Linux & Kubernetes pod log analysis via SSH, kubectl, grep, awk, jq | `"analyze remote logs"` |
| [`troubleshoot-and-fix`](#troubleshoot-and-fix) | **Diagnostics** | Isolated reproduction testbeds, 3-attempt circuit breaker & anti-fix-bloat | `"troubleshoot and fix"` |
| [`researcher-poc-tester`](#researcher-poc-tester) | **Research & Benchmarking** | Isolated side-by-side PoCs, JIT warmup & percentile stats (VThreads, Polars, DB throughput) | `"test this concept"` |
| [`legacy-code-modernization`](#legacy-code-modernization) | **Modernization** | 4-phase safe modernization (Extract $\to$ Pin $\to$ TDD $\to$ Strangler) | `"modernize legacy code"` |
| [`skill-creator`](#skill-creator) | **Tooling & Automation** | Scaffolds modular knowledge-packs and task skills | `"create a new skill"` |
| [`skill-doctor`](#skill-doctor) | **Tooling & Automation** | Promotes unprocessed `project-memory` learnings into skill updates or new skills | `"run skill doctor"` |
| [`github-security-scanner-hook`](#github-security-scanner-hook) | **Tooling & Automation** | Pre-commit secret scanning & Semgrep OWASP rules | `"scan for security vulnerabilities"` |
| [`python-linter`](#python-linter) | **Tooling & Automation** | Automated Ruff linting, formatting & Mypy typing | `"lint python"` |
| [`sync-github-forks`](#sync-github-forks) | **Tooling & Automation** | Automated cross-platform syncing of all GitHub forks | `"sync github forks"` |
| [`scan-repo-readme`](#scan-repo-readme) | **Tooling & Automation** | Dual-phase keyword and semantic README search | `"scan the readme"` |
| [`save-memory`](#save-memory) | **Memory & Context** | Persists ledger, sidecar, and journal memories to SQLite | `"save memory"` |
| [`load-memory`](#load-memory) | **Memory & Context** | Hybrid semantic (40%) + lexical (60%) memory retrieval | `"load memory"` |
| [`nodejs-executor`](#nodejs-executor) | **Tooling & Automation** | Sandboxed JavaScript/TypeScript execution via MCP | `"run nodejs code"` |
| [`sql-connector`](#sql-connector) | **Database & Tooling** | Multi-DB query & schema inspection with zero-tolerance destructive DDL/DML firewall | `"query database"` |

---

## 🧠 1. Language & Framework Engineering Skills

Modular knowledge packs designed with lean routers (< 60 lines) and deep single-responsibility topic modules loaded selectively to keep context windows lean. All architectural recommendations are designed as **contextual engineering guidelines and heuristics rather than deterministic rules**—the AI agent must consult the dedicated **"When to Use" decision matrix** in each skill to weigh real-world trade-offs, match existing project conventions, and avoid dogmatic abstractions. Additionally, every language specialist includes an integrated **Over-Engineering Self-Check (Anti-Bloat Guardrail)** backed by [`detect-overengineering`](#detect-overengineering) to prevent introducing premature abstractions, 1:1 single-implementation interfaces, trampoline pass-through layers, or pattern ceremony.

### `typescript-developer`
Architectural and engineering guidance for modern TypeScript and JavaScript (Node.js 20+, ES2023+, TS 5+).
- **Core Topics:** Dependency Injection (Pure DI composition roots, NestJS IoC scopes, custom providers, circular dependency avoidance), Modern Design Patterns (Strategy, Factory, Builder, Decorators, Adapter, Observer, Repository & Unit of Work), Hexagonal/Modular/Layered architectures, discriminated unions, branded types, Result pattern, runtime validation (Zod & Valibot), ORMs (Drizzle & Prisma), event loop health, worker_threads, stream backpressure (`pipeline`), closure scope hygiene, and `p-limit` concurrency throttling.
- **Trigger phrases:** `"write typescript code"`, `"develop typescript service"`, `"typescript dependency injection"`, `"typescript design patterns"`, `"typescript architecture best practices"`, `"design node backend"`, `"vitest testing"`, `"modern nodejs patterns"`, `"refactor javascript"`.
- **Supported runtimes:** Node.js 20+, TypeScript 5.x+.

### `python-developer`
Architectural and engineering guidance for modern Python development (3.10–3.13).
- **Core Topics:** Dependency Injection (structural subtyping via `typing.Protocol`, FastAPI `Depends`, dependency overrides, `dependency-injector` containers), Pythonic Design Patterns (Strategy via callables, Factory classmethods, Decorator with `functools.wraps`, Adapter, Repository/UnitOfWork), Data Engine Selection (NumPy homogeneous SIMD arrays vs. Polars multithreaded Apache Arrow DataFrames vs. legacy Pandas), Built-in Collection Optimization (`deque` for FIFO/sliding windows, `heapq` for priority queues, `set` for $O(1)$ membership, `array.array`, `@dataclass(slots=True)`), Hexagonal & service-repository architectures, Pydantic v2 enterprise validation (`ConfigDict`, `@field_validator`, `@model_validator`, `TypeAdapter`, `pydantic-settings`), memory cycle prevention (`weakref`), late-binding closure fixes, and non-blocking `asyncio` (`asyncio.TaskGroup`, `asyncio.to_thread`).
- **Trigger phrases:** `"write python code"`, `"develop python service"`, `"python dependency injection"`, `"python design patterns"`, `"numpy vs polars"`, `"python data structures"`, `"polars dataframe"`, `"python architecture best practices"`, `"design python backend"`, `"pytest guidelines"`, `"modern python patterns"`, `"refactor python"`.
- **Supported versions:** Python 3.10, 3.11, 3.12, 3.13.

### `python-api-writer`
Architectural and engineering guidance for building modern Python APIs with FastAPI and Django (including Django REST Framework and Django Ninja).
- **Core Topics:** Framework selection (FastAPI vs Django trade-offs), 4-tier data boundaries (Request DTO $\to$ Domain Entity $\to$ DB Model $\to$ Response DTO), request/response validation (Pydantic v2 schemas, `@field_validator`, `@model_validator`, `@computed_field`, discriminated unions, DRF serializers), Aspect-Oriented Programming (AOP & decorators for auditing, retries with jitter, service caching, OpenTelemetry tracing), Lifespan context managers (`@asynccontextmanager`), modular `APIRouter` composition, Dependency Injection (`Depends`), Django service layer pattern, QuerySet optimization (`select_related`, `prefetch_related`, `only`, `defer`), SQLAlchemy 2.0 async eager loading (`joinedload`, `selectinload`), connection pool sizing, async event loop hygiene (preventing blocking calls in `async def`), JWT/session auth, CORS defense, rate limiting, and automated testing (`httpx.AsyncClient` & `pytest-django`).
- **Trigger phrases:** `"write python api"`, `"fastapi best practices"`, `"django api best practices"`, `"fastapi vs django"`, `"django ninja"`, `"fastapi validation"`, `"pydantic api validation"`, `"python aop"`, `"python decorators"`, `"fastapi dependency injection"`, `"build python backend"`, `"design python api"`.
- **Supported frameworks:** FastAPI, Django 4.2/5+, Django REST Framework (DRF), Django Ninja.

### `react-developer`
Architectural and engineering guidance for modern React (React 18 & 19, Next.js App Router, Vite, React Server Components).
- **Core Topics:** Presentational vs container architecture, compound component pattern, Prop Drilling Hell resolution (Inversion of Control via `children`/slots, Query/RSC colocation, scoped Context, Zustand), Functional Programming in React (`UI = f(state)`, referential transparency, ES2023 non-mutating methods `toSorted`/`toSpliced`/`with`, Functional Core / Imperative Shell, eliminating procedural `let` ladders and `useEffect` chains), React 18 & 19 hooks (`useState` lazy init, `useReducer` state machines, `"You Might Not Need an Effect"`, `useLayoutEffect`, `useTransition`, `useDeferredValue`, `use()`, `useActionState`, `useFormStatus`, `useOptimistic`, `ref` as a prop, Latest-Ref custom hook patterns), server state vs client state, global stores with Zustand (slice pattern, `useShallow`, non-React mutations), TanStack Query v5 cache lifecycles & optimistic updates, Redux Toolkit entity adapters, stale closure prevention, `AbortController` unmount teardown, `useSyncExternalStore`, DOM virtualization, comprehensive React testing (Vitest, React Testing Library, MSW v2, fake timers, `renderWithProviders`, Zustand/TanStack Query rollback tests, React 19 actions, RSC testing, `vitest-axe`), and an 8-dimension React Code Review & Clean Code audit (`[P0]`–`[P3]`).
- **Trigger phrases:** `"write react code"`, `"develop react component"`, `"react architecture best practices"`, `"nextjs server components"`, `"refactor react frontend"`, `"react 19 actions"`, `"react hooks"`, `"custom hook patterns"`, `"useeffect best practices"`, `"functional programming react"`, `"declarative react patterns"`, `"react code review"`, `"react clean code"`, `"react testing"`, `"react testing library"`, `"test react component"`.
- **Supported environments:** React 18, React 19, Next.js App Router, Remix / React Router v7, Vite.

### `java-developer`
Comprehensive architectural and engineering guidance for modern Java (LTS 17/21/25) and Spring Boot enterprise applications.
- **Core Topics:** Feature decision matrices (when to use records vs classes, virtual threads vs CompletableFuture, sealed ADTs vs enums, JPA vs JdbcClient), Dependency Injection patterns & scopes (constructor injection, captive dependency avoidance, `@RequestScope` proxies), Modern Design Patterns (Strategy via functions, Observer via domain events, Visitor via sealed pattern matching, Builder, Outbox), zero-reflection execution (MethodHandles, VarHandle, MapStruct, GraalVM AOT hints), low-latency architecture & mechanical sympathy (CPU cache lines, false sharing, `@Contended`, zero-allocation steady states, off-heap FFM `Arena`, LMAX Disruptor, Chronicle Queue), enterprise data pipelines (Spring Batch chunk-oriented steps, `JdbcTemplate` & `JdbcClient` cursor streaming, bulk inserts without GC bottlenecks), Virtual Threads & carrier pinning avoidance, collections selection, JVM tuning (Generational ZGC/G1), and Spring Boot 3+ production patterns.
- **Trigger phrases:** `"write java code"`, `"develop java service"`, `"java dependency injection"`, `"java design patterns"`, `"java architecture best practices"`, `"spring boot best practices"`, `"low latency java"`, `"spring batch pipeline"`, `"zero reflection java"`, `"optimize jvm"`, `"write java unit test"`, `"design java service"`, `"java concurrency guide"`, `"virtual threads vs reactor"`, `"migrate to spring boot 3"`.
- **Supported versions:** Java 17, 21, 25 LTS; Spring Boot 3.x.

### `csharp-developer`
Comprehensive architectural and engineering guidance for modern C# (C# 12 & 13, .NET 8 LTS & .NET 9), ASP.NET Core, and cross-platform desktop/client development.
- **Core Topics:** Modern idioms (primary constructors, collection expressions, records, required members, frozen collections), Clean Architecture & Vertical Slice Architecture, Dependency Injection lifetimes & captive dependency prevention, Modern C# Design Patterns (Keyed services for Strategy/Factory, Decorators via Scrutor, Observer via MediatR events, Specification pattern), Minimal APIs (`TypedResults`), RFC 7807 problem details, Polly v8 resilience pipelines (`AddStandardResilienceHandler`), MVVM (`CommunityToolkit.Mvvm`, `WeakReferenceMessenger`, WPF & .NET MAUI thread dispatching), EF Core 8/9 query optimization (split queries, bulk updates, DbContext pooling), Dapper high-throughput queries, zero-allocation memory hygiene (`ReadOnlySpan<T>`, `Memory<T>`, `ArrayPool<T>`, static lambdas), asynchronous backpressure (`System.Threading.Channels`), and modern test stacks (xUnit, NSubstitute, FluentAssertions, `WebApplicationFactory`, Testcontainers.NET).
- **Trigger phrases:** `"write c# code"`, `"develop c# service"`, `"c# dependency injection"`, `"c# design patterns"`, `"c# architecture best practices"`, `"minimal apis best practices"`, `"wpf mvvm guide"`, `"maui mvvm"`, `"ef core query optimization"`, `"polly resilience pipeline"`, `"c# span memory optimization"`.
- **Supported runtimes:** .NET 8 LTS, .NET 9; C# 12, C# 13.

### `powershell-writer`
Staff-level architectural and engineering guidance for modern PowerShell automation, advanced cmdlets, and enterprise modules (PowerShell 7.4+ LTS & Windows PowerShell 5.1).
- **Core Topics:** Advanced functions (`[CmdletBinding()]`, approved verbs from `Get-Verb`, pipeline streaming `begin`/`process`/`end`/`clean`, parameter validation attributes), defensive error handling (`$ErrorActionPreference = 'Stop'`, `Set-StrictMode -Version Latest`, `try/catch` with typed exceptions, `$LASTEXITCODE` validation), Anti-Bloat Guardrails (script vs. module decision matrix, eliminating the $O(N^2)$ array append antipattern `$arr += $item`), Object Pipeline streaming, `[PSCustomObject]` emission, calculated properties, parameter splatting (`@params`), REST APIs (`Invoke-RestMethod` vs. `Invoke-WebRequest`), JSON depth limits (`-Depth 10`), parallel concurrency (`ForEach-Object -Parallel`, `Start-ThreadJob`, `RunspacePool`, thread-safe synchronized hashtables), professional module architecture (`.psm1`, `.psd1` manifests, `Export-ModuleMember`, `Test-ModuleManifest`), script security (`Invoke-Expression` ban, `SecretManagement`, Constrained Language Mode), and unit testing with Pester v5 & PSScriptAnalyzer.
- **Trigger phrases:** `"write powershell"`, `"write powershell script"`, `"powershell-writer"`, `"powershell cmdlet"`, `"create powershell module"`, `"ps1 script"`, `"pester test"`, `"powershell automation"`, `"powershell best practices"`, `"powershell error handling"`.
- **Supported runtimes:** PowerShell 7.4+ LTS (Core), Windows PowerShell 5.1 (Desktop).

---

## 📐 2. Architecture, Quality & Review Skills

Review and audit skills operate on **pragmatic heuristics and evidence-driven severity tiers** rather than deterministic rules—evaluating findings within the context of project scale, team conventions, and operational trade-offs.

### `code-reviewer`
Senior-level code review across languages (Python, TypeScript/JavaScript, React/Next.js, Java, C#, Go, SQL, PowerShell). Audits changes across 7 dimensions: correctness, architecture (SOLID/DRY/KISS), error handling, test coverage, security defense, performance & memory hygiene, and readability. Features dedicated language subdirectories with deep checklists. Standardizes findings into `[P0 - Blocker]`, `[P1 - Major]`, `[P2 - Minor]`, and `[P3 - Nit]` with concrete suggested fix diffs.
- **Trigger phrases:** `"review code"`, `"code review"`, `"review pull request"`, `"audit code changes"`, `"code review checklist"`, `"review this diff"`.

### `api-security`
Universal, language-independent architectural and security review guidance for API authentication, token lifecycles, and cryptographic boundary defense. Covers JWT architecture (RS256/ES256, token rotation, revocation strategies), OAuth 2.1 & OpenID Connect (PKCE for SPAs/mobile, Client Credentials for M2M), stateful session tokens (HttpOnly, Secure, SameSite, CSRF defense), API key design (SHA-256 hashing, secret scanner prefixes), HMAC request signatures (timestamp drift, replay defense, constant-time compare), and Mutual TLS (mTLS).
- **Trigger phrases:** `"review api security"`, `"jwt vs oauth"`, `"jwt vs session"`, `"api authentication best practices"`, `"implement pkce"`, `"webhook hmac signature"`, `"secure api keys"`, `"audit auth architecture"`.

### `algorithmic-complexity-analyzer`
Language-independent asymptotic complexity auditing (Big-O). Audits worst-case time and auxiliary space complexity ($O(1)$, $O(\log n)$, $O(n)$, $O(n \log n)$, $O(n^2)$, $O(2^n)$), detects hidden quadratic traps (nested `includes`/`contains`, array `.shift()` in loops, string concatenation copies, unmemoized recursion), and provides concrete optimization strategies. Integrates with the `nodejs-executor` MCP server for empirical doubling hypothesis benchmarks ($T(2N)/T(N)$ ratio testing) with adaptive batching and sandbox safety.
- **Trigger phrases:** `"check time complexity"`, `"analyze big o"`, `"check algorithmic logic"`, `"optimize loop performance"`, `"audit algorithmic complexity"`, `"check for o(n) vs o(1)"`, `"find hidden quadratic loops"`.
- **Supported languages:** Universal (Python, TypeScript/JavaScript, Java, Go, C++, Rust, C#).
- **Empirical MCP Harness:** Available via `execute_code` in `nodejs-executor` or standalone at `.github/skills/algorithmic-complexity-analyzer/scripts/benchmark-harness.mjs`.

### `detect-overengineering`
Analyzes source code to detect premature abstractions, speculative generality (YAGNI violations), layer bloat, and trampoline pass-through methods. Uses structural AST/regex extraction to score over-engineering risk (0–100) and outputs simplified refactoring diffs. Embedded directly **in the loop** across development, code review, architecture gates, and bug remediation.
- **Trigger phrases:** `"check for over-engineering"`, `"detect over-engineering"`, `"find over-engineered code"`, `"simplify this code"`, `"audit for over-engineering"`, `"check yagni violations"`.

### `caching-queues-reviewer`
Comprehensive architectural guidance and code review auditing for caching, distributed memory systems, and message queues (Redis, Apache Kafka, RabbitMQ, Lua scripting, multi-tier HybridCache, and ecosystem drivers across JavaScript/TypeScript, Python, and C#/.NET). Audits code changes for cache stampede defense, eviction policies, atomic Lua operations, poison pill handling, Kafka partition skew, and offset commit hygiene.
- **Trigger phrases:** `"review caching code"`, `"kafka vs redis"`, `"redis lua script"`, `"audit queue architecture"`, `"cache stampede defense"`, `"c# hybridcache"`, `"python redis celery"`, `"bullmq review"`.

### `sql-executor`
Practitioner guidance for querying, tuning, validating, and troubleshooting enterprise databases (SQL Server, Oracle, PostgreSQL, SQLite, MongoDB, MS Access, MySQL) via the `sql-connector` MCP server. Covers multi-engine joins, specialized PostgreSQL indexes (GIN for JSONB/trigrams, GiST, BRIN), Common Table Expressions (chained & recursive CTEs, materialization fences), temporary tables (`#TempTable` vs. `@TableVariable` vs. Oracle GTTs), OLAP multidimensional aggregations (`CUBE`, `ROLLUP`, `GROUPING SETS`), statistical distributions & percentiles (`PERCENTILE_CONT`), sessionization, cohort retention matrices, stored procedures, Inline TVFs vs. mTVFs, Oracle cursors (`SYS_REFCURSOR`, `BULK COLLECT` + `FORALL`), window analytic functions (`ROWS` vs. `RANGE`), execution plans, and data validation.
- **Trigger phrases:** `"write a sql join"`, `"optimize sql query"`, `"tune database index"`, `"sql cube"`, `"grouping sets"`, `"sql cohort analysis"`, `"postgres gin index"`, `"oracle cursor"`, `"sql stored procedure"`, `"sql cte"`, `"temp table"`, `"window function"`, `"validate extracted data"`, `"troubleshoot slow query"`, `"explain query plan"`, `"run database queries"`.

### `design-pattern-detector`
Identifies design patterns (Singleton, Factory, Observer, Strategy, Builder, Decorator, Repository, Command, Template Method, Facade, Dependency Injection) and anti-patterns (God Object / God File, Long Method, Feature Envy) using structural AST extraction combined with contextual semantic reasoning.
- **Trigger phrases:** `"detect design patterns"`, `"find patterns in this file"`, `"analyze code for patterns"`, `"check for anti-patterns"`, `"detect dependency injection"`, `"is this a singleton"`, `"detect god object"`.

### `architectural-planning`
Interactively guides architecture design for new or existing applications. Recommends compatible technologies across frontend, backend, persistence, caching, messaging, and deployment, outputting Mermaid diagrams, component breakdowns, data models, and API topologies. Includes comprehensive references to foundational architecture literature (Kleppmann, Nygard, Newman, Richards/Ford, Evans, Fowler, Beck) in `references/architecture-books-and-best-practices.md`.
- **Trigger phrases:** `"plan my architecture"`, `"design system architecture"`, `"create an architecture document"`, `"help me choose a tech stack"`, `"system design"`.

### `rag-pipeline`
End-to-end architectural and engineering guidance for designing, building, and evaluating production Retrieval-Augmented Generation (RAG) pipelines. Covers document ingestion & layout/table preservation, structure-aware & contextual/parent-child chunking, Matryoshka (MRL) embeddings, vector databases (`pgvector` `halfvec` HNSW with iterative scan, Qdrant, Milvus, SQLite FTS5), hybrid search (`BM25` + dense vectors + Reciprocal Rank Fusion `RRF`), cross-encoder reranking, query transformations (rewrite, multi-query, step-back, HyDE), grounded generation with citations & abstention, Agentic/Corrective RAG, RAG Triad & offline IR metrics (`Recall@K`, `Precision@K`, `MRR`, `NDCG@K`), and document-level ACL security. Includes zero-dependency CLI utility `rag-pipeline-eval.py`.
- **Trigger phrases:** `"rag-pipeline"`, `"rag-pipeline-creator"`, `"build rag pipeline"`, `"create rag pipeline"`, `"design rag architecture"`, `"chunking strategy"`, `"hybrid search rag"`, `"vector database indexing"`, `"reranking pipeline"`, `"agentic rag"`, `"evaluate rag pipeline"`, `"rag grounding"`.

### `scan-halucinated-tests`
Cross-validates test files against real source code AST to catch phantom functions, non-existent properties, wrong import paths, fabricated constants, bad mocks, and incorrect exception types.
- **Trigger phrases:** `"scan for hallucinated tests"`, `"validate tests against source"`, `"verify test accuracy"`, `"find fake test assertions"`, `"audit tests for hallucinations"`.

### `trace-code-context`
Generates authoritative ground-truth Markdown context files covering defined symbols, imports, callers, callees, and Mermaid call graphs via AST extraction.
- **Trigger phrases:** `"trace code context"`, `"analyze this file"`, `"show callers and callees"`, `"generate a code context file"`, `"map dependencies for X"`.

### `playwright-tester`
Architectural and engineering guidance for End-to-End (E2E) browser test automation using Microsoft Playwright across TypeScript/Node.js, Python, Java, and C# / .NET. Covers `playwright.config.ts` setup, Page Object Models (POM) with accessible locators, fixture injection, auto-waiting, web-first assertions, network mocking (`page.route`), authenticated state reuse (`storageState`), Trace Viewer diagnostics, and parallel CI sharding.
- **Trigger phrases:** `"write playwright tests"`, `"playwright e2e"`, `"e2e browser test"`, `"test with playwright"`, `"playwright page object"`, `"playwright locators"`, `"playwright java"`, `"playwright c#"`, `"playwright trace"`.
- **Supported environments:** TypeScript / Node.js (`@playwright/test`), Python (`pytest-playwright`), Java (`com.microsoft.playwright`), C# / .NET (`Microsoft.Playwright`).

### `bdd-gherkin-tester`
Architectural and engineering guidance for Behavior-Driven Development (BDD) using Gherkin and BDD test runners across TypeScript/Node.js, Python, Java, and C# / .NET (paired with `playwright-tester` for core Playwright mechanics). Covers declarative scenario design, `bddgen` tag filtering, step definitions with parameter expressions, and BDD fixture injection.
- **Trigger phrases:** `"write gherkin feature"`, `"gherkin playwright"`, `"playwright bdd"`, `"cucumber"`, `"pytest-bdd"`, `"reqnroll"`, `"bddgen"`, `"bdd e2e testing"`.
- **Supported environments:** TypeScript / Node.js (`playwright-bdd`), Python (`pytest-bdd`), Java (`playwright` + `cucumber-jvm`), C# / .NET (`Microsoft.Playwright` + `Reqnroll`/`SpecFlow`).

### `test-data-creator`
Generates realistic, schema-conformant synthetic mock datasets, API payloads, and high-volume performance test loads across SQL (SQL Server, PostgreSQL, MySQL, Oracle, SQLite via `sql-connector`), JSON/NDJSON, and CSV formats.
- **Key Capabilities:** Schema inspection via `sql-connector` (`describe_table`), high-throughput chunked batch inserts (500–2,000 rows/statement) with transaction blocks ($20\text{x}\text{--}50\text{x}$ speedups), constant $O(1)$ memory streaming for millions of records, Pareto 80/20 & Zipfian distribution skew (simulating hot tenant partitions and lock contention), and boundary edge-case injection (escaped quotes `O'Connor`, emojis, leap years, max int64). Includes fast streaming CLI script `generate-test-data.py`.
- **Trigger phrases:** `"generate test data"`, `"create test data"`, `"seed database"`, `"mock data generator"`, `"performance test data"`, `"generate sql inserts"`, `"generate mock json"`, `"test-data-creator"`.

---

## 🚀 3. SDLC Orchestration & Multi-Agent Workflows

### `agent-orchestrator`
Automates and coordinates end-to-end multi-agent software engineering workflows across seven quality stages:
`plan` $\to$ `develop` $\to$ `codereview` $\to$ `complexitychecks` $\to$ `architecturechecks` $\to$ `halucinationchecks` $\to$ `securitychecks`.

**Key Capabilities:**
- **Project Memory Bus:** Uses `project-memory` (`save-memory` and `load-memory`) to track sub-agent outputs across stages without context window bloat:
  - `ledger`: Permanent architectural constraints, API contracts, and security policies.
  - `sidecar`: Active task state, sub-agent WIP handoffs, and pending defect fixes.
  - `journal`: Stage execution recaps containing BOTH distilled work summary AND mandatory learnings / traps avoided.
- **In-The-Loop Over-Engineering Detection:** Embeds `detect-overengineering` across development self-checks, code review diff audits, architecture gates (triggering an automated simplification loop when score $\ge 40$), and defect remediation (anti-fix-bloat guardrail).
- **Remediation & Circuit Breaker:** Integrates `troubleshoot-and-fix` with an isolated reproduction testbed and strict 3-iteration circuit breaker.
- **CLI Context Manager:** `.\.venv\Scripts\python.exe .github/skills/agent-orchestrator/scripts/orchestrator-context-manager.py` manages run state, stage handoff payloads, `check-overengineering` audits, `report` generation (with pending-learning counts), and `skill-doctor` diagnostics.
- **Periodic Skill Evolution:** Integrates `skill-doctor` at finalization when `>= 3` unprocessed learnings accumulate or remediation ran during delivery.
- **Trigger phrases:** `"orchestrate a feature"`, `"run full development pipeline"`, `"plan-develop-review"`, `"agent orchestrator"`, `"run full lifecycle checks"`.

### `llm-as-judge`
Built-in evaluation capability for evaluating and comparing LLM responses directly within reasoning workflows without external API dependencies.
- **The 4 Evaluator Archetypes & Styles:**
  1. **The Pessimist (Failure Mode & Blast Radius):** Evaluates catastrophic edge cases, cascading timeouts, missing circuit breakers, and unhandled exceptions.
  2. **The Contrarian (Velocity & Fast Feedback Cycles):** Challenges speculative abstraction, premature generalization, and bureaucratic delays, favoring lightweight observable rollouts.
  3. **The Pragmatist (Production Reality & ROI):** Balances ideal architecture against migration cost, team cognitive load, operational complexity, and technical debt.
  4. **The Specialist (Domain Purity & Standards):** Enforces strict domain compliance, cryptographic hygiene, type safety, and framework conventions.
- **Consensus & Multi-Judge:** 3-model consensus (Lead Judge, Skeptic, Domain Specialist), pairwise comparisons, rubric evaluations, and hallucination auditing.
- **Trigger phrases:** `"judge this response"`, `"compare these responses"`, `"evaluate response quality"`, `"score this output"`, `"rate this response"`.

---

## 🛠️ 4. Diagnostics, Debugging & Modernization

### `remote-pod-log-analyzer`
Operational framework for searching, streaming, and statistically analyzing remote Linux and Kubernetes pod logs over SSH and kubectl without downloading giant log files locally.
- **Core Topics:** Non-interactive SSH execution (`-o BatchMode=yes`, `-o ConnectTimeout=5`), Bastion / Jump host hopping (`-J`), remote heredoc execution, Kubernetes pod log extraction (`kubectl logs -l app=foo`, multi-container `-c`, `--previous` for crashed pods, time-windowed `--since`), container crash exit code diagnosis (`137 OOMKilled`, `143 Terminated`, `127 Command Not Found`), node-level log inspection (`/var/log/pods/`, `crictl logs`), high-performance searching across raw and rotated gzipped archives (`grep`, `zgrep`, `ripgrep -z`), stream statistical parsing with `awk` (HTTP status distributions, P50/P95/P99 latency calculations, multiline stack trace grouping), structured JSON log analysis with `jq` (`select(.level == "error")`, distributed trace ID isolation), systemd journal filtering (`journalctl -u unit -p err`), kernel ring buffer inspection (`dmesg -T` for OOM-killer events), and production incident triage runbooks.
- **Trigger phrases:** `"analyze remote logs"`, `"remote linux log analysis"`, `"remote pod log analysis"`, `"remote-linux-pod-log-analysis"`, `"kubectl logs triage"`, `"ssh log grep"`, `"debug pod crash"`, `"journalctl error analysis"`, `"parse nginx access logs"`, `"zgrep logs"`.

### `troubleshoot-and-fix`
Universal diagnostic and repair framework for runtime crashes, exceptions, and logic errors. Enforces a strict 3-iteration circuit breaker to prevent infinite token-burning trial-and-error loops, escalating a structured out-of-options diagnostic summary when hypotheses fail. Extracts problematic logic and test fixtures into an isolated sandbox harness (`scripts/isolate-runner.js`, `scripts/isolate-runner.py`) to systematically reproduce and verify fixes before porting them back to source code, enforcing in-the-loop over-engineering checks to prevent fix bloat.
- **Trigger phrases:** `"troubleshoot and fix"`, `"debug this error"`, `"fix this bug"`, `"solve runtime exception"`, `"diagnose issue"`, `"reproduce and fix bug"`.

### `researcher-poc-tester`
Empirical Proof-of-Concept (PoC) benchmarking framework for systematically validating technical hypotheses and runtime performance trade-offs. Synthesizes isolated, reproducible side-by-side testbeds (`scratch/pocs/`) with synthetic workloads, isolates runtime confounders (discarding JIT/V8 warmup passes, using monotonic nano-timers, tracking GC allocation), and executes automated multi-iteration statistical sampling with `poc-stats-runner.py` to calculate Median (P50), P95, P99 tail latency, StdDev, throughput (ops/sec), and relative speedup factors. Includes deep pre-packaged scenarios:
- **Java Concurrency**: Virtual Threads (`Thread.ofVirtual()`) vs Platform OS Threads in blocking I/O vs CPU work; carrier thread pinning traps (`synchronized`, JNI) and connection pool saturation.
- **Database Query Throughput**: Batch size optimization (500–2,000 chunks yielding 30x+ speedups) vs single-row round trips; keyset cursor streaming vs $O(N)$ offset pagination.
- **Data Engine Shootouts**: NumPy C-vectorized SIMD arrays vs Polars multithreaded Lazy Arrow vs Pandas GIL contention for analytical filtering, joins, and aggregations.
- **Low-Latency & Mechanical Sympathy**: Cache line false sharing (64-byte L1 invalidation), zero-allocation steady states, and off-heap memory buffers.
- **Automated Runner**: Powered by `poc-stats-runner.py` via `.\.venv\Scripts\python.exe`.
- **Trigger phrases:** `"test this concept"`, `"create a poc"`, `"benchmark these approaches"`, `"virtual threads benchmark"`, `"numpy vs polars performance"`, `"high throughput db query"`, `"low latency stats"`, `"researcher-poc-tester"`.

### `legacy-code-modernization`
Systematic, language-independent framework for safely refactoring and modernizing legacy codebases across 4 phases:
1. **Extract & Isolate:** Break tight couplings using Michael Feathers' seam techniques (parameterize constructor, extract interface, subclass and override).
2. **Characterization Tests:** Freeze existing runtime behavior and quirks using the Golden Master pattern / Approval pinning tests before changing any logic.
3. **TDD Target Architecture:** Design clean domain contracts with Dependency Inversion, driving modern implementation via outside-in Red-Green-Refactor.
4. **Develop & Migrate:** Migrate production traffic incrementally using Branch by Abstraction, the Strangler Fig pattern, and shadow parallel runs with zero downtime.
- **Trigger phrases:** `"modernize legacy code"`, `"refactor legacy service"`, `"extract legacy code"`, `"characterization tests"`, `"golden master testing"`, `"tdd refactor"`, `"strangler fig migration"`.
- **Supported languages:** Universal (Python, TypeScript/JavaScript, Java, C#, Go, C++, PHP).

---

## ⚙️ 5. Developer Tooling, Security & Utilities

### `skill-creator`
Scaffolds and writes new skills following repository conventions. Supports **Modular Knowledge-Pack Skills** (`--modular`), Task/Action skills with scripts, and Lightweight Reference skills. Includes dual cross-platform scaffold scripts in Node.js (`scripts/scaffold-skill.js`) and Python (`scripts/scaffold-skill.py`).
- **Trigger phrases:** `"create a new skill"`, `"add a skill"`, `"write a skill"`, `"scaffold a skill"`, `"build a skill"`.

### `skill-doctor`
Closed-loop skill evolution and optimization utility that periodically harvests unprocessed `journal` and `ledger` learnings from `project-memory`, triages them against existing skills (`UPDATE_EXISTING_SKILL`, `CREATE_NEW_SKILL`, `SKIP_TRANSIENT`), updates modular submodules without router bloat or scaffolds new skills via `skill-creator`, audits and optimizes existing skills (diagnosing vague triggers, instruction bloat, orphan assets, edge-case blind spots, and missing verification steps), and marks processed learnings as `promoted` or `skipped`.
- **CLI Utility:** `.\.venv\Scripts\python.exe .github/skills/skill-doctor/scripts/skill-doctor.py` (`diagnose`, `mark`, `audit-skills [--skill <name>] [--strict]`).
- **Trigger phrases:** `"skill doctor"`, `"run skill doctor"`, `"update skills from memory"`, `"evolve skills from learnings"`, `"promote learnings to skills"`, `"audit skill health"`, `"optimize skill"`.

### `github-security-scanner-hook`
Scans staged files for secrets and code vulnerabilities prior to git commits using `detect-secrets` and 24 Semgrep OWASP rules (command injection, path traversal, hardcoded tokens, hardcoded personal paths/PII, XSS, dangerous subprocesses). Enforces executing concrete scanner rules (`scan-staged.py`) against diffs rather than manual visual sign-off.
- **Trigger phrases:** `"scan for security vulnerabilities"`, `"check for secrets in code"`, `"set up a pre-commit security hook"`, `"scan staged files for secrets"`.

### `python-linter`
Runs Ruff (linting and formatting) and Mypy (type checking) with automated fixes on Python projects, strictly resolving `.\.venv\Scripts\python.exe` (or `uv`) to avoid Windows Store `python` stub failures.
- **Trigger phrases:** `"lint python"`, `"run the linter"`, `"fix linting errors"`, `"run ruff"`, `"format python code"`, `"run mypy"`.

### `sync-github-forks`
Automates cloning and pulling all your GitHub forked repositories using `gh` CLI credentials (PowerShell for Windows, Bash for Linux/macOS).
- **Trigger phrases:** `"sync github forks"`, `"sync forks"`, `"pull all my forks"`.

### `scan-repo-readme`
Dual-phase keyword and semantic extraction across repository README files with `--root-only` filtering.
- **Trigger phrases:** `"scan the readme"`, `"read the repo readme"`, `"check the project documentation"`, `"search the readme for X"`.

---

## 💾 6. Context & Long-Term Memory (MCP Skills)

### `save-memory`
Persists high-signal project memory into the `project-memory` MCP server. Partitions state into `ledger` (permanent architecture decisions), `sidecar` (transient active WIP context), and `journal` (session summaries and mandatory learnings), enforcing `node:sqlite` (`DatabaseSync`), parameterized queries, workspace-bound DB paths, and zero-vector boundary stripping.
- **Trigger phrases:** `"save memory"`, `"record memory"`, `"save to ledger"`, `"save to sidecar"`, `"record mistake"`, `"save learning"`.

### `load-memory`
Retrieves concise memories using hybrid search ($0.40 \times \text{Semantic Cosine} + 0.60 \times \text{Lexical Overlap}$) across 256-dimensional subword embeddings without context-polluting raw logs, and supports `get_unprocessed_learnings`, `mark_learning_promoted`, and `skillStatus` filtering for `skill-doctor`.
- **Trigger phrases:** `"load memory"`, `"check project memory"`, `"retrieve ledger"`, `"check past mistakes"`, `"what did we learn"`.

### `nodejs-executor`
Evaluates JS/TS snippets and executes scripts via the `nodejs-executor` MCP server with multi-layered sandbox security and C++ permission model isolation.
- **Trigger phrases:** `"run nodejs code"`, `"execute javascript"`, `"execute typescript"`, `"run js snippet"`, `"evaluate expression"`.

### `sql-connector`
Executes safe queries and discovers schemas across SQL Server, Oracle, PostgreSQL, SQLite, MongoDB, MS Access, and MySQL via the `sql-connector` MCP server. Zero-tolerance SQL firewall blocks `DROP TABLE`, `DELETE *`, and destructive mutations.
- **Trigger phrases:** `"query database"`, `"connect to sql server"`, `"query postgres"`, `"query oracle"`, `"inspect database schema"`, `"connect to sqlite"`, `"query mongodb"`, `"connect to ms access"`, `"audit sql query safety"`.

---

## 🔌 Model Context Protocol (MCP) Servers

Reusable MCP servers located in `mcp/` providing protocol-compliant tool integrations:

### `nodejs-executor` (`mcp/nodejs-executor/`)
- **Tools:** `execute_code`, `evaluate_expression`, `execute_file`, `run_package_script`, `get_runtime_info`
- **Features:** Native type-stripping TypeScript execution on Node.js 22+, AST sanitization, and secret scrubbing.

### `project-memory` (`mcp/project-memory/`)
- **Tools:** `save_memory`, `load_memory`, `search_memory`, `get_unprocessed_learnings`, `mark_learning_promoted`, `delete_memory`, `clear_sidecar`
- **Features:** SQLite backend (`node:sqlite`), zero external C++ dependencies, anti-bloat filters, `skill_status` learning-promotion tracking for `skill-doctor`, and hybrid semantic/lexical search ($40\% \text{ semantic} + 60\% \text{ lexical}$).
- **Database Location:** `.project-memory/memory.db`.

### `sql-connector` (`mcp/sql-connector/`)
- **Tools:** `execute_query`, `list_tables`, `describe_table`, `explain_query`, `test_connection`, `audit_query_safety`
- **Features:** Multi-database driver support (SQL Server, Oracle, PostgreSQL, SQLite via built-in `node:sqlite`, MongoDB, MS Access, MySQL), zero-tolerance destructive DDL/DML firewall (`DROP TABLE`, `DELETE *`, tautology blocking), auto row capping, query timeout guardrails, and automated repository-wide YAML frontmatter validator (`npm run validate:skills`).

---

## 🤖 Autonomous Agents (`.github/agents/`)

### `software-factory-agent` (`.github/agents/software-factory-agent.md`)
End-to-end autonomous Software Factory Conductor binding all **repository skills** (`.github/skills/`) and all **MCP servers** (`project-memory`, `sql-connector`, `nodejs-executor`) into a closed-loop delivery pipeline:
- **Closed-Loop Pipeline:** `Bootstrap` $\to$ `Plan & Empirical PoC` $\to$ `Develop & Testbed Seed` $\to$ `Code Review & Lint` $\to$ `Complexity & Query Plans` $\to$ `Architecture Simplification` $\to$ `Hallucination & Verification Gate` $\to$ `Security & SQL Firewall` $\to$ `Self-Healing Remediation & Finalize` $\to$ `Periodic Skill Doctor`.
- **In-The-Loop Quality & Anti-Bloat:** Enforces `check-overengineering` (`score < 40`) across implementation, PR review, architecture gates (triggering an automated simplification loop when `>= 40`), and bug patches.
- **Persistent State & Diagnostics:** Coordinates `project-memory` (`ledger`, `sidecar`, `journal` + final `clear_sidecar`), `sql-connector` (`:memory:` fixtures, `explain_query`, `audit_query_safety`), `nodejs-executor` (`benchmark-harness.mjs`), and `troubleshoot-and-fix` + `remote-pod-log-analyzer` with a strict 3-iteration circuit breaker.
- **Periodic Skill Evolution (Phase 9):** Automatically triggers `skill-doctor` after delivery when unprocessed learnings reach `>= 3` or Phase 8 remediation ran, promoting lessons into skills and marking them via `mark_learning_promoted`.
- **Trigger phrases:** `"run software factory"`, `"software-factory-agent"`, `"build feature end to end"`, `"autonomous sdlc loop"`, `"end-to-end software factory"`.

---

## 🚀 Usage & Setup

### Python Environment Standard (STRICT)

> [!IMPORTANT]
> **Always use the local virtual environment for running Python scripts in this workspace:**
> - **Windows (PowerShell / CMD):** `.\.venv\Scripts\python.exe <script> <args>`
> - **Linux / macOS (Bash / Zsh):** `.venv/bin/python <script> <args>`
>
> Bare `python` triggers WindowsApp store redirection stubs in sandboxes, and `py` launcher fallbacks can fail. Using `.\.venv\Scripts\python.exe` ensures 100% reliable execution.

### Skills & Agents Automated Validation

Validate all `SKILL.md` frontmatter headers, `.github/agents/*.md` definitions, and YAML rules across the repository:
```bash
npm run validate:skills --prefix mcp/sql-connector
```

### Claude Code & Antigravity
Skills are discovered automatically from `.github/skills/`. Simply type any trigger phrase in your chat session.

To register the MCP servers, add them to your MCP configuration (`.mcp.json` or `claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "nodejs-executor": {
      "command": "node",
      "args": ["<path-to-repo>/mcp/nodejs-executor/dist/index.js"]
    },
    "project-memory": {
      "command": "node",
      "args": ["--experimental-sqlite", "<path-to-repo>/mcp/project-memory/dist/index.js"]
    },
    "sql-connector": {
      "command": "node",
      "args": ["--experimental-sqlite", "<path-to-repo>/mcp/sql-connector/dist/index.js"]
    }
  }
}
```

### GitHub Copilot
Skills in `.github/skills/` are recognized as custom workspace instructions in Copilot Chat. Use the trigger phrases or invoke skills directly with `@workspace /<skill-name>`.

---

## 📂 Repository Structure

```text
developer-productivity-skills/
├── AGENTS.md                         # Project agent guidelines & .venv execution standard
├── mcp/
│   ├── nodejs-executor/              # Sandboxed JS/TS execution MCP server
│   ├── project-memory/               # SQLite hybrid-search memory MCP server
│   └── sql-connector/                # Multi-engine DB connector with SQL firewall & frontmatter validator
├── .github/
│   ├── agents/
│   │   └── software-factory-agent.md # Autonomous end-to-end closed-loop agent (all skills + MCPs)
│   └── skills/
│       ├── agent-orchestrator/       # 7-stage multi-agent SDLC workflow with memory bus & in-the-loop OE checks
│       ├── api-security/             # Universal API authentication & AppSec audit pack
│       ├── algorithmic-complexity-analyzer/ # Language-agnostic Big-O analysis
│       ├── architectural-planning/   # Interactive system architecture designer & book references
│       ├── caching-queues-reviewer/  # Redis, Kafka, Lua scripts & queue auditor
│       ├── code-reviewer/            # 7-dimension code reviewer ([P0] to [P3])
│       ├── csharp-developer/         # Modern C# 12/13, .NET 8/9, Minimal APIs, MVVM pack
│       ├── design-pattern-detector/  # AST design pattern & anti-pattern detector
│       ├── detect-overengineering/   # YAGNI & complexity risk auditor with extract-signals.py
│       ├── github-security-scanner-hook/ # Pre-commit secret & Semgrep scanner
│       ├── java-developer/           # Modern Java 17/21/25 & Spring Boot 3+ pack
│       ├── legacy-code-modernization/ # Safe 4-phase refactoring & migration framework
│       ├── llm-as-judge/             # 4 Evaluator Archetypes & multi-agent response evaluation
│       ├── load-memory/              # Hybrid memory retrieval skill
│       ├── nodejs-executor/          # MCP wrapper skill for node execution
│       ├── bdd-gherkin-tester/       # Gherkin BDD & BDD runner integration
│       ├── playwright-tester/        # Playwright E2E browser test automation pack
│       ├── powershell-writer/        # Modern PowerShell 7+ & 5.1 automation pack
│       ├── python-api-writer/        # FastAPI & Django API architecture pack
│       ├── python-developer/         # Python 3.10-3.13, Pydantic v2, asyncio pack
│       ├── python-linter/            # Automated Ruff & Mypy quality runner
│       ├── rag-pipeline/             # End-to-end RAG architecture, hybrid search & IR evaluation pack
│       ├── react-developer/          # React 18/19, RSC, Zustand, Query pack
│       ├── remote-pod-log-analyzer/  # Remote Linux & Kubernetes pod log analysis pack
│       ├── researcher-poc-tester/    # Empirical PoC benchmarks, safe research & stats runner
│       ├── save-memory/              # Structured memory persistence skill
│       ├── scan-halucinated-tests/   # AST-based test hallucination scanner
│       ├── scan-repo-readme/         # Semantic repository README searcher
│       ├── skill-creator/            # Modular & task skill scaffolding generator
│       ├── skill-doctor/             # Periodic learning-to-skill evolution & health auditor
│       ├── sql-connector/            # Multi-database query & safety firewall skill
│       ├── sql-executor/             # Multi-engine SQL tuning, joins & validation pack
│       ├── sync-github-forks/        # Automated fork synchronization tool
│       ├── test-data-creator/        # Synthetic SQL/JSON test data & performance load generator
│       ├── trace-code-context/       # AST dependency & Mermaid graph generator
│       ├── troubleshoot-and-fix/     # Isolated reproduction testbed framework with circuit breaker
│       └── typescript-developer/     # Modern Node.js 20+, TypeScript 5+, DI & testing pack
└── README.md
```
