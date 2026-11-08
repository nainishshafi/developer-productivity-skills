# SQL Connector MCP Reference Guide

Comprehensive guide to configuring, querying, and auditing databases using the **`sql-connector`** Model Context Protocol (MCP) server across Microsoft SQL Server, Oracle Database, PostgreSQL, SQLite, MongoDB, MS Access, and MySQL.

---

## 1. Zero-Tolerance Safety Guardrail Architecture

The SQL Connector MCP server acts as an intelligent SQL Firewall between the AI Agent and target databases. Every query passes through AST and lexical normalization before execution.

```
AI Agent Request
       │
       ▼
[SQL Connector Firewall]
  ├── Normalize Whitespace & Strip Comments (/* ... */, --, #)
  ├── Multi-Statement Split & Statement Boundary Inspection
  ├── DDL Audit: Reject DROP TABLE, DROP DATABASE, TRUNCATE, ALTER DROP
  ├── DML Audit: Reject DELETE *, DELETE without WHERE, Tautologies (1=1, true)
  ├── Policy Audit: Enforce 'read-only' vs 'guarded-write'
  └── Safety Verdict:
        ├── REJECTED ──> Return CRITICAL_BLOCKED / Error to Agent (No DB touch)
        └── APPROVED ──> Inject maxRows & execute with timeout
```

### Prohibited Statements & Bypasses in All Modes

| Attack / Dangerous Pattern | Example | Guardrail Behavior |
|:---|:---|:---|
| **`DROP TABLE`** | `DROP TABLE users;` | **CRITICAL_BLOCKED**: Immediate rejection. |
| **`DROP DATABASE / SCHEMA`** | `DROP DATABASE production;` | **CRITICAL_BLOCKED**: Immediate rejection. |
| **`TRUNCATE TABLE`** | `TRUNCATE TABLE audit_log;` | **CRITICAL_BLOCKED**: Immediate rejection. |
| **`ALTER TABLE DROP`** | `ALTER TABLE users DROP COLUMN email;` | **CRITICAL_BLOCKED**: Immediate rejection. |
| **Unbounded `DELETE`** | `DELETE FROM accounts;` | **CRITICAL_BLOCKED**: Unbounded delete forbidden. |
| **`DELETE *`** | `DELETE * FROM accounts;` | **CRITICAL_BLOCKED**: Unbounded delete forbidden. |
| **Tautological `WHERE`** | `DELETE FROM users WHERE 1=1;` | **CRITICAL_BLOCKED**: Tautological wipe caught. |
| **Tautological String Equality** | `DELETE FROM users WHERE 'a'='a';` | **CRITICAL_BLOCKED**: Tautological wipe caught. |
| **Tautological Boolean** | `DELETE FROM users WHERE true;` | **CRITICAL_BLOCKED**: Tautological wipe caught. |
| **Multi-Statement Chaining** | `SELECT 1; DROP TABLE users;` | **CRITICAL_BLOCKED**: Chained destruction rejected. |
| **Comment Obfuscation** | `DROP/**/TABLE users;` | **CRITICAL_BLOCKED**: Comments stripped prior to check. |
| **System Stored Procedures** | `EXEC xp_cmdshell 'dir';` | **CRITICAL_BLOCKED**: Shell execution rejected. |
| **MongoDB Drop Database** | `{"operation": "dropDatabase"}` | **CRITICAL_BLOCKED**: Database drop rejected. |
| **MongoDB Empty `deleteMany`**| `{"operation": "deleteMany", "filter": {}}` | **CRITICAL_BLOCKED**: Unbounded delete rejected. |

---

## 2. MCP Tools Specification

### `execute_query`
Executes SQL queries or MongoDB JSON commands with safety validation and result row truncation.

```json
{
  "name": "execute_query",
  "arguments": {
    "connection": {
      "engine": "postgres",
      "host": "localhost",
      "port": 5432,
      "database": "analytics_db",
      "user": "readonly_user",
      "password": "secret_password"
    },
    "query": "SELECT id, email, created_at FROM users WHERE created_at >= $1 ORDER BY id DESC",
    "parameters": ["2026-01-01"],
    "mode": "read-only",
    "maxRows": 100,
    "timeoutMs": 15000
  }
}
```

