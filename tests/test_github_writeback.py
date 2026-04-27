"""Tests for app.well_harness.github_writeback (P2)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import httpx
import pytest
from app.well_harness import github_writeback as gw

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
    with patch("app.well_harness.github_writeback.shutil.which") as which:
        which.return_value = "/usr/bin/gh"
        with patch("app.well_harness.github_writeback.subprocess.check_output") as check_out:
            check_out.return_value = "gho_zzz\n"
            assert gw._resolve_token() == "gho_zzz"


def test_resolve_token_returns_none_when_unavailable(monkeypatch):
    monkeypatch.delenv("GH_TOKEN", raising=False)
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    with patch("app.well_harness.github_writeback.shutil.which") as which:
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
    with patch("app.well_harness.github_writeback.shutil.which") as which:
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
    with patch("app.well_harness.github_writeback.shutil.which") as which:
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
    r = gw.post_pr_comment(repo="o/r", pr_number=1, body="hi there", token="t", client=mock_client)
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
    r = gw.post_pr_comment(repo="o/r", pr_number=99999, body="hi", token="t", client=mock_client)
    assert r.posted is False
    assert r.status_code == 404
    assert "404" in r.error


def test_post_403_rate_limit_returns_error():
    mock_client, _ = _mock_client_response(403, {"message": "rate limited"}, "rate limited")
    r = gw.post_pr_comment(repo="o/r", pr_number=1, body="hi", token="t", client=mock_client)
    assert r.posted is False
    assert r.status_code == 403


def test_post_handles_transport_error():
    mock_client = MagicMock(spec=httpx.Client)
    mock_client.post.side_effect = httpx.ConnectError("network down")
    r = gw.post_pr_comment(repo="o/r", pr_number=1, body="hi", token="t", client=mock_client)
    assert r.posted is False
    assert "transport error" in r.error
    assert "network down" in r.error


def test_post_uses_resolved_token_when_none_passed(monkeypatch):
    monkeypatch.setenv("GH_TOKEN", "from-env")
    mock_client, _ = _mock_client_response(201, {"html_url": "https://github.com/o/r/issues/1"})
    gw.post_pr_comment(repo="o/r", pr_number=1, body="hi", client=mock_client)
    args, kwargs = mock_client.post.call_args
    assert kwargs["headers"]["Authorization"] == "Bearer from-env"


def test_post_long_body_truncates_error_message():
    """A very long error response shouldn't bloat the error string."""
    mock_client, _ = _mock_client_response(500, {"message": "boom"}, "x" * 10000)
    r = gw.post_pr_comment(repo="o/r", pr_number=1, body="hi", token="t", client=mock_client)
    assert r.posted is False
    # error message truncated to 200 chars of response body
    assert len(r.error) < 350


# ---------------------------------------------------------------------------
# Pre-emptive R2 hardening tests — repo regex, body cap, token strip,
# subprocess timeout. Lifted from the same review patterns as PR #59/#60/#61.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "bad_repo",
    [
        "../etc/passwd",  # path traversal
        "owner/repo/extra",  # too many parts
        "owner/",  # empty name
        "/repo",  # empty owner
        "-bad/repo",  # owner can't lead with hyphen
        "owner with space/repo",  # space
        "owner/repo with space",  # space in name
        "owner//repo",  # double slash
    ],
)
def test_post_rejects_malformed_repo(bad_repo):
    """R2: pre-fix accepted any string with a slash, including
    `../etc/passwd`. The new _REPO_RE rejects path-traversing
    patterns and other GitHub-impossible identifiers."""
    r = gw.post_pr_comment(repo=bad_repo, pr_number=1, body="hi", token="t")
    assert r.posted is False
    assert "invalid repo" in r.error


