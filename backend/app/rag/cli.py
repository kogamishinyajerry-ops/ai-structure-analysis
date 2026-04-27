"""RAG ingest CLI — runs all registered sources through KnowledgeBase (P1-04b).

Walks the `ALL_SOURCES` registry (`app.rag.sources.__init__`),
runs each source's `iter_*_documents(repo_root)` generator, ingests
the resulting Document stream into a KnowledgeBase backed by either:

  * MemoryVectorStore + MockEmbedder      — `--embedder mock` (default; no deps)
  * ChromaVectorStore  + BgeM3Embedder    — `--embedder bge-m3` (requires `[rag]`)

Usage:
    python3 -m app.rag.cli
    python3 -m app.rag.cli --embedder mock --root /path/to/repo
    python3 -m app.rag.cli --embedder bge-m3 --persist-dir runs/rag/kb
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

from app.rag import KnowledgeBase, MemoryVectorStore, MockEmbedder
from app.rag.sources import ALL_SOURCES


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

    R3 (post Codex R2 polish): error messages are emitted ONLY at
    the main() catch — no double print from inside _build_kb. The
    `_UsageError.message` carries the user-facing text.
    """
    if embedder_choice == "mock":
        embedder = MockEmbedder(dim=32)
        store = MemoryVectorStore()
    elif embedder_choice == "bge-m3":
        # Validate cheap argument before any heavy work.
        if persist_dir is None:
            raise _UsageError("--persist-dir is required with --embedder bge-m3")

        # Lazy import — heavy deps. Both the module import AND the
        # `BgeM3Embedder()` constructor lazy-import sentence_transformers,
        # so wrap both in the same translator.
        try:
            from app.rag.embedder import BgeM3Embedder
            from app.rag.store import ChromaVectorStore

            embedder = BgeM3Embedder()
        except ImportError as e:
            raise _UsageError(
                f"bge-m3 backend unavailable: {e}. "
                'Install with: pip install -e ".[rag]"'
            ) from e

        store = ChromaVectorStore(persist_dir=persist_dir, collection_name=collection)
    else:
        raise _UsageError(f"unknown --embedder: {embedder_choice}")

    return KnowledgeBase(embedder, store)


def _acquire_persist_lock(persist_dir: Path):
    """Single-writer guard for concurrent `ingest-rag` runs targeting
    the same `--persist-dir`.

    R3 (post Codex R2 MEDIUM): chromadb's local `PersistentClient` is
    not process-safe for concurrent writers sharing one path
    (per https://docs.trychroma.com/reference/python/client). Without
    a guard, two `ingest-rag --embedder bge-m3 --persist-dir <same>`
    runs can race the on-disk KB and corrupt or duplicate writes.

    Uses `fcntl.flock` (advisory, non-blocking). Returns the lock
    file handle; caller must keep it open for the duration of the
    write to hold the lock. Raises `_UsageError` if another process
    already holds it.

    On platforms without fcntl (Windows), this is a best-effort
    no-op — the persistent-write race is a known platform gap that
    needs a separate fix (e.g. portalocker) when Windows ingest is
    actually exercised.
    """
    persist_dir.mkdir(parents=True, exist_ok=True)
    lock_path = persist_dir / ".ingest.lock"
    f = open(lock_path, "w")
    try:
        import fcntl
    except ImportError:  # pragma: no cover — Windows
        return f
    try:
        fcntl.flock(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except (BlockingIOError, OSError) as e:
        f.close()
        raise _UsageError(
            f"another ingest run is writing to {persist_dir}; "
            "refusing to race the on-disk KB"
        ) from e
    return f


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

    # R3 (post Codex R2 MEDIUM): acquire a single-writer lock on
    # `--persist-dir` BEFORE building the KB, so two concurrent
    # ingest runs targeting the same dir don't race chromadb's
    # local PersistentClient. Mock backend has no on-disk state,
    # so no lock needed.
    lock_handle = None
    try:
        if args.embedder == "bge-m3" and args.persist_dir is not None:
            lock_handle = _acquire_persist_lock(args.persist_dir)
        kb = _build_kb(args.embedder, args.persist_dir, args.collection)
    except _UsageError as e:
        print(f"[ingest-rag] {e.message}", file=sys.stderr)
        if lock_handle is not None:
            lock_handle.close()
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
    try:
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
    finally:
        # R3 (post Codex R2 MEDIUM): release the persist-dir lock so a
        # subsequent ingest can acquire it.
        if lock_handle is not None:
            lock_handle.close()


if __name__ == "__main__":
    sys.exit(main(sys.argv))
