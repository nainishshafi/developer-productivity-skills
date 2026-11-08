# SQL Analytics, Window Functions & Cubing Review Guide

Audit guide for SQL analytic functions, OLAP multidimensional aggregation, and matrix pivoting, cross-referencing [`sql-executor`](file:///.github/skills/sql-executor/SKILL.md).

---

## 1. Window Functions Performance & Partitioning

- [ ] **Frame Specification (`ROWS` vs. `RANGE`)**:
  - When using `ORDER BY` in window functions without specifying a frame, SQL defaults to `RANGE BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW`.
  - `RANGE` writes spool files to `tempdb` and performs duplicate row checks on peer values, degrading performance.
  - **Resolution**: Explicitly specify `ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW` or `ROWS BETWEEN 1 PRECEDING AND CURRENT ROW` for rolling aggregates.
- [ ] **`ROW_NUMBER()` vs. `DENSE_RANK()` vs. `RANK()`**:
  - For top-N deduplication, is `ROW_NUMBER() OVER (PARTITION BY group_id ORDER BY created_at DESC)` used with a filter `WHERE rn = 1`?
  - Does the ordering guarantee determinism (ties broken by primary key)?

---

## 2. Multi-Dimensional OLAP Aggregation (Cubing)

- [ ] **`GROUPING SETS` vs. Multiple `UNION ALL` Queries**:
  - Does code execute multiple queries with `UNION ALL` to aggregate across different grouping levels (e.g. Region + Month, Region alone, Total)?
  - Multiple `UNION ALL` queries rescan the underlying fact table $N$ times.
  - **Resolution**: Use `GROUP BY GROUPING SETS ((region, month), (region), ())` or `ROLLUP` / `CUBE` to aggregate in a single table pass.
- [ ] **Identifying Summary Rows (`GROUPING()` / `GROUPING_ID()` )**:
  - When using `ROLLUP` or `CUBE`, does the query use `GROUPING(column_name)` to differentiate real `NULL` values from super-aggregate subtotal rows?

---

## 3. Matrix Pivoting & Reshaping

- [ ] **Native `PIVOT` vs. Conditional Aggregation**:
  - Is native `PIVOT` or conditional aggregation (`SUM(CASE WHEN category = 'A' THEN amount ELSE 0 END)`) used cleanly?
  - For cross-database portability (PostgreSQL, SQLite, MySQL), conditional aggregation with `CASE` is universally supported without proprietary extensions.

