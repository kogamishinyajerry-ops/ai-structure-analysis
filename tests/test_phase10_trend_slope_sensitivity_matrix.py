"""FM-04a Phase 10 C — trend-slope sensitivity matrix.

Tier 1 engineering candidate; not signed validation; not benchmark agreement.

Pins the cohort-trend-anomalies severity boundaries:

* `TREND_SLOPE_INFO_MAX   == -0.5`
* `TREND_SLOPE_WARN_MAX   == -1.5`
* `TREND_SLOPE_DANGER_MAX == -3.0`
* `TREND_MIN_POINTS       == 3`

…and the severity outcome for every neighbour of the three slope
thresholds. A silent edit of any constant flips at least one
boundary cell.

SSOT methodology doc: `.planning/methodology/cohort_trend_slope_thresholds.md`.
"""

from __future__ import annotations

import pytest
from app.services.reporting.cohort_trend_anomalies import (
    TREND_MIN_POINTS,
    TREND_SLOPE_DANGER_MAX,
    TREND_SLOPE_INFO_MAX,
    TREND_SLOPE_WARN_MAX,
    _least_squares_slope,
    severity_for_slope,
)

# ---------------------------------------------------------------------
# Threshold constants are pinned at the values the methodology doc cites
# ---------------------------------------------------------------------


def test_trend_slope_info_max_is_neg_0_5() -> None:
    assert TREND_SLOPE_INFO_MAX == -0.5


def test_trend_slope_warn_max_is_neg_1_5() -> None:
    assert TREND_SLOPE_WARN_MAX == -1.5


def test_trend_slope_danger_max_is_neg_3_0() -> None:
    assert TREND_SLOPE_DANGER_MAX == -3.0


def test_trend_min_points_is_3() -> None:
    assert TREND_MIN_POINTS == 3


def test_threshold_monotonicity() -> None:
    """DANGER < WARN < INFO < 0 — precedence ladder collapses otherwise."""
    assert TREND_SLOPE_DANGER_MAX < TREND_SLOPE_WARN_MAX
    assert TREND_SLOPE_WARN_MAX < TREND_SLOPE_INFO_MAX
    assert TREND_SLOPE_INFO_MAX < 0


# ---------------------------------------------------------------------
# severity_for_slope boundary matrix
# ---------------------------------------------------------------------


@pytest.mark.parametrize(
    "slope, expected",
    [
        # Above the firing gate (standalone returns conservative 'info')
        (1.0, "info"),
        (0.0, "info"),
        (-0.49, "info"),
        # Exactly at INFO_MAX -> still info (slope <= -0.5 routes to info)
        (-0.5, "info"),
        # Just past INFO_MAX -> still info
        (-0.51, "info"),
        # Approaching WARN_MAX from above -> info
        (-1.49, "info"),
        # Exactly at WARN_MAX -> warn (slope <= -1.5 routes to warn)
        (-1.5, "warn"),
        # Just past WARN_MAX -> warn
        (-1.51, "warn"),
        # Approaching DANGER_MAX from above -> warn
        (-2.99, "warn"),
        # Exactly at DANGER_MAX -> danger (slope <= -3.0 routes to danger)
        (-3.0, "danger"),
        # Just past DANGER_MAX -> danger
        (-3.01, "danger"),
        # Well into danger -> danger
        (-10.0, "danger"),
    ],
)
def test_severity_for_slope_boundary_matrix(slope: float, expected: str) -> None:
    assert severity_for_slope(slope) == expected


# ---------------------------------------------------------------------
# Least-squares slope behavior at the cohort floor
# ---------------------------------------------------------------------


@pytest.mark.parametrize("n_points", [0, 1, 2])
def test_under_floor_slope_calls_handled_safely(n_points: int) -> None:
    """Below TREND_MIN_POINTS the slope cannot be computed reliably.

    The builder's firing gate (_build_event_for_axis) refuses to call
    _least_squares_slope when N < TREND_MIN_POINTS. This test just
    documents that fact + verifies _least_squares_slope returns 0.0
    for the degenerate denominator case (all-equal values), which is
    the closest analog to "no signal" at small N.
    """
    if n_points < 2:
        # _least_squares_slope's denominator goes to 0 for N <= 1.
        # Caller is responsible for not invoking it here; the builder
        # respects TREND_MIN_POINTS = 3.
        return
    # N == 2 with equal values -> slope == 0 (degenerate denominator
    # is not 0 here: n*sum_x2 - sum_x^2 = 2*1 - 1 = 1).
    values = [50] * n_points
    assert _least_squares_slope(values) == 0.0


@pytest.mark.parametrize("n_points", [3, 4, 5])
def test_at_or_above_floor_slope_is_well_defined(n_points: int) -> None:
    """N >= TREND_MIN_POINTS yields a well-defined slope; descending
    sequences produce negative slopes; ascending produce positive."""
    descending = list(range(100, 100 - 10 * n_points, -10))[:n_points]
    ascending = list(range(0, 10 * n_points, 10))[:n_points]
    flat = [50] * n_points
    assert _least_squares_slope(descending) < 0
    assert _least_squares_slope(ascending) > 0
    assert _least_squares_slope(flat) == 0.0


# ---------------------------------------------------------------------
# Drift guard: methodology doc cites all four constants + Tier 1
# disclaimer trio + the "more negative is worse" convention
# ---------------------------------------------------------------------


def test_methodology_doc_exists_at_expected_path() -> None:
    """Phase 10 C ships the trend rebalance methodology doc; the test
    makes the doc impossible to silently delete."""
    from pathlib import Path

    repo_root = Path(__file__).resolve().parents[1]
    doc_path = repo_root / ".planning" / "methodology" / "cohort_trend_slope_thresholds.md"
    assert doc_path.is_file()
    text = doc_path.read_text(encoding="utf-8")
    # All 4 constants by full Python identifier (Phase 10 anti-gaming
    # guard D: -2).
    assert "TREND_SLOPE_INFO_MAX" in text
    assert "TREND_SLOPE_WARN_MAX" in text
    assert "TREND_SLOPE_DANGER_MAX" in text
    assert "TREND_MIN_POINTS" in text
    # The "more negative is worse" convention must be documented.
    assert "more negative is worse" in text.lower()
    # Tier 1 disclaimer trio must be present.
    lowered = text.lower()
    assert "tier 1 engineering candidate" in lowered
    assert "not signed validation" in lowered
    assert "not benchmark agreement" in lowered
    # The rebalance procedure must be procedural (numbered list).
    assert "Rebalance checklist" in text
