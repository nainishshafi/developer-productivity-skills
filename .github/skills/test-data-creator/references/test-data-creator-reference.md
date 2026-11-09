# Test Data Creator Reference Guide

A comprehensive architectural and engineering handbook for generating synthetic test datasets, high-volume performance test loads, and relational database fixtures.

---

## 1. Test Data Generation Architecture

Generating test data for enterprise applications requires balancing three competing forces:

```
                      ┌────────────────────────────────────────┐
                      │          Data Fidelity & Skew          │
                      │ (Pareto 80/20, Zipfian, Cardinalities) │
                      └───────────────────┬────────────────────┘
                                          │
                    ┌─────────────────────┴─────────────────────┐
                    ▼                                           ▼
┌───────────────────────────────────────┐   ┌───────────────────────────────────────┐
│        Relational Integrity           │   │         Generation Throughput         │
│ (Foreign keys, topological ordering)  │   │   (Chunked streaming, O(1) memory)    │
└───────────────────────────────────────┘   └───────────────────────────────────────┘
```

1. **Generation Throughput**: Generating $1\text{M}+$ rows must not allocate $1\text{M}$ objects in memory. It must stream chunked buffers directly to disk or socket.
2. **Relational Integrity**: Dependent child records (`orders`) must strictly reference valid generated parent keys (`customers`).
3. **Distribution Fidelity**: Uniform random data fails to expose production bottlenecks. Real systems experience **Pareto skew** (80% of activity concentrated in 20% of entities), hot partition contention, and clustered timestamps.

---

## 2. Test Volume Tiers & Profiles

| Tier | Row Count | Target Use Case | Primary Focus | Generation Strategy |
|:---|:---|:---|:---|:---|
| **Smoke / Unit** | $10 \dots 500$ | Unit tests, PR checks, local mocks | Edge cases, boundaries, exact values | Single JSON fixture or in-memory SQLite |
| **Integration** | $1,000 \dots 25,000$ | Service integration, API contracts | Foreign key integrity, pagination ($O(\log N)$) | Multi-table SQL script with transaction |
| **Performance / Load** | $100,000 \dots 1,000,000$ | Query tuning, index benchmarking, ORM N+1 | Buffer pool hit ratio, B-Tree depth, join spills | Streaming chunked batch inserts (1k/chunk) |
| **Soak / Volume** | $5,000,000 \dots 50,000,000+$ | Table partitioning, data archival, vacuuming | Disk I/O saturation, table scans ($O(N)$) | Direct bulk loader (`COPY`, `BULK INSERT`) |

---

## 3. Realistic Distribution Modeling & Skew

### 1. The 80/20 Pareto & Zipfian Distribution (Hot Partitions)
In e-commerce, banking, and SaaS systems, activity is heavily skewed:
- 20% of users place 80% of orders.
- 5% of tenants generate 90% of audit logs.
- Testing with uniform random IDs masks lock contention, hot partition bottlenecks, and B-Tree page splits.

```python
# Pareto (80/20) skew generator for foreign keys:
def pareto_skew_id(max_id: int, alpha: float = 1.16) -> int:
    u = random.random()
    val = int(1.0 / ((1.0 - u) ** (1.0 / alpha)))
    return min(max_id, max(1, val))
```

### 2. Cardinality & Index Selectivity:
- **Low Cardinality (Bad for B-Tree, Good for Bitmap/Filtered Indexes)**: Status fields (`ACTIVE`, `INACTIVE`), Boolean flags, Gender.
  - *Trap*: Query optimizer ignores B-Tree index if a status filter matches $> 20\%$ of the table (table scan is cheaper).
- **High Cardinality (Optimal for B-Tree Indexes)**: UUIDs, Order Numbers, Email addresses, timestamps.

### 3. Null Ratio Injection:
Real enterprise databases contain nullable columns. Injecting realistic null ratios ($2\% \dots 15\%$) tests:
- `LEFT OUTER JOIN` vs `INNER JOIN` semantics.
- Partial index coverage (e.g. PostgreSQL `CREATE INDEX ... WHERE phone IS NOT NULL`).
- Code deserializers (catching `NullPointerException` and `TypeError: Cannot read properties of null`).

