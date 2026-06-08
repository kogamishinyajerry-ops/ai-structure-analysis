"""Phase 27 A — second cantilever modal at L/h=50 tests.

Reuses Phase 26 A's runner verbatim with a 1.000 m × 20 mm × 20 mm
beam (DOUBLED length → 4× more slender than Phase 26 A's L/h = 25).
The point of the case is to exercise the SAME analytical helper at
a far more extreme aspect ratio and confirm the envelope holds.

Honest scope: NO new runner, NO new element type, NO new solver
kind. The 7th validated case lifts FEA Dim 2 (validated count
6 → 7) and FEA Dim 3 (envelope honesty across aspect ratios)
only. Shell elements deferred — documented in Phase 27 blueprint
and Phase 27 retro.

Tier 1 / Tier 2 engineering candidate; not signed validation; not
benchmark agreement.
"""

from __future__ import annotations

import json
import math
import shutil
from pathlib import Path
from typing import Final

import pytest

from app.services.cross_check.cantilever_modal import (
    CANTILEVER_MODAL_CROSS_CHECK_TOLERANCE_PCT,
    CANTILEVER_SLENDER_RATIO_MIN,
    compute_cantilever_first_natural_frequency_hz,
)
from app.services.cross_check.cantilever_modal_runner import (
    run_cantilever_modal_cross_check,
)

REPO_ROOT: Final[Path] = Path(__file__).resolve().parents[2]
GEO_PATH: Final[Path] = (
    REPO_ROOT
    / "golden_samples"
    / "cantilever-beam-modal-l50-candidate"
    / "data"
    / "cantilever_modal_l50.geo"
)
VERDICT_PATH: Final[Path] = (
    REPO_ROOT
    / "golden_samples"
    / "cantilever-beam-modal-l50-candidate"
    / "cross_check_verdict.yaml"
)


# -- analytical scaling pins -------------------------------------------


def test_phase27a_f1_at_lh50_is_quarter_of_lh25() -> None:
    """Doubling L from 0.5 m to 1.0 m must quarter f_1 (1/L² scaling)."""
    common = dict(
        height_m=0.020,
        width_m=0.020,
        youngs_modulus_pa=210e9,
        density_kg_m3=7850.0,
        mode_index=1,
    )
    f_short = compute_cantilever_first_natural_frequency_hz(
        length_m=0.500, **common
    )
    f_long = compute_cantilever_first_natural_frequency_hz(
        length_m=1.000, **common
    )
    assert f_short / f_long == pytest.approx(4.0, rel=1e-5)


def test_phase27a_canonical_f1_pin_at_lh50() -> None:
    """L=1.0m × 20mm × 20mm steel cantilever has f_1 ≈ 16.71 Hz."""
    f1 = compute_cantilever_first_natural_frequency_hz(
        length_m=1.000,
        height_m=0.020,
        width_m=0.020,
        youngs_modulus_pa=210e9,
        density_kg_m3=7850.0,
        mode_index=1,
    )
    assert f1 == pytest.approx(16.7103, abs=0.01)


def test_phase27a_lh50_stays_inside_validity_envelope() -> None:
    """L/h = 50 must NOT be refused (well inside L/h ≥ 10)."""
    f1 = compute_cantilever_first_natural_frequency_hz(
        length_m=1.000,
        height_m=0.020,
        width_m=0.020,
        youngs_modulus_pa=210e9,
        density_kg_m3=7850.0,
        mode_index=1,
    )
    assert f1 > 0
    # Slender ratio at the case geometry.
    slender = 1.000 / max(0.020, 0.020)
    assert slender == 50.0
    assert slender >= CANTILEVER_SLENDER_RATIO_MIN


# -- verdict / registry pins ------------------------------------------


def test_phase27a_validated_count_is_seven() -> None:
    """After Phase 27 A persists the L50 verdict YAML, the overlay
    in `_claim_tier.py` promotes 7 cases to tier_2_validated. The
    registry now lists 7 (was 6 at end of Phase 26 A). A drive-by
    edit that removes any of the 7 verdict files trips this pin."""
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
    expected = {
        "cylinder-pv-candidate",
        "cantilever-beam-candidate",
        "plate-with-hole-candidate",
        "euler-column-candidate",
        "plate-simply-supported-candidate",
        "cantilever-beam-modal-candidate",
        "cantilever-beam-modal-l50-candidate",
    }
    assert expected.issubset(validated), (
        f"Phase 27 A guard tripped — expected tier_2_validated cases "
        f"{expected} not contained in {validated}"
    )
    # FM-04a Phase 28 A loosened the strict-equality `len == 7`
    # check to subset-of, preserving Phase 27 A's intent (7 cases
    # REQUIRED present) while admitting Phase 28 A's 8th case
    # (cantilever-buckle-candidate). Same additive-promotion pattern.
    assert len(validated) >= 7, (
        f"validated count = {len(validated)}, expected ≥ 7; cohort={validated}"
    )


