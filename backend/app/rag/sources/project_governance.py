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


def _strip_inline_comment(value: str) -> str:
    """Strip a YAML-style inline comment (`# ...`) from a scalar value,
    preserving `#` inside quoted strings.

    Walks the value left-to-right, tracking quote state. While inside
    `"..."` or `'...'`, `#` is literal. Outside any quote, the first
    `#` preceded by whitespace (or at position 0) ends the value.

    R3 (post Codex R2 MEDIUM): a previous version only short-circuited
    on values that were ENTIRELY quoted (start AND end with same quote).
    That missed the form `"value # not-a-comment" # trailing comment`,
    which truncated to `"value`. The state-machine walk closes that gap.

    Earlier round (R1→R2 MEDIUM): the original parser ignored inline
    comments entirely; whole-line `#` skip was the only check.
    """
    if not value:
        return value
    in_quote: str | None = None
    for i, ch in enumerate(value):
        if in_quote is None:
            if ch == "'" or ch == '"':
                in_quote = ch
            elif ch == "#" and (i == 0 or value[i - 1].isspace()):
                return value[:i].rstrip()
        else:
            if ch == in_quote:
                in_quote = None
    return value


def _parse_frontmatter(text: str) -> tuple[dict, str]:
    """Return (frontmatter_dict, body_text). Empty dict if no frontmatter.

    Pure-stdlib parser — only handles flat key:value lines and the few
    nested fields actually used in this repo (gs_artifact_pin block
    and list values like `related_gs: [GS-001]`). Round-tripping is
    not required; we just need keys for retrieval filtering.

    R2 (post Codex R1 MEDIUM): inline `# comment` suffixes are now
    stripped via `_strip_inline_comment`, so `key: val  # ...` parses
    as `val` and `nested_key:  # ...` is recognized as a nested-block
    start (empty value after comment strip).
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
        # Comment-line + blank line skip (whole-line comment).
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
            # Strip inline comment from the value before classifying it
            # as scalar vs nested-block start.
            value = _strip_inline_comment(value.strip())
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
            inner_value = _strip_inline_comment(inner_value.strip())
            nested_dict[inner_key.strip()] = inner_value.strip("'\"")

    if nested_key is not None:
        parsed[nested_key] = nested_dict

    return parsed, body


def _extract_doc_id(path: Path, frontmatter: dict) -> str:
    """Prefer frontmatter `id` field; fall back to filename pattern; else stem.

    R2 (post Codex R1 MEDIUM): caller MUST namespace the returned id
    with `SOURCE_LABEL:` to avoid cross-source `chunk_id` collisions
    in the KB store (e.g. two corpora both emitting bare `FP-001`
    silently overwrote each other in the upsert path).
    """
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
    """Yield Document objects for every ADR + FailurePattern markdown file.

    R2 (post Codex R1 MEDIUM):
    - Reject symlinks and any candidate path that resolves outside
      `repo_root` (e.g. a committed `ADR-999-link.md -> /etc/hosts`
      previously round-tripped as a normal governance doc).
    - Detect duplicate `doc_id`s within this source and raise a
      `ValueError`; the KB store upserts by chunk_id derived from
      doc_id, so silent overwrites would break retrieval. The
      `SOURCE_LABEL:` prefix namespaces these IDs vs other sources.
    """
    repo_root_resolved = repo_root.resolve()
    candidates: list[tuple[Path, str]] = [
        (repo_root / "docs" / "adr", "adr"),
        (repo_root / "docs" / "failure_patterns", "failure_pattern"),
    ]
    seen_doc_ids: set[str] = set()
    for dir_path, kind in candidates:
        if not dir_path.is_dir():
            continue
        for md in sorted(dir_path.glob("*.md")):
            if md.name.upper() == "README.MD":
                continue
            # Reject symlinks; reject anything that resolves outside
            # the repo root. is_symlink uses lstat (no follow), so it
            # catches the link itself before any resolve() call.
            if md.is_symlink():
                continue
            try:
                resolved = md.resolve()
                resolved.relative_to(repo_root_resolved)
            except (OSError, ValueError):
                continue
            text = md.read_text(encoding="utf-8", errors="replace")
            if not text.strip():
                continue

            frontmatter, body = _parse_frontmatter(text)
            raw_id = _extract_doc_id(md, frontmatter)
            # Namespace the id with the source label (per
            # backend/app/rag/sources/README.md docs):
            doc_id = f"{SOURCE_LABEL}:{raw_id}"
            if doc_id in seen_doc_ids:
                raise ValueError(
                    f"duplicate doc_id {doc_id!r} from {md} — would silently "
                    f"overwrite a prior chunk in the KB store"
                )
            seen_doc_ids.add(doc_id)
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
