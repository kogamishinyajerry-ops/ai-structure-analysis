"""Tests for backend.app.rag.sources.project_governance (Source 4)."""

from __future__ import annotations

from pathlib import Path

import pytest

try:
    from backend.app.rag import KnowledgeBase, MemoryVectorStore, MockEmbedder
    from backend.app.rag.sources.project_governance import (
        SOURCE_LABEL,
        _extract_doc_id,
        _extract_title,
        _parse_frontmatter,
        iter_governance_documents,
        main,
    )
except ImportError as e:
    pytest.skip(f"rag.sources imports failed: {e}", allow_module_level=True)


# ---------------------------------------------------------------------------
# _parse_frontmatter
# ---------------------------------------------------------------------------


def test_parse_frontmatter_simple():
    text = """---
id: FP-001
status: proposed
created: 2026-04-25
---

# Body header

body text
"""
    fm, body = _parse_frontmatter(text)
    assert fm["id"] == "FP-001"
    assert fm["status"] == "proposed"
    assert fm["created"] == "2026-04-25"
    assert "Body header" in body


def test_parse_frontmatter_list_value():
    text = """---
related_gs: [GS-001, GS-002]
related_adr: [ADR-011]
blocks: []
---
body
"""
    fm, _ = _parse_frontmatter(text)
    assert fm["related_gs"] == ["GS-001", "GS-002"]
    assert fm["related_adr"] == ["ADR-011"]
    assert fm["blocks"] == []


def test_parse_frontmatter_nested_block():
    text = """---
id: FP-X
gs_artifact_pin:
  expected_results_version: "1.0"
  inp_sha: "abc123"
classification: geometry_invalid
---
body
"""
    fm, _ = _parse_frontmatter(text)
    assert fm["id"] == "FP-X"
    assert fm["classification"] == "geometry_invalid"
    assert fm["gs_artifact_pin"] == {
        "expected_results_version": "1.0",
        "inp_sha": "abc123",
    }


def test_parse_frontmatter_strips_quotes():
    text = """---
id: 'FP-X'
title: "quoted"
---
body
"""
    fm, _ = _parse_frontmatter(text)
    assert fm["id"] == "FP-X"
    assert fm["title"] == "quoted"


def test_parse_frontmatter_no_frontmatter():
    text = "# Just a markdown\n\nNo frontmatter here.\n"
    fm, body = _parse_frontmatter(text)
    assert fm == {}
    assert body == text


def test_parse_frontmatter_empty_input():
    fm, body = _parse_frontmatter("")
    assert fm == {}
    assert body == ""


def test_parse_frontmatter_skips_comments():
    text = """---
# this is a comment
id: x
# another comment
status: y
---
body
"""
    fm, _ = _parse_frontmatter(text)
    assert fm == {"id": "x", "status": "y"}


# ---------------------------------------------------------------------------
# _extract_doc_id, _extract_title
# ---------------------------------------------------------------------------


def test_extract_doc_id_from_frontmatter():
    assert _extract_doc_id(Path("anything.md"), {"id": "FP-042"}) == "FP-042"


def test_extract_doc_id_from_filename_adr():
    assert _extract_doc_id(Path("ADR-011-pivot-foo.md"), {}) == "ADR-011"


def test_extract_doc_id_from_filename_fp():
    assert _extract_doc_id(Path("FP-003-gs003-bar.md"), {}) == "FP-003"


def test_extract_doc_id_case_insensitive_filename():
    assert _extract_doc_id(Path("adr-007-name.md"), {}) == "ADR-007"


def test_extract_doc_id_fallback_to_stem():
    assert _extract_doc_id(Path("random_doc.md"), {}) == "random_doc"


def test_extract_title_first_h1():
    body = "## subhead\n\n# Real Title\n\n## another\n# not the first\n"
    assert _extract_title(body, fallback="x") == "Real Title"


def test_extract_title_fallback():
    assert _extract_title("no headers here", fallback="filename-stem") == "filename-stem"


# ---------------------------------------------------------------------------
# iter_governance_documents — synthetic repo
# ---------------------------------------------------------------------------


