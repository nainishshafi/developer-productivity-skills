#!/usr/bin/env python3
r"""
rag-pipeline-eval.py — Zero-dependency RAG chunking, hybrid search (BM25 + Dense + RRF),
and offline IR evaluation CLI utility.

Usage:
    .\.venv\Scripts\python.exe .github/skills/rag-pipeline/scripts/rag-pipeline-eval.py chunk --strategy markdown --input README.md --chunk-size 600 --overlap 80
    .\.venv\Scripts\python.exe .github/skills/rag-pipeline/scripts/rag-pipeline-eval.py hybrid-search --query "ERR_CONNECTION_REFUSED pgvector HNSW" --top-k 5
    .\.venv\Scripts\python.exe .github/skills/rag-pipeline/scripts/rag-pipeline-eval.py evaluate --demo --k 5
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

TOKEN_PATTERN = re.compile(r"[a-z0-9_]+")
HEADER_PATTERN = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)

DEFAULT_CORPUS: list[dict[str, str]] = [
    {
        "id": "doc-pgvector-hnsw",
        "title": "PostgreSQL pgvector HNSW Tuning",
        "content": (
            "Use halfvec(1024) with hnsw (m=16, ef_construction=64) in PostgreSQL pgvector. "
            "Enable SET LOCAL hnsw.iterative_scan = relaxed_order to prevent selective tenant "
            "filters from collapsing vector search recall."
        ),
    },
    {
        "id": "doc-conn-refused",
        "title": "Database Socket Connection Triage",
        "content": (
            "ERR_CONNECTION_REFUSED on port 5432 indicates the PostgreSQL listener is down, "
            "pg_hba.conf rejects the subnet, or the connection pooler PgBouncer exhausted sockets."
        ),
    },
    {
        "id": "doc-hybrid-rrf",
        "title": "Hybrid Search & Reciprocal Rank Fusion",
        "content": (
            "Combine sparse lexical BM25 scoring with dense vector cosine similarity via "
            "Reciprocal Rank Fusion (RRF) using smoothing constant k=60 to preserve exact "
            "identifiers alongside semantic paraphrases."
        ),
    },
    {
        "id": "doc-parent-child",
        "title": "Parent-Child Contextual Chunking",
        "content": (
            "Index compact 200-token child chunks for sharp vector precision while returning "
            "surrounding 1000-token parent sections with header breadcrumbs to the LLM."
        ),
    },
    {
        "id": "doc-oom-137",
        "title": "Kubernetes OOMKilled Diagnostics",
        "content": (
            "Container exit code 137 signals SIGKILL from the Linux kernel OOM killer when "
            "a pod exceeds cgroup memory limits during large batch embedding jobs."
        ),
    },
    {
        "id": "doc-acl-security",
        "title": "RAG Tenant & ACL Pre-Filtering",
        "content": (
            "Enforce tenant_id and acl_groups predicates inside the database WHERE clause or "
            "vector payload filter before retrieval; never filter access rights post-LLM."
        ),
    },
]

DEMO_EVAL_CASES: list[dict[str, Any]] = [
    {
        "query": "ERR_CONNECTION_REFUSED pgvector listener",
        "relevant_ids": ["doc-conn-refused", "doc-pgvector-hnsw"],
        "retrieved_ids": ["doc-conn-refused", "doc-hybrid-rrf", "doc-pgvector-hnsw", "doc-oom-137", "doc-acl-security"],
        "grades": {"doc-conn-refused": 3.0, "doc-pgvector-hnsw": 2.0},
    },
    {
        "query": "prevent tenant filter recall drop in hnsw",
        "relevant_ids": ["doc-pgvector-hnsw", "doc-acl-security"],
        "retrieved_ids": ["doc-pgvector-hnsw", "doc-acl-security", "doc-hybrid-rrf", "doc-parent-child", "doc-oom-137"],
        "grades": {"doc-pgvector-hnsw": 3.0, "doc-acl-security": 2.0},
    },
    {
        "query": "pod killed memory limit during embedding batch",
        "relevant_ids": ["doc-oom-137"],
        "retrieved_ids": ["doc-parent-child", "doc-oom-137", "doc-hybrid-rrf", "doc-conn-refused", "doc-acl-security"],
        "grades": {"doc-oom-137": 3.0},
    },
]


def tokenize(text: str) -> list[str]:
    """Extract lowercase alphanumeric/underscore tokens for lexical matching."""
    return TOKEN_PATTERN.findall(text.lower())


def stable_chunk_id(source_label: str, index: int, text: str) -> str:
    """Compute a deterministic 24-char SHA-256 identifier for a chunk."""
    digest = hashlib.sha256(f"{source_label}:{index}:{text.strip()}".encode("utf-8")).hexdigest()
    return digest[:24]


def split_fixed(text: str, chunk_size: int, overlap: int) -> list[str]:
    """Slice text into fixed character windows with bounded overlap."""
    if not text.strip():
        return []
    step = max(1, chunk_size - overlap)
    chunks: list[str] = []
    pos = 0
    while pos < len(text):
        segment = text[pos : pos + chunk_size].strip()
        if segment:
            chunks.append(segment)
        if pos + chunk_size >= len(text):
            break
        pos += step
    return chunks


def split_recursive(text: str, chunk_size: int, overlap: int) -> list[str]:
    """Split text recursively along paragraph, line, and sentence boundaries."""
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    chunks: list[str] = []
    current = ""

    for para in paragraphs:
        if len(para) > chunk_size:
            if current:
                chunks.append(current)
                current = ""
            chunks.extend(split_fixed(para, chunk_size, overlap))
            continue

        candidate = f"{current}\n\n{para}".strip() if current else para
        if len(candidate) <= chunk_size:
            current = candidate
        else:
            chunks.append(current)
            tail = current[-overlap:].strip() if overlap > 0 else ""
            current = f"{tail}\n\n{para}".strip() if tail and len(tail) + len(para) + 2 <= chunk_size else para

    if current:
        chunks.append(current)
    return chunks


def extract_markdown_headings(text: str) -> list[tuple[int, str, int]]:
    """Find Markdown heading positions outside fenced code blocks."""
    headings: list[tuple[int, str, int]] = []
    in_fence = False
    offset = 0
    for line in text.splitlines(keepends=True):
        stripped = line.lstrip()
        if stripped.startswith("```") or stripped.startswith("~~~"):
            in_fence = not in_fence
        elif not in_fence:
            match = HEADER_PATTERN.match(line.rstrip("\r\n"))
            if match:
                headings.append((len(match.group(1)), match.group(2).strip(), offset))
        offset += len(line)
    return headings


def split_markdown(text: str, chunk_size: int, overlap: int) -> list[str]:
    """Split Markdown by heading hierarchy and preserve section breadcrumbs."""
    headings = extract_markdown_headings(text)
    if not headings:
        return split_recursive(text, chunk_size, overlap)

    sections: list[tuple[str, str]] = []
    if headings[0][2] > 0:
        preamble = text[: headings[0][2]].strip()
        if preamble:
            sections.append(("Preamble", preamble))

    stack: list[tuple[int, str]] = []
    for idx, (level, heading, start_pos) in enumerate(headings):
        while stack and stack[-1][0] >= level:
            stack.pop()
        stack.append((level, heading))
        breadcrumb = " > ".join(item[1] for item in stack)
        end_pos = headings[idx + 1][2] if idx + 1 < len(headings) else len(text)
        body = text[start_pos:end_pos].strip()
        if body:
            sections.append((breadcrumb, body))

    results: list[str] = []
    for breadcrumb, body in sections:
        prefix = f"[{breadcrumb}]\n"
        budget = max(100, chunk_size - len(prefix))
        for piece in split_recursive(body, budget, min(overlap, budget // 3)):
            results.append(f"{prefix}{piece}")
    return results


def run_chunk_command(args: argparse.Namespace) -> dict[str, Any]:
    """Execute the chunk simulation subcommand and return structured stats."""
    input_path = Path(args.input)
    if input_path.is_file():
        raw_text = input_path.read_text(encoding="utf-8")
        source_label = input_path.as_posix()
    else:
        raw_text = args.input
        source_label = "inline-text"

    if args.chunk_size <= 0:
        raise ValueError("--chunk-size must be > 0")
    if args.overlap < 0 or args.overlap >= args.chunk_size:
        raise ValueError("--overlap must be >= 0 and < --chunk-size")

    if args.strategy == "fixed":
        raw_chunks = split_fixed(raw_text, args.chunk_size, args.overlap)
    elif args.strategy == "recursive":
        raw_chunks = split_recursive(raw_text, args.chunk_size, args.overlap)
    else:
        raw_chunks = split_markdown(raw_text, args.chunk_size, args.overlap)

    prefix = f"{args.context_prefix.strip()}\n" if args.context_prefix else ""
    records: list[dict[str, Any]] = []
    for idx, body in enumerate(raw_chunks):
        enriched = f"{prefix}{body}"
        records.append(
            {
                "chunk_index": idx,
                "chunk_id": stable_chunk_id(source_label, idx, enriched),
                "chars": len(enriched),
                "est_tokens": max(1, len(enriched) // 4),
                "preview": enriched[:100].replace("\n", " "),
                "text": enriched,
            }
        )

    avg_chars = round(sum(r["chars"] for r in records) / len(records), 1) if records else 0.0
    return {
        "source": source_label,
        "strategy": args.strategy,
        "chunk_size": args.chunk_size,
        "overlap": args.overlap,
        "total_chunks": len(records),
        "avg_chars": avg_chars,
        "chunks": records,
    }


def hash_embed(text: str, dims: int = 128) -> list[float]:
    """Deterministic local n-gram hashed embedding for offline vector similarity demos."""
    vec = [0.0] * dims
    tokens = tokenize(text)
    features = list(tokens)
    for tok in tokens:
        if len(tok) >= 4:
            features.extend(tok[i : i + 3] for i in range(len(tok) - 2))
    for feat in features:
        digest = hashlib.blake2b(feat.encode("utf-8"), digest_size=8).digest()
        bucket = int.from_bytes(digest[:4], "little") % dims
        sign = 1.0 if (digest[4] & 1) == 0 else -1.0
        vec[bucket] += sign

    norm = math.sqrt(sum(v * v for v in vec))
    return [v / norm for v in vec] if norm > 0.0 else vec


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Compute cosine similarity between two equal-length float vectors."""
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