---

## 4. High-Throughput Seeding & Database Guardrails

### 1. Batch Size Sweet Spot:
- Single-row `INSERT INTO table VALUES (...)` incurs one network round-trip and one disk flush per row ($\approx 50\text{--}200\text{ rows/sec}$).
- Multi-row chunked `INSERT INTO table VALUES (...), (...), (...)` in batches of **500 to 2,000 rows** increases throughput to **$30,000\text{--}100,000+\text{ rows/sec}$**.
- Exceeding 5,000 rows per batch triggers SQL engine parameter limits (e.g. SQL Server 2,100 parameter limit; PostgreSQL 65,535 parameter limit).

### 2. Ephemeral SQLite `:memory:` Seeding (Zero-Dependency Testing):
For unit and integration test fixtures, seed an in-memory SQLite database:
```sql
PRAGMA synchronous = OFF;
PRAGMA journal_mode = MEMORY;
PRAGMA temp_store = MEMORY;

BEGIN TRANSACTION;
-- Chunked inserts...
COMMIT;
```

### 3. Engine-Specific High-Volume Bulk Loading:

| Database Engine | Recommended High-Volume Loader | Peak Ingestion Rate |
|---|---|---|
| **PostgreSQL** | `COPY table (cols) FROM STDIN WITH (FORMAT csv)` | $100,000\text{--}250,000\text{ rows/sec}$ |
| **SQL Server** | `BULK INSERT` or `SqlBulkCopy` (.NET) | $80,000\text{--}150,000\text{ rows/sec}$ |
| **Oracle** | SQL*Loader (`DIRECT=TRUE`) or `FORALL` bulk array bind | $50,000\text{--}120,000\text{ rows/sec}$ |
| **MySQL / MariaDB** | `LOAD DATA LOCAL INFILE` | $80,000\text{--}180,000\text{ rows/sec}$ |
| **SQLite** | `BEGIN TRANSACTION;` + chunked multi-row inserts | $100,000\text{--}300,000\text{ rows/sec}$ |

---

## 5. Topological Ordering for Relational Dependencies

When generating multi-table relational datasets, parent tables must be generated and seeded before child tables to satisfy Foreign Key constraints:

```
[1. Users / Accounts]  (Parent)
         │
         ▼
[2. Products / Catalog] (Parent)
         │
         ├──────────────────────┐
         ▼                      ▼
[3. Customer Orders]     [4. Inventory Stock] (Children)
         │
         ▼
[5. Order Items / Payments] (Grandchildren)
```

**Generation Sequence Rule:**
1. Generate parent keys and record ID ranges (e.g. `user_id` $1 \dots 10,000$).
2. Generate child entities referencing parent IDs using uniform or Pareto distributions.
3. Generate line items linking orders to product catalogs.
4. Tear down in reverse order (`OrderItems` $\to$ `Orders` $\to$ `Users`).

---

## 6. Boundary Edge-Case Injection Matrix

| Category | Boundary Values to Inject | Traps Exposed |
|---|---|---|
| **Strings / Names** | Empty string `""`, single whitespace `" "`, $255$-character strings, $10,000$-character CLOBs | Column truncation, missing trim validation |
| **Unicode & Emojis** | `"O'Connor"`, `"D'Angelo"`, `José`, ` Müller`, `日本語`, `🔥🚀`, RTL Arabic/Hebrew | SQL injection via unescaped quotes, `latin1` encoding crashes |
| **Numbers / Money** | `0`, `-0.01`, `0.00001`, `999999999.99`, `NaN`, `Infinity`, `MAX_INT` ($2,147,483,647$) | Division by zero, floating point rounding drift, integer overflow |
| **Dates & Timestamps** | `1970-01-01T00:00:00Z` (Unix Epoch), `2038-01-19T03:14:07Z` (32-bit overflow), Leap year `2024-02-29`, DST switchover hour | Timezone drift, epoch rollover bugs, invalid calendar parsing |
