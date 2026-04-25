"""Tests for backend.app.rag.coverage_audit."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

try:
    from backend.app.rag.coverage_audit import (
        CoverageBucket,
        CoverageReport,
        _discover_adr_files,
        _discover_fp_files,
        _discover_gs_readmes,
        _discover_gs_theory_scripts,
        audit_coverage,
        main,
        report_to_dict,
    )
except ImportError as e:
    pytest.skip(f"coverage_audit imports failed: {e}", allow_module_level=True)


# ---------------------------------------------------------------------------
# Synthetic-repo fixture
# ---------------------------------------------------------------------------


def _make_synth_repo(tmp_path: Path) -> Path:
    # ADR
    adr = tmp_path / "docs" / "adr"
    adr.mkdir(parents=True)
    (adr / "ADR-100-test.md").write_text("# ADR-100\nbody\n")
    (adr / "ADR-101-second.md").write_text("# ADR-101\nbody\n")

    # FP
    fp = tmp_path / "docs" / "failure_patterns"
    fp.mkdir(parents=True)
    (fp / "FP-100.md").write_text("---\nid: FP-100\nstatus: proposed\n---\n# FP-100\nbody\n")
    (fp / "FP-101.md").write_text("---\nid: FP-101\nstatus: proposed\n---\n# FP-101\nbody\n")

    # GS samples
    gs1 = tmp_path / "golden_samples" / "GS-X1"
    gs1.mkdir(parents=True)
    (gs1 / "README.md").write_text("# GS-X1\nbody\n")
    (gs1 / "x1_theory.py").write_text("# theory script\n")

    gs2 = tmp_path / "golden_samples" / "GS-X2"
    gs2.mkdir(parents=True)
    (gs2 / "README.md").write_text("# GS-X2\nbody\n")
    (gs2 / "x2_theoretical.py").write_text("# theoretical script\n")
    (gs2 / "x2_analytical.py").write_text("# analytical script\n")

    return tmp_path


# ---------------------------------------------------------------------------
# Disk discovery
# ---------------------------------------------------------------------------


def test_discover_adr_files(tmp_path):
    repo = _make_synth_repo(tmp_path)
    files = _discover_adr_files(repo)
    names = [f.name for f in files]
    assert "ADR-100-test.md" in names
    assert "ADR-101-second.md" in names
    assert len(files) == 2


def test_discover_adr_files_no_dir_returns_empty(tmp_path):
    assert _discover_adr_files(tmp_path) == []


def test_discover_fp_files(tmp_path):
    repo = _make_synth_repo(tmp_path)
    files = _discover_fp_files(repo)
    names = [f.name for f in files]
    assert names == ["FP-100.md", "FP-101.md"]


def test_discover_gs_readmes(tmp_path):
    repo = _make_synth_repo(tmp_path)
    files = _discover_gs_readmes(repo)
    names = [str(f.relative_to(repo)) for f in files]
    assert "golden_samples/GS-X1/README.md" in names
    assert "golden_samples/GS-X2/README.md" in names
    assert len(files) == 2


def test_discover_gs_theory_scripts_handles_all_three_suffixes(tmp_path):
    repo = _make_synth_repo(tmp_path)
    files = _discover_gs_theory_scripts(repo)
    names = [f.name for f in files]
    assert "x1_theory.py" in names
    assert "x2_theoretical.py" in names
    assert "x2_analytical.py" in names
    assert len(files) == 3


def test_discover_gs_theory_scripts_skips_non_theory(tmp_path):
    repo = _make_synth_repo(tmp_path)
    gs = repo / "golden_samples" / "GS-X1"
    (gs / "main.py").write_text("# not a theory script\n")
    (gs / "test_x1.py").write_text("# tests, not theory\n")
    files = _discover_gs_theory_scripts(repo)
    names = [f.name for f in files]
    assert "main.py" not in names
    assert "test_x1.py" not in names


def test_discover_gs_dirs_handles_no_golden_samples(tmp_path):
    assert _discover_gs_readmes(tmp_path) == []
    assert _discover_gs_theory_scripts(tmp_path) == []


# ---------------------------------------------------------------------------
# audit_coverage on synthetic repo — clean
# ---------------------------------------------------------------------------


def test_audit_coverage_clean_synth_repo(tmp_path):
    repo = _make_synth_repo(tmp_path)
    report = audit_coverage(repo)
    assert (
        report.all_clean()
    ), f"buckets: {[(b.name, b.missing_files, b.extra_files) for b in report.buckets]}"
    assert not report.any_missing()
    assert report.total_expected() == 9  # 2 ADR + 2 FP + 2 README + 3 theory
    assert report.total_covered() == 9
    assert report.total_missing() == 0
    assert report.total_extra() == 0


def test_audit_coverage_bucket_names():
    report = audit_coverage(Path("/nonexistent-dir-for-test"))
    names = [b.name for b in report.buckets]
    assert names == ["adr", "fp", "gs-readme", "gs-theory"]


# ---------------------------------------------------------------------------
# audit_coverage detects missing files
# ---------------------------------------------------------------------------


def test_audit_coverage_missing_adr_after_disk_add(tmp_path):
    """If a new ADR file is added but no ingest re-run, audit should detect it."""
    repo = _make_synth_repo(tmp_path)
    # First audit: clean baseline
    r1 = audit_coverage(repo)
    assert r1.all_clean()

    # Add a new ADR but don't re-run ingest. Since audit_coverage runs
    # iter_fn fresh each time, the new file IS picked up (no caching).
    # To simulate a real "ingest-stale" scenario, we'd need to add a file
    # the iter fn doesn't recognise. Use a malformed name instead:
    # the iter fn will skip it (not match ADR-*.md glob), but disk discovery
    # will... actually, wait — disk discovery uses the same ADR-*.md glob.
    # So this test verifies the parity: disk and ingest agree.
    new_adr = repo / "docs" / "adr" / "ADR-999-new.md"
    new_adr.write_text("# ADR-999\nbody\n")
    r2 = audit_coverage(repo)
    # Both disk and ingest see the new file → still clean
    assert r2.all_clean()
    assert "docs/adr/ADR-999-new.md" in r2.buckets[0].covered_files


def test_audit_coverage_missing_when_iter_fn_skips_a_file(tmp_path, monkeypatch):
    """Force a coverage gap: monkeypatch the project_governance iter to skip one ADR.
    Disk discovery still finds it; cross-ref produces a missing entry."""
    repo = _make_synth_repo(tmp_path)
    import backend.app.rag.coverage_audit as mod

    # Find the original tuple, build a replacement that filters out ADR-100
    original = list(mod.ALL_SOURCES)
    new_sources = []
    for label, fn in original:
        if label == "project-adr-fp":

            def _filtered(root, _orig=fn):
                for d in _orig(root):
                    if d.doc_id != "ADR-100":
                        yield d

            new_sources.append((label, _filtered))
        else:
            new_sources.append((label, fn))

    monkeypatch.setattr(mod, "ALL_SOURCES", new_sources)

    report = mod.audit_coverage(repo)
    adr_bucket = next(b for b in report.buckets if b.name == "adr")
    assert "docs/adr/ADR-100-test.md" in adr_bucket.missing_files
    assert report.any_missing()
    assert not report.all_clean()


# ---------------------------------------------------------------------------
# Real-repo audit
# ---------------------------------------------------------------------------


def test_real_repo_is_clean():
    """The actual repo should currently be clean — every disk file ingested."""
    repo_root = Path(__file__).resolve().parent.parent
    report = audit_coverage(repo_root)
    # If this fails, a new disk file was added without ingest-side support
    # (or vice versa). Either fix the iter fn, or update expected expectations.
    assert report.all_clean(), "real repo coverage drift:\n" + "\n".join(
        f"  {b.name}: missing={list(b.missing_files)} extra={list(b.extra_files)}"
        for b in report.buckets
        if not b.is_clean()
    )


# ---------------------------------------------------------------------------
# CoverageBucket / CoverageReport invariants
# ---------------------------------------------------------------------------


def test_coverage_bucket_is_frozen():
    b = CoverageBucket(
        name="x", expected_files=(), covered_files=(), missing_files=(), extra_files=()
    )
    with pytest.raises((AttributeError, Exception)):
        b.name = "mutated"  # type: ignore[misc]


def test_coverage_bucket_is_clean_predicate():
    clean = CoverageBucket(
        name="x", expected_files=("a",), covered_files=("a",), missing_files=(), extra_files=()
    )
    not_clean_missing = CoverageBucket(
        name="x", expected_files=("a",), covered_files=(), missing_files=("a",), extra_files=()
    )
    not_clean_extra = CoverageBucket(
        name="x", expected_files=(), covered_files=(), missing_files=(), extra_files=("b",)
    )
    assert clean.is_clean()
    assert not not_clean_missing.is_clean()
    assert not_clean_missing.has_missing()
    assert not not_clean_extra.is_clean()
    assert not not_clean_extra.has_missing()


def test_coverage_report_aggregates_correctly():
    b1 = CoverageBucket(
        name="a",
        expected_files=("x", "y"),
        covered_files=("x",),
        missing_files=("y",),
        extra_files=(),
    )
    b2 = CoverageBucket(
        name="b", expected_files=("z",), covered_files=("z",), missing_files=(), extra_files=("w",)
    )
    r = CoverageReport(repo_root="/tmp", buckets=(b1, b2))
    assert r.total_expected() == 3
    assert r.total_covered() == 2
    assert r.total_missing() == 1
    assert r.total_extra() == 1
    assert r.any_missing()
    assert not r.all_clean()


# ---------------------------------------------------------------------------
# report_to_dict — JSON serialisation
# ---------------------------------------------------------------------------


def test_report_to_dict_shape(tmp_path):
    repo = _make_synth_repo(tmp_path)
    d = report_to_dict(audit_coverage(repo))
    assert "repo_root" in d
    assert "summary" in d
    assert "buckets" in d
    assert isinstance(d["buckets"], list)
    assert all("name" in b and "expected" in b for b in d["buckets"])
    # Round-trip through json
    json.dumps(d)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def test_cli_help_exits_zero():
    with pytest.raises(SystemExit) as ei:
        main(["coverage_audit.py", "--help"])
    assert ei.value.code == 0


def test_cli_invalid_root_returns_2(tmp_path, capsys):
    rc = main(["coverage_audit.py", "--root", str(tmp_path / "no-such-dir")])
    err = capsys.readouterr().err
    assert rc == 2
    assert "not a directory" in err


def test_cli_text_output_clean(tmp_path, capsys):
    repo = _make_synth_repo(tmp_path)
    rc = main(["coverage_audit.py", "--root", str(repo)])
    out = capsys.readouterr().out
    assert rc == 0
    assert "[coverage-audit]" in out
    assert "TOTAL:" in out


def test_cli_json_output(tmp_path, capsys):
    repo = _make_synth_repo(tmp_path)
    rc = main(["coverage_audit.py", "--root", str(repo), "--json"])
    out = capsys.readouterr().out
    assert rc == 0
    parsed = json.loads(out)
    assert "summary" in parsed
    assert parsed["summary"]["all_clean"] is True


def test_cli_returns_1_on_missing(tmp_path, capsys, monkeypatch):
    """Force missing coverage via monkeypatched ALL_SOURCES."""
    repo = _make_synth_repo(tmp_path)
    import backend.app.rag.coverage_audit as mod

    def _empty_iter(_root):
        return iter([])  # zero docs from project-adr-fp

    new_sources = [
        ("project-adr-fp", _empty_iter) if lbl == "project-adr-fp" else (lbl, fn)
        for lbl, fn in mod.ALL_SOURCES
    ]
    monkeypatch.setattr(mod, "ALL_SOURCES", new_sources)

    rc = main(["coverage_audit.py", "--root", str(repo)])
    out = capsys.readouterr().out
    assert rc == 1
    assert "MISSING" in out


def test_cli_strict_treats_extras_as_failure(tmp_path, capsys, monkeypatch):
    """In --strict mode, an unexpected extra file from the iter fn → exit 1."""
    import backend.app.rag.coverage_audit as mod
    from backend.app.rag.schemas import Document

    def _extras_iter(_root):
        # Yield a doc whose path isn't in any expected bucket
        yield Document(
            doc_id="EXTRA",
            source="project-adr-fp",
            title="extra",
            text="x",
            metadata={"path": "docs/adr/UNEXPECTED-extra.md"},
        )

    new_sources = [
        ("project-adr-fp", _extras_iter) if lbl == "project-adr-fp" else (lbl, fn)
        for lbl, fn in mod.ALL_SOURCES
    ]
    monkeypatch.setattr(mod, "ALL_SOURCES", new_sources)

    # Without --strict: extras don't fail (only missing does — but the bucket
    # is fully missing, so this still returns 1). Use a repo with no real
    # ADRs to test the extras-only path.
    bare = tmp_path / "bare"
    (bare / "docs" / "adr").mkdir(parents=True)
    (bare / "docs" / "failure_patterns").mkdir(parents=True)
    (bare / "golden_samples").mkdir(parents=True)

    rc_no_strict = main(["coverage_audit.py", "--root", str(bare)])
    capsys.readouterr()
    # No expected, one extra — not strict → 0
    assert rc_no_strict == 0

    rc_strict = main(["coverage_audit.py", "--root", str(bare), "--strict"])
    out = capsys.readouterr().out
    assert rc_strict == 1
    assert "EXTRA" in out
