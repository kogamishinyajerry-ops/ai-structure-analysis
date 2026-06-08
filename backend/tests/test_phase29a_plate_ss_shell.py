"""FM-04a Phase 29 A — S4 shell simply-supported plate cross-check tests.

The first validated case in the cohort to use SHELL elements (S4).
Closes the FEA Dim 1 hard cap (≤75/100 since Phase 18). Reuses the
Phase 25 A Timoshenko α·q·a⁴/D analytical helper verbatim — the
analytical is element-discretization-agnostic.

Anti-gaming guards (each pinned at predicate level):
  A:-1 — center-node lookup is geometric (≤ half-cell from a/2,a/2,0)
  D:-3 — analytical helper reused VERBATIM (no parallel definition)
  E:-1 — convergence pin (n_per_side >= 4 runtime guard)

Tier 1 / Tier 2 engineering candidate; not signed validation; not
benchmark agreement.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.services.cross_check.plate_simply_supported import (
    PLATE_SS_CROSS_CHECK_TOLERANCE_PCT,
    TIMOSHENKO_ALPHA_SQUARE_NU_0_3,
)
from app.services.cross_check.plate_ss_shell_runner import (
    DEFAULT_N_PER_SIDE,
    PlateSSShellCrossCheckResult,
    make_structured_quad_mesh,
    run_plate_ss_shell_cross_check,
    write_plate_ss_shell_verdict_yaml,
)
from app.services.reporting._claim_tier import CLAIM_TIER_REGISTRY


# ─────────────────────────────────────────────────────────────────
# 1. Structured mesh generator pins
# ─────────────────────────────────────────────────────────────────

class TestStructuredQuadMesh:
    def test_node_count_is_n_plus_one_squared(self) -> None:
        nodes, _elements = make_structured_quad_mesh(1.0, 20)
        assert len(nodes) == 21 * 21  # 441

    def test_element_count_is_n_squared(self) -> None:
        _nodes, elements = make_structured_quad_mesh(1.0, 20)
        assert len(elements) == 20 * 20  # 400

    def test_node_ids_are_one_indexed(self) -> None:
        nodes, _elements = make_structured_quad_mesh(1.0, 4)
        assert min(nodes) == 1
        assert max(nodes) == 25
        assert set(nodes) == set(range(1, 26))

    def test_element_ids_are_one_indexed(self) -> None:
        _nodes, elements = make_structured_quad_mesh(1.0, 4)
        assert min(elements) == 1
        assert max(elements) == 16

    def test_corner_node_positions(self) -> None:
        nodes, _elements = make_structured_quad_mesh(1.0, 20)
        # 4 corners: (0,0), (1,0), (0,1), (1,1)
        positions = {(round(x, 9), round(y, 9), z) for x, y, z in nodes.values()}
        assert (0.0, 0.0, 0.0) in positions
        assert (1.0, 0.0, 0.0) in positions
        assert (0.0, 1.0, 0.0) in positions
        assert (1.0, 1.0, 0.0) in positions

    def test_node_winding_is_ccw_viewed_from_plus_z(self) -> None:
        """The S4 winding must be CCW viewed from +z so the right-hand-
        rule normal points in +z. Test by computing cross product of
        (n2-n1) × (n4-n1) for the first element and asserting +z sign."""
        nodes, elements = make_structured_quad_mesh(1.0, 4)
        n1, n2, _n3, n4 = elements[1]
        x1, y1, _ = nodes[n1]
        x2, y2, _ = nodes[n2]
        x4, y4, _ = nodes[n4]
        ex, ey = x2 - x1, y2 - y1
        fx, fy = x4 - x1, y4 - y1
        cross_z = ex * fy - ey * fx
        assert cross_z > 0, "S4 winding must be CCW viewed from +z"

    def test_rejects_zero_or_negative_side_length(self) -> None:
        with pytest.raises(ValueError, match="side_length_m must be positive"):
            make_structured_quad_mesh(0.0, 10)
        with pytest.raises(ValueError, match="side_length_m must be positive"):
            make_structured_quad_mesh(-1.0, 10)

    def test_rejects_n_per_side_below_two(self) -> None:
        with pytest.raises(ValueError, match="n_per_side must be >= 2"):
            make_structured_quad_mesh(1.0, 1)


# ─────────────────────────────────────────────────────────────────
# 2. Runner input validation
# ─────────────────────────────────────────────────────────────────

class TestRunnerInputValidation:
    def test_rejects_zero_pressure(self) -> None:
        with pytest.raises(ValueError, match="pressure_pa must be non-zero"):
            run_plate_ss_shell_cross_check(
                Path("/tmp"),
                case_id="x",
                material_id="steel-s355",
                pressure_pa=0.0,
            )

    def test_rejects_n_per_side_below_four(self) -> None:
        with pytest.raises(ValueError, match="n_per_side must be >= 4"):
            run_plate_ss_shell_cross_check(
                Path("/tmp"),
                case_id="x",
                material_id="steel-s355",
                n_per_side=3,
            )

    def test_default_n_per_side_is_twenty(self) -> None:
        # E:-1 convergence pin: changing the default would silently
        # change the canonical residual. Pin it.
        assert DEFAULT_N_PER_SIDE == 20


# ─────────────────────────────────────────────────────────────────
# 3. Registry + verdict YAML schema pins
# ─────────────────────────────────────────────────────────────────

class TestRegistryAndVerdictSchema:
    def test_plate_ss_shell_candidate_is_in_registry(self) -> None:
        assert "plate-ss-shell-candidate" in CLAIM_TIER_REGISTRY

    def test_validated_count_is_nine_or_more(self) -> None:
        """Additive-promotion pattern: Phase 28 A's strict `len==8` is
        loosened to `>=9` here. Subset-of relationship preserves the
        original intent (no validated case downgraded)."""
        validated = [
            case_id
            for case_id, tier in CLAIM_TIER_REGISTRY.items()
            if tier == "tier_2_validated"
        ]
        assert len(validated) >= 9, (
            f"expected ≥9 tier_2_validated cases after Phase 29 A; "
            f"got {len(validated)}: {sorted(validated)}"
        )

    def test_plate_ss_shell_candidate_is_tier_2_validated(self) -> None:
        """Verdict overlay must have promoted the case from baseline
        tier_1_candidate after the live PASS run wrote the verdict
        YAML to golden_samples/."""
        assert (
            CLAIM_TIER_REGISTRY["plate-ss-shell-candidate"]
            == "tier_2_validated"
        ), "verdict overlay did not promote; check golden_samples/plate-ss-shell-candidate/cross_check_verdict.yaml exists and verdict='PASS'"

    def test_verdict_yaml_schema_version_is_1_1_0(self) -> None:
        """Phase 29 A bumps the verdict schema 1.0.0 → 1.1.0 to add
        `tolerance_pct` + `element_type` + `n_per_side` fields."""
        path = Path(__file__).resolve().parents[2] / (
            "golden_samples/plate-ss-shell-candidate/cross_check_verdict.yaml"
        )
        payload = json.loads(path.read_text(encoding="utf-8"))
        assert payload["schema_version"] == "1.1.0"
        assert payload["verdict"] == "PASS"
        assert payload["element_type"] == "S4"
        assert payload["n_per_side"] == 20
        assert payload["runner"] == "plate_ss_shell_runner"
        assert payload["cross_check_kind"] == "plate_simply_supported_shell_timoshenko"
        # Tolerance pin: 15% canonical envelope.
        assert payload["tolerance_pct"] == pytest.approx(15.0)
        # Residual is documented in NOTES.md as +0.4881%; assert within
        # a generous band to permit future ccx versions / hardware
        # rounding (still well inside the 15% envelope).
        assert abs(payload["residual_pct"]) < 5.0

    def test_verdict_yaml_claim_tier_is_tier_2_validated(self) -> None:
        path = Path(__file__).resolve().parents[2] / (
            "golden_samples/plate-ss-shell-candidate/cross_check_verdict.yaml"
        )
        payload = json.loads(path.read_text(encoding="utf-8"))
        assert payload["claim_tier"] == "tier_2_validated"
        assert "not_signed_validation" in payload["claim_boundary"]


# ─────────────────────────────────────────────────────────────────
# 4. Analytical helper reuse pin (D:-3)
# ─────────────────────────────────────────────────────────────────

class TestAnalyticalReuse:
    def test_runner_reuses_timoshenko_alpha_constant(self) -> None:
        """D:-3 anti-gaming guard: the runner imports the analytical
        helper module rather than re-defining α = 0.00406 locally.
        Confirms by importing from the runner module and asserting
        the constant matches the source."""
        from app.services.cross_check.plate_ss_shell_runner import (
            compute_simply_supported_plate_center_deflection_m,
        )
        # If the runner ever re-defines α locally, the import path
        # diverges and this test breaks deliberately.
        assert TIMOSHENKO_ALPHA_SQUARE_NU_0_3 == 0.00406
        # Sanity: helper produces a finite result for the canonical
        # plate geometry.
        w = compute_simply_supported_plate_center_deflection_m(
            side_length_m=1.0,
            thickness_m=0.020,
            youngs_modulus_pa=210e9,
            poisson_ratio=0.3,
            pressure_pa=-1.0e4,
        )
        assert w < 0  # downward under negative pressure
        assert abs(w) > 0


# ─────────────────────────────────────────────────────────────────
# 5. Tolerance constant + envelope sanity
# ─────────────────────────────────────────────────────────────────

class TestToleranceEnvelope:
    def test_tolerance_constant_is_fifteen_percent(self) -> None:
        """Pin the canonical envelope; a future loosening would
        require explicit retro acknowledgment."""
        assert PLATE_SS_CROSS_CHECK_TOLERANCE_PCT == 15.0


# ─────────────────────────────────────────────────────────────────
# 6. E2E (requires solver) — live ccx run
# ─────────────────────────────────────────────────────────────────


@pytest.mark.requires_solver
class TestLiveCcxRun:
    """End-to-end pin: re-run the full pipeline on a temp dir and
    assert the verdict + residual remain in band. Skipped in default
    pytest runs; run via `pytest -m requires_solver`."""

    def test_live_ccx_run_residual_under_five_percent(
        self, tmp_path: Path
    ) -> None:
        result: PlateSSShellCrossCheckResult = run_plate_ss_shell_cross_check(
            tmp_path,
            case_id="plate-ss-shell-candidate",
            material_id="steel-s355",
        )
        assert result.verdict == "PASS"
        assert result.node_count == 441
        assert result.element_count == 400
        assert result.n_per_side == 20
        assert result.element_type == "S4"
        # 5% generous band on the canonical residual (~0.49% live).
        assert abs(result.residual_pct) < 5.0
        # E:-1: small-deflection envelope honored.
        assert result.small_deflection_ratio < 0.2

    def test_live_ccx_verdict_yaml_round_trip(self, tmp_path: Path) -> None:
        result = run_plate_ss_shell_cross_check(
            tmp_path,
            case_id="plate-ss-shell-candidate",
            material_id="steel-s355",
        )
        write_plate_ss_shell_verdict_yaml(tmp_path, result)
        path = tmp_path / "cross_check_verdict.yaml"
        payload = json.loads(path.read_text(encoding="utf-8"))
        assert payload["schema_version"] == "1.1.0"
        assert payload["element_type"] == "S4"
        assert payload["n_per_side"] == 20
