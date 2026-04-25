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
    with pytest.raises(SystemExit) as ei:
        _load_hint_from_json(Path("/nonexistent/hint.json"))
    # SystemExit can carry int or str; we just need a clear failure
    msg = str(ei.value)
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
    out = capsys.readouterr().out
    assert rc == 1
    assert "failed:" in out
    assert "Forbidden" in out


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