@pytest.mark.parametrize(
    "good_repo",
    [
        "o/r",  # boundary 1-char owner/name
        "owner/repo",  # plain
        "Owner-Name/repo.with.dots",  # dots, hyphens
        "user_name/_under_score",  # underscores
        "kogamishinyajerry-ops/ai-structure-analysis",  # this repo
    ],
)
def test_post_accepts_valid_repo(good_repo):
    """Sanity-check: real-shape repos still pass through to the HTTP layer."""
    mock_client, _ = _mock_client_response(201, {"html_url": "https://github.com/x/y/issues/1#1"})
    r = gw.post_pr_comment(repo=good_repo, pr_number=1, body="hi", token="t", client=mock_client)
    assert r.posted is True


def test_post_truncates_body_over_64kb():
    """R2: GitHub caps issue/PR comment bodies at ~65,536 chars. Pre-fix
    a longer body got a 422 from the API. Now the writeback truncates
    with a clear suffix so the operator gets a useful summary instead."""
    mock_client, _ = _mock_client_response(201, {"html_url": "https://github.com/o/r/issues/1#1"})
    huge_body = "x" * (gw.GITHUB_COMMENT_BODY_LIMIT + 5000)
    gw.post_pr_comment(repo="o/r", pr_number=1, body=huge_body, token="t", client=mock_client)
    args, kwargs = mock_client.post.call_args
    sent_body = kwargs["json"]["body"]
    assert len(sent_body) <= gw.GITHUB_COMMENT_BODY_LIMIT
    assert "truncated by github_writeback" in sent_body


def test_post_does_not_truncate_body_under_limit():
    """Sanity: bodies within the limit are sent verbatim."""
    mock_client, _ = _mock_client_response(201, {"html_url": "https://github.com/o/r/issues/1#1"})
    body = "x" * 100
    gw.post_pr_comment(repo="o/r", pr_number=1, body=body, token="t", client=mock_client)
    args, kwargs = mock_client.post.call_args
    assert kwargs["json"]["body"] == body
    assert "truncated" not in kwargs["json"]["body"]


def test_resolve_token_strips_env_whitespace(monkeypatch):
    """R2: a `.env` file with `GH_TOKEN=ghp_xxx\\n` used to leak the
    newline into `Bearer ghp_xxx\\n`, which GitHub rejects. Now stripped."""
    monkeypatch.setenv("GH_TOKEN", "  ghp_padded_token  \n")
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    tok = gw._resolve_token()
    assert tok == "ghp_padded_token"


def test_resolve_token_empty_env_var_falls_through(monkeypatch):
    """R2: GH_TOKEN='   ' (whitespace only) must be treated as missing,
    not returned as a literal whitespace token."""
    monkeypatch.setenv("GH_TOKEN", "   ")
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.setattr(gw.shutil, "which", lambda _: None)
    tok = gw._resolve_token()
    assert tok is None


def test_resolve_token_subprocess_timeout_returns_none(monkeypatch):
    """R2: a hung `gh auth token` must not hang the publisher chain.
    The subprocess.timeout=5.0 raises TimeoutExpired which is caught."""
    import subprocess as sp

    monkeypatch.delenv("GH_TOKEN", raising=False)
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.setattr(gw.shutil, "which", lambda _: "/usr/bin/gh")

    def _hang(*args, **kwargs):
        raise sp.TimeoutExpired(cmd=args[0], timeout=kwargs.get("timeout", 5.0))

    monkeypatch.setattr(gw.subprocess, "check_output", _hang)
    tok = gw._resolve_token()
    assert tok is None


def test_resolve_token_subprocess_filenotfound_returns_none(monkeypatch):
    """R2 (post Codex R1 MEDIUM on PR #64): if `which()` says gh exists
    but the binary disappeared between the check and the call (concurrent
    uninstall, broken symlink), FileNotFoundError must NOT escape — must
    fall back to no-token-no-op."""
    monkeypatch.delenv("GH_TOKEN", raising=False)
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.setattr(gw.shutil, "which", lambda _: "/usr/bin/gh")

    def _missing(*args, **kwargs):
        raise FileNotFoundError("gh binary disappeared")

    monkeypatch.setattr(gw.subprocess, "check_output", _missing)
    tok = gw._resolve_token()
    assert tok is None


