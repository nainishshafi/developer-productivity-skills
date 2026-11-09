---
name: sql-executor
description: Practitioner guidance for querying, tuning, validating, and troubleshooting enterprise databases (SQL Server, Oracle, PostgreSQL, SQLite, MongoDB, MS Access, MySQL) via the sql-connector MCP server. Covers multi-engine joins, query optimization methods, GIN/GiST/BRIN indexing, stored procedures, TVFs, Oracle cursors, CTEs, #temp tables, OLAP cubing, window functions, and cohort analytics. Use when asked to "write a sql join", "optimize sql query", "tune database index", "query optimization", "sql performance tuning", "sql cube", "grouping sets", "sql cohort analysis", "postgres gin index", "oracle cursor", "sql stored procedure", "sql cte", or "run database queries".
version: 1.4.0
---

# SQL Executor

Architectural heuristics and execution guidance for querying, indexing, and optimizing enterprise relational and document databases via the **`sql-connector`** MCP server.

---

## Architectural Heuristics & Decision Matrix

| Task Category | Recommended Strategy | When NOT to Use | Trade-Offs & Rationale |
|:---|:---|:---|:---|
| **Multi-Table Joins** | ANSI-92 joins; `CROSS/OUTER APPLY` (SQL Server); `LATERAL` (Postgres) | Legacy Oracle `(+)`; unparenthesized MS Access 3+ joins | ANSI provides portable semantics; `APPLY`/`LATERAL` correlate rows without Cartesian bloat. |
| **CTEs vs #TempTables** | Chained/Recursive CTEs for trees; `#TempTable` for $> 1,000$ rows | Re-evaluating expensive CTEs multiple times in SQL Server | CTEs inline cleanly; `#TempTable` provides full column histograms, indexes, and TempDB caching. |
| **OLAP & Cubing** | `GROUP BY GROUPING SETS` / `ROLLUP` | Unbounded `CUBE` on $> 4$ dimensions ($2^N$ blowup) | `GROUPING SETS` avoids combinatorial explosion of unnecessary sub-aggregations. |
| **Specialized Indexing**| GIN for JSONB/trigrams; GiST for ranges; BRIN for append-only logs | B-Trees on high-cardinality JSONB/text or terabyte append-only logs | GIN enables containment/trigram search; BRIN gives 99% space savings on sequential data. |
| **Stored Procedures & TVFs** | Inline TVFs (iTVFs); parameterized `sp_executesql` / `CALL` | Multi-statement TVFs (mTVFs); string concatenation SQL | iTVFs inline into optimizer plans; dynamic SQL with parameters blocks SQL injection. |
| **Oracle Cursors** | `SYS_REFCURSOR` for drivers; `BULK COLLECT` + `LIMIT 1000` | Row-by-row (RBAR) loops; `BULK COLLECT` without `LIMIT` | Bulk operations eliminate PL/SQL context switches; `LIMIT` prevents PGA memory exhaustion. |
| **Window Functions** | `ROWS BETWEEN ...` framing; `DENSE_RANK()` for top $N$ per group | Unbounded `RANGE BETWEEN` when physical rows suffice | `ROWS` operates on physical offsets avoiding temporary disk spooling. |

---

## 🚀 Query Optimization Methods & Techniques

Apply these 7 core query optimization methods when diagnosing slow queries, reducing I/O bottlenecks, or tuning database execution plans:

### 1. Sargable Predicate Optimization (Enabling B-Tree Index Seeks)
A query is **sargable** (Search Argument Able) when the database engine can seek directly into an index ($O(\log N)$) instead of scanning every page ($O(N)$). Wrapping columns in functions or calculations destroys sargability.

| Anti-Pattern (Non-Sargable / Full Scan) | Optimized Sargable Rewrite (Index Seek) | Root Cause & Mechanism |
|:---|:---|:---|
| `WHERE DATE(created_at) = '2026-03-15'` | `WHERE created_at >= '2026-03-15' AND created_at < '2026-03-16'` | Function evaluation forces table-wide row evaluation. |
| `WHERE amount + 50 > 500` | `WHERE amount > 450` | Arithmetic on column prevents B-tree traversal. |
| `WHERE LOWER(email) = 'user@corp.com'` | `WHERE email = 'user@corp.com'` *(or functional index)* | Scalar function invalidates standard B-tree index. |
| `WHERE varchar_key = 1042` *(numeric literal)* | `WHERE varchar_key = '1042'` | Implicit data type conversion casts every column value. |
| `WHERE name LIKE '%smith'` | `WHERE name LIKE 'smith%'` *(or GIN/trigram index)* | Leading wildcard prevents root-to-leaf B-tree navigation. |
| `WHERE status <> 'DELETED'` | `WHERE status IN ('ACTIVE', 'PENDING', 'SUSPENDED')` | Inequality/negation cannot isolate a B-tree search range. |