def bm25_scores(query: str, corpus_texts: list[str], k1: float = 1.5, b: float = 0.75) -> list[float]:
    """Compute Okapi BM25 lexical relevance scores across corpus_texts."""
    tokenized_docs = [tokenize(doc) for doc in corpus_texts]
    n_docs = len(tokenized_docs)
    if n_docs == 0:
        return []

    avgdl = sum(len(doc) for doc in tokenized_docs) / n_docs or 1.0
    doc_freq: Counter[str] = Counter()
    for doc in tokenized_docs:
        doc_freq.update(set(doc))

    query_terms = tokenize(query)
    scores: list[float] = []
    for doc in tokenized_docs:
        tf_map = Counter(doc)
        dl = len(doc)
        score = 0.0
        for term in query_terms:
            df = doc_freq.get(term, 0)
            if df == 0:
                continue
            idf = math.log(1.0 + (n_docs - df + 0.5) / (df + 0.5))
            tf = tf_map.get(term, 0)
            denom = tf + k1 * (1.0 - b + b * (dl / avgdl))
            score += idf * ((tf * (k1 + 1.0)) / denom) if denom > 0 else 0.0
        scores.append(score)
    return scores


def run_hybrid_search(args: argparse.Namespace) -> dict[str, Any]:
    """Run BM25 + dense vector similarity + Reciprocal Rank Fusion (RRF)."""
    if args.corpus:
        raw = json.loads(Path(args.corpus).read_text(encoding="utf-8"))
        corpus = [
            {
                "id": str(item["id"]),
                "title": str(item.get("title", item["id"])),
                "content": str(item["content"]),
                "embedding": item.get("embedding"),
            }
            for item in raw
        ]
    else:
        corpus = [{**doc, "embedding": None} for doc in DEFAULT_CORPUS]

    texts = [f"{doc['title']} {doc['content']}" for doc in corpus]
    lexical = bm25_scores(args.query, texts)

    query_vec = hash_embed(args.query)
    dense = [
        cosine_similarity(query_vec, doc["embedding"] if doc["embedding"] else hash_embed(text))
        for doc, text in zip(corpus, texts)
    ]

    bm25_order = sorted(range(len(corpus)), key=lambda i: lexical[i], reverse=True)
    dense_order = sorted(range(len(corpus)), key=lambda i: dense[i], reverse=True)

    bm25_ranks = {idx: rank for rank, idx in enumerate(bm25_order, start=1) if lexical[idx] > 0.0}
    dense_ranks = {idx: rank for rank, idx in enumerate(dense_order, start=1)}

    fused: list[dict[str, Any]] = []
    for idx, doc in enumerate(corpus):
        b_rank = bm25_ranks.get(idx)
        d_rank = dense_ranks.get(idx)
        rrf = 0.0
        if b_rank is not None:
            rrf += args.bm25_weight / (args.k_rrf + b_rank)
        if d_rank is not None:
            rrf += args.dense_weight / (args.k_rrf + d_rank)
        fused.append(
            {
                "id": doc["id"],
                "title": doc["title"],
                "bm25_score": round(lexical[idx], 4),
                "bm25_rank": b_rank,
                "dense_score": round(dense[idx], 4),
                "dense_rank": d_rank,
                "rrf_score": round(rrf, 6),
            }
        )

    fused.sort(key=lambda row: row["rrf_score"], reverse=True)
    return {
        "query": args.query,
        "k_rrf": args.k_rrf,
        "weights": {"bm25": args.bm25_weight, "dense": args.dense_weight},
        "results": fused[: args.top_k],
    }


