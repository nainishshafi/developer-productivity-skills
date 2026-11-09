# Query Optimization Reference Guide

An architectural and practitioner handbook for diagnosing, tuning, and eliminating bottlenecks in relational database queries across PostgreSQL, Microsoft SQL Server, Oracle Database, MySQL, and SQLite.

---

## 1. Relational Engine Execution & Optimizer Mechanics

Modern relational databases utilize **Cost-Based Optimizers (CBO)** to translate declarative SQL into an imperative physical execution tree:

```
[SQL Query Text]
       │
       ▼
[Parser & Lexer] ─────────────► AST (Abstract Syntax Tree)
       │
       ▼
[Query Rewriter / Binder] ────► Resolves catalog metadata, views, and semantic rules
       │
       ▼
[Cost-Based Optimizer (CBO)] ─► Enumerates candidate plans; estimates I/O and CPU cost
       │
       ▼
[Execution Engine] ───────────► Volcano Iterator Model (Open -> Next -> Close)
```

### The Cost Model (I/O vs. CPU)
The optimizer estimates the total query cost as:

$$\text{Total Cost} = (\text{Page Fetches} \times \text{Page Cost}) + (\text{Tuples Evaluated} \times \text{CPU Operator Cost})$$

- **Sequential Access (`seq_page_cost`)**: Typically benchmarked at $1.0$. Reading contiguous pages sequentially from storage buffers.
- **Random Access (`random_page_cost`)**: Benchmarked at $1.1\text{--}4.0$ depending on storage (NVMe SSD vs spinning rust). Unindexed seeks or heap lookups perform random I/O.
- **Goal of Query Optimization**: Minimize high-cost random page fetches, reduce total logical reads from the buffer pool, and prevent memory spills to disk (`tempdb` / temporary files).

---

## 2. Physical Join Algorithms & Operator Selection

Understanding how the engine physically executes a join is essential for interpreting execution plans and applying targeted tuning.

| Join Algorithm | Algorithmic Complexity | Best Suited For | Critical Vulnerability / Failure Mode |
|:---|:---|:---|:---|
| **Nested Loops Join** | $O(M \times \log N)$ (with indexed inner table) | One small outer set ($M < 100$) joining to an indexed inner table ($N$). | **Loop Thrashing**: If the outer set is underestimated (e.g. 100,000 rows instead of 10), the engine loops 100,000 times seeking the index, causing massive CPU spin. |
| **Hash Join** | $O(M + N)$ | Large, unsorted sets joined on equality predicates (`=`). | **Hash Spills to Disk**: The smaller table is hashed into RAM (Build phase). If memory grant is exceeded, hash buckets spill to `tempdb`/disk, degrading throughput by $10\text{x}\text{--}100\text{x}$. |
| **Merge Join** | $O(M + N)$ (if presorted)<br>$O(M \log M + N \log N)$ (with sort) | Both inputs are already sorted by the join keys (e.g., via clustered index or B-tree). | **Expensive Sort Nodes**: If inputs are not pre-sorted by an index, the engine must inject explicit `Sort` operations before merging. |

### Join Optimization Rules:
1. **Never force physical join hints** (`LOOP`, `HASH`, `MERGE`) unless table statistics are verified accurate and the optimizer consistently picks a degraded path due to plan cache parameter sniffing.
2. **Eliminate Accidental Cartesian Products**: Missing join predicates produce Cartesian Cross Joins ($O(M \times N)$).
3. **Correlate with `APPLY` / `LATERAL`**: Use `CROSS APPLY` (SQL Server) or `LATERAL` (Postgres/Oracle) to push outer predicates directly into dependent table expressions, avoiding large intermediate Cartesian joins.

---

## 3. Sargability & Predicate Optimization Catalog

A predicate is **sargable** (Search Argument Able) when the B-tree index can navigate directly from root to leaf via key comparison ($O(\log N)$). Applying any transformation to an indexed column invalidates direct index seek navigation.

