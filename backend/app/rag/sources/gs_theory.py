"""Source 5 ingestion: Golden Samples READMEs + theory scripts (P1-04b).

Reads `golden_samples/GS-*/README.md` and any `*_theory.py` /
`*_theoretical.py` / `*_analytical.py` script in each sample dir, builds
`Document` objects, returns them for the KnowledgeBase to ingest.

Usage:
    from backend.app.rag.sources.gs_theory import iter_gs_theory_documents
    docs = list(iter_gs_theory_documents(repo_root))
    kb.ingest(docs)

CLI:
    python3 -m backend.app.rag.sources.gs_theory [--root <path>]

The CLI prints a summary (doc_id, title, char count) without running
embedding; use `KnowledgeBase.ingest()` from your own script to actually
embed + store.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Iterator
from pathlib import Path

from backend.app.rag.schemas import Document

SOURCE_LABEL = "gs-theory"


def _is_theory_script(p: Path) -> bool:
    if p.suffix != ".py":
        return False
    name = p.name.lower()
    return any(token in name for token in ("theory", "theoretical", "analytical"))


def _is_safe_under_repo(p: Path, repo_root_resolved: Path) -> bool:
    """Reject symlinks (lstat, no follow) and any path whose resolve()
    escapes the repo root. Mirrors the hardening in
    `backend/app/rag/sources/project_governance.py` (post Codex R1
    MEDIUM in PR #57).
    """
    if p.is_symlink():
        return False
    try:
        rp = p.resolve()
        rp.relative_to(repo_root_resolved)
        return True
    except (OSError, ValueError):
        return False


def iter_gs_theory_documents(repo_root: Path) -> Iterator[Document]:
    """Yield Document objects for every GS-* README + theory script.

    One document per file. Status banner in README is preserved (not
    stripped) so the embedded chunks carry the `insufficient_evidence`
    cross-link to FP-NNN where applicable.

    Hardening (mirrors PR #57 post Codex R1 fixes):
    - Reject symlinks and out-of-repo paths to prevent reading files
      via a planted GS-XXX/README.md → /etc/hosts symlink.
    - doc_ids are namespaced as `SOURCE_LABEL:GS-XXX:README` so they
      can't collide with other sources' namespaces in the KB store.
    - Detect duplicate doc_ids in-pass and raise.
    """
    samples_root = repo_root / "golden_samples"
    if not samples_root.is_dir():
        return
    repo_root_resolved = repo_root.resolve()
    seen_doc_ids: set[str] = set()

    def _emit(doc: Document) -> Iterator[Document]:
        if doc.doc_id in seen_doc_ids:
            raise ValueError(
                f"duplicate doc_id {doc.doc_id!r} in gs-theory ingest — would "
                f"silently overwrite a prior chunk in the KB store"
            )
        seen_doc_ids.add(doc.doc_id)
        yield doc

    for sample_dir in sorted(samples_root.iterdir()):
        if not sample_dir.is_dir() or not sample_dir.name.startswith("GS-"):
            continue
        if not _is_safe_under_repo(sample_dir, repo_root_resolved):
            continue
        gs_id = sample_dir.name

        readme = sample_dir / "README.md"
        if readme.is_file() and _is_safe_under_repo(readme, repo_root_resolved):
            text = readme.read_text(encoding="utf-8", errors="replace")
            if text.strip():
                yield from _emit(
                    Document(
                        doc_id=f"{SOURCE_LABEL}:{gs_id}:README",
                        source=SOURCE_LABEL,
                        title=f"{gs_id} README",
                        text=text,
                        metadata={
                            "sample_id": gs_id,
                            "kind": "readme",
                            "path": str(readme.relative_to(repo_root)),
                        },
                    )
                )

        for script in sorted(sample_dir.iterdir()):
            if not _is_theory_script(script):
                continue
            if not _is_safe_under_repo(script, repo_root_resolved):
                continue
            text = script.read_text(encoding="utf-8", errors="replace")
            if not text.strip():
                continue
            yield from _emit(
                Document(
                    doc_id=f"{SOURCE_LABEL}:{gs_id}:{script.stem}",
                    source=SOURCE_LABEL,
                    title=f"{gs_id} theory — {script.name}",
                    text=text,
                    metadata={
                        "sample_id": gs_id,
                        "kind": "theory_script",
                        "path": str(script.relative_to(repo_root)),
                    },
                )
            )


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="List GS theory documents (Source 5).")
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parents[4],
        help="repo root containing golden_samples/",
    )
    args = parser.parse_args(argv[1:])

    docs = list(iter_gs_theory_documents(args.root))
    if not docs:
        print(f"No GS theory documents found under {args.root}/golden_samples/", file=sys.stderr)
        return 1

    print(f"Source 5 ({SOURCE_LABEL}) — {len(docs)} documents from {args.root}")
    for d in docs:
        print(f"  [{d.metadata.get('kind','?'):14s}] {d.doc_id:30s} {len(d.text):6d} chars  {d.title}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
