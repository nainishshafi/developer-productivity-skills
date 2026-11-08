# Multi-Engine Joins Architecture Guide

Comprehensive patterns, syntax rules, and dialect quirks for formulating high-performance joins across relational and document engines.

---

## 1. Dialect Join Support & Quirks Matrix

| Engine | `LEFT JOIN` | `FULL OUTER` | `LATERAL / APPLY` | Special Dialect Quirks & Pitfalls |
|:---|:---:|:---:|:---:|:---|
| **PostgreSQL** | Native | Native | `JOIN LATERAL (...)` | Supports correlated subqueries in FROM clause; optimizer switches between Hash, Merge, and Nested Loop joins based on statistics. |
| **SQL Server** | Native | Native | `CROSS / OUTER APPLY` | `CROSS APPLY` acts like an inner correlated join (essential for "Top $N$ per category"); `OUTER APPLY` preserves outer row when subquery is empty. |
| **Oracle** | Native | Native | `LATERAL (...)` | Always use ANSI-92 syntax. Never use deprecated Oracle `(+)` outer join operator. |
| **SQLite** | Native | **Unsupported** | **Unsupported** | SQLite lacks `RIGHT JOIN` and `FULL OUTER JOIN`. Workaround: `LEFT JOIN` combined with `UNION ALL` or `FULL OUTER JOIN` simulation. |
| **MongoDB** | `$lookup` | Custom pipeline | `$lookup` with `let` | `$lookup` performs left outer joins. Requires index on `foreignField` to avoid $O(M \times N)$ collection scans. |
| **MS Access** | Native | **Unsupported** | **Unsupported** | **Strict Parentheses Requirement**: Joining 3+ tables fails with syntax error unless explicit nested parentheses group every join pair. |
| **MySQL** | Native | **Unsupported** | Native (8.0.14+) | Simulates `FULL OUTER JOIN` via `UNION`. MySQL 8+ uses Block Nested-Loop / Hash Joins. |

---

## 2. Dialect-Specific Join Patterns

### PostgreSQL: Correlated `LATERAL` Joins
When you need to join each row from `accounts` with the latest 3 transactions:

```sql
SELECT 
    a.id AS account_id, 
    a.name, 
    t.id AS transaction_id, 
    t.amount, 
    t.created_at
FROM accounts a
LEFT JOIN LATERAL (
    SELECT id, amount, created_at
    FROM transactions
    WHERE account_id = a.id
    ORDER BY created_at DESC
    LIMIT 3
) t ON true;
```

---

### SQL Server: `CROSS APPLY` and `OUTER APPLY`
In T-SQL, `APPLY` executes a table-valued function or correlated subquery per outer row:

```sql
SELECT 
    c.CustomerID, 
    c.CompanyName, 
    o.OrderID, 
    o.OrderDate, 
    o.TotalAmount
FROM Customers c
OUTER APPLY (
    SELECT TOP 3 OrderID, OrderDate, TotalAmount
    FROM Orders
    WHERE CustomerID = c.CustomerID
    ORDER BY OrderDate DESC
) o;
```
> [!TIP]
> Use `CROSS APPLY` when rows with no child records should be excluded (like `INNER JOIN`). Use `OUTER APPLY` when the parent record must be preserved (like `LEFT JOIN`).

---

### Oracle: Hierarchical & Partitioned Joins
Oracle ANSI joins with hierarchical CTEs:

```sql
WITH OrgChart (employee_id, manager_id, last_name, org_level) AS (
    SELECT employee_id, manager_id, last_name, 1
    FROM employees
    WHERE manager_id IS NULL
    UNION ALL
    SELECT e.employee_id, e.manager_id, e.last_name, o.org_level + 1
    FROM employees e
    INNER JOIN OrgChart o ON e.manager_id = o.employee_id
)
SELECT 
    o.employee_id, 
    o.last_name, 
    o.org_level, 
    d.department_name
FROM OrgChart o
LEFT JOIN departments d ON o.department_id = d.department_id
ORDER BY o.org_level, o.last_name;
```

---

### SQLite: Simulating `FULL OUTER JOIN`
SQLite supports `INNER JOIN` and `LEFT JOIN`, but rejects `RIGHT JOIN` and `FULL OUTER JOIN`:

```sql
-- Full Outer Join Simulation in SQLite
SELECT a.id, a.name, b.order_num
FROM customers a
LEFT JOIN orders b ON a.id = b.customer_id

UNION ALL

SELECT a.id, a.name, b.order_num
FROM orders b
LEFT JOIN customers a ON a.id = b.customer_id
WHERE a.id IS NULL;
```

---

### MS Access: The Nested Parentheses Rule
MS Access Jet/ACE SQL engine parses joins left-to-right with strict binary associativity:
```sql
-- WRONG in MS Access (Throws: Syntax error in JOIN operation):
-- FROM TableA INNER JOIN TableB ON TableA.id = TableB.a_id INNER JOIN TableC ON TableB.id = TableC.b_id

-- CORRECT in MS Access:
SELECT 
    c.CustomerName, 
    o.OrderID, 
    p.ProductName
FROM (
    (Customers c
    INNER JOIN Orders o ON c.CustomerID = o.CustomerID)
    INNER JOIN OrderDetails od ON o.OrderID = od.OrderID
)
INNER JOIN Products p ON od.ProductID = p.ProductID
WHERE c.Country = 'Canada';
```

---

### MongoDB: `$lookup` Pipeline Joins
In MongoDB, cross-collection joins are performed using aggregation pipelines:

```json
{
  "operation": "aggregate",
  "collection": "customers",
  "pipeline": [
    { "$match": { "status": "active" } },
    {
      "$lookup": {
        "from": "orders",
        "localField": "_id",
        "foreignField": "customerId",
        "as": "recentOrders",
        "pipeline": [
          { "$sort": { "orderDate": -1 } },
          { "$limit": 5 }
        ]
      }
    },
    { "$unwind": { "path": "$recentOrders", "preserveNullAndEmptyArrays": true } },
    {
      "$project": {
        "name": 1,
        "email": 1,
        "orderId": "$recentOrders._id",
        "total": "$recentOrders.totalAmount"
      }
    }
  ]
}
```
