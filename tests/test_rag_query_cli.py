"""Tests for backend.app.rag.query_cli — the operator-facing query CLI."""

from __future__ import annotations

from pathlib import Path

import pytest

try:
    from backend.app.rag.query_cli import _format_result_line, main
    from backend.app.rag.sources import ALL_SOURCES
except ImportError as e:
    pytest.skip(f"rag.query_cli imports failed: {e}", allow_module_level=True)


# ---------------------------------------------------------------------------
# Synthetic-repo fixture (mirrors test_rag_cli.py)
# ---------------------------------------------------------------------------


def _make_synth_repo(tmp_path: Path) -> Path:
    gs = tmp_path / "golden_samples" / "GS-X"
    gs.mkdir(parents=True)
    (gs / "README.md").write_text("# GS-X\nUNIQUE_TOKEN_AAAAA cantilever beam theory body.\n")
    (gs / "x_theory.py").write_text("# theory script with UNIQUE_TOKEN_BBBBB\n")

    adr = tmp_path / "docs" / "adr"
    adr.mkdir(parents=True)
    (adr / "ADR-100-test.md").write_text("# ADR-100: Test\nUNIQUE_TOKEN_CCCCC body content.\n")

    fp = tmp_path / "docs" / "failure_patterns"
    fp.mkdir(parents=True)
    (fp / "FP-100-test.md").write_text(
        "---\nid: FP-100\nstatus: proposed\n---\n# FP-100\nUNIQUE_TOKEN_DDDDD body\n"
    )
    return tmp_path


# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------


def test_query_required(capsys):
    with pytest.raises(SystemExit) as exc_info:
        main(["query_cli.py"])
    # argparse exits 2 on missing required arg
    assert exc_info.value.code == 2


def test_help_exits_zero():
    with pytest.raises(SystemExit) as exc_info:
        main(["query_cli.py", "--help"])
    assert exc_info.value.code == 0


def test_unknown_embedder_systemexit(tmp_path):
    with pytest.raises(SystemExit):
        main(
            [
                "query_cli.py",
                "--query",
                "anything",
                "--embedder",
                "not-real",
                "--root",
                str(tmp_path),
            ]
        )


def test_negative_k_returns_2(tmp_path, capsys):
    rc = main(
        [
            "query_cli.py",
            "--query",
            "anything",
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
            "query_cli.py",
            "--query",
            "anything",
            "--root",
            str(tmp_path),
            "--source-filter",
            "bogus-label",
        ]
    )
    err = capsys.readouterr().err
    assert rc == 2
    assert "unknown --source-filter" in err


# ---------------------------------------------------------------------------
# End-to-end against synthetic repo (mock embedder, in-memory ingest)
# ---------------------------------------------------------------------------


def test_query_synth_repo_returns_results(tmp_path, capsys):
    repo = _make_synth_repo(tmp_path)
    rc = main(
        [
            "query_cli.py",
            "--query",
            "UNIQUE_TOKEN_AAAAA cantilever",
            "--root",
            str(repo),
            "--k",
            "3",
        ]
    )
    out = capsys.readouterr().out
    assert rc == 0
    assert "result(s)" in out
    assert "score=" in out


def test_query_no_ingest_yields_empty(tmp_path, capsys):
    """--no-ingest with mock embedder = empty store = exit 1."""
    repo = _make_synth_repo(tmp_path)
    rc = main(
        [
            "query_cli.py",
            "--query",
            "anything",
            "--root",
            str(repo),
            "--no-ingest",
        ]
    )
    out = capsys.readouterr().out
    assert rc == 1
    assert "no results" in out


