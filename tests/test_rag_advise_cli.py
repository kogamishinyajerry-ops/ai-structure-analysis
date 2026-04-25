"""Tests for backend.app.rag.advise_cli."""

from __future__ import annotations

from pathlib import Path

import pytest

try:
    from backend.app.rag.advise_cli import _format_hit, main
    from backend.app.rag.sources import ALL_SOURCES
except ImportError as e:
    pytest.skip(f"advise_cli imports failed: {e}", allow_module_level=True)


# ---------------------------------------------------------------------------
# Synthetic-repo fixture
# ---------------------------------------------------------------------------


def _make_synth_repo(tmp_path: Path) -> Path:
    gs = tmp_path / "golden_samples" / "GS-X"
    gs.mkdir(parents=True)
    (gs / "README.md").write_text("# GS-X\nUNIQUE_TOKEN cantilever solver convergence body.\n")
    (gs / "x_theory.py").write_text("# theory script with UNIQUE_TOKEN solver convergence\n")

    adr = tmp_path / "docs" / "adr"
    adr.mkdir(parents=True)
    (adr / "ADR-100-test.md").write_text("# ADR-100: solver convergence body content.\n")

    fp = tmp_path / "docs" / "failure_patterns"
    fp.mkdir(parents=True)
    (fp / "FP-100-test.md").write_text(
        "---\nid: FP-100\nstatus: proposed\n---\n# FP-100\nsolver convergence Newton residual\n"
    )
    return tmp_path


# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------


def test_verdict_required():
    with pytest.raises(SystemExit) as exc_info:
        main(["advise_cli.py"])
    assert exc_info.value.code == 2


def test_help_exits_zero():
    with pytest.raises(SystemExit) as exc_info:
        main(["advise_cli.py", "--help"])
    assert exc_info.value.code == 0


def test_zero_k_returns_2(tmp_path, capsys):
    rc = main(
        [
            "advise_cli.py",
            "--verdict",
            "Reject",
            "--root",
            str(tmp_path),
            "--k",
            "0",
        ]
    )
    err = capsys.readouterr().err
    assert rc == 2
    assert "--k must be a positive integer" in err


def test_unknown_source_filter_returns_2(tmp_path, capsys):
    rc = main(
        [
            "advise_cli.py",
            "--verdict",
            "Reject",
            "--root",
            str(tmp_path),
            "--source-filter",
            "bogus-label",
        ]
    )
    err = capsys.readouterr().err
    assert rc == 2
    assert "unknown --source-filter" in err


def test_unknown_fault_warns_but_proceeds(tmp_path, capsys):
    """A fault not in FAULT_QUERY_SEEDS should warn but still run."""
    repo = _make_synth_repo(tmp_path)
    rc = main(
        [
            "advise_cli.py",
            "--verdict",
            "Reject",
            "--fault",
            "totally_made_up_fault",
            "--root",
            str(repo),
        ]
    )
    captured = capsys.readouterr()
    # Warning to stderr
    assert "not in FAULT_QUERY_SEEDS" in captured.err
    # rc 0 (results returned) or 1 (no hits) — both acceptable, never 2
    assert rc in (0, 1)


# ---------------------------------------------------------------------------
# End-to-end against synthetic repo
# ---------------------------------------------------------------------------


def test_advise_synth_repo_returns_results(tmp_path, capsys):
    repo = _make_synth_repo(tmp_path)
    rc = main(
        [
            "advise_cli.py",
            "--verdict",
            "Reject",
            "--fault",
            "solver_convergence",
            "--root",
            str(repo),
            "--k",
            "3",
        ]
    )
    out = capsys.readouterr().out
    assert rc == 0
    assert "hit(s)" in out
    assert "summary:" in out


def test_advise_no_ingest_yields_empty(tmp_path, capsys):
    repo = _make_synth_repo(tmp_path)
    rc = main(
        [
            "advise_cli.py",
            "--verdict",
            "Reject",
            "--fault",
            "solver_convergence",
            "--root",
            str(repo),
            "--no-ingest",
        ]
    )
    out = capsys.readouterr().out
    assert rc == 1
    assert "no corpus hits" in out