def test_resolve_token_subprocess_permission_error_returns_none(monkeypatch):
    """R2 sibling: PermissionError (gh found but not executable) must
    also fall back, not break writeback_enabled()."""
    monkeypatch.delenv("GH_TOKEN", raising=False)
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.setattr(gw.shutil, "which", lambda _: "/usr/bin/gh")

    def _denied(*args, **kwargs):
        raise PermissionError("gh not executable")

    monkeypatch.setattr(gw.subprocess, "check_output", _denied)
    tok = gw._resolve_token()
    assert tok is None


def test_writeback_enabled_returns_false_on_subprocess_oserror(monkeypatch):
    """R2 follow-up: writeback_enabled() must NEVER raise. Pre-fix it
    propagated FileNotFoundError from _resolve_token; now it returns False."""
    monkeypatch.delenv("GH_TOKEN", raising=False)
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.setattr(gw.shutil, "which", lambda _: "/usr/bin/gh")

    def _missing(*args, **kwargs):
        raise FileNotFoundError("gh binary disappeared")

    monkeypatch.setattr(gw.subprocess, "check_output", _missing)
    # Must not raise
    assert gw.writeback_enabled() is False


def test_post_201_with_malformed_json_does_not_raise():
    """R2 (post Codex R1 LOW on PR #64): the contract is "never raises
    on transport/response errors". A 201 with a non-JSON body used to
    leak ValueError/JSONDecodeError; now it returns a posted=True
    result with comment_url=None."""
    mock_resp = MagicMock()
    mock_resp.status_code = 201
    mock_resp.json.side_effect = ValueError("Expecting value: line 1 column 1")
    mock_resp.text = "<html>bad gateway content</html>"
    mock_client = MagicMock(spec=httpx.Client)
    mock_client.post.return_value = mock_resp

    r = gw.post_pr_comment(repo="o/r", pr_number=1, body="hi", token="t", client=mock_client)
    # Posted (the API returned 201); comment_url unknown but no exception
    assert r.posted is True
    assert r.comment_url is None
    assert r.status_code == 201


def test_post_201_with_non_dict_json_handles_gracefully():
    """R2 sibling: a 201 with valid JSON that is NOT a dict (e.g. a
    list, or a bare string) must not crash on `data.get(...)`."""
    mock_resp = MagicMock()
    mock_resp.status_code = 201
    mock_resp.json.return_value = ["unexpected", "list", "response"]
    mock_resp.text = "..."
    mock_client = MagicMock(spec=httpx.Client)
    mock_client.post.return_value = mock_resp

    r = gw.post_pr_comment(repo="o/r", pr_number=1, body="hi", token="t", client=mock_client)
    assert r.posted is True
    assert r.comment_url is None


# ---------------------------------------------------------------------------
# list_pr_comments — GET /repos/{repo}/issues/{n}/comments
# ---------------------------------------------------------------------------


def _mock_get_response(status_code: int, json_data, text: str = ""):
    mock_resp = MagicMock()
    mock_resp.status_code = status_code
    mock_resp.json.return_value = json_data
    mock_resp.text = text or str(json_data)
    mock_client = MagicMock(spec=httpx.Client)
    mock_client.get.return_value = mock_resp
    return mock_client, mock_resp


def test_list_pr_comments_200_returns_data():
    payload = [
        {"id": 1, "body": "hi"},
        {"id": 2, "body": "<!-- ai-fea-preflight -->\nold"},
    ]
    mock_client, _ = _mock_get_response(200, payload)
    out = gw.list_pr_comments(repo="o/r", pr_number=1, token="t", client=mock_client)
    assert out == payload
    # Verify the request shape
    args, kwargs = mock_client.get.call_args
    assert args[0] == "https://api.github.com/repos/o/r/issues/1/comments"
    assert kwargs["headers"]["Authorization"] == "Bearer t"
    # R2 (post Codex R1 MEDIUM-2 on PR #65): pagination enabled, so
    # `page` is included alongside `per_page`. A 2-comment payload is
    # shorter than per_page=100, so we short-circuit after page 1.
    assert kwargs["params"] == {"per_page": 100, "page": 1}


