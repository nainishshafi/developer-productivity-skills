# SQL Routines, TVFs, Cursors & CTEs Review Guide

Audit guide for stored procedures, table-valued functions, Oracle cursors, and temporary storage strategies.

---

## 1. Table-Valued Functions (TVFs)

- [ ] **Inline TVFs vs. Multi-Statement TVFs (mTVFs)**:
  - In SQL Server, is a multi-statement TVF (`RETURNS @t TABLE (...)`) used for queries joined with other tables?
  - mTVFs have historically had a 1-row or 100-row cardinality estimate, causing terrible join choices and nested loop blowups. They also prevent predicate pushdown.
  - **Resolution**: Rewrite as an Inline TVF (`RETURNS TABLE AS RETURN (SELECT ...)`) which the optimizer can inline directly into the parent query tree.

---

## 2. Temporary Storage: CTEs vs. `#temp` Tables vs. Table Variables

- [ ] **CTEs Evaluated Multiple Times**:
  - Is a Common Table Expression (`WITH cte AS (...)`) referenced multiple times in the same query?
  - In SQL Server and Oracle, standard CTEs are inline views that are re-evaluated from scratch each time they are referenced.
  - **Resolution**: Materialize intermediate data into a local temporary table (`#temp_data`) with an index.
- [ ] **Table Variables (`@table`) on Large Datasets**:
  - Are table variables used for sets with > 100 rows?
  - Table variables lack column statistics and distribution histograms, causing poor execution plans. Use `#temp` tables instead.
- [ ] **Recursive CTE Termination**:
  - Do recursive CTEs have a guaranteed base termination condition and `MAXRECURSION` limit to prevent infinite loops?

---

## 3. Cursors & Iterative Row Processing (RBAR)

- [ ] **Row-By-Agonizing-Row (RBAR)**:
  - Is a cursor (`DECLARE cursor_name CURSOR FOR ...`) used where a set-based `UPDATE`, `INSERT`, or window function would work?
  - Set-based SQL is typically $100\times$ faster than row-by-row cursor loops.
- [ ] **Oracle PL/SQL Bulk Operations**:
  - When PL/SQL cursors are strictly necessary, are they using `BULK COLLECT` with a bounded batch size?
  ```sql
  -- BAD: Slow row-by-row context switching
  FOR rec IN c_orders LOOP
    process_order(rec.id);
  END LOOP;

  -- GOOD: Batch fetching with BULK COLLECT LIMIT
  OPEN c_orders;
  LOOP
    FETCH c_orders BULK COLLECT INTO l_orders LIMIT 1000;
    EXIT WHEN l_orders.COUNT = 0;
    FORALL i IN 1..l_orders.COUNT
      UPDATE orders SET status = 'PROCESSED' WHERE id = l_orders(i).id;
  END LOOP;
  CLOSE c_orders;
  ```
- [ ] **Cursor Deallocation**:
  - Are SQL Server cursors explicitly closed and deallocated (`CLOSE cur; DEALLOCATE cur;`)?

