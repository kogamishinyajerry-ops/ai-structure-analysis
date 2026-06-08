"""FM-04a Phase 10 D — per-(case, reviewer) signoff rate limit tests.

Tier 1 engineering candidate; not signed validation; not benchmark agreement.

Pins:
* RATE_LIMIT_MAX_REQUESTS == 5
* RATE_LIMIT_WINDOW_SECONDS == 60
* 5 sub-limit submissions allowed in the same window.
* 6th submission in the same window returns 429 + Retry-After.
* Different reviewer on same case is independent (gets full limit).
* Same reviewer on different case is independent (gets full limit).
* After the window expires (mocked clock), the counter resets.
* HTTP-429 surfaced through the route layer with Retry-After header.
* `_reset_state_for_tests` clears state cleanly.

Phase 10 anti-gaming guard T: -2 — tests use a mocked clock via the
`now=` parameter, NOT `time.sleep`. Tests are deterministic and run
in milliseconds.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

import httpx
import pytest
from app.api.routes import signoff_history as route_module
from app.main import app
from app.services.reporting.signoff_rate_limit import (
    RATE_LIMIT_MAX_REQUESTS,
    RATE_LIMIT_WINDOW_SECONDS,
    _reset_state_for_tests,
    check_and_record,
)


@pytest.fixture(autouse=True)
def _reset_rate_limit_state() -> None:
    """Clear the rate-limit state before each test so cases run in
    isolation. (Phase 10 anti-gaming guard M: -3 — documented reset
    hook used here.)"""
    _reset_state_for_tests()


# ---------------------------------------------------------------------
# Named constants
# ---------------------------------------------------------------------


def test_rate_limit_max_requests_is_5() -> None:
    assert RATE_LIMIT_MAX_REQUESTS == 5


def test_rate_limit_window_seconds_is_60() -> None:
    assert RATE_LIMIT_WINDOW_SECONDS == 60


# ---------------------------------------------------------------------
# Service-layer behavior (synthetic clock)
# ---------------------------------------------------------------------


def test_single_submission_is_allowed() -> None:
    r = check_and_record("GS-A-candidate", "alice", now=1000.0)
    assert r.allowed is True
    assert r.retry_after_seconds == 0


def test_five_submissions_in_window_all_allowed() -> None:
    for i in range(RATE_LIMIT_MAX_REQUESTS):
        r = check_and_record("GS-A-candidate", "alice", now=1000.0 + i)
        assert r.allowed is True, f"submission {i + 1} should be allowed"


def test_sixth_submission_in_window_refused_with_retry_after() -> None:
    for i in range(RATE_LIMIT_MAX_REQUESTS):
        check_and_record("GS-A-candidate", "alice", now=1000.0 + i)
    # 6th attempt 1 second after the 5th -> refused.
    r = check_and_record("GS-A-candidate", "alice", now=1000.0 + RATE_LIMIT_MAX_REQUESTS)
    assert r.allowed is False
    assert r.retry_after_seconds >= 1
    assert r.retry_after_seconds <= RATE_LIMIT_WINDOW_SECONDS + 1


def test_different_reviewer_same_case_is_independent() -> None:
    for i in range(RATE_LIMIT_MAX_REQUESTS):
        check_and_record("GS-A-candidate", "alice", now=1000.0 + i)
    # bob has not submitted yet; should get the full limit.
    r = check_and_record("GS-A-candidate", "bob", now=1005.0)
    assert r.allowed is True


def test_same_reviewer_different_case_is_independent() -> None:
    for i in range(RATE_LIMIT_MAX_REQUESTS):
        check_and_record("GS-A-candidate", "alice", now=1000.0 + i)
    # alice has not submitted to GS-B yet; should get the full limit.
    r = check_and_record("GS-B-candidate", "alice", now=1005.0)
    assert r.allowed is True


def test_window_expiry_resets_counter() -> None:
    # 5 submissions at t=1000 — bucket is full.
    for i in range(RATE_LIMIT_MAX_REQUESTS):
        check_and_record("GS-A-candidate", "alice", now=1000.0 + i)
    # Try 6th just past the boundary -> refused.
    refused = check_and_record("GS-A-candidate", "alice", now=1000.0 + RATE_LIMIT_MAX_REQUESTS)
    assert refused.allowed is False
    # Wait past the window (lazy eviction kicks in on the next call).
    # The first 5 submissions land at times 1000..1004; the window is
    # 60 seconds. At t = 1004 + 60 + 1 = 1065 the oldest evicts.
    allowed_after = check_and_record(
        "GS-A-candidate", "alice", now=1000.0 + RATE_LIMIT_WINDOW_SECONDS + 5
    )
    assert allowed_after.allowed is True


def test_reset_state_clears_recent_submissions() -> None:
    for i in range(RATE_LIMIT_MAX_REQUESTS):
        check_and_record("GS-A-candidate", "alice", now=1000.0 + i)
    # Bucket should be full at this point.
    refused = check_and_record("GS-A-candidate", "alice", now=1000.0 + RATE_LIMIT_MAX_REQUESTS)
    assert refused.allowed is False
    # Reset; the very next call must succeed.
    _reset_state_for_tests()
    allowed = check_and_record("GS-A-candidate", "alice", now=1000.0 + RATE_LIMIT_MAX_REQUESTS + 1)
    assert allowed.allowed is True


def test_retry_after_seconds_is_strictly_positive_when_refused() -> None:
    """`Retry-After: 0` would be a UX bug — countdown wouldn't appear.
    The service guarantees `>= 1` when refused."""
    for i in range(RATE_LIMIT_MAX_REQUESTS):
        check_and_record("GS-A-candidate", "alice", now=1000.0 + i)
    refused = check_and_record("GS-A-candidate", "alice", now=1000.0 + RATE_LIMIT_MAX_REQUESTS)
    assert refused.allowed is False
    assert refused.retry_after_seconds >= 1


def test_concurrent_same_second_burst_does_not_double_count() -> None:
    """Five calls in the same UTC second all count distinct entries,
    so the 6th must be refused. No race relaxation."""
    for _ in range(RATE_LIMIT_MAX_REQUESTS):
        r = check_and_record("GS-A-candidate", "alice", now=1000.0)
        assert r.allowed is True
    r = check_and_record("GS-A-candidate", "alice", now=1000.0)
    assert r.allowed is False


# ---------------------------------------------------------------------
# HTTP-422 / 429 surfaced through the route layer
# ---------------------------------------------------------------------


class _SyncASGIClient:
    def __init__(self, asgi_app: Any) -> None:
        self._transport = httpx.ASGITransport(app=asgi_app)

    def post(self, url: str, *, json_body: Any) -> httpx.Response:
        async def _run() -> httpx.Response:
            async with httpx.AsyncClient(
                transport=self._transport, base_url="http://testserver"
            ) as client:
                return await client.post(url, json=json_body)

        return asyncio.run(_run())


@pytest.fixture()
def client() -> _SyncASGIClient:
    return _SyncASGIClient(app)


@pytest.fixture()
def fake_repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(route_module, "_repo_root", lambda: tmp_path)
    return tmp_path


def test_route_returns_429_on_sixth_submission_with_retry_after_header(
    client: _SyncASGIClient, fake_repo: Path
) -> None:
    """The route layer translates a rate-limit refusal into HTTP-429 +
    Retry-After header. Real wall clock is used here because the route
    doesn't accept a `now` parameter; we just submit 6 times in rapid
    succession, which fits comfortably inside the 60-second window."""
    for _ in range(RATE_LIMIT_MAX_REQUESTS):
        res = client.post(
            "/api/v1/signoff-history/GS-A-candidate",
            json_body={"reviewer": "alice", "verdict": "watching", "notes": "ok"},
        )
        assert res.status_code == 200, res.text
    res_refused = client.post(
        "/api/v1/signoff-history/GS-A-candidate",
        json_body={"reviewer": "alice", "verdict": "watching", "notes": "ok"},
    )
    assert res_refused.status_code == 429
    assert "rate limit exceeded" in res_refused.json()["detail"]
    retry_after = res_refused.headers.get("Retry-After")
    assert retry_after is not None
    assert int(retry_after) >= 1
