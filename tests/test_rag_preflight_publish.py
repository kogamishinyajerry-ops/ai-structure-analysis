"""Tests for app.rag.preflight_publish."""

from __future__ import annotations

from dataclasses import dataclass

import pytest

try:
    from app.rag.preflight_publish import (
        PublishResult,
        find_existing_preflight_comment,
        is_github_writeback_available,
        publish_preflight,
    )
    from app.rag.preflight_summary import PreflightSummary
except ImportError as e:
    pytest.skip(f"preflight_publish imports failed: {e}", allow_module_level=True)


# ---------------------------------------------------------------------------
# Stub post_callback (mirrors WritebackResult shape)
# ---------------------------------------------------------------------------


@dataclass
class _StubResult:
    posted: bool = True
    comment_url: str | None = "https://example.com/c/1"
    status_code: int | None = 201
    error: str | None = None


@dataclass
class _CallRecord:
    repo: str = ""
    pr_number: int = 0
    body: str = ""
    n_calls: int = 0


def _make_callback(result: _StubResult, record: _CallRecord):
    def _cb(repo: str, pr_number: int, body: str, **kwargs):
        record.repo = repo
        record.pr_number = pr_number
        record.body = body
        record.n_calls += 1
        return result

    return _cb


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _populated_summary() -> PreflightSummary:
    return PreflightSummary(
        case_id="GS-001",
        verdict="Reject",
        fault_class="solver_convergence",
        quantity_lines=("  - max_displacement = 1.234 mm @ free_end  (low)",),
        advice_lines=("  - #1 [project-adr-fp] FP-002:3 (score=0.409)  ...",),
        confidence_indicator="low",
        markdown=(
            "## Preflight — GS-001\n\n"
            "**Verdict:** Reject  **Fault:** solver_convergence  "
            "**Surrogate confidence:** low\n\n"
            "### Surrogate predictions (placeholder-mlp@v0)\n"
            "  - max_displacement = 1.234 mm @ free_end  (low)\n\n"
            "### Corpus advice\n"
            "  - #1 [project-adr-fp] FP-002:3 (score=0.409)  ...\n"
        ),
    )


def _empty_summary() -> PreflightSummary:
    return PreflightSummary(
        case_id="GS-001",
        verdict="Reject",
        fault_class="solver_convergence",
        markdown="",
    )


# ---------------------------------------------------------------------------
# Input validation
# ---------------------------------------------------------------------------


def test_invalid_repo_returns_error():
    record = _CallRecord()
    result = publish_preflight(
        _populated_summary(),
        repo="bad-no-slash",
        pr_number=1,
        post_callback=_make_callback(_StubResult(), record),
    )
    assert not result.posted
    assert "invalid repo" in (result.error or "")
    assert record.n_calls == 0  # callback never reached


def test_empty_repo_returns_error():
    result = publish_preflight(
        _populated_summary(),
        repo="",
        pr_number=1,
        post_callback=_make_callback(_StubResult(), _CallRecord()),
    )
    assert not result.posted
    assert "invalid repo" in (result.error or "")


def test_zero_pr_number_returns_error():
    result = publish_preflight(
        _populated_summary(),
        repo="owner/repo",
        pr_number=0,
        post_callback=_make_callback(_StubResult(), _CallRecord()),
    )
    assert not result.posted
    assert "invalid pr_number" in (result.error or "")


def test_negative_pr_number_returns_error():
    result = publish_preflight(
        _populated_summary(),
        repo="owner/repo",
        pr_number=-5,
        post_callback=_make_callback(_StubResult(), _CallRecord()),
    )
    assert not result.posted
    assert "invalid pr_number" in (result.error or "")


# ---------------------------------------------------------------------------
# Empty-summary handling
# ---------------------------------------------------------------------------


def test_empty_summary_skipped_by_default():
    record = _CallRecord()
    result = publish_preflight(
        _empty_summary(),
        repo="owner/repo",
        pr_number=1,
        post_callback=_make_callback(_StubResult(), record),
    )
    assert not result.posted
    assert result.summary_was_empty
    assert "empty" in (result.error or "")
    assert record.n_calls == 0


def test_empty_summary_can_be_forced():
    record = _CallRecord()
    result = publish_preflight(
        _empty_summary(),
        repo="owner/repo",
        pr_number=1,
        post_callback=_make_callback(_StubResult(), record),
        skip_when_empty=False,
    )
    assert result.posted
    assert record.n_calls == 1


# ---------------------------------------------------------------------------
# Happy path — populated summary posts
# ---------------------------------------------------------------------------


