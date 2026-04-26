"""Tests for backend.app.rag.advise_cli."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

try:
    from backend.app.rag.advise_cli import _format_hit, _UsageError, main
    from backend.app.rag.reviewer_advisor import KNOWN_VERDICTS
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


def test_bge_m3_requires_persist_dir(capsys):
    """R2 (lifted from PR #59/#60): missing --persist-dir must fail with
    rc=2 BEFORE BgeM3Embedder() runs. main() catches _UsageError and
    translates it to a single [advise-rag] stderr line."""
    rc = main(
        [
            "advise_cli.py",
            "--verdict",
            "Reject",
            "--embedder",
            "bge-m3",
        ]
    )
    err = capsys.readouterr().err
    assert rc == 2
    assert "--persist-dir is required" in err
    assert err.count("[advise-rag]") == 1


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


# ---------------------------------------------------------------------------
# R2 (pre-emptive, lifted from PR #59 + #60 + #61 Codex R1 patterns)
#
# - rc=2 contract via _UsageError (not plain SystemExit("msg") which is rc=1)
# - cheap-validation-first: --persist-dir checked before BgeM3Embedder()
# - both bge-m3 imports AND constructors share one ImportError translator
# - mock corpus ValueError/OSError surfaces as rc=2
# - advise() ValueError (unknown verdict, etc.) surfaces as rc=2
# ---------------------------------------------------------------------------


def test_usage_error_exits_with_code_2_not_1():
    err = _UsageError("test message")
    assert err.code == 2
    assert err.message == "test message"


def test_unknown_verdict_translates_to_rc_2(tmp_path, capsys):
    """R2 (post Codex R1 MEDIUM on PR #62): unknown --verdict must
    fail BEFORE the KB is built (cheap-validation-first), not after.
    The CLI catches the rejection and translates to rc=2 + single
    stderr line, no traceback."""
    repo = _make_synth_repo(tmp_path)
    rc = main(
        [
            "advise_cli.py",
            "--verdict",
            "BogusVerdict",
            "--fault",
            "solver_convergence",
            "--root",
            str(repo),
        ]
    )
    err = capsys.readouterr().err
    assert rc == 2
    assert "unknown --verdict" in err
    assert err.count("[advise-rag]") == 1
    assert "Traceback" not in err


def test_lowercase_verdict_translates_to_rc_2(tmp_path, capsys):
    """'reject' is not canonical; pre-KB validation rejects with rc=2."""
    repo = _make_synth_repo(tmp_path)
    rc = main(
        [
            "advise_cli.py",
            "--verdict",
            "reject",
            "--fault",
            "solver_convergence",
            "--root",
            str(repo),
        ]
    )
    err = capsys.readouterr().err
    assert rc == 2
    assert "unknown --verdict" in err


def test_invalid_verdict_does_not_build_kb(tmp_path, monkeypatch, capsys):
    """R2 MED: invalid --verdict must short-circuit BEFORE _build_kb()
    runs. Without this, an operator typo would trigger a ~2GB
    BgeM3Embedder model download even though the run would fail anyway."""
    import backend.app.rag.advise_cli as amod

    build_kb_called: list[bool] = []
    orig = amod._build_kb

    def _spy(*args, **kwargs):
        build_kb_called.append(True)
        return orig(*args, **kwargs)

    monkeypatch.setattr(amod, "_build_kb", _spy)

    rc = amod.main(
        [
            "advise_cli.py",
            "--verdict",
            "BogusVerdict",
            "--fault",
            "solver_convergence",
            "--root",
            str(tmp_path),
        ]
    )
    capsys.readouterr()  # drain
    assert rc == 2
    assert (
        build_kb_called == []
    ), "_build_kb was called despite invalid verdict — cheap-validation-first violated"


def test_invalid_verdict_unknown_listed_in_error(tmp_path, capsys):
    """The pre-KB error message must list the canonical KNOWN_VERDICTS
    so the operator can recover from a typo without grepping source."""
    repo = _make_synth_repo(tmp_path)
    rc = main(
        [
            "advise_cli.py",
            "--verdict",
            "RejectButTypo",
            "--root",
            str(repo),
        ]
    )
    err = capsys.readouterr().err
    assert rc == 2
    for v in KNOWN_VERDICTS:
        assert v in err, f"{v!r} not listed in pre-KB error message"


def test_whitespace_verdict_normalized_then_runs(tmp_path, capsys):
    """' Reject ' must be normalized inside advise() and the run
    completes (governance bias fires; rc 0 or 1)."""
    repo = _make_synth_repo(tmp_path)
    rc = main(
        [
            "advise_cli.py",
            "--verdict",
            "  Reject  ",
            "--fault",
            "solver_convergence",
            "--root",
            str(repo),
        ]
    )
    err = capsys.readouterr().err
    # Must NOT raise; rc 0 (hits) or 1 (no hits) are both fine
    assert rc in (0, 1)
    assert "unknown verdict" not in err
    assert "Traceback" not in err


def test_header_echoes_normalized_verdict_not_padded(tmp_path, capsys):
    """R2 (post Codex R1 LOW on PR #62): the `[advise-rag] verdict:`
    header line must echo the canonical (stripped) form, matching the
    query / summary which use the normalized verdict. Pre-fix the
    header showed the raw padded value while query showed canonical."""
    repo = _make_synth_repo(tmp_path)
    main(
        [
            "advise_cli.py",
            "--verdict",
            "  Reject  ",
            "--fault",
            "solver_convergence",
            "--root",
            str(repo),
        ]
    )
    out = capsys.readouterr().out
    # Find the header verdict line
    header_lines = [ln for ln in out.splitlines() if ln.startswith("[advise-rag] verdict:")]
    assert header_lines, "no [advise-rag] verdict: header line found"
    # Must NOT contain the padded form; must contain the canonical form
    assert "  Reject  " not in header_lines[0]
    assert "'Reject'" in header_lines[0]


def test_unknown_fault_warning_text_describes_real_behavior(tmp_path, capsys):
    """R2 (post Codex R1 LOW on PR #62): the unknown-fault warning
    used to claim 'falling back to generic query', but `_build_query`
    actually uses the raw fault token verbatim. The fixed message
    must say 'using the raw fault token verbatim'."""
    repo = _make_synth_repo(tmp_path)
    main(
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
    err = capsys.readouterr().err
    assert "raw fault token verbatim" in err
    # Also confirm the misleading old wording is gone:
    assert "falling back to generic query" not in err


def test_bge_m3_chromadb_constructor_failure_rc_2(monkeypatch, capsys):
    """R2 (lifted from PR #60 MED-1): if `ChromaVectorStore.__init__`
    raises ImportError (chromadb missing inside the lazy-import body),
    main() must surface rc=2 + single line, not a traceback."""
    import backend.app.rag.advise_cli as amod

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

    rc = amod.main(
        [
            "advise_cli.py",
            "--verdict",
            "Reject",
            "--fault",
            "solver_convergence",
            "--embedder",
            "bge-m3",
            "--persist-dir",
            "/tmp/test-persist-advise",
        ]
    )
    err = capsys.readouterr().err
    assert rc == 2
    assert "bge-m3 backend unavailable" in err
    assert err.count("[advise-rag]") == 1
    assert "Traceback" not in err


def test_mock_corpus_value_error_rc_2(tmp_path, monkeypatch, capsys):
    """R2 (lifted from PR #60 MED-2): a source iterator raising
    ValueError must produce rc=2 + single stderr line, not a traceback."""
    import backend.app.rag.advise_cli as amod

    def bad_iter(repo_root):
        raise ValueError("simulated duplicate doc_id")
        yield  # pragma: no cover

    monkeypatch.setattr(amod, "ALL_SOURCES", [("bad-src", bad_iter)])

    rc = amod.main(
        [
            "advise_cli.py",
            "--verdict",
            "Reject",
            "--fault",
            "solver_convergence",
            "--root",
            str(tmp_path),
        ]
    )
    err = capsys.readouterr().err
    assert rc == 2
    assert "corpus ingest failed" in err
    assert err.count("[advise-rag]") == 1
    assert "Traceback" not in err


def test_mock_corpus_os_error_rc_2(tmp_path, monkeypatch, capsys):
    """R2 sibling: OSError on the mock path also maps to rc=2."""
    import backend.app.rag.advise_cli as amod

    def bad_iter(repo_root):
        raise OSError("simulated symlink escape")
        yield  # pragma: no cover

    monkeypatch.setattr(amod, "ALL_SOURCES", [("bad-src", bad_iter)])

    rc = amod.main(
        [
            "advise_cli.py",
            "--verdict",
            "Reject",
            "--fault",
            "solver_convergence",
            "--root",
            str(tmp_path),
        ]
    )
    err = capsys.readouterr().err
    assert rc == 2
    assert "corpus ingest failed" in err
    assert "Traceback" not in err


# ---------------------------------------------------------------------------
# --json output mode (P1-04b symmetry with publish_cli)
# ---------------------------------------------------------------------------


def test_json_output_emits_single_record(tmp_path, capsys):
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
            "--json",
        ]
    )
    out = capsys.readouterr().out
    assert rc in (0, 1)
    payload = json.loads(out.strip())
    assert isinstance(payload, dict)
    assert payload["verdict"] == "Reject"
    assert payload["fault"] == "solver_convergence"
    assert "embedder" in payload
    assert "query" in payload
    assert "hit_count" in payload
    assert "by_source" in payload
    assert "summary" in payload
    assert "results" in payload
    assert payload["hit_count"] == len(payload["results"])
    # No human banner mixed into stdout
    assert "[advise-rag]" not in out


def test_json_output_no_hits_returns_rc_1(tmp_path, capsys):
    """--json + advice.is_empty() → rc=1."""
    repo = tmp_path / "empty_repo"
    repo.mkdir()
    # No corpus content under --root → mock embedder returns nothing.
    rc = main(
        [
            "advise_cli.py",
            "--verdict",
            "Reject",
            "--fault",
            "solver_convergence",
            "--root",
            str(repo),
            "--json",
        ]
    )
    out = capsys.readouterr().out
    payload = json.loads(out.strip())
    if payload["hit_count"] == 0:
        assert rc == 1


def test_json_record_per_result_shape(tmp_path, capsys):
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
            "--json",
        ]
    )
    out = capsys.readouterr().out
    assert rc in (0, 1)
    payload = json.loads(out.strip())
    if payload["results"]:
        first = payload["results"][0]
        for required in ("rank", "score", "source", "chunk_id", "text"):
            assert required in first


def test_json_output_stderr_clean_on_success(tmp_path, capsys):
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
            "--json",
        ]
    )
    captured = capsys.readouterr()
    assert rc in (0, 1)
    assert captured.err == ""
    json.loads(captured.out.strip())
