---
name: sql-connector
description: Connects to, introspects, and queries multi-engine databases (Microsoft SQL Server, Oracle, PostgreSQL, SQLite, MongoDB, MS Access, MySQL) via the sql-connector TypeScript MCP server. Enforces zero-tolerance safety guardrails preventing DROP TABLE, DELETE * or unbounded updates, and destructive DDL. Use when asked to "query database", "connect to sql server", "query postgres", "query oracle", "inspect database schema", "connect to sqlite", "query mongodb", "connect to ms access", "run safe sql", or "audit sql query safety".
version: 1.0.0
---

# SQL Connector

Safely inspect database schemas, evaluate query plans, and execute guarded SQL or MongoDB queries across relational and document databases using the `sql-connector` MCP server.

---

## Architectural Heuristics & Decision Matrix

| Database Engine | Recommended Adapter | Safety Mode Guidance | Primary Use Cases |
|:---|:---|:---|:---|
| **SQLite** | Built-in `node:sqlite` (Node 22+) | `read-only` (default) or `guarded-write` | Local testbeds, isolated reproduction fixtures, scratch databases. |
| **PostgreSQL** | Pure-JS `pg` adapter | `read-only` for audits; `guarded-write` for bounded data updates | Cloud databases, analytical queries, JSONB document querying. |
| **SQL Server** | Pure-JS `tedious` (TDS protocol) | `read-only` with `maxRows` capping | Enterprise transactional databases, T-SQL queries, stored procedure calls. |
| **Oracle** | `oracledb` Thin Client | `read-only` for inspection; `EXPLAIN PLAN` for tuning | Enterprise ERP/core systems, PL/SQL queries, data dictionary audits. |
| **MongoDB** | `mongodb` driver (MQL) | Structured JSON queries (`find`, `aggregate`) | Document stores, nested JSON collections, event streams. |
| **MS Access** | Windows ACE OLEDB / ODBC | `read-only` schema and table discovery | Legacy desktop databases (`.accdb`, `.mdb`), local file data extraction. |
| **MySQL / MariaDB**| Pure-JS `mysql2` | `read-only` (default) | Web applications, read replicas, relational queries. |

---

## Zero-Tolerance Safety Guardrails

Every query is filtered through the SQL Connector Firewall before execution:
1. **Forbidden DDL**: `DROP TABLE`, `DROP DATABASE`, `TRUNCATE TABLE`, `ALTER TABLE ... DROP` are strictly blocked in all modes.
2. **Forbidden DML**: `DELETE *`, `DELETE FROM table` without `WHERE`, and tautological clauses (`WHERE 1=1`, `WHERE 'a'='a'`, `WHERE true`) are blocked.
3. **Execution Mode**: Defaults to `read-only` (only `SELECT`, `EXPLAIN`, `SHOW`, `find`). Use `guarded-write` strictly for bounded `INSERT`/`UPDATE`/`DELETE` with explicit targets.
4. **Context Protection**: Results are capped to `maxRows: 500` by default to prevent context window exhaustion.

---

## Modular References

- [SQL Connector MCP Reference Guide](file:///.github/skills/sql-connector/references/sql-connector-reference.md) — Tool specifications, connection strings, firewall rules, and dialect examples.
