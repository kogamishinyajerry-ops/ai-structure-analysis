"""FM-04a Phase 38 A — NAFEMS LE10 published-reference pins.

Phase 38 A records the PUBLISHED NAFEMS LE10 target (direct stress
sigma_yy = -5.38 MPa at point D, compressive) as the FIRST NAFEMS-tagged
entry in the FM-04a cohort. It is **analytical-only** — NO ccx solve is
performed at this phase (a real meshed solve + signed residual comparison
is deferred to the Phase 41-43 NAFEMS suite).

The artifact is `published_reference.yaml`, NOT `cross_check_verdict.yaml`
— it records a reference, not a verdict. That naming keeps it out of the
verdict cohort (the Phase 35 B solver_kind distribution pin globs
`*-candidate/cross_check_verdict.yaml`) and is honest: a published
reference with no observed value is not a cross-check.

These tests pin the reference payload AND guard against the tautological-
PASS / silent-promotion defect found in `cylinder-pv-candidate` and fixed
2026-05-24 (Codex review R0).

Anti-gaming guards exercised here:
  * T:-1 — a NAFEMS-tagged case MUST cite a public NAFEMS reference
           (publication + ISBN + signed target value) so it is reviewable
           against the published benchmark.
  * tautology guard — an analytical-only reference must NOT claim a
           verdict of "PASS" (no observed value exists to compare).
  * tier guard — the case stays tier_1_candidate; the promotion overlay
           must NOT lift it to tier_2_validated.
  * reference-not-verdict guard — the case must NOT carry a
           cross_check_verdict.yaml (which would re-enter the verdict
           cohort and break the Phase 35 B distribution pin).

Tier 1 engineering candidate; analytical reference only; not signed
validation; not benchmark agreement.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

CASE_ID = "nafems-le10-thick-plate-candidate"


def _case_dir() -> Path:
    return Path(__file__).resolve().parents[2] / "golden_samples" / CASE_ID


def _reference_path() -> Path:
    return _case_dir() / "published_reference.yaml"


@pytest.fixture(scope="module")
def payload() -> dict:
    path = _reference_path()
    assert path.is_file(), f"missing published_reference for {CASE_ID} at {path}"
    return json.loads(path.read_text(encoding="utf-8"))


def test_reference_file_exists() -> None:
    assert _reference_path().is_file()


def test_is_reference_not_verdict() -> None:
    """Reference-not-verdict guard. This case records a published
    reference, not a cross-check verdict — it must NOT carry a
    cross_check_verdict.yaml, or it would re-enter the verdict cohort
    and break the Phase 35 B solver_kind distribution pin (which globs
    `*-candidate/cross_check_verdict.yaml`)."""
    assert not (_case_dir() / "cross_check_verdict.yaml").exists(), (
        "nafems-le10 case must use published_reference.yaml, NOT "
        "cross_check_verdict.yaml — it is a reference, not a verdict, and "
        "must stay out of the Phase 35 B verdict cohort"
    )


def test_schema_and_kind(payload: dict) -> None:
    assert payload["schema_version"] == "1.0.0"
    assert payload["case_id"] == CASE_ID
    assert payload["record_kind"] == "published_benchmark_reference"
    assert payload["solver_kind"] == "linear_static"
    assert payload["cross_check_kind"] == "nafems_le10_thick_plate_pressure_point_d"


def test_analytical_only_not_tautological_pass(payload: dict) -> None:
    """The cylinder-pv-candidate guard: an analytical-only reference must
    declare itself analytical-only and must NOT claim a PASS verdict (there
    is no real observed value to compare against)."""
    assert payload["analytical_only"] is True
    assert payload["verdict"] == "REFERENCE_ONLY"
    assert payload["verdict"] != "PASS"
    assert payload["tier"] == "tier_1_candidate"


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
    assert ref["target_value_pa"] == pytest.approx(-5.38e6)
    assert abs(ref["target_value_pa"]) == pytest.approx(5.38e6)  # magnitude
    assert "sign" in ref["target_sign_convention"].lower()


def test_benchmark_context_recorded(payload: dict) -> None:
    """The material / loading / BC context is recorded for the deferred
    real solve and for reviewer scrutiny. Provenance of each field is
    annotated in the artifact (`_provenance`)."""
    ctx = payload["benchmark_context"]
    assert ctx["material"]["youngs_modulus_pa"] == pytest.approx(2.10e11)
    assert ctx["material"]["poisson_ratio"] == pytest.approx(0.30)
    assert ctx["loading"]["pressure_pa"] == pytest.approx(1.0e6)
    assert len(ctx["boundary_conditions"]) == 4
    assert "_provenance" in ctx  # honest provenance annotation present


def test_stays_tier_1_not_promoted() -> None:
    """Guard against the promotion overlay lifting an analytical-only
    reference to tier_2_validated. `_apply_verdict_overlay()` only visits
    registry members, and this case is deliberately not registered — but
    we run the overlay first to prove the case stays Tier 1 even after a
    full promotion pass."""
    from app.services.reporting._claim_tier import (
        _apply_verdict_overlay,
        get_claim_tier,
    )

    _apply_verdict_overlay()
    assert get_claim_tier(CASE_ID) == "tier_1_candidate"


def test_not_in_promotion_registry() -> None:
    """Analytical-only reference cases must NOT be added to the promotion
    registry (the cylinder-pv-candidate lesson: registry membership +
    verdict==PASS is what silently promotes a case to tier_2)."""
    from app.services.reporting._claim_tier import CLAIM_TIER_REGISTRY

    assert CASE_ID not in CLAIM_TIER_REGISTRY