def _make_synth(tmp_path: Path) -> Path:
    docs = tmp_path / "docs"
    adr = docs / "adr"
    fp = docs / "failure_patterns"
    adr.mkdir(parents=True)
    fp.mkdir(parents=True)

    # ADR with minimal frontmatter
    (adr / "ADR-100-test-adr.md").write_text("# ADR-100: Test ADR\n\nADR body content here.\n")

    # FP with full frontmatter
    (fp / "FP-100-test-fp.md").write_text(
        """---
id: FP-100
status: proposed
classification: test_class
related_gs: [GS-X]
related_adr: [ADR-100]
schema_version: 1
---

# FP-100: Test failure pattern

FP body text.
"""
    )

    # README.md in failure_patterns — should be skipped
    (fp / "README.md").write_text("# Patterns README\n\nIndex.\n")

    # Empty markdown file — should be skipped
    (fp / "FP-200-empty.md").write_text("")

    return tmp_path


def test_iter_finds_adr_and_fp(tmp_path):
    repo = _make_synth(tmp_path)
    docs = list(iter_governance_documents(repo))
    ids = sorted(d.doc_id for d in docs)
    # R2 (post Codex R1 MEDIUM): doc_ids are now namespaced with the
    # SOURCE_LABEL prefix to avoid cross-source chunk_id collisions.
    assert ids == ["project-adr-fp:ADR-100", "project-adr-fp:FP-100"]


def test_iter_skips_readme_and_empty(tmp_path):
    repo = _make_synth(tmp_path)
    docs = list(iter_governance_documents(repo))
    assert all(d.doc_id != "README" for d in docs)
    assert all(d.doc_id != "FP-200" for d in docs)


def test_iter_lifts_metadata_from_frontmatter(tmp_path):
    repo = _make_synth(tmp_path)
    docs = list(iter_governance_documents(repo))
    fp_doc = next(d for d in docs if d.doc_id == "project-adr-fp:FP-100")
    assert fp_doc.metadata["status"] == "proposed"
    assert fp_doc.metadata["classification"] == "test_class"
    assert fp_doc.metadata["related_gs"] == ["GS-X"]
    assert fp_doc.metadata["related_adr"] == ["ADR-100"]
    assert fp_doc.metadata["kind"] == "failure_pattern"
    # frontmatter parser keeps int-looking values as strings (no type coercion);
    # downstream filters can int-cast as needed.
    assert fp_doc.metadata["schema_version"] in (1, "1")


def test_iter_adr_uses_filename_id_when_no_frontmatter(tmp_path):
    repo = _make_synth(tmp_path)
    docs = list(iter_governance_documents(repo))
    adr_doc = next(d for d in docs if d.doc_id == "project-adr-fp:ADR-100")
    assert adr_doc.metadata["kind"] == "adr"
    assert "status" not in adr_doc.metadata  # ADR file had no frontmatter


def test_iter_uses_correct_source_label(tmp_path):
    repo = _make_synth(tmp_path)
    docs = list(iter_governance_documents(repo))
    assert all(d.source == SOURCE_LABEL for d in docs)
    assert SOURCE_LABEL == "project-adr-fp"


def test_iter_no_dirs_returns_empty(tmp_path):
    """If neither docs/adr/ nor docs/failure_patterns/ exists, yield nothing."""
    docs = list(iter_governance_documents(tmp_path))
    assert docs == []


def test_iter_handles_one_dir_missing(tmp_path):
    """If only docs/adr/ exists (no failure_patterns), still yield ADRs."""
    adr = tmp_path / "docs" / "adr"
    adr.mkdir(parents=True)
    (adr / "ADR-007-x.md").write_text("# ADR-007\n\nbody\n")
    docs = list(iter_governance_documents(tmp_path))
    assert len(docs) == 1
    # R2: SOURCE_LABEL: prefix added.
    assert docs[0].doc_id == "project-adr-fp:ADR-007"


def test_iter_full_text_preserved(tmp_path):
    """Full text including frontmatter is what gets embedded — preserves
    the cross-reference links in retrieval."""
    repo = _make_synth(tmp_path)
    docs = list(iter_governance_documents(repo))
    fp_doc = next(d for d in docs if d.doc_id == "project-adr-fp:FP-100")
    assert "---" in fp_doc.text  # frontmatter present
    assert "FP body text" in fp_doc.text  # body present


# ---------------------------------------------------------------------------
# Integration with KnowledgeBase
# ---------------------------------------------------------------------------