def test_populated_summary_posts():
    record = _CallRecord()
    cb_result = _StubResult(posted=True, comment_url="https://x/c/42", status_code=201)
    result = publish_preflight(
        _populated_summary(),
        repo="owner/repo",
        pr_number=99,
        post_callback=_make_callback(cb_result, record),
    )
    assert result.posted
    assert result.comment_url == "https://x/c/42"
    assert result.status_code == 201
    assert result.error is None
    # callback received correct args
    assert record.repo == "owner/repo"
    assert record.pr_number == 99
    assert record.n_calls == 1


def test_callback_receives_markdown_body():
    record = _CallRecord()
    publish_preflight(
        _populated_summary(),
        repo="owner/repo",
        pr_number=1,
        post_callback=_make_callback(_StubResult(), record),
    )
    assert "Preflight" in record.body
    assert "max_displacement" in record.body
    assert "FP-002:3" in record.body


# ---------------------------------------------------------------------------
# Header marker
# ---------------------------------------------------------------------------


def test_default_header_marker_prepended():
    record = _CallRecord()
    publish_preflight(
        _populated_summary(),
        repo="owner/repo",
        pr_number=1,
        post_callback=_make_callback(_StubResult(), record),
    )
    assert record.body.startswith("<!-- ai-fea-preflight -->")


def test_custom_header_marker():
    record = _CallRecord()
    publish_preflight(
        _populated_summary(),
        repo="owner/repo",
        pr_number=1,
        post_callback=_make_callback(_StubResult(), record),
        header_marker="<!-- custom -->",
    )
    assert record.body.startswith("<!-- custom -->")


def test_disabled_header_marker():
    record = _CallRecord()
    publish_preflight(
        _populated_summary(),
        repo="owner/repo",
        pr_number=1,
        post_callback=_make_callback(_StubResult(), record),
        header_marker="",
    )
    assert not record.body.startswith("<!--")
    assert record.body.startswith("## Preflight")


# ---------------------------------------------------------------------------
# Failure propagation
# ---------------------------------------------------------------------------


def test_callback_failure_propagates_to_result():
    record = _CallRecord()
    failed = _StubResult(posted=False, status_code=403, error="Forbidden")
    result = publish_preflight(
        _populated_summary(),
        repo="owner/repo",
        pr_number=1,
        post_callback=_make_callback(failed, record),
    )
    assert not result.posted
    assert result.status_code == 403
    assert result.error == "Forbidden"


# ---------------------------------------------------------------------------
# Default callback path — when github_writeback is unavailable
# ---------------------------------------------------------------------------


def test_no_callback_no_default_returns_error(monkeypatch):
    """Simulate environment where github_writeback is missing."""
    import app.rag.preflight_publish as mod

    monkeypatch.setattr(mod, "_default_post_pr_comment", None)

    result = publish_preflight(
        _populated_summary(),
        repo="owner/repo",
        pr_number=1,
        post_callback=None,
    )
    assert not result.posted
    # R2 (post Codex R1 LOW on PR #64): the prior message pointed at a
    # `[notion]` extra that doesn't exist in this repo's pyproject.toml.
    # Updated to refer to the actual cause (module unimportable) and the
    # actual remediation (check the file + httpx, or pass post_callback=).
    assert "github_writeback module is unimportable" in (result.error or "")
    assert "post_callback" in (result.error or "")


def test_is_github_writeback_available_returns_bool():
    assert isinstance(is_github_writeback_available(), bool)


# ---------------------------------------------------------------------------
# PublishResult invariants
# ---------------------------------------------------------------------------


def test_publish_result_is_frozen():
    r = PublishResult(posted=False)
    with pytest.raises((AttributeError, Exception)):
        r.posted = True  # type: ignore[misc]


def test_publish_result_defaults():
    r = PublishResult(posted=False)
    assert r.posted is False
    assert r.comment_url is None
    assert r.status_code is None
    assert r.error is None
    assert r.summary_was_empty is False


# ---------------------------------------------------------------------------
# Robust to callback returning a bare object (duck-type)
# ---------------------------------------------------------------------------


def test_callback_returning_bare_object_does_not_crash():
    """A callback that returns an object missing some result attrs
    should still produce a sensible PublishResult."""

    class _Bare:
        posted = True
        # no comment_url, no status_code, no error

    record = _CallRecord()

    def _cb(repo, pr_number, body, **kwargs):
        record.n_calls += 1
        return _Bare()

    result = publish_preflight(
        _populated_summary(),
        repo="owner/repo",
        pr_number=1,
        post_callback=_cb,
    )
    assert result.posted
    assert result.comment_url is None
    assert result.status_code is None
    assert result.error is None


