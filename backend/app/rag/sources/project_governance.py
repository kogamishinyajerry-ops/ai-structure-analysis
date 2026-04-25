"""Source 4 ingestion: project ADRs + FailurePatterns (P1-04b).

Walks `docs/adr/` and `docs/failure_patterns/` for markdown files,
parses YAML frontmatter (FailurePatterns have it; ADRs don't), and
yields `Document` objects with rich metadata so retrieval can
filter by ADR ID / FP ID / status / classification.

Markdown files outside these two directories are not ingested by
this source.

Usage:
    from backend.app.rag.sources.project_governance import iter_governance_documents
    docs = list(iter_governance_documents(repo_root))
    kb.ingest(docs)

CLI:
    python3 -m backend.app.rag.sources.project_governance [--root <path>]
"""

from __future__ import annotations

import argparse
import re
import sys
from collections.abc import Iterator
from pathlib import Path

from backend.app.rag.schemas import Document

SOURCE_LABEL = "project-adr-fp"

# Frontmatter pattern: text starts with `---\n`, then YAML, then `---\n`.
_FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n(.*)\Z", re.DOTALL)
# Title pattern: first H1 line in the body.
_H1_RE = re.compile(r"^# (.+)$", re.MULTILINE)
# ADR/FP id pattern in filename: ADR-NNN-... or FP-NNN-...
_DOC_ID_RE = re.compile(r"^(ADR|FP)-(\d{3})", re.IGNORECASE)


def _parse_frontmatter(text: str) -> tuple[dict, str]:
    """Return (frontmatter_dict, body_text). Empty dict if no frontmatter.

    Pure-stdlib parser — only handles flat key:value lines and the few
    nested fields actually used in this repo (gs_artifact_pin block
    and list values like `related_gs: [GS-001]`). Round-tripping is
    not required; we just need keys for retrieval filtering.
    """
    m = _FRONTMATTER_RE.match(text)
    if not m:
        return {}, text

    frontmatter_text = m.group(1)
    body = m.group(2)

    parsed: dict = {}
    nested_key: str | None = None
    nested_dict: dict = {}

    for raw_line in frontmatter_text.split("\n"):
        # Comment + blank line skip
        stripped = raw_line.rstrip()
        if not stripped or stripped.lstrip().startswith("#"):
            continue

        # Detect nested-block start: `key:` (no value), followed by indented lines.
        if not raw_line.startswith(" ") and ":" in raw_line:
            # Flush previous nested
            if nested_key is not None:
                parsed[nested_key] = nested_dict
                nested_key = None
                nested_dict = {}
            key, _, value = raw_line.partition(":")
            key = key.strip()
            value = value.strip()
            if value == "":
                # Could be a nested-block start
                nested_key = key
                nested_dict = {}
            else:
                # List literal `[a, b]` → split on commas
                if value.startswith("[") and value.endswith("]"):
                    inner = value[1:-1].strip()
                    parsed[key] = (
                        [v.strip().strip("'\"") for v in inner.split(",") if v.strip()]
                        if inner
                        else []
                    )
                else:
                    parsed[key] = value.strip("'\"")
        elif nested_key is not None and raw_line.startswith(" ") and ":" in raw_line:
            inner_key, _, inner_value = raw_line.strip().partition(":")
            nested_dict[inner_key.strip()] = inner_value.strip().strip("'\"")

    if nested_key is not None:
        parsed[nested_key] = nested_dict

    return parsed, body


def _extract_doc_id(path: Path, frontmatter: dict) -> str:
    """Prefer frontmatter `id` field; fall back to filename pattern; else stem."""
    if isinstance(frontmatter.get("id"), str) and frontmatter["id"]:
        return str(frontmatter["id"])
    m = _DOC_ID_RE.match(path.stem)
    if m:
        return f"{m.group(1).upper()}-{m.group(2)}"
    return path.stem


def _extract_title(body: str, fallback: str) -> str:
    m = _H1_RE.search(body)
    return m.group(1).strip() if m else fallback


def iter_governance_documents(repo_root: Path) -> Iterator[Document]:
    """Yield Document objects for every ADR + FailurePattern markdown file."""
    candidates: list[tuple[Path, str]] = [
        (repo_root / "docs" / "adr", "adr"),
        (repo_root / "docs" / "failure_patterns", "failure_pattern"),
    ]
    for dir_path, kind in candidates:
        if not dir_path.is_dir():
            continue
        for md in sorted(dir_path.glob("*.md")):
            if md.name.upper() == "README.MD":
                continue
            text = md.read_text(encoding="utf-8", errors="replace")
            if not text.strip():
                continue

            frontmatter, body = _parse_frontmatter(text)
            doc_id = _extract_doc_id(md, frontmatter)
            title = _extract_title(body, fallback=md.stem)

            metadata: dict = {
                "kind": kind,
                "path": str(md.relative_to(repo_root)),
                "filename": md.name,
            }
            # Lift commonly-filterable frontmatter into top-level metadata.
            for key in ("id", "status", "classification", "schema_version"):
                if key in frontmatter and isinstance(frontmatter[key], (str, int)):
                    metadata[key] = frontmatter[key]
            for key in ("related_gs", "related_adr", "blocks"):
                val = frontmatter.get(key)
                if isinstance(val, list):
                    metadata[key] = list(val)

            yield Document(
                doc_id=doc_id,
                source=SOURCE_LABEL,
                title=title,
                text=text,  # full text including frontmatter — chunks preserve it
                metadata=metadata,
            )


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        description="List project ADR + FailurePattern documents (Source 4)."
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parents[4],
        help="repo root containing docs/adr/ and docs/failure_patterns/",
    )
    args = parser.parse_args(argv[1:])

    docs = list(iter_governance_documents(args.root))
    if not docs:
        print(f"No governance documents under {args.root}/docs/{{adr,failure_patterns}}/", file=sys.stderr)
        return 1

    print(f"Source 4 ({SOURCE_LABEL}) — {len(docs)} documents from {args.root}")
    for d in docs:
        kind = d.metadata.get("kind", "?")
        status = d.metadata.get("status", "")
        suffix = f" [status:{status}]" if status else ""
        print(f"  [{kind:16s}] {d.doc_id:14s} {len(d.text):6d} chars  {d.title[:60]}{suffix}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
