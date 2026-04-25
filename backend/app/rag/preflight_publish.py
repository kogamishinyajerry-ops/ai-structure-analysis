"""Preflight publisher — post a PreflightSummary as a GitHub PR/Issue comment (P1-08).

Closes the loop: PreflightSummary (PR #42) → markdown → GitHub PR comment
via post_pr_comment (PR #29).

Two modes:
  * mode="post"   (default): always POST a new comment.
  * mode="upsert": list existing comments, find the prior preflight by
                   header_marker, PATCH it if found, otherwise POST a
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

import os
import shutil
import subprocess
from dataclasses import dataclass
from typing import Any, Callable, Optional

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

try:
    import httpx as _httpx  # noqa: F401

    _HTTPX_AVAILABLE = True
except ImportError:  # pragma: no cover
    _httpx = None  # type: ignore[assignment]
    _HTTPX_AVAILABLE = False


GITHUB_API = "https://api.github.com"


@dataclass(frozen=True)
class PublishResult:
    """Outcome of a publish_preflight call.

    Mirrors WritebackResult but adds an `action` field distinguishing
    "posted" (new comment) from "updated" (PATCHed prior comment).
    """

    posted: bool
    comment_url: Optional[str] = None
    status_code: Optional[int] = None
    error: Optional[str] = None
    summary_was_empty: bool = False
    action: Optional[str] = None  # "posted" | "updated" | None on failure


PostCallback = Callable[..., Any]
ListCallback = Callable[..., Any]
PatchCallback = Callable[..., Any]


def _validate_inputs(repo: str, pr_number: int) -> Optional[str]:
    if not repo or "/" not in repo:
        return f"invalid repo: {repo!r}"
    if pr_number <= 0:
        return f"invalid pr_number: {pr_number}"
    return None


def _resolve_token() -> Optional[str]:
    """Find a GitHub token from env, then fall back to `gh auth token`."""
    for var in ("GH_TOKEN", "GITHUB_TOKEN"):
        v = os.environ.get(var)
        if v:
            return v
    if shutil.which("gh"):
        try:
            r = subprocess.run(
                ["gh", "auth", "token"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if r.returncode == 0 and r.stdout.strip():
                return r.stdout.strip()
        except (subprocess.SubprocessError, FileNotFoundError, OSError):
            pass
    return None


def list_pr_comments(
    repo: str,
    pr_number: int,
    *,
    token: Optional[str] = None,
    client: Optional[Any] = None,
    timeout: float = 10.0,
) -> list[dict]:
    """List Issue/PR comments via the GitHub API. Returns [] on failure.

    GitHub paginates at 30/page by default; for typical preflight use cases
    (≤ a few comments per PR) one page is sufficient. We deliberately do not
    paginate — the marker-search degrades gracefully if a prior preflight
    comment lives on a later page (the upsert falls through to a new POST).
    """
    if _httpx is None:
        return []
    err = _validate_inputs(repo, pr_number)
    if err:
        return []
    tok = token if token is not None else _resolve_token()
    if not tok:
        return []
    url = f"{GITHUB_API}/repos/{repo}/issues/{pr_number}/comments"
    headers = {
        "Authorization": f"Bearer {tok}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    owns_client = client is None
    c = client or _httpx.Client(timeout=timeout)
    try:
        resp = c.get(url, headers=headers, params={"per_page": 100})
        if resp.status_code != 200:
            return []
        data = resp.json()
        return data if isinstance(data, list) else []
    except Exception:
        return []
    finally:
        if owns_client:
            c.close()


def patch_pr_comment(
    repo: str,
    comment_id: int,
    body: str,
    *,
    token: Optional[str] = None,
    client: Optional[Any] = None,
    timeout: float = 10.0,
) -> Any:
    """PATCH an existing comment. Returns a WritebackResult-shaped object.

    Endpoint: /repos/{repo}/issues/comments/{comment_id} (works for both
    PR and Issue comments, since GitHub treats PR thread comments as Issue
    comments).
    """
    # We construct a duck-typed result object that matches WritebackResult.
    if _httpx is None:
        return _bare_result(posted=False, error="httpx not installed")
    if not repo or "/" not in repo:
        return _bare_result(posted=False, error=f"invalid repo: {repo!r}")
    if comment_id <= 0:
        return _bare_result(posted=False, error=f"invalid comment_id: {comment_id}")
    if not body or not body.strip():
        return _bare_result(posted=False, error="empty body")

    tok = token if token is not None else _resolve_token()
    if not tok:
        return _bare_result(
            posted=False,
            error="no GitHub token (set GH_TOKEN/GITHUB_TOKEN or `gh auth login`)",
        )

    url = f"{GITHUB_API}/repos/{repo}/issues/comments/{comment_id}"
    headers = {
        "Authorization": f"Bearer {tok}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    payload = {"body": body}
    owns_client = client is None
    c = client or _httpx.Client(timeout=timeout)
    try:
        resp = c.patch(url, headers=headers, json=payload)
        if resp.status_code == 200:
            data = resp.json()
            return _bare_result(
                posted=True,
                comment_url=data.get("html_url"),
                status_code=200,
            )
        return _bare_result(
            posted=False,
            status_code=resp.status_code,
            error=f"GitHub API returned {resp.status_code}: {resp.text[:200]}",
        )
    except Exception as e:
        return _bare_result(posted=False, error=f"transport error: {e}")
    finally:
        if owns_client:
            c.close()


@dataclass(frozen=True)
class _BareResult:
    posted: bool
    comment_url: Optional[str] = None
    status_code: Optional[int] = None
    error: Optional[str] = None


def _bare_result(**kwargs: Any) -> _BareResult:
    return _BareResult(**kwargs)


def find_existing_preflight_comment(
    comments: list[dict],
    header_marker: str,
) -> Optional[dict]:
    """Return the first comment whose body starts with header_marker.

    Why startswith(): publish_preflight prepends the marker as the very
    first line. If callers add their own pre-text, the marker won't be
    at the start — that's a deliberate design: only "owned" preflight
    comments get upserted.
    """
    if not header_marker:
        return None
    for c in comments:
        body = c.get("body", "")
        if isinstance(body, str) and body.startswith(header_marker):
            return c
    return None


def publish_preflight(
    summary: PreflightSummary,
    repo: str,
    pr_number: int,
    *,
    mode: str = "post",
    post_callback: Optional[PostCallback] = None,
    list_callback: Optional[ListCallback] = None,
    patch_callback: Optional[PatchCallback] = None,
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
            Callback signature: (repo, pr_number, body) → result-like.
        list_callback: testing seam for upsert's list step. Defaults to
            list_pr_comments. Callback signature: (repo, pr_number) → list[dict].
        patch_callback: testing seam for upsert's patch step. Defaults to
            patch_pr_comment. Callback signature: (repo, comment_id, body) → result-like.
        skip_when_empty: if True (default) and the summary has no quantities
            and no advice, return a no-op PublishResult instead of posting.
        header_marker: HTML comment prepended to the body and used by upsert
            mode to identify prior preflight comments. Default
            "<!-- ai-fea-preflight -->". Empty string disables the marker.

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
        list_cb = list_callback or list_pr_comments
        comments = list_cb(repo, pr_number)
        existing = find_existing_preflight_comment(comments, header_marker)
        if existing is not None:
            comment_id = existing.get("id")
            if not isinstance(comment_id, int) or comment_id <= 0:
                return PublishResult(
                    posted=False,
                    error=f"prior preflight comment has invalid id: {comment_id!r}",
                )
            patch_cb = patch_callback or patch_pr_comment
            raw = patch_cb(repo, comment_id, body)
            return PublishResult(
                posted=bool(getattr(raw, "posted", False)),
                comment_url=getattr(raw, "comment_url", None),
                status_code=getattr(raw, "status_code", None),
                error=getattr(raw, "error", None),
                action="updated" if getattr(raw, "posted", False) else None,
            )
        # Fall through: no prior comment, do a normal POST
        # (action will be "posted" below)

    # POST path
    callback = post_callback or _default_post_pr_comment
    if callback is None:
        return PublishResult(
            posted=False,
            error="github_writeback unavailable (httpx not installed). "
            'Install with: pip install -e ".[notion]" or pass post_callback=',
        )

    raw = callback(repo, pr_number, body)
    return PublishResult(
        posted=bool(getattr(raw, "posted", False)),
        comment_url=getattr(raw, "comment_url", None),
        status_code=getattr(raw, "status_code", None),
        error=getattr(raw, "error", None),
        action="posted" if getattr(raw, "posted", False) else None,
    )


def is_github_writeback_available() -> bool:
    """Convenience predicate. Useful for callers deciding whether to
    set up an explicit post_callback or rely on the default."""
    return _GITHUB_WRITEBACK_AVAILABLE