# ---------------------------------------------------------------------------
# Pre-emptive R2: stricter repo validation (mirrors github_writeback._REPO_RE)
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
    ],
)
def test_publish_rejects_path_traversal_repo(bad_repo):
    """R2 (lifted from github_writeback): pre-fix accepted any string
    with a slash. Now path-traversing identifiers are rejected with
    a clear error so a malformed `repo` input cannot reach the
    GitHub API URL builder."""
    record = _CallRecord()

    def _cb(repo, pr_number, body, **kwargs):
        record.n_calls += 1
        return None  # would crash downstream if reached

    result = publish_preflight(
        _populated_summary(),
        repo=bad_repo,
        pr_number=1,
        post_callback=_cb,
    )
    assert result.posted is False
    assert "invalid repo" in (result.error or "")
    assert record.n_calls == 0, "callback must not be invoked on invalid repo"


def test_publish_accepts_real_shape_repo():
    """Sanity: real-shape repos still pass through and reach the callback."""
    record = _CallRecord()

    def _cb(repo, pr_number, body, **kwargs):
        record.n_calls += 1
        return _StubResult()

    result = publish_preflight(
        _populated_summary(),
        repo="kogamishinyajerry-ops/ai-structure-analysis",
        pr_number=42,
        post_callback=_cb,
    )
    assert result.posted is True


# ---------------------------------------------------------------------------
# action field — distinguishes "posted" (new) vs "updated" (PATCHed)
# ---------------------------------------------------------------------------


def test_publish_post_path_sets_action_posted():
    """A successful POST in the default 'post' mode must set action='posted'."""
    record = _CallRecord()
    result = publish_preflight(
        _populated_summary(),
        repo="owner/repo",
        pr_number=1,
        post_callback=_make_callback(_StubResult(posted=True), record),
    )
    assert result.posted is True
    assert result.action == "posted"


def test_publish_post_failure_action_is_none():
    """On callback failure (posted=False), action must remain None
    (not 'posted')."""
    record = _CallRecord()
    result = publish_preflight(
        _populated_summary(),
        repo="owner/repo",
        pr_number=1,
        post_callback=_make_callback(_StubResult(posted=False, error="boom"), record),
    )
    assert result.posted is False
    assert result.action is None


def test_publish_validation_error_action_is_none():
    """Validation errors before the callback runs leave action=None."""
    result = publish_preflight(
        _populated_summary(),
        repo="bad",
        pr_number=1,
        post_callback=_make_callback(_StubResult(), _CallRecord()),
    )
    assert result.posted is False
    assert result.action is None


# ---------------------------------------------------------------------------
# find_existing_preflight_comment helper
# ---------------------------------------------------------------------------


def test_find_existing_returns_last_match_newest_wins():
    """R2 (post Codex R1 LOW on PR #65): GitHub returns issue comments
    oldest→newest. When multiple preflight comments coexist (e.g. an
    older orphan + a newer upserted one), we want PATCH to target the
    *newest* so the conversation stays coherent and the older one
    becomes a historical artifact."""
    comments = [
        {"id": 1, "body": "unrelated comment"},
        {"id": 42, "body": "<!-- ai-fea-preflight -->\n\n## Preflight — GS-001 (older)"},
        {"id": 99, "body": "<!-- ai-fea-preflight -->\n\n## Preflight — GS-001 (newest)"},
    ]
    found = find_existing_preflight_comment(comments, "<!-- ai-fea-preflight -->")
    assert found is not None
    assert found["id"] == 99


def test_find_existing_returns_single_match():
    """When only one comment matches, return it (regression for the
    common case)."""
    comments = [
        {"id": 1, "body": "unrelated comment"},
        {"id": 42, "body": "<!-- ai-fea-preflight -->\n\n## Preflight — GS-001"},
    ]
    found = find_existing_preflight_comment(comments, "<!-- ai-fea-preflight -->")
    assert found is not None
    assert found["id"] == 42


def test_find_existing_returns_none_when_no_match():
    comments = [
        {"id": 1, "body": "unrelated"},
        {"id": 2, "body": "also unrelated"},
    ]
    found = find_existing_preflight_comment(comments, "<!-- ai-fea-preflight -->")
    assert found is None


def test_find_existing_returns_none_for_empty_marker():
    """Empty marker is treated as "no marker, never match" — never
    upserts an arbitrary first comment."""
    comments = [{"id": 1, "body": "anything"}]
    assert find_existing_preflight_comment(comments, "") is None