def compute_ndcg_at_k(retrieved: list[str], grades: dict[str, float], k: int) -> float:
    """Compute Normalized Discounted Cumulative Gain at cutoff K."""
    dcg = sum(
        (2.0 ** grades.get(doc_id, 0.0) - 1.0) / math.log2(rank + 1)
        for rank, doc_id in enumerate(retrieved[:k], start=1)
    )
    ideal_gains = sorted(grades.values(), reverse=True)[:k]
    idcg = sum(
        (2.0**rel - 1.0) / math.log2(rank + 1)
        for rank, rel in enumerate(ideal_gains, start=1)
    )
    return (dcg / idcg) if idcg > 0.0 else 0.0


def evaluate_queries(cases: list[dict[str, Any]], k: int) -> dict[str, Any]:
    """Compute HitRate@K, Recall@K, Precision@K, MRR, and NDCG@K across queries."""
    if not cases:
        raise ValueError("Evaluation dataset is empty")
    if k <= 0:
        raise ValueError("--k must be > 0")

    per_query: list[dict[str, Any]] = []
    for idx, case in enumerate(cases):
        retrieved = [str(x) for x in case["retrieved_ids"]][:k]
        relevant = {str(x) for x in case["relevant_ids"]}
        raw_grades = case.get("grades")
        grades: dict[str, float] = (
            {str(doc): float(val) for doc, val in raw_grades.items()}
            if isinstance(raw_grades, dict)
            else {doc: 1.0 for doc in relevant}
        )

        hits = [doc for doc in retrieved if doc in relevant]
        hit_rate = 1.0 if hits else 0.0
        recall = (len(set(hits)) / len(relevant)) if relevant else 0.0
        precision = len(set(hits)) / k
        first_rank = next((rank for rank, doc in enumerate(retrieved, start=1) if doc in relevant), None)
        rr = (1.0 / first_rank) if first_rank is not None else 0.0
        ndcg = compute_ndcg_at_k(retrieved, grades, k)

        per_query.append(
            {
                "query": str(case.get("query", f"query-{idx + 1}")),
                "hit_rate": round(hit_rate, 4),
                "recall": round(recall, 4),
                "precision": round(precision, 4),
                "reciprocal_rank": round(rr, 4),
                "ndcg": round(ndcg, 4),
            }
        )

    count = len(per_query)
    return {
        "k": k,
        "num_queries": count,
        "metrics": {
            f"hit_rate@{k}": round(sum(q["hit_rate"] for q in per_query) / count, 4),
            f"recall@{k}": round(sum(q["recall"] for q in per_query) / count, 4),
            f"precision@{k}": round(sum(q["precision"] for q in per_query) / count, 4),
            "mrr": round(sum(q["reciprocal_rank"] for q in per_query) / count, 4),
            f"ndcg@{k}": round(sum(q["ndcg"] for q in per_query) / count, 4),
        },
        "per_query": per_query,
    }


