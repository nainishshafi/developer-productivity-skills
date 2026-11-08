# SQL Connector MCP Server (`sql-connector`)

Enterprise Model Context Protocol (MCP) server providing unified, multi-database query execution and schema discovery across **Microsoft SQL Server, Oracle Database, PostgreSQL, SQLite, MongoDB, MS Access (`.accdb`/`.mdb`), and MySQL/MariaDB**.

Engineered with **Zero-Tolerance Safety Guardrails** to prevent catastrophic data wipes (`DROP TABLE`, `DELETE *`, tautological deletes, unbounded updates, and destructive DDL) when AI agents query databases.

---

## 🛡️ Core Safety Guardrails & SQL Firewall

The SQL Connector integrates an AST and lexical SQL firewall that audits every incoming query before database execution:

| Threat Category | Blocked Patterns | Engine Action |
|:---|:---|:---|
| **Destructive DDL** | `DROP TABLE`, `DROP DATABASE`, `DROP SCHEMA`, `DROP VIEW`, `DROP INDEX`, `DROP PROCEDURE`, `DROP FUNCTION`, `TRUNCATE TABLE`, `ALTER TABLE ... DROP ...` | **CRITICAL_BLOCKED**: Immediate rejection with security error; query never reaches DB. |
| **Unbounded Destructive DML** | `DELETE FROM table;`, `DELETE table;`, `DELETE * FROM table`, `UPDATE table SET ...` without `WHERE` | **CRITICAL_BLOCKED**: Unbounded data wipe strictly forbidden. |
| **Tautological Bypasses** | `WHERE 1=1`, `WHERE 0=0`, `WHERE 'a'='a'`, `WHERE true`, `WHERE 1`, `WHERE null is null`, `WHERE 1<=1` | **CRITICAL_BLOCKED**: Catches evasive clauses attempting to wipe all records. |
| **Multi-Statement Injections** | `SELECT * FROM users; DROP TABLE accounts;` | **CRITICAL_BLOCKED**: Individual statements split and audited; rejected if any statement violates policy. |
| **Obfuscated Comments** | `DROP/**/TABLE`, `-- comment \n DROP TABLE` | **CRITICAL_BLOCKED**: Comments stripped and normalized prior to evaluation. |
| **Administrative Commands** | `xp_cmdshell`, `sp_configure`, `SHUTDOWN`, `KILL` | **CRITICAL_BLOCKED**: System commands and arbitrary shell execution blocked. |
| **MongoDB Destructive MQL** | `db.users.drop()`, `dropDatabase()`, `deleteMany({})`, `remove({})` | **CRITICAL_BLOCKED**: Shell and JSON destructive operations blocked. |
| **Read-Only Mode Violations** | Any `INSERT`, `UPDATE`, `DELETE`, `MERGE` in default `read-only` mode | **REJECTED**: Defaults to read-only; mutations require explicit `guarded-write` mode. |

---

## 🗄️ Supported Database Engines

| Engine | Dialect / Driver | Connection Requirements | Key Features |
|:---|:---|:---|:---|
| **SQLite** | Built-in `node:sqlite` (Node 22+) | `filePath: "path/to/db.sqlite"` or `":memory:"` | Zero native compilation, in-memory testbeds, full schema introspection. |
| **PostgreSQL** | Wire protocol (`pg`) | `connectionString` or `host`, `port` (5432), `database`, `user`, `password` | Schema isolation, `EXPLAIN (FORMAT JSON)`, SSL support. |
| **SQL Server** | TDS protocol (`tedious`) | `host`, `port` (1433), `database`, `user`, `password` | Pure JavaScript TDS driver; works on Windows, Linux, and macOS. `SET SHOWPLAN_ALL`. |
| **Oracle** | Thin Client (`oracledb`) | `connectionString` or `host`, `port` (1521), `database` (Service Name) | Pure JavaScript thin mode (no Oracle Instant Client required). `DBMS_XPLAN.DISPLAY()`. |
| **MongoDB** | BSON / MQL (`mongodb`) | `connectionString` (e.g. `mongodb://localhost:27017/mydb`) | Structured JSON commands (`find`, `aggregate`, `countDocuments`). |
| **MS Access** | OLE DB / ODBC (`.accdb`, `.mdb`) | `filePath: "C:/path/to/database.accdb"` | Windows ACE OLEDB Provider bridge for legacy enterprise desktop databases. |
| **MySQL / MariaDB** | MySQL wire protocol (`mysql2`) | `connectionString` or `host`, `port` (3306), `database` | Fast pure-JS driver with connection pooling. |

---

## 🛠️ MCP Tools Reference

### 1. `execute_query`
Executes SQL queries or MongoDB JSON commands with safety firewall inspection, row capping, and timeout controls.
- **Parameters**:
  - `connection`: Database connection configuration (`engine`, `connectionString`, `filePath`, etc.).
  - `query`: SQL query string or MongoDB JSON command.
  - `parameters` *(optional)*: Positional parameter values for parameterized queries.
  - `mode` *(optional)*: `'read-only'` (default, only SELECT/find) or `'guarded-write'` (bounded mutations only).
  - `maxRows` *(optional)*: Row limit truncation threshold (default: 500, max: 5000).
  - `timeoutMs` *(optional)*: Execution timeout in milliseconds (default: 15000, max: 60000).

### 2. `list_tables`
Enumerates user tables, views, or MongoDB collections in the target database.
- **Parameters**:
  - `connection`: Database connection configuration.

### 3. `describe_table`
Inspects column names, data types, nullability, and primary key constraints for a specific table.
- **Parameters**:
  - `connection`: Database connection configuration.
  - `tableName`: Name of the table or collection to inspect.

### 4. `explain_query`
Inspects the query execution plan (`EXPLAIN`, `SHOWPLAN`) without modifying data or risking locks.
- **Parameters**:
  - `connection`: Database connection configuration.
  - `query`: Query string to explain.

### 5. `test_connection`
Verifies network connectivity, credentials, and firewall latency to the database.
- **Parameters**:
  - `connection`: Database connection configuration.

### 6. `audit_query_safety`
Offline dry-run tool to evaluate any query against the SQL Connector guardrails without executing against a live database.
- **Parameters**:
  - `query`: SQL or MongoDB query string.
  - `engine` *(optional)*: Dialect to analyze against (`'postgres'`, `'sqlserver'`, `'oracle'`, etc.).
  - `mode` *(optional)*: Intended safety mode (`'read-only'` or `'guarded-write'`).

---

## 🚀 Setup & Registration

### Installation
```bash
cd mcp/sql-connector
npm install
npm run build
npm test
```

### Register with MCP Clients

#### Claude Code / Claude Desktop
Add to your `claude_desktop_config.json` or `.mcp.json`:
```json
{
  "mcpServers": {
    "sql-connector": {
      "command": "node",
      "args": [
        "--experimental-sqlite",
        "<path-to-repo>/mcp/sql-connector/dist/index.js"
      ]
    }
  }
}
```

#### Cursor / Antigravity IDE
Register via CLI:
```bash
claude mcp add sql-connector node --experimental-sqlite <path-to-repo>/mcp/sql-connector/dist/index.js
```
