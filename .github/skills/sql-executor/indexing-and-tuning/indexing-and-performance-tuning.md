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

## 3. Performance Statistics & Metrics to Look For Across Engines

When analyzing execution performance, do not rely solely on clock execution time (which fluctuates based on concurrent server load). Focus on these hardware and engine-level metrics:

### A. I/O & Memory Metrics: Logical vs. Physical Reads
Every database engine retrieves data in disk/memory pages (8 KB in SQL Server/Postgres, 8 KB or 16 KB in Oracle):

| Metric | Meaning | What to Look For | How to Improve |
|:---|:---|:---|:---|
| **Logical Reads** (`shared hit`) | 8 KB pages retrieved from in-memory Buffer Cache | Primary metric for query workload! A query retrieving 10 rows should not perform 200,000 logical reads. | Add covering index (`INCLUDE`) or tighten filter predicates. |
| **Physical Reads** (`shared read`) | 8 KB pages read from physical SSD/NVMe disk | If high, indicates cold cache, buffer pool thrashing, or massive table scan. | Increase database buffer cache memory; eliminate unindexed scans. |
| **Rows Removed by Filter** (Postgres) | Rows read from disk/cache and discarded by secondary filter | High count indicates the index filtered by some columns, but engine had to scan and reject rows in post-processing. | Add the discarded filter column to the composite index. |
| **Spill to Disk / TempDB** | Query sort, hash join, or aggregation exceeded assigned memory grant | Look for `Worktable`, `Spill to TempDB`, or `Sort Method: external merge Disk`. | Increase session memory (`work_mem` in Postgres), or add index matching `ORDER BY`. |

---

### B. Diagnostic Commands & Instrumentation

#### PostgreSQL: `EXPLAIN (ANALYZE, BUFFERS)`
```sql
EXPLAIN (ANALYZE, BUFFERS, VERBOSE, SETTINGS)
SELECT c.name, o.total_amount
FROM customers c
INNER JOIN orders o ON c.id = o.customer_id
WHERE o.order_date >= '2026-01-01' AND c.status = 'ACTIVE';

-- KEY METRICS IN OUTPUT:
-- 1. "Buffers: shared hit=845 read=12" -> 845 pages from RAM, 12 from disk (98.6% cache hit).
-- 2. "Rows Removed by Filter: 48920"  -> Index was incomplete; 48k rows were evaluated and thrown away!
-- 3. "Planning Time: 0.2ms, Execution Time: 4.8ms"
```

#### SQL Server: `SET STATISTICS IO, TIME ON`
```sql
SET STATISTICS IO ON;
SET STATISTICS TIME ON;

SELECT CustomerID, OrderDate, TotalAmount
FROM dbo.Orders
WHERE OrderDate >= '2026-01-01';

-- OUTPUT WINDOW METRICS:
-- Table 'Orders'. Scan count 1, logical reads 1420, physical reads 0, read-ahead reads 0.
-- SQL Server Execution Times: CPU time = 15 ms, elapsed time = 18 ms.
```
> [!TIP]
> **CPU Time vs. Elapsed Time Heuristic**:
> - **$\text{CPU Time} > \text{Elapsed Time}$**: Query ran in parallel across multiple CPU cores.
> - **$\text{Elapsed Time} \gg \text{CPU Time}$**: Query spent majority of time waiting on external resources (disk I/O `PAGEIOLATCH_SH`, network transmission `ASYNC_NETWORK_IO`, or lock blocking `LCK_M_*`).

#### Oracle: `AUTOTRACE` & `V$SQL`
```sql
-- In SQL*Plus / SQLcl:
SET AUTOTRACE ON STATISTICS;

-- Key Metrics:
-- "consistent gets" = Logical reads from buffer cache.
-- "physical reads"   = I/O blocks fetched from disk.
-- "redo size"        = Transaction log volume generated.
```

---

## 4. Optimizer Statistics, Histograms & Cardinality Estimation

Database Cost-Based Optimizers (CBO) rely on **column statistics and histograms** to estimate how many rows a query will return. When statistics become stale or missing, query plans collapse:

