---
name: rag-pipeline
description: End-to-end architectural and engineering guidance for designing, building, and evaluating production Retrieval-Augmented Generation (RAG) pipelines. Covers document ingestion & layout preservation, structure-aware & contextual chunking, Matryoshka embeddings, vector databases (PostgreSQL pgvector HNSW, Qdrant, Milvus, SQLite FTS5), hybrid search (BM25 + dense vectors + Reciprocal Rank Fusion), cross-encoder reranking, query transformations (HyDE, multi-query, step-back), grounded generation with inline citations, Agentic & Corrective RAG, RAG Triad & offline IR evaluation (Recall@K, MRR, NDCG@K), 5-layer RAG testing strategies, and document-level ACL security. Use when asked to "rag-pipeline", "rag-pipeline-creator", "build rag pipeline", "create rag pipeline", "design rag architecture", "chunking strategy", "hybrid search rag", "vector database indexing", "reranking pipeline", "agentic rag", "evaluate rag pipeline", "rag testing strategy", "test rag pipeline", or "rag grounding".
version: 1.1.0
---

# RAG Pipeline Skill

You are a Principal AI & Search Systems Architect specializing in production **Retrieval-Augmented Generation (RAG)** pipelines—spanning document parsing, chunking, embedding models, vector/lexical indexing, hybrid retrieval, cross-encoder reranking, grounded generation, and information retrieval (IR) evaluation.

---

## Guiding Principles & Architectural Heuristics

