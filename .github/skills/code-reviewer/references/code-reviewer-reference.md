# Code Reviewer Reference Guide

Advanced code review strategies, cognitive heuristics, language-specific checklist matrices, and specialized domain auditing guides.

---

## 1. Review Heuristics & Cognitive Biases

A senior code reviewer approaches code with a specific lens and consciously avoids cognitive traps:

1. **Verify the Problem First**:
   - Before reading single lines of code, read the user requirements, issue description, or architectural spec.
   - Ask: "Does this patch actually solve the problem it claims to solve?"
2. **Review Tests Before Implementation**:
   - Inspect test files first. Do the tests prove the new behavior? Do they fail when the behavior is broken?
   - If tests only cover the golden path, flag missing edge cases immediately.
3. **Trace the Data Flow**:
   - Follow external inputs from the entrypoint (HTTP controller, event listener, or CLI command) down to database/disk and back.
   - Look for missing sanitization, unvalidated type casts, and state mutations.
4. **Assume Unhappy Paths**:
   - What happens when network disconnects or times out?
   - What happens if the database returns 0 rows or violates a unique constraint?
   - What happens if disk is full or read-only?
   - What happens if concurrent requests arrive with the exact same ID or token?

### Avoiding Review Cognitive Biases
- **Bikeshedding (Parkinson's Law of Triviality)**: Do not spend 80% of review energy arguing over formatting, spacing, or variable naming while ignoring complex concurrency or SQL table scans. Let automated linters handle formatting.
- **Anchoring Bias**: Do not assume the author's chosen design pattern is necessary just because they wrote code for it. Check whether the problem could be solved with simpler, existing constructs.
- **Review Fatigue**: When reviewing large diffs (> 300 lines), break review into passes: first architecture and tests, then edge cases and security, then style.

---

## 2. Language-Specific Review Checklist Matrices

For deep guidelines, consult the dedicated review modules in each language directory.

### Python Reviews
*Detailed Modules: [Python Checklist](file:///.github/skills/code-reviewer/python/python-review-checklist.md) | [Web API Review](file:///.github/skills/code-reviewer/python/web-api-review.md) | [Concurrency & Memory](file:///.github/skills/code-reviewer/python/concurrency-and-memory-review.md)*
- **Typing:** Are return types and parameter types annotated? Are `Optional[T]` or `T | None` used where `None` can be returned?
- **Collections & Caching:** Are dict lookups using `.get()` or catching `KeyError`? Are `@functools.lru_cache` calls bounded with an explicit `maxsize`?
- **Async & Event Loop:** Is `asyncio.sleep()` called instead of blocking `time.sleep()`? Are CPU-bound or sync operations offloaded with `asyncio.to_thread()`?
- **Resource Cleanup:** Are file handles, sockets, and database sessions managed in `with` / `async with` blocks?
- **Closures & Scope:** Are default arguments immutable (no `target=[]` or `target={}`)? Are loop variables in closures bound at definition time (`lambda i=i: i`)?
- **Memory & References:** Are circular references avoided or decoupled via `weakref`? Are generators (`yield`) used for large dataset iteration?

### TypeScript / JavaScript Reviews
*Detailed Modules: [TypeScript Checklist](file:///.github/skills/code-reviewer/typescript/typescript-review-checklist.md) | [Node & Runtime Memory](file:///.github/skills/code-reviewer/typescript/node-and-runtime-review.md) | [Async & Concurrency](file:///.github/skills/code-reviewer/typescript/async-and-concurrency-review.md)*
- **Strict Typing:** Is `any` used? (Flag as P1). Is `as Type` force-casting without validation?
- **Equality:** Is `===` used instead of `==`?
- **Async & Concurrency:** Are promises awaited or chained? Are there unhandled floating promises? Is `Promise.all` bounded using concurrency throttling (`p-limit`)?
- **Nullish Coalescing:** Is `??` used where falsy values like `0` or `""` are legitimate?
- **Closure & Scope Hygiene:** Do callbacks or event handlers accidentally retain large outer objects or request contexts?
- **Memory & Resource Hygiene:** Are event listeners, intervals, and observers cleaned up (using `AbortSignal`, `.off()`, or `clearInterval`)? Are caches bounded (LRU) rather than unbounded `Map`/`Set`? Are large files streamed rather than buffered in RAM?

### React Reviews
*Detailed Modules: [React Checklist](file:///.github/skills/code-reviewer/react/react-review-checklist.md) | [Hooks & Rendering](file:///.github/skills/code-reviewer/react/hooks-and-rendering-review.md) | [State & Fetching](file:///.github/skills/code-reviewer/react/state-and-data-fetching-review.md) | [RSC & Next.js](file:///.github/skills/code-reviewer/react/rsc-and-nextjs-review.md)*
- **Pure Render Functions:** Are component bodies pure and free from mutations, random IDs, or side-effects during render?
- **Exhaustive Dependencies:** Do `useEffect`, `useCallback`, and `useMemo` declare all referenced variables in their dependency arrays?
- **State Architecture:** Is derived state calculated on-the-fly rather than synced via redundant `useEffect` + `useState` pairs?
- **Server vs. Client Components:** Are interactive elements isolated to leaf client components (`'use client'`) while layouts/pages remain Server Components?
- **Server Actions:** Are `'use server'` mutations properly authenticating callers and validating schema inputs with Zod?

### Java Reviews
*Detailed Modules: [Java Checklist](file:///.github/skills/code-reviewer/java/java-review-checklist.md) | [Spring Boot & Data](file:///.github/skills/code-reviewer/java/spring-boot-and-data-review.md) | [Virtual Threads & JVM](file:///.github/skills/code-reviewer/java/concurrency-and-jvm-review.md)*
- **Null Safety:** Are `Optional<T>` methods used properly without blind `.get()` calls?
- **Immutability:** Are DTOs using Java Records (`record User(...)`)?
- **Streams & Memory:** Are stream operations side-effect free? Are large result sets streamed / paginated rather than collected into large heap lists?
- **Memory Leaks:** Are static collections bounded? Are `ThreadLocal` variables cleared in `finally` blocks? Are non-static inner classes avoiding unintended outer reference retention?
- **Concurrency:** Are threads pinned on carrier threads in Virtual Threads (e.g. `synchronized` blocks doing I/O)?
- **Transactions & Resources:** Are `@Transactional` methods public and called from outside the class instance? Are all `AutoCloseable` resources managed in `try-with-resources`?

### C# (.NET) Reviews
*Detailed Modules: [C# Checklist](file:///.github/skills/code-reviewer/csharp/csharp-review-checklist.md) | [ASP.NET & EF Core](file:///.github/skills/code-reviewer/csharp/aspnet-and-efcore-review.md) | [Performance & Runtime](file:///.github/skills/code-reviewer/csharp/performance-and-runtime-review.md)*
- **Cancellation Propagation:** Do all async methods accept and forward `CancellationToken cancellationToken = default` down to I/O calls?
- **Resource Cleanup:** Are `IDisposable` and `IAsyncDisposable` objects handled with `using` or `await using` declarations?
- **Async Avoidance of `async void`:** Are all async methods returning `Task` or `Task<T>`, never `async void` (except top-level UI event handlers)?
- **EF Core Performance:** Are read-only queries marked with `.AsNoTracking()`? Are queries evaluating client-side due to unsupported expressions?
- **LINQ Deferred Execution:** Are `IEnumerable<T>` queries enumerated multiple times without `.ToList()` or `.ToArray()`?
- **Memory Allocation:** Are hot path string or buffer operations using `Span<T>`, `ReadOnlySpan<T>`, or `ArrayPool<T>` instead of allocating heap arrays?

### Go Reviews
*Detailed Modules: [Go Checklist](file:///.github/skills/code-reviewer/go/go-review-checklist.md) | [Concurrency & Runtime](file:///.github/skills/code-reviewer/go/concurrency-and-runtime-review.md)*
- **Context Propagation:** Is `ctx context.Context` the first argument of all I/O or RPC functions and forwarded down?
- **Goroutine Leaks:** Does every spawned goroutine have a guaranteed exit path via context cancellation, closed channel, or timeout?
- **Defer in Loops:** Are `defer f.Close()` calls placed inside long-running loops instead of calling explicitly or wrapping in a helper function?
- **Error Wrapping:** Are errors wrapped with `fmt.Errorf("failed doing x: %w", err)` to preserve causal chains?
- **Receiver Consistency:** Are struct methods consistent with pointer receivers `(s *Service)` vs value receivers `(s Service)` to avoid unintentional mutation or slice copying?

### SQL Reviews
*Detailed Modules: [SQL Checklist](file:///.github/skills/code-reviewer/sql/sql-review-checklist.md) | [Indexing & Execution Plans](file:///.github/skills/code-reviewer/sql/indexing-and-execution-plans-review.md) | [Procedures, TVFs & Cursors](file:///.github/skills/code-reviewer/sql/procedures-tvfs-and-cursors-review.md) | [Analytics & Windowing](file:///.github/skills/code-reviewer/sql/analytics-and-windowing-review.md)*
- **Destructive SQL Guardrails:** Are `DROP TABLE`, `TRUNCATE`, or unconstrained `DELETE` statements absent?
- **Parameterization:** Are queries strictly parameterized against SQL injection?
- **NULL Semantics:** Is three-valued logic handled (`IS NULL` vs `= NULL`, `NOT IN` with nullable subqueries)?
- **Execution Plans & SARGability:** Do execution plans avoid $O(N)$ full table scans? Are predicates SARGable (no functions on indexed columns)?
- **Indexes:** Are specialized indexes (GIN, GiST, BRIN, covering `INCLUDE`) utilized where appropriate?
- **Routines & Cursors:** Are inline TVFs preferred over multi-statement TVFs? Are cursors avoided or bounded with `BULK COLLECT LIMIT`?

---

## 3. Specialized Domain Review Guides

### A. Distributed Caching & Message Queues
When inspecting code that uses Redis, Kafka, or RabbitMQ, cross-reference [`caching-queues-reviewer`](file:///.github/skills/caching-queues-reviewer/SKILL.md):
- **Redis Distributed Locks:** Is release implemented using an atomic Lua script comparing token ownership? Is lock expiration bounded with a TTL?
- **Cache Stampede Prevention:** Are hot keys protected using probabilistic early expiration (XFetch), mutex locks, or `HybridCache`?
- **Kafka Producer Idempotency:** Is `enable.idempotence=true` configured? Are partition keys well-distributed to prevent hot partition skew?
- **Consumer Reliability:** Are failed messages routed to a Dead-Letter Queue (DLQ) with exponential backoff rather than infinite retry loops?
- **Transactional Outbox:** Are database state changes and message publications coordinated via the Outbox pattern rather than dual-write antipatterns?

### B. Database Queries & Schema Review
When reviewing SQL queries, migrations, or ORM queries, cross-reference [`sql-executor`](file:///.github/skills/sql-executor/SKILL.md):
- **Execution Plans:** Run `explain_query` or examine query plans to ensure indexes (B-Tree, GIN, BRIN) eliminate $O(N)$ full table scans.
- **CTEs vs. Temporary Tables:** In SQL Server / Oracle, are complex multi-step queries materializing intermediate sets into `#temp` tables to avoid re-evaluating costly CTEs?
- **Table-Valued Functions (TVFs):** Are inline TVFs preferred over multi-statement TVFs to allow the optimizer to push predicates down?
- **Destructive SQL Guardrails:** Ensure no raw `DROP TABLE`, `TRUNCATE`, or unconstrained `DELETE` statements exist in application code.

### C. API Security & Authentication
When reviewing controllers, middleware, or auth handlers, cross-reference [`api-security`](file:///.github/skills/api-security/SKILL.md):
- **JWT Algorithms:** Are asymmetric algorithms (RS256, ES256) enforced? Is algorithm `none` explicitly rejected?
- **OAuth 2.1 PKCE:** Is Proof Key for Code Exchange (S256 code challenge) enforced for authorization code grants?
- **Session Cookie Flags:** Are session cookies configured with `HttpOnly; Secure; SameSite=Strict` (or `Lax`)?
- **API Key Security:** Are API keys hashed (SHA-256) at rest rather than stored in plaintext?

### D. Architecture & Anti-Bloat Auditing
When reviewing abstractions, interfaces, and module structure, cross-reference [`detect-overengineering`](file:///.github/skills/detect-overengineering/SKILL.md):
- **Layer Depth:** Is the call chain limited to $\le 3$ layers (e.g., Controller $\to$ Service $\to$ Repository)?
- **Speculative Interfaces:** Does an interface have only one implementation with no polymorphism or test mock justification?
- **Trampoline Methods:** Are there pass-through methods that simply forward arguments to the next layer without transformation or logic?

---

## 4. Review Comment Principles & Constructive Feedback

1. **Be Specific:** Always point to the exact file, line number, and concrete mechanism.
2. **Explain the "Why":** Explain the technical reason, performance implication, concurrency risk, or bug potential.
3. **Provide Drop-In Solutions:** Include a concise diff whenever possible so the author can immediately verify the recommendation.
4. **Distinguish Requirements from Suggestions:** Always prefix comments with standardized severity tags:
   - `[P0 - Blocker]`: Prevents acceptance, breaks contract or security.
   - `[P1 - Major]`: Must be resolved before merge.
   - `[P2 - Minor]`: Strongly recommended improvement.
   - `[P3 - Nit]`: Optional polish or style preference.

---

## 5. References

- [API Security](file:///.github/skills/api-security/SKILL.md) — Universal API authentication, token security, and cryptographic audit.
- [Caching & Queues Reviewer](file:///.github/skills/caching-queues-reviewer/SKILL.md) — Redis, Kafka, and RabbitMQ architecture and code review.
- [SQL Executor](file:///.github/skills/sql-executor/SKILL.md) — Multi-engine SQL query tuning, indexing, and validation.
- [Detect Overengineering](file:///.github/skills/detect-overengineering/SKILL.md) — Anti-bloat heuristics and YAGNI auditing.
- [Algorithmic Complexity Analyzer](file:///.github/skills/algorithmic-complexity-analyzer/SKILL.md) — Time and space complexity auditing.
- [Troubleshoot and Fix](file:///.github/skills/troubleshoot-and-fix/SKILL.md) — Isolated testbed reproduction and 3-iteration circuit breaker remediation.
- [Scan Hallucinated Tests](file:///.github/skills/scan-halucinated-tests/SKILL.md) — AST ground-truth test verification.
