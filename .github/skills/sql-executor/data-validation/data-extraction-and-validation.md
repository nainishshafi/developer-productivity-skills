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