### `list_tables`
Enumerates all tables, views, or collections.

```json
{
  "name": "list_tables",
  "arguments": {
    "connection": {
      "engine": "sqlite",
      "filePath": "C:/data/app.db"
    }
  }
}
```

### `describe_table`
Retrieves column names, data types, nullability, and primary key indicators.

```json
{
  "name": "describe_table",
  "arguments": {
    "connection": {
      "engine": "sqlserver",
      "host": "sql.corp.internal",
      "port": 1433,
      "database": "Northwind",
      "user": "sa",
      "password": "Password123!"
    },
    "tableName": "Customers"
  }
}
```

### `explain_query`
Generates execution plan without running mutations.

```json
{
  "name": "explain_query",
  "arguments": {
    "connection": {
      "engine": "oracle",
      "host": "oracle.corp.internal",
      "port": 1521,
      "database": "ORCLPDB1",
      "user": "hr",
      "password": "hr_password"
    },
    "query": "SELECT employee_id, last_name, salary FROM employees WHERE department_id = 80"
  }
}
```

### `test_connection`
Verifies latency and connectivity.

```json
{
  "name": "test_connection",
  "arguments": {
    "connection": {
      "engine": "mongodb",
      "connectionString": "mongodb://localhost:27017/shop"
    }
  }
}
```

### `audit_query_safety`
Offline dry-run tool to evaluate query safety without database credentials.

```json
{
  "name": "audit_query_safety",
  "arguments": {
    "query": "DELETE FROM invoices WHERE 1=1;",
    "engine": "postgres",
    "mode": "guarded-write"
  }
}
```

---

## 3. Engine-Specific Configuration Examples

### Microsoft SQL Server (`sqlserver`)
Uses the pure-JS TDS protocol driver (`tedious`).
```json
{
  "engine": "sqlserver",
  "host": "localhost",
  "port": 1433,
  "database": "SalesDB",
  "user": "sql_agent",
  "password": "SecurePassword123!",
  "ssl": true
}
```

### Oracle Database (`oracle`)
Uses the thin mode driver (`oracledb`). Requires no Oracle Instant Client.
```json
{
  "engine": "oracle",
  "host": "oracle-host.example.com",
  "port": 1521,
  "database": "FREEPDB1",
  "user": "scott",
  "password": "tiger"
}
```

### PostgreSQL (`postgres`)
```json
{
  "engine": "postgres",
  "connectionString": "postgresql://agent_user:password@localhost:5432/reporting_db?sslmode=prefer"
}
```

### SQLite (`sqlite`)
Uses Node 22 native `node:sqlite`. Zero external dependencies.
```json
{
  "engine": "sqlite",
  "filePath": ":memory:"
}
```
Or for file-based databases:
```json
{
  "engine": "sqlite",
  "filePath": "C:/workspace/data/cache.sqlite3"
}
```

### MongoDB (`mongodb`)
MQL queries formatted as JSON commands:
```json
{
  "operation": "find",
  "collection": "orders",
  "filter": { "status": "shipped", "total": { "$gte": 100 } },
  "limit": 50
}
```

### Microsoft Access (`msaccess`)
Connects to `.accdb` or `.mdb` files via Windows ACE OLEDB Provider:
```json
{
  "engine": "msaccess",
  "filePath": "C:/legacy_apps/inventory.accdb"
}
```

---

## 4. Integration with `agent-orchestrator`

During multi-agent lifecycles coordinated by [`agent-orchestrator`](file:///.github/skills/agent-orchestrator/SKILL.md):
- **Stage 1 (Plan)**: Use `list_tables` and `describe_table` to inspect schema definitions, foreign keys, and constraints before proposing data model migrations or API designs.
- **Stage 2 (Develop)**: Use SQLite in `:memory:` mode for isolated test fixture seeding, zero-latency unit tests, and regression harnesses.
- **Stage 4 (Complexity Checks)**: Use `explain_query` to evaluate whether database queries execute full table scans or utilize B-tree indexes, avoiding $O(N)$ database scans in production hot paths.
- **Stage 7 (Security Checks)**: Use `audit_query_safety` to verify that dynamic SQL queries constructed by the agent do not permit SQL injection or catastrophic data loss.