1. **Hybrid Search by Default (`BM25` + Dense + `RRF`)**: Dense embeddings capture semantic paraphrases but miss exact identifiers (SKUs, error codes, function names, acronyms). Combine sparse/lexical retrieval (`BM25` / `tsvector`) with dense vector search via **Reciprocal Rank Fusion (`RRF`)**.
2. **Structure-Aware & Contextual Chunking**: Never slice documents at blind fixed character offsets when structural boundaries (Markdown headings, HTML sections, code AST nodes, table rows) exist. Prepend succinct document/section context before embedding and lexical indexing.
3. **Two-Stage Retrieval (`Recall` $\to$ `Rerank`)**: Retrieve a broad candidate pool ($N = 30\text{--}100$) with fast bi-encoders + BM25, then rescore `(query, chunk)` pairs jointly using a Cross-Encoder or late-interaction reranker to pass only the top $K = 4\text{--}10$ high-precision chunks to the LLM.
4. **Strict Pre-Retrieval Authorization**: Enforce tenant isolation and document-level ACLs (`WHERE tenant_id = ... AND acl_groups && ...`) *inside* the vector/hybrid query filter—never retrieve unauthorized chunks and attempt to filter them post-LLM.
5. **Measure Retrieval Before Tuning Prompts**: Never blame the LLM prompt for retrieval failures. Quantify offline retrieval quality (`Recall@K`, `MRR`, `NDCG@K`) first, then audit claim-level groundedness using [`llm-as-judge`](file:///.github/skills/llm-as-judge/SKILL.md).

---

## End-to-End 5-Stage RAG Architecture

```
┌───────────────────────────┐     ┌──────────────────────────────────┐     ┌──────────────────────────────────┐
│ 1. Ingestion & Parsing    │ ──► │ 2. Chunking & Context Enrichment │ ──► │ 3. Embedding & Hybrid Indexing   │
│  • Layout/table preserve  │     │  • Markdown/AST/Parent-Child     │     │  • Dense vector (MRL / halfvec)  │
│  • PII/secret redaction   │     │  • Contextual prefix prepend     │     │  • Sparse/BM25 (GIN tsvector)    │
│  • SHA-256 delta hashing  │     │  • Tenant & ACL metadata attach  │     │  • HNSW index + iterative scan   │
└───────────────────────────┘     └──────────────────────────────────┘     └─────────────────┬────────────────┘
                                                                                             │
┌───────────────────────────┐     ┌──────────────────────────────────┐                       │
│ 5. Grounded Generation    │ ◄── │ 4. Retrieval, RRF & Reranking    │ ◄─────────────────────┘
│  • XML source delimiters  │     │  • Query rewrite / step-back     │
│  • Inline [doc_i] cites   │     │  • Pre-filter tenant & ACLs      │
│  • Abstain below tau      │     │  • RRF(k=60) + Cross-Encoder     │
│  • RAG Triad & IR eval    │     │  • "Lost in the Middle" reorder  │
└───────────────────────────┘     └──────────────────────────────────┘
```

---

## When to Use Which RAG Pattern & Store (Agent Decision Matrix)

| Requirement / Workload | Optimal Selection | Anti-Pattern / What to Avoid | Rationale |
|---|---|---|---|
| **General enterprise docs, wikis, & support KBs** | **Hybrid Search (`BM25` + Dense + `RRF`) + Cross-Encoder Reranker** | Dense-only Top-5 cosine search | Hybrid search catches exact error codes/IDs while reranking eliminates noisy false positives before the LLM context window. |
| **Long technical manuals where chunks lose surrounding context** | **Parent-Child (Small-to-Big) + Contextual Retrieval** | Isolated 500-token slices with no section headers | Embeds crisp 256-token child chunks for high vector precision while returning 1,024-token parent sections for full LLM reasoning. |
| **Existing PostgreSQL stack (< 5M vectors)** | **PostgreSQL + `pgvector` (`halfvec` HNSW) + `tsvector` GIN** | Spinning up a separate distributed vector cluster immediately | Single ACID database keeps documents, ACLs, relational joins, BM25, and vectors consistent with zero sync drift. |
| **High-scale (> 10M vectors), multi-tenant quantization, sub-20ms SLA** | **Dedicated Vector DB (`Qdrant`, `Milvus`)** with Binary/Scalar Quantization | Unindexed `IVFFlat` or brute-force exact scans | Dedicated engines provide payload-aware HNSW graphs, memory-mapped segments, and quantized two-phase rescoring. |
| **Local CLI / desktop / zero-infra edge search** | **SQLite (`FTS5` BM25 + `sqlite-vec`)** | Running Docker vector clusters for single-user local apps | Zero-ops single-file persistence with fast lexical + vector fusion. |
| **Multi-hop ambiguity or stale/low-confidence retrievals** | **Corrective RAG (CRAG) / Adaptive Query Router** | Blindly stuffing low-scoring chunks into generation | Grades retrieved relevance first, rewrites queries or routes to structured SQL ([`sql-connector`](file:///.github/skills/sql-connector/SKILL.md)) when needed. |
| **Global corpus-wide synthesis ("Summarize themes across 5k docs")** | **GraphRAG / Hierarchical Map-Reduce Summaries** | Standard Top-K chunk retrieval | Top-K retrieval cannot aggregate global themes across thousands of documents; use GraphRAG *only* for global/multi-hop synthesis. |

---

## Over-Engineering Self-Check (Anti-Bloat Guardrail)

Before generating RAG infrastructure or application code, audit your design against these anti-bloat heuristics:

1. **No Premature GraphRAG**: Do not build an expensive LLM entity-extraction knowledge graph pipeline when Hybrid Search + Cross-Encoder Reranking satisfies factual QA.
2. **No Unnecessary Vector Cluster Sprawl**: If the application already runs PostgreSQL and expects $< 5\text{M}$ chunks, use `pgvector` + `tsvector` instead of introducing a separate vector store and dual-write synchronization pipeline.
3. **Avoid Deep Framework Wrapper Bloat**: Do not wrap a straightforward 50-line embed-query-rerank-stream flow in 6 layers of `BaseRetriever` / `Chain` abstractions. Write direct, inspectable SDK and SQL calls.
4. **Skip HyDE on Latency-Sensitive Paths**: Hypothetical Document Embeddings (HyDE) adds an extra LLM generation round-trip before search; reserve it for ambiguous exploratory queries, not real-time autocomplete or known-entity lookup.
5. **Direct Tool Audit**: Run [`detect-overengineering`](file:///.github/skills/detect-overengineering/SKILL.md) on generated pipeline modules to verify low accidental complexity.

---

## CLI Evaluation & Simulation Utility (`scripts/rag-pipeline-eval.py`)

Test chunking boundaries, simulate BM25 + dense vector RRF fusion, and compute offline IR metrics (`Recall@K`, `Precision@K`, `HitRate@K`, `MRR`, `NDCG@K`) using the repository virtual environment:

```powershell
# Simulate structure-aware Markdown chunking with deterministic SHA-256 IDs
.\.venv\Scripts\python.exe .github/skills/rag-pipeline/scripts/rag-pipeline-eval.py chunk `
    --strategy markdown --input .github/skills/rag-pipeline/SKILL.md --chunk-size 600 --overlap 80

# Compare BM25 vs Dense vs Hybrid RRF (k=60) rankings on a query
.\.venv\Scripts\python.exe .github/skills/rag-pipeline/scripts/rag-pipeline-eval.py hybrid-search `
    --query "ERR_CONNECTION_REFUSED pgvector HNSW index recall" --top-k 5

# Compute offline IR metrics (Recall@K, Precision@K, HitRate@K, MRR, NDCG@K)
.\.venv\Scripts\python.exe .github/skills/rag-pipeline/scripts/rag-pipeline-eval.py evaluate --demo --k 5
```

*(On POSIX, substitute `.\.venv\Scripts\python.exe` with `.venv/bin/python`).*

---

## 5-Layer RAG Testing Strategy (`scripts/rag-testing-strategy.py`)

Validate ingestion, access controls, retrieval regressions, grounding, and prompt injection defenses across five automated layers before shipping pipeline changes:

| Layer | Verification Target | Failure Mode Prevented | CI Quality Gate |
|---|---|---|---|
| **1. Ingestion, Chunking & PII** | Deterministic `SHA-256` chunk IDs, max character/token bounds, Markdown breadcrumbs, pre-indexing secret scrubbing | Duplicate index rows, severed section headers, secrets/PII baked into embeddings | `0` unredacted secrets (`[REDACTED_*]`), deterministic chunk IDs |
| **2. Tenant & ACL Pre-Filtering** | `tenant_id` and `acl_groups` enforced *inside* retrieval before BM25/vector scoring | Cross-tenant leakage or RBAC bypass via exact keyword match | `0` cross-tenant & `0` unauthorized group leaks |
| **3. Hybrid IR Quality Gate** | Golden query suite scored with `Recall@K`, `Precision@K`, `MRR`, and `NDCG@K` | Silent recall regressions after chunk size or embedding changes | `Recall@3 >= 0.90`, `MRR >= 0.80`, `NDCG@3 >= 0.85` |
| **4. Grounding & Abstention** | Relevance threshold $\tau$ abstention (`insufficient_evidence`), valid `[doc_id]` citations, claim support ratio | Hallucinated answers on low-relevance hits or phantom citations | `0` phantom citations, abstention enforced below $\tau$ |
| **5. Prompt Injection Defense** | Instruction-override/exfiltration regex detection and XML `<sources>` escaping | Retrieved tickets/docs hijacking system instructions | Adversarial rules flagged & payload HTML-escaped |

Run the sample 5-layer test harness using the repository virtual environment:

```powershell
# Run all 5 testing layers and print a pass/fail summary table
.\.venv\Scripts\python.exe .github/skills/rag-pipeline/scripts/rag-testing-strategy.py --mode report

# Emit machine-readable JSON for CI quality gates
.\.venv\Scripts\python.exe .github/skills/rag-pipeline/scripts/rag-testing-strategy.py --mode report --format json

# Run the standard unittest.TestCase suite (RagPipelineTestingStrategyTests)
.\.venv\Scripts\python.exe .github/skills/rag-pipeline/scripts/rag-testing-strategy.py --mode unittest
```

---

## Knowledge Modules

Load only the modules relevant to the task:

- [Document Ingestion, Parsing & Chunking Strategies](ingestion-and-chunking/chunking-and-parsing-strategies.md) — Layout/table preservation, recursive/Markdown/AST/Parent-Child/Contextual chunking, and SHA-256 idempotent delta ingestion.
- [Embeddings, Quantization & Vector Database Indexing](embeddings-and-vectordbs/embeddings-and-vector-stores.md) — MRL dimension truncation, asymmetric prefixes, HNSW/IVFFlat tuning, quantization, and production PostgreSQL `pgvector` schemas.
- [Hybrid Search, Query Transformation & Reranking](retrieval-and-reranking/hybrid-search-and-reranking.md) — BM25 + Dense Reciprocal Rank Fusion (`RRF`), PostgreSQL CTE queries, multi-query/step-back/HyDE, Cross-Encoder reranking, and context reordering.
- [Grounded Generation, Streaming APIs & Agentic RAG](generation-and-agentic-rag/grounded-generation-and-agentic-rag.md) — Strict citation prompts, Pydantic v2 output contracts, abstention thresholds, Corrective/Self-RAG routers, FastAPI SSE streaming, and caching.
- [RAG Evaluation, IR Metrics & Security Boundaries](evaluation-and-security/rag-evaluation-and-security.md) — RAG Triad, `Recall@K`/`MRR`/`NDCG@K` formulas, document-level ACL pre-filtering, indirect prompt injection defense, PII scrubbing, and the 5-Layer Automated RAG Testing Strategy.

---

## Integration with Repository Skills

- **[LLM-as-Judge](file:///.github/skills/llm-as-judge/SKILL.md)**: Use Pattern 3 (Claim-Level Hallucination & RAG Grounding Audit) to score faithfulness (`SUPPORTED` / `CONTRADICTED` / `UNSUPPORTED`) against retrieved chunks.
- **[SQL Executor](file:///.github/skills/sql-executor/SKILL.md)** & **[SQL Connector](file:///.github/skills/sql-connector/SKILL.md)**: Inspect `pgvector` HNSW/GIN execution plans and safely query structured relational stores for hybrid SQL+RAG routers.
- **[Python API Writer](file:///.github/skills/python-api-writer/SKILL.md)**: Build non-blocking FastAPI `StreamingResponse` SSE endpoints with lifespan connection pool management.
- **[Caching & Queues Reviewer](file:///.github/skills/caching-queues-reviewer/SKILL.md)**: Design Redis embedding caches, async ingestion worker queues (`Arq`/`Celery`), and rate limits.
- **[Researcher PoC Tester](file:///.github/skills/researcher-poc-tester/SKILL.md)**: Benchmark competing chunk sizes, `ef_search` settings, or reranker latency percentiles (P50/P95/P99).
- **[Save Memory](file:///.github/skills/save-memory/SKILL.md)** & **[Load Memory](file:///.github/skills/load-memory/SKILL.md)**: Persist embedding model choices, index dimensions, and retrieval evaluation baselines in `.project-memory/memory.db` (`ledger` & `journal`).

