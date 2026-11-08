# MCP Workflow & Schema Discovery

Operational guide for querying databases and discovering schemas via the **`sql-connector`** MCP server.

---

## 1. The 3-Step Database Operations Protocol

AI agents interacting with live databases through `sql-connector` must follow this sequential protocol to avoid guessing column names, hitting unindexed scans, or triggering firewall blocks:

```
Step 1: Schema Discovery ──> Step 2: Query Plan & Safety Audit ──> Step 3: Guarded Execution
    (list_tables &                 (audit_query_safety &                (execute_query with
    describe_table)                    explain_query)                   maxRows & parameters)
```

### Step 1: Schema & Constraint Discovery
Never generate SQL queries based on assumed table or column names.
1. Run `list_tables` with the connection config to get active tables, views, or collections.
2. Run `describe_table` on target tables to discover:
   - Exact column names (case-sensitivity differences, e.g., Oracle uppercase vs Postgres lowercase).
   - Data types (`NUMERIC`, `VARCHAR`, `TIMESTAMP WITH TIME ZONE`, `BSON`).
   - Nullability constraints and Primary Key flags.

### Step 2: Safety Audit & Execution Plan
1. For complex queries or joins, run `audit_query_safety` dry-run to verify zero firewall violations (ensuring no accidental keywords trigger `CRITICAL_BLOCKED`).
2. Run `explain_query` to verify that joins and filter predicates utilize indexes rather than initiating full table scans on large tables.

### Step 3: Guarded Execution
1. Always supply query parameters as an array/object (`parameters: [...]`) instead of concatenating strings.
2. Rely on default `maxRows: 500` to prevent memory blowups in AI context windows.
3. Default to `mode: "read-only"`. Only switch to `mode: "guarded-write"` when bounded `INSERT` or specific `UPDATE ... WHERE id = ?` mutations are required.

---

## 2. Tool Invocation Templates

### Discovering Tables & Columns
```json
{
  "name": "list_tables",
  "arguments": {
    "connection": {
      "engine": "postgres",
      "connectionString": "postgresql://user:pass@localhost:5432/orders_db"
    }
  }
}
```

```json
{
  "name": "describe_table",
  "arguments": {
    "connection": {
      "engine": "postgres",
      "connectionString": "postgresql://user:pass@localhost:5432/orders_db"
    },
    "tableName": "customers"
  }
}
```

### Dry-Run Safety Audit
```json
{
  "name": "audit_query_safety",
  "arguments": {
    "query": "SELECT c.id, c.name, o.total FROM customers c INNER JOIN orders o ON c.id = o.customer_id WHERE o.created_at >= $1",
    "engine": "postgres",
    "mode": "read-only"
  }
}
```

### Executing Guarded Parameterized Query
```json
{
  "name": "execute_query",
  "arguments": {
    "connection": {
      "engine": "sqlite",
      "filePath": ":memory:"
    },
    "query": "SELECT id, sku, price FROM products WHERE category = ? AND in_stock = 1 ORDER BY price DESC",
    "parameters": ["electronics"],
    "mode": "read-only",
    "maxRows": 100,
    "timeoutMs": 10000
  }
}
```
