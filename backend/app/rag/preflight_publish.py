"""Preflight publisher — post a PreflightSummary as a GitHub PR/Issue comment (P1-08).

Closes the loop: PreflightSummary (PR #42) → markdown → GitHub PR comment
via post_pr_comment (PR #29).

Designed to be opt-in (no token → no-op result) and side-effect-isolated
(returns a structured result; never raises on transport errors). Mirrors
the discipline of github_writeback.py.

Usage:
    from backend.app.rag.preflight_summary import combine
    from backend.app.rag.preflight_publish import publish_preflight

    summary = combine(hint, advice)
    result = publish_preflight(summary, repo="owner/repo", pr_number=42)
    if result.posted:
        print(f"posted: {result.comment_url}")
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from backend.app.rag.preflight_summary import PreflightSummary

# Wrap-then-import: github_writeback may not be importable in environments
# that do not depend on httpx. We expose the publisher API regardless and
# fall back to a clear error result if the dep is missing.
try:
    from backend.app.well_harness.github_writeback import (
        WritebackResult as _WritebackResult,
    )
    from backend.app.well_harness.github_writeback import (
        post_pr_comment as _default_post_pr_comment,
    )

    _GITHUB_WRITEBACK_AVAILABLE = True
except ImportError:  # pragma: no cover — covered by import-gate test
    _WritebackResult = None  # type: ignore[assignment,misc]
    _default_post_pr_comment = None  # type: ignore[assignment]
    _GITHUB_WRITEBACK_AVAILABLE = False


@dataclass(frozen=True)
class PublishResult:
    """Outcome of a publish_preflight call.

    Mirrors WritebackResult but is its own type so callers don't have to
    conditionally import from well_harness.
    """

    posted: bool
    comment_url: str | None = None
    status_code: int | None = None
    error: str | None = None
    summary_was_empty: bool = False


# Type alias for the post callback. Real callers pass post_pr_comment from
# github_writeback.py; tests pass a stub.
PostCallback = Callable[..., Any]


# Mirror github_writeback's _REPO_RE so preflight_publish rejects the
# same set of malformed repo identifiers (no path traversal etc.).
_REPO_RE = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9._-]{0,38})/[A-Za-z0-9._-]{1,100}$")


def _validate_inputs(repo: str, pr_number: int) -> str | None:
    if not repo or not _REPO_RE.match(repo):
        return f"invalid repo: {repo!r} (expected owner/name)"
    if pr_number <= 0:
        return f"invalid pr_number: {pr_number}"
    return None


def publish_preflight(
    summary: PreflightSummary,
    repo: str,
    pr_number: int,
    *,
    post_callback: PostCallback | None = None,
    skip_when_empty: bool = True,
    header_marker: str = "<!-- ai-fea-preflight -->",
) -> PublishResult:
    """Post a PreflightSummary's markdown as a GitHub PR/Issue comment.

    Args:
        summary: a PreflightSummary from preflight_summary.combine().
        repo: target repo as "owner/name".
        pr_number: PR or Issue number (positive int).
        post_callback: testing seam. Defaults to
            backend.app.well_harness.github_writeback.post_pr_comment.
            The callback signature must match (repo, pr_number, body, **kwargs)
            and return an object with .posted, .comment_url, .status_code,
            .error attributes.
        skip_when_empty: if True (default) and the summary has no quantities
            and no advice, return a no-op PublishResult instead of posting an
            empty comment. Set False to always post.
        header_marker: HTML comment prepended to the body. This module
            ALWAYS posts a new comment; the marker is just a stable token
            that a future upsert path (PR #44) will use to find prior
            preflight comments and PATCH them instead of creating
            duplicates. Default "<!-- ai-fea-preflight -->". Set to "" to
            disable.

    Returns:
        PublishResult. Never raises.
    """
    err = _validate_inputs(repo, pr_number)
    if err:
        return PublishResult(posted=False, error=err)

    if skip_when_empty and summary.is_empty():
        return PublishResult(
            posted=False,
            error="summary is empty (no quantities, no advice); skipped",
            summary_was_empty=True,
        )

    callback = post_callback or _default_post_pr_comment
    if callback is None:
        # R2 (post Codex R1 LOW on PR #64): the prior message pointed at
        # `pip install -e ".[notion]"` which doesn't exist as an extra in
        # this repo's pyproject.toml. httpx is a base dependency; the
        # only realistic way to trip this branch is for the github_writeback
        # module itself to be unimportable (e.g. removed or renamed).
        return PublishResult(
            posted=False,
            error=(
                "github_writeback module is unimportable from this environment "
                "(check that backend/app/well_harness/github_writeback.py exists "
                "and that httpx is installed). Pass post_callback=<your-fn> to "
                "supply an alternative."
            ),
        )

    body = summary.markdown
    if header_marker:
        body = f"{header_marker}\n\n{body}"

    raw = callback(repo, pr_number, body)

    return PublishResult(
        posted=bool(getattr(raw, "posted", False)),
        comment_url=getattr(raw, "comment_url", None),
        status_code=getattr(raw, "status_code", None),
        error=getattr(raw, "error", None),
    )


def is_github_writeback_available() -> bool:
    """Convenience predicate. Useful for callers deciding whether to
    set up an explicit post_callback or rely on the default."""
    return _GITHUB_WRITEBACK_AVAILABLE
