"""RAG query CLI — operator-facing retrieval against the live corpus (P1-04b).

Pairs with `backend.app.rag.cli` (the ingest CLI). Where ingest *writes*
chunks to a vector store, this CLI *reads* them back.

For the default mock backend the embedder is sha256-based — there is no
semantic similarity, so query() will only return useful hits when the
question text overlaps the chunk text byte-for-byte. That is intentional:
mock mode is for plumbing/format checks, not retrieval quality. For real
retrieval, install the [rag] extra and pass `--embedder bge-m3`.

Usage:
    # Mock (no deps) — exercises the pipeline; retrieval quality is N/A
    python3 -m backend.app.rag.query_cli --query "ADR-011"

    # Real retrieval (requires sentence-transformers + a populated chroma store)
    python3 -m backend.app.rag.query_cli \\
        --embedder bge-m3 --persist-dir runs/rag/kb \\
        --query "static analysis convergence guidance" --k 5

Exit codes:
    0 — at least one result returned
    1 — empty result set (legitimate retrieval miss, or empty corpus)
    2 — usage error (no --query, unknown source filter, etc.)
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from backend.app.rag import KnowledgeBase, MemoryVectorStore, MockEmbedder
from backend.app.rag.sources import ALL_SOURCES


def _build_kb_for_query(
    embedder_choice: str,
    persist_dir: Path | None,
    collection: str,
    root: Path,
    ingest_in_memory: bool,
) -> KnowledgeBase:
    """Construct a KB. For mock, optionally ingest the live repo into memory
    so query has something to match against (mock has no persistence)."""
    if embedder_choice == "mock":
        embedder = MockEmbedder(dim=32)
        store = MemoryVectorStore()
        kb = KnowledgeBase(embedder, store)
        if ingest_in_memory:
            for _label, iter_fn in ALL_SOURCES:
                docs = list(iter_fn(root))
                if docs:
                    kb.ingest(docs)
        return kb

    if embedder_choice == "bge-m3":
        try:
            from backend.app.rag.embedder import BgeM3Embedder
            from backend.app.rag.store import ChromaVectorStore
        except ImportError as e:
            raise SystemExit(
                f"[query-rag] bge-m3 backend unavailable: {e}. "
                'Install with: pip install -e ".[rag]"'
            ) from e

        if persist_dir is None:
            raise SystemExit("[query-rag] --persist-dir is required with --embedder bge-m3")
        return KnowledgeBase(
            BgeM3Embedder(),
            ChromaVectorStore(persist_dir=persist_dir, collection_name=collection),
        )

    raise SystemExit(f"[query-rag] unknown --embedder: {embedder_choice}")


def _format_result_line(rank: int, score: float, source: str, chunk_id: str, snippet: str) -> str:
    snippet = snippet.replace("\n", " ").strip()
    if len(snippet) > 120:
        snippet = snippet[:117] + "..."
    return f"  #{rank + 1:<2d} score={score:6.3f}  [{source:16s}] {chunk_id}\n      {snippet}"


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Query the RAG knowledge base.")
    parser.add_argument(
        "--embedder",
        choices=["mock", "bge-m3"],
        default="mock",
        help="Embedder backend (default: mock; no deps but no semantic similarity)",
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parents[3],
        help="Repo root for in-memory mock ingest (ignored for bge-m3)",
    )
    parser.add_argument(
        "--persist-dir",
        type=Path,
        default=None,
        help="ChromaDB persist directory (required with --embedder bge-m3)",
    )
    parser.add_argument(
        "--collection",
        default="ai_fea_kb",
        help="ChromaDB collection name (default: ai_fea_kb)",
    )
    parser.add_argument(
        "--query",
        required=True,
        help="Question text to embed and look up",
    )
    parser.add_argument(
        "--k",
        type=int,
        default=5,
        help="Top-k results to retrieve (default: 5)",
    )
    parser.add_argument(
        "--source-filter",
        default=None,
        help="Restrict to one source label (e.g. project-adr-fp, gs-theory)",
    )
    parser.add_argument(
        "--no-ingest",
        action="store_true",
        help="Mock backend only: skip in-memory ingest of the live repo",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit one JSON record on stdout instead of human-readable lines",
    )
    args = parser.parse_args(argv[1:])

    if args.k <= 0:
        print("[query-rag] --k must be a positive integer", file=sys.stderr)
        return 2

    if args.source_filter is not None:
        known = {lbl for (lbl, _) in ALL_SOURCES}
        if args.source_filter not in known:
            print(
                f"[query-rag] unknown --source-filter: {args.source_filter}. "
                f"Available: {sorted(known)}",
                file=sys.stderr,
            )
            return 2

    kb = _build_kb_for_query(
        embedder_choice=args.embedder,
        persist_dir=args.persist_dir,
        collection=args.collection,
        root=args.root,
        ingest_in_memory=(args.embedder == "mock" and not args.no_ingest),
    )

    results = kb.query(args.query, k=args.k, source_filter=args.source_filter)

    if args.json:
        payload = {
            "embedder": kb.embedder_id,
            "query": args.query,
            "k": args.k,
            "source_filter": args.source_filter,
            "result_count": len(results),
            "results": [
                {
                    "rank": r.rank,
                    "score": r.score,
                    "source": r.chunk.source,
                    "chunk_id": r.chunk.chunk_id,
                    "text": r.chunk.text,
                }
                for r in results
            ],
        }
        print(json.dumps(payload))
        return 0 if results else 1

    print(f"[query-rag] embedder: {kb.embedder_id}")
    print(f"[query-rag] query:    {args.query!r}")
    print(f"[query-rag] k:        {args.k}")
    if args.source_filter:
        print(f"[query-rag] source:   {args.source_filter}")
    print()

    if not results:
        print("[query-rag] no results.")
        return 1

    for r in results:
        print(_format_result_line(r.rank, r.score, r.chunk.source, r.chunk.chunk_id, r.chunk.text))
    print()
    print(f"[query-rag] {len(results)} result(s).")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
