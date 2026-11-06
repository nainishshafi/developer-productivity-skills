# developer-productivity-skills

A collection of reusable AI skills stored in `.github/skills/`, compatible with **Claude Code** and **GitHub Copilot**. These skills provide ready-made workflows for common development tasks — invoke them by typing a trigger phrase in your AI session.

## Skills

### `trace-code-context`
Generates a rich, ground-truth Markdown context file for any source code file — covering defined symbols, imports, callers, callees, a Mermaid call graph, and a business-readable description. Uses a Python script for AST/parser-validated symbol extraction (ground truth) and a subagent for business context. Skips regeneration if the source file has not changed since the last run. Output is written to `.code-context/` mirroring the source file structure.

**Trigger phrases:** "trace code context", "analyze this file", "show callers and callees", "generate a code context file", "map dependencies for X", "what calls this file", "what does this file call", "document this code file", "create a mermaid diagram for this code", "explain what this module does"

**Supported languages:** Python, Java, JavaScript, TypeScript, Go, C#, C++, C

---

### `scan-halucinated-tests`
Cross-validates a test file against its real source code to detect LLM hallucinations — phantom functions, non-existent properties, wrong import paths, fabricated constants, bad mock targets, and incorrect exception types. Uses `trace-code-context` to extract authoritative ground truth from the source, a parser script to extract all references from the test, then a subagent to cross-reference the two. Results are written to `.scan-test-results/` as a timestamped Markdown report with severity-graded findings.

**Trigger phrases:** "scan for hallucinated tests", "check if my tests are hallucinated", "validate tests against source", "verify test accuracy", "find fake test assertions", "audit tests for hallucinations", "test hallucination scan", "verify tests match source code"

**Supported languages:** Python (AST), Java (JUnit/Mockito), C# (xUnit/NUnit/MSTest/Moq), JavaScript/TypeScript (Jest/Vitest)

---

### `skill-creator`
Scaffolds and writes new skills following established conventions. Handles both reference/knowledge skills (rich documentation) and task/action skills (step-by-step workflows with scripts). Includes a Python script that generates the folder and boilerplate files.

**Trigger phrases:** "create a new skill", "add a skill", "write a skill", "scaffold a skill", "build a skill"

---

### `python-linter`
Runs ruff (lint + format) and optionally mypy (type checking) on Python code. Auto-fixes what it can and reports remaining issues with file and line references.

**Trigger phrases:** "lint python", "run the linter", "fix linting errors", "run ruff", "format python code", "check types", "run mypy"

**Prerequisites:** Python on PATH — skill creates `.venv` and installs `ruff`/`mypy` automatically

---

### `github-security-scanner-hook`
Scans staged files for secrets and code-level security vulnerabilities before every git commit. Language-agnostic — works with Python, JavaScript/TypeScript, Go, and more. Uses `detect-secrets` for credential/key detection and `semgrep` with 24 bundled rules for command injection, shell execution risks, destructive filesystem deletions, environment secret leakage, hardcoded personal user paths, XSS, path traversal, and other OWASP patterns. Can install a git pre-commit hook to automate scanning on every commit.

**Trigger phrases:** "scan for security vulnerabilities", "check for secrets in code", "set up a pre-commit security hook", "scan staged files for secrets", "check for hardcoded credentials", "detect leaked API keys", "scan for SQL injection", "check for XSS vulnerabilities", "check for command injection", "audit subprocess security"

**Prerequisites:** Python on PATH — skill creates `.venv` and installs `detect-secrets` and `semgrep` automatically

---

### `sync-github-forks`
Syncs all your GitHub forked repositories — clones missing ones and pulls existing ones. Uses the `gh` CLI for authentication, no token config needed. Cross-platform: PowerShell script for Windows, Bash script for Linux/macOS.

**Trigger phrases:** "sync github forks", "sync forks", "pull all my forks"

**Prerequisites:** `gh` CLI (authenticated), `git`, SSH key added to GitHub. Linux/macOS also requires `jq`.

---

