---
name: sql-executor
description: Practitioner guidance for querying, tuning, validating, and troubleshooting enterprise databases (SQL Server, Oracle, PostgreSQL, SQLite, MongoDB, MS Access, MySQL) via the sql-connector MCP server. Covers multi-engine joins, index design, execution plan tuning, sargability, data extraction validation, and firewall resolution. Use when asked to "write a sql join", "optimize sql query", "tune database index", "validate extracted data", "troubleshoot slow query", "explain query plan", or "run database queries".
version: 1.0.0
---

# SQL Executor

Architectural heuristics and execution guidance for querying, indexing, and optimizing enterprise relational and document databases via the **`sql-connector`** MCP server.

---

## Architectural Heuristics & Decision Matrix

| Task Category | Recommended Strategy | When NOT to Use | Trade-Offs & Rationale |
|:---|:---|:---|:---|
| **Multi-Table Joins** | ANSI-92 standard joins; `CROSS/OUTER APPLY` in SQL Server; `LATERAL` in Postgres | Legacy Oracle `(+)` syntax; unparenthesized MS Access 3+ joins | ANSI joins provide portable semantics; `APPLY`/`LATERAL` enable correlated subquery joins without Cartesian bloat. |
| **Composite Indexing** | [Equality] $\to$ [Range] $\to$ [ORDER BY] column order | Single-column indexes on high-cardinality multi-predicate queries | Ordering equality predicates first allows the B-tree to navigate directly to the target slice before scanning the range. |
| **Covering Indexes** | `INCLUDE (cols)` (SQL Server/Postgres) | Adding all table columns to index leaf | Eliminates heap lookups, but increases index storage and write amplification on table mutations. |
| **Pagination** | Keyset pagination (`WHERE id > last_seen`) | High-offset pagination (`OFFSET 100000`) | Keyset pagination is $O(\log N)$ via index seek; high offset is $O(N)$ scanning and discarding rows. |
| **Extraction Validation**| Group-by count assertions, orphan detection | Relying on unverified row counts | Catches partial extractions, foreign key corruption, and silent nullability violations. |

---

## 🛡️ Over-Engineering Self-Check (Anti-Bloat Guardrail)

Before generating queries, stored procedures, or table schemas, consult [`detect-overengineering`](file:///.github/skills/detect-overengineering/SKILL.md):
- **Avoid Speculative Indexes**: Do not index every column proactively. Only index columns with proven cardinality in `WHERE`, `JOIN`, or `ORDER BY` predicates.
- **Avoid Query Ceremony**: Prefer simple ANSI joins over multi-level nested CTEs or temporary tables unless intermediate materialization is required.
- **Avoid `SELECT *`**: Explicitly specify only required columns to reduce network bandwidth and enable Index-Only Scans.

---

## 📚 Modular Deep Topics

- **[MCP Workflow & Schema Discovery](file:///.github/skills/sql-executor/mcp-operations/mcp-workflow-and-discovery.md)** — Discovery workflow, tool payloads, and connection handling.
- **[Multi-Engine Joins Architecture](file:///.github/skills/sql-executor/joins/multi-engine-joins.md)** — Dialect-specific join syntax, `APPLY`, `LATERAL`, and MS Access parentheses rules.
- **[Indexing & Performance Tuning](file:///.github/skills/sql-executor/indexing-and-tuning/indexing-and-performance-tuning.md)** — B-trees, composite ordering, sargability anti-patterns, and execution plans.
- **[Data Extraction & Validation](file:///.github/skills/sql-executor/data-validation/data-extraction-and-validation.md)** — Uniqueness, orphan checks, nullability audits, and checksums.
- **[Troubleshooting & Firewall Resolution](file:///.github/skills/sql-executor/troubleshooting/troubleshooting-and-firewall.md)** — Resolving firewall blocks, deadlocks, and driver setup.
