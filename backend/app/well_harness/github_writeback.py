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
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
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

    if pr_number <= 0:
        return WritebackResult(posted=False, error=f"invalid pr_number: {pr_number}")

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
            data = resp.json()
            return WritebackResult(
                posted=True,
                comment_url=data.get("html_url"),
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