### `scan-repo-readme`
Efficiently locate and extract information from repository README files. Uses a lightweight subagent to perform dual-phase search (keyword + semantic) and writes results to a timestamped file under `.scan-readme-results/`. Defaults to `--root-only` mode to avoid noisy results from nested packages and virtualenvs. When no query is provided, returns a full summary of all README files found.

**Trigger phrases:** "scan the readme", "read the repo readme", "check the project documentation", "search the readme for X", "what does the readme say about Y", "summarize the readme", "find readme", "look up X in the readme"

---

### `design-pattern-detector`
Detects design patterns and anti-patterns in source code using structural extraction (Python AST, regex for other languages) combined with a subagent for contextual reasoning. Supports single-file and repo-wide modes with staleness checking — skips regeneration if the source file has not changed since the last run. Output is written to `.pattern-analysis/` mirroring the source file structure, with a `_index.md` summary for repo-wide scans.

**Design patterns:** Singleton, Factory, Observer, Strategy, Builder, Decorator, Repository, Command, Template Method, Facade

**Anti-patterns:** God Object / God File, Long Method, Feature Envy

**Trigger phrases:** "detect design patterns", "find patterns in this file", "analyze code for patterns", "check for anti-patterns", "pattern analysis", "is this a singleton", "detect god object", "check for god file", "find factory pattern", "detect facade", "check for strategy pattern", "scan for design patterns", "what patterns does this code use", "find anti-patterns", "pattern audit"

**Supported languages:** Python (AST), Java, JavaScript, TypeScript, Go, C# (regex), C++, C (fallback)

---

