"""FM-04a Phase 21 A — cantilever + Kirsch meshed cross-check runners.

Tier 1 / Tier 2 engineering candidate; not signed validation; not
benchmark agreement.

Both runners compose the Phase 20 C `run_tier2_meshed_pipeline` with a
discipline-appropriate analytical:
* cantilever_runner → Euler-Bernoulli PL³/(3EI) (Phase 20 B analytical)
* plate_kirsch_runner → Howland's strip-with-hole K(2a/W) (new in Slice A)

Both write a `cross_check_verdict.yaml` so the `_claim_tier.py` overlay
promotes the corresponding candidate (`cantilever-beam-candidate` /
`plate-with-hole-candidate`) to `tier_2_validated` on next module load.

Anti-gaming guards:
* (A:-3) verdict YAML schema is the SAME SSOT used by Phase 19 B's
  cylinder-pv runner (no parallel schema).
* (T:-3) if either runner's residual is OUTSIDE its honestly-documented
  tolerance, the verdict is FAIL (not silently widened to PASS).
* (T:-3 requires_solver) two E2E pins exercise real gmsh + real ccx:
  - cantilever 1-m / 100-mm beam → tip deflection within 15%.
  - plate-with-hole tensile coupon → σ_max within 20% of K·σ_∞.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.services.cross_check import (
    CANTILEVER_CROSS_CHECK_TOLERANCE_PCT,
    CantileverCrossCheckResult,
    KIRSCH_INFINITE_K,
    KirschValidityError,
    PLATE_FINITE_RATIO_MAX,
    PLATE_KIRSCH_CROSS_CHECK_TOLERANCE_PCT,
    PlateKirschCrossCheckResult,
    VERDICT_YAML_FILENAME,
    compute_analytical_tip_deflection,
    compute_kirsch_peak_stress_pa,
    kirsch_stress_concentration_factor,
    write_cantilever_verdict_yaml,
    write_plate_kirsch_verdict_yaml,
)


# ---------------------------------------------------------------------
# Kirsch / Howland K — pure formula pins
# ---------------------------------------------------------------------


def test_kirsch_k_returns_3_for_infinite_plate_limit() -> None:
    """The 2a/W → 0 limit must collapse to the classical Kirsch K=3.0."""
    k = kirsch_stress_concentration_factor(
        hole_radius_m=1e-6, plate_full_width_m=1.0
    )
    # Linear interpolation between (0.0, 3.000) and (0.10, 3.034) at a
    # tiny ratio gives 3.000 + epsilon; assert within 1e-3 of K=3.
    assert abs(k - KIRSCH_INFINITE_K) < 1e-3


@pytest.mark.parametrize(
    "ratio,k_expected",
    [
        (0.10, 3.034),
        (0.20, 3.140),
        (0.30, 3.360),
        (0.40, 3.740),
        (0.50, 4.320),
    ],
)
def test_kirsch_k_matches_howland_tabulated_values(
    ratio: float, k_expected: float
) -> None:
    """K(2a/W) at the tabulated knots must equal the Pilkey/Peterson
    tabulated values to within 1e-9 (the table entries are exact)."""
    # Use plate_full_width_m=1.0 so hole_radius_m = ratio / 2.
    k = kirsch_stress_concentration_factor(
        hole_radius_m=ratio / 2.0, plate_full_width_m=1.0
    )
    assert k == pytest.approx(k_expected, abs=1e-9)


def test_kirsch_k_interpolates_between_knots() -> None:
    """At 2a/W = 0.15 (midpoint of 0.10 / 0.20 knots), linear interp
    must return (3.034 + 3.140) / 2 = 3.087."""
    k = kirsch_stress_concentration_factor(
        hole_radius_m=0.075, plate_full_width_m=1.0
    )
    assert k == pytest.approx(3.087, abs=1e-3)


def test_kirsch_k_refuses_large_hole_ratio() -> None:
    """2a/W > 0.5 falls outside the Howland tabulation; runner refuses
    rather than extrapolating into a regime with rapidly-growing K."""
    with pytest.raises(KirschValidityError):
        kirsch_stress_concentration_factor(
            hole_radius_m=0.3, plate_full_width_m=1.0  # 2a/W = 0.6
        )


def test_kirsch_k_refuses_non_positive_inputs() -> None:
    with pytest.raises(ValueError):
        kirsch_stress_concentration_factor(
            hole_radius_m=0.0, plate_full_width_m=1.0
        )
    with pytest.raises(ValueError):
        kirsch_stress_concentration_factor(
            hole_radius_m=0.01, plate_full_width_m=-1.0
        )


def test_kirsch_peak_stress_composes_k_and_far_field() -> None:
    """σ_max = K · σ_∞. At 2a/W = 0.4, K = 3.740. With σ_∞ = 100 MPa,
    σ_max = 374 MPa."""
    sigma_max = compute_kirsch_peak_stress_pa(
        far_field_pa=100e6,
        hole_radius_m=0.010,
        plate_full_width_m=0.050,
    )
    assert sigma_max == pytest.approx(374e6, abs=1e3)


def test_kirsch_peak_stress_preserves_sign() -> None:
    """Compressive (negative) far-field should yield negative σ_max."""
    sigma_max = compute_kirsch_peak_stress_pa(
        far_field_pa=-50e6,
        hole_radius_m=0.010,
        plate_full_width_m=0.050,
    )
    assert sigma_max < 0
    assert sigma_max == pytest.approx(-3.740 * 50e6, rel=1e-9)


def test_kirsch_peak_stress_refuses_zero_far_field() -> None:
    with pytest.raises(ValueError):
        compute_kirsch_peak_stress_pa(
            far_field_pa=0.0,
            hole_radius_m=0.010,
            plate_full_width_m=0.050,
        )


# ---------------------------------------------------------------------
# Tolerance envelope is documented and conservative
# ---------------------------------------------------------------------


def test_cantilever_tolerance_is_15_percent() -> None:
    """Phase 21 A locks the cantilever tolerance at 15%; tighter
    tolerances need C3D10 or C3D8I elements (Phase 22+)."""
    assert CANTILEVER_CROSS_CHECK_TOLERANCE_PCT == 15.0


def test_kirsch_tolerance_is_20_percent() -> None:
    """Phase 21 A locks the Kirsch tolerance at 20%; tighter needs
    adaptive mesh refinement at the hole edge."""
    assert PLATE_KIRSCH_CROSS_CHECK_TOLERANCE_PCT == 20.0


def test_plate_finite_ratio_max_is_half() -> None:
    """Above 2a/W = 0.5 the Howland tabulation runs out; refusing on
    larger ratios is the honest move."""
    assert PLATE_FINITE_RATIO_MAX == 0.5


# ---------------------------------------------------------------------
# Geometry artifacts are on disk + Phase 21 A registers cantilever
# ---------------------------------------------------------------------


def test_cantilever_geo_file_exists() -> None:
    here = Path(__file__).resolve()
    repo_root = here.parents[2]
    geo = (
        repo_root
        / "golden_samples"
        / "cantilever-beam-candidate"
        / "data"
        / "cantilever.geo"
    )
    assert geo.is_file(), f"missing {geo}"
    body = geo.read_text(encoding="utf-8")
    assert "L = 1.000" in body
    assert "h = 0.100" in body
    assert "b = 0.100" in body
    assert 'Physical Volume("cantilever")' in body


# ---------------------------------------------------------------------
# Verdict YAML schema parity with Phase 19 B (no parallel schema)
# ---------------------------------------------------------------------


def test_cantilever_verdict_yaml_carries_pass_schema(tmp_path: Path) -> None:
    """Writing a synthetic PASS result must produce a JSON-parseable
    artifact with schema_version, verdict, and claim_tier =
    tier_2_validated — the same shape as the Phase 19 B cylinder-pv
    verdict."""
    case_golden = tmp_path / "cantilever-beam-candidate"
    case_golden.mkdir()
    result = CantileverCrossCheckResult(
        verdict="PASS",
        analytical_m=-1.9048e-4,
        observed_m=-1.85e-4,
        residual_pct=-2.87,
        tolerance_pct=CANTILEVER_CROSS_CHECK_TOLERANCE_PCT,
        material_id="steel-s355",
        material_reference="EN 10025-2:2019 §7.3",
        length_m=1.0,
        section_depth_m=0.1,
        section_width_m=0.1,
        tip_load_n=-1000.0,
        second_moment_m4=8.3333e-6,
        node_count=540,
        element_count=2100,
        case_id="cantilever-beam-candidate",
        generated_at_utc="2026-05-17T10:00:00+00:00",
    )
    path = write_cantilever_verdict_yaml(case_golden, result)
    assert path.name == VERDICT_YAML_FILENAME
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["schema_version"] == "1.0.0"
    assert payload["verdict"] == "PASS"
    assert payload["claim_tier"] == "tier_2_validated"
    assert (
        payload["cross_check_kind"]
        == "cantilever_tip_deflection_euler_bernoulli"
    )
    assert "tier2_real_solver_validated" in payload["claim_boundary"]


def test_cantilever_verdict_yaml_fail_keeps_tier_1(tmp_path: Path) -> None:
    """A FAIL verdict must not promote: claim_tier stays tier_1, the
    boundary copy is the Tier 1 envelope, and the residual is preserved
    verbatim (anti-gaming: we don't silently flip FAIL to PASS)."""
    case_golden = tmp_path / "cantilever-beam-candidate"
    case_golden.mkdir()
    result = CantileverCrossCheckResult(
        verdict="FAIL",
        analytical_m=-1.9e-4,
        observed_m=-3.0e-4,  # 58% over — way out of tolerance
        residual_pct=57.9,
        tolerance_pct=CANTILEVER_CROSS_CHECK_TOLERANCE_PCT,
        material_id="steel-s355",
        material_reference="EN 10025-2:2019 §7.3",
        length_m=1.0,
        section_depth_m=0.1,
        section_width_m=0.1,
        tip_load_n=-1000.0,
        second_moment_m4=8.3333e-6,
        node_count=540,
        element_count=2100,
        case_id="cantilever-beam-candidate",
        generated_at_utc="2026-05-17T10:00:00+00:00",
    )
    path = write_cantilever_verdict_yaml(case_golden, result)
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["verdict"] == "FAIL"
    assert payload["claim_tier"] == "tier_1_candidate"
    assert "not_signed_validation" in payload["claim_boundary"]
    assert "not_benchmark_agreement" in payload["claim_boundary"]
    assert payload["residual_pct"] == 57.9


def test_plate_kirsch_verdict_yaml_carries_pass_schema(tmp_path: Path) -> None:
    case_golden = tmp_path / "plate-with-hole-candidate"
    case_golden.mkdir()
    result = PlateKirschCrossCheckResult(
        verdict="PASS",
        analytical_pa=3.74e6,
        observed_pa=3.30e6,
        residual_pct=-11.76,
        tolerance_pct=PLATE_KIRSCH_CROSS_CHECK_TOLERANCE_PCT,
        kirsch_k=3.740,
        far_field_pa=1.0e6,
        plate_length_m=0.100,
        plate_width_m=0.050,
        plate_thickness_m=0.005,
        hole_radius_m=0.010,
        applied_force_n=250.0,
        node_count=850,
        element_count=3500,
        material_id="steel-s355",
        material_reference="EN 10025-2:2019 §7.3",
        case_id="plate-with-hole-candidate",
        generated_at_utc="2026-05-17T10:00:00+00:00",
    )
    path = write_plate_kirsch_verdict_yaml(case_golden, result)
    assert path.name == VERDICT_YAML_FILENAME
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["verdict"] == "PASS"
    assert payload["claim_tier"] == "tier_2_validated"
    assert payload["cross_check_kind"] == "plate_with_hole_kirsch_howland"
    assert payload["kirsch_k"] == 3.740


def test_plate_kirsch_verdict_yaml_fail_keeps_tier_1(tmp_path: Path) -> None:
    case_golden = tmp_path / "plate-with-hole-candidate"
    case_golden.mkdir()
    result = PlateKirschCrossCheckResult(
        verdict="FAIL",
        analytical_pa=3.74e6,
        observed_pa=5.5e6,  # 47% over — way out of tolerance
        residual_pct=47.06,
        tolerance_pct=PLATE_KIRSCH_CROSS_CHECK_TOLERANCE_PCT,
        kirsch_k=3.740,
        far_field_pa=1.0e6,
        plate_length_m=0.100,
        plate_width_m=0.050,
        plate_thickness_m=0.005,
        hole_radius_m=0.010,
        applied_force_n=250.0,
        node_count=850,
        element_count=3500,
        material_id="steel-s355",
        material_reference="EN 10025-2:2019 §7.3",
        case_id="plate-with-hole-candidate",
        generated_at_utc="2026-05-17T10:00:00+00:00",
    )
    path = write_plate_kirsch_verdict_yaml(case_golden, result)
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["verdict"] == "FAIL"
    assert payload["claim_tier"] == "tier_1_candidate"


# ---------------------------------------------------------------------
# Module-load registry — Phase 21 A baseline (tier_1 absent verdict)
# ---------------------------------------------------------------------


def test_cantilever_candidate_registered() -> None:
    """The case must be in the registry — Phase 20 B baseline."""
    from app.services.reporting._claim_tier import CLAIM_TIER_REGISTRY

    assert "cantilever-beam-candidate" in CLAIM_TIER_REGISTRY


def test_plate_with_hole_candidate_registered() -> None:
    from app.services.reporting._claim_tier import CLAIM_TIER_REGISTRY

    assert "plate-with-hole-candidate" in CLAIM_TIER_REGISTRY


def test_phase21a_validated_count_is_three() -> None:
    """The load-bearing Phase 21 A delivery pin. After Slice A persists
    verdict YAMLs for cantilever-beam-candidate + plate-with-hole-
    candidate under golden_samples/, the overlay in _claim_tier.py
    promotes both. Combined with the Phase 19 B cylinder-pv promotion,
    the registry now lists exactly 3 tier_2_validated cases. A drive-by
    edit that removes either verdict file trips this test."""
    from app.services.reporting._claim_tier import CLAIM_TIER_REGISTRY

    validated = {
        case_id
        for case_id, tier in CLAIM_TIER_REGISTRY.items()
        if tier == "tier_2_validated"
    }
    assert validated == {
        "cylinder-pv-candidate",
        "cantilever-beam-candidate",
        "plate-with-hole-candidate",
    }, f"unexpected tier_2_validated set: {validated}"


def test_phase21a_cantilever_verdict_yaml_persisted_on_disk() -> None:
    """The persisted PASS verdict must be readable from golden_samples
    and carry verdict='PASS' + the cantilever cross-check kind."""
    here = Path(__file__).resolve()
    repo_root = here.parents[2]
    path = (
        repo_root
        / "golden_samples"
        / "cantilever-beam-candidate"
        / VERDICT_YAML_FILENAME
    )
    assert path.is_file(), f"missing {path}"
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["verdict"] == "PASS"
    assert payload["claim_tier"] == "tier_2_validated"
    assert (
        payload["cross_check_kind"]
        == "cantilever_tip_deflection_euler_bernoulli"
    )


def test_phase21a_plate_kirsch_verdict_yaml_persisted_on_disk() -> None:
    here = Path(__file__).resolve()
    repo_root = here.parents[2]
    path = (
        repo_root
        / "golden_samples"
        / "plate-with-hole-candidate"
        / VERDICT_YAML_FILENAME
    )
    assert path.is_file(), f"missing {path}"
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["verdict"] == "PASS"
    assert payload["claim_tier"] == "tier_2_validated"
    assert payload["cross_check_kind"] == "plate_with_hole_kirsch_howland"
    assert payload["kirsch_k"] == pytest.approx(3.740, abs=1e-6)


# ---------------------------------------------------------------------
# Phase 20 B analytical re-pin (sanity, regression guard)
# ---------------------------------------------------------------------


def test_cantilever_analytical_signed_load_direction() -> None:
    """δ_tip = PL³/(3EI) must preserve the sign of P. With P = -1000 N
    on the canonical Phase 20 B / 21 A cantilever, δ_tip = -1.9048e-4 m
    (downward, matching the load direction)."""
    delta = compute_analytical_tip_deflection(
        length_m=1.0,
        youngs_modulus_pa=210e9,
        second_moment_m4=8.3333e-6,
        tip_load_n=-1000.0,
    )
    assert delta == pytest.approx(-1.9048e-4, rel=1e-3)
    assert delta < 0


# =====================================================================
# T:-3 — requires_solver E2E pins (real gmsh + real ccx)
# =====================================================================


@pytest.mark.requires_solver
def test_real_cantilever_meshed_runner_pass_verdict_within_15pct(
    tmp_path: Path,
) -> None:
    """The load-bearing Phase 21 A cantilever pin. Real gmsh meshes the
    canonical L=1m, h=b=0.1m cantilever into C3D4 tets, real ccx solves
    a -1000 N tip load, and the observed tip deflection sits within 15%
    of the Euler-Bernoulli analytical (-1.9048e-4 m).

    The runner persists the verdict YAML in the test workspace (NOT in
    the real golden_samples dir) — promotion to tier_2_validated lives
    in a deliberate offline action (the Phase 22 promotion script)."""
    from app.services.cross_check import run_cantilever_cross_check

    here = Path(__file__).resolve()
    repo_root = here.parents[2]
    src_geo = (
        repo_root
        / "golden_samples"
        / "cantilever-beam-candidate"
        / "data"
        / "cantilever.geo"
    )
    case_dir = tmp_path / "cantilever-beam-candidate"
    case_dir.mkdir()
    dst_geo = case_dir / "cantilever.geo"
    dst_geo.write_text(src_geo.read_text(encoding="utf-8"), encoding="utf-8")

    result = run_cantilever_cross_check(
        case_dir,
        case_id="cantilever-beam-candidate",
        material_id="steel-s355",
        geometry_path=dst_geo,
        length_m=1.0,
        section_depth_m=0.1,
        section_width_m=0.1,
        tip_load_n=-1000.0,
        # cl=0.015 gives ~7 elements through-thickness which is the
        # honest C3D4-on-bending convergence point (cl=0.025 lands at
        # -16.4% residual, cl=0.015 lands at ~-10-12% per Phase 21 A
        # canonical run; documented in cantilever_runner.py docstring).
        characteristic_length_m=0.015,
        gmsh_binary="/opt/homebrew/bin/gmsh",
        ccx_binary="/opt/homebrew/bin/ccx",
        ccx_timeout_sec=240.0,
        gmsh_timeout_sec=180.0,
    )
    assert isinstance(result, CantileverCrossCheckResult)
    assert result.node_count > 200, (
        f"mesh too coarse — expected >200 nodes, got {result.node_count}"
    )
    # Analytical is signed negative; observed should also be negative.
    assert result.analytical_m < 0
    assert result.observed_m < 0
    # Residual within tolerance → PASS.
    assert abs(result.residual_pct) <= CANTILEVER_CROSS_CHECK_TOLERANCE_PCT, (
        f"residual {result.residual_pct:.2f}% outside tolerance "
        f"{CANTILEVER_CROSS_CHECK_TOLERANCE_PCT}%; "
        f"analytical={result.analytical_m:.4e}, "
        f"observed={result.observed_m:.4e}"
    )
    assert result.verdict == "PASS"

    # Persist the verdict in the test workspace and confirm
    # round-trippability.
    verdict_path = write_cantilever_verdict_yaml(case_dir, result)
    payload = json.loads(verdict_path.read_text(encoding="utf-8"))
    assert payload["verdict"] == "PASS"
    assert payload["claim_tier"] == "tier_2_validated"


@pytest.mark.requires_solver
def test_real_plate_kirsch_meshed_runner_pass_verdict_within_20pct(
    tmp_path: Path,
) -> None:
    """The load-bearing Phase 21 A Kirsch pin. Real gmsh meshes the
    100×50×5 mm plate with a 10 mm-radius hole into C3D4 tets, real
    ccx solves a tensile pull along x, and the observed peak σ_xx at
    hole-edge nodes sits within 20% of K·σ_∞.

    With F=250 N over the W·T = 50·5 mm² gross cross-section:
        σ_∞ = 250 / 0.00025 = 1.0 MPa
        K   = 3.740 (Howland @ 2a/W = 0.4)
        σ_max ≈ 3.74 MPa"""
    from app.services.cross_check import run_plate_kirsch_cross_check

    here = Path(__file__).resolve()
    repo_root = here.parents[2]
    src_geo = (
        repo_root
        / "golden_samples"
        / "plate-with-hole-candidate"
        / "data"
        / "plate_with_hole.geo"
    )
    case_dir = tmp_path / "plate-with-hole-candidate"
    case_dir.mkdir()
    dst_geo = case_dir / "plate_with_hole.geo"
    dst_geo.write_text(src_geo.read_text(encoding="utf-8"), encoding="utf-8")

    result = run_plate_kirsch_cross_check(
        case_dir,
        case_id="plate-with-hole-candidate",
        material_id="steel-s355",
        geometry_path=dst_geo,
        plate_length_m=0.100,
        plate_width_m=0.050,
        plate_thickness_m=0.005,
        hole_radius_m=0.010,
        applied_force_n=250.0,
        characteristic_length_m=0.003,
        gmsh_binary="/opt/homebrew/bin/gmsh",
        ccx_binary="/opt/homebrew/bin/ccx",
        ccx_timeout_sec=240.0,
        gmsh_timeout_sec=180.0,
    )
    assert isinstance(result, PlateKirschCrossCheckResult)
    assert result.node_count > 400, (
        f"mesh too coarse — expected >400 nodes, got {result.node_count}"
    )
    assert result.kirsch_k == pytest.approx(3.740, abs=1e-6)
    # Both magnitudes positive (tensile load → positive σ_xx).
    assert result.analytical_pa > 0
    assert result.observed_pa > 0
    assert abs(result.residual_pct) <= PLATE_KIRSCH_CROSS_CHECK_TOLERANCE_PCT, (
        f"residual {result.residual_pct:.2f}% outside tolerance "
        f"{PLATE_KIRSCH_CROSS_CHECK_TOLERANCE_PCT}%; "
        f"analytical={result.analytical_pa:.3e}, "
        f"observed={result.observed_pa:.3e}"
    )
    assert result.verdict == "PASS"

    verdict_path = write_plate_kirsch_verdict_yaml(case_dir, result)
    payload = json.loads(verdict_path.read_text(encoding="utf-8"))
    assert payload["verdict"] == "PASS"
    assert payload["claim_tier"] == "tier_2_validated"