def test_phase27a_l50_verdict_yaml_persisted_on_disk() -> None:
    assert VERDICT_PATH.is_file(), f"missing Phase 27 A verdict at {VERDICT_PATH}"
    payload = json.loads(VERDICT_PATH.read_text(encoding="utf-8"))
    assert payload["verdict"] == "PASS"
    assert payload["case_id"] == "cantilever-beam-modal-l50-candidate"
    assert payload["cross_check_kind"] == "cantilever_modal_euler_bernoulli"
    assert payload["claim_tier"] == "tier_2_validated"
    assert abs(payload["residual_pct"]) <= CANTILEVER_MODAL_CROSS_CHECK_TOLERANCE_PCT
    # Envelope-stress-test pin: this case carries L/h = 50, NOT 25.
    assert payload["slender_ratio"] == pytest.approx(50.0, abs=1e-6)
    assert payload["length_m"] == pytest.approx(1.000, abs=1e-9)


def test_phase27a_residual_matches_phase26a_to_within_one_pct() -> None:
    """Envelope-stress-test pin: at L/h = 50 (4× more slender than
    Phase 26 A's L/h = 25) the residual should be within 1% of
    Phase 26 A's +0.13%. If the residual blows up to e.g. 5% here,
    we'd be exiting the Euler-Bernoulli envelope earlier than
    advertised — and the test would catch it."""
    payload = json.loads(VERDICT_PATH.read_text(encoding="utf-8"))
    # Phase 26 A's residual was +0.1325%. Phase 27 A's L/h=50 run
    # produces +0.136%. Both well inside 1% of each other.
    assert abs(payload["residual_pct"]) < 1.0, (
        f"L/h=50 residual {payload['residual_pct']:.3f}% exceeds 1% "
        f"— Euler-Bernoulli envelope is degrading at the slenderness "
        f"extreme; either the analytical needs a shear correction "
        f"(Timoshenko) or the mesh needs refinement"
    )


def test_phase27a_doublet_structure_preserved_at_extreme_slenderness() -> None:
    """Square cross-section yields a degenerate doublet at modes
    1+2. Phase 26 A pinned this at L/h = 25; Phase 27 A pins it at
    L/h = 50 (the doublet structure is a geometric invariant; aspect
    ratio shouldn't change it)."""
    payload = json.loads(VERDICT_PATH.read_text(encoding="utf-8"))
    modes = payload["all_observed_hz"]
    assert len(modes) >= 4
    # mode-1 vs mode-2 doublet: same to <1% (both bending mode 1
    # but about y vs z axis).
    assert abs(modes[0] - modes[1]) / modes[0] < 0.01
    # mode-3 vs mode-4 doublet: same to <1% (both bending mode 2).
    assert abs(modes[2] - modes[3]) / modes[2] < 0.01


# -- live-solver E2E pin ----------------------------------------------


@pytest.mark.requires_solver
def test_phase27a_l50_cantilever_modal_residual_below_12pct(
    tmp_path: Path,
) -> None:
    """End-to-end real ccx run pin at L/h=50: must produce
    |residual_pct| ≤ 12% vs Euler-Bernoulli analytical."""
    geo_local = tmp_path / "cantilever_modal_l50.geo"
    shutil.copyfile(GEO_PATH, geo_local)
    result = run_cantilever_modal_cross_check(
        tmp_path,
        case_id="cantilever-beam-modal-l50-candidate",
        material_id="steel-s355",
        geometry_path=geo_local,
        length_m=1.000,
        height_m=0.020,
        width_m=0.020,
        characteristic_length_m=0.020,
        element_order=2,
        num_modes=5,
    )
    assert result.verdict == "PASS"
    assert abs(result.residual_pct) <= CANTILEVER_MODAL_CROSS_CHECK_TOLERANCE_PCT
    # Geometric pin: this geometry has slender_ratio 50.0.
    assert result.slender_ratio == pytest.approx(50.0, abs=1e-6)
