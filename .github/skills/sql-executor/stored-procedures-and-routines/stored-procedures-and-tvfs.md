# Stored Procedures, Functions & Routines Guide

Architectural heuristics and execution patterns for stored procedures, table-valued functions (TVFs), dynamic SQL, and temporary structures across SQL Server, PostgreSQL, and Oracle.

---

## 1. Stored Procedure Invocation Across Dialects

| Engine | Execution Syntax | Output Parameter Pattern | Result Set Return |
|:---|:---|:---|:---|
| **SQL Server** | `EXEC dbo.sp_name @param = $1;` | `@param_out INT OUTPUT` | Direct `SELECT` statement within procedure. |
| **PostgreSQL** | `CALL public.sp_name($1, $2);` | `INOUT param_name type` | Procedures (`CALL`) for transactional control; Functions (`SELECT * FROM fn()`) for result sets. |
| **Oracle** | `BEGIN pkg.sp_name(:p1, :p2); END;` | `param_name OUT type` | Output parameter as `SYS_REFCURSOR`. |
| **MySQL** | `CALL sp_name(?, ?);` | `@user_variable` | Direct `SELECT` within procedure. |

---

## 2. SQL Server: Inline TVFs vs. Multi-Statement TVFs

When authoring modular reusable database logic in Microsoft SQL Server, choosing the wrong function type can cripple execution performance:

### A. Inline Table-Valued Functions (iTVFs) — *PREFERRED*
An iTVF contains a single `RETURN SELECT ...` statement without a `BEGIN ... END` block:

```sql
CREATE FUNCTION dbo.fn_GetActiveCustomerOrders (@CustomerID INT)
RETURNS TABLE
AS
RETURN (
    SELECT 
        o.OrderID, 
        o.OrderDate, 
        o.TotalAmount
    FROM dbo.Orders o
    WHERE o.CustomerID = @CustomerID 
      AND o.Status = 'ACTIVE'
);
```
> [!TIP]
> **Why iTVFs are Superior**: The query optimizer treats an iTVF like a parameterized view. It merges the function's AST directly into the calling query, pushes outer join predicates down, leverages base table indexes, and computes accurate cardinality estimates.

### B. Multi-Statement Table-Valued Functions (mTVFs) — *CAUTION*
An mTVF declares an explicit `@TableVariable TABLE (...)` and populates it iteratively:

```sql
-- ANTI-PATTERN on large datasets:
CREATE FUNCTION dbo.fn_GetCustomerOrdersBad (@CustomerID INT)
RETURNS @Orders TABLE (OrderID INT, OrderDate DATETIME, TotalAmount MONEY)
AS
BEGIN
    INSERT INTO @Orders
    SELECT OrderID, OrderDate, TotalAmount FROM dbo.Orders WHERE CustomerID = @CustomerID;
    RETURN;
END;
```
> [!WARNING]
> Prior to SQL Server 2017 Adaptive Query Processing, the optimizer assumed every mTVF returned exactly **1 row** (or 100 in 2017+), regardless of actual row count. When joined with other tables, this triggers nested loop scans that catastrophically freeze execution on large tables.

---

## 3. Dynamic SQL & Injection Defense

When procedures must assemble queries dynamically (e.g., dynamic search filters), never use raw string concatenation:

### SQL Server: `sp_executesql` with Typed Bindings
```sql
CREATE PROCEDURE dbo.sp_SearchProducts
    @Category VARCHAR(50) = NULL,
    @MinPrice DECIMAL(10,2) = NULL
AS
BEGIN
    SET NOCOUNT ON;
    
    DECLARE @SQL NVARCHAR(MAX) = N'SELECT ProductID, Name, Price FROM dbo.Products WHERE 1=1';
    DECLARE @ParamDef NVARCHAR(500) = N'@pCategory VARCHAR(50), @pMinPrice DECIMAL(10,2)';
    
    IF @Category IS NOT NULL
        SET @SQL += N' AND Category = @pCategory';
        
    IF @MinPrice IS NOT NULL
        SET @SQL += N' AND Price >= @pMinPrice';
        
    -- Parameterized dynamic execution preserves query cache and blocks SQL injection
    EXEC sp_executesql 
        @stmt = @SQL, 
        @params = @ParamDef, 
        @pCategory = @Category, 
        @pMinPrice = @MinPrice;
END;
```

---

## 4. Temporary Tables vs. Table Variables in Stored Procedures

| Feature | `#TemporaryTable` | `@TableVariable` |
|:---|:---|:---|
| **Storage Engine** | TempDB (full disk/buffer pool) | In-memory buffer with TempDB spill |
| **Statistics** | Full column-level histogram statistics | **No statistics** (engine assumes 1 row) |
| **Indexes** | Supports multiple clustered and nonclustered indexes | Primary key and unique constraints only |
| **Parallelism** | Supports parallel execution plans | Serial execution only |
| **Rule of Thumb** | **Use for $> 1,000$ rows** or when joining with other tables | **Use for $< 100$ rows** (simple key lookups) |

---

## 5. PostgreSQL: Stored Procedures vs Functions

- **Functions (`CREATE FUNCTION`)**: Execute within an ambient transaction; cannot issue `COMMIT` or `ROLLBACK`. Best for calculations, triggers, and queryable projections (`SELECT * FROM my_func()`).
- **Procedures (`CREATE PROCEDURE`)**: Introduced in PostgreSQL 11. Can manage autonomous transaction boundaries (`COMMIT` or `ROLLBACK` within the loop body), making them ideal for large-scale data migrations and ETL chunking:

```sql
CREATE OR REPLACE PROCEDURE archive_stale_logs(batch_size INT)
LANGUAGE plpgsql
AS $$
DECLARE
    rows_deleted INT;
BEGIN
    LOOP
        DELETE FROM access_logs 
        WHERE id IN (
            SELECT id FROM access_logs 
            WHERE log_date < CURRENT_DATE - INTERVAL '90 days'
            LIMIT batch_size
        );
        GET DIAGNOSTICS rows_deleted = ROW_COUNT;
        
        COMMIT; -- Commits per batch to prevent long-held locks and WAL bloat
        EXIT WHEN rows_deleted = 0;
    END LOOP;
END;
$$;
```