def test_advise_source_filter_restricts(tmp_path, capsys):
    repo = _make_synth_repo(tmp_path)
    rc = main(
        [
            "advise_cli.py",
            "--verdict",
            "Reject",
            "--fault",
            "solver_convergence",
            "--root",
            str(repo),
            "--k",
            "10",
            "--source-filter",
            "gs-theory",
        ]
    )
    out = capsys.readouterr().out
    assert rc == 0
    # Result hit lines look like "  #1  score=...  [<source>] ..."
    for line in out.splitlines():
        if "score=" in line and "[" in line:
            assert "gs-theory" in line


def test_advise_real_repo_smoke():
    repo_root = Path(__file__).resolve().parent.parent
    rc = main(
        [
            "advise_cli.py",
            "--verdict",
            "Reject",
            "--fault",
            "solver_convergence",
            "--root",
            str(repo_root),
            "--k",
            "5",
        ]
    )
    assert rc in (0, 1)


# ---------------------------------------------------------------------------
# bge-m3 path
# ---------------------------------------------------------------------------


def test_bge_m3_requires_persist_dir():
    with pytest.raises(SystemExit):
        main(
            [
                "advise_cli.py",
                "--verdict",
                "Reject",
                "--embedder",
                "bge-m3",
            ]
        )


# ---------------------------------------------------------------------------
# Output format invariants
# ---------------------------------------------------------------------------


def test_format_hit_truncates_long_snippet():
    long_text = "x" * 500
    line = _format_hit(0, 0.123, "src", "abc:0", long_text)
    assert "..." in line
    assert "x" * 107 in line


def test_format_hit_collapses_newlines():
    line = _format_hit(0, 0.5, "src", "abc:0", "line1\nline2\nline3")
    snippet_part = line.split("\n      ", 1)[1]
    assert "\n" not in snippet_part


def test_format_hit_has_rank_and_score():
    line = _format_hit(2, 0.987, "gs-theory", "GS-001:0", "snippet")
    assert "#3" in line
    assert "0.987" in line
    assert "gs-theory" in line


# ---------------------------------------------------------------------------
# Stdout/stderr discipline
# ---------------------------------------------------------------------------


def test_results_to_stdout_not_stderr(tmp_path, capsys):
    repo = _make_synth_repo(tmp_path)
    main(
        [
            "advise_cli.py",
            "--verdict",
            "Reject",
            "--fault",
            "solver_convergence",
            "--root",
            str(repo),
        ]
    )
    captured = capsys.readouterr()
    assert "advise-rag" in captured.out
    # On the success path stderr stays empty (no unknown-fault warning)
    assert captured.err == "" or captured.err.strip() == ""


# ---------------------------------------------------------------------------
# Every registered source label is a valid filter
# ---------------------------------------------------------------------------


def test_every_registered_source_is_valid_filter(tmp_path, capsys):
    repo = _make_synth_repo(tmp_path)
    for label, _ in ALL_SOURCES:
        rc = main(
            [
                "advise_cli.py",
                "--verdict",
                "Reject",
                "--fault",
                "solver_convergence",
                "--root",
                str(repo),
                "--source-filter",
                label,
            ]
        )
        capsys.readouterr()
        assert rc in (0, 1)


# ---------------------------------------------------------------------------
# Governance-biasing verdicts produce ADR-flavoured queries
# ---------------------------------------------------------------------------


def test_reject_verdict_query_includes_adr(tmp_path, capsys):
    repo = _make_synth_repo(tmp_path)
    main(
        [
            "advise_cli.py",
            "--verdict",
            "Reject",
            "--fault",
            "solver_convergence",
            "--root",
            str(repo),
        ]
    )
    out = capsys.readouterr().out
    assert "ADR" in out  # query line echoes the composed string


def test_accept_verdict_query_does_not_include_adr(tmp_path, capsys):
    repo = _make_synth_repo(tmp_path)
    main(
        [
            "advise_cli.py",
            "--verdict",
            "Accept",
            "--fault",
            "none",
            "--root",
            str(repo),
        ]
    )
    out = capsys.readouterr().out
    # Accept is not governance-biasing — query line should not have ADR
    # Find the query: line and check
    for line in out.splitlines():
        if line.startswith("[advise-rag] query:"):
            assert "ADR" not in line
            break
    else:
        pytest.fail("query: line not found in output")
