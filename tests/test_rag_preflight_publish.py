"""Tests for backend.app.rag.preflight_publish."""

from __future__ import annotations

from dataclasses import dataclass

import pytest

try:
    from backend.app.rag.preflight_publish import (
        PublishResult,
        is_github_writeback_available,
        publish_preflight,
    )
    from backend.app.rag.preflight_summary import PreflightSummary
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
    import backend.app.rag.preflight_publish as mod

    monkeypatch.setattr(mod, "_default_post_pr_comment", None)

    result = publish_preflight(
        _populated_summary(),
        repo="owner/repo",
        pr_number=1,
        post_callback=None,
    )
    assert not result.posted
    assert "github_writeback unavailable" in (result.error or "")


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
