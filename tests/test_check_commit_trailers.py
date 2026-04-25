"""Tests for scripts/check_commit_trailers.py (FF-07 / HF5)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent
_SCRIPTS_DIR = _REPO_ROOT / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))


@pytest.fixture(scope="module")
def mod():
    import check_commit_trailers  # type: ignore[import-not-found]

    return check_commit_trailers


# ---------------------------------------------------------------------------
# check_commit — happy paths
# ---------------------------------------------------------------------------


def test_execution_by_trailer_accepted(mod):
    body = "Some commit message.\n\nExecution-by: claude-code-opus47\n"
    r = mod.check_commit("abc123", "subject", body)
    assert r.has_attribution
    assert r.attribution_value == "claude-code-opus47"
    assert r.violations == []


def test_co_authored_by_trailer_accepted(mod):
    body = "Some commit.\n\nCo-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>\n"
    r = mod.check_commit("abc123", "subject", body)
    assert r.has_attribution
    assert "Claude Opus 4.7" in r.attribution_value
    assert r.violations == []


def test_execution_by_with_subagent(mod):
    body = "x\n\nExecution-by: claude-code-opus47 · Subagent: gsd-planner-1\n"
    r = mod.check_commit("abc123", "subj", body)
    assert r.has_attribution
    assert r.violations == []


def test_codex_verified_valid_format(mod):
    body = """Subject

Body text.

