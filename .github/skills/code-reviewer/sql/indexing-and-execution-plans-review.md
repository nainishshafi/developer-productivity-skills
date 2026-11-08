# SQL Indexing & Execution Plans Review Guide

Audit guide for query performance, execution plan analysis, index selection, and SARGability, cross-referencing [`sql-executor`](file:///.github/skills/sql-executor/SKILL.md).

---

## 1. Execution Plan Inspection (`explain_query`)

- [ ] **Full Table Scans ($O(N)$)**:
  - Does the execution plan show `Table Scan` (SQL Server), `Seq Scan` (PostgreSQL), or `TABLE ACCESS FULL` (Oracle) on large tables (> 10,000 rows)?
  - Flag unindexed large table scans on hot queries as `[P1 - Major]`.
- [ ] **Index Seek vs. Index Scan**:
  - Does the plan perform an `Index Seek` (traversing the B-Tree directly, $O(\log N)$) rather than an `Index Scan` (scanning the entire index leaves, $O(N)$)?
- [ ] **Estimated vs. Actual Row Discrepancy**:
  - Is there a $10\times$ or greater difference between estimated rows and actual rows?
  - This indicates stale table statistics. Advise running `UPDATE STATISTICS` (SQL Server), `ANALYZE` (PostgreSQL), or `DBMS_STATS.GATHER_TABLE_STATS` (Oracle).

---

## 2. SARGability (Search Argument Ability)

- [ ] **Functions on Indexed Columns in `WHERE` Clauses**:
  - Are columns wrapped in scalar functions, preventing index seeks?
  ```sql
  -- BAD: Non-SARGable; forces full table scan
  WHERE UPPER(email) = 'USER@EXAMPLE.COM'
  WHERE YEAR(created_at) = 2026
  WHERE SUBSTRING(phone, 1, 3) = '415'

  -- GOOD: SARGable ranges or expression indexes
  WHERE email = 'user@example.com'  -- (with case-insensitive collation or functional index)
  WHERE created_at >= '2026-01-01' AND created_at < '2027-01-01'
  WHERE phone LIKE '415%'
  ```
- [ ] **Implicit Type Conversion**:
  - Does the query compare a `VARCHAR` column to an `NVARCHAR` parameter (or integer to string)?
  - Implicit type conversion forces the database engine to cast every row, disqualifying index usage.
- [ ] **Leading Wildcards in `LIKE`**:
  - Is `LIKE '%pattern'` used? Leading wildcards cannot use standard B-Tree indexes.
  - **Resolution**: Use PostgreSQL `pg_trgm` GIN index or SQL Server Full-Text Search.

---

## 3. Specialized Index Architecture

- [ ] **PostgreSQL GIN / GiST / BRIN**:
  - JSONB, Array, or Full-Text Search columns: Is a **GIN** index (`USING gin(payload)`) used?
  - Geospatial (PostGIS) or range types: Is a **GiST** index used?
  - Append-only time-series or sequential logs: Is a **BRIN** (Block Range) index used to save 99% disk space?
- [ ] **Covering Indexes (`INCLUDE`)**:
  - Does a query frequently look up non-key columns after seeking on an index (Key Lookup / Bookmark Lookup)?
  - **Resolution**: Add non-key columns to the leaf pages using `INCLUDE (colA, colB)` to achieve pure index-only scans.
- [ ] **Composite Index Column Ordering**:
  - Are composite index columns ordered by equality predicates first, followed by range predicates?
  - Rule: `(Equality_Col1, Equality_Col2, Range_Col3)`.

---

## 4. Keyset Pagination vs. `OFFSET / FETCH`

- [ ] **Deep Paging Degradation**:
  - Is `OFFSET 100000 ROWS FETCH NEXT 50 ROWS` used?
  - High offsets scan and discard 100,000 rows ($O(N)$ cost).
  - **Resolution**: Use Keyset (Cursor-based) pagination (`WHERE id > @last_seen_id ORDER BY id ASC LIMIT 50`) which runs in $O(1)$ time via index seek.
