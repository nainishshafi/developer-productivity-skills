# Data Extraction & Validation Guide

Rigorous methodologies for verifying data integrity, detecting anomalies, and validating extracted database records.

---

## 1. Automated Extraction Verification Protocol

When extracting data for analysis, migration, or reporting via `sql-connector`, follow this verification checklist:

```
[Extract Sample (N=10)] ──> [Schema & Type Check] ──> [Reconciliation & Integrity] ──> [Chunked Extraction]
```

---

## 2. Integrity Verification Query Patterns

### A. Uniqueness & Primary Key Validation
Verify that no duplicate natural or surrogate keys exist:

```sql
SELECT 
    customer_code, 
    COUNT(*) AS occurrence_count
FROM customers
GROUP BY customer_code
HAVING COUNT(*) > 1;
```
*Expected Result: 0 rows returned.*

### B. Completeness & Nullability Audits
Identify unexpected `NULL` values in mandatory fields across large tables:

```sql
SELECT 
    COUNT(*) AS total_rows,
    COUNT(order_id) AS non_null_orders,
    COUNT(*) - COUNT(customer_id) AS missing_customer_ids,
    COUNT(*) - COUNT(total_amount) AS missing_amounts,
    COUNT(*) - COUNT(created_at) AS missing_timestamps
FROM orders;
```

### C. Referential Integrity & Orphan Checks
Catch dangling records where foreign keys do not match primary records:

```sql
SELECT 
    o.id AS orphan_order_id, 
    o.customer_id, 
    o.created_at
FROM orders o
LEFT JOIN customers c ON o.customer_id = c.id
WHERE c.id IS NULL;
```
*Expected Result: 0 rows returned.*

### D. Value Range & Boundary Checks
Detect anomalies such as negative prices, future transaction timestamps, or illegal statuses:

```sql
SELECT 
    COUNT(*) AS anomaly_count,
    MIN(unit_price) AS min_price,
    MAX(unit_price) AS max_price,
    MIN(created_at) AS earliest_record,
    MAX(created_at) AS latest_record
FROM order_items
WHERE unit_price < 0 
   OR created_at > CURRENT_TIMESTAMP;
```

---

## 3. Cross-Database Reconciliation Checksums

When validating that data extracted matches the source or comparing data across replicas:

### PostgreSQL Checksum
```sql
SELECT md5(string_agg(id::text || ':' || amount::text, ',' ORDER BY id)) AS table_checksum
FROM payments;
```

### SQL Server Checksum
```sql
SELECT HASHBYTES('SHA2_256', 
    STRING_AGG(CONCAT(id, ':', amount), ',') WITHIN GROUP (ORDER BY id)
) AS table_checksum
FROM payments;
```

### SQLite Checksum
```sql
SELECT 
    COUNT(*) AS total_count,
    SUM(id) AS id_sum,
    ROUND(SUM(amount), 2) AS amount_sum
FROM payments;
```

---

## 4. Chunked Extraction with Keyset Pagination

Never use high-offset pagination (`LIMIT 500 OFFSET 100000`) for large data extractions, as the database engine must scan and discard all 100,000 preceding rows ($O(N)$).

### Recommended: Keyset Pagination ($O(\log N)$)
```sql
-- Batch 1:
SELECT id, sku, price, updated_at 
FROM products 
ORDER BY id ASC 
LIMIT 500;

-- Subsequent batches (using last seen ID):
SELECT id, sku, price, updated_at 
FROM products 
WHERE id > 500 
ORDER BY id ASC 
LIMIT 500;
```

---

## 5. Troubleshooting Data Defects & Remediation Workflow