def test_query_source_filter_restricts(tmp_path, capsys):
    repo = _make_synth_repo(tmp_path)
    rc = main(
        [
            "query_cli.py",
            "--query",
            "UNIQUE_TOKEN",
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
    # Every result line tags the source — only gs-theory should appear
    for line in out.splitlines():
        if line.lstrip().startswith("#") and "[" in line and "]" in line:
            assert "gs-theory" in line


def test_query_real_repo_smoke():
    """Real repo: a query that should match something in the corpus."""
    repo_root = Path(__file__).resolve().parent.parent
    rc = main(
        [
            "query_cli.py",
            "--query",
            "ADR-011 governance",
            "--root",
            str(repo_root),
            "--k",
            "5",
        ]
    )
    # rc may be 0 (results found) — mock embedder usually returns ≥1 hit
    # for a corpus this size. If it's 1 (empty), still acceptable as a
    # smoke since mock has no semantic similarity guarantee.
    assert rc in (0, 1)


# ---------------------------------------------------------------------------
# bge-m3 path (deps may be missing — gate accordingly)
# ---------------------------------------------------------------------------


def test_bge_m3_requires_persist_dir():
    with pytest.raises(SystemExit):
        main(
            [
                "query_cli.py",
                "--query",
                "anything",
                "--embedder",
                "bge-m3",
            ]
        )


# ---------------------------------------------------------------------------
# _format_result_line — output contract
# ---------------------------------------------------------------------------


def test_format_result_line_truncates_long_snippets():
    long_text = "x" * 500
    line = _format_result_line(0, 0.123, "src", "abc:0", long_text)
    assert "..." in line
    assert "x" * 117 in line


def test_format_result_line_collapses_newlines():
    text = "line one\nline two\nline three"
    line = _format_result_line(2, 0.5, "src", "abc:2", text)
    assert "\n      " in line  # only the prefix newline before the snippet
    # snippet itself should not contain raw newlines
    snippet_part = line.split("\n      ", 1)[1]
    assert "\n" not in snippet_part


def test_format_result_line_includes_rank_and_score():
    line = _format_result_line(0, 0.987, "gs-theory", "GS-001:0", "snippet")
    assert "#1" in line
    assert "0.987" in line
    assert "gs-theory" in line
    assert "GS-001:0" in line


# ---------------------------------------------------------------------------
# Stdout/stderr discipline
# ---------------------------------------------------------------------------


def test_results_go_to_stdout(tmp_path, capsys):
    repo = _make_synth_repo(tmp_path)
    main(
        [
            "query_cli.py",
            "--query",
            "UNIQUE_TOKEN_AAAAA",
            "--root",
            str(repo),
        ]
    )
    captured = capsys.readouterr()
    assert "query-rag" in captured.out
    assert captured.err == "" or captured.err.strip() == ""


# ---------------------------------------------------------------------------
# Registry coverage — every source label is queryable
# ---------------------------------------------------------------------------


def test_every_registered_source_can_be_filter(tmp_path, capsys):
    repo = _make_synth_repo(tmp_path)
    for label, _ in ALL_SOURCES:
        rc = main(
            [
                "query_cli.py",
                "--query",
                "anything",
                "--root",
                str(repo),
                "--source-filter",
                label,
            ]
        )
        capsys.readouterr()  # drain
        assert rc in (0, 1)  # 1 = no hits is fine; we only assert no crash


# ---------------------------------------------------------------------------
# --json output mode
# ---------------------------------------------------------------------------


def test_json_with_results(tmp_path, capsys):
    import json as _json

    repo = _make_synth_repo(tmp_path)
    rc = main(
        [
            "query_cli.py",
            "--query",
            "UNIQUE_TOKEN_AAAAA",
            "--root",
            str(repo),
            "--k",
            "3",
            "--json",
        ]
    )
    out = capsys.readouterr().out
    assert rc == 0
    parsed = _json.loads(out)
    assert parsed["query"] == "UNIQUE_TOKEN_AAAAA"
    assert parsed["k"] == 3
    assert parsed["source_filter"] is None
    assert "embedder" in parsed
    assert isinstance(parsed["result_count"], int)
    assert isinstance(parsed["results"], list)
    if parsed["results"]:
        first = parsed["results"][0]
        assert "rank" in first and "score" in first and "source" in first
        assert "chunk_id" in first and "text" in first


def test_json_empty_returns_1(tmp_path, capsys):
    import json as _json

    repo = _make_synth_repo(tmp_path)
    rc = main(
        [
            "query_cli.py",
            "--query",
            "anything",
            "--root",
            str(repo),
            "--no-ingest",
            "--json",
        ]
    )
    out = capsys.readouterr().out
    assert rc == 1  # empty store
    parsed = _json.loads(out)
    assert parsed["result_count"] == 0
    assert parsed["results"] == []


def test_json_source_filter_field(tmp_path, capsys):
    import json as _json

    repo = _make_synth_repo(tmp_path)
    rc = main(
        [
            "query_cli.py",
            "--query",
            "UNIQUE_TOKEN",
            "--root",
            str(repo),
            "--source-filter",
            "gs-theory",
            "--json",
        ]
    )
    out = capsys.readouterr().out
    assert rc in (0, 1)
    parsed = _json.loads(out)
    assert parsed["source_filter"] == "gs-theory"
    for r in parsed["results"]:
        assert r["source"] == "gs-theory"


def test_json_single_record(tmp_path, capsys):
    """Output must be exactly one JSON object — no banner, no trailing text."""
    import json as _json

    repo = _make_synth_repo(tmp_path)
    main(
        [
            "query_cli.py",
            "--query",
            "anything",
            "--root",
            str(repo),
            "--json",
        ]
    )
    out = capsys.readouterr().out.strip()
    parsed = _json.loads(out)
    assert isinstance(parsed, dict)
