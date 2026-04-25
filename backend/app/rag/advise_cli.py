"""RAG advise CLI — verdict-driven corpus lookup as a shell tool (P1-05b).

Sibling to backend.app.rag.cli (ingest) and backend.app.rag.query_cli (query).
Wraps reviewer_advisor.advise so operators / debug sessions can ask:

    "Given a Reviewer verdict + fault classification, what does the
     corpus tell us about this failure mode?"

Usage:
    python3 -m backend.app.rag.advise_cli --verdict Reject --fault solver_convergence
    python3 -m backend.app.rag.advise_cli --verdict Reject --fault mesh_jacobian --k 3
    python3 -m backend.app.rag.advise_cli --verdict 'Re-run' --fault solver_timestep \\
        --source-filter project-adr-fp

Exit codes:
    0 — at least one corpus hit returned
    1 — empty result set (legitimate retrieval miss)
    2 — usage error (missing args, bad k, unknown source filter)
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from backend.app.rag import KnowledgeBase, MemoryVectorStore, MockEmbedder
from backend.app.rag.reviewer_advisor import (
    FAULT_QUERY_SEEDS,
    advise,
)
from backend.app.rag.sources import ALL_SOURCES


def _build_kb(
    embedder_choice: str,
    persist_dir: Path | None,
    collection: str,
    root: Path,
    ingest_in_memory: bool,
) -> KnowledgeBase:
    if embedder_choice == "mock":
        kb = KnowledgeBase(MockEmbedder(dim=32), MemoryVectorStore())
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
                f"[advise-rag] bge-m3 backend unavailable: {e}. "
                'Install with: pip install -e ".[rag]"'
            ) from e

        if persist_dir is None:
            raise SystemExit("[advise-rag] --persist-dir is required with --embedder bge-m3")
        return KnowledgeBase(
            BgeM3Embedder(),
            ChromaVectorStore(persist_dir=persist_dir, collection_name=collection),
        )

    raise SystemExit(f"[advise-rag] unknown --embedder: {embedder_choice}")


def _format_hit(rank: int, score: float, source: str, chunk_id: str, snippet: str) -> str:
    snippet = snippet.replace("\n", " ").strip()
    if len(snippet) > 110:
        snippet = snippet[:107] + "..."
    return f"  #{rank + 1:<2d} score={score:6.3f}  [{source:16s}] {chunk_id}\n      {snippet}"


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Verdict-driven RAG advisor.")
    parser.add_argument(
        "--verdict",
        required=True,
        help="Reviewer verdict (e.g. Accept, Reject, Re-run, Needs Review)",
    )
    parser.add_argument(
        "--fault",
        default="unknown",
        help="FaultClass value (e.g. solver_convergence, mesh_jacobian); default: unknown",
    )
    parser.add_argument(
        "--k",
        type=int,
        default=5,
        help="Top-k retrieved chunks (default: 5)",
    )
    parser.add_argument(
        "--embedder",
        choices=["mock", "bge-m3"],
        default="mock",
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parents[3],
        help="Repo root for in-memory mock ingest",
    )
    parser.add_argument(
        "--persist-dir",
        type=Path,
        default=None,
    )
    parser.add_argument(
        "--collection",
        default="ai_fea_kb",
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
        print("[advise-rag] --k must be a positive integer", file=sys.stderr)
        return 2

    if args.source_filter is not None:
        known = {lbl for (lbl, _) in ALL_SOURCES}
        if args.source_filter not in known:
            print(
                f"[advise-rag] unknown --source-filter: {args.source_filter}. "
                f"Available: {sorted(known)}",
                file=sys.stderr,
            )
            return 2

    if args.fault not in FAULT_QUERY_SEEDS:
        # Don't reject — _build_query has a fallback. But warn to stderr
        # so operators notice typos.
        print(
            f"[advise-rag] note: fault '{args.fault}' not in FAULT_QUERY_SEEDS; "
            f"falling back to generic query.",
            file=sys.stderr,
        )

    kb = _build_kb(
        embedder_choice=args.embedder,
        persist_dir=args.persist_dir,
        collection=args.collection,
        root=args.root,
        ingest_in_memory=(args.embedder == "mock" and not args.no_ingest),
    )

    advice = advise(
        kb,
        verdict=args.verdict,
        fault_class=args.fault,
        k=args.k,
        source_filter=args.source_filter,
    )

    if args.json:
        payload = {
            "embedder": kb.embedder_id,
            "verdict": args.verdict,
            "fault": args.fault,
            "query": advice.query,
            "source_filter": args.source_filter,
            "hit_count": len(advice.results),
            "by_source": {
                src: len(rs) for src, rs in sorted(advice.grouped_by_source.items())
            },
            "summary": advice.summary,
            "results": [
                {
                    "rank": r.rank,
                    "score": r.score,
                    "source": r.chunk.source,
                    "chunk_id": r.chunk.chunk_id,
                    "text": r.chunk.text,
                }
                for r in advice.results
            ],
        }
        print(json.dumps(payload))
        return 0 if not advice.is_empty() else 1

    print(f"[advise-rag] embedder: {kb.embedder_id}")
    print(f"[advise-rag] verdict:  {args.verdict!r}")
    print(f"[advise-rag] fault:    {args.fault!r}")
    print(f"[advise-rag] query:    {advice.query!r}")
    if args.source_filter:
        print(f"[advise-rag] source:   {args.source_filter}")
    print()

    if advice.is_empty():
        print("[advise-rag] no corpus hits.")
        return 1

    for r in advice.results:
        print(_format_hit(r.rank, r.score, r.chunk.source, r.chunk.chunk_id, r.chunk.text))
    print()

    # Source breakdown
    by_source = ", ".join(
        f"{src}={len(rs)}" for src, rs in sorted(advice.grouped_by_source.items())
    )
    print(f"[advise-rag] {len(advice.results)} hit(s) — by source: {by_source}")
    print(f"[advise-rag] summary: {advice.summary}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