def test_find_existing_only_matches_marker_at_start():
    """`startswith` semantics: a marker buried inside the body must NOT
    match. Only "owned" preflight comments (marker at the very first
    line) qualify for upsert."""
    comments = [
        {"id": 1, "body": "preamble text\n<!-- ai-fea-preflight -->\n## Preflight"},
    ]
    assert find_existing_preflight_comment(comments, "<!-- ai-fea-preflight -->") is None


def test_find_existing_handles_non_dict_entries():
    """Defensive: a list with stray non-dict entries (broken upstream)
    must not crash the helper."""
    comments = [
        "stray string",
        None,
        42,
        {"id": 7, "body": "<!-- ai-fea-preflight -->\nbody"},
    ]
    found = find_existing_preflight_comment(comments, "<!-- ai-fea-preflight -->")
    assert found is not None
    assert found["id"] == 7


def test_find_existing_handles_non_string_body():
    """Defensive: a comment dict with body=None or body=42 must not
    crash on .startswith()."""
    comments = [
        {"id": 1, "body": None},
        {"id": 2, "body": 42},
        {"id": 3, "body": "<!-- ai-fea-preflight -->\nok"},
    ]
    found = find_existing_preflight_comment(comments, "<!-- ai-fea-preflight -->")
    assert found is not None
    assert found["id"] == 3


# ---------------------------------------------------------------------------
# Upsert mode — invalid args
# ---------------------------------------------------------------------------


def test_publish_invalid_mode_returns_error():
    result = publish_preflight(
        _populated_summary(),
        repo="owner/repo",
        pr_number=1,
        mode="bogus",
        post_callback=_make_callback(_StubResult(), _CallRecord()),
    )
    assert result.posted is False
    assert "invalid mode" in (result.error or "")


def test_publish_upsert_requires_header_marker():
    """upsert mode without a marker has no way to identify prior
    comments — must fail early."""
    result = publish_preflight(
        _populated_summary(),
        repo="owner/repo",
        pr_number=1,
        mode="upsert",
        header_marker="",
        post_callback=_make_callback(_StubResult(), _CallRecord()),
    )
    assert result.posted is False
    assert "upsert mode requires" in (result.error or "")


# ---------------------------------------------------------------------------
# Upsert mode — happy paths (PATCH on existing, POST on missing)
# ---------------------------------------------------------------------------


def test_upsert_patches_existing_comment():
    """Upsert mode finds the prior comment and PATCHes it. Must NOT
    call post_callback. Result.action == 'updated'."""
    list_calls = _CallRecord()
    patch_calls = _CallRecord()
    post_calls = _CallRecord()

    def _list(repo, pr_number):
        list_calls.repo = repo
        list_calls.pr_number = pr_number
        list_calls.n_calls += 1
        return [
            {"id": 1, "body": "unrelated"},
            {"id": 999, "body": "<!-- ai-fea-preflight -->\n\nold preflight"},
        ]

    def _patch(repo, comment_id, body):
        patch_calls.repo = repo
        patch_calls.pr_number = comment_id  # reusing field for assertions
        patch_calls.body = body
        patch_calls.n_calls += 1
        return _StubResult(posted=True, comment_url="https://x/c/999", status_code=200)

    def _post(repo, pr_number, body, **kwargs):
        post_calls.n_calls += 1
        return _StubResult()

    result = publish_preflight(
        _populated_summary(),
        repo="owner/repo",
        pr_number=42,
        mode="upsert",
        list_callback=_list,
        patch_callback=_patch,
        post_callback=_post,
    )
    assert result.posted is True
    assert result.action == "updated"
    assert result.comment_url == "https://x/c/999"
    assert result.status_code == 200
    assert list_calls.n_calls == 1
    assert patch_calls.n_calls == 1
    assert patch_calls.pr_number == 999  # the comment_id we passed
    assert post_calls.n_calls == 0  # POST never fired


def test_upsert_falls_through_to_post_when_no_prior_comment():
    """No prior preflight → upsert falls through to POST. Action='posted'."""
    list_calls = _CallRecord()
    post_calls = _CallRecord()

    def _list(repo, pr_number):
        list_calls.n_calls += 1
        return [{"id": 1, "body": "unrelated"}]

    def _post(repo, pr_number, body, **kwargs):
        post_calls.n_calls += 1
        post_calls.body = body
        return _StubResult(posted=True, comment_url="https://x/c/new", status_code=201)

    result = publish_preflight(
        _populated_summary(),
        repo="owner/repo",
        pr_number=42,
        mode="upsert",
        list_callback=_list,
        post_callback=_post,
    )
    assert result.posted is True
    assert result.action == "posted"
    assert result.comment_url == "https://x/c/new"
    assert list_calls.n_calls == 1
    assert post_calls.n_calls == 1
    # Body must include the marker
    assert post_calls.body.startswith("<!-- ai-fea-preflight -->")


