# Developer Productivity Skills

A curated suite of enterprise-grade AI skills and Model Context Protocol (MCP) servers for **Claude Code**, **Antigravity**, and **GitHub Copilot**. 

These skills provide ready-made workflows for modern software engineering — spanning architectural planning, language-specific engineering knowledge packs, Big-O complexity analysis, multi-agent SDLC orchestration, security scanning, automated code review, and isolated debugging.

---

## 📑 Skills Catalog

| Skill | Category | Core Purpose | Primary Trigger Phrase |
|---|---|---|---|
| [`agent-orchestrator`](#agent-orchestrator) | **Orchestration** | End-to-end 7-stage multi-agent SDLC coordination | `"orchestrate a feature"` |
| [`llm-as-judge`](#llm-as-judge) | **Orchestration** | Rubric evaluations, pairwise ranking & consensus | `"judge this response"` |
| [`typescript-developer`](#typescript-developer) | **Language Specialist** | Node.js, TS 5+, Zod, Drizzle/Prisma, event loop hygiene | `"write typescript code"` |
| [`python-developer`](#python-developer) | **Language Specialist** | Python 3.10–3.13, Pydantic v2, asyncio, memory/GC | `"write python code"` |
| [`react-developer`](#react-developer) | **Language Specialist** | React 18/19, Next.js RSC, Zustand, TanStack Query | `"write react code"` |
| [`java-developer`](#java-developer) | **Language Specialist** | Modern Java 17/21/25 LTS, Spring Boot 3+, Virtual Threads | `"review java code"` |
| [`code-reviewer`](#code-reviewer) | **Architecture & Quality** | 7-dimension senior review ([P0] Blocker to [P3] Nit) | `"review code"` |
| [`algorithmic-complexity-analyzer`](#algorithmic-complexity-analyzer) | **Architecture & Quality** | Big-O time/space audits ($O(1) \dots O(2^n)$), hidden loop traps | `"check time complexity"` |
| [`detect-overengineering`](#detect-overengineering) | **Architecture & Quality** | YAGNI audits, layer bloat, trampoline pass-throughs | `"check for over-engineering"` |
| [`design-pattern-detector`](#design-pattern-detector) | **Architecture & Quality** | Structural AST extraction of design patterns & anti-patterns | `"detect design patterns"` |
| [`architectural-planning`](#architectural-planning) | **Architecture & Quality** | Interactive system design, Mermaid specs & tech choices | `"plan my architecture"` |
| [`scan-halucinated-tests`](#scan-halucinated-tests) | **Architecture & Quality** | Cross-validates test symbols against AST ground truth | `"scan for hallucinated tests"` |
| [`trace-code-context`](#trace-code-context) | **Architecture & Quality** | AST symbol extraction, callers/callees & Mermaid graph | `"trace code context"` |
| [`troubleshoot-and-fix`](#troubleshoot-and-fix) | **Diagnostics** | Isolated reproduction testbeds and fix verification | `"troubleshoot and fix"` |
| [`legacy-code-modernization`](#legacy-code-modernization) | **Modernization** | 4-phase safe modernization (Extract $\to$ Pin $\to$ TDD $\to$ Strangler) | `"modernize legacy code"` |
| [`skill-creator`](#skill-creator) | **Tooling & Automation** | Scaffolds modular knowledge-packs and task skills | `"create a new skill"` |
| [`github-security-scanner-hook`](#github-security-scanner-hook) | **Tooling & Automation** | Pre-commit secret scanning & Semgrep OWASP rules | `"scan for security vulnerabilities"` |
| [`python-linter`](#python-linter) | **Tooling & Automation** | Automated Ruff linting, formatting & Mypy typing | `"lint python"` |
| [`sync-github-forks`](#sync-github-forks) | **Tooling & Automation** | Automated cross-platform syncing of all GitHub forks | `"sync github forks"` |
| [`scan-repo-readme`](#scan-repo-readme) | **Tooling & Automation** | Dual-phase keyword and semantic README search | `"scan the readme"` |
| [`save-memory`](#save-memory) | **Memory & Context** | Persists ledger, sidecar, and journal memories to SQLite | `"save memory"` |
| [`load-memory`](#load-memory) | **Memory & Context** | Hybrid semantic (40%) + lexical (60%) memory retrieval | `"load memory"` |
| [`nodejs-executor`](#nodejs-executor) | **Tooling & Automation** | Sandboxed JavaScript/TypeScript execution via MCP | `"run nodejs code"` |

---

## 🧠 1. Language & Framework Engineering Skills

Modular knowledge packs designed with lean routers (< 45 lines) and deep single-responsibility topic modules loaded selectively to keep context windows lean.

### `typescript-developer`
Architectural and engineering guidance for modern TypeScript and JavaScript (Node.js 20+, ES2023+, TS 5+).
- **Core Topics:** Hexagonal/Modular/Layered architectures, discriminated unions, branded types, Result pattern, runtime validation (Zod & Valibot), ORMs (Drizzle & Prisma), event loop health, worker_threads, stream backpressure (`pipeline`), closure scope hygiene, and `p-limit` concurrency throttling.
- **Trigger phrases:** `"write typescript code"`, `"develop typescript service"`, `"typescript architecture best practices"`, `"design node backend"`, `"vitest testing"`, `"modern nodejs patterns"`, `"refactor javascript"`.
- **Supported runtimes:** Node.js 20+, TypeScript 5.x+.

### `python-developer`
Architectural and engineering guidance for modern Python development (3.10–3.13).
- **Core Topics:** Hexagonal & service-repository architectures, `@dataclass(slots=True, frozen=True)`, `typing.Protocol` structural subtyping, Pydantic v2 enterprise validation (`ConfigDict`, `@field_validator`, `@model_validator`, `TypeAdapter`, `pydantic-settings`), memory cycle prevention (`weakref`), late-binding closure fixes, and non-blocking `asyncio` (`asyncio.TaskGroup`, `asyncio.to_thread`).
- **Trigger phrases:** `"write python code"`, `"develop python service"`, `"python architecture best practices"`, `"design python backend"`, `"pytest guidelines"`, `"modern python patterns"`, `"refactor python"`.
- **Supported versions:** Python 3.10, 3.11, 3.12, 3.13.

### `react-developer`
Architectural and engineering guidance for modern React (React 18 & 19, Next.js App Router, Vite, React Server Components).
- **Core Topics:** Presentational vs container architecture, compound component pattern, server state vs client state, global stores with Zustand (slice pattern, `useShallow`, non-React mutations), TanStack Query v5 cache lifecycles & optimistic updates, Redux Toolkit entity adapters, stale closure prevention, `AbortController` unmount teardown, `useSyncExternalStore`, and DOM virtualization.
- **Trigger phrases:** `"write react code"`, `"develop react component"`, `"react architecture best practices"`, `"nextjs server components"`, `"refactor react frontend"`, `"react 19 actions"`, `"custom hook patterns"`.
- **Supported environments:** React 18, React 19, Next.js App Router, Remix / React Router v7, Vite.

### `java-developer`
Comprehensive guidelines and best practices for modern Java (LTS 17/21/25) and Spring Boot enterprise applications.
- **Core Topics:** Modern idioms (records, sealed types, pattern matching), Virtual Threads & CompletableFuture, carrier pinning avoidance, collections selection, JVM tuning & low-latency GC (ZGC/Shenandoah/G1), application security, Spring Boot 3+ production patterns (RFC 7807 problem details, RestClient, slice/testcontainer testing), and legacy modernization (refactoring JSP and Spring Webflow to RESTful microservices).
- **Trigger phrases:** `"review java code"`, `"spring boot best practices"`, `"optimize jvm"`, `"write java unit test"`, `"design java service"`, `"java concurrency guide"`, `"virtual threads vs reactor"`, `"java security audit"`, `"migrate to spring boot 3"`.
- **Supported versions:** Java 17, 21, 25 LTS; Spring Boot 3.x.

---

## 📐 2. Architecture, Quality & Review Skills

### `code-reviewer`
Senior-level code review across languages (Python, TypeScript/JavaScript, Java, Go, C#). Audits changes across 7 dimensions: correctness, architecture (SOLID/DRY/KISS), error handling, test coverage, security defense, performance & memory hygiene, and readability. Standardizes findings into `[P0 - Blocker]`, `[P1 - Major]`, `[P2 - Minor]`, and `[P3 - Nit]` with concrete suggested fix diffs.
- **Trigger phrases:** `"review code"`, `"code review"`, `"review pull request"`, `"audit code changes"`, `"code review checklist"`, `"review this diff"`.

### `algorithmic-complexity-analyzer`
Language-independent asymptotic complexity auditing (Big-O). Audits worst-case time and auxiliary space complexity ($O(1)$, $O(\log n)$, $O(n)$, $O(n \log n)$, $O(n^2)$, $O(2^n)$), detects hidden quadratic traps (nested `includes`/`contains`, array `.shift()` in loops, string concatenation copies, unmemoized recursion), and provides concrete optimization strategies.
- **Trigger phrases:** `"check time complexity"`, `"analyze big o"`, `"check algorithmic logic"`, `"optimize loop performance"`, `"audit algorithmic complexity"`, `"check for o(n) vs o(1)"`, `"find hidden quadratic loops"`.
- **Supported languages:** Universal (Python, TypeScript/JavaScript, Java, Go, C++, Rust, C#).

### `detect-overengineering`
Analyzes source code to detect premature abstractions, speculative generality (YAGNI violations), layer bloat, and trampoline pass-through methods. Uses structural extraction to score over-engineering risk and output simplified refactoring diffs.
- **Trigger phrases:** `"check for over-engineering"`, `"detect over-engineering"`, `"find over-engineered code"`, `"simplify this code"`, `"audit for over-engineering"`, `"check yagni violations"`.

### `design-pattern-detector`
Identifies design patterns (Factory, Strategy, Observer, Repository, Builder, etc.) and anti-patterns (God Object, Long Method, Feature Envy) using structural AST extraction combined with semantic reasoning.
- **Trigger phrases:** `"detect design patterns"`, `"find patterns in this file"`, `"analyze code for patterns"`, `"check for anti-patterns"`, `"is this a singleton"`, `"detect god object"`.

### `architectural-planning`
Interactively guides architecture design for new or existing applications. Recommends compatible technologies across frontend, backend, persistence, caching, messaging, and deployment, outputting Mermaid diagrams, component breakdowns, data models, and API topologies.
- **Trigger phrases:** `"plan my architecture"`, `"design system architecture"`, `"create an architecture document"`, `"help me choose a tech stack"`, `"system design"`.

### `scan-halucinated-tests`
Cross-validates test files against real source code AST to catch phantom functions, non-existent properties, wrong import paths, fabricated constants, bad mocks, and incorrect exception types.
- **Trigger phrases:** `"scan for hallucinated tests"`, `"validate tests against source"`, `"verify test accuracy"`, `"find fake test assertions"`, `"audit tests for hallucinations"`.

### `trace-code-context`
Generates authoritative ground-truth Markdown context files covering defined symbols, imports, callers, callees, and Mermaid call graphs via AST extraction.
- **Trigger phrases:** `"trace code context"`, `"analyze this file"`, `"show callers and callees"`, `"generate a code context file"`, `"map dependencies for X"`.

---

## 🚀 3. SDLC Orchestration & Multi-Agent Workflows

### `agent-orchestrator`
Automates and coordinates end-to-end multi-agent software engineering workflows across seven quality stages:
`plan` $\to$ `develop` $\to$ `codereview` $\to$ `complexitychecks` $\to$ `architecturechecks` $\to$ `halucinationchecks` $\to$ `securitychecks`.
Manages bounded context handoffs to prevent context pollution in sub-agents, integrates `troubleshoot-and-fix` for isolated reproduction testbeds during remediation, and enforces quality gates with closed-loop feedback.
- **Trigger phrases:** `"orchestrate a feature"`, `"run full development pipeline"`, `"plan-develop-review"`, `"agent orchestrator"`, `"run full lifecycle checks"`.

### `llm-as-judge`
Built-in evaluation capability for evaluating and comparing LLM responses directly within reasoning workflows without external API dependencies. Supports single-agent rubric evaluation, pairwise ranking, hallucination scoring, and multi-agent consensus.
- **Trigger phrases:** `"judge this response"`, `"compare these responses"`, `"evaluate response quality"`, `"score this output"`, `"rate this response"`.

---

## 🛠️ 4. Diagnostics, Debugging & Modernization

### `troubleshoot-and-fix`
Universal diagnostic and repair framework for runtime crashes, exceptions, and logic errors. Extracts problematic logic and test fixtures into an isolated sandbox harness (`scripts/isolate-runner.js`, `scripts/isolate-runner.py`) to systematically reproduce and verify fixes before porting them back to source code.
- **Trigger phrases:** `"troubleshoot and fix"`, `"debug this error"`, `"fix this bug"`, `"solve runtime exception"`, `"diagnose issue"`, `"reproduce and fix bug"`.

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

### `github-security-scanner-hook`
Scans staged files for secrets and code vulnerabilities prior to git commits using `detect-secrets` and 24 Semgrep OWASP rules (command injection, path traversal, hardcoded tokens, XSS, dangerous subprocesses).
- **Trigger phrases:** `"scan for security vulnerabilities"`, `"check for secrets in code"`, `"set up a pre-commit security hook"`, `"scan staged files for secrets"`.

### `python-linter`
Runs Ruff (linting and formatting) and Mypy (type checking) with automated fixes on Python projects.
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
Persists high-signal project memory into the `project-memory` MCP server. Partitions state into `ledger` (permanent architecture decisions), `sidecar` (transient active WIP context), and `journal` (session summaries and mandatory learnings).
- **Trigger phrases:** `"save memory"`, `"record memory"`, `"save to ledger"`, `"save to sidecar"`, `"record mistake"`, `"save learning"`.

### `load-memory`
Retrieves concise memories using hybrid search ($0.40 \times \text{Semantic Cosine} + 0.60 \times \text{Lexical Overlap}$) across 256-dimensional subword embeddings without context-polluting raw logs.
- **Trigger phrases:** `"load memory"`, `"check project memory"`, `"retrieve ledger"`, `"check past mistakes"`, `"what did we learn"`.

### `nodejs-executor`
Evaluates JS/TS snippets and executes scripts via the `nodejs-executor` MCP server with multi-layered sandbox security and C++ permission model isolation.
- **Trigger phrases:** `"run nodejs code"`, `"execute javascript"`, `"execute typescript"`, `"run js snippet"`, `"evaluate expression"`.

---

## 🔌 Model Context Protocol (MCP) Servers

Reusable MCP servers located in `mcp/` providing protocol-compliant tool integrations:

### `nodejs-executor` (`mcp/nodejs-executor/`)
- **Tools:** `execute_code`, `evaluate_expression`, `execute_file`, `run_package_script`, `get_runtime_info`
- **Features:** Native type-stripping TypeScript execution on Node.js 22+, AST sanitization, and secret scrubbing.

### `project-memory` (`mcp/project-memory/`)
- **Tools:** `save_memory`, `load_memory`, `search_memory`, `delete_memory`, `clear_sidecar`
- **Features:** SQLite backend (`node:sqlite`), zero external C++ dependencies, anti-bloat filters, and hybrid semantic/lexical search.

---

## 🚀 Usage & Setup

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
├── mcp/
│   ├── nodejs-executor/              # Sandboxed JS/TS execution MCP server
│   └── project-memory/               # SQLite hybrid-search memory MCP server
├── .github/
│   └── skills/
│       ├── agent-orchestrator/       # 7-stage multi-agent SDLC workflow
│       ├── algorithmic-complexity-analyzer/ # Language-agnostic Big-O analysis
│       ├── architectural-planning/   # Interactive system architecture designer
│       ├── code-reviewer/            # 7-dimension code reviewer ([P0] to [P3])
│       ├── design-pattern-detector/  # AST design pattern & anti-pattern detector
│       ├── detect-overengineering/   # YAGNI & complexity risk auditor
│       ├── github-security-scanner-hook/ # Pre-commit secret & Semgrep scanner
│       ├── java-developer/           # Modern Java 17/21/25 & Spring Boot 3+ pack
│       ├── legacy-code-modernization/ # Safe 4-phase refactoring & migration framework
│       ├── llm-as-judge/             # Multi-agent response evaluation & ranking
│       ├── load-memory/              # Hybrid memory retrieval skill
│       ├── nodejs-executor/          # MCP wrapper skill for node execution
│       ├── python-developer/         # Python 3.10-3.13, Pydantic v2, asyncio pack
│       ├── python-linter/            # Automated Ruff & Mypy quality runner
│       ├── react-developer/          # React 18/19, RSC, Zustand, Query pack
│       ├── save-memory/              # Structured memory persistence skill
│       ├── scan-halucinated-tests/   # AST-based test hallucination scanner
│       ├── scan-repo-readme/         # Semantic repository README searcher
│       ├── skill-creator/            # Modular & task skill scaffolding generator
│       ├── sync-github-forks/        # Automated fork synchronization tool
│       ├── trace-code-context/       # AST dependency & Mermaid graph generator
│       └── troubleshoot-and-fix/     # Isolated reproduction testbed framework
└── README.md
```