| Category | Non-Sargable Anti-Pattern ($O(N)$ Scan) | Optimized Sargable Rewrite ($O(\log N)$ Seek) | Explanation |
|:---|:---|:---|:---|
| **Date Truncation** | `WHERE DATE(created_at) = '2026-03-15'` | `WHERE created_at >= '2026-03-15' AND created_at < '2026-03-16'` | Date functions strip index seekability. Range comparisons preserve B-tree bounds. |
| **Year / Month** | `WHERE YEAR(order_date) = 2026` | `WHERE order_date >= '2026-01-01' AND order_date < '2027-01-01'` | Preserves boundary seeks across the year range. |
| **Arithmetic** | `WHERE total_amount + 50 > 500` | `WHERE total_amount > 450` | Algebraically isolate the column on one side of the operator. |
| **Case Conversion** | `WHERE LOWER(username) = 'admin'` | Store normalized lowercase or use functional index: `CREATE INDEX idx_user_lower ON users (LOWER(username));` | Engine must evaluate `LOWER()` on every row unless indexed with expression. |
| **Substrings** | `WHERE SUBSTRING(sku, 1, 4) = 'PROD'` | `WHERE sku LIKE 'PROD%'` | Prefix wildcards allow B-tree index seeks. |
| **Leading Wildcards** | `WHERE email LIKE '%@gmail.com'` | Reverse string index (`REVERSE(email) LIKE REVERSE('@gmail.com')%`) or GIN trigram index | B-trees cannot seek on leading wildcards. |
| **Type Conversion** | `WHERE varchar_col = 12345` | `WHERE varchar_col = '12345'` | Number-to-string precedence forces engine to cast every row in `varchar_col` to `INT`. |
| **Collation Mismatch** | `WHERE c.name COLLATE Latin1_General_CS_AS = 'John'` | Align table/database collations or use matching indexed collation | Collation conversion forces scalar evaluation. |
| **Null Coalescing** | `WHERE COALESCE(status, 'NEW') = 'NEW'` | `WHERE status = 'NEW' OR status IS NULL` *(or filtered index)* | `COALESCE` disables index seek on `status`. |
| **Inequality / Negation** | `WHERE status <> 'CANCELLED'` | `WHERE status IN ('PENDING', 'PROCESSING', 'DELIVERED')` | B-tree cannot establish seek boundaries for inequality. |

---

## 4. Indexing Architectures & Access Path Strategies

### A. The Composite Index Column Sequence Formula
When designing multi-column composite B-tree indexes, strictly order columns according to predicate selectivity:

$$\boxed{\text{Index Columns: } [ \text{Equality Predicates } (=) ] \longrightarrow [ \text{Range / Inequality } (<, >, \text{BETWEEN}) ] \longrightarrow [ \text{ORDER BY Sort Columns} ]}$$

- **Why Equality First**: Equality predicates narrow the B-tree search path to a single branch.
- **Why Range Second**: Once a range predicate is traversed, all subsequent index columns can no longer be used for seeks—they can only be used for index filtering.
- **Why Sort Last**: Matching the `ORDER BY` direction allows the index B-tree sequence to fulfill the sort with **zero CPU sorting memory**.

### B. Covering Indexes & Index-Only Scans
When a query requests columns not present in the index key, the engine performs a **Heap / Bookmark Lookup** (Clustered Index seek) for every matching leaf node. If $10,000$ rows match, that is $10,000$ random I/O seeks!

```sql
-- Solution: Add projected columns into the INCLUDE leaf payload:
-- PostgreSQL & SQL Server:
CREATE INDEX idx_orders_customer_date 
ON orders (customer_id, order_date) 
INCLUDE (total_amount, status);

-- Result: Index-Only Scan. Zero random I/O lookups to table heap.
SELECT total_amount, status 
FROM orders 
WHERE customer_id = 9128 AND order_date >= '2026-01-01';
```

### C. Filtered / Partial Indexes
For tables where $90\%$ of rows represent inactive, archived, or processed states, indexing the entire table wastes RAM and disk:

```sql
-- PostgreSQL:
CREATE INDEX idx_unprocessed_jobs ON queue_jobs (created_at) WHERE status = 'PENDING';

-- SQL Server:
CREATE NONCLUSTERED INDEX idx_active_subscriptions ON subscriptions (user_id) WHERE is_active = 1;
```

---

## 5. Subqueries & Set Operations Optimization

### A. Semi-Joins: `EXISTS` vs. `IN` vs. `SELECT DISTINCT`
When checking for existence in parent-child relationships:

```sql
-- ❌ Antipattern 1: Joins parent to child, creates duplicate parent rows, then deduplicates via sort/hash:
SELECT DISTINCT c.id, c.name
FROM customers c
INNER JOIN orders o ON c.id = o.customer_id
WHERE o.order_date >= '2026-01-01';

-- ❌ Antipattern 2: IN with subquery (prone to NULL-trap and materialization bloat):
SELECT c.id, c.name FROM customers c
WHERE c.id IN (SELECT o.customer_id FROM orders o WHERE o.order_date >= '2026-01-01');

-- ✅ Optimal: Short-circuiting EXISTS semi-join:
SELECT c.id, c.name FROM customers c
WHERE EXISTS (
    SELECT 1 FROM orders o
    WHERE o.customer_id = c.id AND o.order_date >= '2026-01-01'
);
```