def test_can_ingest_into_knowledge_base(tmp_path):
    repo = _make_synth(tmp_path)
    docs = list(iter_governance_documents(repo))
    kb = KnowledgeBase(MockEmbedder(dim=16), MemoryVectorStore(), chunk_size=500)
    stats = kb.ingest(docs)
    assert stats.documents_seen == 2
    assert stats.chunks_written >= 2

    # Source filter works end-to-end
    results = kb.query("test", k=10, source_filter=SOURCE_LABEL)
    assert all(r.chunk.source == SOURCE_LABEL for r in results)


# ---------------------------------------------------------------------------
# Real-repo smoke
# ---------------------------------------------------------------------------


def test_real_repo_yields_adr_011_plus_fps():
    repo_root = Path(__file__).resolve().parent.parent
    docs = list(iter_governance_documents(repo_root))
    ids = {d.doc_id for d in docs}
    # R2: SOURCE_LABEL: namespace prefix on every id.
    assert "project-adr-fp:ADR-011" in ids
    assert {
        "project-adr-fp:FP-001",
        "project-adr-fp:FP-002",
        "project-adr-fp:FP-003",
    }.issubset(ids)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def test_main_lists_docs(tmp_path, capsys):
    repo = _make_synth(tmp_path)
    rc = main(["project_governance.py", "--root", str(repo)])
    out = capsys.readouterr().out
    assert rc == 0
    assert "ADR-100" in out
    assert "FP-100" in out
    assert "status:proposed" in out  # status lifted into output


# ---------------------------------------------------------------------------
# R2 — Codex R1 MEDIUMs (symlink escape, inline-comment misparse, doc_id dup)
# ---------------------------------------------------------------------------


def test_iter_rejects_symlinks_pointing_outside_repo(tmp_path):
    """R2 (Codex R1 MEDIUM-1): a committed symlink in docs/adr/ pointing
    outside the repo must NOT be ingested. Live probe in R1 confirmed
    the prior implementation read /etc/hosts via such a link."""
    repo = _make_synth(tmp_path)
    outside = tmp_path.parent / "outside_secret.md"
    outside.write_text("# secret\nshould not be ingested\n")
    link = repo / "docs" / "adr" / "ADR-999-link.md"
    try:
        link.symlink_to(outside)
    except OSError:
        pytest.skip("symlink not supported on this filesystem")
    docs = list(iter_governance_documents(repo))
    assert all("ADR-999" not in d.doc_id for d in docs), (
        "symlink ADR-999-link.md must not be ingested"
    )
    assert all("secret" not in d.text for d in docs)


def test_iter_rejects_symlinks_pointing_inside_repo(tmp_path):
    """Even if the symlink target is INSIDE the repo, the link itself
    is rejected — it's a different file, and its name could collide
    with a real ADR id."""
    repo = _make_synth(tmp_path)
    link = repo / "docs" / "adr" / "ADR-998-self-link.md"
    target = repo / "docs" / "adr" / "ADR-100-test.md"
    try:
        link.symlink_to(target)
    except OSError:
        pytest.skip("symlink not supported")
    docs = list(iter_governance_documents(repo))
    assert all("ADR-998" not in d.doc_id for d in docs)


def test_inline_yaml_comment_stripped_from_scalar_value(tmp_path):
    """R2 (Codex R1 MEDIUM-2): `classification: geometry_invalid  # ...`
    must parse the value as `geometry_invalid`, not the whole string
    including the comment. The README documents this form."""
    fp = tmp_path / "docs" / "failure_patterns"
    fp.mkdir(parents=True)
    (fp / "FP-501-x.md").write_text(
        "---\n"
        "id: FP-501\n"
        "classification: geometry_invalid  # see ADR-002 §3 for taxonomy\n"
        "status: proposed\n"
        "---\n"
        "# FP-501\n\nbody\n"
    )
    docs = list(iter_governance_documents(tmp_path))
    fp_doc = next(d for d in docs if "FP-501" in d.doc_id)
    assert fp_doc.metadata["classification"] == "geometry_invalid", (
        "inline `# ...` comment must be stripped from scalar value"
    )


