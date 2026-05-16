"""FM-04a Phase 9 C — bucket sensitivity matrix.

Tier 1 engineering candidate; not signed validation; not benchmark agreement.

Pins the cohort-executive-summary bucket boundaries:

* `HEALTHY_TRUST_SCORE_MIN == 80`
* `WATCHING_TRUST_SCORE_MIN == 50`

…and the bucket outcome for every neighbour of the two thresholds
crossed with every signoff verdict. A silent edit of either constant
flips at least one boundary cell.

SSOT methodology doc: `.planning/methodology/cohort_bucket_thresholds.md`.
"""

from __future__ import annotations

import pytest
from app.services.reporting.cohort_executive_summary import (
    HEALTHY_TRUST_SCORE_MIN,
    WATCHING_TRUST_SCORE_MIN,
    _classify_bucket,
)

# ---------------------------------------------------------------------
# Threshold constants are pinned at 80 / 50
# ---------------------------------------------------------------------


def test_healthy_trust_score_min_is_80() -> None:
    """A silent edit of HEALTHY_TRUST_SCORE_MIN flips the 80 boundary cell."""
    assert HEALTHY_TRUST_SCORE_MIN == 80


def test_watching_trust_score_min_is_50() -> None:
    """A silent edit of WATCHING_TRUST_SCORE_MIN flips the 50 boundary cell."""
    assert WATCHING_TRUST_SCORE_MIN == 50


def test_healthy_threshold_strictly_above_watching_threshold() -> None:
    """Precedence ladder collapses if HEALTHY < WATCHING."""
    assert HEALTHY_TRUST_SCORE_MIN > WATCHING_TRUST_SCORE_MIN


# ---------------------------------------------------------------------
# trust_score boundary cells — no signoff, no alarm
# ---------------------------------------------------------------------


@pytest.mark.parametrize(
    "score, expected",
    [
        (0, "regressed"),  # well below WATCHING_MIN
        (49, "regressed"),  # one below WATCHING_MIN
        (50, "watching"),  # exactly WATCHING_MIN
        (51, "watching"),  # one above WATCHING_MIN
        (79, "watching"),  # one below HEALTHY_MIN
        (80, "healthy"),  # exactly HEALTHY_MIN
        (81, "healthy"),  # one above HEALTHY_MIN
        (99, "healthy"),  # well above HEALTHY_MIN
        (100, "healthy"),  # top of envelope
    ],
)
def test_bucket_by_score_only(score: int, expected: str) -> None:
    assert _classify_bucket(score, alarm_count=0, signoff_verdict=None) == expected


def test_bucket_with_no_snapshot_falls_to_healthy() -> None:
    """trust_score=None is the "no snapshot yet" path; defaults to healthy."""
    assert _classify_bucket(None, alarm_count=0, signoff_verdict=None) == "healthy"


# ---------------------------------------------------------------------
# alarm precedence — any alarm > 0 dominates score
# ---------------------------------------------------------------------


@pytest.mark.parametrize("score", [None, 0, 49, 50, 79, 80, 99, 100])
def test_any_alarm_forces_regressed_regardless_of_score(score: int | None) -> None:
    assert _classify_bucket(score, alarm_count=1, signoff_verdict=None) == "regressed"


# ---------------------------------------------------------------------
# blocked_pending_input verdict — overrides score AND alarm
# ---------------------------------------------------------------------


@pytest.mark.parametrize("score", [None, 0, 50, 80, 99, 100])
@pytest.mark.parametrize("alarm_count", [0, 1])
def test_blocked_pending_input_forces_regressed(score: int | None, alarm_count: int) -> None:
    assert (
        _classify_bucket(score, alarm_count, signoff_verdict="blocked_pending_input") == "regressed"
    )


# ---------------------------------------------------------------------
# Watching signoff verdicts — downgrade healthy → watching
# ---------------------------------------------------------------------


@pytest.mark.parametrize("verdict", ["watching", "needs_more_evidence", "needs_more_convergence"])
def test_watching_verdict_downgrades_healthy_score_to_watching(verdict: str) -> None:
    """A score that would be healthy (≥ 80) drops to watching when the
    reviewer's latest verdict says so."""
    assert _classify_bucket(95, alarm_count=0, signoff_verdict=verdict) == "watching"


@pytest.mark.parametrize("verdict", ["watching", "needs_more_evidence", "needs_more_convergence"])
def test_watching_verdict_does_not_lift_regressed_score_to_watching(
    verdict: str,
) -> None:
    """A score below WATCHING_MIN stays regressed — verdict cannot lift it."""
    assert _classify_bucket(40, alarm_count=0, signoff_verdict=verdict) == "regressed"


@pytest.mark.parametrize("verdict", ["watching", "needs_more_evidence", "needs_more_convergence"])
def test_watching_verdict_does_not_override_alarm(verdict: str) -> None:
    """An alarm fires regressed regardless of the watching verdict."""
    assert _classify_bucket(95, alarm_count=1, signoff_verdict=verdict) == "regressed"


# ---------------------------------------------------------------------
# Boundary cells crossed with watching verdict
# ---------------------------------------------------------------------


@pytest.mark.parametrize(
    "score, expected",
    [
        (49, "regressed"),  # below WATCHING_MIN → regressed wins over verdict
        (50, "watching"),  # at WATCHING_MIN; verdict matches bucket
        (79, "watching"),  # below HEALTHY_MIN; verdict matches bucket
        (80, "watching"),  # at HEALTHY_MIN; verdict downgrades healthy
        (99, "watching"),  # well above HEALTHY_MIN; verdict still downgrades
    ],
)
def test_boundary_with_watching_signoff(score: int, expected: str) -> None:
    assert _classify_bucket(score, alarm_count=0, signoff_verdict="watching") == expected


# ---------------------------------------------------------------------
# Unknown signoff verdict — falls through to score-only path
# ---------------------------------------------------------------------


def test_unknown_signoff_verdict_falls_through_to_score_path() -> None:
    """Defensive: a verdict not in _WATCHING_SIGNOFF_VERDICTS and not
    "blocked_pending_input" lets the score-only path decide. (The
    POST endpoint refuses such verdicts at HTTP-422; this is the
    last-line defense for direct service-layer callers.)"""
    assert _classify_bucket(95, alarm_count=0, signoff_verdict="some_unseen_verdict") == "healthy"
    assert _classify_bucket(60, alarm_count=0, signoff_verdict="some_unseen_verdict") == "watching"


# ---------------------------------------------------------------------
# Drift guard: rebalance methodology procedure is documented
# ---------------------------------------------------------------------


def test_methodology_doc_exists_at_expected_path() -> None:
    """Phase 9 C ships the rebalance methodology doc; the test makes
    the doc impossible to silently delete."""
    from pathlib import Path

    repo_root = Path(__file__).resolve().parents[1]
    doc_path = repo_root / ".planning" / "methodology" / "cohort_bucket_thresholds.md"
    assert doc_path.is_file()
    text = doc_path.read_text(encoding="utf-8")
    # The doc must reference the two constants by full Python identifier
    # (Phase 9 anti-gaming guard D: -2).
    assert "HEALTHY_TRUST_SCORE_MIN" in text
    assert "WATCHING_TRUST_SCORE_MIN" in text
    # And the precedence rule must be documented.
    assert "regressed > watching > healthy" in text
    # And the Tier 1 disclaimer trio must be present.
    lowered = text.lower()
    assert "tier 1 engineering candidate" in lowered
    assert "not signed validation" in lowered
    assert "not benchmark agreement" in lowered
