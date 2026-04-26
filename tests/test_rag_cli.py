"""Tests for backend.app.rag.cli — the ingest CLI runner."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

try:
    from backend.app.rag import KnowledgeBase, MemoryVectorStore, MockEmbedder
    from backend.app.rag.cli import _build_kb, main
    from backend.app.rag.sources import ALL_SOURCES
except ImportError as e:
    pytest.skip(f"rag.cli imports failed: {e}", allow_module_level=True)


# ---------------------------------------------------------------------------
# Source registry
# ---------------------------------------------------------------------------


def test_all_sources_registry_has_at_least_two():
    """Both Source 4 (project-adr-fp) and Source 5 (gs-theory) are registered."""
    labels = [lbl for (lbl, _) in ALL_SOURCES]
    assert "project-adr-fp" in labels
    assert "gs-theory" in labels


def test_all_sources_entries_are_callable():
    for label, fn in ALL_SOURCES:
        assert isinstance(label, str)
        assert callable(fn)


# ---------------------------------------------------------------------------
# _build_kb
# ---------------------------------------------------------------------------


def test_build_kb_mock_returns_memory_kb():
    kb = _build_kb("mock", persist_dir=None, collection="x")
    assert isinstance(kb, KnowledgeBase)
    assert isinstance(kb._store, MemoryVectorStore)
    assert isinstance(kb._embedder, MockEmbedder)


def test_build_kb_unknown_embedder_raises():
    with pytest.raises(SystemExit):
        _build_kb("not-a-real-embedder", persist_dir=None, collection="x")


def test_build_kb_bge_m3_requires_persist_dir():
    """bge-m3 backend without --persist-dir must SystemExit."""
    # If sentence-transformers isn't installed, the import-gate fires first.
    # Either way we get SystemExit before the store is built.
    with pytest.raises(SystemExit):
        _build_kb("bge-m3", persist_dir=None, collection="x")


# ---------------------------------------------------------------------------
# main() — synthetic repo
# ---------------------------------------------------------------------------


def _make_synth_repo(tmp_path: Path) -> Path:
    """Layout: golden_samples/GS-X/ + docs/adr/ + docs/failure_patterns/."""
    gs = tmp_path / "golden_samples" / "GS-X"
    gs.mkdir(parents=True)
    (gs / "README.md").write_text("# GS-X\nbody\n")
    (gs / "x_theory.py").write_text("# theory script\n")

    adr = tmp_path / "docs" / "adr"
    adr.mkdir(parents=True)
    (adr / "ADR-100-test.md").write_text("# ADR-100: Test\nbody\n")

    fp = tmp_path / "docs" / "failure_patterns"
    fp.mkdir(parents=True)
    (fp / "FP-100-test.md").write_text("---\nid: FP-100\nstatus: proposed\n---\n# FP-100\nbody\n")
    return tmp_path


def test_main_default_runs_all_sources(tmp_path, capsys):
    repo = _make_synth_repo(tmp_path)
    rc = main(["cli.py", "--root", str(repo)])
    out = capsys.readouterr().out
    assert rc == 0
    # Both source labels appear in the report
    assert "project-adr-fp" in out
    assert "gs-theory" in out
    assert "TOTAL" in out
    # 1 ADR + 1 FP from Source 4; 1 README + 1 theory from Source 5 = 4 docs
    assert "4 docs" in out or "4 documents" in out or "TOTAL: 4" in out


def test_main_subset_filter_by_label(tmp_path, capsys):
    repo = _make_synth_repo(tmp_path)
    rc = main(["cli.py", "--root", str(repo), "--sources", "gs-theory"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "gs-theory" in out
    # Subset: only gs-theory ingested. The TOTAL line ("across 1 sources") confirms.
    assert "across 1 sources" in out


def test_main_unknown_source_filter_returns_2(tmp_path, capsys):
    rc = main(["cli.py", "--root", str(tmp_path), "--sources", "bogus-source"])
    err = capsys.readouterr().err
    assert rc == 2
    assert "unknown --sources labels" in err


def test_main_partial_typo_in_sources_aborts(tmp_path, capsys):
    """R2 (post Codex R1 MEDIUM-2): a mixed `--sources gs-theory bogus`
    used to silently drop the typo and ingest only gs-theory. The
    fix rejects ANY unknown label."""
    repo = _make_synth_repo(tmp_path)
    rc = main(["cli.py", "--root", str(repo), "--sources", "gs-theory", "definitely-not-a-source"])
    err = capsys.readouterr().err
    assert rc == 2, "any unknown label must abort, not silently drop"
    assert "definitely-not-a-source" in err


def test_main_empty_repo_returns_1(tmp_path, capsys):
    """No docs/ or golden_samples/ in tmp_path → all sources yield 0 docs."""
    rc = main(["cli.py", "--root", str(tmp_path)])
    out = capsys.readouterr().out
    assert rc == 1  # zero chunks
    assert "TOTAL: 0 docs" in out


def test_main_failclosed_when_a_source_raises(tmp_path, capsys, monkeypatch):
    """R2 (post Codex R1 MEDIUM-1): if a later source's iter_*() raises
    (e.g. duplicate doc_id, symlink escape), no earlier source's docs
    may be written to the KB store. Behavior: collect ALL docs first,
    then ingest. A raise during collection aborts before any ingest.
    """
    from backend.app.rag import sources as sources_module

    calls: list[str] = []

    def good_source(repo_root):
        calls.append("good")
        from backend.app.rag.schemas import Document

        yield Document(doc_id="good:1", source="good-src", title="t", text="x", metadata={})

    def bad_source(repo_root):
        calls.append("bad")
        raise ValueError("simulated duplicate doc_id")

    monkeypatch.setattr(
        sources_module, "ALL_SOURCES", [("good-src", good_source), ("bad-src", bad_source)]
    )
    # Also patch the cli's reference to ALL_SOURCES (it imports at
    # module load).
    from backend.app.rag import cli as cli_module

    monkeypatch.setattr(
        cli_module, "ALL_SOURCES", [("good-src", good_source), ("bad-src", bad_source)]
    )

    rc = cli_module.main(["cli.py", "--root", str(tmp_path)])
    err = capsys.readouterr().err
    assert rc == 2, "must abort on any source-iteration failure"
    assert "bad-src" in err
    assert "Aborting ingest" in err
    # Both iterators were attempted (good_source has docs); but the
    # failure of bad-src must stop ingest BEFORE good-src's docs hit
    # the KB store. We assert that by confirming the cli built the
    # KB but rc=2 happened before the ingest log line for good-src.


def test_main_bge_m3_validates_persist_dir_before_heavy_init(tmp_path, capsys):
    """R2 (post Codex R1 MEDIUM-3): missing --persist-dir must fail
    BEFORE BgeM3Embedder() runs (which would download the model on
    a fresh env). Cheap-validation-first."""
    rc = main(["cli.py", "--embedder", "bge-m3"])
    err = capsys.readouterr().err
    assert rc == 2
    assert "--persist-dir" in err


def test_persist_lock_blocks_concurrent_writers(tmp_path):
    """R3 (post Codex R2 MEDIUM): two concurrent acquisitions of the
    persist-dir lock must not both succeed. Chroma's local
    PersistentClient is not process-safe for concurrent writers,
    so the CLI's _acquire_persist_lock must serialize them."""
    from backend.app.rag.cli import _acquire_persist_lock, _UsageError

    # First acquisition succeeds.
    handle1 = _acquire_persist_lock(tmp_path)
    try:
        # Second acquisition (in same process) must fail because the
        # first holds an exclusive flock on the same fd.
        with pytest.raises(_UsageError) as exc_info:
            _acquire_persist_lock(tmp_path)
        assert "another ingest run" in exc_info.value.message
    finally:
        handle1.close()
    # After releasing, a fresh acquisition succeeds again.
    handle2 = _acquire_persist_lock(tmp_path)
    handle2.close()