When validation checks detect corrupted, duplicate, or orphaned records, **never make speculative, unverified `UPDATE` or `DELETE` edits directly in the live database**. Follow the empirical framework established by [`troubleshoot-and-fix`](file:///.github/skills/troubleshoot-and-fix/SKILL.md):

```
[1. Extract Defect Slices] ──> [2. Isolate in Scratch Testbed] ──> [3. 3-Attempt Circuit Breaker] ──> [4. Backport Verified Fix]
                                  (:memory: SQLite / Scratch)        (Max 3 Repair Hypotheses)
```

---

### A. The 3-Phase Data Troubleshooting Protocol

1. **Extract & Isolate Problematic Slices**:
   - Extract the anomalous rows identified by Section 2 (duplicates, orphans, negative values) into an isolated testbed (`scratch/repro/corrupt_data.json` or an in-memory SQLite database via `sql-connector`).
   - Leave the production database untouched and read-only.
2. **Formulate & Test Root-Cause Hypotheses in Isolation**:
   - **Hypothesis 1 (Ingestion / ETL Truncation)**: Did upstream services truncate strings, omit timezones, or mangle character encodings (e.g. mojibake, non-breaking spaces `\u00A0`)?
   - **Hypothesis 2 (Concurrency & Race Conditions)**: Did parallel workers perform uncoordinated inserts without unique constraints or transaction serialization?
   - **Hypothesis 3 (Schema Drift & Soft Constraints)**: Did historical data bypass application-level validation before a constraint was added?
3. **Respect the 3-Iteration Circuit Breaker**:
   - Adhere strictly to the [`troubleshoot-and-fix`](file:///.github/skills/troubleshoot-and-fix/SKILL.md) budget: test up to **3 repair hypotheses** against the isolated testbed.
   - If after 3 attempts the data reconciliation or deduplication cannot be validated with 100% certainty, **HALT IMMEDIATELY**.
   - Output the **Data Defect Escalation Summary** to the user. Do not attempt speculative bulk mutations.

---

### B. Safe Data Remediation Patterns

#### 1. Deduplication Without Data Loss
When duplicate surrogate or natural keys exist, use a CTE with `ROW_NUMBER()` to isolate duplicate instances while preserving the single most recent authoritative record:

```sql
-- Safe Deduplication Pattern (SQL Server / PostgreSQL / Oracle):
WITH RankedDuplicates AS (
    SELECT 
        id,
        user_email,
        updated_at,
        ROW_NUMBER() OVER (
            PARTITION BY user_email 
            ORDER BY updated_at DESC, id DESC
        ) AS row_num
    FROM users
)
-- Test in isolation first: verify row_num > 1 isolates exactly the duplicates:
SELECT * FROM RankedDuplicates WHERE row_num > 1;

-- Guarded delete (only run after verifying isolated harness):
DELETE FROM users 
WHERE id IN (
    SELECT id FROM RankedDuplicates WHERE row_num > 1
);
```

#### 2. Quarantine Orphan Records (Prevent Cascade Accidents)
Instead of executing destructive blanket deletes on orphaned child records, route them into a dedicated quarantine table for audit:

```sql
-- 1. Create Quarantine Table
CREATE TABLE quarantined_orphan_orders AS
SELECT o.*, CURRENT_TIMESTAMP AS quarantined_at, 'MISSING_CUSTOMER_ID' AS reason
FROM orders o
LEFT JOIN customers c ON o.customer_id = c.id
WHERE c.id IS NULL;

-- 2. Safely remove quarantined IDs with specific key boundaries:
DELETE FROM orders 
WHERE id IN (SELECT id FROM quarantined_orphan_orders);
```

#### 3. Defensive Type Casting & Error Trapping
Avoid query crashes caused by unexpected non-numeric or malformed date strings in legacy columns:

```sql
-- SQL Server: TRY_CAST returns NULL on failure instead of throwing error 245
SELECT 
    raw_id,
    TRY_CAST(raw_amount AS DECIMAL(10,2)) AS clean_amount,
    TRY_CONVERT(DATETIME2, raw_date, 126) AS clean_timestamp
FROM staging_raw_feed;

-- PostgreSQL 16+: Safe cast with fallback default
SELECT 
    raw_id,
    CASE 
        WHEN raw_amount ~ '^-?[0-9]+(\.[0-9]+)?$' THEN raw_amount::numeric 
        ELSE NULL 
    END AS clean_amount
FROM staging_raw_feed;

-- Oracle 12c R2+: DEFAULT ON CONVERSION ERROR
SELECT 
    TO_NUMBER(raw_amount DEFAULT NULL ON CONVERSION ERROR) AS clean_amount
FROM staging_raw_feed;
```

#### 4. Cleansing Non-Breaking Spaces & Control Characters
Hidden unicode whitespace (`\u00A0` / `CHAR(160)`) frequently causes string equality lookups to fail silently:

```sql
-- Cleans standard spaces, non-breaking spaces, tabs, and carriage returns:
UPDATE customers
SET clean_tax_id = TRIM(
    REPLACE(
        REPLACE(
            REPLACE(tax_id, CHAR(160), ' '), -- Non-breaking space
            CHAR(9), ' '                     -- Tab
        ), 
        CHAR(13), ''                         -- Carriage return
    )
)
WHERE tax_id IS NOT NULL;
```

---

### C. Data Defect Escalation Summary Template

When the 3-iteration circuit breaker trips during data troubleshooting, present this structured escalation summary:

```markdown
## 🛑 Data Troubleshooting Circuit Breaker: Out of Options Summary

### 1. Data Defect Baseline
- **Target Table**: `dbo.Orders` / `public.users`
- **Total Corrupted Records**: 4,210 rows out of 1,200,000 (0.35%)
- **Validation Failure**: Duplicate unique constraints / Unresolved orphan foreign keys.

### 2. Hypotheses Tested in Isolation
- **Attempt 1**: Tested deduplication partitioned by `email` keeping latest `updated_at`. Failed: Multiple records share identical timestamps with conflicting billing addresses.
- **Attempt 2**: Tested auto-healing customer foreign keys by fuzzy-matching company name. Failed: 18% ambiguous matches with $> 1$ candidate customer.
- **Attempt 3**: Tested routing unmatched records to default system tenant account. Failed: Violates audit compliance policy requiring explicit customer assignment.

### 3. Current Working Tree & Sandbox Status
- Production tables remain untouched (0 live mutations executed).
- Isolated reproduction fixtures preserved at `scratch/repro/data_defect_orders.sql`.

### 4. Recommended Next Steps for Human Domain Expert
- Determine authoritative precedence rule for duplicate records with identical timestamps.
- Provide business rule for orphan order re-attribution or approve archiving to quarantine.
```

---

## 6. References

- [Troubleshoot and Fix Skill](file:///.github/skills/troubleshoot-and-fix/SKILL.md) — 3-iteration circuit breaker, isolated testbeds, and root-cause verification.
- [SQL Troubleshooting & Firewall Resolution Guide](file:///.github/skills/sql-executor/troubleshooting/troubleshooting-and-firewall.md) — Resolving query syntax errors, timeouts, and guardrail blocks.


