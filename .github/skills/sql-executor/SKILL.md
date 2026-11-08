---
name: sql-executor
description: Practitioner guidance for querying, tuning, validating, and troubleshooting enterprise databases (SQL Server, Oracle, PostgreSQL, SQLite, MongoDB, MS Access, MySQL) via the sql-connector MCP server. Covers multi-engine joins, GIN/GiST/BRIN indexing, stored procedures, TVFs, Oracle cursors, CTEs, #temp tables, window functions, and data validation. Use when asked to "write a sql join", "optimize sql query", "tune database index", "postgres gin index", "oracle cursor", "sql stored procedure", "sql cte", "temp table", "window function", or "run database queries".
version: 1.2.0
---

# SQL Executor

Architectural heuristics and execution guidance for querying, indexing, and optimizing enterprise relational and document databases via the **`sql-connector`** MCP server.

---

## Architectural Heuristics & Decision Matrix

| Task Category | Recommended Strategy | When NOT to Use | Trade-Offs & Rationale |
|:---|:---|:---|:---|
| **Multi-Table Joins** | ANSI-92 joins; `CROSS/OUTER APPLY` (SQL Server); `LATERAL` (Postgres) | Legacy Oracle `(+)`; unparenthesized MS Access 3+ joins | ANSI provides portable semantics; `APPLY`/`LATERAL` correlate rows without Cartesian bloat. |
| **CTEs vs #TempTables** | Chained/Recursive CTEs for trees; `#TempTable` for $> 1,000$ rows | Re-evaluating expensive CTEs multiple times in SQL Server | CTEs inline cleanly; `#TempTable` provides full column histograms, indexes, and TempDB caching. |
| **Specialized Indexing**| GIN for JSONB/trigrams; GiST for ranges; BRIN for append-only logs | B-Trees on high-cardinality JSONB/text or terabyte append-only logs | GIN enables containment/trigram search; BRIN gives 99% space savings on sequential data. |
| **Stored Procedures & TVFs** | Inline TVFs (iTVFs); parameterized `sp_executesql` / `CALL` | Multi-statement TVFs (mTVFs); string concatenation SQL | iTVFs inline into optimizer plans; dynamic SQL with parameters blocks SQL injection. |
| **Oracle Cursors** | `SYS_REFCURSOR` for drivers; `BULK COLLECT` + `LIMIT 1000` | Row-by-row (RBAR) loops; `BULK COLLECT` without `LIMIT` | Bulk operations eliminate PL/SQL context switches; `LIMIT` prevents PGA memory exhaustion. |
| **Window Functions** | `ROWS BETWEEN ...` framing; `DENSE_RANK()` for top $N$ per group | Unbounded `RANGE BETWEEN` when physical rows suffice | `ROWS` operates on physical offsets avoiding temporary disk spooling. |

---

## 🛡️ Over-Engineering Self-Check (Anti-Bloat Guardrail)

Before generating queries, stored procedures, or table schemas, consult [`detect-overengineering`](file:///.github/skills/detect-overengineering/SKILL.md):
- **Avoid Speculative Indexes**: Do not index every column proactively. Only index proven predicates.
- **Avoid Query Ceremony**: Prefer simple ANSI joins over multi-level nested CTEs unless intermediate materialization is required.
- **Avoid `SELECT *`**: Explicitly specify required columns to enable Index-Only Scans.

---

## 📚 Modular Deep Topics

- **[MCP Workflow & Schema Discovery](file:///.github/skills/sql-executor/mcp-operations/mcp-workflow-and-discovery.md)** — Discovery workflow, tool payloads, and connection handling.
- **[Multi-Engine Joins Architecture](file:///.github/skills/sql-executor/joins/multi-engine-joins.md)** — Dialect-specific join syntax, `APPLY`, `LATERAL`, and MS Access parentheses rules.
- **[Temporary Structures, CTEs & #TempTables](file:///.github/skills/sql-executor/temporary-tables-and-ctes/temp-tables-and-ctes.md)** — Chained/Recursive CTEs, CTE materialization, `#TempTable` vs `@TableVariable`, and GTTs.
- **[Window Functions, TVFs & Pivoting](file:///.github/skills/sql-executor/advanced-querying/window-functions-tvfs-and-pivots.md)** — Analytic window functions (`ROWS` vs `RANGE`), cross-engine TVFs, and matrix pivoting.
- **[Indexing & Performance Tuning](file:///.github/skills/sql-executor/indexing-and-tuning/indexing-and-performance-tuning.md)** — B-trees, composite ordering, sargability anti-patterns, and execution plans.
- **[PostgreSQL Specialized Indexing](file:///.github/skills/sql-executor/indexing-and-tuning/postgres-specialized-indexes.md)** — GIN (`jsonb_ops`, `jsonb_path_ops`, `pg_trgm`), GiST, and BRIN time-series indexes.
- **[Stored Procedures, TVFs & Dynamic SQL](file:///.github/skills/sql-executor/stored-procedures-and-routines/stored-procedures-and-tvfs.md)** — iTVFs vs mTVFs, output parameters, and `sp_executesql`.
- **[Oracle Cursors & PL/SQL Optimization](file:///.github/skills/sql-executor/oracle-plsql/oracle-cursors-and-plsql.md)** — `SYS_REFCURSOR`, `BULK COLLECT` + `FORALL` batching, and cursor locking.
- **[Data Extraction & Validation](file:///.github/skills/sql-executor/data-validation/data-extraction-and-validation.md)** — Uniqueness, orphan checks, nullability audits, and checksums.
- **[Troubleshooting & Firewall Resolution](file:///.github/skills/sql-executor/troubleshooting/troubleshooting-and-firewall.md)** — Resolving firewall blocks, deadlocks, and driver setup.