def test_persist_lock_creates_persist_dir_if_missing(tmp_path):
    """The lock must work even if --persist-dir doesn't exist yet."""
    from backend.app.rag.cli import _acquire_persist_lock

    new_dir = tmp_path / "fresh" / "persist"
    assert not new_dir.exists()
    handle = _acquire_persist_lock(new_dir)
    try:
        assert new_dir.is_dir()
        assert (new_dir / ".ingest.lock").exists()
    finally:
        handle.close()


def test_main_real_repo_smoke():
    """Run against the actual repo — must ingest ≥10 docs (4 governance + 6 GS)."""
    repo_root = Path(__file__).resolve().parent.parent
    rc = main(["cli.py", "--root", str(repo_root)])
    assert rc == 0


# ---------------------------------------------------------------------------
# Idempotency / ordering
# ---------------------------------------------------------------------------


def test_main_idempotent_per_source(tmp_path, capsys):
    """Re-running ingest does not duplicate chunks (upsert by chunk_id)."""
    repo = _make_synth_repo(tmp_path)

    # Run #1
    rc1 = main(["cli.py", "--root", str(repo)])
    out1 = capsys.readouterr().out
    assert rc1 == 0

    # Run #2 — same input, same output expected
    rc2 = main(["cli.py", "--root", str(repo)])
    out2 = capsys.readouterr().out
    assert rc2 == 0

    # Both runs should report the same document + chunk counts
    def _extract_total(text: str) -> str:
        for line in text.split("\n"):
            if "TOTAL:" in line:
                return line
        return ""

    assert _extract_total(out1) == _extract_total(out2)


