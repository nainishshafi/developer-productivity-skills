# Window Functions, Table-Valued Functions (TVFs) & Pivoting

Comprehensive architectural reference for analytic window functions, cross-engine Table-Valued Functions (TVFs), pipelined functions, and matrix pivot transformations.

---

## 1. Table-Valued Functions (TVFs) Across Engines

Table-Valued Functions return a set of rows rather than a scalar value, acting as parameterized virtual tables:

### A. SQL Server: Inline TVF with `CROSS APPLY`
```sql
-- 1. Define Inline TVF (Optimizer inlines this logic directly)
CREATE FUNCTION dbo.tvf_GetTopCustomerOrders (@CustomerID INT, @TopN INT)
RETURNS TABLE
AS
RETURN (
    SELECT TOP (@TopN)
        OrderID, 
        OrderDate, 
        TotalAmount
    FROM dbo.Orders
    WHERE CustomerID = @CustomerID
    ORDER BY OrderDate DESC
);

-- 2. Query with CROSS APPLY (Invoked per outer row)
SELECT 
    c.CustomerID, 
    c.CompanyName, 
    o.OrderID, 
    o.OrderDate, 
    o.TotalAmount
FROM dbo.Customers c
CROSS APPLY dbo.tvf_GetTopCustomerOrders(c.CustomerID, 3) o;
```

---

### B. PostgreSQL: Set-Returning Function (SRF) with `LATERAL`
```sql
-- 1. Define Set-Returning Function
CREATE OR REPLACE FUNCTION get_top_customer_orders(p_customer_id INT, p_top_n INT)
RETURNS TABLE (
    order_id INT,
    order_date DATE,
    total_amount NUMERIC(10,2)
) 
LANGUAGE sql
STABLE
AS $$
    SELECT order_id, order_date, total_amount
    FROM orders
    WHERE customer_id = p_customer_id
    ORDER BY order_date DESC
    LIMIT p_top_n;
$$;

-- 2. Query with JOIN LATERAL
SELECT 
    c.id, 
    c.name, 
    o.order_id, 
    o.total_amount
FROM customers c
CROSS JOIN LATERAL get_top_customer_orders(c.id, 3) o;
```

---

### C. Oracle: Pipelined Table Functions (`PIPELINED`)
In Oracle, Pipelined Table Functions stream rows back to the consumer one at a time via `PIPE ROW`, avoiding massive PGA memory allocations:

```plsql
-- 1. Object and Table Types
CREATE OR REPLACE TYPE t_order_row AS OBJECT (
    order_id NUMBER,
    total_amount NUMBER(10,2)
);
/
CREATE OR REPLACE TYPE t_order_tab IS TABLE OF t_order_row;
/

-- 2. Pipelined Function
CREATE OR REPLACE FUNCTION pipe_discounted_orders (p_customer_id NUMBER)
RETURN t_order_tab PIPELINED AS
BEGIN
    FOR r IN (
        SELECT order_id, total_amount 
        FROM orders 
        WHERE customer_id = p_customer_id
    ) LOOP
        -- Stream row immediately to caller without in-memory buffering
        PIPE ROW(t_order_row(r.order_id, r.total_amount * 0.90));
    END LOOP;
    RETURN;
END;
/

-- 3. Query as standard relational table
SELECT * FROM TABLE(pipe_discounted_orders(42));
```

---

## 2. Window Functions & Analytic Queries

Window functions perform calculations across a set of table rows related to the current row without collapsing rows into a single summary output:

$$\text{Function}() \text{ OVER } ( [ \text{PARTITION BY } \dots ] \ [ \text{ORDER BY } \dots ] \ [ \text{Frame: ROWS BETWEEN } \dots ] )$$

### A. Ranking Functions Comparison