def format_table(headers: list[str], rows: list[list[Any]]) -> str:
    """Render an aligned plain-text ASCII table."""
    str_rows = [[str(cell) for cell in row] for row in rows]
    widths = [max([len(h)] + [len(r[i]) for r in str_rows]) for i, h in enumerate(headers)]
    sep = " | ".join("-" * w for w in widths)
    head_line = " | ".join(h.ljust(widths[i]) for i, h in enumerate(headers))
    body_lines = [" | ".join(r[i].ljust(widths[i]) for i in range(len(headers))) for r in str_rows]
    return "\n".join([head_line, sep, *body_lines])


def render_output(payload: dict[str, Any], command: str, fmt: str) -> str:
    """Render command results as JSON or human-readable tables."""
    if fmt == "json":
        return json.dumps(payload, indent=2)

    if command == "chunk":
        rows = [[c["chunk_index"], c["chunk_id"], c["chars"], c["est_tokens"], c["preview"]] for c in payload["chunks"]]
        header = f"Strategy: {payload['strategy']} | Chunks: {payload['total_chunks']} | Avg chars: {payload['avg_chars']}"
        return f"{header}\n\n" + format_table(["#", "Chunk ID", "Chars", "~Tokens", "Preview"], rows)

    if command == "hybrid-search":
        rows = [
            [r["id"], r["bm25_rank"] or "-", r["bm25_score"], r["dense_rank"] or "-", r["dense_score"], r["rrf_score"]]
            for r in payload["results"]
        ]
        header = f"Query: {payload['query']} (RRF k={payload['k_rrf']})"
        return f"{header}\n\n" + format_table(
            ["Doc ID", "BM25 Rank", "BM25", "Dense Rank", "Dense", "RRF Score"], rows
        )

    k = payload["k"]
    m = payload["metrics"]
    summary = (
        f"Evaluated {payload['num_queries']} queries @ K={k} -> "
        f"HitRate@{k}={m[f'hit_rate@{k}']} | Recall@{k}={m[f'recall@{k}']} | "
        f"Precision@{k}={m[f'precision@{k}']} | MRR={m['mrr']} | NDCG@{k}={m[f'ndcg@{k}']}"
    )
    rows = [[q["query"], q["hit_rate"], q["recall"], q["precision"], q["reciprocal_rank"], q["ndcg"]] for q in payload["per_query"]]
    return f"{summary}\n\n" + format_table(["Query", "Hit", "Recall", "Precision", "RR", "NDCG"], rows)


