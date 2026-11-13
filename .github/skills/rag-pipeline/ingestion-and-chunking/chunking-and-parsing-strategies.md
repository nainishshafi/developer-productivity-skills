# Document Ingestion, Parsing & Chunking Strategies

Retrieval quality is bounded by ingestion quality. If tables are shattered across chunks, code blocks lose function signatures, or headings are stripped from paragraphs, even the strongest embedding model and LLM will fail to retrieve or reason accurately.

---

## 1. Document Parsing & Layout Preservation

### Structural Rules by Format
| Source Format | Recommended Extraction Strategy | Common Failure Mode |
|---|---|---|
| **PDF (Text / Multi-Column)** | Layout-aware parser (`PyMuPDF4LLM`, `Docling`, `Unstructured`) preserving reading order & headings | Naive `pypdf` reading across two columns horizontally, merging unrelated sentences |
| **PDF (Scanned / Complex Tables)** | OCR / Vision-Language extraction outputting structured Markdown tables | Flattening table cells into space-separated text, destroying row-column alignment |
| **HTML / Web Pages** | Strip nav/footer/scripts (`trafilatura` / `readability`) $\to$ clean Semantic Markdown | Indexing boilerplate navigation menus, cookie banners, and CSS class noise |
| **Markdown / Docs** | Parse heading hierarchy (`H1 > H2 > H3`) and preserve fenced code blocks intact | Splitting inside a fenced code block or separating a heading from its paragraph |
| **Source Code** | Tree-sitter / Python `ast` symbol extraction (class, function, docstring, signature) | Arbitrary line slicing cutting a function body away from its signature and imports |

### Table Serialization Best Practices
Never split a Markdown or HTML table mid-row without repeating the header row:
- **Small tables (< 500 tokens)**: Keep the entire table intact in a single chunk with its caption/preceding heading.
- **Large tables**: Split by row groups and prepend the header row (`| Col A | Col B |` + `|---|---|`) to every chunk, or serialize each row into key-value prose (`"Row 14 — Service: auth-api, SLA: 99.95%, Owner: Platform"`).

---

## 2. Chunking Strategy Decision Matrix

| Strategy | Typical Chunk Size | Overlap | Best For | Avoid When |
|---|---|---|---|---|
| **Fixed-Token / Character** | $400\text{--}512$ tokens | $10\text{--}20\%$ | Uniform plain text logs or transcripts | Structured docs, code, or tables where mid-sentence breaks hurt |
| **Recursive Structure-Aware** | $400\text{--}800$ tokens | $10\text{--}15\%$ | General prose, articles, support tickets | Documents needing section hierarchy metadata |
| **Markdown / Header-Aware** | Section-bounded (cap at $800$ tokens) | $0\text{--}10\%$ | Technical docs, runbooks, RFCs, ADRs | Flat unformatted text with zero headings |
| **Code AST Chunking** | 1 function / method / class | None (prepend module/class path) | Codebases, API references | Non-code prose |
| **Parent-Child (Small-to-Big)** | Child: $128\text{--}256$ tokens; Parent: $800\text{--}1500$ tokens | Child: $20\text{--}32$ tokens | Dense technical manuals, legal contracts, multi-topic pages | Short FAQ entries already under 250 tokens |
| **Contextual Retrieval** | $300\text{--}600$ tokens + $50\text{--}100$ token prefix | $10\%$ | High-accuracy enterprise KBs with pronouns/cross-references | Ultra-tight ingestion budgets where LLM prefixing is unnecessary (use deterministic header breadcrumbs instead) |

---

## 3. Parent-Child (Small-to-Big) & Contextual Retrieval

### Pattern A — Parent-Child Indexing
Vectors represent the *average* semantic meaning of a chunk. Large chunks (1,200 tokens) dilute vector specificity, while tiny chunks (200 tokens) lack enough surrounding evidence for the LLM to answer cleanly.

**Solution:**
1. Split each document into **Parent Chunks** ($800\text{--}1,500$ tokens) stored in a document/KV table keyed by `parent_id`.
2. Split each parent into **Child Chunks** ($150\text{--}250$ tokens) storing `parent_id` as metadata; index *only* child chunks in the vector + BM25 store.
3. At query time, search child chunks, deduplicate by `parent_id` (retaining max child score), and pass the **Parent Chunks** to the reranker/LLM.

### Pattern B — Contextual Retrieval Prefixing
A chunk reading *"Latency increased by 40% after the v2.4 migration"* fails retrieval for *"Why was auth-service slow?"* because *"auth-service"* appeared three paragraphs earlier.

**Two Tiers of Contextual Enrichment:**
1. **Zero-Cost Deterministic Breadcrumbs (Always Do This)**: Prepend document title, URI, and Markdown heading path to the chunk text before embedding and BM25 indexing:
   ```text
   [Doc: Runbook — Auth Service Incidents | Section: 3. Post-Migration Regressions > v2.4]
   Latency increased by 40% after the v2.4 migration...
   ```
2. **LLM-Generated Situating Context (High-Value Corpora)**: During offline ingestion, use a fast model with prompt caching over the full document to prepend 1–2 sentences situating each chunk within the whole document before generating embeddings and BM25 tokens.

---

## 4. Idempotent Incremental Ingestion Pipeline

Re-embedding an entire corpus on every CI deploy wastes compute and causes transient search outages if chunks are deleted before replacements land.

```python
import hashlib
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ChunkRecord:
    chunk_id: str
    doc_id: str
    doc_version: str
    chunk_index: int
    content_hash: str
    text: str
    metadata: dict[str, str]


def compute_content_hash(doc_id: str, normalized_text: str) -> str:
    """Deterministic SHA-256 digest for idempotent delta upserts."""
    payload = f"{doc_id}::{normalized_text.strip()}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def build_chunk_id(doc_id: str, chunk_index: int, content_hash: str) -> str:
    """Stable primary key combining document identity, order, and content hash."""
    raw = f"{doc_id}:{chunk_index}:{content_hash[:16]}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:32]
```

### Safe Sync Lifecycle (Upsert-Then-Sweep)
1. **Compute Hashes**: Normalize whitespace and compute `content_hash` per document/chunk.
2. **Skip Unchanged Documents**: Compare incoming `(doc_id, doc_hash)` against stored ingestion state; skip unmodified files completely.
3. **Batch Embed & Upsert**: Embed changed chunks in bounded batches (e.g., 64–128 chunks/request with exponential backoff on 429s) and upsert with `doc_version = new_version`.
4. **Tombstone Sweep**: Inside a transaction, `DELETE FROM rag_chunks WHERE doc_id = :doc_id AND doc_version <> :new_version` so users never see partial or missing search results during re-indexing.