### B. The `NOT IN` Null Trap vs. `NOT EXISTS`
If a subquery evaluated by `NOT IN` contains even a single `NULL` value, the entire predicate evaluates to `UNKNOWN` / `FALSE`, returning **0 rows**:

```sql
-- ❌ DANGEROUS: If any order has customer_id IS NULL, this returns ZERO rows:
SELECT id FROM customers WHERE id NOT IN (SELECT customer_id FROM orders);

-- ✅ SAFE & FAST: NOT EXISTS handles nullability correctly and leverages Anti-Semi-Join:
SELECT c.id FROM customers c
WHERE NOT EXISTS (
    SELECT 1 FROM orders o WHERE o.customer_id = c.id
);
```

### C. `UNION ALL` vs. `UNION`
- `UNION ALL` streams records concurrently with constant $O(1)$ memory.
- `UNION` forces a sort or hash table deduplication step across the entire combined dataset ($O(N \log N)$), causing severe memory pressure and TempDB spills on large sets.

---

## 6. Pagination & High-Volume Data Streaming

### The Deep `OFFSET` Degradation Problem
```sql
-- ❌ O(N) Degradation:
-- Paging page 4,000 (rows 100,000 to 100,025) requires reading 100,025 rows and discarding 100,000!
SELECT id, title, created_at FROM events
ORDER BY created_at DESC, id DESC
OFFSET 100000 ROWS FETCH NEXT 25 ROWS ONLY;
```

### Optimal Solution: Keyset / Cursor Pagination ($O(1)$)
Seek directly to the exact B-tree key coordinates of the last observed tuple:

```sql
-- ✅ Constant O(1) B-tree Seek:
SELECT id, title, created_at FROM events
WHERE (created_at < :last_seen_created_at)
   OR (created_at = :last_seen_created_at AND id < :last_seen_id)
ORDER BY created_at DESC, id DESC
FETCH FIRST 25 ROWS ONLY;
```

### The Deferred Join Pattern
If keyset pagination is not possible (e.g. user must jump to arbitrary page numbers), use a **Deferred Join** to paginate only the small indexed primary key first, then join back to fetch heavy payload columns:

```sql
-- ✅ Reads 100,025 integers from index, not full wide table rows:
SELECT e.id, e.title, e.payload_json, e.created_at
FROM events e
INNER JOIN (
    SELECT id FROM events
    ORDER BY created_at DESC
    OFFSET 100000 ROWS FETCH NEXT 25 ROWS ONLY
) AS page ON e.id = page.id
ORDER BY e.created_at DESC;
```

---

## 7. Aggregations, Window Functions & Analytics Tuning

### A. Filter Pushdown (`WHERE` vs. `HAVING`)
- `WHERE` filters rows **before** aggregation, reducing the volume of data stored in hash aggregation tables.
- `HAVING` filters rows **after** aggregation, wasting CPU computing groups that are immediately discarded.

```sql
-- ❌ Suboptimal:
SELECT department_id, COUNT(*) FROM employees
GROUP BY department_id HAVING department_id IN (10, 20, 30);

-- ✅ Optimal:
SELECT department_id, COUNT(*) FROM employees
WHERE department_id IN (10, 20, 30) GROUP BY department_id;
```

### B. Window Framing: `ROWS` vs. `RANGE`
By default, SQL standard window functions use:
`RANGE BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW`

`RANGE` requires the engine to inspect peer values to check for duplicates, spooling rows to memory or disk. Explicitly changing this to `ROWS` avoids peer spooling:

```sql
-- ✅ Explicit physical row framing:
SUM(amount) OVER (
    PARTITION BY account_id 
    ORDER BY transaction_date 
    ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
)
```

### C. Fast Metadata Row Count Estimation
Never run `SELECT COUNT(*)` on multi-million row tables just to display an approximate record count:

| Engine | Exact $O(N)$ Scan (Slow) | Approximate $O(1)$ Metadata Count (Instant) |
|:---|:---|:---|
| **PostgreSQL** | `SELECT COUNT(*) FROM orders;` | `SELECT reltuples::BIGINT FROM pg_class WHERE relname = 'orders';` |
| **SQL Server** | `SELECT COUNT(*) FROM dbo.Orders;` | `SELECT SUM(rows) FROM sys.partitions WHERE object_id = OBJECT_ID('dbo.Orders') AND index_id IN (0, 1);` |
| **Oracle** | `SELECT COUNT(*) FROM orders;` | `SELECT num_rows FROM all_tables WHERE table_name = 'ORDERS';` |
| **MySQL** | `SELECT COUNT(*) FROM orders;` | `SELECT table_rows FROM information_schema.tables WHERE table_name = 'orders';` |

---

## 8. Cross-Engine Execution Plan Profiling Playbook

```
┌─────────────────────────────────┐
│ 1. Run Engine Diagnostic Tool   │ ──► PostgreSQL: EXPLAIN (ANALYZE, BUFFERS) | SQL Server: SET STATISTICS IO ON
└────────────────┬────────────────┘
                 │
                 ▼
┌─────────────────────────────────┐
│ 2. Check Logical vs Physical    │ ──► High logical reads indicates missing covering index or poor filtering
└────────────────┬────────────────┘
                 │
                 ▼
┌─────────────────────────────────┐
│ 3. Check Estimated vs Actual    │ ──► Large divergence indicates stale statistics or parameter sniffing
└────────────────┬────────────────┘
                 │
                 ▼
┌─────────────────────────────────┐
│ 4. Check "Rows Removed by Filter"│ ──► Incomplete index; add filter column to composite index
└────────────────┬────────────────┘
                 │
                 ▼
┌─────────────────────────────────┐
│ 5. Check Memory Spills / TempDB │ ──► Hash/Sort exceeded memory grant; add index matching ORDER BY or bump work_mem
└─────────────────────────────────┘
```

### Engine Diagnostic Commands:

#### 1. PostgreSQL: `EXPLAIN (ANALYZE, BUFFERS, VERBOSE, SETTINGS)`
- Look for `Buffers: shared hit=... read=...` (logical reads vs disk reads).
- Look for `Rows Removed by Filter: 120000` (index missed secondary predicates).
- Look for `Sort Method: external merge Disk: 4520kB` (work_mem spill).

#### 2. SQL Server: `SET STATISTICS IO, TIME ON;`
- Look for `Scan count N, logical reads M`.
- Look for `Spill to tempdb` in XML graphical execution plans.
- Compare `CPU time` vs `elapsed time` (CPU > Elapsed indicates parallelism; Elapsed >> CPU indicates waiting on disk `PAGEIOLATCH_SH` or blocking).

#### 3. Oracle Database: `DBMS_XPLAN.DISPLAY_CURSOR`
```sql
SELECT /*+ GATHER_PLAN_STATISTICS */ * FROM orders WHERE status = 'PENDING';
SELECT * FROM TABLE(DBMS_XPLAN.DISPLAY_CURSOR(format => 'ALLSTATS LAST'));
```
- Inspect `A-Rows` (Actual Rows) vs `E-Rows` (Estimated Rows).
- Check `OMem` and `1Mem` for memory sizing and disk spills.

#### 4. MySQL: `EXPLAIN ANALYZE`
```sql
EXPLAIN ANALYZE SELECT * FROM orders WHERE customer_id = 42;
```
- Check actual execution time per node and loop counts.

#### 5. SQLite: `EXPLAIN QUERY PLAN`
```sql
EXPLAIN QUERY PLAN SELECT * FROM orders WHERE customer_id = 42;
```
- Verify `SEARCH TABLE ... USING INDEX` (seek) vs `SCAN TABLE` (scan).

---

## 9. References & Deep Dive Guides

- [Multi-Engine Joins Architecture](file:///.github/skills/sql-executor/joins/multi-engine-joins.md) — Detailed join syntax, `APPLY`, `LATERAL`, and dialect quirks.
- [Indexing & Performance Tuning](file:///.github/skills/sql-executor/indexing-and-tuning/indexing-and-performance-tuning.md) — B-trees, cardinality estimation, and execution statistics.
- [PostgreSQL Specialized Indexing](file:///.github/skills/sql-executor/indexing-and-tuning/postgres-specialized-indexes.md) — GIN (`jsonb`, `pg_trgm`), GiST, and BRIN time-series indexing.
- [Temporary Structures, CTEs & #TempTables](file:///.github/skills/sql-executor/temporary-tables-and-ctes/temp-tables-and-ctes.md) — Chained CTEs vs `#TempTable` optimizer tradeoffs.
- [SQL Connector MCP Server](file:///.github/skills/sql-connector/SKILL.md) — Safely executing and auditing SQL queries with automated firewall protection.
