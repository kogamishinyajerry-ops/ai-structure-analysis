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


def iter_gs_theory_documents(repo_root: Path) -> Iterator[Document]:
    """Yield Document objects for every GS-* README + theory script.

    One document per file. Status banner in README is preserved (not
    stripped) so the embedded chunks carry the `insufficient_evidence`
    cross-link to FP-NNN where applicable.
    """
    samples_root = repo_root / "golden_samples"
    if not samples_root.is_dir():
        return

    for sample_dir in sorted(samples_root.iterdir()):
        if not sample_dir.is_dir() or not sample_dir.name.startswith("GS-"):
            continue
        gs_id = sample_dir.name

        readme = sample_dir / "README.md"
        if readme.is_file():
            text = readme.read_text(encoding="utf-8", errors="replace")
            if text.strip():
                yield Document(
                    doc_id=f"{gs_id}:README",
                    source=SOURCE_LABEL,
                    title=f"{gs_id} README",
                    text=text,
                    metadata={
                        "sample_id": gs_id,
                        "kind": "readme",
                        "path": str(readme.relative_to(repo_root)),
                    },
                )

        for script in sorted(sample_dir.iterdir()):
            if not _is_theory_script(script):
                continue
            text = script.read_text(encoding="utf-8", errors="replace")
            if not text.strip():
                continue
            yield Document(
                doc_id=f"{gs_id}:{script.stem}",
                source=SOURCE_LABEL,
                title=f"{gs_id} theory — {script.name}",
                text=text,
                metadata={
                    "sample_id": gs_id,
                    "kind": "theory_script",
                    "path": str(script.relative_to(repo_root)),
                },
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
