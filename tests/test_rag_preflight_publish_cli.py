"""Tests for backend.app.rag.preflight_publish_cli."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

try:
    from backend.app.rag import preflight_publish_cli
    from backend.app.rag.preflight_publish_cli import (
        _CliHint,
        _CliQuantity,
        _load_hint_from_json,
        _UsageError,
        main,
    )
except ImportError as e:
    pytest.skip(f"preflight_publish_cli imports failed: {e}", allow_module_level=True)


# ---------------------------------------------------------------------------
# Synthetic-repo fixture
# ---------------------------------------------------------------------------


def _make_synth_repo(tmp_path: Path) -> Path:
    gs = tmp_path / "golden_samples" / "GS-X"
    gs.mkdir(parents=True)
    (gs / "README.md").write_text("# GS-X\nbody\n")
    (gs / "x_theory.py").write_text("# theory\n")

    adr = tmp_path / "docs" / "adr"
    adr.mkdir(parents=True)
    (adr / "ADR-100-test.md").write_text("# ADR-100\nbody\n")

    fp = tmp_path / "docs" / "failure_patterns"
    fp.mkdir(parents=True)
    (fp / "FP-100.md").write_text("---\nid: FP-100\nstatus: proposed\n---\n# FP-100\nbody\n")
    return tmp_path


# ---------------------------------------------------------------------------
# Argparse edges
# ---------------------------------------------------------------------------


def test_verdict_required():
    with pytest.raises(SystemExit) as ei:
        main(["publish_cli.py"])
    assert ei.value.code == 2


def test_help_exits_zero():
    with pytest.raises(SystemExit) as ei:
        main(["publish_cli.py", "--help"])
    assert ei.value.code == 0


def test_negative_k_returns_2(tmp_path, capsys):
    rc = main(["publish_cli.py", "--verdict", "Reject", "--root", str(tmp_path), "--k", "0"])
    err = capsys.readouterr().err
    assert rc == 2
    assert "--k must be a positive integer" in err


def test_post_and_dry_run_mutually_exclusive(tmp_path, capsys):
    rc = main(
        [
            "publish_cli.py",
            "--verdict",
            "Reject",
            "--root",
            str(tmp_path),
            "--post",
            "--dry-run",
        ]
    )
    err = capsys.readouterr().err
    assert rc == 2
    assert "mutually exclusive" in err


def test_post_without_repo_pr_returns_2(tmp_path, capsys, monkeypatch):
    """--post without --repo or --pr must exit 2 BEFORE any network call."""
    repo = _make_synth_repo(tmp_path)

    def _fail_publish(*a, **k):
        raise AssertionError("publish_preflight should not be called")

    monkeypatch.setattr(preflight_publish_cli, "publish_preflight", _fail_publish)

    rc = main(["publish_cli.py", "--verdict", "Reject", "--root", str(repo), "--post"])
    err = capsys.readouterr().err
    assert rc == 2
    assert "--repo and --pr" in err


def test_unknown_fault_warns_but_proceeds(tmp_path, capsys):
    repo = _make_synth_repo(tmp_path)
    rc = main(
        [
            "publish_cli.py",
            "--verdict",
            "Reject",
            "--fault",
            "totally_made_up",
            "--root",
            str(repo),
        ]
    )
    captured = capsys.readouterr()
    assert "not in FAULT_QUERY_SEEDS" in captured.err
    assert rc == 0  # dry-run always 0 if it builds


# ---------------------------------------------------------------------------
# Dry-run path (default)
# ---------------------------------------------------------------------------


def test_dry_run_default_prints_markdown(tmp_path, capsys):
    repo = _make_synth_repo(tmp_path)
    rc = main(
        [
            "publish_cli.py",
            "--verdict",
            "Reject",
            "--fault",
            "solver_convergence",
            "--root",
            str(repo),
            "--case-id",
            "GS-X",
        ]
    )
    out = capsys.readouterr().out
    assert rc == 0
    assert "DRY-RUN" in out
    assert "## Preflight" in out
    assert "GS-X" in out


def test_dry_run_explicit_flag_works(tmp_path, capsys):
    repo = _make_synth_repo(tmp_path)
    rc = main(
        [
            "publish_cli.py",
            "--verdict",
            "Reject",
            "--root",
            str(repo),
            "--dry-run",
        ]
    )
    out = capsys.readouterr().out
    assert rc == 0
    assert "DRY-RUN (forced)" in out


def test_dry_run_advisor_only_no_quantities(tmp_path, capsys):
    """Without --hint-json, the preflight is advisor-only."""
    repo = _make_synth_repo(tmp_path)
    rc = main(
        [
            "publish_cli.py",
            "--verdict",
            "Reject",
            "--fault",
            "solver_convergence",
            "--root",
            str(repo),
        ]
    )
    out = capsys.readouterr().out
    assert rc == 0
    assert "_(no predictions)_" in out


# ---------------------------------------------------------------------------
# --hint-json
# ---------------------------------------------------------------------------


def test_hint_json_loads_quantities(tmp_path, capsys):
    repo = _make_synth_repo(tmp_path)
    hint_path = tmp_path / "hint.json"
    hint_path.write_text(
        json.dumps(
            {
                "case_id": "GS-001",
                "provider": "manual@v0",
                "quantities": [
                    {
                        "name": "max_displacement",
                        "value": 1.234,
                        "unit": "mm",
                        "confidence": "low",
                        "location": "free_end",
                    }
                ],
                "notes": "manual sketch",
            }
        )
    )
    rc = main(
        [
            "publish_cli.py",
            "--verdict",
            "Accept",
            "--fault",
            "none",
            "--root",
            str(repo),
            "--hint-json",
            str(hint_path),
        ]
    )
    out = capsys.readouterr().out
    assert rc == 0
    assert "max_displacement" in out
    assert "1.234" in out
    assert "manual@v0" in out
    assert "manual sketch" in out


def test_hint_json_missing_file_exits():
    """R2 (pre-emptive, mirrors advise_cli pattern): rc=2 via _UsageError
    with a `.message` attribute, not plain SystemExit("msg") rc=1."""
    with pytest.raises(SystemExit) as ei:
        _load_hint_from_json(Path("/nonexistent/hint.json"))
    assert ei.value.code == 2
    msg = getattr(ei.value, "message", "")
    assert "failed to read" in msg or "hint.json" in msg


def test_hint_json_bad_json_exits(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text("{not-valid")
    with pytest.raises(SystemExit):
        _load_hint_from_json(p)


def test_hint_json_not_object_exits(tmp_path):
    p = tmp_path / "list.json"
    p.write_text("[1, 2, 3]")
    with pytest.raises(SystemExit):
        _load_hint_from_json(p)


def test_hint_json_missing_case_id_exits(tmp_path):
    p = tmp_path / "no_case.json"
    p.write_text(json.dumps({"provider": "x", "quantities": []}))
    with pytest.raises(SystemExit):
        _load_hint_from_json(p)


def test_hint_json_quantities_must_be_list(tmp_path):
    p = tmp_path / "bad_qs.json"
    p.write_text(json.dumps({"case_id": "GS-1", "quantities": "not-a-list"}))
    with pytest.raises(SystemExit):
        _load_hint_from_json(p)


def test_hint_json_quantity_missing_fields_exits(tmp_path):
    p = tmp_path / "bad_q.json"
    p.write_text(
        json.dumps({"case_id": "GS-1", "quantities": [{"name": "x"}]})  # no value, no unit
    )
    with pytest.raises(SystemExit):
        _load_hint_from_json(p)


def test_hint_json_quantity_value_must_be_number(tmp_path):
    p = tmp_path / "bad_val.json"
    p.write_text(
        json.dumps(
            {
                "case_id": "GS-1",
                "quantities": [{"name": "x", "value": "not-a-num", "unit": "mm"}],
            }
        )
    )
    with pytest.raises(SystemExit):
        _load_hint_from_json(p)


def test_hint_json_minimal_valid(tmp_path):
    p = tmp_path / "ok.json"
    p.write_text(json.dumps({"case_id": "GS-1", "quantities": []}))
    hint = _load_hint_from_json(p)
    assert isinstance(hint, _CliHint)
    assert hint.case_id == "GS-1"
    assert hint.provider == "manual@v0"  # default
    assert hint.quantities == []


def test_hint_json_full_shape(tmp_path):
    p = tmp_path / "full.json"
    p.write_text(
        json.dumps(
            {
                "case_id": "GS-1",
                "provider": "fno@v1",
                "quantities": [
                    {"name": "u", "value": 1, "unit": "mm"},
                    {
                        "name": "s",
                        "value": 2.5,
                        "unit": "MPa",
                        "confidence": "medium",
                        "location": "tip",
                    },
                ],
                "notes": "n",
            }
        )
    )
    hint = _load_hint_from_json(p)
    assert hint.case_id == "GS-1"
    assert hint.provider == "fno@v1"
    assert len(hint.quantities) == 2
    assert hint.quantities[0].value == 1.0
    assert hint.quantities[1].confidence == "medium"
    assert hint.quantities[1].location == "tip"
    assert hint.notes == "n"


# ---------------------------------------------------------------------------
# --post path with monkeypatched publish_preflight
# ---------------------------------------------------------------------------


class _FakePublishResult:
    def __init__(
        self,
        posted,
        action="posted",
        comment_url="https://x/c/1",
        status_code=201,
        error=None,
        summary_was_empty=False,
    ):
        self.posted = posted
        self.action = action
        self.comment_url = comment_url
        self.status_code = status_code
        self.error = error
        self.summary_was_empty = summary_was_empty


def test_post_path_success_returns_0(tmp_path, capsys, monkeypatch):
    repo = _make_synth_repo(tmp_path)
    captured_args = {}

    def _fake_publish(summary, repo, pr_number, **kw):
        captured_args["repo"] = repo
        captured_args["pr_number"] = pr_number
        captured_args["mode"] = kw.get("mode")
        return _FakePublishResult(posted=True, action="posted")

    monkeypatch.setattr(preflight_publish_cli, "publish_preflight", _fake_publish)

    rc = main(
        [
            "publish_cli.py",
            "--verdict",
            "Reject",
            "--fault",
            "solver_convergence",
            "--root",
            str(repo),
            "--repo",
            "owner/repo",
            "--pr",
            "42",
            "--post",
        ]
    )
    out = capsys.readouterr().out
    assert rc == 0
    assert "posted: https://x/c/1" in out
    assert captured_args == {"repo": "owner/repo", "pr_number": 42, "mode": "post"}


def test_post_path_upsert_mode_passed(tmp_path, capsys, monkeypatch):
    repo = _make_synth_repo(tmp_path)
    captured = {}

    def _fake_publish(summary, repo, pr_number, **kw):
        captured["mode"] = kw.get("mode")
        return _FakePublishResult(posted=True, action="updated")

    monkeypatch.setattr(preflight_publish_cli, "publish_preflight", _fake_publish)

    rc = main(
        [
            "publish_cli.py",
            "--verdict",
            "Reject",
            "--fault",
            "solver_convergence",
            "--root",
            str(repo),
            "--repo",
            "o/r",
            "--pr",
            "1",
            "--post",
            "--mode",
            "upsert",
        ]
    )
    out = capsys.readouterr().out
    assert rc == 0
    assert captured["mode"] == "upsert"
    assert "updated:" in out


def test_post_path_failure_returns_1(tmp_path, capsys, monkeypatch):
    repo = _make_synth_repo(tmp_path)

    def _fake_publish(summary, repo, pr_number, **kw):
        return _FakePublishResult(
            posted=False, action=None, comment_url=None, status_code=403, error="Forbidden"
        )

    monkeypatch.setattr(preflight_publish_cli, "publish_preflight", _fake_publish)

    rc = main(
        [
            "publish_cli.py",
            "--verdict",
            "Reject",
            "--fault",
            "solver_convergence",
            "--root",
            str(repo),
            "--repo",
            "o/r",
            "--pr",
            "1",
            "--post",
        ]
    )
    captured = capsys.readouterr()
    assert rc == 1
    # R2 (post Codex R1 LOW on PR #66): failure messages now go to
    # stderr to keep the stdout/stderr split clean for piping.
    assert "failed:" in captured.err
    assert "Forbidden" in captured.err
    # Banner stays on stdout
    assert "verdict:" in captured.out
    assert "target:" in captured.out


def test_post_path_empty_summary_returns_0(tmp_path, capsys, monkeypatch):
    """summary_was_empty path: skipped, but rc=0 (not a failure)."""

    def _fake_publish(summary, repo, pr_number, **kw):
        return _FakePublishResult(
            posted=False,
            action=None,
            comment_url=None,
            error="summary is empty",
            summary_was_empty=True,
        )

    monkeypatch.setattr(preflight_publish_cli, "publish_preflight", _fake_publish)

    repo = _make_synth_repo(tmp_path)
    rc = main(
        [
            "publish_cli.py",
            "--verdict",
            "Reject",
            "--root",
            str(repo),
            "--repo",
            "o/r",
            "--pr",
            "1",
            "--post",
        ]
    )
    out = capsys.readouterr().out
    assert rc == 0
    assert "skipped" in out


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def test_cli_quantity_is_frozen():
    q = _CliQuantity(name="x", value=1.0, unit="mm")
    with pytest.raises((AttributeError, Exception)):
        q.name = "mutated"  # type: ignore[misc]


def test_cli_hint_default_provider_in_advisor_only_path(tmp_path, capsys):
    """No --hint-json: advisor-only@v0 should appear as the provider."""
    repo = _make_synth_repo(tmp_path)
    rc = main(
        [
            "publish_cli.py",
            "--verdict",
            "Reject",
            "--fault",
            "solver_convergence",
            "--root",
            str(repo),
        ]
    )
    out = capsys.readouterr().out
    assert rc == 0
    assert "advisor-only@v0" in out


# ---------------------------------------------------------------------------
# Pre-emptive R2 hardening (mirrors fixes from PR #62 / #65)
# ---------------------------------------------------------------------------


def test_usage_error_exits_with_code_2_not_1():
    """Plain SystemExit(str) exits rc=1; _UsageError standardizes rc=2."""
    err = _UsageError("test message")
    assert err.code == 2
    assert err.message == "test message"


def test_main_propagates_hint_json_failure_as_rc_2(tmp_path, capsys):
    """A bad --hint-json should surface as rc=2 (usage), not as a
    leaked traceback or rc=1."""
    repo = _make_synth_repo(tmp_path)
    bad = tmp_path / "bad.json"
    bad.write_text("{not-valid")
    rc = main(
        [
            "publish_cli.py",
            "--verdict",
            "Reject",
            "--fault",
            "solver_convergence",
            "--root",
            str(repo),
            "--hint-json",
            str(bad),
        ]
    )
    err = capsys.readouterr().err
    assert rc == 2
    assert "publish-rag" in err


def test_hint_json_oversize_rejected(tmp_path):
    """Pre-emptive R2: a >1 MiB hint payload must be rejected before
    json.loads buffers it into memory."""
    p = tmp_path / "huge.json"
    # Construct a JSON object whose serialized size exceeds the cap.
    p.write_text('{"pad": "' + ("x" * (preflight_publish_cli._HINT_JSON_MAX_BYTES + 1)) + '"}')
    with pytest.raises(SystemExit) as ei:
        _load_hint_from_json(p)
    assert ei.value.code == 2
    assert "bytes" in getattr(ei.value, "message", "")


def test_hint_json_bool_value_rejected(tmp_path):
    """Pre-emptive R2 (mirrors PR #65 _is_positive_int): bool is
    technically int-subclass but `value=True` is almost always a JSON
    typo. Reject explicitly."""
    p = tmp_path / "bool_value.json"
    p.write_text(
        json.dumps(
            {
                "case_id": "GS-1",
                "quantities": [{"name": "x", "value": True, "unit": "mm"}],
            }
        )
    )
    with pytest.raises(SystemExit) as ei:
        _load_hint_from_json(p)
    assert ei.value.code == 2
    assert "must be a number" in getattr(ei.value, "message", "")


def test_negative_pr_returns_2(tmp_path, capsys, monkeypatch):
    """Pre-emptive R2: --pr < 0 surfaces as rc=2 (usage) rather than
    relying on publish_preflight to reject it as rc=1."""
    repo = _make_synth_repo(tmp_path)

    # Stub publish_preflight so we can detect that it's NOT reached.
    called = {"n": 0}

    def _fake_publish(*a, **kw):
        called["n"] += 1
        raise AssertionError("publish_preflight should not be reached")

    monkeypatch.setattr(preflight_publish_cli, "publish_preflight", _fake_publish)

    rc = main(
        [
            "publish_cli.py",
            "--verdict",
            "Reject",
            "--fault",
            "solver_convergence",
            "--root",
            str(repo),
            "--repo",
            "owner/name",
            "--pr",
            "-5",
            "--post",
        ]
    )
    err = capsys.readouterr().err
    assert rc == 2
    assert called["n"] == 0
    assert "must be a positive integer" in err


def test_negative_max_advice_lines_returns_2(tmp_path, capsys):
    """Pre-emptive R2: --max-advice-lines < 0 surfaces as rc=2 instead
    of leaking ValueError from combine()."""
    repo = _make_synth_repo(tmp_path)
    rc = main(
        [
            "publish_cli.py",
            "--verdict",
            "Reject",
            "--fault",
            "solver_convergence",
            "--root",
            str(repo),
            "--max-advice-lines",
            "-1",
        ]
    )
    err = capsys.readouterr().err
    assert rc == 2
    assert ">= 0" in err


def test_advise_value_error_translates_to_rc_2(tmp_path, capsys):
    """Pre-emptive R2 (mirrors PR #62 fix): an unknown --verdict raises
    ValueError inside advise(); the CLI must translate to rc=2 + a
    clean stderr line, not leak a traceback."""
    repo = _make_synth_repo(tmp_path)
    rc = main(
        [
            "publish_cli.py",
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
    assert "publish-rag" in err


# ---------------------------------------------------------------------------
# R2 (post Codex R1 on PR #66) — new findings
# ---------------------------------------------------------------------------


def test_corpus_ingest_value_error_returns_rc_2(tmp_path, capsys, monkeypatch):
    """R2 (post Codex R1 HIGH on PR #66): _build_kb wraps ValueError /
    OSError from ALL_SOURCES. A duplicate doc_id (raised as ValueError
    inside KnowledgeBase.ingest) must surface as rc=2 with a clean
    stderr line, not a traceback / rc=1."""
    repo = _make_synth_repo(tmp_path)

    def _broken_build_kb(root):
        raise ValueError("duplicate doc_id: ADR-100 (synthesized)")

    monkeypatch.setattr(preflight_publish_cli, "_build_kb", _broken_build_kb)

    rc = main(
        [
            "publish_cli.py",
            "--verdict",
            "Reject",
            "--fault",
            "solver_convergence",
            "--root",
            str(repo),
        ]
    )
    err = capsys.readouterr().err
    assert rc == 2
    assert "corpus ingest failed" in err
    assert "duplicate" in err


def test_corpus_ingest_oserror_returns_rc_2(tmp_path, capsys, monkeypatch):
    """OSError (e.g. broken symlink) translates the same way."""
    repo = _make_synth_repo(tmp_path)

    def _broken_build_kb(root):
        raise OSError("symlink loop on /etc")

    monkeypatch.setattr(preflight_publish_cli, "_build_kb", _broken_build_kb)

    rc = main(
        [
            "publish_cli.py",
            "--verdict",
            "Reject",
            "--fault",
            "solver_convergence",
            "--root",
            str(repo),
        ]
    )
    err = capsys.readouterr().err
    assert rc == 2
    assert "corpus ingest failed" in err


@pytest.mark.parametrize("bad_qs", ["", 0, False, {}])
def test_hint_json_falsy_non_list_quantities_rejected(tmp_path, bad_qs):
    """R2 (post Codex R1 MEDIUM-1 on PR #66): pre-fix `or []` coerced
    "", 0, False, {} all into [] silently. Now they hit the type
    check and produce a rc=2 _UsageError."""
    p = tmp_path / "bad.json"
    p.write_text(json.dumps({"case_id": "GS-1", "quantities": bad_qs}))
    with pytest.raises(SystemExit) as ei:
        _load_hint_from_json(p)
    assert ei.value.code == 2
    assert "must be a list" in getattr(ei.value, "message", "")


def test_hint_json_null_quantities_treated_as_empty(tmp_path):
    """null / missing 'quantities' is the only acceptable empty form."""
    p = tmp_path / "null.json"
    p.write_text(json.dumps({"case_id": "GS-1", "quantities": None}))
    hint = _load_hint_from_json(p)
    assert hint.quantities == []


def test_hint_json_missing_quantities_treated_as_empty(tmp_path):
    p = tmp_path / "missing.json"
    p.write_text(json.dumps({"case_id": "GS-1"}))
    hint = _load_hint_from_json(p)
    assert hint.quantities == []


@pytest.mark.parametrize(
    "bad_repo",
    ["owneronly", "../etc/passwd", "owner/../etc", "  owner/repo  ", " ", "/leading-slash"],
)
def test_post_malformed_repo_returns_rc_2(tmp_path, capsys, monkeypatch, bad_repo):
    """R2 (post Codex R1 MEDIUM-2 on PR #66): malformed --repo
    pre-validates against _REPO_RE and surfaces as rc=2 instead of
    leaking through publish_preflight as rc=1."""
    repo = _make_synth_repo(tmp_path)

    def _fail(*a, **kw):
        raise AssertionError("publish_preflight should not be reached")

    monkeypatch.setattr(preflight_publish_cli, "publish_preflight", _fail)

    rc = main(
        [
            "publish_cli.py",
            "--verdict",
            "Reject",
            "--fault",
            "solver_convergence",
            "--root",
            str(repo),
            "--repo",
            bad_repo,
            "--pr",
            "1",
            "--post",
        ]
    )
    err = capsys.readouterr().err
    assert rc == 2
    assert "malformed" in err or "owner/name" in err


def test_post_zero_pr_returns_rc_2_with_specific_message(tmp_path, capsys, monkeypatch):
    """R2 (post Codex R1 MEDIUM-2 on PR #66): --pr 0 used to hit the
    generic 'requires --repo and --pr' branch (correct rc but
    misleading message). Now distinguished from missing."""
    repo = _make_synth_repo(tmp_path)

    def _fail(*a, **kw):
        raise AssertionError("publish_preflight should not be reached")

    monkeypatch.setattr(preflight_publish_cli, "publish_preflight", _fail)

    rc = main(
        [
            "publish_cli.py",
            "--verdict",
            "Reject",
            "--fault",
            "solver_convergence",
            "--root",
            str(repo),
            "--repo",
            "owner/repo",
            "--pr",
            "0",
            "--post",
        ]
    )
    err = capsys.readouterr().err
    assert rc == 2
    assert "must be a positive integer" in err


def test_post_upsert_with_empty_header_marker_returns_rc_2(tmp_path, capsys, monkeypatch):
    """R2 (post Codex R1 MEDIUM-2 on PR #66): --mode upsert + empty
    --header-marker pre-validates instead of failing at publish_preflight."""
    repo = _make_synth_repo(tmp_path)

    def _fail(*a, **kw):
        raise AssertionError("publish_preflight should not be reached")

    monkeypatch.setattr(preflight_publish_cli, "publish_preflight", _fail)

    rc = main(
        [
            "publish_cli.py",
            "--verdict",
            "Reject",
            "--fault",
            "solver_convergence",
            "--root",
            str(repo),
            "--repo",
            "owner/repo",
            "--pr",
            "1",
            "--post",
            "--mode",
            "upsert",
            "--header-marker",
            "",
        ]
    )
    err = capsys.readouterr().err
    assert rc == 2
    assert "header-marker" in err
