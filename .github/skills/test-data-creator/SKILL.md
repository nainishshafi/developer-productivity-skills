---
name: test-data-creator
description: >-
  Generates realistic, schema-conformant synthetic test data and high-volume performance test datasets across SQL (SQL Server, PostgreSQL, MySQL, Oracle, SQLite via sql-connector), JSON, and CSV formats. Supports streaming chunk generation for millions of records with constant memory, realistic cardinality and Zipfian/Pareto distributions, relational foreign-key integrity, boundary edge-case injection, and ephemeral in-memory SQLite fixtures for unit, integration, and load testing.
version: 1.0.0
---

# Test Data Creator

The **Test Data Creator** synthesizes realistic, high-fidelity mock datasets, API payloads, and high-volume performance test fixtures across relational databases (via [`sql-connector`](file:///.github/skills/sql-connector/SKILL.md)), JSON document trees, and CSV flat files.

Designed to prevent the pitfalls of trivial random test data, this skill enforces **relational foreign key integrity, realistic distribution skew (Pareto 80/20 hot partitions, Zipfian distributions), boundary edge-case injection, and constant $O(1)$ memory streaming** for high-volume load testing ($100\text{K} \dots 10\text{M}+$ rows).

---

## When to Use This Skill

- Generating synthetic test data for relational databases (SQL Server, Oracle, PostgreSQL, MySQL, SQLite).
- Seeding ephemeral in-memory SQLite (`:memory:`) databases for local unit and integration tests.
- Synthesizing mock JSON payloads for REST APIs, message queues (Kafka, RabbitMQ), or NoSQL collections (MongoDB).
- Generating high-volume datasets for load, stress, and performance testing ($100\text{K} \dots 1\text{M}+$ rows).
- Modeling realistic data skew (Pareto 80/20, hot tenant partitions, index selectivity, null ratios).
- Injecting adversarial boundary test cases (special characters, SQL quote escaping, extreme timestamps, overflow numbers).

---

## Core Capabilities

```
┌─────────────────────────────────┐
│     Schema & Table Inspection   │ ──► Inspects target tables via `sql-connector` (`describe_table`)
└────────────────┬────────────────┘
                 │
                 ▼
┌─────────────────────────────────┐
│   Data Modeling & Distribution  │ ──► Configures cardinality, null ratios, and Pareto 80/20 skew
└────────────────┬────────────────┘
                 │
                 ▼
┌─────────────────────────────────┐
│     Streaming Data Synthesis    │ ──► Generates SQL batches, JSON/NDJSON, or CSV with O(1) memory
└────────────────┬────────────────┘
                 │
                 ▼
┌─────────────────────────────────┐
│    Database Seeding & Verify    │ ──► Executes chunked inserts (500–2k rows) within transaction blocks
└─────────────────────────────────┘
```

1. **Relational Schema Fidelity**: Inspects existing tables via `sql-connector` (`describe_table`, `list_tables`) to match data types, column lengths, nullability constraints, and foreign key dependencies.
2. **High-Throughput Chunked Batching**: Emits multi-row `INSERT INTO ... VALUES (...), (...)` in chunks of 500 to 2,000 rows inside transaction blocks, accelerating seeding by $20\text{x}\text{--}50\text{x}$ over single-row inserts.
3. **Realistic Distribution Skew**: Supports Pareto 80/20 power-law and normal/Gaussian distributions to simulate real-world hot tenant partitions and database lock contention.
4. **Zero-Dependency Ephemeral Fixtures**: Seeds in-memory SQLite fixtures (`:memory:`) with zero external infrastructure required.
5. **Boundary & Injection Defense**: Systematically injects apostrophes (`O'Connor`), unicode/emojis (`🔥`), leap year timestamps (`2024-02-29`), and max integers to verify sanitization and edge-case handling.

---

## 5-Phase Workflow

### Phase 1: Schema & Domain Inspection

Inspect the target schema to identify required fields, types, and constraints:
- **For Relational Databases**: Use the [`sql-connector`](file:///.github/skills/sql-connector/SKILL.md) MCP server:
  - `list_tables` &rarr; Identify target tables and topological parent-child hierarchy.
  - `describe_table` &rarr; Retrieve column names, data types, nullability, and primary/foreign keys.
- **For JSON / Document APIs**: Inspect TypeScript interfaces, Pydantic models, or sample JSON payloads.

---

### Phase 2: Volume, Distribution & Profile Configuration

Select the appropriate volume tier and distribution profile:

| Volume Profile | Row Count | Target Evaluation | Distribution Setting |
|:---|:---|:---|:---|
| **Smoke / Unit** | $10 \dots 500$ | Local unit tests, mock API stubs | Uniform, strict boundary values |
| **Integration** | $1,000 \dots 25,000$ | API contract tests, join validation | Realistic foreign key relationships |
| **Load / Performance** | $100,000 \dots 1,000,000$ | Query optimization, index selectivity | Pareto 80/20 (`--skew pareto`), null ratios |
| **Soak / Volume** | $5,000,000+$ | Table partitioning, disk I/O, vacuuming | Streaming NDJSON / CSV direct bulk load |

---

### Phase 3: Generator Synthesis & Chunk Streaming

Execute the streaming data generator script using the repository virtual environment:

```bash
# Generate 1,000 user accounts in JSON format:
.\.venv\Scripts\python.exe .github/skills/test-data-creator/scripts/generate-test-data.py \
    --preset users --count 1000 --format json --output scratch/fixtures/users.json

# Generate 50,000 orders in SQL with 80/20 Pareto customer skew (batches of 1,000):
.\.venv\Scripts\python.exe .github/skills/test-data-creator/scripts/generate-test-data.py \
    --preset orders --count 50000 --format sql --table-name customer_orders \
    --batch-size 1000 --skew pareto --output scratch/fixtures/orders.sql

# Generate IoT time-series sensor metrics:
.\.venv\Scripts\python.exe .github/skills/test-data-creator/scripts/generate-test-data.py \
    --preset metrics --count 25000 --format csv --output scratch/fixtures/telemetry.csv

# Generate custom schema with specific fields:
.\.venv\Scripts\python.exe .github/skills/test-data-creator/scripts/generate-test-data.py \
    --fields "id:id,name:name,email:email,status:choice[ACTIVE|PENDING|SUSPENDED],balance:float,created_at:datetime" \
    --count 10000 --format sql --table-name accounts --output scratch/fixtures/accounts.sql
```

*(On POSIX, substitute `.\.venv\Scripts\python.exe` with `.venv/bin/python`).*

---

### Phase 4: Database Seeding & Safety Guardrails

When executing generated SQL statements into target databases:

1. **Verify Query Safety**: Run `audit_query_safety` via `sql-connector` to guarantee zero destructive mutations (`DROP TABLE`, `DELETE *`).
2. **Transaction Scoping**: Always execute inserts inside explicit `BEGIN TRANSACTION;` and `COMMIT;` blocks to prevent disk sync thrashing.
3. **Topological Order**: Seed parent tables first (Users $\to$ Products), followed by dependent child tables (Orders $\to$ OrderItems).
4. **Ephemeral SQLite In-Memory Seeding**:
   ```typescript
   import { DatabaseSync } from 'node:sqlite';
   const db = new DatabaseSync(':memory:');
   db.exec(`
     CREATE TABLE users (id INTEGER PRIMARY KEY, username TEXT, email TEXT);
     BEGIN TRANSACTION;
     INSERT INTO users (id, username, email) VALUES (1, 'john.doe', 'john@example.com'), (2, 'jane.smith', 'jane@example.com');
     COMMIT;
   `);
   ```

---

### Phase 5: Verification & Memory Persistence

1. **Verify Ingested Counts & Distribution**:
   - Run verification query: `SELECT status, COUNT(*) FROM customer_orders GROUP BY status;`
   - Verify Pareto distribution: Top 20% of customer IDs should account for ~80% of generated orders.
2. **Record Schema Seed Standards to Memory**:
   - Save permanent test data conventions and seed parameters into **`ledger`** using [`save-memory`](file:///.github/skills/save-memory/SKILL.md).
   - Save generation throughput benchmarks and lessons learned into **`journal`**.

---

## Practical Examples

### Example 1: Creating Relational Seed Data for Performance Testing

Goal: Generate 100,000 orders referencing 5,000 users with realistic Pareto distribution (testing database index efficiency).

```powershell
# 1. Generate 5,000 parent users:
.\.venv\Scripts\python.exe .github/skills/test-data-creator/scripts/generate-test-data.py `
    --preset users --count 5000 --format sql --table-name users `
    --batch-size 1000 --output scratch/seed_users.sql

# 2. Generate 100,000 child orders referencing the 5,000 users with Pareto skew:
.\.venv\Scripts\python.exe .github/skills/test-data-creator/scripts/generate-test-data.py `
    --preset orders --count 100000 --format sql --table-name orders `
    --batch-size 1000 --skew pareto --null-ratio 0.05 --output scratch/seed_orders.sql
```

### Example 2: Generating JSON Payload Mock for REST API / Kafka Stream

Goal: Stream 20,000 sensor telemetry records in NDJSON format for Kafka load testing.

```powershell
.\.venv\Scripts\python.exe .github/skills/test-data-creator/scripts/generate-test-data.py `
    --preset metrics --count 20000 --format ndjson `
    --output scratch/telemetry.ndjson
```

---

## References

- [Test Data Creator Reference Guide](file:///.github/skills/test-data-creator/references/test-data-creator-reference.md) — Comprehensive technical reference, distribution math, bulk loaders, and boundary edge cases.
- [Streaming Data Generator Script](file:///.github/skills/test-data-creator/scripts/generate-test-data.py) — Universal streaming generator in Python.
- [Sample Vocabularies Fixture](file:///.github/skills/test-data-creator/scripts/samples.json) — External JSON vocabulary fixture for names, domains, currencies, and devices.
- [SQL Connector MCP Server](file:///.github/skills/sql-connector/SKILL.md) — Database query execution, schema inspection, and safety firewall.
- [SQL Executor](file:///.github/skills/sql-executor/SKILL.md) — Multi-engine SQL query tuning and validation.
- [Researcher PoC Tester](file:///.github/skills/researcher-poc-tester/SKILL.md) — Empirical benchmarking and statistical test runner.
- [Save Memory](file:///.github/skills/save-memory/SKILL.md) — Persist test data configurations and seed schemas into `ledger`.