def test_upsert_posts_when_list_returns_empty():
    """Empty comment list → upsert falls through to POST."""
    list_calls = _CallRecord()
    post_calls = _CallRecord()

    def _list(repo, pr_number):
        list_calls.n_calls += 1
        return []

    def _post(repo, pr_number, body, **kwargs):
        post_calls.n_calls += 1
        return _StubResult(posted=True)

    result = publish_preflight(
        _populated_summary(),
        repo="owner/repo",
        pr_number=42,
        mode="upsert",
        list_callback=_list,
        post_callback=_post,
    )
    assert result.posted is True
    assert result.action == "posted"


def test_upsert_handles_non_list_from_callback():
    """Defensive: if list_callback returns None or a non-list (e.g.
    misbehaving stub or upstream API hiccup), upsert must not crash
    and should fall through to POST."""
    post_calls = _CallRecord()

    def _list(repo, pr_number):
        return None  # type: ignore[return-value]

    def _post(repo, pr_number, body, **kwargs):
        post_calls.n_calls += 1
        return _StubResult(posted=True)

    result = publish_preflight(
        _populated_summary(),
        repo="owner/repo",
        pr_number=42,
        mode="upsert",
        list_callback=_list,
        post_callback=_post,
    )
    assert result.posted is True
    assert result.action == "posted"
    assert post_calls.n_calls == 1


def test_upsert_patch_failure_returns_error_with_action_none():
    """If PATCH fails, action stays None and error is propagated."""

    def _list(repo, pr_number):
        return [{"id": 999, "body": "<!-- ai-fea-preflight -->\nold"}]

    def _patch(repo, comment_id, body):
        return _StubResult(posted=False, status_code=404, error="not found")

    result = publish_preflight(
        _populated_summary(),
        repo="owner/repo",
        pr_number=42,
        mode="upsert",
        list_callback=_list,
        patch_callback=_patch,
    )
    assert result.posted is False
    assert result.action is None
    assert result.status_code == 404
    assert "not found" in (result.error or "")


def test_upsert_invalid_comment_id_returns_error():
    """Defensive: a prior 'preflight' comment dict with a missing or
    non-int id must not crash; surface a clear error instead."""

    def _list(repo, pr_number):
        return [{"id": "not-an-int", "body": "<!-- ai-fea-preflight -->\nold"}]

    def _patch(repo, comment_id, body):
        # Should never be invoked
        raise AssertionError("patch callback called with bad id")

    result = publish_preflight(
        _populated_summary(),
        repo="owner/repo",
        pr_number=42,
        mode="upsert",
        list_callback=_list,
        patch_callback=_patch,
    )
    assert result.posted is False
    assert result.action is None
    assert "invalid id" in (result.error or "")


def test_upsert_negative_comment_id_returns_error():
    def _list(repo, pr_number):
        return [{"id": -5, "body": "<!-- ai-fea-preflight -->\nold"}]

    def _patch(repo, comment_id, body):
        raise AssertionError("patch callback called with bad id")

    result = publish_preflight(
        _populated_summary(),
        repo="owner/repo",
        pr_number=42,
        mode="upsert",
        list_callback=_list,
        patch_callback=_patch,
    )
    assert result.posted is False
    assert "invalid id" in (result.error or "")


def test_upsert_skip_when_empty_short_circuits_before_list():
    """An empty summary in upsert mode must skip BEFORE listing
    comments — saves a GitHub API call when there's nothing to post."""
    list_calls = _CallRecord()

    def _list(repo, pr_number):
        list_calls.n_calls += 1
        return []

    result = publish_preflight(
        _empty_summary(),
        repo="owner/repo",
        pr_number=42,
        mode="upsert",
        list_callback=_list,
    )
    assert result.summary_was_empty is True
    assert list_calls.n_calls == 0


def test_upsert_default_callbacks_unavailable_returns_error(monkeypatch):
    """If github_writeback is unimportable AND no list_callback is
    passed, upsert must fail with a clear message."""
    import app.rag.preflight_publish as mod

    monkeypatch.setattr(mod, "_default_list_pr_comments", None)
    monkeypatch.setattr(mod, "_default_patch_pr_comment", None)

    result = publish_preflight(
        _populated_summary(),
        repo="owner/repo",
        pr_number=42,
        mode="upsert",
    )
    assert result.posted is False
    assert "github_writeback" in (result.error or "")
    assert "unimportable" in (result.error or "")
