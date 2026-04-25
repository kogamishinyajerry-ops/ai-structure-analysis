"""Tests for backend.app.well_harness.github_writeback (P2)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import httpx
import pytest

from backend.app.well_harness import github_writeback as gw


# ---------------------------------------------------------------------------
# build_run_summary_comment
# ---------------------------------------------------------------------------


def test_build_summary_minimal():
    body = gw.build_run_summary_comment(
        case_id="GS-001",
        verdict="ACCEPT",
        summary_text="All checks green.",
    )
    assert "well_harness run · GS-001 · **ACCEPT**" in body
    assert "All checks green." in body
    assert "Auto-posted" in body


def test_build_summary_with_all_fields():
    body = gw.build_run_summary_comment(
        case_id="GS-002",
        verdict="REJECT",
        summary_text="Stress check failed.",
        notion_url="https://www.notion.so/abc",
        commit_sha="e53b0f779815d0416764bf69a64f2d8cc339cba1",
        extra_lines=["- detail 1", "- detail 2"],
    )
    assert "GS-002" in body
    assert "REJECT" in body
    assert "Stress check failed." in body
    assert "e53b0f779815" in body
    assert "https://www.notion.so/abc" in body
    assert "- detail 1" in body
    assert "- detail 2" in body


def test_build_summary_strips_outer_whitespace():
    body = gw.build_run_summary_comment(
        case_id="X",
        verdict="V",
        summary_text="\n\n   internal preserved   \n\n",
    )
    assert "internal preserved" in body
    # ensure no excessive blank lines from raw input
    assert "\n\n\n\n" not in body


# ---------------------------------------------------------------------------
# _resolve_token
# ---------------------------------------------------------------------------


def test_resolve_token_from_gh_token(monkeypatch):
    monkeypatch.setenv("GH_TOKEN", "ghp_xxx")
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    assert gw._resolve_token() == "ghp_xxx"


def test_resolve_token_from_github_token(monkeypatch):
    monkeypatch.delenv("GH_TOKEN", raising=False)
    monkeypatch.setenv("GITHUB_TOKEN", "ghs_yyy")
    assert gw._resolve_token() == "ghs_yyy"


def test_resolve_token_falls_back_to_gh_cli(monkeypatch):
    monkeypatch.delenv("GH_TOKEN", raising=False)
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    with patch("backend.app.well_harness.github_writeback.shutil.which") as which:
        which.return_value = "/usr/bin/gh"
        with patch(
            "backend.app.well_harness.github_writeback.subprocess.check_output"
        ) as check_out:
            check_out.return_value = "gho_zzz\n"
            assert gw._resolve_token() == "gho_zzz"


def test_resolve_token_returns_none_when_unavailable(monkeypatch):
    monkeypatch.delenv("GH_TOKEN", raising=False)
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    with patch("backend.app.well_harness.github_writeback.shutil.which") as which:
        which.return_value = None
        assert gw._resolve_token() is None


# ---------------------------------------------------------------------------
# writeback_enabled
# ---------------------------------------------------------------------------


def test_writeback_enabled_true_when_token_set(monkeypatch):
    monkeypatch.setenv("GH_TOKEN", "x")
    assert gw.writeback_enabled() is True


def test_writeback_enabled_false_when_no_token(monkeypatch):
    monkeypatch.delenv("GH_TOKEN", raising=False)
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    with patch("backend.app.well_harness.github_writeback.shutil.which") as which:
        which.return_value = None
        assert gw.writeback_enabled() is False


# ---------------------------------------------------------------------------
# post_pr_comment — input validation
# ---------------------------------------------------------------------------


def test_post_rejects_empty_repo():
    r = gw.post_pr_comment(repo="", pr_number=1, body="hi", token="t")
    assert r.posted is False
    assert "invalid repo" in r.error


def test_post_rejects_repo_without_slash():
    r = gw.post_pr_comment(repo="solo", pr_number=1, body="hi", token="t")
    assert r.posted is False
    assert "invalid repo" in r.error


def test_post_rejects_zero_pr_number():
    r = gw.post_pr_comment(repo="o/r", pr_number=0, body="hi", token="t")
    assert r.posted is False
    assert "invalid pr_number" in r.error


def test_post_rejects_negative_pr_number():
    r = gw.post_pr_comment(repo="o/r", pr_number=-5, body="hi", token="t")
    assert r.posted is False


def test_post_rejects_empty_body():
    r = gw.post_pr_comment(repo="o/r", pr_number=1, body="", token="t")
    assert r.posted is False
    assert "empty body" in r.error


def test_post_rejects_whitespace_body():
    r = gw.post_pr_comment(repo="o/r", pr_number=1, body="   \n   ", token="t")
    assert r.posted is False


def test_post_no_token_no_op(monkeypatch):
    monkeypatch.delenv("GH_TOKEN", raising=False)
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    with patch("backend.app.well_harness.github_writeback.shutil.which") as which:
        which.return_value = None
        r = gw.post_pr_comment(repo="o/r", pr_number=1, body="hi")
    assert r.posted is False
    assert "no GitHub token" in r.error


# ---------------------------------------------------------------------------
# post_pr_comment — successful POST
# ---------------------------------------------------------------------------


def _mock_client_response(status_code: int, json_data: dict, text: str = ""):
    mock_resp = MagicMock()
    mock_resp.status_code = status_code
    mock_resp.json.return_value = json_data
    mock_resp.text = text or str(json_data)
    mock_client = MagicMock(spec=httpx.Client)
    mock_client.post.return_value = mock_resp
    return mock_client, mock_resp


def test_post_201_returns_comment_url():
    mock_client, mock_resp = _mock_client_response(
        201, {"html_url": "https://github.com/o/r/issues/1#comment-42"}
    )
    r = gw.post_pr_comment(
        repo="o/r", pr_number=1, body="hi there", token="t", client=mock_client
    )
    assert r.posted is True
    assert r.comment_url == "https://github.com/o/r/issues/1#comment-42"
    assert r.status_code == 201

    # Verify the request shape
    mock_client.post.assert_called_once()
    args, kwargs = mock_client.post.call_args
    assert args[0] == "https://api.github.com/repos/o/r/issues/1/comments"
    assert kwargs["headers"]["Authorization"] == "Bearer t"
    assert kwargs["headers"]["Accept"] == "application/vnd.github+json"
    assert kwargs["json"] == {"body": "hi there"}


def test_post_404_returns_error():
    mock_client, _ = _mock_client_response(404, {"message": "Not Found"}, "Not Found")
    r = gw.post_pr_comment(
        repo="o/r", pr_number=99999, body="hi", token="t", client=mock_client
    )
    assert r.posted is False
    assert r.status_code == 404
    assert "404" in r.error


def test_post_403_rate_limit_returns_error():
    mock_client, _ = _mock_client_response(
        403, {"message": "rate limited"}, "rate limited"
    )
    r = gw.post_pr_comment(
        repo="o/r", pr_number=1, body="hi", token="t", client=mock_client
    )
    assert r.posted is False
    assert r.status_code == 403


def test_post_handles_transport_error():
    mock_client = MagicMock(spec=httpx.Client)
    mock_client.post.side_effect = httpx.ConnectError("network down")
    r = gw.post_pr_comment(
        repo="o/r", pr_number=1, body="hi", token="t", client=mock_client
    )
    assert r.posted is False
    assert "transport error" in r.error
    assert "network down" in r.error


def test_post_uses_resolved_token_when_none_passed(monkeypatch):
    monkeypatch.setenv("GH_TOKEN", "from-env")
    mock_client, _ = _mock_client_response(
        201, {"html_url": "https://github.com/o/r/issues/1"}
    )
    gw.post_pr_comment(repo="o/r", pr_number=1, body="hi", client=mock_client)
    args, kwargs = mock_client.post.call_args
    assert kwargs["headers"]["Authorization"] == "Bearer from-env"


def test_post_long_body_truncates_error_message():
    """A very long error response shouldn't bloat the error string."""
    mock_client, _ = _mock_client_response(
        500, {"message": "boom"}, "x" * 10000
    )
    r = gw.post_pr_comment(
        repo="o/r", pr_number=1, body="hi", token="t", client=mock_client
    )
    assert r.posted is False
    # error message truncated to 200 chars of response body
    assert len(r.error) < 350
