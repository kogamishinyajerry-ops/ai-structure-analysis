"""Preflight publisher — post (or upsert) a PreflightSummary as a GitHub PR/Issue comment (P1-08).

Closes the loop: PreflightSummary (PR #42) → markdown → GitHub PR comment
via post_pr_comment / patch_pr_comment.

Two modes:
  * mode="post"   (default): always POST a new comment.
  * mode="upsert": list existing comments, find the prior preflight by
                   `header_marker`, PATCH it if found, otherwise POST a
                   new one. Prevents preflight-comment spam on PRs that
                   re-run.

Designed to be opt-in (no token → no-op result) and side-effect-isolated
(returns a structured result; never raises on transport errors). Mirrors
the discipline of github_writeback.py.

Usage:
    from backend.app.rag.preflight_summary import combine
    from backend.app.rag.preflight_publish import publish_preflight

    summary = combine(hint, advice)
    result = publish_preflight(summary, repo="owner/repo", pr_number=42)
    if result.posted:
        print(f"{result.action}: {result.comment_url}")  # 'posted' or 'updated'
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
        list_pr_comments as _default_list_pr_comments,
    )
    from backend.app.well_harness.github_writeback import (
        patch_pr_comment as _default_patch_pr_comment,
    )
    from backend.app.well_harness.github_writeback import (
        post_pr_comment as _default_post_pr_comment,
    )

    _GITHUB_WRITEBACK_AVAILABLE = True
except ImportError:  # pragma: no cover — covered by import-gate test
    _WritebackResult = None  # type: ignore[assignment,misc]
    _default_post_pr_comment = None  # type: ignore[assignment]
    _default_list_pr_comments = None  # type: ignore[assignment]
    _default_patch_pr_comment = None  # type: ignore[assignment]
    _GITHUB_WRITEBACK_AVAILABLE = False


@dataclass(frozen=True)
class PublishResult:
    """Outcome of a publish_preflight call.

    Mirrors WritebackResult but adds an `action` field distinguishing
    "posted" (new comment created) from "updated" (existing comment
    PATCHed). `action` is None on failure / skip.
    """

    posted: bool
    comment_url: str | None = None
    status_code: int | None = None
    error: str | None = None
    summary_was_empty: bool = False
    # "posted" | "updated" | None on failure / skip
    action: str | None = None


# Type aliases for the testing seams. Real callers use the github_writeback
# defaults; tests pass stubs.
PostCallback = Callable[..., Any]
ListCallback = Callable[..., Any]
PatchCallback = Callable[..., Any]


# Mirror github_writeback's _REPO_RE so preflight_publish rejects the
# same set of malformed repo identifiers (no path traversal etc.).
_REPO_RE = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9._-]{0,38})/[A-Za-z0-9._-]{1,100}$")


def _validate_inputs(repo: str, pr_number: int) -> str | None:
    if not repo or not _REPO_RE.match(repo):
        return f"invalid repo: {repo!r} (expected owner/name)"
    # R2 (post Codex R1 MEDIUM-1 on PR #65): strict positive-int check
    # so a stray str/None/float/bool produces a clear error instead of
    # a TypeError leaking from `pr_number <= 0`.
    if not isinstance(pr_number, int) or isinstance(pr_number, bool) or pr_number <= 0:
        return f"invalid pr_number: {pr_number!r}"
    return None


def find_existing_preflight_comment(
    comments: list[dict],
    header_marker: str,
) -> dict | None:
    """Return the *last* (newest) comment whose body starts with
    `header_marker`, or None if no match.

    Why startswith(): `publish_preflight` prepends the marker as the very
    first line. If a caller adds their own pre-text before the marker,
    the marker won't be at the start — that is intentional, only
    'owned' preflight comments get upserted.

    Why "last" not "first" (R2, post Codex R1 LOW on PR #65): GitHub
    returns issue comments in creation order (oldest first). When
    multiple legacy preflight comments coexist on a PR — e.g. an older
    comment from a previous run that we lost track of, plus a newer one
    we successfully upserted on the last run — we want PATCH to keep
    targeting the *newest* one, so the conversation thread stays
    coherent (newest comment = current state, older ones become
    historical artifacts the operator can clean up manually).

    This also reduces (but does not eliminate) the risk that a human
    comment which happens to start with the marker — e.g. someone
    pasted a marker in a reply — gets accidentally clobbered: as long
    as the bot has posted *any* preflight after the human comment, the
    bot's own comment will be selected for PATCH instead.
    """
    if not header_marker:
        return None
    match: dict | None = None
    for c in comments:
        if not isinstance(c, dict):
            continue
        body = c.get("body", "")
        if isinstance(body, str) and body.startswith(header_marker):
            match = c
    return match


_GITHUB_WRITEBACK_UNAVAILABLE_ERROR = (
    "github_writeback module is unimportable from this environment "
    "(check that backend/app/well_harness/github_writeback.py exists "
    "and that httpx is installed). Pass post_callback=<your-fn> to "
    "supply an alternative."
)


def publish_preflight(
    summary: PreflightSummary,
    repo: str,
    pr_number: int,
    *,
    mode: str = "post",
    post_callback: PostCallback | None = None,
    list_callback: ListCallback | None = None,
    patch_callback: PatchCallback | None = None,
    skip_when_empty: bool = True,
    header_marker: str = "<!-- ai-fea-preflight -->",
) -> PublishResult:
    """Post (or upsert) a PreflightSummary's markdown as a PR/Issue comment.

    Args:
        summary: a PreflightSummary from preflight_summary.combine().
        repo: target repo as "owner/name".
        pr_number: PR or Issue number (positive int).
        mode: "post" (default) always POSTs a new comment.
              "upsert" lists existing comments, looks for a prior preflight
              by header_marker; PATCHes if found, POSTs otherwise. Requires
              header_marker to be non-empty.
        post_callback: testing seam for the POST path. Defaults to
            backend.app.well_harness.github_writeback.post_pr_comment.
            Callback signature: (repo, pr_number, body) → result-like with
            .posted, .comment_url, .status_code, .error attributes.
        list_callback: testing seam for upsert's list step. Defaults to
            github_writeback.list_pr_comments.
            Callback signature: (repo, pr_number) → list[dict].
        patch_callback: testing seam for upsert's patch step. Defaults to
            github_writeback.patch_pr_comment.
            Callback signature: (repo, comment_id, body) → result-like.
        skip_when_empty: if True (default) and the summary has no quantities
            and no advice, return a no-op PublishResult instead of posting.
        header_marker: HTML comment prepended to the body and used by upsert
            mode to identify prior preflight comments. Default
            "<!-- ai-fea-preflight -->". Empty string disables the marker
            (and forbids upsert).

    Returns:
        PublishResult. `action` is "posted" (new), "updated" (PATCHed), or
        None on failure/skip. Never raises.
    """
    err = _validate_inputs(repo, pr_number)
    if err:
        return PublishResult(posted=False, error=err)

    if mode not in ("post", "upsert"):
        return PublishResult(posted=False, error=f"invalid mode: {mode!r}")

    if skip_when_empty and summary.is_empty():
        return PublishResult(
            posted=False,
            error="summary is empty (no quantities, no advice); skipped",
            summary_was_empty=True,
        )

    if mode == "upsert" and not header_marker:
        return PublishResult(
            posted=False,
            error="upsert mode requires a non-empty header_marker",
        )

    body = summary.markdown
    if header_marker:
        body = f"{header_marker}\n\n{body}"

    if mode == "upsert":
        list_cb = list_callback or _default_list_pr_comments
        if list_cb is None:
            return PublishResult(posted=False, error=_GITHUB_WRITEBACK_UNAVAILABLE_ERROR)
        comments = list_cb(repo, pr_number)
        if not isinstance(comments, list):
            # Defensive: a misbehaving callback that returns None or a
            # non-list shouldn't crash the upsert path.
            comments = []
        existing = find_existing_preflight_comment(comments, header_marker)
        if existing is not None:
            comment_id = existing.get("id")
            # R2 (post Codex R1 MEDIUM-1 on PR #65): exclude bool from the
            # int check (`bool` is a subclass of `int`, so `True`/`False`
            # would otherwise sneak through).
            if not isinstance(comment_id, int) or isinstance(comment_id, bool) or comment_id <= 0:
                return PublishResult(
                    posted=False,
                    error=f"prior preflight comment has invalid id: {comment_id!r}",
                )
            patch_cb = patch_callback or _default_patch_pr_comment
            if patch_cb is None:
                return PublishResult(posted=False, error=_GITHUB_WRITEBACK_UNAVAILABLE_ERROR)
            raw = patch_cb(repo, comment_id, body)
            posted = bool(getattr(raw, "posted", False))
            return PublishResult(
                posted=posted,
                comment_url=getattr(raw, "comment_url", None),
                status_code=getattr(raw, "status_code", None),
                error=getattr(raw, "error", None),
                action="updated" if posted else None,
            )
        # No existing preflight comment — fall through to POST below.

    # POST path (also used as upsert fallback when no prior comment exists)
    callback = post_callback or _default_post_pr_comment
    if callback is None:
        return PublishResult(posted=False, error=_GITHUB_WRITEBACK_UNAVAILABLE_ERROR)

    raw = callback(repo, pr_number, body)
    posted = bool(getattr(raw, "posted", False))
    return PublishResult(
        posted=posted,
        comment_url=getattr(raw, "comment_url", None),
        status_code=getattr(raw, "status_code", None),
        error=getattr(raw, "error", None),
        action="posted" if posted else None,
    )


def is_github_writeback_available() -> bool:
    """Convenience predicate. Useful for callers deciding whether to
    set up an explicit post_callback or rely on the default."""
    return _GITHUB_WRITEBACK_AVAILABLE
