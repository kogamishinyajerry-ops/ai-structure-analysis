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
import sys
from pathlib import Path

from backend.app.rag import KnowledgeBase, MemoryVectorStore, MockEmbedder
from backend.app.rag.reviewer_advisor import (
    FAULT_QUERY_SEEDS,
    advise,
)
from backend.app.rag.sources import ALL_SOURCES


class _UsageError(SystemExit):
    """Mirrors the pattern in `backend.app.rag.cli` and
    `backend.app.rag.query_cli`: exit code 2 for usage / fatal errors
    with a user-facing message attribute. Plain `SystemExit("msg")`
    exits with code 1, conflicting with the docstring's
    `2 = usage error` contract.
    """

    def __init__(self, message: str) -> None:
        super().__init__(2)
        self.message = message


def _build_kb(
    embedder_choice: str,
    persist_dir: Path | None,
    collection: str,
    root: Path,
    ingest_in_memory: bool,
) -> KnowledgeBase:
    """Construct a KB. For mock, optionally ingest the live repo into memory.

    Pre-emptive R2 hardening (lifted from PR #59 + #60 Codex R1 fixes):
    - rc=2 via _UsageError, never plain SystemExit("msg") rc=1
    - validate `--persist-dir` BEFORE constructing BgeM3Embedder (cheap-
      validation-first); the constructor downloads ~2GB of model
    - both the imports AND both constructors live inside the same
      ImportError translator (chromadb is lazy-imported inside the
      ChromaVectorStore __init__ body)
    - mock-path corpus iteration translates ValueError/OSError into
      _UsageError so duplicate-doc_id / symlink-escape failures surface
      as rc=2 instead of leaking a traceback.
    """
    if embedder_choice == "mock":
        kb = KnowledgeBase(MockEmbedder(dim=32), MemoryVectorStore())
        if ingest_in_memory:
            try:
                for _label, iter_fn in ALL_SOURCES:
                    docs = list(iter_fn(root))
                    if docs:
                        kb.ingest(docs)
            except (ValueError, OSError) as e:
                raise _UsageError(f"corpus ingest failed against --root {root}: {e}") from e
        return kb

    if embedder_choice == "bge-m3":
        # Validate cheap argument before any heavy work.
        if persist_dir is None:
            raise _UsageError("--persist-dir is required with --embedder bge-m3")

        # Wrap both imports AND both constructor calls so chromadb-
        # missing-at-construct-time also maps to a clean rc=2.
        try:
            from backend.app.rag.embedder import BgeM3Embedder
            from backend.app.rag.store import ChromaVectorStore

            embedder = BgeM3Embedder()
            store = ChromaVectorStore(persist_dir=persist_dir, collection_name=collection)
        except ImportError as e:
            raise _UsageError(
                f'bge-m3 backend unavailable: {e}. Install with: pip install -e ".[rag]"'
            ) from e

        return KnowledgeBase(embedder, store)

    raise _UsageError(f"unknown --embedder: {embedder_choice}")


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

    try:
        kb = _build_kb(
            embedder_choice=args.embedder,
            persist_dir=args.persist_dir,
            collection=args.collection,
            root=args.root,
            ingest_in_memory=(args.embedder == "mock" and not args.no_ingest),
        )
    except _UsageError as e:
        print(f"[advise-rag] {e.message}", file=sys.stderr)
        return 2

    # `advise()` validates verdict / k / source_filter and raises ValueError.
    # Translate to rc=2 for the operator-facing surface (mirrors the
    # _UsageError contract above). Without this, a typo on --verdict would
    # leak a traceback and exit 1.
    try:
        advice = advise(
            kb,
            verdict=args.verdict,
            fault_class=args.fault,
            k=args.k,
            source_filter=args.source_filter,
        )
    except ValueError as e:
        print(f"[advise-rag] {e}", file=sys.stderr)
        return 2

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