Execution-by: claude-code-opus47
Codex-verified: ADR-011-r5@e53b0f7
"""
    r = mod.check_commit("abc123", "subj", body)
    assert r.has_codex_trailer
    assert r.codex_format_valid
    assert r.codex_value == "ADR-011-r5@e53b0f7"
    assert r.violations == []


def test_codex_verified_with_full_sha(mod):
    body = "x\n\nExecution-by: x\nCodex-verified: FF-06-r2@e53b0f779815d0416764bf69a64f2d8cc339cba1\n"
    r = mod.check_commit("abc123", "subj", body)
    assert r.codex_format_valid


def test_codex_verified_placeholder_allowed(mod):
    body = "x\n\nExecution-by: x\nCodex-verified: <claim-id>@HEAD\n"
    r = mod.check_commit("abc123", "subj", body)
    assert r.codex_format_valid

    body2 = "x\n\nExecution-by: x\nCodex-verified: ADR-013-r1@<sha>\n"
    r2 = mod.check_commit("abc123", "subj", body2)
    assert r2.codex_format_valid


def test_codex_omitted_is_fine(mod):
    """ADR-011: Codex-verified is conditional, not always required."""
    body = "Doc-only commit\n\nExecution-by: claude-code-opus47\n"
    r = mod.check_commit("abc123", "subj", body)
    assert not r.has_codex_trailer
    assert r.violations == []


# ---------------------------------------------------------------------------
# check_commit — violations
# ---------------------------------------------------------------------------


def test_no_attribution_trailer_violates(mod):
    body = "Some commit message with no trailers.\n"
    r = mod.check_commit("abc123", "subj", body)
    assert not r.has_attribution
    assert len(r.violations) == 1
    assert "missing execution-attribution" in r.violations[0]


def test_codex_invalid_format_violates(mod):
    body = "x\n\nExecution-by: x\nCodex-verified: not-a-valid-format\n"
    r = mod.check_commit("abc123", "subj", body)
    assert r.has_codex_trailer
    assert not r.codex_format_valid
    assert any("does not match" in v for v in r.violations)


def test_codex_value_with_short_sha_under_7_violates(mod):
    body = "x\n\nExecution-by: x\nCodex-verified: ADR-011@abc12\n"
    r = mod.check_commit("abc123", "subj", body)
    assert not r.codex_format_valid


def test_codex_value_no_at_sign_violates(mod):
    body = "x\n\nExecution-by: x\nCodex-verified: ADR-011-r5\n"
    r = mod.check_commit("abc123", "subj", body)
    assert not r.codex_format_valid


def test_both_violations_reported_independently(mod):
    """No attribution AND invalid Codex format should produce two violations."""
    body = "x\n\nCodex-verified: bogus\n"
    r = mod.check_commit("abc123", "subj", body)
    assert len(r.violations) == 2


# ---------------------------------------------------------------------------
# Multiple Co-Authored-By lines, case-insensitivity
# ---------------------------------------------------------------------------


def test_case_insensitive_attribution(mod):
    body = "x\n\nexecution-by: lowercase-allowed\n"
    r = mod.check_commit("abc123", "subj", body)
    assert r.has_attribution


def test_multiple_coauthors_first_match_wins(mod):
    body = (
        "x\n\nCo-Authored-By: Alice <a@x>\n"
        "Co-Authored-By: Bob <b@x>\n"
    )
    r = mod.check_commit("abc123", "subj", body)
    assert r.has_attribution
    # First match takes attribution_value
    assert "Alice" in r.attribution_value


# ---------------------------------------------------------------------------
# JSON output
# ---------------------------------------------------------------------------


def test_to_json_shape(mod):
    body_ok = "x\n\nExecution-by: claude\n"
    body_bad = "no trailers\n"
    results = [mod.check_commit("a", "s1", body_ok), mod.check_commit("b", "s2", body_bad)]
    import json

    out = json.loads(mod.to_json(results))
    assert len(out) == 2
    assert out[0]["has_attribution"] is True
    assert out[1]["has_attribution"] is False
    assert "violations" in out[1]


# ---------------------------------------------------------------------------
# main() — integration with a temp git repo
# ---------------------------------------------------------------------------


def test_main_reports_violations_via_subprocess(mod, tmp_path, monkeypatch, capsys):
    """End-to-end: spawn a temp git repo, make 2 commits (one good, one bad)."""
    import subprocess

    repo = tmp_path / "r"
    repo.mkdir()
    monkeypatch.chdir(repo)
    subprocess.run(["git", "init", "-q", "-b", "main"], check=True)
    subprocess.run(["git", "config", "user.email", "t@t"], check=True)
    subprocess.run(["git", "config", "user.name", "t"], check=True)
    subprocess.run(["git", "config", "commit.gpgsign", "false"], check=True)

    # Initial commit (good)
    (repo / "a").write_text("a")
    subprocess.run(["git", "add", "a"], check=True)
    subprocess.run(
        ["git", "commit", "-q", "-m", "first\n\nExecution-by: claude-code-opus47\n"],
        check=True,
    )

    # Second commit (bad — no trailer)
    (repo / "b").write_text("b")
    subprocess.run(["git", "add", "b"], check=True)
    subprocess.run(["git", "commit", "-q", "-m", "second"], check=True)

    rc = mod.main(["check_commit_trailers.py", "HEAD~1..HEAD"])
    assert rc == 1
    out = capsys.readouterr().out
    assert "FAIL" in out
    assert "Summary: 0/1" in out


def test_main_passes_when_all_good(mod, tmp_path, monkeypatch, capsys):
    import subprocess

    repo = tmp_path / "r2"
    repo.mkdir()
    monkeypatch.chdir(repo)
    subprocess.run(["git", "init", "-q", "-b", "main"], check=True)
    subprocess.run(["git", "config", "user.email", "t@t"], check=True)
    subprocess.run(["git", "config", "user.name", "t"], check=True)
    subprocess.run(["git", "config", "commit.gpgsign", "false"], check=True)

    (repo / "a").write_text("a")
    subprocess.run(["git", "add", "a"], check=True)
    subprocess.run(
        ["git", "commit", "-q", "-m", "x\n\nCo-Authored-By: Claude <noreply@anthropic.com>\n"],
        check=True,
    )

    rc = mod.main(["check_commit_trailers.py", "HEAD"])
    out = capsys.readouterr().out
    assert "OK" in out
    assert rc == 0


def test_main_json_mode(mod, tmp_path, monkeypatch, capsys):
    import json
    import subprocess

    repo = tmp_path / "r3"
    repo.mkdir()
    monkeypatch.chdir(repo)
    subprocess.run(["git", "init", "-q", "-b", "main"], check=True)
    subprocess.run(["git", "config", "user.email", "t@t"], check=True)
    subprocess.run(["git", "config", "user.name", "t"], check=True)
    subprocess.run(["git", "config", "commit.gpgsign", "false"], check=True)

    (repo / "a").write_text("a")
    subprocess.run(["git", "add", "a"], check=True)
    subprocess.run(
        ["git", "commit", "-q", "-m", "x\n\nExecution-by: claude\n"],
        check=True,
    )

    rc = mod.main(["check_commit_trailers.py", "--json", "HEAD"])
    out = capsys.readouterr().out
    parsed = json.loads(out)
    assert isinstance(parsed, list)
    assert parsed[0]["has_attribution"] is True
    assert rc == 0
