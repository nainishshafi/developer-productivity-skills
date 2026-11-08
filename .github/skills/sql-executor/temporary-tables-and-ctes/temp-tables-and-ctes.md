# Temporary Structures & CTEs Architecture Guide

Comprehensive architectural heuristics for Common Table Expressions (`WITH`), Temporary Tables (`#TempTable`, `CREATE TEMP TABLE`), Table Variables (`@TableVariable`), and Global Temporary Tables across SQL Server, PostgreSQL, Oracle, and SQLite.

---

## 1. Structure Selection Decision Matrix

| Mechanism | Scope & Lifespan | Statistics & Cardinality | Indexing Capability | Re-execution Behavior | Best Use Case |
|:---|:---|:---|:---|:---|:---|
| **CTE (`WITH`)** | Single query execution | Inlined; relies on base table stats | **None** | Re-executed for every reference (SQL Server); materializable in Postgres | Decomposing complex queries; recursive hierarchical tree traversals; single-use transformations. |
| **`#TempTable`** | Current session or stored procedure | **Full column histograms & statistics** | Primary Key, Clustered & Nonclustered B-Tree | Materialized once in TempDB | Intermediate storage for $> 1,000$ rows; multi-step data pipelines; breaking complex optimizer plans. |
| **`@TableVariable`** | Batch/procedure variable scope | **No statistics** (engine assumes 1 row in older engines) | Primary Key & Unique constraints only | Materialized in-memory with TempDB spill | Small lookup sets ($< 100$ rows); when rollback independence is explicitly needed. |
| **GTT / PTT (Oracle)** | Transaction or session (`ON COMMIT DELETE/PRESERVE`) | Can gather manual stats | Full B-tree indexes | Materialized in temp tablespace per session | Enterprise PL/SQL ETL pipelines, staging transaction data without redo log overhead. |
| **`CREATE TEMP TABLE` (Postgres)** | Session or transaction (`ON COMMIT DROP`) | Full auto-vacuum & analyze stats | Full B-tree, GIN, GiST, BRIN | Materialized in temp buffers | Session-isolated staging, complex multi-stage ETL scripts. |

---

## 2. Common Table Expressions (`WITH`) & Recursive Patterns

### A. Chained Common Table Expressions
Break monolithic queries into readable, testable logical units:

```sql
WITH CustomerSpend AS (
    SELECT 
        customer_id, 
        COUNT(order_id) AS total_orders, 
        SUM(total_amount) AS lifetime_value
    FROM orders
    WHERE status = 'COMPLETED'
    GROUP BY customer_id
),
HighValueCustomers AS (
    SELECT customer_id, lifetime_value
    FROM CustomerSpend
    WHERE lifetime_value >= 10000
)
SELECT 
    c.id, 
    c.name, 
    c.email, 
    h.lifetime_value
FROM customers c
INNER JOIN HighValueCustomers h ON c.id = h.customer_id
ORDER BY h.lifetime_value DESC;
```

---

### B. Recursive CTEs for Hierarchies, Trees & Sequences
A recursive CTE consists of an **Anchor Member**, a `UNION ALL`, and a **Recursive Member** referencing the CTE itself:

#### 1. Organizational Hierarchy (Manager $\to$ Direct Reports)
```sql
-- Supported in PostgreSQL, SQL Server, Oracle, and SQLite
WITH RECURSIVE EmployeeHierarchy AS (
    -- Anchor Member: Top-level executives (no manager)
    SELECT 
        employee_id, 
        manager_id, 
        full_name, 
        1 AS hierarchy_level,
        CAST(full_name AS VARCHAR(1000)) AS reporting_path
    FROM employees
    WHERE manager_id IS NULL
    
    UNION ALL
    
    -- Recursive Member: Subordinates joining to parent anchor
    SELECT 
        e.employee_id, 
        e.manager_id, 
        e.full_name, 
        eh.hierarchy_level + 1,
        CAST(eh.reporting_path || ' -> ' || e.full_name AS VARCHAR(1000))
    FROM employees e
    INNER JOIN EmployeeHierarchy eh ON e.manager_id = eh.employee_id
)
SELECT * FROM EmployeeHierarchy 
ORDER BY reporting_path;
```

#### 2. Generating Continuous Date Ranges (Zero Gaps)
```sql
-- PostgreSQL / SQLite date series generator:
WITH RECURSIVE DateRange AS (
    SELECT DATE '2026-01-01' AS calendar_date
    UNION ALL
    SELECT calendar_date + INTERVAL '1 day'
    FROM DateRange
    WHERE calendar_date < DATE '2026-01-31'
)
SELECT d.calendar_date, COALESCE(SUM(o.amount), 0) AS daily_revenue
FROM DateRange d
LEFT JOIN orders o ON DATE(o.created_at) = d.calendar_date
GROUP BY d.calendar_date
ORDER BY d.calendar_date;
```

---

### C. CTE Materialization Controls & Traps