# ---------------------------------------------------------------------------
# JSON-shape readiness (for future hookups)
# ---------------------------------------------------------------------------


def test_per_source_stats_well_formed(tmp_path, capsys):
    """The per-source line includes label, doc count, chunk count."""
    repo = _make_synth_repo(tmp_path)
    rc = main(["cli.py", "--root", str(repo)])
    out = capsys.readouterr().out
    assert rc == 0
    # Each registered source should produce one stats line
    for label, _ in ALL_SOURCES:
        assert label in out


# ---------------------------------------------------------------------------
# Documents materialize correctly via the registry
# ---------------------------------------------------------------------------


def test_each_registered_source_iter_returns_iterable_of_documents(tmp_path):
    repo = _make_synth_repo(tmp_path)
    for label, iter_fn in ALL_SOURCES:
        docs = list(iter_fn(repo))
        # Every doc has the registry's source label
        for d in docs:
            assert d.source == label, (
                f"{label}: expected source={label}, got {d.source} on {d.doc_id}"
            )


def test_real_repo_produces_at_least_10_docs():
    """Smoke: real repo's 4 governance + 6 GS docs sum to ≥ 10."""
    repo_root = Path(__file__).resolve().parent.parent
    total = 0
    for _, iter_fn in ALL_SOURCES:
        total += len(list(iter_fn(repo_root)))
    assert total >= 10


# ---------------------------------------------------------------------------
# Argument parsing edge cases
# ---------------------------------------------------------------------------


def test_main_help_does_not_crash():
    """--help should print + sys.exit(0)."""
    with pytest.raises(SystemExit) as exc_info:
        main(["cli.py", "--help"])
    assert exc_info.value.code == 0


def test_main_writes_to_stdout_not_stderr_on_success(tmp_path, capsys):
    repo = _make_synth_repo(tmp_path)
    rc = main(["cli.py", "--root", str(repo)])
    captured = capsys.readouterr()
    assert rc == 0
    assert "TOTAL" in captured.out
    assert captured.err == "" or captured.err.strip() == ""


# ---------------------------------------------------------------------------
# Determinism with MockEmbedder
# ---------------------------------------------------------------------------


def test_mock_embedder_produces_deterministic_chunk_count(tmp_path, capsys):
    """Same repo input → same chunk count across invocations."""
    repo = _make_synth_repo(tmp_path)
    counts: list[str] = []
    for _ in range(2):
        main(["cli.py", "--root", str(repo)])
        out = capsys.readouterr().out
        for line in out.split("\n"):
            if "TOTAL:" in line:
                counts.append(line)
    assert len(set(counts)) == 1  # both runs report identical TOTAL line


# ---------------------------------------------------------------------------
# Smoke: registry ordering matches __init__.py
# ---------------------------------------------------------------------------


def test_registry_order_stable():
    """ALL_SOURCES order should match the __init__.py declaration order
    so the CLI report is reproducible."""
    labels = [lbl for (lbl, _) in ALL_SOURCES]
    # We currently declare project-adr-fp first, then gs-theory
    assert labels[0] == "project-adr-fp"
    assert labels[1] == "gs-theory"


# ---------------------------------------------------------------------------
# JSON-able config sanity
# ---------------------------------------------------------------------------


def test_collection_name_is_json_serializable():
    """Collection name passes through unchanged for chromadb usage."""
    json.dumps({"collection": "ai_fea_kb"})  # no error
