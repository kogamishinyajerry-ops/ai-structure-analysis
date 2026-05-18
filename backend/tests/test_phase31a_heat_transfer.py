"""FM-04a Phase 31 A — first *HEAT TRANSFER validated case tests.

PIVOT from blueprint *CONTACT PAIR slice documented in
`golden_samples/heat-transfer-1d-candidate/NOTES.md` and Phase 31
retro. Contact-pair moves to Phase 32.

Three deliveries pinned:

1. Analytical helpers (`heat_transfer_1d.py`):
   * `steady_state_1d_temperature_k` correctly produces the linear
     profile at boundary endpoints, midpoint, and arbitrary x.
   * Preconditions (length > 0, x in [0, L]) raise ValueError.
   * `residual_pct` produces signed % vs |analytical|.

2. Runner unit-level (`heat_transfer_runner.py`):
   * Structured C3D8 mesh has the right node/element count for
     the default 10 × 2 × 2 partition.
   * Midplane node locator picks the node at exactly x = L/2 on
     the y=0, z=0 corner edge.
   * .dat NT-block parser handles the actual CCX header format
     ("temperatures for set ALL_NODES and time …") with the
     intervening blank line.
   * INP composer emits the required *HEAT TRANSFER / *CONDUCTIVITY
     / *BOUNDARY (DOF 11) / *NODE PRINT NT blocks.

3. Golden-samples verdict YAML (`cross_check_verdict.yaml`) at
   schema 1.3.0 with `solver_kind: heat_transfer_steady_state`
   and `claim_boundary` containing `"first_heat_transfer_validated"`.

4. @requires_solver E2E: live ccx run reproduces the linear
   analytical to within 1% at the midplane probe.

Tier 1 / Tier 2 engineering candidate; not signed validation;
not benchmark agreement.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Final

import pytest

from app.services.cross_check.heat_transfer_1d import (
    residual_pct,
    steady_state_1d_temperature_k,
)
from app.services.cross_check.heat_transfer_runner import (
    DEFAULT_HEIGHT_M,
    DEFAULT_LENGTH_M,
    DEFAULT_NX,
    DEFAULT_NY,
    DEFAULT_NZ,
    DEFAULT_T_LEFT_K,
    DEFAULT_T_RIGHT_K,
    DEFAULT_WIDTH_M,
    HEAT_TRANSFER_CROSS_CHECK_TOLERANCE_PCT,
    HEAT_TRANSFER_DEFAULT_CONDUCTIVITY_W_MK,
    _build_structured_hex_mesh,
    _find_midplane_node,
    _parse_nt_block,
    _write_heat_transfer_inp,
    run_heat_transfer_cross_check,
    write_heat_transfer_verdict_yaml,
)

REPO_ROOT: Final[Path] = Path(__file__).resolve().parents[2]
GOLDEN_DIR: Final[Path] = (
    REPO_ROOT / "golden_samples" / "heat-transfer-1d-candidate"
)


# ────────────────────────────────────────────────────────────────────
# 1. Analytical helpers
# ────────────────────────────────────────────────────────────────────


class TestSteadyState1DTemperatureK:
    def test_left_boundary_returns_t_left(self) -> None:
        assert steady_state_1d_temperature_k(
            x_m=0.0,
            length_m=0.100,
            t_left_k=373.15,
            t_right_k=273.15,
        ) == pytest.approx(373.15, abs=1e-9)

    def test_right_boundary_returns_t_right(self) -> None:
        assert steady_state_1d_temperature_k(
            x_m=0.100,
            length_m=0.100,
            t_left_k=373.15,
            t_right_k=273.15,
        ) == pytest.approx(273.15, abs=1e-9)

    def test_midpoint_returns_average(self) -> None:
        # 373.15 + (273.15 - 373.15) * 0.5 = 323.15
        assert steady_state_1d_temperature_k(
            x_m=0.050,
            length_m=0.100,
            t_left_k=373.15,
            t_right_k=273.15,
        ) == pytest.approx(323.15, abs=1e-9)

    def test_quarter_point_returns_three_quarter_left(self) -> None:
        # 373.15 + (273.15 - 373.15) * 0.25 = 348.15
        assert steady_state_1d_temperature_k(
            x_m=0.025,
            length_m=0.100,
            t_left_k=373.15,
            t_right_k=273.15,
        ) == pytest.approx(348.15, abs=1e-9)

    def test_celsius_unit_agnostic(self) -> None:
        # Linear combination is unit-agnostic over T.
        assert steady_state_1d_temperature_k(
            x_m=0.050,
            length_m=0.100,
            t_left_k=100.0,
            t_right_k=0.0,
        ) == pytest.approx(50.0, abs=1e-9)

    def test_negative_length_raises(self) -> None:
        with pytest.raises(ValueError, match="length_m must be positive"):
            steady_state_1d_temperature_k(
                x_m=0.0, length_m=-1.0, t_left_k=300, t_right_k=300
            )

    def test_x_outside_bar_raises(self) -> None:
        with pytest.raises(ValueError, match="outside the bar"):
            steady_state_1d_temperature_k(
                x_m=2.0, length_m=1.0, t_left_k=300, t_right_k=300
            )

    def test_x_just_over_bound_clamped_within_tolerance(self) -> None:
        # Tolerance allows ~1e-9 over for FP boundary noise.
        result = steady_state_1d_temperature_k(
            x_m=0.100 + 1e-15,
            length_m=0.100,
            t_left_k=373.15,
            t_right_k=273.15,
        )
        assert result == pytest.approx(273.15, abs=1e-9)


class TestResidualPct:
    def test_zero_residual(self) -> None:
        assert residual_pct(observed=100.0, analytical=100.0) == 0.0

    def test_signed_positive_residual(self) -> None:
        # observed 110, analytical 100 → +10%
        assert residual_pct(observed=110.0, analytical=100.0) == pytest.approx(10.0)

    def test_signed_negative_residual(self) -> None:
        # observed 90, analytical 100 → -10%
        assert residual_pct(observed=90.0, analytical=100.0) == pytest.approx(-10.0)

    def test_residual_against_negative_analytical_uses_abs_in_denom(self) -> None:
        # observed -10, analytical -20 → (-10 - -20)/20 * 100 = +50%
        assert residual_pct(observed=-10.0, analytical=-20.0) == pytest.approx(50.0)

    def test_zero_analytical_returns_abs_observed_pct(self) -> None:
        # Degraded indicator: |observed| * 100
        assert residual_pct(observed=0.5, analytical=0.0) == 50.0


# ────────────────────────────────────────────────────────────────────
# 2. Runner unit-level
# ────────────────────────────────────────────────────────────────────


class TestStructuredHexMesh:
    def test_default_partition_node_and_element_counts(self) -> None:
        nodes, elements = _build_structured_hex_mesh(
            length_m=DEFAULT_LENGTH_M,
            height_m=DEFAULT_HEIGHT_M,
            width_m=DEFAULT_WIDTH_M,
            nx=DEFAULT_NX,
            ny=DEFAULT_NY,
            nz=DEFAULT_NZ,
        )
        # (10+1)(2+1)(2+1) = 99; 10 * 2 * 2 = 40.
        assert len(nodes) == 99
        assert len(elements) == 40

    def test_node_coords_at_corners(self) -> None:
        nodes, _ = _build_structured_hex_mesh(
            length_m=1.0, height_m=2.0, width_m=3.0, nx=1, ny=1, nz=1
        )
        # 8 nodes for 1×1×1 partition.
        assert len(nodes) == 8
        # First corner at origin.
        assert nodes[1] == (0.0, 0.0, 0.0)
        # Last corner at (L, H, W).
        assert nodes[8] == pytest.approx((1.0, 2.0, 3.0))

    def test_element_connectivity_is_8_nodes(self) -> None:
        _, elements = _build_structured_hex_mesh(
            length_m=1.0, height_m=1.0, width_m=1.0, nx=2, ny=1, nz=1
        )
        for connectivity in elements.values():
            assert len(connectivity) == 8

    def test_zero_partition_raises(self) -> None:
        with pytest.raises(ValueError, match="must each be"):
            _build_structured_hex_mesh(
                length_m=1.0, height_m=1.0, width_m=1.0, nx=0, ny=1, nz=1
            )


class TestFindMidplaneNode:
    def test_finds_node_at_exact_midplane_on_corner_edge(self) -> None:
        # 10 × 2 × 2 partition → node #6 is at x=0.050, y=z=0.
        nodes, _ = _build_structured_hex_mesh(
            length_m=DEFAULT_LENGTH_M,
            height_m=DEFAULT_HEIGHT_M,
            width_m=DEFAULT_WIDTH_M,
            nx=DEFAULT_NX,
            ny=DEFAULT_NY,
            nz=DEFAULT_NZ,
        )
        nid, xc = _find_midplane_node(nodes, DEFAULT_LENGTH_M)
        assert xc == pytest.approx(0.050, abs=1e-9)
        assert nodes[nid] == pytest.approx((0.050, 0.0, 0.0))

    def test_finds_node_for_odd_partition(self) -> None:
        nodes, _ = _build_structured_hex_mesh(
            length_m=1.0, height_m=1.0, width_m=1.0, nx=3, ny=1, nz=1
        )
        nid, xc = _find_midplane_node(nodes, 1.0)
        # Closest x on the y=z=0 edge to x=0.5: either x≈0.333 or
        # x≈0.667. Both equidistant; the iterator finds the first
        # one but either is acceptable for this asymmetric partition.
        assert abs(xc - 0.5) <= 1.0 / 3.0 / 2.0 + 1e-9


class TestParseNTBlock:
    def test_parses_canonical_ccx_header(self, tmp_path: Path) -> None:
        # Synthesized to match the live ccx output observed during
        # the Phase 31 A development smoke run.
        dat_content = """

                        S T E P       1


                                INCREMENT     1


 temperatures for set ALL_NODES and time  0.1000000E+01

         1  3.731500E+02
         2  3.631500E+02
         3  3.531500E+02
         6  3.231500E+02
