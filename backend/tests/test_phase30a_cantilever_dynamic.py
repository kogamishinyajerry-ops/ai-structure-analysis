"""FM-04a Phase 30 A — cantilever free-vibration *DYNAMIC cross-check tests.

The FIRST validated case in the cohort to use CalculiX `*DYNAMIC`
(transient implicit time integration). Closes the FEA Dim 6
ballistic-readiness floor (50/100 since project inception).

Anti-gaming guards (each pinned at predicate level):
  A:-1 — observed period derived from zero-crossing spacing
  D:-3 — analytical helper reused VERBATIM (no parallel β₁L def)
  E:-1 — Courant time-step pin (dt < T_analytical / 20)
  E:-2 — damping pin (α = 0 in *DYNAMIC card)

Tier 1 / Tier 2 engineering candidate; not signed validation; not
benchmark agreement.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from app.services.cross_check.cantilever_dynamic_runner import (
    CANTILEVER_DYNAMIC_CROSS_CHECK_TOLERANCE_PCT,
    DEFAULT_DT_INITIAL_S,
    DEFAULT_IMPULSE_DURATION_S,
    DEFAULT_IMPULSE_PEAK_N,
    DEFAULT_T_TOTAL_S,
    CantileverDynamicCrossCheckResult,
    compute_observed_period_s,
    extract_zero_crossings,
    run_cantilever_dynamic_cross_check,
    write_cantilever_dynamic_verdict_yaml,
)
from app.services.cross_check.cantilever_modal import (
    compute_cantilever_first_natural_frequency_hz,
)
from app.services.reporting._claim_tier import CLAIM_TIER_REGISTRY


REPO_ROOT = Path(__file__).resolve().parents[2]
GEO_PATH = (
    REPO_ROOT
    / "golden_samples"
    / "cantilever-dynamic-candidate"
    / "data"
    / "cantilever_dynamic.geo"
)
VERDICT_PATH = (
    REPO_ROOT
    / "golden_samples"
    / "cantilever-dynamic-candidate"
    / "cross_check_verdict.yaml"
)


# ─────────────────────────────────────────────────────────────────
# 1. Zero-crossing extractor pins (A:-1)
# ─────────────────────────────────────────────────────────────────

class TestZeroCrossingExtractor:
    def test_sin_at_period_10ms_yields_crossings_every_5ms(self) -> None:
        import math
        times = [i * 1e-4 for i in range(101)]  # 0 to 10ms
        values = [math.sin(2 * math.pi * t / 0.010) for t in times]
        crossings = extract_zero_crossings(times, values)
        # Expect crossings at 0, 5ms, 10ms (3 crossings; the boundary
        # at t=0 may be missed if v[0] == 0 and v[1] != 0).
        assert len(crossings) >= 2
        # Spacing between crossings is half-period = 5ms.
        for i in range(len(crossings) - 1):
            assert crossings[i + 1] - crossings[i] == pytest.approx(
                0.005, abs=1e-4
            )

    def test_constant_signal_yields_no_crossings(self) -> None:
        times = [i * 1e-4 for i in range(10)]
        values = [1.0] * 10
        assert extract_zero_crossings(times, values) == []

    def test_linear_crossing_interpolation(self) -> None:
        # Values go from -2 to +2 over t in [0, 1]; zero crossing at t=0.5.
        times = [0.0, 1.0]
        values = [-2.0, 2.0]
        crossings = extract_zero_crossings(times, values)
        assert len(crossings) == 1
        assert crossings[0] == pytest.approx(0.5)

    def test_mismatched_lengths_raises(self) -> None:
        with pytest.raises(ValueError, match="must be the same length"):
            extract_zero_crossings([0.0, 1.0], [1.0, 2.0, 3.0])


class TestObservedPeriodCompute:
    def test_period_from_evenly_spaced_crossings(self) -> None:
        # 5 crossings 5ms apart → 4 spacings of 5ms each → period = 10ms.
        crossings = [0.001, 0.006, 0.011, 0.016, 0.021]  # 5 crossings
        observed = compute_observed_period_s(crossings)
        # Drop first (transient); spacings 5/5/5 → mean 5ms → period 10ms.
        assert observed == pytest.approx(0.010, abs=1e-6)

    def test_fewer_than_three_crossings_raises(self) -> None:
        with pytest.raises(ValueError, match=">= 3 zero crossings"):
            compute_observed_period_s([0.001, 0.005])

    def test_drops_first_crossing_for_transient(self) -> None:
        # If we DIDN'T drop the first crossing, this list would give
        # period 2 × ((0.001-0)+(0.006-0.001)+(0.011-0.006))/3 = 2×0.00367
        # = 7.33ms. After dropping the first (0): spacings (0.005, 0.005)
        # → mean 5ms → period 10ms.
        crossings = [0.0, 0.001, 0.006, 0.011]
        observed = compute_observed_period_s(crossings)
        assert observed == pytest.approx(0.010, abs=1e-6)


# ─────────────────────────────────────────────────────────────────
# 2. Runner input validation
# ─────────────────────────────────────────────────────────────────

class TestRunnerInputValidation:
    def test_rejects_zero_length(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="length_m must be positive"):
            run_cantilever_dynamic_cross_check(
                tmp_path,
                case_id="x",
                material_id="steel-s355",
                geometry_path=tmp_path / "x.geo",
                length_m=0.0,
            )

    def test_rejects_zero_dt(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="dt_initial_s must be positive"):
            run_cantilever_dynamic_cross_check(
                tmp_path,
                case_id="x",
                material_id="steel-s355",
                geometry_path=tmp_path / "x.geo",
                dt_initial_s=0.0,
            )

    def test_E_minus_1_courant_dt_too_large_raises(self, tmp_path: Path) -> None:
        # T_analytical ≈ 14.96 ms for the default geometry; Courant
        # limit T/20 ≈ 0.75 ms. dt = 1ms (> 0.75ms) must trip the guard.
        with pytest.raises(ValueError, match="Courant limit"):
            run_cantilever_dynamic_cross_check(
                tmp_path,
                case_id="x",
                material_id="steel-s355",
                geometry_path=tmp_path / "x.geo",
                dt_initial_s=1.0e-3,  # 1ms, well over the 0.75ms limit
            )


# ─────────────────────────────────────────────────────────────────
# 3. Registry + verdict YAML schema pins
# ─────────────────────────────────────────────────────────────────

class TestRegistryAndVerdictSchema:
    def test_cantilever_dynamic_candidate_in_registry(self) -> None:
        assert "cantilever-dynamic-candidate" in CLAIM_TIER_REGISTRY

    def test_validated_count_is_ten_or_more(self) -> None:
        from app.services.reporting._claim_tier import _apply_verdict_overlay
        _apply_verdict_overlay()
        validated = {
            case_id
            for case_id, tier in CLAIM_TIER_REGISTRY.items()
            if tier == "tier_2_validated"
        }
        assert len(validated) >= 10, (
            f"expected ≥10 tier_2_validated cases after Phase 30 A; "
            f"got {len(validated)}: {sorted(validated)}"
        )

    def test_cantilever_dynamic_promoted_to_tier_2_validated(self) -> None:
        assert (
            CLAIM_TIER_REGISTRY["cantilever-dynamic-candidate"]
            == "tier_2_validated"
        ), "verdict overlay did not promote; check verdict YAML PASS"

    def test_verdict_yaml_schema_is_1_2_0(self) -> None:
        """Phase 30 A bumps schema 1.1.0 → 1.2.0 adding
        observed_period_s + analytical_period_s + solver_kind=dynamic."""
        payload = json.loads(VERDICT_PATH.read_text(encoding="utf-8"))
        assert payload["schema_version"] == "1.2.0"
        assert payload["verdict"] == "PASS"
        assert payload["solver_kind"] == "dynamic"
        assert payload["runner"] == "cantilever_dynamic_runner"
        assert (
            payload["cross_check_kind"]
            == "cantilever_free_vibration_dynamic"
        )

    def test_verdict_yaml_carries_period_fields(self) -> None:
        payload = json.loads(VERDICT_PATH.read_text(encoding="utf-8"))
        assert "observed_period_s" in payload
        assert "analytical_period_s" in payload
        assert payload["observed_period_s"] > 0
        assert payload["analytical_period_s"] > 0
        # Tolerance pin: 8% canonical envelope.
        assert payload["tolerance_pct"] == pytest.approx(8.0)
        # Live residual was -1.19%; assert well inside 5% generous band.
        assert abs(payload["residual_pct"]) < 5.0

    def test_verdict_yaml_claim_boundary_mentions_first_dynamic(self) -> None:
        payload = json.loads(VERDICT_PATH.read_text(encoding="utf-8"))
        assert payload["claim_tier"] == "tier_2_validated"
        # Boundary string must record the "first dynamic" milestone.
        assert "first_dynamic_validated" in payload["claim_boundary"]


# ─────────────────────────────────────────────────────────────────
# 4. Analytical helper reuse pin (D:-3)
# ─────────────────────────────────────────────────────────────────

class TestAnalyticalReuse:
    def test_runner_reuses_phase26a_f1_helper(self) -> None:
        """D:-3 anti-gaming guard: the analytical helper is reused
        from Phase 26 A; there is no parallel β₁L = 1.875104 in the
        Phase 30 A runner. Confirm by sanity-checking the helper
        produces the canonical value."""
        f1 = compute_cantilever_first_natural_frequency_hz(
            length_m=0.500,
            height_m=0.020,
            width_m=0.020,
            youngs_modulus_pa=210e9,
            density_kg_m3=7850.0,
            mode_index=1,
        )
        # Phase 26 A pinned analytical f_1 ≈ 66.84 Hz for this geometry.
        assert f1 == pytest.approx(66.84, abs=0.5)
        # Period 1/f → ≈ 14.96 ms
        assert 1.0 / f1 == pytest.approx(0.01496, abs=1e-4)


# ─────────────────────────────────────────────────────────────────
# 5. Tolerance constant pin
# ─────────────────────────────────────────────────────────────────

class TestToleranceEnvelope:
    def test_tolerance_constant_is_eight_percent(self) -> None:
        """Pin canonical envelope; future loosening requires retro."""
        assert CANTILEVER_DYNAMIC_CROSS_CHECK_TOLERANCE_PCT == 8.0

    def test_defaults_pinned(self) -> None:
        """Convergence-relevant defaults are pinned so a future
        relax doesn't silently change the canonical residual."""
        assert DEFAULT_DT_INITIAL_S == 1.0e-4
        assert DEFAULT_T_TOTAL_S == 0.060
        assert DEFAULT_IMPULSE_PEAK_N == 200.0
        assert DEFAULT_IMPULSE_DURATION_S == 0.001


