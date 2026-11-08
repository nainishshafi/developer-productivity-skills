# Indexing & Query Performance Tuning Guide

Architectural heuristics for index design, sargability optimization, and execution plan diagnosis across enterprise database engines.

---

## 1. Core Indexing Heuristics

### A. The "Equality First, Range Second" Rule for Composite Indexes
When creating composite indexes for queries containing both equality (`=`) and range (`<`, `>`, `BETWEEN`, `LIKE 'prefix%'`) predicates:

$$\text{Index Columns: } [ \text{Equality Predicates} ] \longrightarrow [ \text{Range / Inequality Predicates} ] \longrightarrow [ \text{ORDER BY Columns} ]$$

```sql
-- Query:
SELECT id, total FROM orders 
WHERE store_id = 42 AND created_at >= '2026-01-01' 
ORDER BY total DESC;

-- OPTIMAL Index:
CREATE INDEX idx_orders_composite 
ON orders (store_id, created_at, total);
```

### B. Covering Indexes (Index-Only Scans)
Eliminate expensive heap table lookups (Clustered Index Lookups or Table Access by RowID) by including projection columns in the index leaf pages:

```sql
-- PostgreSQL & SQL Server (using INCLUDE):
CREATE INDEX idx_customers_covering 
ON customers (country, status) 
INCLUDE (name, email, phone);

-- Query executes entirely in index leaf without touching table heap:
SELECT name, email, phone FROM customers 
WHERE country = 'US' AND status = 'active';
```

### C. Partial / Filtered Indexes
Save storage and buffer pool memory by indexing only the active or queried subset of rows:

```sql
-- PostgreSQL:
CREATE INDEX idx_unprocessed_events 
ON events (created_at) 
WHERE processed = false;

-- SQL Server:
CREATE NONCLUSTERED INDEX idx_pending_orders 
ON orders (customer_id, order_date) 
WHERE status = 'PENDING';
```

---

## 2. Sargability (Search Argument Ability) Anti-Patterns

A query is **sargable** if the database engine can take advantage of an index to filter rows directly via B-tree seeks ($O(\log N)$) rather than scanning every row ($O(N)$).

| Anti-Pattern (Non-Sargable) | Problem | Optimized Sargable Rewrite |
|:---|:---|:---|
| `WHERE YEAR(created_at) = 2026` | Wraps column in function; invalidates B-tree index seek. | `WHERE created_at >= '2026-01-01' AND created_at < '2027-01-01'` |
| `WHERE LOWER(email) = 'user@corp.com'` | Disables index scan unless function-based index exists. | Store email pre-lowercased, or create `INDEX ON table (LOWER(email))` |
| `WHERE SUBSTRING(sku, 1, 4) = 'PROD'` | Function call on indexed column. | `WHERE sku LIKE 'PROD%'` |
| `WHERE account_num = 12345` *(col is VARCHAR)* | Implicit type conversion forces engine to cast every row. | `WHERE account_num = '12345'` (Match data types strictly) |
| `WHERE status <> 'ARCHIVED'` | Negative operators (`!=`, `<>`) cannot use B-tree seeks. | `WHERE status IN ('ACTIVE', 'PENDING', 'DRAFT')` |
| `WHERE name LIKE '%john%'` | Leading wildcard forces complete table scan. | Use full-text search (PostgreSQL `tsvector`/GIN, SQL Server Full-Text, or trigram index). |

---

## 3. Reading Execution Plans via `explain_query`

Use `explain_query` via MCP to inspect the execution strategy. Watch for these red flags:

### Red Flags to Eliminate:
1. **`Seq Scan` / `Table Scan` on Large Tables**: Indicates missing index or non-sargable predicate. Replace with `Index Scan` or `Index Seek`.
2. **`Sort Method: external merge Disk` / `Spill to TempDB`**: The query sorting requires more memory than `work_mem` (Postgres) or SQL Server workspace buffer. Fix: Add index matching `ORDER BY` or increase sorting memory.
3. **Severe Estimated vs. Actual Row Discrepancy**: Indicates stale statistics. Run `ANALYZE table_name;` (Postgres/SQLite) or `UPDATE STATISTICS table_name;` (SQL Server).
4. **Nested Loop with High Outer Row Count**: In Postgres/Oracle, if a nested loop join executes $1,000,000$ iterations, verify if an index on the inner join column is missing or if statistics should trigger a `Hash Join`.

### Diagnostic Commands per Engine
- **PostgreSQL**: `EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) <query>`
- **SQL Server**: `SET SHOWPLAN_ALL ON; <query>; SET SHOWPLAN_ALL OFF;`
- **Oracle**: `EXPLAIN PLAN FOR <query>` followed by `SELECT * FROM TABLE(DBMS_XPLAN.DISPLAY());`
- **SQLite**: `EXPLAIN QUERY PLAN <query>`
- **MySQL**: `EXPLAIN FORMAT=JSON <query>`
- **MongoDB**: Append `.explain("executionStats")` to aggregation/find

---

## 4. Specialized Index Architecture Deep Dive

For advanced index types (PostgreSQL GIN for JSONB and `pg_trgm` wildcard search, GiST exclusion constraints, and BRIN time-series indexing), consult:
- **[PostgreSQL Specialized Indexing Guide](file:///.github/skills/sql-executor/indexing-and-tuning/postgres-specialized-indexes.md)**

