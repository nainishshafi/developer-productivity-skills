# Embeddings, Quantization & Vector Database Indexing

Choosing the wrong embedding dimension, overflowing `max_seq_length`, or misconfiguring HNSW/filter settings silently degrades retrieval recall without raising runtime exceptions.

---

## 1. Embedding Model Discipline

### Critical Pitfalls to Guard Against
1. **Silent Context Truncation**: Many dense encoders have a `max_seq_length` of 512 tokens (some newer models support 8,192). Any tokens past the limit are silently dropped. Always verify chunk token length $\le 0.85 \times \text{model\_max\_tokens}$ using the model's actual tokenizer (`tiktoken` or HuggingFace tokenizer).
2. **Asymmetric Query/Document Prefixes**: Models like `nomic-embed-text`, `bge-*`, and `e5-*` require distinct prefixes (`search_query: ...` vs `search_document: ...`, or `query: ...` vs `passage: ...`). Omitting or mismatching prefixes measurably drops `NDCG@10`.
3. **Embedding Model Version Lock**: Never mix embeddings from different models or incompatible dimensions inside the same vector index. Persist `embedding_model` and `dimensions` in the index metadata (and in `project-memory` `ledger`); re-index into a new column/collection during model upgrades.

### Matryoshka Representation Learning (MRL) & L2 Renormalization
Models trained with MRL pack coarse semantic signal into earlier vector dimensions. You can truncate a 1536-d or 3072-d vector down to `512` or `256` dimensions to cut RAM/disk footprint by $3\text{x}\text{--}6\text{x}$ with minimal recall loss—**provided you L2-renormalize after slicing**:

```python
import math


def truncate_mrl_vector(vec: list[float], target_dim: int) -> list[float]:
    """Slice an MRL embedding to target_dim and renormalize to unit L2 length."""
    if target_dim <= 0 or target_dim > len(vec):
        raise ValueError(f"target_dim ({target_dim}) must be in 1..{len(vec)}")
    sliced = vec[:target_dim]
    norm = math.sqrt(sum(x * x for x in sliced))
    if norm == 0.0:
        return sliced
    return [x / norm for x in sliced]
```

---

## 2. Distance Metrics & Quantization

| Metric | pgvector Operator | When to Use | Note |
|---|---|---|---|
| **Cosine Distance** | `<=>` | Default for normalized and unnormalized text embeddings | Measures angle ($1 - \cos\theta$). |
| **Negative Inner Product** | `<#>` | Unit L2-normalized embeddings (`||v|| == 1`) | Fastest compute; equivalent to Cosine ordering on unit vectors. |
| **Euclidean (L2)** | `<->` | Embeddings trained specifically for L2 distance | Equivalent to Cosine ordering when all vectors are unit-normalized. |

### Vector Quantization Trade-Offs (Memory vs. Recall)
- **`FP32` (4 bytes/dim)**: Baseline full precision. At 1M × 1536 dims $\approx 6.14\text{ GB}$ raw vectors (often $10\text{--}12\text{ GB}$ with HNSW graph edges).
- **`FP16` / `BF16` (`pgvector` `halfvec`, 2 bytes/dim)**: 50% RAM savings with virtually zero (< 0.1%) recall degradation. **Recommended default for `pgvector`**.
- **Scalar Quantization (`SQ8` / `int8`, 1 byte/dim)**: 75% RAM savings, ~98–99% recall retention.
- **Binary Quantization (`BQ`, 1 bit/dim)**: 32x RAM savings. Always pair with **oversampling + full-precision rescoring** (retrieve Top-100 in binary Hamming distance, rescore with stored `FP16`/`FP32` vectors to pick Top-20).

---

## 3. Vector Index Selection & Tuning

