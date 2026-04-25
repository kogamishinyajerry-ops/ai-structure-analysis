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
    assert ids == ["ADR-100", "FP-100"]


def test_iter_skips_readme_and_empty(tmp_path):
    repo = _make_synth(tmp_path)
    docs = list(iter_governance_documents(repo))
    assert all(d.doc_id != "README" for d in docs)
    assert all(d.doc_id != "FP-200" for d in docs)


def test_iter_lifts_metadata_from_frontmatter(tmp_path):
    repo = _make_synth(tmp_path)
    docs = list(iter_governance_documents(repo))
    fp_doc = next(d for d in docs if d.doc_id == "FP-100")
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
    adr_doc = next(d for d in docs if d.doc_id == "ADR-100")
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
    assert docs[0].doc_id == "ADR-007"


def test_iter_full_text_preserved(tmp_path):
    """Full text including frontmatter is what gets embedded — preserves
    the cross-reference links in retrieval."""
    repo = _make_synth(tmp_path)
    docs = list(iter_governance_documents(repo))
    fp_doc = next(d for d in docs if d.doc_id == "FP-100")
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
    # ADR-011 is on main; FP-001/002/003 too
    assert "ADR-011" in ids
    assert {"FP-001", "FP-002", "FP-003"}.issubset(ids)


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


def test_main_returns_1_when_no_docs(tmp_path, capsys):
    rc = main(["project_governance.py", "--root", str(tmp_path)])
    err = capsys.readouterr().err
    assert rc == 1
    assert "No governance" in err
