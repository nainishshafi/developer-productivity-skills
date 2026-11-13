# Hybrid Search, Query Transformation & Reranking

Pure vector similarity fails on exact identifiers (`ERR_CONNECTION_REFUSED`, `CVE-2024-3094`, SKU codes, symbol names). Pure BM25 lexical search fails on synonyms and conceptual phrasing (*"pod killed due to memory limit"* vs *"OOMKilled exit code 137"*). Combining both with **Reciprocal Rank Fusion (`RRF`)** and a **Cross-Encoder Reranker** resolves both failure modes.

---

## 1. Reciprocal Rank Fusion (`RRF`)

`RRF` fuses ranked lists from heterogeneous scorers (whose raw cosine vs. BM25 scores live on incompatible scales) using only their rank positions:

$$\text{RRF\_Score}(d) = \sum_{m \in \{\text{dense}, \text{bm25}\}} \frac{w_m}{k + \text{rank}_m(d)}$$

- Standard smoothing constant: $k = 60$ (prevents rank-1 outliers from dominating while rewarding documents appearing in *both* result lists).
- Typical weights: $w_{\text{dense}} = 0.5, w_{\text{bm25}} = 0.5$ (tune toward $0.65 / 0.35$ for conceptual QA or $0.35 / 0.65$ for code/error-log search).

### Production PostgreSQL Hybrid Search Query (`pgvector` + `tsvector` + `RRF`)

```sql
WITH params AS (
    SELECT
        $1::halfvec(1024) AS q_vec,
        websearch_to_tsquery('english', $2) AS q_ts,
        $3::text AS tenant_id,
        $4::text[] AS user_groups,
        60.0 AS rrf_k
),
dense_candidates AS (
    SELECT
        c.chunk_id,
        ROW_NUMBER() OVER (ORDER BY c.embedding <=> p.q_vec) AS dense_rank
    FROM rag_chunks c, params p
    WHERE c.tenant_id = p.tenant_id
      AND c.acl_groups && p.user_groups
    ORDER BY c.embedding <=> p.q_vec
    LIMIT 50
),
lexical_candidates AS (
    SELECT
        c.chunk_id,
        ROW_NUMBER() OVER (ORDER BY ts_rank_cd(c.tsv, p.q_ts) DESC) AS bm25_rank
    FROM rag_chunks c, params p
    WHERE c.tenant_id = p.tenant_id
      AND c.acl_groups && p.user_groups
      AND c.tsv @@ p.q_ts
    ORDER BY ts_rank_cd(c.tsv, p.q_ts) DESC
    LIMIT 50
),
fused AS (
    SELECT
        COALESCE(d.chunk_id, l.chunk_id) AS chunk_id,
        d.dense_rank,
        l.bm25_rank,
        COALESCE(0.5 / (60.0 + d.dense_rank), 0.0)
          + COALESCE(0.5 / (60.0 + l.bm25_rank), 0.0) AS rrf_score
    FROM dense_candidates d
    FULL OUTER JOIN lexical_candidates l ON d.chunk_id = l.chunk_id
)
SELECT
    c.chunk_id,
    c.doc_id,
    c.title,
    c.source_uri,
    c.content,
    f.dense_rank,
    f.bm25_rank,
    f.rrf_score
FROM fused f
JOIN rag_chunks c ON c.chunk_id = f.chunk_id
ORDER BY f.rrf_score DESC
LIMIT 30;
```

*(Note: Execute `SET LOCAL hnsw.iterative_scan = relaxed_order;` inside the transaction when tenant filters are highly selective.)*

### Python RRF Helper

```python
def reciprocal_rank_fusion(
    ranked_lists: list[tuple[list[str], float]],
    k: int = 60,
) -> list[tuple[str, float]]:
    """Fuse multiple ordered ID lists with weights using Reciprocal Rank Fusion."""
    scores: dict[str, float] = {}
    for doc_ids, weight in ranked_lists:
        for rank_idx, doc_id in enumerate(doc_ids, start=1):
            scores[doc_id] = scores.get(doc_id, 0.0) + (weight / (k + rank_idx))
    return sorted(scores.items(), key=lambda item: item[1], reverse=True)
```

---

## 2. Query Transformation Patterns

| Pattern | Mechanism | When to Use | When to Skip |
|---|---|---|---|
| **Coreference Rewrite** | Rewrite *"How do I fix it on Windows?"* using prior turn context into *"How do I fix pgvector HNSW build failure on Windows?"* | **Always** in multi-turn conversational RAG | Single-turn standalone API queries |
| **Structured Metadata Extraction** | Parse dates, product names, or tenants (`"last quarter's SOC2 report"`) into deterministic SQL/payload filters | Queries mixing temporal/categorical constraints with semantic intent | Purely unstructured prose queries |
| **Multi-Query Expansion** | Generate 2–3 lexical/semantic query variants in parallel and fuse via RRF | Ambiguous or underspecified user questions | Latency-critical (< 100ms) search endpoints |
| **Step-Back Prompting** | Ask a broader foundational query alongside the specific query | Deep debugging or root-cause synthesis needing underlying rules | Direct fact/definition lookup |
| **HyDE (Hypothetical Doc)** | Generate a hypothetical answer and embed *that* instead of the short user question | Vocabulary mismatch between terse user queries and formal manuals | Queries containing exact IDs/symbols, or strict latency budgets |

---

## 3. Two-Stage Retrieval & Cross-Encoder Reranking

Bi-encoders compress an entire chunk into a single vector *before* seeing the query, losing fine-grained token-to-token interactions. A **Cross-Encoder** (or **ColBERT** late-interaction scorer) processes `[CLS] query [SEP] chunk [SEP]` jointly with full cross-attention.

### Recommended Funnel Dimensions
1. **Stage 1 — Hybrid Candidate Generation (`BM25` + Dense + `RRF`)**: Retrieve top $N = 30\text{--}60$ chunks (~5–25 ms).
2. **Stage 2 — Cross-Encoder Reranking**: Score top $N$ chunks in one batched forward pass (e.g., `bge-reranker-v2-m3`, `ms-marco-MiniLM`, or hosted rerank API) (~30–120 ms) and retain top $K = 4\text{--}8$ chunks exceeding minimum relevance threshold $\tau$.
3. **Deduplication & Parent Expansion**: Collapse overlapping child chunks from the same parent section before passing to the LLM.

### Mitigating "Lost in the Middle" Context Degradation
LLMs attend more strongly to tokens at the **beginning** and **end** of the prompt context than tokens buried in the middle.
- **Reorder Top-$K$ Chunks**: Place the highest-scored chunk (`rank 1`) first, `rank 2` last, `rank 3` second, `rank 4` second-to-last (`[1, 3, 5, ..., 6, 4, 2]`), or group chunks chronologically/by document when preserving narrative continuity matters more.

