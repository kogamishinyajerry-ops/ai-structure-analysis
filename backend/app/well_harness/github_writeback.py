"""GitHub PR / Issue writeback for well_harness run completions (P2).

When a well_harness run finishes and Notion has been updated, this
module posts a summary comment to the linked GitHub PR or Issue so
the conversation thread carries the verdict + Notion deep-link.

Designed to be opt-in (no token → no-op) and side-effect-isolated
(returns a structured result instead of raising on transport errors,
so a failed comment never breaks the rest of the writeback chain).

Required env / config:
    GH_TOKEN or GITHUB_TOKEN     PAT or GitHub App token with
                                 `repo:status` + `pull_request:write`
                                 on the target repo. Falls back to
                                 `gh auth token` output if neither set.
    `github_repository`          owner/repo, taken from NotionSyncConfig.

Public API:
    post_pr_comment(repo, pr_number, body) -> WritebackResult
    build_run_summary_comment(run_record, notion_url, repo, sha) -> str

Tests in tests/test_github_writeback.py mock the httpx client so the
module is offline-safe at test time.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from dataclasses import dataclass

import httpx

GITHUB_API = "https://api.github.com"

# GitHub repo identifier: `owner/name` where each part is the GitHub
# username/repo regex (alphanum, hyphens, dots, underscores; no leading
# hyphen for owner). Pre-emptive R2 hardening: pre-fix `_validate_repo`
# only checked for "/" which accepted `../foo/bar` and the like, which
# would build a path-traversing URL inside the GITHUB_API host. httpx
# url-encodes individual path components but not the entire path string,
# so this is worth tightening at the source.
_REPO_RE = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9._-]{0,38})/[A-Za-z0-9._-]{1,100}$")

# GitHub Issues / PR comments cap body size at ~65,536 chars. Posting
# something larger gets a 422. We pre-truncate with a clear suffix so
# the user-facing failure mode is "got a useful summary" rather than
# "got nothing because the API rejected the comment".
GITHUB_COMMENT_BODY_LIMIT = 65_536
_BODY_TRUNCATION_SUFFIX = "\n\n_…truncated by github_writeback (body exceeded 64KB)_"

# Pagination safety cap for list_pr_comments. GitHub allows per_page=100,
# so 10 pages = up to 1000 comments per PR — well above any realistic
# preflight workload. Beyond this we stop paginating to bound API spend
# and degrade gracefully (find_existing_preflight_comment will return
# None and the publisher falls through to POST).
_LIST_COMMENTS_MAX_PAGES = 10


def _is_positive_int(n: object) -> bool:
    """Strict positive-int check.

    R2 (post Codex R1 MEDIUM-1 on PR #65): the prior code did `n <= 0`
    which raises TypeError for str/None, and accepts `True`/`False`
    (bool subclasses int) silently. The module contract is "never
    raises on invalid input" — we must reject non-ints up front.
    """
    return isinstance(n, int) and not isinstance(n, bool) and n > 0


@dataclass
class WritebackResult:
    posted: bool
    comment_url: str | None = None
    status_code: int | None = None
    error: str | None = None


def _resolve_token() -> str | None:
    """Find a GitHub token from env, then fall back to `gh auth token`.

    R2 (pre-emptive): subprocess has a hard timeout so a hung `gh`
    binary cannot hang the writeback / publisher chain forever.
    Also strips leading/trailing whitespace from env tokens so an
    accidental trailing newline in a `.env` file doesn't break the
    `Bearer ...` header.
    """
    for var in ("GH_TOKEN", "GITHUB_TOKEN"):
        v = os.environ.get(var)
        if v:
            v = v.strip()
            if v:
                return v
    if shutil.which("gh"):
        try:
            return (
                subprocess.check_output(
                    ["gh", "auth", "token"],
                    text=True,
                    stderr=subprocess.DEVNULL,
                    timeout=5.0,
                ).strip()
                or None
            )
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError):
            # R2 (post Codex R1 MEDIUM on PR #64): widen catch to OSError so
            # FileNotFoundError (gh removed between which() and the call) and
            # PermissionError (gh found but not executable) both fall back
            # to "no token available" instead of leaking up through
            # writeback_enabled() and breaking the no-token no-op contract.
            return None
    return None


def post_pr_comment(
    repo: str,
    pr_number: int,
    body: str,
    *,
    token: str | None = None,
    client: httpx.Client | None = None,
    timeout: float = 10.0,
) -> WritebackResult:
    """Post `body` as a comment on `repo`'s PR/Issue `pr_number`.

    GitHub treats PR comments-on-thread (not review comments) as Issue
    comments, so the endpoint is /repos/{repo}/issues/{number}/comments
    for both PRs and Issues.

    Returns WritebackResult; never raises on network/HTTP errors.
    """
    # R2 (pre-emptive): tighten repo validation. Pre-fix only checked
    # `"/" in repo`, which accepted `../foo/bar` and the like — those
    # would build a path-traversing URL into the GITHUB_API host.
    if not repo or not _REPO_RE.match(repo):
        return WritebackResult(posted=False, error=f"invalid repo: {repo!r} (expected owner/name)")

    # R2 (post Codex R1 MEDIUM-1 on PR #65): strict positive-int check
    # so a stray str/None/float/bool can't break the never-raise contract.
    if not _is_positive_int(pr_number):
        return WritebackResult(posted=False, error=f"invalid pr_number: {pr_number!r}")

    if not body or not body.strip():
        return WritebackResult(posted=False, error="empty body")

    # R2 (pre-emptive): truncate to GitHub's 65,536-char cap with a
    # clear marker so the operator sees a useful summary instead of
    # a 422 from the API.
    if len(body) > GITHUB_COMMENT_BODY_LIMIT:
        head_len = GITHUB_COMMENT_BODY_LIMIT - len(_BODY_TRUNCATION_SUFFIX)
        body = body[:head_len] + _BODY_TRUNCATION_SUFFIX

    tok = token if token is not None else _resolve_token()
    if not tok:
        return WritebackResult(
            posted=False,
            error="no GitHub token (set GH_TOKEN/GITHUB_TOKEN or `gh auth login`)",
        )

    url = f"{GITHUB_API}/repos/{repo}/issues/{pr_number}/comments"
    headers = {
        "Authorization": f"Bearer {tok}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    payload = {"body": body}

    owns_client = client is None
    c = client or httpx.Client(timeout=timeout)
    try:
        resp = c.post(url, headers=headers, json=payload)
        if resp.status_code == 201:
            # R2 (post Codex R1 LOW on PR #64): a 201 with a malformed
            # body (proxy mangled, content-type drift) used to escape
            # via JSONDecodeError. The module contract is "never raises
            # on transport / response errors", so wrap json() too.
            try:
                data = resp.json()
                comment_url = data.get("html_url") if isinstance(data, dict) else None
            except (ValueError, TypeError):
                comment_url = None
            return WritebackResult(
                posted=True,
                comment_url=comment_url,
                status_code=201,
            )
        return WritebackResult(
            posted=False,
            status_code=resp.status_code,
            error=f"GitHub API returned {resp.status_code}: {resp.text[:200]}",
        )
    except httpx.HTTPError as e:
        return WritebackResult(posted=False, error=f"transport error: {e}")
    finally:
        if owns_client:
            c.close()


def list_pr_comments(
    repo: str,
    pr_number: int,
    *,
    token: str | None = None,
    client: httpx.Client | None = None,
    timeout: float = 10.0,
    per_page: int = 100,
) -> list[dict]:
    """List Issue/PR comments for `pr_number`. Never raises.

    Returns the raw JSON list (each dict has at least `id`, `body`,
    `html_url`). Returns `[]` on any failure (no token, transport
    error, non-200 response, malformed JSON, missing repo).

    Used by the upsert path in `preflight_publish.publish_preflight` to
    locate a prior preflight comment by `header_marker`.

    Pagination: GitHub paginates issue comments at 30/page by default;
    we request `per_page=100` (the API max) and walk pages until either
    the API exhausts (a short page is the last page) or
    `_LIST_COMMENTS_MAX_PAGES` is reached. The cap bounds API spend
    while still covering up to ~1000 comments per PR — far beyond any
    realistic preflight workload. If a prior preflight lives past the
    cap, the publisher degrades gracefully to a fresh POST.

    R2 (post Codex R1 MEDIUM-2 on PR #65): single-page lookup let the
    upsert mode reintroduce duplicates on busy PRs once the prior
    preflight scrolled past 100 comments — defeating the no-spam goal.
    """
    if not repo or not _REPO_RE.match(repo):
        return []
    # R2 (post Codex R1 MEDIUM-1 on PR #65): strict int check so a
    # stray str/None/float/bool returns [] instead of TypeError.
    if not _is_positive_int(pr_number):
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
    c = client or httpx.Client(timeout=timeout)
    try:
        all_comments: list[dict] = []
        for page in range(1, _LIST_COMMENTS_MAX_PAGES + 1):
            try:
                resp = c.get(
                    url,
                    headers=headers,
                    params={"per_page": per_page, "page": page},
                )
            except httpx.HTTPError:
                # Return what we have so far rather than dropping all
                # already-fetched pages on a late transport blip.
                return all_comments
            if resp.status_code != 200:
                return all_comments
            try:
                data = resp.json()
            except (ValueError, TypeError):
                return all_comments
            if not isinstance(data, list):
                return all_comments
            all_comments.extend(data)
            # A short page (less than per_page) is the last page —
            # short-circuit to avoid an extra GET that we know returns [].
            if len(data) < per_page:
                return all_comments
        return all_comments
    finally:
        if owns_client:
            c.close()


def patch_pr_comment(
    repo: str,
    comment_id: int,
    body: str,
    *,
    token: str | None = None,
    client: httpx.Client | None = None,
    timeout: float = 10.0,
) -> WritebackResult:
    """PATCH an existing PR/Issue comment in place.

    Endpoint: /repos/{owner}/{name}/issues/comments/{id}. GitHub treats
    PR thread comments as Issue comments, so this works for both.

    Returns a `posted=True` WritebackResult on 200 (the field is named
    `posted` for symmetry with `post_pr_comment`; semantically here it
    means "request succeeded — comment was updated"). Never raises on
    transport / HTTP errors.

    Mirrors `post_pr_comment`'s R2 hardening: same _REPO_RE, body cap,
    json() / non-dict guards.
    """
    if not repo or not _REPO_RE.match(repo):
        return WritebackResult(posted=False, error=f"invalid repo: {repo!r} (expected owner/name)")
    # R2 (post Codex R1 MEDIUM-1 on PR #65): strict positive-int check
    # so a stray str/None/float/bool can't break the never-raise contract.
    if not _is_positive_int(comment_id):
        return WritebackResult(posted=False, error=f"invalid comment_id: {comment_id!r}")
    if not body or not body.strip():
        return WritebackResult(posted=False, error="empty body")

    if len(body) > GITHUB_COMMENT_BODY_LIMIT:
        head_len = GITHUB_COMMENT_BODY_LIMIT - len(_BODY_TRUNCATION_SUFFIX)
        body = body[:head_len] + _BODY_TRUNCATION_SUFFIX

    tok = token if token is not None else _resolve_token()
    if not tok:
        return WritebackResult(
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
    c = client or httpx.Client(timeout=timeout)
    try:
        resp = c.patch(url, headers=headers, json=payload)
        if resp.status_code == 200:
            try:
                data = resp.json()
                comment_url = data.get("html_url") if isinstance(data, dict) else None
            except (ValueError, TypeError):
                comment_url = None
            return WritebackResult(
                posted=True,
                comment_url=comment_url,
                status_code=200,
            )
        return WritebackResult(
            posted=False,
            status_code=resp.status_code,
            error=f"GitHub API returned {resp.status_code}: {resp.text[:200]}",
        )
    except httpx.HTTPError as e:
        return WritebackResult(posted=False, error=f"transport error: {e}")
    finally:
        if owns_client:
            c.close()


def build_run_summary_comment(
    case_id: str,
    verdict: str,
    summary_text: str,
    notion_url: str | None = None,
    commit_sha: str | None = None,
    extra_lines: list[str] | None = None,
) -> str:
    """Format a run summary as Markdown for posting to a PR/Issue thread."""
    lines = [
        f"### well_harness run · {case_id} · **{verdict}**",
        "",
        summary_text.strip(),
    ]
    if commit_sha:
        lines.append("")
        lines.append(f"Commit: `{commit_sha[:12]}`")
    if notion_url:
        lines.append(f"Notion: [{notion_url}]({notion_url})")
    if extra_lines:
        lines.append("")
        lines.extend(extra_lines)
    lines.append("")
    lines.append("---")
    lines.append(
        "*Auto-posted by well_harness github_writeback (P2 / Notion task 345c6894-2bed-81b9).*"
    )
    return "\n".join(lines)


def writeback_enabled() -> bool:
    """Whether writeback should be attempted given current env."""
    return _resolve_token() is not None
