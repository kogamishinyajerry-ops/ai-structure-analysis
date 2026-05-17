"""Phase 25 A — simply-supported plate cross-check runner tests.

Closes the Phase 24 retro punchlist item #3 (FEA Dim 2 held flat at
71). Promotes `plate-simply-supported-candidate` to tier_2_validated,
flipping the validated count 4 → 5.

Test cohort:
* analytical-known-input pins on
  ``compute_simply_supported_plate_center_deflection_m`` and
  ``plate_flexural_rigidity_d_n_m``
* validity-envelope refusals (a/t < 20)
* verdict-YAML overlay pin (registry lists 5 tier_2_validated cases)
* anti-gaming guard A:-1 — center-node-selection sanity
* ``@pytest.mark.requires_solver`` E2E pin: real gmsh + real ccx
  end-to-end with |residual| < 15%

Tier 1 / Tier 2 engineering candidate; not signed validation; not
benchmark agreement.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Final

import pytest

from app.services.cross_check.plate_simply_supported import (
    PLATE_SS_CROSS_CHECK_TOLERANCE_PCT,
    PLATE_SS_SMALL_DEFLECTION_RATIO_MAX,
    PLATE_SS_THIN_PLATE_RATIO_MIN,
    PlateSimplySupportedValidityError,
    TIMOSHENKO_ALPHA_SQUARE_NU_0_3,
    compute_simply_supported_plate_center_deflection_m,
    plate_flexural_rigidity_d_n_m,
)
from app.services.cross_check.plate_ss_runner import (
    _find_center_node,
    _select_bottom_edge_nodes,
    _select_top_face_nodes,
    run_plate_ss_cross_check,
    write_plate_ss_verdict_yaml,
)

REPO_ROOT: Final[Path] = Path(__file__).resolve().parents[2]
PLATE_GEO: Final[Path] = (
    REPO_ROOT / "golden_samples" / "plate-simply-supported-candidate"
    / "data" / "plate_ss.geo"
)


# -- analytical-helpers ----------------------------------------------------


def test_phase25a_timoshenko_alpha_value() -> None:
    """α = 0.00406 is the Timoshenko & Woinowsky-Krieger §30 Table 8
    value for square plate, ν=0.3, simply-supported, uniform load."""
    assert TIMOSHENKO_ALPHA_SQUARE_NU_0_3 == pytest.approx(0.00406, abs=1e-5)


def test_phase25a_flexural_rigidity_steel_default() -> None:
    """D = E·t³ / (12(1-ν²)) for E=210 GPa, t=0.02 m, ν=0.3 → 153,846 N·m."""
    d = plate_flexural_rigidity_d_n_m(
        youngs_modulus_pa=210e9,
        thickness_m=0.020,
        poisson_ratio=0.3,
    )
    assert d == pytest.approx(153846.15, rel=1e-3)


def test_phase25a_compute_center_deflection_canonical_pin() -> None:
    """Canonical pin for the live-run benchmark geometry:
    1m × 1m × 20mm steel plate at 10 kPa uniform pressure →
    w_center analytical = -0.264 mm."""
    w = compute_simply_supported_plate_center_deflection_m(
        side_length_m=1.0,
        thickness_m=0.020,
        youngs_modulus_pa=210e9,
        poisson_ratio=0.3,
        pressure_pa=-1.0e4,
    )
    # α=0.00406, q=-1e4, a=1, D=1.538e5 → w = 0.00406·(-1e4)/(1.538e5)
    expected = 0.00406 * (-1.0e4) * 1.0**4 / 153846.15
    assert w == pytest.approx(expected, rel=1e-3)
    assert abs(w) == pytest.approx(2.639e-4, rel=1e-3)


def test_phase25a_validity_envelope_refuses_thick_plate() -> None:
    """a/t < 20 falls outside Kirchhoff thin-plate regime → refused."""
    with pytest.raises(PlateSimplySupportedValidityError) as excinfo:
        compute_simply_supported_plate_center_deflection_m(
            side_length_m=0.5,
            thickness_m=0.040,  # a/t = 12.5 < 20
            youngs_modulus_pa=210e9,
            poisson_ratio=0.3,
            pressure_pa=1.0e4,
        )
    assert "Kirchhoff" in str(excinfo.value)


def test_phase25a_validity_envelope_at_boundary() -> None:
    """a/t = 20 exactly is the lower bound; should NOT refuse."""
    w = compute_simply_supported_plate_center_deflection_m(
        side_length_m=1.0,
        thickness_m=0.050,  # a/t = 20
        youngs_modulus_pa=210e9,
        poisson_ratio=0.3,
        pressure_pa=1.0e4,
    )
    assert w > 0  # pressure positive → deflection positive in formula


def test_phase25a_compute_rejects_negative_dimensions() -> None:
    with pytest.raises(ValueError, match="side_length_m"):
        compute_simply_supported_plate_center_deflection_m(
            side_length_m=-1.0,
            thickness_m=0.020,
            youngs_modulus_pa=210e9,
            poisson_ratio=0.3,
            pressure_pa=1.0e4,
        )


def test_phase25a_compute_rejects_invalid_poisson() -> None:
    with pytest.raises(ValueError, match="poisson_ratio"):
        compute_simply_supported_plate_center_deflection_m(
            side_length_m=1.0,
            thickness_m=0.020,
            youngs_modulus_pa=210e9,
            poisson_ratio=0.6,
            pressure_pa=1.0e4,
        )


# -- node-selection helpers (used by A:-1 anti-gaming guard) --------------


def _stub_nodes_grid() -> dict[int, tuple[float, float, float]]:
    """5x5x2 corner-grid nodes for a 1m × 1m × 0.02m plate."""
    nodes: dict[int, tuple[float, float, float]] = {}
    nid = 1
    for k, z in enumerate([0.0, 0.020]):
        for j in range(5):
            for i in range(5):
                x = i * 0.25
                y = j * 0.25
                nodes[nid] = (x, y, z)
                nid += 1
    return nodes


def test_phase25a_select_bottom_edge_nodes_excludes_interior() -> None:
    nodes = _stub_nodes_grid()
    edges = _select_bottom_edge_nodes(nodes, side_length_m=1.0, tol_m=1e-4)
    # Bottom face (z=0) has 25 nodes; 16 are on the perimeter (5+5+5+5 − 4 corners
    # double-counted = 16). All 4 corner nodes + non-corner edge nodes.
    assert len(edges) == 16
    # All selected nodes must lie on z=0 plane.
    for nid in edges:
        assert abs(nodes[nid][2]) < 1e-4


def test_phase25a_select_top_face_nodes_only_top() -> None:
    nodes = _stub_nodes_grid()
    top = _select_top_face_nodes(nodes, thickness_m=0.020, tol_m=1e-4)
    assert len(top) == 25  # full 5×5 grid
    for nid in top:
        assert abs(nodes[nid][2] - 0.020) < 1e-4


def test_phase25a_center_node_is_central_a1_anti_gaming_guard() -> None:
    """A:-1 anti-gaming guard at the predicate level: the center-node
    selection must land at the geometric center, NOT a corner / edge."""
    nodes = _stub_nodes_grid()
    cn = _find_center_node(nodes, side_length_m=1.0, thickness_m=0.020)
    cx, cy, cz = nodes[cn]
    # Plate-center 3D is (0.5, 0.5, 0.010); nearest grid node lies at
    # (0.5, 0.5, 0.0) or (0.5, 0.5, 0.020) — both 0.010 m from target.
    assert cx == pytest.approx(0.5)
    assert cy == pytest.approx(0.5)
    assert cz in (0.0, 0.020)


# -- registry + verdict-overlay pins --------------------------------------


def test_phase25a_validated_count_is_five() -> None:
    """Load-bearing Phase 25 A delivery pin. After Slice A persists
    the PASS verdict YAML for plate-simply-supported-candidate under
    golden_samples/, the overlay in `_claim_tier.py` promotes it to
    tier_2_validated. Combined with the 4 prior promotions (Phase 19
    B / 21 A / 23 A), the registry now lists exactly 5 tier_2_validated
    cases. A drive-by edit that removes any verdict file trips this pin.
    """
    from app.services.reporting._claim_tier import (
        CLAIM_TIER_REGISTRY,
        _apply_verdict_overlay,
    )

    # Force re-read from disk (Phase 18-24 modules may have been
    # imported earlier in the test process).
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
    }
    assert expected.issubset(validated), (
        f"Phase 25 A guard tripped — expected tier_2_validated cases "
        f"{expected} not contained in {validated}"
    )
    # Strict-count pin: nothing has snuck into validated cohort beyond
    # the planned 5 cases.
    assert len(validated) == 5, (
        f"validated count = {len(validated)}, expected 5; cohort={validated}"
    )


def test_phase25a_plate_ss_verdict_yaml_persisted_on_disk() -> None:
    """The persisted PASS verdict must be readable from golden_samples
    and carry verdict='PASS' + the plate_ss_runner provenance."""
    path = REPO_ROOT / "golden_samples" / "plate-simply-supported-candidate" \
        / "cross_check_verdict.yaml"
    assert path.is_file(), f"missing Phase 25 A verdict at {path}"
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["verdict"] == "PASS"
    assert payload["case_id"] == "plate-simply-supported-candidate"
    assert payload["cross_check_kind"] == "plate_simply_supported_timoshenko"
    assert payload["claim_tier"] == "tier_2_validated"
    assert abs(payload["residual_pct"]) <= PLATE_SS_CROSS_CHECK_TOLERANCE_PCT
    assert payload["small_deflection_ratio"] <= PLATE_SS_SMALL_DEFLECTION_RATIO_MAX
    # a/t envelope check carried in the verdict's recorded geometry.
    aspect = payload["side_length_m"] / payload["thickness_m"]
    assert aspect >= PLATE_SS_THIN_PLATE_RATIO_MIN


def test_phase25a_write_verdict_yaml_round_trip(tmp_path: Path) -> None:
    """``write_plate_ss_verdict_yaml`` writes a parseable schema-versioned
    YAML."""
    from app.services.cross_check.plate_ss_runner import PlateSSCrossCheckResult

    result = PlateSSCrossCheckResult(
        verdict="PASS",
        analytical_w_center_m=-2.64e-4,
        observed_w_center_m=-2.48e-4,
        residual_pct=-6.0,
        tolerance_pct=15.0,
        flexural_rigidity_d=1.538e5,
        side_length_m=1.0,
        thickness_m=0.020,
        pressure_pa=1.0e4,
        applied_force_n=1.0e4,
        node_count=4420,
        element_count=2125,
        material_id="steel-s355",
        material_reference="EN 10025-2:2019",
        case_id="plate-simply-supported-candidate",
        generated_at_utc="2026-05-17T00:00:00+00:00",
        small_deflection_ratio=0.0124,
    )
    path = write_plate_ss_verdict_yaml(tmp_path, result)
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["schema_version"] == "1.0.0"
    assert payload["verdict"] == "PASS"
    assert payload["claim_tier"] == "tier_2_validated"


# -- live-solver E2E pin --------------------------------------------------


@pytest.mark.requires_solver
def test_phase25a_plate_ss_runner_residual_below_15pct(tmp_path: Path) -> None:
    """End-to-end real ccx run pin: 1m × 1m × 20mm steel plate at 10 kPa
    must produce |residual_pct| ≤ 15% vs Timoshenko α=0.00406 analytical."""
    geo_local = tmp_path / "plate_ss.geo"
    shutil.copyfile(PLATE_GEO, geo_local)
    result = run_plate_ss_cross_check(
        tmp_path,
        case_id="plate-simply-supported-candidate",
        material_id="steel-s355",
        geometry_path=geo_local,
    )
    assert result.verdict == "PASS"
    assert abs(result.residual_pct) <= PLATE_SS_CROSS_CHECK_TOLERANCE_PCT
    assert result.small_deflection_ratio <= PLATE_SS_SMALL_DEFLECTION_RATIO_MAX
