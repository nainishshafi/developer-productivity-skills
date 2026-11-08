# PostgreSQL Specialized Indexing Architecture Guide

Comprehensive reference for Generalized Inverted Indexes (GIN), Generalized Search Trees (GiST), Block Range Indexes (BRIN), JSONB optimization, and trigram fuzzy matching in PostgreSQL.

---

## 1. PostgreSQL Index Engine Selection Matrix

| Index Type | Underlying Structure | Target Column Types / Operators | Space Footprint | Ideal Use Cases |
|:---|:---|:---|:---:|:---|
| **B-Tree** (Default) | Self-balancing search tree | `=`, `<`, `<=`, `>`, `>=`, `BETWEEN`, `IN` | Moderate | Primary keys, surrogate keys, unique constraints, sorted ranges. |
| **GIN** | Inverted index (term $\to$ row pointer list) | JSONB (`@>`, `?`), Arrays (`@>`, `&&`), `tsvector` (`@@`), Trigrams (`ILIKE '%x%'`) | Large | JSONB document attributes, tag search, full-text search, wildcard text matching. |
| **GiST** | Lossy, height-balanced tree | Range types (`&&`, `@>`), PostGIS geometries (`&&`, `ST_DWithin`), KNN nearest-neighbor (`<->`) | Moderate | Scheduling reservations (exclusion constraints), spatial lookups, nearest-neighbor. |
| **BRIN** | Block range metadata summary (min/max per 128 pages) | Append-only sequential columns (`created_at`, serial IDs) | **Tiny (< 1% of B-Tree)** | Multi-gigabyte / terabyte append-only time-series or audit tables. |

---

## 2. GIN Indexing for JSONB Documents

PostgreSQL offers two distinct GIN operator classes for indexing `JSONB` data:

### A. Default Operator Class (`jsonb_ops`)
Indexes every individual key, value, and nested path within the JSON document:

```sql
CREATE INDEX idx_users_metadata_gin 
ON users USING gin (metadata);

-- Supported Operators:
-- Containment:
SELECT * FROM users WHERE metadata @> '{"role": "admin", "active": true}';

-- Key Existence:
SELECT * FROM users WHERE metadata ? 'tax_id';

-- Any/All Keys:
SELECT * FROM users WHERE metadata ?| array['is_vip', 'is_employee'];
```

### B. Path Operator Class (`jsonb_path_ops`) — *HIGH EFFICIENCY*
Hashes the complete path and value together into a single token (e.g. `hash("address.city.seattle")`):

```sql
CREATE INDEX idx_users_metadata_path_gin 
ON users USING gin (metadata jsonb_path_ops);

-- Supported Operator (Containment ONLY):
SELECT * FROM users WHERE metadata @> '{"status": "APPROVED", "tier": "GOLD"}';
```
> [!TIP]
> **Heuristic**: If queries only use the containment operator (`@>`), always prefer `jsonb_path_ops`. It produces an index that is **2x to 3x smaller** and provides faster lookups than `jsonb_ops`.

---

## 3. Trigram Indexing (`pg_trgm`) for Wildcard & Fuzzy Search

Standard B-Tree indexes cannot accelerate queries with leading wildcards (`WHERE name LIKE '%john%'`), forcing full sequential scans ($O(N)$). The `pg_trgm` extension breaks strings into 3-character slices and indexes them using GIN:

```sql
-- Enable trigram extension
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Create GIN trigram index
CREATE INDEX idx_customers_name_trgm 
ON customers USING gin (name gin_trgm_ops);

-- Now executes via Bitmap Index Scan (O(log N)):
SELECT id, name, email 
FROM customers 
WHERE name ILIKE '%acme aerospace%';

-- Also accelerates regex matches:
SELECT id, name 
FROM customers 
WHERE name ~* 'acme[0-9]+';
```

---

## 4. GiST & Exclusion Constraints (Zero Race Conditions)

Prevent overlapping date ranges or room bookings at the database engine level without application-level race conditions:

```sql
CREATE EXTENSION IF NOT EXISTS btree_gist;

CREATE TABLE room_reservations (
    id SERIAL PRIMARY KEY,
    room_number INT NOT NULL,
    reservation_period TSRANGE NOT NULL,
    
    -- Excludes rows where room_number is equal AND periods overlap (&&):
    CONSTRAINT no_overlapping_reservations 
    EXCLUDE USING gist (
        room_number WITH =, 
        reservation_period WITH &&
    )
);

-- Insert succeeds:
INSERT INTO room_reservations (room_number, reservation_period)
VALUES (101, tsrange('2026-06-01 10:00', '2026-06-01 12:00'));

-- Concurrent insert fails with exclusion constraint violation:
INSERT INTO room_reservations (room_number, reservation_period)
VALUES (101, tsrange('2026-06-01 11:00', '2026-06-01 13:00'));
```

---

## 5. BRIN (Block Range Index) for Big Data & Time-Series

When logging millions of rows where `created_at` or `id` increases monotonically:

```sql
-- A 100M-row table: B-Tree index would consume ~2.5 GB RAM.
-- BRIN consumes ~5 MB RAM (99.8% memory savings):
CREATE INDEX idx_audit_logs_brin 
ON audit_logs USING brin (created_at);

-- Engine scans only block ranges whose min/max spans the target date:
SELECT * FROM audit_logs 
WHERE created_at BETWEEN '2026-05-01' AND '2026-05-02';
```

---

## 6. Index Maintenance: Unused Index Auditing & Concurrent Reindexing

### Finding Unused Indexes (Eliminating Write Overhead)
```sql
SELECT 
    schemaname, 
    relname AS table_name, 
    indexrelname AS index_name, 
    idx_scan AS number_of_scans, 
    pg_size_pretty(pg_relation_size(indexrelid)) AS index_size
FROM pg_stat_user_indexes
WHERE idx_scan = 0 
  AND indexrelname NOT LIKE '%_pkey'
ORDER BY pg_relation_size(indexrelid) DESC;
```

### Zero-Downtime Index Rebuilding
Standard `REINDEX` acquires an exclusive lock blocking all read and write traffic. Always use `CONCURRENTLY`:
```sql
REINDEX INDEX CONCURRENTLY idx_users_metadata_gin;
```