---

### 2. Composite & Covering Index Design (Equality $\to$ Range $\to$ Include)
To eliminate expensive Heap/Clustered Index Lookups (random I/O), align composite index column orders and leaf payload columns:

1. **Column Sequence Rule**:
   $$\text{Index Columns: } [ \text{Equality Predicates } (=) ] \longrightarrow [ \text{Range / Inequality } (<, >, \text{BETWEEN}) ] \longrightarrow [ \text{ORDER BY Columns} ]$$
2. **Covering Leaf Projections (`INCLUDE`)**:
   Add projected columns to index leaf pages to achieve **Index-Only Scans** (0 heap touches):
   ```sql
   -- PostgreSQL / SQL Server covering index:
   CREATE INDEX idx_orders_covering 
   ON orders (store_id, order_date) 
   INCLUDE (total_amount, customer_id);

   -- Query executes entirely within index leaf memory:
   SELECT total_amount, customer_id 
   FROM orders 
   WHERE store_id = 42 AND order_date >= '2026-01-01';
   ```

---

### 3. Keyset / Seek Pagination ($O(1)$ vs. Deep $O(N)$ `OFFSET`)
Offset pagination (`OFFSET 100000 ROWS FETCH NEXT 25`) forces the engine to read and discard $100,000$ rows from disk for every page request.

```sql
-- ❌ Suboptimal (Degrades to O(N) full scan on deep pages):
SELECT id, title, created_at FROM articles
ORDER BY created_at DESC, id DESC
OFFSET 100000 ROWS FETCH NEXT 25 ROWS ONLY;

-- ✅ Optimal Keyset / Cursor Pagination (Constant O(1) or O(log N) seek):
SELECT id, title, created_at FROM articles
WHERE (created_at < :last_seen_created_at)
   OR (created_at = :last_seen_created_at AND id < :last_seen_id)
ORDER BY created_at DESC, id DESC
FETCH FIRST 25 ROWS ONLY;
```

---

### 4. Semi-Join (`EXISTS`) over `IN` and Deduplicating `DISTINCT`
Avoid using `SELECT DISTINCT` after joining one-to-many tables. Joining parent to child duplicates parent rows in memory only to spend CPU deduplicating them.

```sql
-- ❌ Suboptimal (Generates cartesian duplicates, then sorts/hashes to deduplicate):
SELECT DISTINCT c.id, c.name 
FROM customers c
INNER JOIN orders o ON c.id = o.customer_id
WHERE o.status = 'COMPLETED';

-- ✅ Optimal (Short-circuits on first matching child row, zero memory bloat):
SELECT c.id, c.name 
FROM customers c
WHERE EXISTS (
    SELECT 1 FROM orders o 
    WHERE o.customer_id = c.id AND o.status = 'COMPLETED'
);
```
> [!NOTE]
> `NOT EXISTS` is immune to `NULL` pitfalls, whereas `NOT IN (SELECT col ...)` returns **0 rows** if the subquery returns even a single `NULL`.

---

### 5. Set Operations: `UNION ALL` vs. Deduplicating `UNION`
- **Default to `UNION ALL`**: Appends result streams in constant $O(1)$ memory.
- **Avoid bare `UNION`**: Forces the engine to perform an expensive $O(N \log N)$ sort or in-memory hash table deduplication pass across both streams unless duplicates are strictly impossible to tolerate.

---

### 6. Window Function Framing Optimization (`ROWS` vs. `RANGE`)
When using window aggregate functions (`SUM() OVER (...)`, `AVG() OVER (...)`):
```sql
-- ❌ Suboptimal (Default 'RANGE BETWEEN' creates disk/memory spools to check peer ties):
SELECT employee_id, salary,
       SUM(salary) OVER (PARTITION BY department_id ORDER BY hire_date) AS dept_running_total
FROM employees;

-- ✅ Optimal (Explicit 'ROWS BETWEEN' avoids spooling by operating on physical rows):
SELECT employee_id, salary,
       SUM(salary) OVER (
           PARTITION BY department_id 
           ORDER BY hire_date 
           ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
       ) AS dept_running_total
FROM employees;
```

---

### 7. Systematic 5-Step Optimization Diagnostic Workflow

When profiling a slow query with `sql-connector`:

```
┌─────────────────────────────────┐
│ 1. Benchmark Logical Reads      │ ──► Focus on page reads in RAM (shared hit / logical reads), not clock time
└────────────────┬────────────────┘
                 │
                 ▼
┌─────────────────────────────────┐
│ 2. Check Cardinality Estimates  │ ──► Compare Estimated Rows vs Actual Rows (update stale histograms/stats)
└────────────────┬────────────────┘
                 │
                 ▼
┌─────────────────────────────────┐
│ 3. Check "Rows Removed by Filter"│ ──► Add discarded filter columns to composite index
└────────────────┬────────────────┘
                 │
                 ▼
┌─────────────────────────────────┐
│ 4. Convert Scans into Seeks     │ ──► Eliminate non-sargable functions, casts, or leading wildcards
└────────────────┬────────────────┘
                 │
                 ▼
┌─────────────────────────────────┐
│ 5. Eliminate Memory Spills      │ ──► Fix Sort/Hash Spills to TempDB/Disk by indexing ORDER BY or increasing memory
└─────────────────────────────────┘
```