| Function | Behavior on Duplicate/Tied Values | Example Sequence on Ties (100, 100, 90) |
|:---|:---|:---:|
| **`ROW_NUMBER()`** | Assigns strictly unique, sequential integers | $1, 2, 3$ |
| **`RANK()`** | Assigns same rank to ties; leaves gaps in rank sequence | $1, 1, 3$ |
| **`DENSE_RANK()`** | Assigns same rank to ties; leaves **no gaps** | $1, 1, 2$ |
| **`NTILE(N)`** | Divides partition into $N$ roughly equal buckets (e.g. quartiles: $1..4$) | $1, 1, 2, 2, 3, 3, 4, 4$ |

#### "Top $N$ per Group" Pattern using `DENSE_RANK()`:
```sql
WITH RankedOrders AS (
    SELECT 
        customer_id, 
        order_id, 
        total_amount,
        DENSE_RANK() OVER (
            PARTITION BY customer_id 
            ORDER BY total_amount DESC
        ) AS spending_rank
    FROM orders
)
SELECT * FROM RankedOrders 
WHERE spending_rank <= 3;
```

---

### B. Offset & Period-over-Period Calculations (`LAG` & `LEAD`)

```sql
SELECT 
    account_id,
    transaction_date,
    amount,
    -- Get previous transaction amount for the same account:
    LAG(amount, 1, 0) OVER (
        PARTITION BY account_id 
        ORDER BY transaction_date ASC
    ) AS prev_amount,
    -- Compute day-over-day delta:
    amount - LAG(amount, 1, 0) OVER (
        PARTITION BY account_id 
        ORDER BY transaction_date ASC
    ) AS delta
FROM transactions;
```

---

### C. Running Totals & Moving Averages (Frame Specifications)

```sql
SELECT 
    account_id,
    trans_date,
    amount,
    -- 1. Cumulative Running Balance:
    SUM(amount) OVER (
        PARTITION BY account_id 
        ORDER BY trans_date ASC
        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
    ) AS running_balance,
    -- 2. 7-Day Moving Average:
    AVG(amount) OVER (
        PARTITION BY account_id 
        ORDER BY trans_date ASC
        ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
    ) AS moving_avg_7d
FROM transactions;
```
> [!IMPORTANT]
> **Performance Heuristic (`ROWS` vs `RANGE`)**:
> Always specify `ROWS BETWEEN ...` instead of leaving the default `RANGE BETWEEN`. `RANGE` requires the engine to evaluate whether subsequent rows contain identical ordering values, often forcing temporary disk spooling. `ROWS` operates purely on physical row offsets and executes significantly faster.

---

## 3. Matrix Pivoting & Cross-Tabulation

Transforming normalized row-based records into columnar summary matrices:

### A. SQL Server & Oracle: Native `PIVOT` Operator
```sql
SELECT 
    Department, 
    [Q1], [Q2], [Q3], [Q4]
FROM (
    SELECT Department, Quarter, Revenue 
    FROM DepartmentRevenues
) AS SourceTable
PIVOT (
    SUM(Revenue)
    FOR Quarter IN ([Q1], [Q2], [Q3], [Q4])
) AS PivotTable;
```

### B. PostgreSQL & Universal ANSI: Conditional Aggregation
Compatible across all SQL engines (PostgreSQL, SQLite, MySQL, SQL Server, Oracle):

```sql
SELECT 
    department,
    SUM(CASE WHEN quarter = 'Q1' THEN revenue ELSE 0 END) AS q1_revenue,
    SUM(CASE WHEN quarter = 'Q2' THEN revenue ELSE 0 END) AS q2_revenue,
    SUM(CASE WHEN quarter = 'Q3' THEN revenue ELSE 0 END) AS q3_revenue,
    SUM(CASE WHEN quarter = 'Q4' THEN revenue ELSE 0 END) AS q4_revenue
FROM department_revenues
GROUP BY department;
```
*(In PostgreSQL 9.4+, you can also use modern aggregate filter syntax: `SUM(revenue) FILTER (WHERE quarter = 'Q1') AS q1_revenue`).*

