"""FM-04a Phase 31 C — Richardson extrapolation pins.

Three deliveries pinned:

1. richardson_extrapolate module unit tests — closed-form math
   correctness (textbook 3-point convergent triple), non-monotone
   rejection (no fabricated f_∞), constant-ratio vs non-constant-
   ratio handling, sign preservation.

2. plate-ss-shell-candidate richardson section — schema 1.1.0
   addendum on the Phase 30 D artifact. Pins the f_∞ value, p
   order, r=2 constant, and the +1.31% extrapolated residual that
   CONFIRMS the S4+Mindlin asymptotic bias originally identified
   in Phase 30 D.

3. cantilever-beam-modal-candidate richardson section — schema
   1.1.0 addendum. Pins the f_∞ value, p estimate, r=1.6 with
   refinement_ratio_constant=False (cl=12/8/5 non-constant
   ratio), and the +0.030% extrapolated residual indicating
   asymptotic agreement with Euler-Bernoulli.

Anti-gaming guards:
* A:-1: Richardson values pinned at 6+ digits of precision, NOT
  hand-tweaked. Source: live application of `richardson_extrapolate`
  to the existing Phase 30 D points.
* B:-1: r=2.0 / r=1.6 pinned verbatim — no rounding-to-friendly.
* C:-1: All Phase 30 D pins (test_phase30d_convergence_study.py)
  must still pass. This file adds NEW pins on the NEW richardson
  field; it does not change Phase 30 D behavior.
* D:-3: Math formula `f_∞ = f_3 + (f_3 - f_2) / (r ** p - 1)` is
  the SSOT in `convergence_study.richardson_extrapolate`; the
  textbook test calls that function — no parallel re-implementation.
* E:-1: When extrapolation fails (non-monotone / division-by-zero),
  the test asserts the returned RichardsonEstimate has
  `extrapolated_value=None` — no fabricated fallback.

Tier 1 / Tier 2 engineering candidate; not signed validation; not
benchmark agreement.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import pytest

from app.services.cross_check.convergence_study import (
    ConvergenceArtifact,
    ConvergencePoint,
    RichardsonEstimate,
    compute_richardson_from_artifact,
    read_convergence_artifact,
    richardson_extrapolate,
)

GOLDEN_ROOT: Path = (
    Path(__file__).resolve().parents[2] / "golden_samples"
)


# ────────────────────────────────────────────────────────────────────
# 1. richardson_extrapolate unit tests (closed-form math)
# ────────────────────────────────────────────────────────────────────


class TestRichardsonExtrapolateMath:
    """The textbook math: for f(h) = f_∞ - C·h^p with h_1 = 4, h_2 =
    2, h_3 = 1 (r = 2), p = 1, C = 1, f_∞ = 1:
        f_1 = 1 - 4 = -3
        f_2 = 1 - 2 = -1
        f_3 = 1 - 1 = 0
    Richardson should recover p = 1 and f_∞ = 1 exactly.
    """

    def test_textbook_p1_recovery(self) -> None:
        est = richardson_extrapolate(
            h_sizes=[4.0, 2.0, 1.0],
            observed_values=[-3.0, -1.0, 0.0],
            analytical_value=1.0,
        )
        assert est.extrapolated_value == pytest.approx(1.0, abs=1e-12)
        assert est.observed_order_p == pytest.approx(1.0, abs=1e-12)
        assert est.refinement_ratio_r == pytest.approx(2.0, abs=1e-12)
        assert est.refinement_ratio_constant is True
        assert est.extrapolated_residual_pct == pytest.approx(0.0, abs=1e-9)

    def test_textbook_p2_recovery(self) -> None:
        # f(h) = 1 - h^2 with r=2, h=4/2/1 → f = -15, -3, 0
        est = richardson_extrapolate(
            h_sizes=[4.0, 2.0, 1.0],
            observed_values=[-15.0, -3.0, 0.0],
            analytical_value=1.0,
        )
        assert est.extrapolated_value == pytest.approx(1.0, abs=1e-12)
        assert est.observed_order_p == pytest.approx(2.0, abs=1e-12)

    def test_non_constant_ratio_flag_set(self) -> None:
        # h = 12, 8, 5 → r_12 = 1.5, r_23 = 1.6 (~7% delta → > 5%)
        est = richardson_extrapolate(
            h_sizes=[12.0, 8.0, 5.0],
            observed_values=[10.0, 8.0, 6.5],
            analytical_value=None,
        )
        assert est.refinement_ratio_constant is False
        assert est.refinement_ratio_r == pytest.approx(1.6, abs=1e-12)
        assert "non-constant" in est.notes.lower()

    def test_constant_ratio_flag_when_within_5pct(self) -> None:
        # r_12 = 2.0, r_23 = 2.04 → ~2% delta → constant
        est = richardson_extrapolate(
            h_sizes=[4.08, 2.04, 1.0],
            observed_values=[-3.0, -1.0, 0.0],
            analytical_value=None,
        )
        assert est.refinement_ratio_constant is True
        # When ratio ~constant: r = avg of r_12 and r_23
        assert est.refinement_ratio_r == pytest.approx(
            (4.08 / 2.04 + 2.04 / 1.0) / 2.0, abs=1e-12
        )

    def test_non_monotone_returns_none(self) -> None:
        # f_1 < f_2 > f_3 → convergence reverses → no asymptotic order
        est = richardson_extrapolate(
            h_sizes=[4.0, 2.0, 1.0],
            observed_values=[1.0, 2.0, 1.5],
            analytical_value=1.0,
        )
        assert est.extrapolated_value is None
        assert est.observed_order_p is None
        assert est.extrapolated_residual_pct is None
        assert "convergence reverses" in est.notes.lower()

    def test_division_by_zero_returns_none(self) -> None:
        # f_2 == f_3 → diff_23 == 0 → cannot estimate p
        est = richardson_extrapolate(
            h_sizes=[4.0, 2.0, 1.0],
            observed_values=[1.0, 0.5, 0.5],
            analytical_value=1.0,
        )
        assert est.extrapolated_value is None
        assert est.observed_order_p is None
        assert "noise floor" in est.notes.lower()

    def test_rejects_wrong_length(self) -> None:
        with pytest.raises(ValueError, match="exactly 3 points"):
            richardson_extrapolate(
                h_sizes=[4.0, 2.0],
                observed_values=[-3.0, -1.0],
                analytical_value=1.0,
            )
        with pytest.raises(ValueError, match="exactly 3 points"):
            richardson_extrapolate(
                h_sizes=[4.0, 2.0, 1.0],
                observed_values=[-3.0, -1.0],
                analytical_value=1.0,
            )

    def test_rejects_non_decreasing_h(self) -> None:
        with pytest.raises(ValueError, match="strictly decreasing"):
            richardson_extrapolate(
                h_sizes=[1.0, 2.0, 4.0],  # increasing — wrong order
                observed_values=[0.0, -1.0, -3.0],
                analytical_value=1.0,
            )
        with pytest.raises(ValueError, match="strictly decreasing"):
            richardson_extrapolate(
                h_sizes=[4.0, 4.0, 1.0],  # equal coarse/mid
                observed_values=[-3.0, -3.0, 0.0],
                analytical_value=1.0,
            )

    def test_no_analytical_no_residual(self) -> None:
        est = richardson_extrapolate(
            h_sizes=[4.0, 2.0, 1.0],
            observed_values=[-3.0, -1.0, 0.0],
            analytical_value=None,
        )
        assert est.extrapolated_value == pytest.approx(1.0, abs=1e-12)
        assert est.extrapolated_residual_pct is None

    def test_signed_residual_preserved(self) -> None:
        # f_∞ overshoots analytical → positive residual
        est = richardson_extrapolate(
            h_sizes=[4.0, 2.0, 1.0],
            observed_values=[-3.0, -1.0, 0.0],
            analytical_value=0.9,  # truth is 0.9; Richardson predicts 1.0
        )
        assert est.extrapolated_residual_pct == pytest.approx(
            (1.0 - 0.9) / 0.9 * 100.0, abs=1e-9
        )


# ────────────────────────────────────────────────────────────────────
# 2. compute_richardson_from_artifact helper (sign-alignment)
# ────────────────────────────────────────────────────────────────────


def _mk_artifact(
    case_id: str,
    refinement_param_name: str,
    points_data: list[tuple[float | int, int, int, float, float, float, str, str]],
) -> ConvergenceArtifact:
    """Helper to construct a minimal ConvergenceArtifact for tests."""
    points = tuple(
        ConvergencePoint(
            label=label,
            refinement_param=rp,
            node_count=nc,
            element_count=ec,
            observed_value=obs,
            analytical_value=ana,
            residual_pct=res,
            verdict=v,
        )
        for (rp, nc, ec, obs, ana, res, v, label) in points_data
    )
    return ConvergenceArtifact(
        case_id=case_id,
        refinement_param_name=refinement_param_name,
        refinement_units="-",
        points=points,
        trend_monotone=True,
        generated_at_utc="2026-05-18T00:00:00+00:00",
        notes="",
    )


class TestComputeRichardsonFromArtifact:
    def test_returns_none_for_fewer_than_three_points(self) -> None:
        art = _mk_artifact(
            "x",
            "n_per_side",
            [
                (10, 100, 100, 1.0, 1.0, 0.0, "PASS", "lo"),
                (20, 200, 200, 1.0, 1.0, 0.0, "PASS", "mid"),
            ],
        )
        assert compute_richardson_from_artifact(art, "param_inverse_to_h") is None

    def test_raises_on_divergent_analyticals(self) -> None:
        art = _mk_artifact(
            "x",
            "n_per_side",
            [
                (10, 100, 100, 1.0, 1.0, 0.0, "PASS", "lo"),
                (20, 200, 200, 1.0, 1.1, 0.0, "PASS", "mid"),
                (40, 400, 400, 1.0, 1.0, 0.0, "PASS", "hi"),
            ],
        )
        with pytest.raises(ValueError, match="divergent analytical"):
            compute_richardson_from_artifact(art, "param_inverse_to_h")

    def test_param_inverse_to_h_uses_reciprocal(self) -> None:
        # n_per_side: n=10/20/40 → h = 1/10, 1/20, 1/40 → ratio = 2
        # Mimic linear convergence: f = f_∞ - C·h^p with f_∞=1, C=1, p=1
        # f(1/10) = 1 - 0.1 = 0.9
        # f(1/20) = 1 - 0.05 = 0.95
        # f(1/40) = 1 - 0.025 = 0.975
        art = _mk_artifact(
            "x",
            "n_per_side",
            [
                (10, 100, 100, 0.9, 1.0, -10.0, "PASS", "lo"),
                (20, 400, 400, 0.95, 1.0, -5.0, "PASS", "mid"),
                (40, 1600, 1600, 0.975, 1.0, -2.5, "PASS", "hi"),
            ],
        )
        est = compute_richardson_from_artifact(art, "param_inverse_to_h")
        assert est is not None
        assert est.extrapolated_value == pytest.approx(1.0, abs=1e-9)
        assert est.observed_order_p == pytest.approx(1.0, abs=1e-9)
        assert est.refinement_ratio_r == pytest.approx(2.0, abs=1e-12)

    def test_sign_alignment_for_opposite_conventions(self) -> None:
        # Observed positive, analytical negative (plate-ss-shell pattern):
        # the helper should align the analytical sign to match observed
        # convention before computing residual.
        art = _mk_artifact(
            "x",
            "n_per_side",
            [
                (10, 100, 100, 0.9, -1.0, -10.0, "PASS", "lo"),
                (20, 400, 400, 0.95, -1.0, -5.0, "PASS", "mid"),
                (40, 1600, 1600, 0.975, -1.0, -2.5, "PASS", "hi"),
            ],
        )
        est = compute_richardson_from_artifact(art, "param_inverse_to_h")
        # f_∞ should be positive (Richardson preserves observed seq sign)
        assert est.extrapolated_value == pytest.approx(1.0, abs=1e-9)
        # residual is computed against |analytical| = 1.0
        assert est.extrapolated_residual_pct == pytest.approx(0.0, abs=1e-9)


# ────────────────────────────────────────────────────────────────────
# 3. plate-ss-shell richardson section pin (schema 1.1.0)
# ────────────────────────────────────────────────────────────────────


class TestPlateSSShellRichardson:
    @pytest.fixture
    def payload(self) -> dict:
        path = (
            GOLDEN_ROOT
            / "plate-ss-shell-candidate"
            / "convergence_study.json"
        )
        return json.loads(path.read_text(encoding="utf-8"))

    def test_schema_v110_pin(self, payload: dict) -> None:
        assert payload["schema_version"] == "1.1.0"

    def test_richardson_field_present(self, payload: dict) -> None:
        assert "richardson" in payload
        assert payload["richardson"] is not None

    def test_extrapolated_value_pin(self, payload: dict) -> None:
        # 6-digit precision pin against the Richardson math output.
        assert payload["richardson"]["extrapolated_value"] == pytest.approx(
            0.000267370, abs=1e-9
        )

    def test_observed_order_p_pin(self, payload: dict) -> None:
        # Empirically ~2.48 — close to but distinct from S4's
        # theoretical p=2 for bending; super-convergence on this
        # particular problem.
        assert payload["richardson"]["observed_order_p"] == pytest.approx(
            2.4804, abs=1e-3
        )

    def test_refinement_ratio_r_pin(self, payload: dict) -> None:
        # n=10/20/40 → h ratio = 2 exactly
        assert payload["richardson"]["refinement_ratio_r"] == 2.0

    def test_refinement_ratio_constant_true(self, payload: dict) -> None:
        # r_12 = r_23 = 2.0 exactly
        assert payload["richardson"]["refinement_ratio_constant"] is True

    def test_extrapolated_residual_pct_pins_asymptotic_bias(
        self, payload: dict
    ) -> None:
        # The KEY honest finding: Richardson predicts f_∞ ≈ +1.31%
        # off the analytical reference. This CONFIRMS the Phase 30 D
        # asymptotic-bias hypothesis. If a future runner change
        # eliminates the bias, this test will trip and the maintainer
        # should re-verify the S4 implementation.
        assert payload["richardson"][
            "extrapolated_residual_pct"
        ] == pytest.approx(1.3149, abs=1e-3)

    def test_richardson_notes_explain_asymptotic_bias(
        self, payload: dict
    ) -> None:
        notes = payload["richardson"]["notes"].lower()
        assert "asymptotic" in notes
        assert "bias" in notes

    def test_recompute_matches_stored_richardson(self, payload: dict) -> None:
        """Re-run Richardson from the points and assert exact agreement
        with the stored values — D:-3 audit trail."""
        points = tuple(
            ConvergencePoint(
                label=p["label"],
                refinement_param=p["refinement_param"],
                node_count=p["node_count"],
                element_count=p["element_count"],
                observed_value=p["observed_value"],
                analytical_value=p["analytical_value"],
                residual_pct=p["residual_pct"],
                verdict=p["verdict"],
            )
            for p in payload["points"]
        )
        artifact = ConvergenceArtifact(
            case_id=payload["case_id"],
            refinement_param_name=payload["refinement_param_name"],
            refinement_units=payload["refinement_units"],
            points=points,
            trend_monotone=payload["trend_monotone"],
            generated_at_utc=payload["generated_at_utc"],
            notes=payload["notes"],
        )
        est = compute_richardson_from_artifact(
            artifact, "param_inverse_to_h"
        )
        assert est is not None
        assert est.extrapolated_value == pytest.approx(
            payload["richardson"]["extrapolated_value"], rel=1e-12
        )
        assert est.observed_order_p == pytest.approx(
            payload["richardson"]["observed_order_p"], rel=1e-12
        )
        assert est.extrapolated_residual_pct == pytest.approx(
            payload["richardson"]["extrapolated_residual_pct"], rel=1e-12
        )


# ────────────────────────────────────────────────────────────────────
# 4. cantilever-beam-modal richardson section pin (schema 1.1.0)
# ────────────────────────────────────────────────────────────────────


class TestCantileverModalRichardson:
    @pytest.fixture
    def payload(self) -> dict:
        path = (
            GOLDEN_ROOT
            / "cantilever-beam-modal-candidate"
            / "convergence_study.json"
        )
        return json.loads(path.read_text(encoding="utf-8"))

    def test_schema_v110_pin(self, payload: dict) -> None:
        assert payload["schema_version"] == "1.1.0"

    def test_richardson_field_present(self, payload: dict) -> None:
        assert "richardson" in payload
        assert payload["richardson"] is not None

    def test_extrapolated_value_pin(self, payload: dict) -> None:
        # f_∞ ≈ 66.861 Hz vs analytical 66.84133 Hz → +0.030% residual.
        assert payload["richardson"]["extrapolated_value"] == pytest.approx(
            66.86149, abs=1e-4
        )

    def test_observed_order_p_pin(self, payload: dict) -> None:
        # Empirical p ~0.69 — low; honestly flagged as a side-effect of
        # the non-constant refinement ratio, NOT a physical anomaly.
        assert payload["richardson"]["observed_order_p"] == pytest.approx(
            0.6884, abs=1e-3
        )

    def test_refinement_ratio_r_pin(self, payload: dict) -> None:
        # Non-constant: r_12 = 1.5, r_23 = 1.6. Generalized form
        # stores r = r_23 = 1.6.
        assert payload["richardson"]["refinement_ratio_r"] == pytest.approx(
            1.6, abs=1e-9
        )

    def test_refinement_ratio_constant_false(self, payload: dict) -> None:
        # 1.5 vs 1.6 → ~7% delta > 5% tolerance → flagged non-constant.
        assert payload["richardson"]["refinement_ratio_constant"] is False

    def test_extrapolated_residual_pct_near_zero(self, payload: dict) -> None:
        # Honest result: Richardson predicts asymptotic convergence to
        # essentially the Euler-Bernoulli analytical (0.030% bias).
        assert payload["richardson"][
            "extrapolated_residual_pct"
        ] == pytest.approx(0.0302, abs=1e-3)
        # NOT zero (we're not gaming) but well below the 0.5% Phase
        # 30 A modal tolerance envelope.
        assert (
            abs(payload["richardson"]["extrapolated_residual_pct"])
            < 0.5
        )

    def test_richardson_notes_flag_non_constant_ratio(
        self, payload: dict
    ) -> None:
        notes = payload["richardson"]["notes"].lower()
        assert "non-constant" in notes
        assert "r_12=1.5000" in notes or "1.5" in notes
        assert "r_23=1.6000" in notes or "1.6" in notes

    def test_recompute_matches_stored_richardson(self, payload: dict) -> None:
        """D:-3: re-run Richardson from the points and assert exact
        agreement with the stored values."""
        points = tuple(
            ConvergencePoint(
                label=p["label"],
                refinement_param=p["refinement_param"],
                node_count=p["node_count"],
                element_count=p["element_count"],
                observed_value=p["observed_value"],
                analytical_value=p["analytical_value"],
                residual_pct=p["residual_pct"],
                verdict=p["verdict"],
            )
            for p in payload["points"]
        )
        artifact = ConvergenceArtifact(
            case_id=payload["case_id"],
            refinement_param_name=payload["refinement_param_name"],
            refinement_units=payload["refinement_units"],
            points=points,
            trend_monotone=payload["trend_monotone"],
            generated_at_utc=payload["generated_at_utc"],
            notes=payload["notes"],
        )
        est = compute_richardson_from_artifact(artifact, "param_is_h")
        assert est is not None
        assert est.extrapolated_value == pytest.approx(
            payload["richardson"]["extrapolated_value"], rel=1e-12
        )
        assert est.observed_order_p == pytest.approx(
            payload["richardson"]["observed_order_p"], rel=1e-12
        )
        assert est.extrapolated_residual_pct == pytest.approx(
            payload["richardson"]["extrapolated_residual_pct"], rel=1e-12
        )


# ────────────────────────────────────────────────────────────────────
# 5. Schema 1.1.0 round-trip via write_convergence_artifact
# ────────────────────────────────────────────────────────────────────


class TestSchema110RoundTrip:
    def test_write_emits_richardson_null_when_no_estimate(
        self, tmp_path: Path
    ) -> None:
        from app.services.cross_check.convergence_study import (
            run_convergence_study,
            write_convergence_artifact,
        )

        def _mk_pt(obs: float, n: int) -> ConvergencePoint:
            return ConvergencePoint(
                label=f"n={n}",
                refinement_param=n,
                node_count=n * n,
                element_count=(n - 1) * (n - 1),
                observed_value=obs,
                analytical_value=2.0,
                residual_pct=(obs - 2.0) / 2.0 * 100,
                verdict="PASS",
            )

        # No richardson supplied → schema 1.1.0 still emitted, field is null.
        artifact = run_convergence_study(
            case_id="x",
            refinement_param_name="n_per_side",
            refinement_units="-",
            runner_callable=lambda v: _mk_pt(2.0 - v * 0.01, n=int(v)),
            param_values=[10, 20, 40],
            notes="",
        )
        out = write_convergence_artifact(tmp_path, artifact)
        payload = json.loads(out.read_text(encoding="utf-8"))
        assert payload["schema_version"] == "1.1.0"
        assert "richardson" in payload
        assert payload["richardson"] is None

    def test_write_emits_richardson_payload_when_supplied(
        self, tmp_path: Path
    ) -> None:
        from app.services.cross_check.convergence_study import (
            run_convergence_study,
            write_convergence_artifact,
        )

        def _mk_pt(obs: float, n: int) -> ConvergencePoint:
            return ConvergencePoint(
                label=f"n={n}",
                refinement_param=n,
                node_count=n * n,
                element_count=(n - 1) * (n - 1),
                observed_value=obs,
                analytical_value=2.0,
                residual_pct=(obs - 2.0) / 2.0 * 100,
                verdict="PASS",
            )

        base = run_convergence_study(
            case_id="x",
            refinement_param_name="n_per_side",
            refinement_units="-",
            runner_callable=lambda v: _mk_pt(2.0 - v * 0.01, n=int(v)),
            param_values=[10, 20, 40],
            notes="",
        )
        # Attach a richardson estimate (synthetic but well-formed).
        richardson = RichardsonEstimate(
            extrapolated_value=1.99,
            observed_order_p=1.5,
            refinement_ratio_r=2.0,
            refinement_ratio_constant=True,
            extrapolated_residual_pct=-0.5,
            notes="synthetic",
        )
        artifact = ConvergenceArtifact(
            case_id=base.case_id,
            refinement_param_name=base.refinement_param_name,
            refinement_units=base.refinement_units,
            points=base.points,
            trend_monotone=base.trend_monotone,
            generated_at_utc=base.generated_at_utc,
            notes=base.notes,
            richardson=richardson,
        )
        out = write_convergence_artifact(tmp_path, artifact)
        payload = json.loads(out.read_text(encoding="utf-8"))
        assert payload["schema_version"] == "1.1.0"
        assert payload["richardson"]["extrapolated_value"] == 1.99
        assert payload["richardson"]["observed_order_p"] == 1.5
        assert payload["richardson"]["refinement_ratio_r"] == 2.0
        assert payload["richardson"]["refinement_ratio_constant"] is True
        assert payload["richardson"]["extrapolated_residual_pct"] == -0.5
        assert payload["richardson"]["notes"] == "synthetic"
