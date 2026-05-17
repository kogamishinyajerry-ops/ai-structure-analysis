"""FM-04a Phase 29 D — per-case registry tolerance pin.

Phase 28 FEA audit flagged: "Registry pins verdict only, not
tolerance — a future loosening of BUCKLING_CROSS_CHECK_TOLERANCE_PCT
would not trip a regression test." Phase 29 D closes that gap by
pinning the per-case tolerance values directly against the verdict
YAMLs on disk.

Rationale: if a future maintainer loosens the tolerance constant
in a runner module to make a marginally-failing case pass, the
verdict YAML re-generation would lift the tolerance_pct field and
THIS test would trip — surfacing the loosening for review instead
of letting it slide.

Anti-gaming guard:
  E:-1 — every tier_2_validated case MUST have a tolerance_pct
         field and its value MUST match the canonical pin below.

Tier 1 / Tier 2 engineering candidate; not signed validation; not
benchmark agreement.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest


# Pinned per-case tolerance values (in PERCENT). These are the
# residual envelopes each runner was validated against at the time
# of Phase 29 D. Loosening any of these in the codebase without
# updating this pin is the canonical signal of a hedging move.
CANONICAL_TOLERANCES: dict[str, float] = {
    "cylinder-pv-candidate": 5.0,
    "cantilever-beam-candidate": 15.0,
    "plate-with-hole-candidate": 20.0,
    "euler-column-candidate": 10.0,
    "plate-simply-supported-candidate": 15.0,
    "cantilever-beam-modal-candidate": 12.0,
    "cantilever-beam-modal-l50-candidate": 12.0,
    "cantilever-buckle-candidate": 10.0,
    "plate-ss-shell-candidate": 15.0,
}


def _verdict_path(case_id: str) -> Path:
    return (
        Path(__file__).resolve().parents[2]
        / "golden_samples"
        / case_id
        / "cross_check_verdict.yaml"
    )


@pytest.mark.parametrize("case_id, expected_tolerance", CANONICAL_TOLERANCES.items())
def test_each_case_verdict_carries_canonical_tolerance(
    case_id: str, expected_tolerance: float
) -> None:
    """Per-case tolerance pin. Trips if anyone loosens a runner's
    tolerance constant without updating this test."""
    path = _verdict_path(case_id)
    assert path.is_file(), f"missing verdict YAML for {case_id} at {path}"
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert "tolerance_pct" in payload, (
        f"verdict YAML for {case_id} missing required field "
        f"`tolerance_pct`; Phase 29 D registry pin failed"
    )
    actual = payload["tolerance_pct"]
    assert actual == pytest.approx(expected_tolerance), (
        f"tolerance loosening detected for {case_id}: "
        f"expected {expected_tolerance}%, got {actual}%. "
        f"If this loosening was intentional, update "
        f"CANONICAL_TOLERANCES in this file AND add a retro entry "
        f"explaining the change."
    )


def test_validated_cohort_size_matches_tolerance_registry() -> None:
    """Pin that the registered tolerance set covers exactly the
    tier_2_validated cohort. If a new case ships with a verdict
    PASS but isn't in CANONICAL_TOLERANCES, this trips with a clear
    pointer to the missing entry."""
    from app.services.reporting._claim_tier import (
        CLAIM_TIER_REGISTRY,
        _apply_verdict_overlay,
    )

    _apply_verdict_overlay()
    validated = {
        case_id
        for case_id, tier in CLAIM_TIER_REGISTRY.items()
        if tier == "tier_2_validated"
    }
    registered = set(CANONICAL_TOLERANCES.keys())
    missing = validated - registered
    extra = registered - validated
    assert not missing, (
        f"validated cases missing from CANONICAL_TOLERANCES pin: {missing}. "
        f"Add them to Phase 29 D registry."
    )
    assert not extra, (
        f"CANONICAL_TOLERANCES has unvalidated cases: {extra}. "
        f"Did one of these regress?"
    )


def test_tolerance_pct_is_positive_and_under_100() -> None:
    """Sanity envelope: no negative tolerances (would invert PASS
    semantics) and no > 100% (which is "all residuals PASS" — a
    silent bypass)."""
    for case_id, tolerance in CANONICAL_TOLERANCES.items():
        assert 0.0 < tolerance < 100.0, (
            f"{case_id} tolerance {tolerance}% outside the honest envelope (0, 100)"
        )


def test_no_case_uses_excessive_tolerance() -> None:
    """Bound the upper limit. The widest envelope today (plate-with-
    hole) is 20%. Anything > 25% would be a Tier-1-candidate-grade
    envelope, not Tier-2-validated grade. Pin so a future widening
    requires explicit retro acknowledgment."""
    HONEST_TIER2_MAX = 25.0
    over = {
        case_id: tol
        for case_id, tol in CANONICAL_TOLERANCES.items()
        if tol > HONEST_TIER2_MAX
    }
    assert not over, (
        f"cases exceed the {HONEST_TIER2_MAX}% Tier-2 envelope: {over}. "
        f"These should be re-classified as tier_1_candidate, or the "
        f"runner/analytical needs sharpening."
    )