def test_list_pr_comments_404_returns_empty():
    """Never-raises contract: any non-200 returns []."""
    mock_client, _ = _mock_get_response(404, {"message": "Not Found"}, "Not Found")
    out = gw.list_pr_comments(repo="o/r", pr_number=99999, token="t", client=mock_client)
    assert out == []


def test_list_pr_comments_transport_error_returns_empty():
    mock_client = MagicMock(spec=httpx.Client)
    mock_client.get.side_effect = httpx.ConnectError("network down")
    out = gw.list_pr_comments(repo="o/r", pr_number=1, token="t", client=mock_client)
    assert out == []


def test_list_pr_comments_non_list_json_returns_empty():
    """If the API returns JSON that isn't a list (proxy mangle, etc.),
    return [] rather than confusing the caller."""
    mock_client, _ = _mock_get_response(200, {"unexpected": "object"})
    out = gw.list_pr_comments(repo="o/r", pr_number=1, token="t", client=mock_client)
    assert out == []


def test_list_pr_comments_malformed_json_returns_empty():
    """Bad JSON in the body must not raise."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.side_effect = ValueError("bad json")
    mock_resp.text = "<html>"
    mock_client = MagicMock(spec=httpx.Client)
    mock_client.get.return_value = mock_resp
    out = gw.list_pr_comments(repo="o/r", pr_number=1, token="t", client=mock_client)
    assert out == []


def test_list_pr_comments_invalid_repo_returns_empty():
    """Path-traversal repos rejected by _REPO_RE must NOT reach the
    HTTP layer — return [] without making a request."""
    mock_client = MagicMock(spec=httpx.Client)
    out = gw.list_pr_comments(repo="../etc/passwd", pr_number=1, token="t", client=mock_client)
    assert out == []
    mock_client.get.assert_not_called()


def test_list_pr_comments_invalid_pr_number_returns_empty():
    mock_client = MagicMock(spec=httpx.Client)
    out = gw.list_pr_comments(repo="o/r", pr_number=0, token="t", client=mock_client)
    assert out == []
    mock_client.get.assert_not_called()


def test_list_pr_comments_no_token_returns_empty(monkeypatch):
    monkeypatch.delenv("GH_TOKEN", raising=False)
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.setattr(gw.shutil, "which", lambda _: None)
    mock_client = MagicMock(spec=httpx.Client)
    out = gw.list_pr_comments(repo="o/r", pr_number=1, client=mock_client)
    assert out == []
    mock_client.get.assert_not_called()


# R2 (post Codex R1 MEDIUM-1 on PR #65): non-int IDs must NOT raise
# TypeError from `pr_number <= 0` — the never-raises contract requires
# returning [] for str / None / float / bool (bool is an int subclass
# but semantically wrong here).
@pytest.mark.parametrize("bad_pr", ["1", None, 1.5, True, False, [], {}, b"1"])
def test_list_pr_comments_non_int_pr_returns_empty(bad_pr):
    mock_client = MagicMock(spec=httpx.Client)
    out = gw.list_pr_comments(repo="o/r", pr_number=bad_pr, token="t", client=mock_client)
    assert out == []
    mock_client.get.assert_not_called()


def test_list_pr_comments_paginates_until_short_page():
    """R2 (post Codex R1 MEDIUM-2 on PR #65): when page 1 fills (100
    items), we request page 2. A short page 2 (<100) terminates the
    walk."""
    page1 = [{"id": i, "body": f"c{i}"} for i in range(1, 101)]
    page2 = [{"id": 101, "body": "<!-- ai-fea-preflight -->\nold"}]

    mock_resp_p1 = MagicMock()
    mock_resp_p1.status_code = 200
    mock_resp_p1.json.return_value = page1

    mock_resp_p2 = MagicMock()
    mock_resp_p2.status_code = 200
    mock_resp_p2.json.return_value = page2

    mock_client = MagicMock(spec=httpx.Client)
    mock_client.get.side_effect = [mock_resp_p1, mock_resp_p2]

    out = gw.list_pr_comments(repo="o/r", pr_number=1, token="t", client=mock_client)
    assert len(out) == 101
    assert out[-1]["id"] == 101
    assert mock_client.get.call_count == 2

    # Verify both calls had the right page param
    page_params = [c.kwargs["params"]["page"] for c in mock_client.get.call_args_list]
    assert page_params == [1, 2]


def test_list_pr_comments_pagination_caps_at_max_pages():
    """Safety: we never paginate past _LIST_COMMENTS_MAX_PAGES even if
    every page returns a full per_page worth of data. Bounds API spend."""
    full_page = [{"id": i, "body": f"c{i}"} for i in range(100)]

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = full_page

    mock_client = MagicMock(spec=httpx.Client)
    mock_client.get.return_value = mock_resp

    out = gw.list_pr_comments(repo="o/r", pr_number=1, token="t", client=mock_client)
    assert len(out) == 100 * gw._LIST_COMMENTS_MAX_PAGES
    assert mock_client.get.call_count == gw._LIST_COMMENTS_MAX_PAGES


def test_list_pr_comments_partial_page_returns_collected_data():
    """If page 2 returns 404 after page 1 succeeded, we keep the
    page-1 data instead of dropping everything."""
    page1 = [{"id": 1, "body": "c"} for _ in range(100)]

    mock_resp_p1 = MagicMock()
    mock_resp_p1.status_code = 200
    mock_resp_p1.json.return_value = page1

    mock_resp_p2 = MagicMock()
    mock_resp_p2.status_code = 502
    mock_resp_p2.json.return_value = {"message": "bad gateway"}
    mock_resp_p2.text = "bad gateway"

    mock_client = MagicMock(spec=httpx.Client)
    mock_client.get.side_effect = [mock_resp_p1, mock_resp_p2]

    out = gw.list_pr_comments(repo="o/r", pr_number=1, token="t", client=mock_client)
    assert len(out) == 100  # page-1 preserved
    assert mock_client.get.call_count == 2


def test_list_pr_comments_partial_page_transport_error_returns_collected():
    """Same as above for httpx.HTTPError on the second page."""
    page1 = [{"id": 1, "body": "c"} for _ in range(100)]

    mock_resp_p1 = MagicMock()
    mock_resp_p1.status_code = 200
    mock_resp_p1.json.return_value = page1

    mock_client = MagicMock(spec=httpx.Client)
    mock_client.get.side_effect = [mock_resp_p1, httpx.ConnectError("network down")]

    out = gw.list_pr_comments(repo="o/r", pr_number=1, token="t", client=mock_client)
    assert len(out) == 100
    assert mock_client.get.call_count == 2


# ---------------------------------------------------------------------------
# patch_pr_comment — PATCH /repos/{repo}/issues/comments/{id}
# ---------------------------------------------------------------------------


def _mock_patch_response(status_code: int, json_data, text: str = ""):
    mock_resp = MagicMock()
    mock_resp.status_code = status_code
    mock_resp.json.return_value = json_data
    mock_resp.text = text or str(json_data)
    mock_client = MagicMock(spec=httpx.Client)
    mock_client.patch.return_value = mock_resp
    return mock_client, mock_resp


def test_patch_pr_comment_200_returns_updated_url():
    mock_client, _ = _mock_patch_response(
        200, {"html_url": "https://github.com/o/r/issues/1#comment-99"}
    )
    r = gw.patch_pr_comment(
        repo="o/r", comment_id=99, body="updated body", token="t", client=mock_client
    )
    assert r.posted is True
    assert r.comment_url == "https://github.com/o/r/issues/1#comment-99"
    assert r.status_code == 200
    args, kwargs = mock_client.patch.call_args
    assert args[0] == "https://api.github.com/repos/o/r/issues/comments/99"
    assert kwargs["json"] == {"body": "updated body"}
    assert kwargs["headers"]["Authorization"] == "Bearer t"


def test_patch_pr_comment_404_returns_error():
    mock_client, _ = _mock_patch_response(404, {"message": "Not Found"}, "Not Found")
    r = gw.patch_pr_comment(repo="o/r", comment_id=99, body="hi", token="t", client=mock_client)
    assert r.posted is False
    assert r.status_code == 404
    assert "404" in r.error


def test_patch_pr_comment_rejects_invalid_repo():
    r = gw.patch_pr_comment(repo="../etc/passwd", comment_id=99, body="hi", token="t")
    assert r.posted is False
    assert "invalid repo" in r.error


def test_patch_pr_comment_rejects_zero_comment_id():
    r = gw.patch_pr_comment(repo="o/r", comment_id=0, body="hi", token="t")
    assert r.posted is False
    assert "invalid comment_id" in r.error


def test_patch_pr_comment_rejects_negative_comment_id():
    r = gw.patch_pr_comment(repo="o/r", comment_id=-5, body="hi", token="t")
    assert r.posted is False
    assert "invalid comment_id" in r.error


# R2 (post Codex R1 MEDIUM-1 on PR #65): non-int comment_id must NOT
# raise TypeError from `comment_id <= 0`. Reject str / None / float /
# bool with a clear error.
@pytest.mark.parametrize("bad_id", ["99", None, 99.0, True, False, [], b"99"])
def test_patch_pr_comment_rejects_non_int_comment_id(bad_id):
    r = gw.patch_pr_comment(repo="o/r", comment_id=bad_id, body="hi", token="t")
    assert r.posted is False
    assert "invalid comment_id" in r.error


# Symmetric guard on post_pr_comment for the same TypeError class.
@pytest.mark.parametrize("bad_pr", ["1", None, 1.5, True, False, [], b"1"])
def test_post_pr_comment_rejects_non_int_pr_number(bad_pr):
    r = gw.post_pr_comment(repo="o/r", pr_number=bad_pr, body="hi", token="t")
    assert r.posted is False
    assert "invalid pr_number" in r.error


def test_patch_pr_comment_rejects_empty_body():
    r = gw.patch_pr_comment(repo="o/r", comment_id=99, body="", token="t")
    assert r.posted is False
    assert "empty body" in r.error


def test_patch_pr_comment_no_token_no_op(monkeypatch):
    monkeypatch.delenv("GH_TOKEN", raising=False)
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.setattr(gw.shutil, "which", lambda _: None)
    r = gw.patch_pr_comment(repo="o/r", comment_id=99, body="hi")
    assert r.posted is False
    assert "no GitHub token" in r.error


def test_patch_pr_comment_truncates_body_over_64kb():
    """Same body cap as post_pr_comment."""
    mock_client, _ = _mock_patch_response(
        200, {"html_url": "https://github.com/o/r/issues/1#comment-99"}
    )
    huge = "x" * (gw.GITHUB_COMMENT_BODY_LIMIT + 5000)
    gw.patch_pr_comment(repo="o/r", comment_id=99, body=huge, token="t", client=mock_client)
    args, kwargs = mock_client.patch.call_args
    sent_body = kwargs["json"]["body"]
    assert len(sent_body) <= gw.GITHUB_COMMENT_BODY_LIMIT
    assert "truncated by github_writeback" in sent_body


def test_patch_pr_comment_transport_error():
    mock_client = MagicMock(spec=httpx.Client)
    mock_client.patch.side_effect = httpx.ConnectError("network down")
    r = gw.patch_pr_comment(repo="o/r", comment_id=99, body="hi", token="t", client=mock_client)
    assert r.posted is False
    assert "transport error" in r.error
    assert "network down" in r.error


def test_patch_pr_comment_200_with_malformed_json_does_not_raise():
    """Same never-raises contract on the success path as post_pr_comment."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.side_effect = ValueError("bad json")
    mock_resp.text = "<html>"
    mock_client = MagicMock(spec=httpx.Client)
    mock_client.patch.return_value = mock_resp
    r = gw.patch_pr_comment(repo="o/r", comment_id=99, body="hi", token="t", client=mock_client)
    assert r.posted is True
    assert r.comment_url is None
    assert r.status_code == 200
