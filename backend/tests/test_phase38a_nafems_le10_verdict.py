"""FM-04a Phase 38 A (UPDATED V2-1 / ADR-027) — NAFEMS LE10 reference-record
discipline + reference/verdict separation.

Phase 38 A originally recorded the PUBLISHED NAFEMS LE10 target (direct stress
sigma_yy = -5.38 MPa at point D, compressive) as an **analytical-only** entry,
with the real meshed solve deferred. **That deferral is now closed:** V2-1 /
ADR-027 (2026-06-03) landed the real ccx 2.23 solve (observed -5.4379 MPa,
+1.08% vs the -5.38 MPa target), promoting the case to ``tier_2_validated`` —
the project's first PUBLIC-BENCHMARK agreement.

These tests therefore pin the NEW invariant (Codex R1 P2):

  * the REFERENCE record (``published_reference.yaml``) is still a *citation*,
    not a verdict — it stays ``verdict: REFERENCE_ONLY`` and never carries a
    PASS (the cylinder-pv tautology guard, preserved);
  * a SIBLING ``cross_check_verdict.yaml`` now exists and is ``PASS``;
  * NO tautological observed == target shortcut — the verdict's observed value
    genuinely differs from the published target by the recorded residual;
  * tier promotion comes ONLY from the real-solve verdict overlay (the case is
    now registered AND resolves to ``tier_2_validated``), NOT from the
    reference record.

The forward-going benchmark-agreement regression FLOOR (residual tolerance,
sign/point correctness, monotone convergence, requires_solver reproduction)
lives in ``test_nafems_le10_benchmark.py``; this file owns the
reference-record honesty + the reference/verdict file separation.

Tier 2 real-solver validated; public-benchmark agreement; NOT signed validation.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

CASE_ID = "nafems-le10-thick-plate-candidate"
PUBLISHED_TARGET_PA = -5.38e6  # NAFEMS LE10 sigma_yy(D), TNSB Rev.3 (compressive)


def _case_dir() -> Path:
    return Path(__file__).resolve().parents[2] / "golden_samples" / CASE_ID


def _reference_path() -> Path:
    return _case_dir() / "published_reference.yaml"


def _verdict_path() -> Path:
    return _case_dir() / "cross_check_verdict.yaml"


@pytest.fixture(scope="module")
def payload() -> dict:
    path = _reference_path()
    assert path.is_file(), f"missing published_reference for {CASE_ID} at {path}"
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def verdict() -> dict:
    path = _verdict_path()
    assert path.is_file(), f"missing cross_check_verdict for {CASE_ID} at {path}"
    return json.loads(path.read_text(encoding="utf-8"))


def test_reference_file_exists() -> None:
    assert _reference_path().is_file()


def test_reference_and_verdict_are_distinct_records(verdict: dict) -> None:
    """Reference/verdict SEPARATION (was: reference-not-verdict).

    Post-V2-1 the case carries BOTH files, each with a distinct role: the
    published_reference.yaml is the citation of the published value; the
    cross_check_verdict.yaml is the real-solve verdict. The sibling verdict
    must exist and be PASS — the deferral Phase 38 A originally pinned is now
    closed.
    """
    assert _verdict_path().is_file(), (
        "V2-1 landed the real LE10 solve; the sibling cross_check_verdict.yaml "
        "must now exist (the Phase 38 A deferral is closed)"
    )
    assert verdict["verdict"] == "PASS"
    assert verdict["reference_kind"] == "published_benchmark"


def test_reference_record_stays_reference_only_not_tautological(payload: dict) -> None:
    """The cylinder-pv guard, preserved: the REFERENCE record is a citation,
    not a verdict — it must declare ``REFERENCE_ONLY`` and must NEVER claim a
    PASS. The real PASS lives in the sibling verdict, not here."""
    assert payload["verdict"] == "REFERENCE_ONLY"
    assert payload["verdict"] != "PASS"
    assert payload["record_kind"] == "published_benchmark_reference"
    # the case is no longer analytical-only (a real solve exists now)
    assert payload["analytical_only"] is False


def test_no_tautological_observed_equals_target(verdict: dict) -> None:
    """Anti-gaming: the verdict's observed value must genuinely DIFFER from the
    published target (a tautological observed == target would fake agreement).
    Both share the compressive sign; agreement is the small residual, not
    identity."""
    observed = verdict["observed_pa"]
    target = verdict["analytical_pa"]
    assert observed != target, "observed must not be a tautological copy of target"
    assert target == pytest.approx(PUBLISHED_TARGET_PA)
    assert observed < 0 and target < 0, "both compressive (same sign)"
    # the recorded residual matches the actual gap (within rounding)
    expected_resid = abs(observed - target) / abs(target) * 100.0
    assert verdict["residual_pct"] == pytest.approx(expected_resid, abs=0.05)


def test_schema_and_kind(payload: dict) -> None:
    assert payload["schema_version"] == "1.0.0"
    assert payload["case_id"] == CASE_ID
    assert payload["record_kind"] == "published_benchmark_reference"
    assert payload["solver_kind"] == "linear_static"
    assert payload["cross_check_kind"] == "nafems_le10_thick_plate_pressure_point_d"


def test_nafems_public_reference_cited(payload: dict) -> None:
    """T:-1 guard — the published benchmark must be reviewable: a real
    NAFEMS publication, its ISBN, the stress component, and the SIGNED
    target value all have to be present and correct."""
    ref = payload["published_reference"]
    assert "NAFEMS LE10" in ref["benchmark"]
    assert "1990" in ref["source"]
    assert "1-874376-04-0" in ref["source"]  # NAFEMS TNSB Rev.3 ISBN
    assert ref["target_stress_component"].startswith("sigma_yy")
    # Signed value preserved (Codex R0 finding 2): compressive -5.38 MPa,
    # NOT the magnitude. A future signed residual check compares correctly.
    assert ref["target_value_pa"] == pytest.approx(PUBLISHED_TARGET_PA)
    assert abs(ref["target_value_pa"]) == pytest.approx(5.38e6)  # magnitude
    assert "sign" in ref["target_sign_convention"].lower()


def test_benchmark_context_recorded(payload: dict) -> None:
    """The material / loading / BC context is recorded for the real solve and
    for reviewer scrutiny. Provenance of each field is annotated."""
    ctx = payload["benchmark_context"]
    assert ctx["material"]["youngs_modulus_pa"] == pytest.approx(2.10e11)
    assert ctx["material"]["poisson_ratio"] == pytest.approx(0.30)
    assert ctx["loading"]["pressure_pa"] == pytest.approx(1.0e6)
    assert len(ctx["boundary_conditions"]) == 4
    assert "_provenance" in ctx  # honest provenance annotation present


def test_point_d_is_upper_major_axis(verdict: dict) -> None:
    """Guards the two errors the 2026-06-03 spec triangulation caught in the
    prior records: point D is the UPPER surface (not lower) and the
    inner-ellipse MAJOR-axis tip (2.0, 0, +0.3) on the y=0 plane (not the
    minor axis). Pinned on the verdict, which carries the corrected location."""
    assert verdict["point_d_m"] == [2.0, 0.0, 0.3]
    assert verdict["point_d_surface"] == "upper"


def test_promotion_driven_by_real_solve_verdict() -> None:
    """The case is now PROMOTED to tier_2_validated — but only because the real
    solve verdict (sibling cross_check_verdict.yaml, verdict=PASS) drives the
    overlay. This flips the original Phase 38 A 'stays Tier 1 / not registered'
    pins, which were correct only while the solve was deferred.

    The reference record itself still does NOT drive promotion (its tier field
    stays tier_1_candidate); promotion is the overlay reading the verdict.
    """
    from app.services.reporting._claim_tier import (
        _apply_verdict_overlay,
        CLAIM_TIER_REGISTRY,
        get_claim_tier,
    )

    _apply_verdict_overlay()
    # the case is admitted to the registry (real-solver cohort)...
    assert CASE_ID in CLAIM_TIER_REGISTRY
    # ...and the verdict overlay promotes it to tier_2_validated.
    assert get_claim_tier(CASE_ID) == "tier_2_validated"


def test_claim_boundary_is_public_benchmark_not_analytical() -> None:
    """LE10's tier_2 substantiation is a PUBLIC-BENCHMARK agreement, not an
    analytical cross-check (Codex R1 P1). The claim boundary must say so."""
    from app.services.reporting._claim_tier import claim_boundary_for

    boundary = claim_boundary_for(CASE_ID)
    assert "public_benchmark_agreement_nafems_le10" in boundary
    assert "not_signed_validation" in boundary
    assert "cross_check_against_analytical" not in boundary