### A. The Consequences of Bad Cardinality Estimates
1. **Severe Underestimation (Engine expects 1 row, but receives 1,000,000)**:
   - Optimizer chooses **Nested Loops** join (suitable for 1 row).
   - Loops 1,000,000 times executing random index seeks $\to$ Massive CPU spin and hours of query locking!
2. **Severe Overestimation (Engine expects 1,000,000 rows, but receives 10)**:
   - Optimizer requests a massive **Memory Grant** (e.g. 16 GB RAM for sorting/hash tables).
   - High-concurrency queries queue behind each other waiting for RAM (`RESOURCE_SEMAPHORE` waits in SQL Server), causing artificial system-wide timeouts.
3. **The Ascending Key Problem**:
   - In auto-incrementing IDs or date columns (`order_id`, `created_at`), new data is inserted past the highest value recorded in the last statistics histogram.
   - For any query targeting `created_at >= TODAY`, the optimizer assumes **0 or 1 row** exists!

---

### B. Updating Statistics & Restoring Cardinality

| Engine | Update Command | Recommended Heuristic |
|:---|:---|:---|
| **PostgreSQL** | `ANALYZE table_name;` | Run after large batch inserts/deletes. Increase sampling resolution via `ALTER TABLE t ALTER col SET STATISTICS 1000;`. |
| **SQL Server** | `UPDATE STATISTICS dbo.Orders WITH FULLSCAN;` | `FULLSCAN` calculates exact distributions without sample estimation errors. |
| **Oracle** | `DBMS_STATS.GATHER_TABLE_STATS('SCOTT', 'ORDERS', estimate_percent => DBMS_STATS.AUTO_SAMPLE_SIZE);` | Uses Oracle HyperLogLog auto-sampling for fast, exact stats gathering. |
| **SQLite** | `ANALYZE;` | Populates `sqlite_stat1` and `sqlite_stat4` tables for index selection. |

---

## 5. Step-by-Step Performance Improvement Playbook

Follow this 5-step systematic workflow to optimize any slow query:

```
[1. Identify High Logical Reads] ──> [2. Fix Cardinality Mismatch] ──> [3. Eliminate Filter Waste]
                 │                                                                   │
                 ▼                                                                   ▼
[5. Memory Spill & Worktable Prevention] <──────────── [4. Enforce Sargable Index Seeks]
```

### Step 1: Benchmark Baseline Logical Reads
Run `EXPLAIN (ANALYZE, BUFFERS)` or `SET STATISTICS IO ON`. Record the baseline:
- Total logical page reads.
- Execution time (ms).
- Physical reads (disk fetches).

### Step 2: Compare Estimated vs. Actual Rows
Inspect the execution plan node by node:
- If node shows: `Rows Estimated: 1` vs `Rows Actual: 85,000`:
  - Update table statistics (`UPDATE STATISTICS` / `ANALYZE`).
  - If a multi-statement table-valued function (mTVF) or table variable caused the estimate, convert to an Inline TVF (iTVF) or `#TempTable`.

### Step 3: Eliminate "Rows Removed by Filter"
Check if an Index Scan read 100,000 rows only to discard 99,000 with a secondary filter:
- Add the discarded predicate columns into the composite index following the **[Equality] $\to$ [Range] $\to$ [Include]** rule.

### Step 4: Convert Scans into Seeks (Sargability)
Search the plan for `Seq Scan` (Postgres) or `Clustered Index Scan` (SQL Server):
- Check WHERE clause for non-sargable functions (`LOWER(col)`, `YEAR(col)`, type mismatches).
- Refactor predicates to bare column comparisons against constant literals.

### Step 5: Prevent Memory Spills
If the plan displays `Sort Method: external merge Disk` or `TempDB Spills`:
- If query requires `ORDER BY`, add the sort columns to the index definition to allow the index B-tree order to satisfy the query with zero in-memory sorting.
- If unavoidable, increase local query memory (`SET work_mem = '64MB';` in Postgres).

---

## 6. Specialized Index Architecture Deep Dive

For advanced index types (PostgreSQL GIN for JSONB and `pg_trgm` wildcard search, GiST exclusion constraints, and BRIN time-series indexing), consult:
- **[PostgreSQL Specialized Indexing Guide](file:///.github/skills/sql-executor/indexing-and-tuning/postgres-specialized-indexes.md)**

