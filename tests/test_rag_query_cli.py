"""Tests for backend.app.rag.query_cli — the operator-facing query CLI."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

try:
    from backend.app.rag.query_cli import (
        _build_kb_for_query,
        _format_result_line,
        _UsageError,
        main,
    )
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


def test_unknown_embedder_systemexit(tmp_path, capsys):
    """argparse rejects unknown --embedder choices BEFORE main()'s body
    runs (choices=['mock', 'bge-m3']), so this exits via argparse with
    rc=2. The _build_kb_for_query branch's _UsageError("unknown
    --embedder") is defensive only.
    """
    with pytest.raises(SystemExit) as exc_info:
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
    assert exc_info.value.code == 2


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


def test_bge_m3_requires_persist_dir(capsys):
    """R2 (post Codex R1 MEDIUM-3 lifted from cli.py): missing --persist-dir
    must fail with rc=2 BEFORE BgeM3Embedder() is constructed (which would
    download the model on a fresh env). main() catches _UsageError and
    translates it to a clean rc=2 with an [query-rag] prefixed message."""
    rc = main(
        [
            "query_cli.py",
            "--query",
            "anything",
            "--embedder",
            "bge-m3",
        ]
    )
    err = capsys.readouterr().err
    assert rc == 2
    assert "--persist-dir is required" in err


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


# ---------------------------------------------------------------------------
# R2 (pre-emptive, lifted from PR #59 Codex R1 findings on cli.py)
#
# These guard the rc=2 contract documented in the module docstring
# ("2 — usage error"). Before R2, _build_kb_for_query raised plain
# SystemExit("msg") which exits with status 1, conflicting with the
# documented contract. Now it raises _UsageError(msg) which super-inits
# with code=2 and carries .message; main() catches and prints once.
# ---------------------------------------------------------------------------


def test_usage_error_exits_with_code_2_not_1():
    """_UsageError must exit with code 2, never 1. This is the bug
    cli.py had pre-R2: plain SystemExit("msg") sets code=1."""
    err = _UsageError("test message")
    assert err.code == 2
    assert err.message == "test message"


def test_build_kb_bge_m3_raises_usage_error_not_systemexit_with_msg():
    """Cheap-validation-first: missing --persist-dir must raise the
    typed _UsageError BEFORE any heavy imports/model construction."""
    with pytest.raises(_UsageError) as exc_info:
        _build_kb_for_query(
            embedder_choice="bge-m3",
            persist_dir=None,
            collection="x",
            root=Path("/tmp"),
            ingest_in_memory=False,
        )
    assert exc_info.value.code == 2
    assert "--persist-dir" in exc_info.value.message


def test_build_kb_unknown_embedder_raises_usage_error():
    with pytest.raises(_UsageError) as exc_info:
        _build_kb_for_query(
            embedder_choice="not-real",
            persist_dir=None,
            collection="x",
            root=Path("/tmp"),
            ingest_in_memory=False,
        )
    assert exc_info.value.code == 2
    assert "unknown --embedder" in exc_info.value.message


def test_main_bge_m3_missing_persist_dir_prints_once(capsys):
    """The user-facing message must appear exactly once on stderr,
    not duplicated (one from _build_kb_for_query, another from main)."""
    rc = main(["query_cli.py", "--query", "anything", "--embedder", "bge-m3"])
    err = capsys.readouterr().err
    assert rc == 2
    # Single occurrence of the [query-rag] prefix → no double-print.
    assert err.count("[query-rag]") == 1
    assert "--persist-dir is required" in err


# ---------------------------------------------------------------------------
# R2 (post Codex R1 on PR #60, 2 MEDIUM findings)
#
# MED-1: bge-m3 fatal-error translation must cover BOTH the imports AND
#        the ChromaVectorStore(...) constructor (chromadb is lazy-imported
#        inside the constructor body, not at module import).
# MED-2: mock corpus-integrity failures (duplicate doc_id, symlink escape,
#        missing path) must surface as _UsageError → rc=2 + single stderr
#        line, mirroring cli.py's behavior. Without this, a bad --root
#        leaks a traceback and exits 1.
# ---------------------------------------------------------------------------


def test_bge_m3_chromadb_constructor_failure_routes_to_usage_error(monkeypatch):
    """R2 MED-1: simulate `ChromaVectorStore.__init__` raising ImportError
    (e.g. chromadb missing inside the constructor's lazy import).
    The fix folds the constructor into the same try/except as the module
    imports, so this maps to _UsageError(rc=2), not a raw traceback."""
    import backend.app.rag.query_cli as qmod

    # Stub out heavy imports so we test the wrapping logic, not deps.
    class _FakeEmbedder:
        embedder_id = "fake"

        def embed(self, texts):
            return [[0.0] * 8 for _ in texts]

    fake_embedder_mod = type("M", (), {"BgeM3Embedder": lambda: _FakeEmbedder()})

    def _bad_chroma(*args, **kwargs):
        raise ImportError("chromadb not installed (simulated)")

    fake_store_mod = type("M", (), {"ChromaVectorStore": _bad_chroma})

    monkeypatch.setitem(__import__("sys").modules, "backend.app.rag.embedder", fake_embedder_mod)
    monkeypatch.setitem(__import__("sys").modules, "backend.app.rag.store", fake_store_mod)

    with pytest.raises(qmod._UsageError) as exc_info:
        qmod._build_kb_for_query(
            embedder_choice="bge-m3",
            persist_dir=Path("/tmp/test-persist"),
            collection="test",
            root=Path("/tmp"),
            ingest_in_memory=False,
        )
    assert exc_info.value.code == 2
    assert "bge-m3 backend unavailable" in exc_info.value.message
    assert "chromadb not installed" in exc_info.value.message


def test_main_bge_m3_chromadb_missing_prints_single_line(monkeypatch, capsys):
    """End-to-end: main() must print exactly one [query-rag] stderr line
    for the chromadb-missing path, not a Python traceback."""
    import backend.app.rag.query_cli as qmod

    class _FakeEmbedder:
        embedder_id = "fake"

        def embed(self, texts):
            return [[0.0] * 8 for _ in texts]

    fake_embedder_mod = type("M", (), {"BgeM3Embedder": lambda: _FakeEmbedder()})

    def _bad_chroma(*args, **kwargs):
        raise ImportError("chromadb not installed (simulated)")

    fake_store_mod = type("M", (), {"ChromaVectorStore": _bad_chroma})

    monkeypatch.setitem(__import__("sys").modules, "backend.app.rag.embedder", fake_embedder_mod)
    monkeypatch.setitem(__import__("sys").modules, "backend.app.rag.store", fake_store_mod)

    rc = qmod.main(
        [
            "query_cli.py",
            "--query",
            "anything",
            "--embedder",
            "bge-m3",
            "--persist-dir",
            "/tmp/test-persist",
        ]
    )
    err = capsys.readouterr().err
    assert rc == 2
    assert err.count("[query-rag]") == 1
    assert "bge-m3 backend unavailable" in err
    assert "Traceback" not in err


def test_mock_corpus_value_error_routes_to_usage_error(tmp_path, monkeypatch, capsys):
    """R2 MED-2: a source iterator raising ValueError (e.g. duplicate
    doc_id, malformed frontmatter) must produce rc=2 + single stderr
    line, not a traceback. Mirrors cli.py's two-phase guard but inline
    in the mock-path ingest loop."""
    import backend.app.rag.query_cli as qmod

    def bad_iter(repo_root):
        raise ValueError("simulated duplicate doc_id")
        yield  # pragma: no cover — generator marker

    monkeypatch.setattr(qmod, "ALL_SOURCES", [("bad-src", bad_iter)])

    rc = qmod.main(
        [
            "query_cli.py",
            "--query",
            "anything",
            "--root",
            str(tmp_path),
        ]
    )
    err = capsys.readouterr().err
    assert rc == 2
    assert err.count("[query-rag]") == 1
    assert "corpus ingest failed" in err
    assert "simulated duplicate doc_id" in err
    assert "Traceback" not in err


def test_mock_corpus_os_error_routes_to_usage_error(tmp_path, monkeypatch, capsys):
    """R2 MED-2 sibling: OSError (e.g. symlink escape rejection) on the
    mock path must also map to rc=2."""
    import backend.app.rag.query_cli as qmod

    def bad_iter(repo_root):
        raise OSError("simulated path escape")
        yield  # pragma: no cover

    monkeypatch.setattr(qmod, "ALL_SOURCES", [("bad-src", bad_iter)])

    rc = qmod.main(["query_cli.py", "--query", "anything", "--root", str(tmp_path)])
    err = capsys.readouterr().err
    assert rc == 2
    assert "corpus ingest failed" in err
    assert "Traceback" not in err


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
# --json output mode (P1-04b symmetry with publish_cli)
# ---------------------------------------------------------------------------


def test_json_output_emits_single_record(tmp_path, capsys):
    repo = _make_synth_repo(tmp_path)
    rc = main(
        [
            "query_cli.py",
            "--query",
            "ADR",
            "--k",
            "5",
            "--root",
            str(repo),
            "--json",
        ]
    )
    out = capsys.readouterr().out
    assert rc in (0, 1)
    # Single JSON record per spec: stdout parses as one JSON, no extra lines.
    payload = json.loads(out.strip())
    assert isinstance(payload, dict)
    assert payload["query"] == "ADR"
    assert payload["k"] == 5
    assert "embedder" in payload
    assert "result_count" in payload
    assert "results" in payload
    assert payload["result_count"] == len(payload["results"])
    # No human banner mixed into stdout
    assert "[query-rag]" not in out


def test_json_output_no_results_returns_rc_1(tmp_path, capsys):
    """R2 NIT (post Codex R1 on PR #67): --json + actually empty KB →
    rc=1 with empty results array.

    Pre-fix this test ran against a populated mock KB which always
    returned top-k candidates, so the rc=1 branch was effectively
    untested. Now we use --no-ingest against an empty repo so
    KnowledgeBase.query returns [] deterministically."""
    empty_repo = tmp_path / "empty_repo"
    empty_repo.mkdir()
    rc = main(
        [
            "query_cli.py",
            "--query",
            "anything",
            "--root",
            str(empty_repo),
            "--json",
            "--no-ingest",
        ]
    )
    out = capsys.readouterr().out
    payload = json.loads(out.strip())
    assert rc == 1
    assert payload["result_count"] == 0
    assert payload["results"] == []


def test_json_record_has_per_result_shape(tmp_path, capsys):
    repo = _make_synth_repo(tmp_path)
    rc = main(
        [
            "query_cli.py",
            "--query",
            "ADR",
            "--k",
            "5",
            "--root",
            str(repo),
            "--json",
        ]
    )
    out = capsys.readouterr().out
    assert rc in (0, 1)
    payload = json.loads(out.strip())
    if payload["results"]:
        first = payload["results"][0]
        for required in ("rank", "score", "source", "chunk_id", "text"):
            assert required in first, f"missing {required} in result row"
        assert isinstance(first["rank"], int)
        assert isinstance(first["score"], int | float)
        assert isinstance(first["text"], str)


def test_json_output_stderr_clean_on_success(tmp_path, capsys):
    """JSON path: success leaves stderr empty (no banner crossover)."""
    repo = _make_synth_repo(tmp_path)
    rc = main(
        [
            "query_cli.py",
            "--query",
            "ADR",
            "--root",
            str(repo),
            "--json",
        ]
    )
    captured = capsys.readouterr()
    assert rc in (0, 1)
    assert captured.err == ""
    json.loads(captured.out.strip())  # parses clean
