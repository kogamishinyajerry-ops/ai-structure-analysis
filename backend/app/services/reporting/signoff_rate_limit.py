"""Tier 1 candidate signoff rate limit (FM-04a Phase 10 D).

Tier 1 engineering candidate; not signed validation; not benchmark agreement.

Sliding-window per-(case_id, reviewer) rate limit applied at the
``POST /api/v1/signoff-history/<case-id>`` route boundary. Prevents
a careless or malicious reviewer from flooding the signoff log on
a single case in a short window.

Constants:

* :data:`RATE_LIMIT_MAX_REQUESTS` — max signoffs per window per
  (case_id, reviewer) pair.
* :data:`RATE_LIMIT_WINDOW_SECONDS` — sliding window length.

State model:

* Module-level dict keyed by ``(case_id, reviewer)``, value is a
  list of UTC timestamps (seconds) of recent allowed submissions.
* Each call to :func:`check_and_record` evicts entries older than
  ``RATE_LIMIT_WINDOW_SECONDS`` before counting (lazy eviction —
  no background timer).
* :func:`_reset_state_for_tests` clears the dict; the test fixture
  for the rate-limit suite calls it in ``setup_method`` /
  ``conftest`` so tests are deterministic.

Clock injection: every public function accepts a ``now`` parameter
in seconds since epoch. Tests pass a fixed value rather than calling
``time.time()`` (Phase 10 anti-gaming guard T: -2 — no
``time.sleep`` in rate-limit tests).

Forbidden wording (per ADR-023 + ADR-024 lite): no ``benchmark
agreement``, no ``signed validation``, no ``perforation completed``,
no ``bullet-through-steel complete``, no ``validated physics``.

Closes Phase 9 retrospective carry-forward §4.
"""

from __future__ import annotations

import time
from collections import defaultdict
from dataclasses import dataclass

# Named constants (Phase 10 anti-gaming guard M: -2)
RATE_LIMIT_MAX_REQUESTS: int = 5
"""Maximum number of signoff POSTs per (case_id, reviewer) within
``RATE_LIMIT_WINDOW_SECONDS``. Pinned by
``test_rate_limit_max_requests_is_5``."""

RATE_LIMIT_WINDOW_SECONDS: int = 60
"""Sliding window length in seconds. Pinned by
``test_rate_limit_window_seconds_is_60``."""


@dataclass(frozen=True)
class RateLimitResult:
    """Outcome of a rate-limit check.

    * ``allowed=True`` — submission may proceed. ``retry_after_seconds=0``.
    * ``allowed=False`` — submission must be refused with HTTP 429.
      ``retry_after_seconds`` is the integer number of seconds until
      the oldest request in the current window expires.
    """

    allowed: bool
    retry_after_seconds: int


# Module-level state. Each key is a (case_id, reviewer) pair; each
# value is a list of float timestamps (seconds since epoch) of past
# ALLOWED submissions in chronological order.
_recent_submissions: dict[tuple[str, str], list[float]] = defaultdict(list)


def check_and_record(
    case_id: str,
    reviewer: str,
    *,
    now: float | None = None,
) -> RateLimitResult:
    """Evict expired entries, count remaining, and either record-and-allow
    or refuse with a Retry-After hint.

    The rate-limit state is per-(case_id, reviewer) pair. A reviewer
    can submit ``RATE_LIMIT_MAX_REQUESTS`` signoffs to one case in a
    window, and independently submit the same number to a different
    case; two distinct reviewers can each submit the limit to the
    same case.

    Empty / whitespace-only inputs are passed through to the caller's
    own validation; this function does not interpret them — it just
    keys on the literal string values it receives.
    """
    moment = time.time() if now is None else now
    key = (case_id, reviewer)
    cutoff = moment - RATE_LIMIT_WINDOW_SECONDS

    # Evict expired entries first (lazy eviction).
    bucket = _recent_submissions[key]
    bucket[:] = [t for t in bucket if t >= cutoff]

    if len(bucket) >= RATE_LIMIT_MAX_REQUESTS:
        # The oldest surviving entry determines when the window will
        # next have room. Retry-After is the integer ceiling of the
        # seconds remaining; minimum 1 so callers always see a
        # meaningful countdown.
        oldest = bucket[0]
        seconds_until_free = max(
            1, int(oldest + RATE_LIMIT_WINDOW_SECONDS - moment) + 1
        )
        return RateLimitResult(allowed=False, retry_after_seconds=seconds_until_free)

    # Allow + record.
    bucket.append(moment)
    return RateLimitResult(allowed=True, retry_after_seconds=0)


def _reset_state_for_tests() -> None:
    """Clear the rate-limit state. Phase 10 anti-gaming guard M: -3:
    rate-limit state has a documented, named test reset hook so the
    suite is deterministic without relying on process boundaries."""
    _recent_submissions.clear()
