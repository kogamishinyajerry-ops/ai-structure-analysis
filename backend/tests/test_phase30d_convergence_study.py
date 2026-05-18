"""FM-04a Phase 30 D — convergence-study module + artifact pins.

Three deliveries pinned:

1. convergence_study module — ConvergencePoint / ConvergenceArtifact
   dataclasses, run_convergence_study orchestrator, monotone-decrease
   predicate, write_convergence_artifact round-trip.

2. plate-ss-shell-candidate convergence_study.json — schema, three
   refinements (n=10/20/40), live-ccx provenance.

3. cantilever-beam-modal-candidate convergence_study.json — schema,
   three refinements (cl=12/8/5 mm), monotone-decreasing residual.

Honest scope (Phase 30 D):
* cylinder-pv-candidate is DEFERRED — no tunable mesh parameter in
  the runner. Pinned by `test_cylinder_pv_convergence_deferred`
  which checks the artifact ABSENCE is documented (not as a missing
  artifact bug but as a known runner-extension gap).

Tier 1 / Tier 2 engineering candidate; not signed validation; not
benchmark agreement.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from app.services.cross_check.convergence_study import (
    ConvergenceArtifact,
    ConvergencePoint,
    _check_monotone_decreasing,
    read_convergence_artifact,
    run_convergence_study,
    write_convergence_artifact,
)

GOLDEN_ROOT: Path = (
    Path(__file__).resolve().parents[2] / "golden_samples"
)


# ────────────────────────────────────────────────────────────────────
# 1. convergence_study module unit tests
# ────────────────────────────────────────────────────────────────────


def _mk_pt(residual: float, n: int = 100) -> ConvergencePoint:
    return ConvergencePoint(
        label=f"n={n}",
        refinement_param=n,
        node_count=n * 10,
        element_count=n * 8,
        observed_value=1.0,
        analytical_value=1.0,
        residual_pct=residual,
        verdict="PASS",
    )


class TestMonotonePredicate:
    def test_strictly_decreasing_residual_returns_true(self) -> None:
        pts = [_mk_pt(5.0), _mk_pt(2.5), _mk_pt(1.0)]
        assert _check_monotone_decreasing(pts) is True

    def test_residual_growing_returns_false(self) -> None:
        pts = [_mk_pt(1.0), _mk_pt(2.0), _mk_pt(3.0)]
        assert _check_monotone_decreasing(pts) is False

    def test_oscillating_with_overshoot_returns_false(self) -> None:
        # Real plate-ss-shell behavior: -3.3 → +0.5 → +1.2
        # The absolute residual goes 3.3 → 0.5 → 1.2: NOT monotone
        # because |0.5| < |1.2| but |1.2| > |0.5| at the last step.
        pts = [_mk_pt(-3.3), _mk_pt(0.5), _mk_pt(1.2)]
        assert _check_monotone_decreasing(pts) is False

    def test_below_noise_floor_treated_as_monotone(self) -> None:
        # Both residuals are below 1%; a tiny bump doesn't fail.
        pts = [_mk_pt(0.5), _mk_pt(0.6), _mk_pt(0.4)]
        assert _check_monotone_decreasing(pts) is True

    def test_sign_change_ok_if_absolute_decreases(self) -> None:
        # |-2| > |+1| > |+0.3| — monotone in absolute value.
        pts = [_mk_pt(-2.0), _mk_pt(1.0), _mk_pt(0.3)]
        assert _check_monotone_decreasing(pts) is True

    def test_single_point_is_trivially_monotone(self) -> None:
        assert _check_monotone_decreasing([_mk_pt(1.0)]) is True

    def test_empty_list_is_trivially_monotone(self) -> None:
        assert _check_monotone_decreasing([]) is True


class TestRunConvergenceStudy:
    def test_orchestrator_calls_runner_once_per_param_value(self) -> None:
        calls: list[float | int] = []

        def fake_runner(v: float | int) -> ConvergencePoint:
            calls.append(v)
            return _mk_pt(2.0 - len(calls) * 0.5, n=int(v))

        artifact = run_convergence_study(
            case_id="fake-case",
            refinement_param_name="dummy",
            refinement_units="-",
            runner_callable=fake_runner,
            param_values=[10, 20, 40],
            notes="",
        )
        assert calls == [10, 20, 40]
        assert len(artifact.points) == 3

    def test_single_value_raises(self) -> None:
        with pytest.raises(ValueError, match="≥2 refinements"):
            run_convergence_study(
                case_id="x",
                refinement_param_name="-",
                refinement_units="-",
                runner_callable=lambda v: _mk_pt(0),
                param_values=[10],
                notes="",
            )

    def test_runner_returning_non_point_raises(self) -> None:
        with pytest.raises(TypeError, match="ConvergencePoint"):
            run_convergence_study(
                case_id="x",
                refinement_param_name="-",
                refinement_units="-",
                runner_callable=lambda v: "not a point",  # type: ignore
                param_values=[10, 20],
                notes="",
            )

    def test_timestamp_is_iso_utc(self) -> None:
        artifact = run_convergence_study(
            case_id="x",
            refinement_param_name="-",
            refinement_units="-",
            runner_callable=lambda v: _mk_pt(1.0, n=int(v)),
            param_values=[10, 20],
            notes="",
        )
        assert re.match(
            r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d+\+00:00$",
            artifact.generated_at_utc,
        )


class TestWriteArtifact:
    def test_write_then_read_round_trips(self, tmp_path: Path) -> None:
        artifact = run_convergence_study(
            case_id="round-trip-case",
            refinement_param_name="n_per_side",
            refinement_units="elements_per_side",
            runner_callable=lambda v: _mk_pt(2.0 - v * 0.1, n=int(v)),
            param_values=[10, 20, 40],
            notes="unit test",
        )
        out = write_convergence_artifact(tmp_path, artifact)
        assert out.is_file()
        payload = read_convergence_artifact(out)
        # Phase 31 C bumps schema 1.0.0 → 1.1.0 (additive richardson field).
        assert payload["schema_version"] == "1.1.0"
        assert payload["case_id"] == "round-trip-case"
        assert payload["refinement_param_name"] == "n_per_side"
        assert len(payload["points"]) == 3
        assert payload["points"][0]["label"] == "n=10"

    def test_writes_required_field_set(self, tmp_path: Path) -> None:
        artifact = run_convergence_study(
            case_id="x",
            refinement_param_name="-",
            refinement_units="-",
            runner_callable=lambda v: _mk_pt(1.0, n=int(v)),
            param_values=[10, 20],
            notes="",
        )
        out = write_convergence_artifact(tmp_path, artifact)
        payload = json.loads(out.read_text(encoding="utf-8"))
        REQUIRED = {
            "schema_version",
            "case_id",
            "refinement_param_name",
            "refinement_units",
            "trend_monotone",
            "generated_at_utc",
            "notes",
            "points",
        }
        assert REQUIRED.issubset(set(payload.keys()))

    def test_write_to_missing_dir_raises(self, tmp_path: Path) -> None:
        artifact = run_convergence_study(
            case_id="x",
            refinement_param_name="-",
            refinement_units="-",
            runner_callable=lambda v: _mk_pt(1.0, n=int(v)),
            param_values=[10, 20],
            notes="",
        )
        with pytest.raises(FileNotFoundError):
            write_convergence_artifact(tmp_path / "nope", artifact)


# ────────────────────────────────────────────────────────────────────
# 2. plate-ss-shell-candidate convergence artifact pin
# ────────────────────────────────────────────────────────────────────


class TestPlateSSShellArtifact:
    @pytest.fixture
    def payload(self) -> dict:
        path = (
            GOLDEN_ROOT
            / "plate-ss-shell-candidate"
            / "convergence_study.json"
        )
        assert path.is_file(), (
            f"missing convergence_study.json at {path}; "
            f"regenerate via tmp/run_convergence_plate_ss_shell.py"
        )
        return json.loads(path.read_text(encoding="utf-8"))

    def test_schema_version_pinned(self, payload: dict) -> None:
        # Phase 31 C bumps schema 1.0.0 → 1.1.0 (additive richardson field).
        assert payload["schema_version"] == "1.1.0"

    def test_case_id_pinned(self, payload: dict) -> None:
        assert payload["case_id"] == "plate-ss-shell-candidate"

    def test_refinement_param_is_n_per_side(self, payload: dict) -> None:
        assert payload["refinement_param_name"] == "n_per_side"

    def test_three_refinements(self, payload: dict) -> None:
        assert len(payload["points"]) == 3

    def test_refinement_param_values(self, payload: dict) -> None:
        values = [p["refinement_param"] for p in payload["points"]]
        assert values == [10, 20, 40]

    def test_all_points_pass_verdict(self, payload: dict) -> None:
        # E:-1 audit-trail: every refinement was under the 15% Phase
        # 29 A tolerance envelope. PASSes across the trend.
        for pt in payload["points"]:
            assert pt["verdict"] == "PASS"

    def test_all_residuals_under_tier2_envelope(self, payload: dict) -> None:
        # Phase 29 A tolerance is 15%; the convergence sweep should
        # stay well under that even at the coarsest mesh.
        for pt in payload["points"]:
            assert abs(pt["residual_pct"]) < 15.0

    def test_trend_monotone_flag_set_honestly(self, payload: dict) -> None:
        # The S4 element + Mindlin thick-shell kinematics produces
        # non-monotone convergence (crosses zero between lo and mid,
        # overshoots at hi). The artifact records this HONESTLY as
        # trend_monotone=false. If a future runner change makes the
        # trend monotone, this test will trip and the maintainer
        # should re-verify the artifact wasn't fudged.
        assert payload["trend_monotone"] is False

    def test_node_counts_strictly_increase(self, payload: dict) -> None:
        nodes = [p["node_count"] for p in payload["points"]]
        assert nodes == sorted(nodes)
        assert len(set(nodes)) == 3  # all distinct


# ────────────────────────────────────────────────────────────────────
# 3. cantilever-beam-modal-candidate convergence artifact pin
# ────────────────────────────────────────────────────────────────────


class TestCantileverModalArtifact:
    @pytest.fixture
    def payload(self) -> dict:
        path = (
            GOLDEN_ROOT
            / "cantilever-beam-modal-candidate"
            / "convergence_study.json"
        )
        assert path.is_file(), (
            f"missing convergence_study.json at {path}; "
            f"regenerate via tmp/run_convergence_cantilever_modal.py"
        )
        return json.loads(path.read_text(encoding="utf-8"))

    def test_schema_version_pinned(self, payload: dict) -> None:
        # Phase 31 C bumps schema 1.0.0 → 1.1.0 (additive richardson field).
        assert payload["schema_version"] == "1.1.0"

    def test_case_id_pinned(self, payload: dict) -> None:
        assert payload["case_id"] == "cantilever-beam-modal-candidate"

    def test_refinement_param_is_characteristic_length(
        self, payload: dict
    ) -> None:
        assert payload["refinement_param_name"] == "characteristic_length_m"

    def test_three_refinements(self, payload: dict) -> None:
        assert len(payload["points"]) == 3

    def test_refinement_param_values(self, payload: dict) -> None:
        # 12 / 8 / 5 mm — chosen so all three produce DISTINCT meshes
        # below the .geo's hard-coded cl=0.012 floor.
        values = [p["refinement_param"] for p in payload["points"]]
        assert values == [0.012, 0.008, 0.005]

    def test_trend_monotone_decreasing(self, payload: dict) -> None:
        # C3D10 + gmsh mesh refinement → monotone decrease in residual.
        # This is the EXPECTED honest behavior for a well-conditioned
        # Euler-Bernoulli eigenvalue problem.
        assert payload["trend_monotone"] is True

    def test_all_points_pass(self, payload: dict) -> None:
        for pt in payload["points"]:
            assert pt["verdict"] == "PASS"

    def test_residual_magnitude_under_tier2_envelope(
        self, payload: dict
    ) -> None:
        # Tolerance is 12%; observed residuals all well below 1%.
        for pt in payload["points"]:
            assert abs(pt["residual_pct"]) < 12.0


# ────────────────────────────────────────────────────────────────────
# 4. cylinder-pv-candidate deferral acknowledgment
# ────────────────────────────────────────────────────────────────────


def test_cylinder_pv_convergence_deferred() -> None:
    """The cylinder-pv-candidate runner does NOT take a tunable mesh
    refinement parameter — its wall-coupon mesh is fixed. Phase 30 D
    HONESTLY defers convergence for this case rather than fabricating
    one. This test pins the gap so the next maintainer who wants to
    close it has a clear pointer to which file needs extension."""

    # 1. The cylinder runner signature MUST NOT carry a mesh-tunable
    #    parameter today (or else this test is stale).
    import inspect

    from app.services.cross_check.cylinder_pv_runner import (
        run_cylinder_pv_cross_check,
    )

    sig = inspect.signature(run_cylinder_pv_cross_check)
    mesh_params = {"n_per_side", "characteristic_length_m", "n_elements"}
    found = set(sig.parameters.keys()) & mesh_params
    assert not found, (
        f"cylinder_pv_runner now exposes mesh params {found}; "
        f"the Phase 30 D deferral is stale — add a "
        f"cylinder-pv-candidate convergence_study.json and remove "
        f"this test."
    )

    # 2. Document the absence: a convergence_study.json MUST NOT
    #    exist for cylinder-pv until the runner is extended (so we
    #    don't ship a stub artifact with single-mesh data).
    cyl_artifact = (
        GOLDEN_ROOT / "cylinder-pv-candidate" / "convergence_study.json"
    )
    assert not cyl_artifact.exists(), (
        f"cylinder-pv-candidate has a convergence_study.json at "
        f"{cyl_artifact} but the runner has no tunable mesh param. "
        f"Either remove the artifact or extend the runner first."
    )
