"""Phase 26 A — cantilever modal cross-check runner tests.

Closes the Phase 25 retro punchlist item #3 (FEA Dim 4 solver-kind
coverage held flat at 68). Introduces the `*FREQUENCY` modal-
eigenvalue solver kind to the validated cohort.

Test cohort:
* analytical-known-input pins on
  ``compute_cantilever_first_natural_frequency_hz`` and the
  ``CANTILEVER_BETA_LX_MODES`` table
* validity-envelope refusals (L/h < 10 + mode_index out of range)
* anti-gaming guard A:-1 — rigid-body-mode filter at predicate level
* verdict-YAML overlay pin (registry lists 6 tier_2_validated cases)
* ``@pytest.mark.requires_solver`` E2E pin: real gmsh + real ccx
  end-to-end with |residual| < 12%

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
    CANTILEVER_BETA_LX_MODES,
    CANTILEVER_MODAL_CROSS_CHECK_TOLERANCE_PCT,
    CANTILEVER_SLENDER_RATIO_MIN,
    CantileverModalValidityError,
    compute_cantilever_first_natural_frequency_hz,
)
from app.services.cross_check.cantilever_modal_runner import (
    _filter_rigid_body_modes,
    _RIGID_BODY_MODE_REJECT_HZ,
    run_cantilever_modal_cross_check,
    write_cantilever_modal_verdict_yaml,
)

REPO_ROOT: Final[Path] = Path(__file__).resolve().parents[2]
GEO_PATH: Final[Path] = (
    REPO_ROOT / "golden_samples" / "cantilever-beam-modal-candidate"
    / "data" / "cantilever_modal.geo"
)


# -- analytical helpers --------------------------------------------------


def test_phase26a_beta_lx_root_values_match_rao_table() -> None:
    """β_n·L roots match Rao §8.5 Table 8.4 to 6 digits."""
    expected_rao = (1.875104, 4.694091, 7.854757, 10.995541, 14.137168)
    for i, exp in enumerate(expected_rao):
        assert CANTILEVER_BETA_LX_MODES[i] == pytest.approx(exp, abs=1e-5)


def test_phase26a_beta_lx_satisfies_characteristic_equation() -> None:
    """Each root must satisfy cosh(βL)·cos(βL) + 1 = 0 within 1e-10."""
    for beta_l in CANTILEVER_BETA_LX_MODES:
        residual = math.cosh(beta_l) * math.cos(beta_l) + 1.0
        assert abs(residual) < 1e-8, f"βL={beta_l} fails char eq: {residual}"


def test_phase26a_canonical_f1_pin() -> None:
    """Canonical 0.5m × 20mm × 20mm steel cantilever has f_1 ≈ 66.84 Hz."""
    f1 = compute_cantilever_first_natural_frequency_hz(
        length_m=0.500,
        height_m=0.020,
        width_m=0.020,
        youngs_modulus_pa=210e9,
        density_kg_m3=7850.0,
        mode_index=1,
    )
    assert f1 == pytest.approx(66.8413, abs=0.01)


def test_phase26a_f1_inversely_quadratic_in_length() -> None:
    """Doubling L should drop f_1 by 4x (Euler-Bernoulli scaling)."""
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


def test_phase26a_validity_envelope_refuses_stubby_beam() -> None:
    """L/h < 10 falls outside Euler-Bernoulli regime → refused."""
    with pytest.raises(CantileverModalValidityError) as excinfo:
        compute_cantilever_first_natural_frequency_hz(
            length_m=0.10,
            height_m=0.020,  # L/h = 5, below 10
            width_m=0.020,
            youngs_modulus_pa=210e9,
            density_kg_m3=7850.0,
            mode_index=1,
        )
    assert "Euler-Bernoulli" in str(excinfo.value)


def test_phase26a_validity_envelope_at_boundary() -> None:
    """L/h = 10 exactly should NOT refuse."""
    f1 = compute_cantilever_first_natural_frequency_hz(
        length_m=0.20,
        height_m=0.020,
        width_m=0.020,
        youngs_modulus_pa=210e9,
        density_kg_m3=7850.0,
        mode_index=1,
    )
    assert f1 > 0


def test_phase26a_mode_index_out_of_range_refused() -> None:
    with pytest.raises(ValueError, match="mode_index"):
        compute_cantilever_first_natural_frequency_hz(
            length_m=0.5,
            height_m=0.020,
            width_m=0.020,
            youngs_modulus_pa=210e9,
            density_kg_m3=7850.0,
            mode_index=6,
        )


def test_phase26a_mode_2_to_mode_1_ratio_matches_beta_squared() -> None:
    """f_2 / f_1 = (β_2 / β_1)² ≈ 6.27 (Euler-Bernoulli analytical)."""
    common = dict(
        length_m=0.500,
        height_m=0.020,
        width_m=0.020,
        youngs_modulus_pa=210e9,
        density_kg_m3=7850.0,
    )
    f1 = compute_cantilever_first_natural_frequency_hz(mode_index=1, **common)
    f2 = compute_cantilever_first_natural_frequency_hz(mode_index=2, **common)
    expected_ratio = (CANTILEVER_BETA_LX_MODES[1] / CANTILEVER_BETA_LX_MODES[0]) ** 2
    assert f2 / f1 == pytest.approx(expected_ratio, rel=1e-6)


# -- A:-1 anti-gaming guard ---------------------------------------------


def test_phase26a_filter_rigid_body_modes_drops_below_threshold() -> None:
    """A:-1 anti-gaming guard at predicate level."""
    spurious = [1e-6, 5e-7, 66.93, 416.45, 1153.11]
    filtered = _filter_rigid_body_modes(spurious)
    assert all(f >= _RIGID_BODY_MODE_REJECT_HZ for f in filtered)
    assert filtered == [66.93, 416.45, 1153.11]


def test_phase26a_filter_preserves_structural_modes() -> None:
    """Pure structural modes pass through untouched."""
    structural = [66.93, 416.45, 1153.11]
    assert _filter_rigid_body_modes(structural) == structural


def test_phase26a_filter_handles_empty_list() -> None:
    assert _filter_rigid_body_modes([]) == []


# -- registry overlay pin ----------------------------------------------


def test_phase26a_validated_count_is_six() -> None:
    """Load-bearing Phase 26 A delivery pin. After Slice A persists
    the PASS verdict YAML for cantilever-beam-modal-candidate, the
    overlay in `_claim_tier.py` promotes it to tier_2_validated.
    The registry now lists 6 tier_2_validated cases (was 5 at end
    of Phase 25). A drive-by edit that removes any verdict file
    trips this pin."""
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
    }
    assert expected.issubset(validated), (
        f"Phase 26 A guard tripped — expected tier_2_validated cases "
        f"{expected} not contained in {validated}"
    )
    assert len(validated) == 6, (
        f"validated count = {len(validated)}, expected 6; cohort={validated}"
    )


def test_phase26a_modal_verdict_yaml_persisted_on_disk() -> None:
    path = REPO_ROOT / "golden_samples" / "cantilever-beam-modal-candidate" \
        / "cross_check_verdict.yaml"
    assert path.is_file(), f"missing Phase 26 A verdict at {path}"
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["verdict"] == "PASS"
    assert payload["case_id"] == "cantilever-beam-modal-candidate"
    assert payload["cross_check_kind"] == "cantilever_modal_euler_bernoulli"
    assert payload["claim_tier"] == "tier_2_validated"
    assert abs(payload["residual_pct"]) <= CANTILEVER_MODAL_CROSS_CHECK_TOLERANCE_PCT
    # Slender envelope sanity.
    assert (
        payload["length_m"] / max(payload["height_m"], payload["width_m"])
        >= CANTILEVER_SLENDER_RATIO_MIN
    )


def test_phase26a_write_verdict_yaml_round_trip(tmp_path: Path) -> None:
    from app.services.cross_check.cantilever_modal_runner import (
        CantileverModalResult,
    )

    result = CantileverModalResult(
        verdict="PASS",
        analytical_hz=66.84,
        observed_hz=66.93,
        residual_pct=0.13,
        tolerance_pct=12.0,
        all_observed_hz=(66.93, 66.93, 416.45),
        length_m=0.500,
        height_m=0.020,
        width_m=0.020,
        node_count=1895,
        element_count=814,
        material_id="steel-s355",
        material_reference="EN 10025-2:2019",
        case_id="cantilever-beam-modal-candidate",
        generated_at_utc="2026-05-17T00:00:00+00:00",
        slender_ratio=25.0,
    )
    path = write_cantilever_modal_verdict_yaml(tmp_path, result)
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["schema_version"] == "1.0.0"
    assert payload["verdict"] == "PASS"
    assert payload["claim_tier"] == "tier_2_validated"


# -- live-solver E2E pin ----------------------------------------------


@pytest.mark.requires_solver
def test_phase26a_cantilever_modal_residual_below_12pct(tmp_path: Path) -> None:
    """End-to-end real ccx run pin: canonical 0.5m × 20mm × 20mm
    steel cantilever must produce |residual_pct| ≤ 12% vs Euler-
    Bernoulli analytical."""
    geo_local = tmp_path / "cantilever_modal.geo"
    shutil.copyfile(GEO_PATH, geo_local)
    result = run_cantilever_modal_cross_check(
        tmp_path,
        case_id="cantilever-beam-modal-candidate",
        material_id="steel-s355",
        geometry_path=geo_local,
    )
    assert result.verdict == "PASS"
    assert abs(result.residual_pct) <= CANTILEVER_MODAL_CROSS_CHECK_TOLERANCE_PCT
    assert result.slender_ratio >= CANTILEVER_SLENDER_RATIO_MIN