def build_parser() -> argparse.ArgumentParser:
    """Construct the CLI argument parser for chunk, hybrid-search, and evaluate."""
    parser = argparse.ArgumentParser(description="RAG Pipeline Chunking, Hybrid RRF & IR Evaluation Utility")
    subparsers = parser.add_subparsers(dest="command", required=True)

    p_chunk = subparsers.add_parser("chunk", help="Simulate document chunking and inspect SHA-256 IDs & token budgets")
    p_chunk.add_argument("--strategy", choices=["fixed", "recursive", "markdown"], default="markdown")
    p_chunk.add_argument("--input", required=True, help="File path or inline text string")
    p_chunk.add_argument("--chunk-size", type=int, default=500)
    p_chunk.add_argument("--overlap", type=int, default=80)
    p_chunk.add_argument("--context-prefix", default="")
    p_chunk.add_argument("--format", choices=["table", "json"], default="table")
    p_chunk.add_argument("--output", help="Optional path to write output")

    p_search = subparsers.add_parser("hybrid-search", help="Simulate BM25 + Dense Vector Reciprocal Rank Fusion")
    p_search.add_argument("--query", required=True)
    p_search.add_argument("--corpus", help="Optional JSON file containing [{id, title, content, embedding?}]")
    p_search.add_argument("--top-k", type=int, default=5)
    p_search.add_argument("--k-rrf", type=int, default=60)
    p_search.add_argument("--dense-weight", type=float, default=0.5)
    p_search.add_argument("--bm25-weight", type=float, default=0.5)
    p_search.add_argument("--format", choices=["table", "json"], default="table")

    p_eval = subparsers.add_parser("evaluate", help="Compute Recall@K, Precision@K, HitRate@K, MRR, and NDCG@K")
    p_eval.add_argument("--predictions", help="JSON file of [{query, relevant_ids, retrieved_ids, grades?}]")
    p_eval.add_argument("--demo", action="store_true", help="Run built-in benchmark queries")
    p_eval.add_argument("--k", type=int, default=5)
    p_eval.add_argument("--format", choices=["table", "json"], default="table")

    return parser


def main() -> int:
    """CLI entrypoint."""
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "chunk":
        payload = run_chunk_command(args)
        rendered = render_output(payload, "chunk", args.format)
        if args.output:
            out_path = Path(args.output)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(rendered + "\n", encoding="utf-8")
            print(f"Wrote chunk report to {out_path.as_posix()}")
        else:
            print(rendered)
        return 0

    if args.command == "hybrid-search":
        payload = run_hybrid_search(args)
        print(render_output(payload, "hybrid-search", args.format))
        return 0

    if args.predictions:
        cases = json.loads(Path(args.predictions).read_text(encoding="utf-8"))
    elif args.demo:
        cases = DEMO_EVAL_CASES
    else:
        print("Error: supply --predictions <file.json> or --demo", file=sys.stderr)
        return 1

    payload = evaluate_queries(cases, args.k)
    print(render_output(payload, "evaluate", args.format))
    return 0


if __name__ == "__main__":
    sys.exit(main())