| Store / Index | Strengths | Weaknesses / Traps | Recommended Config |
|---|---|---|---|
| **PostgreSQL `pgvector` `HNSW`** | ACID transactions, relational joins, zero sync lag, supports `halfvec` (up to 4,000 dims) and `tsvector` hybrid queries | Single-node RAM constraints above ~5M–10M vectors | `m = 16`, `ef_construction = 64` (or `128` for high recall); query `hnsw.ef_search = 64–100` |
| **PostgreSQL `pgvector` `IVFFlat`** | Faster index build, lower RAM than HNSW | Requires non-empty training data (`lists`), recall degrades as data distribution shifts | Use HNSW instead unless index build memory is severely constrained |
| **Qdrant / Milvus** | Native payload-filtered HNSW, on-disk mmap segments, SQ8/BQ quantization, distributed sharding | Extra service to deploy, backup, and keep consistent with primary DB | Use when $> 5\text{M}$ vectors or strict multi-region low-latency SLAs apply |
| **SQLite (`FTS5` + `sqlite-vec`)** | Embedded, zero external dependencies, portable single file | Single-writer concurrency | Ideal for local developer tools, desktop apps, and unit/eval harnesses |

### Solving the Pre-Filter vs. Post-Filter Recall Collapse
In naive HNSW queries with selective metadata filters (`WHERE tenant_id = 'acme'`), HNSW traverses the global graph for Top-$K$ neighbors and applies `WHERE` *afterward*—often returning 0 or 2 results instead of $K = 20$!

**Fixes:**
- **`pgvector` $\ge 0.8.0$**: Enable iterative index scanning inside the transaction:
  ```sql
  BEGIN;
  SET LOCAL hnsw.iterative_scan = relaxed_order;
  SET LOCAL hnsw.max_scan_tuples = 20000;
  SELECT id, content FROM rag_chunks
  WHERE tenant_id = 'acme'
  ORDER BY embedding <=> $1::halfvec(1024)
  LIMIT 20;
  COMMIT;
  ```
- **Qdrant**: Uses **Filterable HNSW** automatically (adds intra-tenant graph links when payload indexes exist on `tenant_id` and `acl_groups`).
- **Low-Cardinality Tenant Partitioning**: In PostgreSQL, partition `rag_chunks` by `LIST (tenant_id)` or `HASH (tenant_id)` for large multi-tenant tables so each tenant queries a tight, isolated HNSW index.

---

## 4. Production PostgreSQL `pgvector` Schema (Hybrid-Ready)

```sql
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE rag_chunks (
    chunk_id       TEXT PRIMARY KEY,
    doc_id         TEXT NOT NULL,
    doc_version    TEXT NOT NULL,
    tenant_id      TEXT NOT NULL,
    acl_groups     TEXT[] NOT NULL DEFAULT ARRAY['public'],
    chunk_index    INTEGER NOT NULL,
    title          TEXT NOT NULL,
    source_uri     TEXT NOT NULL,
    content        TEXT NOT NULL,
    content_hash   TEXT NOT NULL,
    metadata       JSONB NOT NULL DEFAULT '{}'::jsonb,
    embedding      halfvec(1024) NOT NULL,
    tsv            tsvector GENERATED ALWAYS AS (
                       setweight(to_tsvector('english', coalesce(title, '')), 'A') ||
                       setweight(to_tsvector('english', coalesce(content, '')), 'B')
                   ) STORED,
    updated_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Tenant + document lookup & tombstone cleanup
CREATE INDEX idx_rag_chunks_doc ON rag_chunks (tenant_id, doc_id, doc_version);

-- ACL array containment index
CREATE INDEX idx_rag_chunks_acl ON rag_chunks USING GIN (acl_groups);

-- Full-text lexical index (BM25/ts_rank_cd candidate generation)
CREATE INDEX idx_rag_chunks_tsv ON rag_chunks USING GIN (tsv);

-- HNSW dense vector index using halfvec cosine distance
CREATE INDEX idx_rag_chunks_hnsw ON rag_chunks
    USING hnsw (embedding halfvec_cosine_ops)
    WITH (m = 16, ef_construction = 64);
```