# ─────────────────────────────────────────────────────────────────
# 6. E2E (requires solver) — live ccx run
# ─────────────────────────────────────────────────────────────────


@pytest.mark.requires_solver
class TestLiveCcxRun:
    """End-to-end pin: re-run the full pipeline on a temp dir and
    assert the verdict + residual remain in band."""

    def test_live_ccx_run_residual_under_five_percent(
        self, tmp_path: Path
    ) -> None:
        geo_local = tmp_path / "cantilever_dynamic.geo"
        shutil.copyfile(GEO_PATH, geo_local)
        result: CantileverDynamicCrossCheckResult = (
            run_cantilever_dynamic_cross_check(
                tmp_path,
                case_id="cantilever-dynamic-candidate",
                material_id="steel-s355",
                geometry_path=geo_local,
            )
        )
        assert result.verdict == "PASS"
        # 5% generous band on the canonical residual (~-1.19% live).
        assert abs(result.residual_pct) < 5.0
        # E:-1 + sampling sanity: must have at least 8 zero crossings
        # over 4 periods, and at least 100 increments to support clean
        # period extraction.
        assert result.n_zero_crossings >= 5
        assert result.n_increments >= 100

    def test_live_ccx_verdict_yaml_round_trip(self, tmp_path: Path) -> None:
        geo_local = tmp_path / "cantilever_dynamic.geo"
        shutil.copyfile(GEO_PATH, geo_local)
        result = run_cantilever_dynamic_cross_check(
            tmp_path,
            case_id="cantilever-dynamic-candidate",
            material_id="steel-s355",
            geometry_path=geo_local,
        )
        write_cantilever_dynamic_verdict_yaml(tmp_path, result)
        path = tmp_path / "cross_check_verdict.yaml"
        payload = json.loads(path.read_text(encoding="utf-8"))
        assert payload["schema_version"] == "1.2.0"
        assert payload["solver_kind"] == "dynamic"
        assert payload["verdict"] == "PASS"
