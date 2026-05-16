"""FM-04a Phase 8 E — property-based tests for cohort anomaly arithmetic.

Tier 1 engineering candidate; not signed validation; not benchmark agreement.

All tests use ``derandomize=True`` so any failure is reproducible
without needing the Hypothesis database (Phase 8 anti-gaming guard
T: -3).
"""

from __future__ import annotations

from app.services.reporting.cohort_anomalies import (
    ANOMALY_SIGMA_DANGER_MIN,
    ANOMALY_SIGMA_INFO_MIN,
    ANOMALY_SIGMA_WARN_MIN,
    severity_for,
)
from hypothesis import given, settings
from hypothesis import strategies as st

_PROFILE = settings(derandomize=True, max_examples=25, deadline=None)


# ---------------------------------------------------------------------
# severity_for invariants
# ---------------------------------------------------------------------


@_PROFILE
@given(st.floats(min_value=ANOMALY_SIGMA_DANGER_MIN, max_value=1e6))
def test_property_above_danger_always_danger(z: float) -> None:
    assert severity_for(z) == "danger"
    assert severity_for(-z) == "danger"


@_PROFILE
@given(
    st.floats(
        min_value=ANOMALY_SIGMA_WARN_MIN,
        max_value=ANOMALY_SIGMA_DANGER_MIN - 1e-6,
    )
)
def test_property_in_warn_range_returns_warn(z: float) -> None:
    assert severity_for(z) == "warn"
    assert severity_for(-z) == "warn"


@_PROFILE
@given(
    st.floats(
        min_value=ANOMALY_SIGMA_INFO_MIN,
        max_value=ANOMALY_SIGMA_WARN_MIN - 1e-6,
    )
)
def test_property_in_info_range_returns_info(z: float) -> None:
    assert severity_for(z) == "info"
    assert severity_for(-z) == "info"


@_PROFILE
@given(st.floats(min_value=0.0, max_value=ANOMALY_SIGMA_INFO_MIN - 1e-6))
def test_property_below_info_floor_returns_info(z: float) -> None:
    """Below the info floor, severity_for routes to info as the
    most-conservative bucket; the gate that prevents below-floor
    z-scores from emitting anomalies lives in the builder, not in
    severity_for itself."""
    assert severity_for(z) == "info"
    assert severity_for(-z) == "info"