#### Diagnostic Commands by Database Engine:
- **PostgreSQL**: `EXPLAIN (ANALYZE, BUFFERS, VERBOSE)` &rarr; Check `Buffers: shared hit/read` and `Rows Removed by Filter`.
- **SQL Server**: `SET STATISTICS IO, TIME ON;` &rarr; Check `logical reads`, `physical reads`, and `CPU time vs. elapsed time`.
- **Oracle**: `SET AUTOTRACE ON STATISTICS;` or `SELECT * FROM TABLE(DBMS_XPLAN.DISPLAY_CURSOR());` &rarr; Check `consistent gets`.
- **MySQL**: `EXPLAIN ANALYZE SELECT ...;` &rarr; Check table scan costs and join buffering.
- **SQLite**: `EXPLAIN QUERY PLAN SELECT ...;` &rarr; Verify presence of `SEARCH TABLE ... USING INDEX` (seek) vs `SCAN TABLE` (scan).

---

## 🛡️ Over-Engineering Self-Check (Anti-Bloat Guardrail)

Before generating queries, stored procedures, or table schemas, consult [`detect-overengineering`](file:///.github/skills/detect-overengineering/SKILL.md):
- **Avoid Speculative Indexes**: Do not index every column proactively. Only index proven predicates.
- **Avoid Query Ceremony**: Prefer simple ANSI joins over multi-level nested CTEs unless intermediate materialization is required.
- **Avoid `SELECT *`**: Explicitly specify required columns to enable Index-Only Scans.

---

## 📚 Modular Deep Topics

- **[Query Optimization Reference Guide](file:///.github/skills/sql-executor/query-optimization/query-optimization-reference.md)** — Architectural reference for CBO cost models, join algorithms, sargability, pagination, and diagnostic playbooks.
- **[MCP Workflow & Schema Discovery](file:///.github/skills/sql-executor/mcp-operations/mcp-workflow-and-discovery.md)** — Discovery workflow, tool payloads, and connection handling.
- **[Multi-Engine Joins Architecture](file:///.github/skills/sql-executor/joins/multi-engine-joins.md)** — Dialect-specific join syntax, `APPLY`, `LATERAL`, and MS Access parentheses rules.
- **[Temporary Structures, CTEs & #TempTables](file:///.github/skills/sql-executor/temporary-tables-and-ctes/temp-tables-and-ctes.md)** — Chained/Recursive CTEs, CTE materialization, `#TempTable` vs `@TableVariable`, and GTTs.
- **[OLAP Cubing & Advanced Analytics](file:///.github/skills/sql-executor/advanced-querying/olap-cubing-and-analytics.md)** — CUBE, ROLLUP, GROUPING SETS, percentiles, sessionization, and cohort retention.
- **[Window Functions, TVFs & Pivoting](file:///.github/skills/sql-executor/advanced-querying/window-functions-tvfs-and-pivots.md)** — Analytic window functions (`ROWS` vs `RANGE`), cross-engine TVFs, and matrix pivoting.
- **[Indexing & Performance Tuning](file:///.github/skills/sql-executor/indexing-and-tuning/indexing-and-performance-tuning.md)** — B-trees, composite ordering, sargability anti-patterns, and execution plans.
- **[PostgreSQL Specialized Indexing](file:///.github/skills/sql-executor/indexing-and-tuning/postgres-specialized-indexes.md)** — GIN (`jsonb_ops`, `jsonb_path_ops`, `pg_trgm`), GiST, and BRIN time-series indexes.
- **[Stored Procedures, TVFs & Dynamic SQL](file:///.github/skills/sql-executor/stored-procedures-and-routines/stored-procedures-and-tvfs.md)** — iTVFs vs mTVFs, output parameters, and `sp_executesql`.
- **[Oracle Cursors & PL/SQL Optimization](file:///.github/skills/sql-executor/oracle-plsql/oracle-cursors-and-plsql.md)** — `SYS_REFCURSOR`, `BULK COLLECT` + `FORALL` batching, and cursor locking.
- **[Data Extraction & Validation](file:///.github/skills/sql-executor/data-validation/data-extraction-and-validation.md)** — Uniqueness, orphan checks, nullability audits, and checksums.
- **[Troubleshooting & Firewall Resolution](file:///.github/skills/sql-executor/troubleshooting/troubleshooting-and-firewall.md)** — Resolving firewall blocks, deadlocks, and driver setup.




