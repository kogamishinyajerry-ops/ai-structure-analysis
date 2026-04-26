"""RAG ingest CLI — runs all registered sources through KnowledgeBase (P1-04b).

Walks the `ALL_SOURCES` registry (`backend.app.rag.sources.__init__`),
runs each source's `iter_*_documents(repo_root)` generator, ingests
the resulting Document stream into a KnowledgeBase backed by either:

  * MemoryVectorStore + MockEmbedder      — `--embedder mock` (default; no deps)
  * ChromaVectorStore  + BgeM3Embedder    — `--embedder bge-m3` (requires `[rag]`)

Usage:
    python3 -m backend.app.rag.cli
    python3 -m backend.app.rag.cli --embedder mock --root /path/to/repo
    python3 -m backend.app.rag.cli --embedder bge-m3 --persist-dir runs/rag/kb
    make ingest-rag

Exit codes:
    0 — at least one source ingested ≥1 document successfully
    1 — every source produced 0 documents (likely misconfigured paths)
    2 — usage / fatal error
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from backend.app.rag import KnowledgeBase, MemoryVectorStore, MockEmbedder
from backend.app.rag.sources import ALL_SOURCES


class _UsageError(SystemExit):
    """Raised for usage / fatal CLI errors. Exits with code 2 to match
    the docstring's exit-code contract.

    R2 (post Codex R1 MEDIUM-3): plain `SystemExit("msg")` exits with
    status 1, conflicting with the documented `2 = usage / fatal`.
    """

    def __init__(self, message: str) -> None:
        super().__init__(2)
        self.message = message


def _build_kb(embedder_choice: str, persist_dir: Path | None, collection: str) -> KnowledgeBase:
    """Wire embedder + vector store; lazy-import the heavy deps.

    R2 (post Codex R1 MEDIUM-3): validate `--persist-dir` BEFORE
    constructing `BgeM3Embedder()`, so a missing-arg error doesn't
    require a model download first.
    """
    if embedder_choice == "mock":
        embedder = MockEmbedder(dim=32)
        store = MemoryVectorStore()
    elif embedder_choice == "bge-m3":
        # Validate cheap argument before any heavy work.
        if persist_dir is None:
            print(
                "[ingest-rag] --persist-dir is required with --embedder bge-m3",
                file=sys.stderr,
            )
            raise _UsageError("--persist-dir is required with --embedder bge-m3")

        # Lazy import — heavy deps. Both the module import AND the
        # `BgeM3Embedder()` constructor lazy-import sentence_transformers,
        # so wrap both in the same translator.
        try:
            from backend.app.rag.embedder import BgeM3Embedder
            from backend.app.rag.store import ChromaVectorStore

            embedder = BgeM3Embedder()
        except ImportError as e:
            print(
                f"[ingest-rag] bge-m3 backend unavailable: {e}. "
                'Install with: pip install -e ".[rag]"',
                file=sys.stderr,
            )
            raise _UsageError(f"bge-m3 backend unavailable: {e}") from e

        store = ChromaVectorStore(persist_dir=persist_dir, collection_name=collection)
    else:
        print(f"[ingest-rag] unknown --embedder: {embedder_choice}", file=sys.stderr)
        raise _UsageError(f"unknown --embedder: {embedder_choice}")

    return KnowledgeBase(embedder, store)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Ingest RAG sources into the knowledge base.")
    parser.add_argument(
        "--embedder",
        choices=["mock", "bge-m3"],
        default="mock",
        help="Embedder backend (default: mock; no deps)",
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parents[3],
        help="Repo root containing docs/, golden_samples/, etc.",
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
        "--sources",
        nargs="*",
        help="Subset of source labels to ingest (default: all registered)",
    )
    args = parser.parse_args(argv[1:])

    available = {lbl for (lbl, _) in ALL_SOURCES}
    selected = ALL_SOURCES
    if args.sources:
        # R2 (post Codex R1 MEDIUM-2): reject ANY unknown label, not
        # just "all unknown". Operator typos used to be silently
        # ignored, returning success after ingesting only the matched
        # subset. Now a single typo aborts.
        unknown = [s for s in args.sources if s not in available]
        if unknown:
            print(
                f"[ingest-rag] unknown --sources labels: {unknown}. "
                f"Available: {sorted(available)}",
                file=sys.stderr,
            )
            return 2
        selected = [(label, fn) for (label, fn) in ALL_SOURCES if label in set(args.sources)]

    try:
        kb = _build_kb(args.embedder, args.persist_dir, args.collection)
    except _UsageError as e:
        print(f"[ingest-rag] {e.message}", file=sys.stderr)
        return 2

    print(f"[ingest-rag] embedder: {kb.embedder_id}")
    print(f"[ingest-rag] root: {args.root}")
    print(f"[ingest-rag] sources: {[lbl for (lbl, _) in selected]}")
    print()

    # R2 (post Codex R1 MEDIUM-1): collect ALL Documents across ALL
    # selected sources BEFORE any ingest, so a duplicate-doc_id /
    # symlink-escape failure in source N aborts the run before
    # source N-1's chunks are written. Fail-closed at the whole-CLI
    # level — the alternative (ingest each source then rollback) is
    # more complex than the corpus integrity warrants.
    pending: list[tuple[str, list]] = []
    for label, iter_fn in selected:
        try:
            docs = list(iter_fn(args.root))
        except (ValueError, OSError) as e:
            print(
                f"[ingest-rag] source {label!r} failed: {e}. Aborting "
                "ingest before any source is written to the KB store.",
                file=sys.stderr,
            )
            return 2
        pending.append((label, docs))

    total_docs = 0
    total_chunks = 0
    per_source: list[tuple[str, int, int]] = []

    for label, docs in pending:
        if not docs:
            print(f"  [{label:16s}] 0 documents (skipping)")
            per_source.append((label, 0, 0))
            continue
        stats = kb.ingest(docs)
        per_source.append((label, stats.documents_seen, stats.chunks_written))
        total_docs += stats.documents_seen
        total_chunks += stats.chunks_written
        print(
            f"  [{label:16s}] {stats.documents_seen} docs → {stats.chunks_written} chunks "
            f"(avg {stats.chunks_per_doc_avg:.1f} chunks/doc)"
        )

    print()
    print(
        f"[ingest-rag] TOTAL: {total_docs} docs → {total_chunks} chunks "
        f"across {len(per_source)} sources"
    )
    return 0 if total_chunks > 0 else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
