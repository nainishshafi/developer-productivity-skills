# Oracle Cursors & PL/SQL Optimization Guide

Architectural heuristics and production patterns for working with Oracle cursors, `SYS_REFCURSOR`, bulk array operations, and PL/SQL execution.

---

## 1. Cursor Types & Selection Matrix

| Cursor Pattern | Typical Use Case | Memory / Context | Performance Heuristic |
|:---|:---|:---|:---|
| **Cursor `FOR` Loop** | Iterating over small/medium read sets (< 10,000 rows) | Handled automatically by PL/SQL engine | Oracle 11g+ auto-optimizes with internal 100-row bulk array fetch. Cleanest code. |
| **`BULK COLLECT` + `LIMIT`** | High-volume batch processing (> 50,000 rows) | Process Private Memory (PGA) array allocation | **Mandatory**: Always specify `LIMIT 500..5000` to prevent PGA memory exhaustion. |
| **`SYS_REFCURSOR`** | Returning dynamic query result sets to client drivers (Node.js/oracledb) | Client/Server shared cursor pointer | Return cursor open; client is responsible for fetching and closing. |
| **Explicit Cursor (`OPEN/FETCH/CLOSE`)** | When granular control over `%ROWCOUNT` or `%FOUND` flags is required | Requires manual cursor lifecycle management | Use only when Cursor FOR Loop or BULK COLLECT does not fit logic. |
| **`SELECT INTO` (Implicit)** | Single-row exact lookups | Automatic | **Must handle exceptions**: `NO_DATA_FOUND` and `TOO_MANY_ROWS`. |

---

## 2. Eliminating RBAR: `BULK COLLECT` and `FORALL`

Row-By-Row processing ("Row By Agonizing Row" or RBAR) incurs excessive context switching between the PL/SQL engine and SQL execution engine. Use `BULK COLLECT` and `FORALL` to execute in batches:

### Bulk Data Fetching with Bounded PGA Allocation
```plsql
DECLARE
    TYPE t_order_tab IS TABLE OF orders%ROWTYPE;
    l_orders t_order_tab;
    
    CURSOR c_orders IS
        SELECT * FROM orders
        WHERE status = 'PENDING'
        ORDER BY order_date ASC;
BEGIN
    OPEN c_orders;
    LOOP
        -- Fetch in chunks of 1,000 to keep PGA memory footprint bounded
        FETCH c_orders BULK COLLECT INTO l_orders LIMIT 1000;
        EXIT WHEN l_orders.COUNT = 0;
        
        -- Process batch in-memory or prepare DML
        FORALL i IN 1..l_orders.COUNT
            UPDATE orders 
            SET processed_date = SYSDATE, status = 'PROCESSING'
            WHERE order_id = l_orders(i).order_id;
            
        COMMIT; -- Commit per batch to release undo/redo pressure
    END LOOP;
    CLOSE c_orders;
END;
/
```
> [!IMPORTANT]
> Never write `FETCH ... BULK COLLECT INTO` without a `LIMIT` clause on unbounded tables. Without `LIMIT`, Oracle attempts to load the entire table into PGA RAM, triggering `ORA-04030: out of process memory`.

---

## 3. `SYS_REFCURSOR` for Node.js & MCP Clients

`SYS_REFCURSOR` enables PL/SQL stored procedures or anonymous blocks to return dynamic, weakly-typed result sets to client drivers like `oracledb`:

### PL/SQL Procedure Returning Cursor
```plsql
CREATE OR REPLACE PROCEDURE get_customer_orders (
    p_customer_id IN  customers.customer_id%TYPE,
    p_cursor      OUT SYS_REFCURSOR
) AS
BEGIN
    OPEN p_cursor FOR
        SELECT 
            o.order_id, 
            o.order_date, 
            o.total_amount, 
            o.status
        FROM orders o
        WHERE o.customer_id = p_customer_id
        ORDER BY o.order_date DESC;
END get_customer_orders;
/
```

### Consuming `SYS_REFCURSOR` in Node.js `oracledb` Thin Client
```typescript
import oracledb from 'oracledb';

async function fetchCustomerOrders(connection: oracledb.Connection, customerId: number) {
  const result = await connection.execute<{ p_cursor: oracledb.ResultSet<any> }>(
    `BEGIN get_customer_orders(:p_customer_id, :p_cursor); END;`,
    {
      p_customer_id: customerId,
      p_cursor: { type: oracledb.CURSOR, dir: oracledb.BIND_OUT },
    }
  );

  const resultSet = result.outBinds?.p_cursor;
  if (!resultSet) return [];

  const rows: any[] = [];
  let rowChunk: any[];
  
  // Stream rows in 100-row chunks
  while ((rowChunk = await resultSet.getRows(100)).length > 0) {
    rows.push(...rowChunk);
  }

  // Always close the result set to release Oracle server cursor resources
  await resultSet.close();
  return rows;
}
```

---

## 4. Parameterized Cursors & Pessimistic Locking

### Parameterized Cursor with `FOR UPDATE NOWAIT`
When acquiring locks on rows for critical transaction processing:

```plsql
DECLARE
    CURSOR c_inventory (p_sku VARCHAR2) IS
        SELECT product_id, stock_qty, reserved_qty
        FROM inventory
        WHERE sku = p_sku
        FOR UPDATE OF stock_qty NOWAIT; -- Fails immediately with ORA-00054 if locked
        
    l_inv c_inventory%ROWTYPE;
BEGIN
    OPEN c_inventory('SKU-9901');
    FETCH c_inventory INTO l_inv;
    
    IF c_inventory%FOUND THEN
        UPDATE inventory 
        SET reserved_qty = reserved_qty + 1 
        WHERE CURRENT OF c_inventory; -- Uses cursor rowid seek for instant O(1) update
    END IF;
    
    CLOSE c_inventory;
    COMMIT;
EXCEPTION
    WHEN OTHERS THEN
        IF c_inventory%ISOPEN THEN CLOSE c_inventory; END IF;
        RAISE;
END;
/
```