### `detect-overengineering`
Analyzes source code and architectures to detect over-engineering, premature abstractions, speculative generality (YAGNI violations), layer bloat, trampoline pass-through methods, and pattern overkill. Uses deterministic structural extraction (Python AST for Python, structural regex for TS/JS, Java, C#, Go) to calculate an over-engineering risk score and output concrete, simplified refactoring diffs. Results are written to `.overengineering-analysis/` mirroring the source file structure.

**Trigger phrases:** "check for over-engineering", "detect over-engineering", "find over-engineered code", "simplify this code", "audit for over-engineering", "check yagni violations", "reduce accidental complexity", "eliminate premature abstractions", "check code bloat", "is this over-engineered", "refactor for simplicity"

**Supported languages:** Python (AST), TypeScript, JavaScript, Java, C#, Go

---

### `architectural-planning`
Interactively guides you through architectural decisions for a new or existing project. Asks structured questions about project type, backend/frontend stack, database, caching, authentication, messaging, deployment, CI/CD, and monitoring — recommending compatible technologies at each step with specific library and version suggestions. Generates a comprehensive architecture document with Mermaid diagrams, component breakdown, data model, API design, security architecture, deployment topology, and project directory layout.

**Trigger phrases:** "plan my architecture", "design system architecture", "create an architecture document", "help me choose a tech stack", "what technologies should I use", "recommend a database for my project", "architecture planning", "tech stack recommendation", "design my API layer", "create a system design"

---

### `agent-orchestrator`
Automates and coordinates end-to-end multi-agent software engineering workflows across six quality stages: `plan` -> `develop` -> `codereview` -> `architecturechecks` -> `halucinationchecks` -> `securitychecks`. Manages bounded context handoffs to prevent context pollution in sub-agents, routes tasks to specialized skills (`architectural-planning`, `python-developer`, `typescript-developer`, `react-developer`, `java-developer`, `troubleshoot-and-fix`, `code-reviewer`, `detect-overengineering`, `scan-halucinated-tests`, `github-security-scanner-hook`), and enforces quality gates with closed-loop remediation feedback.

**Trigger phrases:** "orchestrate a feature", "run full development pipeline", "plan-develop-review", "agent orchestrator", "orchestrate subagents", "run full lifecycle checks", "orchestrate sdlc"

**Supported stages:**
1. `plan` — System design and contract specifications (`architectural-planning`)
2. `develop` — Production code and unit test implementation (`python-developer`, `typescript-developer`, `react-developer`, `java-developer`)
3. `codereview` — Multi-dimension code review across logic, errors, security, and clean code (`code-reviewer`)
4. `architecturechecks` — Over-engineering, YAGNI, layer bloat, and anti-pattern detection (`detect-overengineering`, `design-pattern-detector`)
5. `halucinationchecks` — Cross-validation of test symbols against ground-truth AST (`scan-halucinated-tests`)
6. `securitychecks` — Pre-commit credential leak and OWASP security vulnerability scan (`github-security-scanner-hook`)

---

### `python-developer`
Architectural and engineering guidance for modern Python development (3.10–3.13). Guides the LLM to inspect and discover the project's baseline architecture, adapt to codebase conventions, and apply clean architecture (Hexagonal/Layered/Modular), domain modeling, dependency inversion (`typing.Protocol`), and testing patterns pragmatically without imposing dogmatic hard rules.

**Trigger phrases:** "write python code", "develop python service", "python architecture best practices", "design python backend", "pytest guidelines", "modern python patterns", "refactor python"

**Supported versions:** Python 3.10, 3.11, 3.12, 3.13

---

### `typescript-developer`
Architectural and engineering guidance for modern TypeScript and JavaScript (Node.js 20+, ES2023+, TS 5+). Guides the LLM to inspect and discover existing project architecture (Modular/NestJS, Layered/Express/Fastify, or Vertical Slice), adapt to runtime conventions, and apply clean architecture, type-driven domain modeling (discriminated unions, `as const`), resilient error handling (`Result` pattern), and testing patterns pragmatically without imposing dogmatic hard rules.

**Trigger phrases:** "write typescript code", "develop typescript service", "typescript architecture best practices", "design node backend", "vitest testing", "modern nodejs patterns", "refactor javascript"

**Supported runtimes:** Node.js 20+, TypeScript 5.x+

---

### `react-developer`
Architectural and engineering guidance for modern React development (React 18 & 19, Next.js App Router, Remix / React Router v7, Vite, React Server Components). Guides the LLM to inspect project context, adapt to frontend architecture (Feature-Sliced, Layered, or App Router), manage state cleanly (TanStack Query, Zustand, Context, URL state), apply custom hook abstraction, adhere to RSC client/server boundaries, and ensure accessible, resilient component design.

**Trigger phrases:** "write react code", "develop react component", "react architecture best practices", "nextjs server components", "refactor react frontend", "react 19 actions", "custom hook patterns"

**Supported environments:** React 18, React 19, Next.js, Remix/React Router v7, Vite

---

### `code-reviewer`
Conducts rigorous, senior-level code reviews across languages (Python, TypeScript/JavaScript, Java, Go, C#). Audits code changes across 7 dimensions: logic correctness, architecture & design principles (DRY/KISS/SOLID), error handling & boundary defense, test coverage & quality, security & input sanitization, performance & resource hygiene, and clean code readability. Classifies all findings into standardized severities (`[P0 - Blocker]`, `[P1 - Major]`, `[P2 - Minor]`, `[P3 - Nit]`) with actionable suggested fix diffs.

**Trigger phrases:** "review code", "code review", "review pull request", "audit code changes", "code review checklist", "review this diff", "inspect pull request"

---

### `algorithmic-complexity-analyzer`
Rigorous, language-independent algorithmic complexity analysis (Big-O time and space complexity). Audits source code for asymptotic bounds ($O(1)$, $O(\log n)$, $O(n)$, $O(n \log n)$, $O(n^2)$, $O(2^n)$), detects hidden quadratic/exponential anti-patterns (nested linear scans, array shifting in queues, string concatenation allocations, recursion stack depth traps), and proposes optimized algorithmic strategies (hash mapping, two-pointer, sliding window, binary search, dynamic programming).

**Trigger phrases:** "check time complexity", "analyze big o", "check algorithmic logic", "optimize loop performance", "audit algorithmic complexity", "check for o(n) vs o(1)", "find hidden quadratic loops"

**Supported languages:** Language-independent (Python, TypeScript, JavaScript, Java, Go, C++, Rust, C#)

---

### `troubleshoot-and-fix`
Universal, language-independent diagnostic and repair framework for debugging runtime crashes, exceptions, logic errors, and flakiness. Refers to language-specific developer skills (`python-developer`, `typescript-developer`, `react-developer`, `java-developer`) for runtime idioms. When direct in-project reproduction is blocked by heavy dependencies, cloud credentials, or monolithic setup, it systematically extracts the problematic logic, generates realistic mock fixtures, and executes an isolated reproduction testbed to verify the fix before porting it back.

**Trigger phrases:** "troubleshoot and fix", "debug this error", "fix this bug", "solve runtime exception", "diagnose issue", "reproduce and fix bug", "debug failing code", "isolate and debug"

**Tools included:** Standalone reproduction harness generator (`scripts/isolate-runner.js`, `scripts/isolate-runner.py`)

---

### `java-developer`
Comprehensive guidelines and best practices for modern Java (LTS 17/21/25) and Spring Boot enterprise applications. Covers modern language features (records, sealed types, pattern matching, switch expressions), concurrency (Virtual Threads, CompletableFuture, carrier pinning avoidance), collection selection and performance, functional architecture, JVM tuning & low-latency GC (ZGC/Shenandoah/G1), application security (OWASP, IDOR, SSRF, injection defense), Spring Boot 3+ production patterns (thin controllers, transactional boundaries, RFC 7807 problem details, RestClient, and slice/testcontainer testing), and legacy modernization (refactoring JSP and Spring Webflow state machines to RESTful microservices, `jakarta.*` migration, Spring Security 6, and AOT/GraalVM).

**Trigger phrases:** "review java code", "spring boot best practices", "optimize jvm", "write java unit test", "design java service", "java concurrency guide", "virtual threads vs reactor", "java security audit", "migrate to spring boot 3", "modernize legacy jsp webflow"

**Supported versions:** Java 17, 21, 25 LTS; Spring Boot 3.x

---

### `nodejs-executor`
Executes JavaScript and TypeScript code snippets, evaluates expressions, runs script files, and automates package scripts using the `nodejs-executor` MCP server with multi-layered sandbox security (Node.js C++ permission model, secret scrubbing, and pre-execution safety linter).

**Trigger phrases:** "run nodejs code", "execute javascript", "execute typescript", "run js snippet", "run node script", "evaluate expression", "execute node file", "run package script", "test node snippet"

**Prerequisites:** Node.js >= 20.0.0 (Node 22+ recommended for native TypeScript strip-types)

---

### `llm-as-judge`
Built-in evaluation capability for Copilot/Claude to evaluate and compare LLM responses directly within the agent's reasoning process without external APIs or dependencies. Supports single-agent rubric evaluation, pairwise comparison, hallucination detection, grounding verification, and multi-agent sequential consensus evaluation.

**Trigger phrases:** "judge this response", "compare these responses", "evaluate response quality", "check for hallucinations", "score this output", "rate this response", "which response is better", "evaluate with rubrics"

---

### `save-memory`
Persists high-signal, non-bloated project memory into the `project-memory` MCP server. Strictly partitions memory into three categories: `ledger` (permanent architecture decisions and constraints), `sidecar` (transient active WIP context), and `journal` (session summary paired with mandatory learnings from mistakes and errors encountered or avoided). Strips raw code, logs, and stack traces to preserve context window bandwidth.

**Trigger phrases:** "save memory", "record memory", "save to ledger", "save to sidecar", "record mistake", "save learning", "remember this decision", "log anti-pattern", "persist task context"

**Prerequisites:** `project-memory` MCP server configured

---

### `load-memory`
Retrieves concise project memories from the `project-memory` MCP server without context-polluting vectors or raw logs. Supports category filtering (`ledger`, `sidecar`, `journal`), balanced session snapshots, and hybrid search with 40% semantic cosine similarity + 60% lexical overlap to locate relevant historical context and past mistakes to avoid before starting tasks.

**Trigger phrases:** "load memory", "check project memory", "what was I working on", "retrieve ledger", "search memory", "check past mistakes", "what did we learn", "load project context", "recall decisions"

**Prerequisites:** `project-memory` MCP server configured

---

## Model Context Protocol (MCP) Servers

Reusable MCP servers located in `mcp/` providing protocol-compliant tool integrations for AI assistants.

### `nodejs-executor`
A high-performance MCP server for executing JavaScript and TypeScript code snippets, evaluating expressions with deep object inspection, executing `.js`/`.ts` script files, and running npm/pnpm/yarn package scripts.

- **Tools:** `execute_code`, `evaluate_expression`, `execute_file`, `run_package_script`, `get_runtime_info`
- **Location:** `mcp/nodejs-executor/`
- **TypeScript Support:** Native type-stripping execution on Node.js 22+

### `project-memory`
A high-performance MCP server providing persistent project memory backed by Node.js native SQLite (`node:sqlite`), **40% semantic hybrid search**, anti-bloat guards, and strict 3-category memory partitioning (`ledger`, `sidecar`, `journal`).

- **Tools:** `save_memory`, `load_memory`, `search_memory`, `delete_memory`, `clear_sidecar`
- **Location:** `mcp/project-memory/`
- **Search:** Hybrid $(0.40 \times \text{Semantic Cosine} + 0.60 \times \text{Lexical Overlap})$ across 256-dimensional subword embeddings
- **Storage:** Local SQLite database in `.project-memory/memory.db` with zero external native compilation dependencies

## Usage

### Claude Code & Antigravity
Skills are loaded automatically from `.github/skills/`. Invoke them by using any trigger phrase above in your session.

MCP servers can be registered in your MCP configuration (`.mcp.json` or `claude_desktop_config.json`):

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
Skills in `.github/skills/` are picked up as custom instructions by Copilot Chat. Use the same trigger phrases in Copilot Chat, or reference a skill by name (e.g. `@workspace /python-linter`).

## Structure

```
mcp/
├── nodejs-executor/
│   ├── src/
│   │   ├── process/
│   │   │   ├── runner.ts
│   │   │   └── terminator.ts
│   │   ├── security/
│   │   │   ├── permissions.ts
│   │   │   ├── sanitizer.ts
│   │   │   └── validator.ts
│   │   ├── tools/
│   │   │   ├── evaluate-expr.ts
│   │   │   ├── execute-code.ts
│   │   │   ├── execute-file.ts
│   │   │   ├── package-script.ts
│   │   │   └── runtime-info.ts
│   │   ├── executor.ts
│   │   ├── index.ts
│   │   ├── server.ts
│   │   └── types.ts
│   ├── tests/
│   │   ├── executor.test.ts
│   │   └── mcp-client.test.ts
│   ├── examples/
│   │   └── demo.ts
│   ├── scripts/
│   │   └── invoke.mjs
│   ├── package.json
│   ├── tsconfig.json
│   └── README.md
└── project-memory/
    ├── src/
    │   ├── db/
    │   │   └── database.ts
    │   ├── search/
    │   │   └── semantic.ts
    │   ├── tools/
    │   │   ├── load-memory.ts
    │   │   ├── manage-memory.ts
    │   │   ├── save-memory.ts
    │   │   └── search-memory.ts
    │   ├── utils/
    │   │   └── sanitizer.ts
    │   ├── index.ts
    │   ├── server.ts
    │   └── types.ts
    ├── tests/
    │   ├── mcp-client.test.ts
    │   └── memory.test.ts
    ├── package.json
    ├── tsconfig.json
    └── README.md
.github/
└── skills/
    ├── trace-code-context/
    │   ├── SKILL.md
    │   ├── references/
    │   │   └── trace-code-context-reference.md
    │   └── scripts/
    │       └── trace-context.py
    ├── scan-halucinated-tests/
    │   ├── SKILL.md
    │   ├── references/
    │   │   └── scan-halucinated-tests-reference.md
    │   └── scripts/
    │       └── parse-test-refs.py
    ├── skill-creator/
    │   ├── SKILL.md
    │   ├── references/
    │   │   └── skill-anatomy.md
    │   └── scripts/
    │       └── scaffold-skill.py
    ├── python-linter/
    │   ├── SKILL.md
    │   └── references/
    │       └── python-linter-reference.md
    ├── github-security-scanner-hook/
    │   ├── SKILL.md
    │   ├── references/
    │   │   └── github-security-scanner-hook-reference.md
    │   ├── rules/
    │   │   └── security.yml
    │   └── scripts/
    │       ├── scan-staged.py
    │       └── install-hook.py
    ├── sync-github-forks/
    │   ├── SKILL.md
    │   └── scripts/
    │       ├── setup-ssh.sh
    │       ├── sync-forks.sh
    │       └── sync-forks.ps1
    ├── scan-repo-readme/
    │   ├── SKILL.md
    │   ├── references/
    │   │   └── search-patterns.md
    │   └── scripts/
    │       └── find-readmes.py
    ├── design-pattern-detector/
    │   ├── SKILL.md
    │   ├── references/
    │   │   └── design-pattern-detector-reference.md
    │   └── scripts/
    │       └── extract-patterns.py
    ├── detect-overengineering/
    │   ├── SKILL.md
    │   ├── references/
    │   │   └── detect-overengineering-reference.md
    │   └── scripts/
    │       └── extract-signals.py
    ├── architectural-planning/
    │   ├── SKILL.md
    │   └── references/
    │       └── architectural-planning-reference.md
    ├── nodejs-executor/
    │   ├── SKILL.md
    │   └── references/
    │       └── nodejs-executor-reference.md
    ├── llm-as-judge/
    │   ├── SKILL.md
    │   ├── README.md
    │   ├── CHANGELOG.md
    │   └── references/
    │       ├── evaluation-frameworks.md
    │       ├── judge-templates.md
    │       └── use-cases.md
    ├── save-memory/
    │   └── SKILL.md
    ├── load-memory/
    │   └── SKILL.md
    ├── agent-orchestrator/
    │   ├── SKILL.md
    │   └── scripts/
    │       └── orchestrator-context-manager.py
    ├── code-reviewer/
    │   ├── SKILL.md
    │   └── references/
    │       └── code-reviewer-reference.md
    ├── python-developer/
    │   ├── SKILL.md
    │   ├── core/
    │   ├── runtime-and-memory/
    │   ├── concurrency/
    │   ├── security/
    │   └── testing/
    ├── typescript-developer/
    │   ├── SKILL.md
    │   ├── core/
    │   ├── runtime-and-memory/
    │   ├── concurrency/
    │   ├── frameworks/
    │   ├── security/
    │   └── testing/
    ├── react-developer/
    │   ├── SKILL.md
    │   ├── core/
    │   ├── state-management/
    │   ├── runtime-and-memory/
    │   ├── server-components/
    │   └── testing/
    ├── algorithmic-complexity-analyzer/
    │   ├── SKILL.md
    │   ├── core/
    │   ├── anti-patterns/
    │   ├── data-structures/
    │   ├── optimization-patterns/
    │   └── audit-workflow/
    ├── troubleshoot-and-fix/
    │   ├── SKILL.md
    │   ├── references/
    │   │   └── troubleshoot-and-fix-reference.md
    │   └── scripts/
    │       ├── isolate-runner.js
    │       └── isolate-runner.py
    └── java-developer/
        ├── SKILL.md
        ├── plain-java/
        │   ├── collections.md
        │   ├── concurrency.md
        │   ├── conventions.md
        │   ├── dry-kiss-solid.md
        │   ├── functional-programming.md
        │   ├── jvm-and-memory.md
        │   ├── reactor-pattern.md
        │   └── security.md
        ├── design-patterns/
        │   └── patterns.md
        ├── spring-boot/
        │   ├── architecture.md
        │   ├── best-practices.md
        │   └── modernization.md
        └── testing/
            └── best-practices.md
```