#### The SQL Server Multiple-Reference Trap
In Microsoft SQL Server, if a CTE is referenced three times in a query (e.g., via multiple joins or `UNION`), the SQL Server query optimizer **re-executes the CTE definition three separate times**.
> [!WARNING]
> **Heuristic**: In SQL Server, if a complex or expensive CTE is referenced more than once in the same query, materialize it into a `#TempTable` first.

#### PostgreSQL Materialization Directives (`MATERIALIZED` vs `NOT MATERIALIZED`)
PostgreSQL 12+ defaults to inlining CTEs unless they are recursive or have side-effects:

```sql
-- FORCE MATERIALIZATION (Optimization Fence):
-- Evaluates the CTE exactly once, stores it in temp memory, and shares it across joins:
WITH ExpensiveAgg AS MATERIALIZED (
    SELECT department_id, AVG(salary) AS avg_sal, COUNT(*) AS emp_count
    FROM employees
    GROUP BY department_id
)
SELECT * FROM ExpensiveAgg e1
JOIN ExpensiveAgg e2 ON e1.avg_sal > e2.avg_sal;

-- PREVENT MATERIALIZATION (Inline into outer query for predicate pushdown):
WITH RecentOrders AS NOT MATERIALIZED (
    SELECT * FROM orders WHERE status = 'SHIPPED'
)
SELECT * FROM RecentOrders WHERE customer_id = 42; 
-- Pushes 'customer_id = 42' directly into the base orders table index seek!
```

---

## 3. `#TempTable` Best Practices (SQL Server & Beyond)

Temporary tables (`#TempTable`) are physical tables created in `TempDB`. They support full indexing, dynamic statistics, and parallel query execution.

### Optimal `#TempTable` Workflow
```sql
-- 1. Create temporary table with explicit types and Primary Key
CREATE TABLE #StagingOrders (
    OrderID INT NOT NULL,
    CustomerID INT NOT NULL,
    TotalAmount DECIMAL(12, 2) NOT NULL,
    OrderDate DATETIME2 NOT NULL,
    PRIMARY KEY CLUSTERED (OrderID)
);

-- 2. Populate via bulk insert
INSERT INTO #StagingOrders (OrderID, CustomerID, TotalAmount, OrderDate)
SELECT OrderID, CustomerID, TotalAmount, OrderDate
FROM dbo.Orders
WHERE OrderDate >= '2026-01-01';

-- 3. Add secondary nonclustered index for subsequent join queries
CREATE NONCLUSTERED INDEX idx_staging_customer 
ON #StagingOrders (CustomerID) 
INCLUDE (TotalAmount);

-- 4. Execute complex multi-table query with accurate statistics
SELECT 
    c.CustomerName, 
    s.TotalAmount
FROM dbo.Customers c
INNER JOIN #StagingOrders s ON c.CustomerID = s.CustomerID;

-- 5. Explicitly drop to free TempDB buffers promptly
DROP TABLE #StagingOrders;
```

### Minimizing TempDB Allocation Latches
In high-concurrency environments, rapid `CREATE TABLE #temp` / `DROP TABLE #temp` in loops causes severe latch contention on TempDB allocation pages (PFS, GAM, SGAM).
- **Rule 1**: Reuse the temporary table inside loops by using `TRUNCATE TABLE #temp` instead of dropping and recreating.
- **Rule 2**: For stored procedures executed thousands of times per minute, prefer `@TableVariable` if row counts are small ($< 100$).

---

## 4. Table Variables (`@TableVariable`) Nuances

```sql
DECLARE @TargetIDs TABLE (
    ID INT PRIMARY KEY CLUSTERED
);

INSERT INTO @TargetIDs (ID) VALUES (101), (102), (103);

SELECT p.* 
FROM dbo.Products p
INNER JOIN @TargetIDs t ON p.ProductID = t.ID;
```

### Critical Differences:
1. **Transaction Rollback Immunity**: If an active transaction issues `ROLLBACK`, changes made to `@TableVariable` **do not roll back**. They retain their values!
2. **Cardinality Assumption**: Without trace flags or SQL Server 2019+ Table Variable Deferred Compilation, the optimizer estimates `@TableVariable` has **1 row**. If it actually holds 500,000 rows, the engine selects a Nested Loops join instead of a Hash Join, causing massive CPU spikes.

---

## 5. PostgreSQL & Oracle Temporary Tables

### PostgreSQL Temporary Tables
```sql
CREATE TEMP TABLE temp_extracted_customers (
    customer_id INT PRIMARY KEY,
    risk_score NUMERIC(5,2)
) ON COMMIT DROP; -- Automatically dropped at transaction boundary
```

### Oracle Global Temporary Tables (GTT)
In Oracle, DDL for temporary tables is static (defined once in the schema); data rows are private to the session/transaction:
```sql
CREATE GLOBAL TEMPORARY TABLE gtt_invoice_buffer (
    invoice_id NUMBER PRIMARY KEY,
    amount NUMBER(12, 2)
) ON COMMIT PRESERVE ROWS; -- Rows retained across commits for the duration of the session
```
*(In Oracle 18c+, Private Temporary Tables `CREATE PRIVATE TEMPORARY TABLE ORA$PTT_...` can also be created dynamically with session/transaction drop semantics).*