"""
        dat = tmp_path / "fake.dat"
        dat.write_text(dat_content, encoding="utf-8")
        result = _parse_nt_block(dat)
        assert result == {
            1: 373.15,
            2: 363.15,
            3: 353.15,
            6: 323.15,
        }

    def test_blank_lines_within_header_section_do_not_terminate_scan(
        self, tmp_path: Path
    ) -> None:
        # The first blank line after the header should NOT end the
        # block — only blank lines AFTER the first data row do.
        dat_content = """ temperatures for set X and time  1.0e+00


         5  2.500000E+02
"""
        dat = tmp_path / "fake.dat"
        dat.write_text(dat_content, encoding="utf-8")
        result = _parse_nt_block(dat)
        assert result == {5: 250.0}

    def test_missing_block_raises(self, tmp_path: Path) -> None:
        dat = tmp_path / "empty.dat"
        dat.write_text("nothing of interest here\n", encoding="utf-8")
        from app.adapters.calculix.runner import CalculiXRunError

        with pytest.raises(CalculiXRunError, match="no NT block"):
            _parse_nt_block(dat)

    def test_missing_file_raises(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            _parse_nt_block(tmp_path / "nope.dat")


class TestWriteInp:
    def test_emits_required_keywords(self, tmp_path: Path) -> None:
        nodes, elements = _build_structured_hex_mesh(
            length_m=1.0, height_m=1.0, width_m=1.0, nx=1, ny=1, nz=1
        )
        inp = _write_heat_transfer_inp(
            tmp_path,
            jobname="x",
            nodes=nodes,
            elements=elements,
            length_m=1.0,
            material_name="STEEL_HT",
            conductivity_w_mk=50.0,
            t_left_k=400.0,
            t_right_k=300.0,
            t_initial_k=350.0,
        )
        text = inp.read_text(encoding="utf-8")
        for needle in [
            "*HEADING",
            "*NODE",
            "*ELEMENT, TYPE=C3D8",
            "*NSET, NSET=LEFT",
            "*NSET, NSET=RIGHT",
            "*NSET, NSET=ALL_NODES",
            "*MATERIAL, NAME=STEEL_HT",
            "*CONDUCTIVITY",
            "*SOLID SECTION, ELSET=BAR, MATERIAL=STEEL_HT",
            "*INITIAL CONDITIONS, TYPE=TEMPERATURE",
            "*PHYSICAL CONSTANTS, ABSOLUTE ZERO=0.0",
            "*STEP",
            "*HEAT TRANSFER, STEADY STATE",
            "*BOUNDARY",
            "LEFT, 11, 11, 4.000000e+02",
            "RIGHT, 11, 11, 3.000000e+02",
            "*NODE PRINT, NSET=ALL_NODES",
            "NT",
            "*END STEP",
        ]:
            assert needle in text, f"missing {needle!r} in INP"


# ────────────────────────────────────────────────────────────────────
# 3. Golden-samples verdict YAML pin
# ────────────────────────────────────────────────────────────────────


class TestVerdictYamlOnDisk:
    @pytest.fixture
    def payload(self) -> dict:
        path = GOLDEN_DIR / "cross_check_verdict.yaml"
        assert path.is_file(), (
            f"missing verdict at {path}; re-run via "
            f"backend/app/services/cross_check/heat_transfer_runner.run_heat_transfer_cross_check"
        )
        return json.loads(path.read_text(encoding="utf-8"))

    def test_schema_version(self, payload: dict) -> None:
        assert payload["schema_version"] == "1.3.0"

    def test_case_id(self, payload: dict) -> None:
        assert payload["case_id"] == "heat-transfer-1d-candidate"

    def test_solver_kind(self, payload: dict) -> None:
        assert payload["solver_kind"] == "heat_transfer_steady_state"

    def test_cross_check_kind(self, payload: dict) -> None:
        assert payload["cross_check_kind"] == "heat_transfer_1d_linear_conduction"

    def test_verdict_pass(self, payload: dict) -> None:
        assert payload["verdict"] == "PASS"

    def test_tolerance_matches_default(self, payload: dict) -> None:
        assert payload["tolerance_pct"] == pytest.approx(
            HEAT_TRANSFER_CROSS_CHECK_TOLERANCE_PCT
        )

    def test_residual_is_within_envelope(self, payload: dict) -> None:
        assert abs(payload["residual_pct"]) <= payload["tolerance_pct"]

    def test_claim_boundary_mentions_first_heat_transfer(self, payload: dict) -> None:
        assert "first_heat_transfer_validated" in payload["claim_boundary"]

    def test_geometry_pins(self, payload: dict) -> None:
        assert payload["length_m"] == pytest.approx(DEFAULT_LENGTH_M)
        assert payload["height_m"] == pytest.approx(DEFAULT_HEIGHT_M)
        assert payload["width_m"] == pytest.approx(DEFAULT_WIDTH_M)

    def test_bc_pins(self, payload: dict) -> None:
        assert payload["t_left_k"] == pytest.approx(DEFAULT_T_LEFT_K)
        assert payload["t_right_k"] == pytest.approx(DEFAULT_T_RIGHT_K)

    def test_midplane_node_on_corner_edge(self, payload: dict) -> None:
        assert payload["midplane_node_x_m"] == pytest.approx(0.050, abs=1e-9)

    def test_element_type(self, payload: dict) -> None:
        assert payload["element_type"] == "C3D8"

    def test_node_element_counts(self, payload: dict) -> None:
        assert payload["node_count"] == 99
        assert payload["element_count"] == 40

    def test_runner_field(self, payload: dict) -> None:
        assert payload["runner"] == "heat_transfer_runner"

    def test_claim_tier_promoted_or_candidate(self, payload: dict) -> None:
        # tier_2_validated for PASS, tier_1_candidate otherwise.
        assert payload["claim_tier"] in {"tier_1_candidate", "tier_2_validated"}
        # Phase 31 A ships PASS so should be tier_2_validated.
        assert payload["claim_tier"] == "tier_2_validated"


# ────────────────────────────────────────────────────────────────────
# 4. Claim-tier registry membership
# ────────────────────────────────────────────────────────────────────


def test_heat_transfer_1d_candidate_in_claim_tier_registry() -> None:
    from app.services.reporting._claim_tier import CLAIM_TIER_REGISTRY

    assert "heat-transfer-1d-candidate" in CLAIM_TIER_REGISTRY


def test_heat_transfer_1d_candidate_promoted_to_tier_2_after_overlay() -> None:
    from app.services.reporting._claim_tier import (
        CLAIM_TIER_REGISTRY,
        _apply_verdict_overlay,
    )

    _apply_verdict_overlay()
    assert CLAIM_TIER_REGISTRY["heat-transfer-1d-candidate"] == "tier_2_validated"


def test_validated_cohort_size_at_least_eleven() -> None:
    """Phase 1-30 chain additive only: validated count was 10 after
    Phase 30 A; Phase 31 A makes it 11. The strict pin is loosened
    to >= to honor the additive-promotion pattern."""
    from app.services.reporting._claim_tier import (
        CLAIM_TIER_REGISTRY,
        _apply_verdict_overlay,
    )

    _apply_verdict_overlay()
    validated = [
        case_id
        for case_id, tier in CLAIM_TIER_REGISTRY.items()
        if tier == "tier_2_validated"
    ]
    assert len(validated) >= 11


# ────────────────────────────────────────────────────────────────────
# 5. @requires_solver E2E
# ────────────────────────────────────────────────────────────────────


@pytest.mark.requires_solver
def test_phase31a_heat_transfer_residual_under_one_percent(
    tmp_path: Path,
) -> None:
    """End-to-end real ccx run pin: 0.100 m × 0.020 m × 0.020 m steel
    bar with 373.15 K / 273.15 K end-face temperatures must produce
    |residual_pct| ≤ 1% at the midplane probe (and in practice
    ≪ 0.001% because C3D8 reproduces a linear field exactly)."""
    result = run_heat_transfer_cross_check(
        tmp_path,
        case_id="heat-transfer-1d-candidate",
        material_id="steel-s355",
    )
    assert result.verdict == "PASS"
    assert abs(result.residual_pct) <= HEAT_TRANSFER_CROSS_CHECK_TOLERANCE_PCT
    assert result.node_count == 99
    assert result.element_count == 40
    assert result.element_type == "C3D8"


@pytest.mark.requires_solver
def test_phase31a_verdict_yaml_round_trip(tmp_path: Path) -> None:
    """Run + write + read-back round-trip pin."""
    result = run_heat_transfer_cross_check(
        tmp_path,
        case_id="heat-transfer-1d-candidate",
        material_id="steel-s355",
    )
    write_heat_transfer_verdict_yaml(tmp_path, result)
    path = tmp_path / "cross_check_verdict.yaml"
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["schema_version"] == "1.3.0"
    assert payload["solver_kind"] == "heat_transfer_steady_state"
    assert payload["element_type"] == "C3D8"


# ────────────────────────────────────────────────────────────────────
# 6. Default constants pin (anti-drift)
# ────────────────────────────────────────────────────────────────────


def test_default_conductivity_pin() -> None:
    """Pin the hardcoded conductivity at the textbook S355 value.
    A future tweak that drifts this value MUST update the docstring
    + NOTES.md so reviewers see the lineage."""
    assert HEAT_TRANSFER_DEFAULT_CONDUCTIVITY_W_MK == 50.0


def test_default_tolerance_pin() -> None:
    assert HEAT_TRANSFER_CROSS_CHECK_TOLERANCE_PCT == 1.0
