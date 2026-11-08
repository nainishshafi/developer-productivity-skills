# SQL Troubleshooting & Firewall Resolution Guide

Diagnostic playbook for resolving SQL Connector firewall rejections, connection failures, lock contention, and cross-dialect syntax pitfalls.

---

## 1. Resolving SQL Connector Firewall Blocks

When `sql-connector` blocks a query, it returns a structured violation message without touching the database:

### A. "Unbounded DELETE without WHERE clause (or DELETE *) is strictly blocked"
- **Cause**: Statement is `DELETE FROM table;` or `DELETE * FROM table`.
- **Resolution**: Supply a bounded, specific `WHERE` predicate:
  ```sql
  -- REJECTED:
  DELETE FROM staging_events;
  
  -- RESOLUTION:
  DELETE FROM staging_events WHERE batch_id = 4520 AND processed = 1;
  ```

### B. "DELETE with tautological WHERE condition is strictly blocked"
- **Cause**: Statement includes tautological bypasses such as `WHERE 1=1`, `WHERE 'a'='a'`, `WHERE true`, or `WHERE 0=0`.
- **Resolution**: Remove artificial tautologies and specify real identifier boundaries.

### C. "Mutation operation 'INSERT' is not permitted in 'read-only' mode"
- **Cause**: Query defaults to `mode: "read-only"`.
- **Resolution**: Set `mode: "guarded-write"` in the MCP tool parameters:
  ```json
  {
    "mode": "guarded-write"
  }
  ```

### D. "Destructive operation 'DROP_STATEMENT' is strictly blocked"
- **Cause**: `DROP TABLE`, `DROP DATABASE`, and `TRUNCATE TABLE` are unconditionally blocked in all modes by safety policy.
- **Resolution**: For test suites, use an ephemeral in-memory SQLite database (`filePath: ":memory:"`) where new test runs start with fresh, clean state.

---

## 2. Cross-Dialect Syntax Pitfalls

| Feature | PostgreSQL | SQL Server (T-SQL) | Oracle (PL/SQL) | SQLite |
|:---|:---|:---|:---|:---|
| **String Concatenation** | `'a' || 'b'` | `'a' + 'b'` or `CONCAT('a', 'b')` | `'a' || 'b'` | `'a' || 'b'` |
| **Current Timestamp** | `CURRENT_TIMESTAMP` or `now()` | `GETDATE()` or `SYSDATETIME()` | `SYSDATE` or `CURRENT_TIMESTAMP` | `datetime('now')` |
| **Row Limiting** | `LIMIT 10 OFFSET 20` | `OFFSET 20 ROWS FETCH NEXT 10 ROWS ONLY` | `FETCH FIRST 10 ROWS ONLY` | `LIMIT 10 OFFSET 20` |
| **Identifier Casing** | Default lowercase (`users`) | Case-insensitive default | Default UPPERCASE (`USERS`) | Case-insensitive |
| **Boolean Literals** | `TRUE`, `FALSE` | `1`, `0` (BIT type) | `1`, `0` (NUMBER type) | `1`, `0` (INTEGER) |
| **Null Handling** | `COALESCE(val, 0)` | `ISNULL(val, 0)` or `COALESCE` | `NVL(val, 0)` or `COALESCE` | `IFNULL(val, 0)` or `COALESCE` |

---

## 3. Diagnosing Locks & Timeouts

### PostgreSQL: Detecting Blocked Queries
```sql
SELECT 
    pid, 
    usename, 
    pg_blocking_pids(pid) AS blocked_by, 
    query, 
    state, 
    now() - query_start AS duration
FROM pg_stat_activity
WHERE cardinality(pg_blocking_pids(pid)) > 0;
```

### SQL Server: Identifying Lock Waiters
```sql
SELECT 
    r.session_id, 
    r.blocking_session_id, 
    r.wait_type, 
    r.wait_time / 1000 AS wait_sec, 
    t.text AS query_text
FROM sys.dm_exec_requests r
CROSS APPLY sys.dm_exec_sql_text(r.sql_handle) t
WHERE r.blocking_session_id <> 0;
```

---

## 4. Missing Database Drivers Remediation

If calling an adapter returns `Cannot find package '<driver>'`:
```bash
# Navigate to sql-connector MCP directory:
cd mcp/sql-connector

# Install the required driver:
npm install pg           # For PostgreSQL
npm install tedious      # For Microsoft SQL Server
npm install oracledb     # For Oracle Database
npm install mongodb      # For MongoDB
npm install mysql2       # For MySQL / MariaDB

# Rebuild:
npm run build
```
*(SQLite is built directly into Node.js 22 and requires no external packages).*