def test_inline_yaml_comment_on_nested_block_start(tmp_path):
    """R2 (Codex R1 MEDIUM-2): `nested_key:  # comment` must be
    recognized as a nested-block start (empty value after strip),
    not as a scalar with the comment baked in."""
    fp = tmp_path / "docs" / "failure_patterns"
    fp.mkdir(parents=True)
    (fp / "FP-502-x.md").write_text(
        "---\n"
        "id: FP-502\n"
        "gs_artifact_pin:  # placeholder until pin populated\n"
        "  hash: abc123\n"
        "  case: GS-001\n"
        "---\n"
        "# FP-502\n\nbody\n"
    )
    fm, _ = _parse_frontmatter_call(tmp_path / "docs" / "failure_patterns" / "FP-502-x.md")
    # gs_artifact_pin must be recognized as a nested dict, not a scalar.
    assert isinstance(fm.get("gs_artifact_pin"), dict), (
        "nested-block start with inline comment must produce a dict"
    )
    assert fm["gs_artifact_pin"].get("hash") == "abc123"
    assert fm["gs_artifact_pin"].get("case") == "GS-001"


def test_inline_comment_stripper_preserves_hash_inside_quotes(tmp_path):
    """R3 (post Codex R2 MEDIUM): the value
    `"value # not-a-comment" # trailing comment` must round-trip as
    `"value # not-a-comment"` — quote state must shield the inner
    `#` from comment-stripping. The first attempt only short-circuited
    on fully-quoted values and corrupted this form.
    """
    from backend.app.rag.sources.project_governance import _strip_inline_comment

    # Quoted body containing `#`, plus a real trailing inline comment.
    out = _strip_inline_comment('"value # not-a-comment" # trailing comment')
    assert out == '"value # not-a-comment"'

    # Single-quote variant.
    out = _strip_inline_comment("'kept # inside' # comment")
    assert out == "'kept # inside'"

    # Mixed: `#` only inside the quote, no trailing.
    out = _strip_inline_comment('"a # b"')
    assert out == '"a # b"'

    # Whole-line comment value.
    out = _strip_inline_comment("# this is all comment")
    assert out == ""

    # No `#` at all.
    out = _strip_inline_comment("plain value")
    assert out == "plain value"

    # Unquoted with comment.
    out = _strip_inline_comment("plain value  # comment")
    assert out == "plain value"


def test_inline_comment_stripper_round_trips_through_parser(tmp_path):
    """End-to-end: a frontmatter line with a quoted value containing `#`
    AND a trailing inline comment must produce the unmodified quoted
    value (minus the surrounding quotes, since _parse_frontmatter
    strips them after comment removal)."""
    fp = tmp_path / "docs" / "failure_patterns"
    fp.mkdir(parents=True)
    (fp / "FP-503-x.md").write_text(
        "---\n"
        "id: FP-503\n"
        'classification: "value # not-a-comment" # trailing comment\n'
        "---\n"
        "# FP-503\n\nbody\n"
    )
    docs = list(iter_governance_documents(tmp_path))
    fp_doc = next(d for d in docs if "FP-503" in d.doc_id)
    # Parser strips the surrounding quotes after stripping the trailing
    # comment, so the value reads as the inner literal.
    assert fp_doc.metadata["classification"] == "value # not-a-comment"


def test_iter_raises_on_duplicate_doc_id(tmp_path):
    """R2 (Codex R1 MEDIUM-3): two docs with the same `id` in
    frontmatter would silently overwrite each other in the KB upsert
    path. Detect + raise instead."""
    fp = tmp_path / "docs" / "failure_patterns"
    fp.mkdir(parents=True)
    (fp / "FP-001-a.md").write_text("---\nid: FP-001\nstatus: a\n---\n# A\n\nbody A\n")
    (fp / "FP-001-b.md").write_text("---\nid: FP-001\nstatus: b\n---\n# B\n\nbody B\n")
    with pytest.raises(ValueError, match="duplicate doc_id"):
        list(iter_governance_documents(tmp_path))


def _parse_frontmatter_call(md_path):
    """Helper: reproduce read+parse path for direct frontmatter inspection."""
    from backend.app.rag.sources.project_governance import _parse_frontmatter

    text = md_path.read_text(encoding="utf-8")
    return _parse_frontmatter(text)


def test_main_returns_1_when_no_docs(tmp_path, capsys):
    rc = main(["project_governance.py", "--root", str(tmp_path)])
    err = capsys.readouterr().err
    assert rc == 1
    assert "No governance" in err
