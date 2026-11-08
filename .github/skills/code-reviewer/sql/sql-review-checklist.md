# SQL Code Review Checklist

Senior-level review checklist for enterprise SQL across relational engines (SQL Server / T-SQL, PostgreSQL / PL-pgSQL, Oracle / PL-SQL, MySQL, SQLite), cross-referencing [`sql-executor`](file:///.github/skills/sql-executor/SKILL.md) and [`sql-connector`](file:///.github/skills/sql-connector/SKILL.md).

---

## 1. Zero-Tolerance SQL Firewall & Safety

- [ ] **Destructive DDL/DML Guardrails**:
  - Are raw `DROP TABLE`, `TRUNCATE TABLE`, or unconstrained `DELETE` statements present in application or migration code? Flag as `[P0 - Blocker]`.
  - Every `DELETE` or `UPDATE` must have an explicit, constrained `WHERE` clause matching specific primary keys or foreign keys.
- [ ] **SQL Injection Defense**:
  - Are queries using parameterized placeholders (`?`, `@param`, `:param`, `$1`) instead of raw string interpolation or concatenation (`+`, f-strings, template literals)?
  - Flag raw string concatenation in SQL queries as `[P0 - Blocker]`.

---

## 2. NULL Semantics & Three-Valued Logic

- [ ] **Comparison with NULL**:
  - Is `IS NULL` or `IS NOT NULL` used instead of `= NULL` or `!= NULL`?
  - In ANSI SQL, `col = NULL` always evaluates to `UNKNOWN` (falsy in `WHERE` clauses).
- [ ] **`NOT IN` with Nullable Subqueries**:
  - Is `NOT IN (SELECT col FROM ...)` used where `col` can contain `NULL`?
  - If a subquery returns a single `NULL`, `NOT IN` evaluates to `UNKNOWN` and returns zero rows!
  - **Resolution**: Use `NOT EXISTS (SELECT 1 FROM ... WHERE ...)` or add `WHERE col IS NOT NULL`.
- [ ] **Aggregate Functions & NULLs**:
  - Does code account for `COUNT(*)` (counts rows including NULLs) vs `COUNT(col)` (ignores NULLs)?
  - Are `COALESCE(SUM(val), 0)` or `ISNULL(SUM(val), 0)` used to handle empty sets?

---

## 3. Joins & Predicate Discipline

- [ ] **Explicit ANSI Joins**:
  - Are explicit `INNER JOIN`, `LEFT JOIN`, `FULL OUTER JOIN` used instead of comma-separated `FROM table1, table2` syntax?
- [ ] **Join Predicate Completeness**:
  - Does every join have a fully qualified `ON` condition? Missing predicates produce accidental Cartesian products ($O(N \times M)$ row blowups).
- [ ] **Outer Join Filter Placement**:
  - When filtering the preserved (left) table vs the optional (right) table in a `LEFT JOIN`:
    - Filtering the right table in the `WHERE` clause converts the `LEFT JOIN` into an `INNER JOIN` (unless checking `IS NULL`).
    - Right-table conditions intended for the join must reside in the `ON` clause.
- [ ] **Correlated Subqueries vs. Lateral Joins**:
  - Are expensive correlated subqueries in the `SELECT` list replaced with `LEFT JOIN LATERAL` (PostgreSQL) or `OUTER APPLY` (SQL Server / Oracle)?

---

## 4. Transaction Boundaries & Locking

- [ ] **Minimal Transaction Scope**:
  - Do transactions stay open across network calls or long-running computations?
  - Keep transactions as short as possible to prevent lock escalation, table locks, and blocking.
- [ ] **Deadlock Prevention**:
  - Are multiple tables updated in the exact same deterministic order across all application transactions?
- [ ] **Isolation Levels**:
  - Is `READ COMMITTED` or `READ COMMITTED SNAPSHOT` (RCSI) used to prevent read queries from taking shared locks that block writers?

