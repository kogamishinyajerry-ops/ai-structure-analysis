#!/usr/bin/env python3
"""FM-04a Tier 1 ballistic candidate synthetic pipeline (no OpenRadioss required).

Tier 1 engineering candidate. Not signed validation. Not benchmark agreement.

What this script demonstrates:
    1. Generate a synthetic projectile trajectory + energy audit + mesh
       refinement sweep + time-step refinement sweep.
    2. Drive the FM-04a Tier 1 writers to land sidecars under
       ``project_state/graph_executor/<case>/{ballistic,mesh}/``.
    3. Build the candidate report spine (FM-03 v2) and print the populated
       ballistic block + mesh / dt convergence verdicts.

What this script does NOT do:
    * It does NOT invoke OpenRadioss. The synthetic trajectory is illustrative.
    * It does NOT claim benchmark agreement, signed validation, or any Tier 2
      promotion. ADR-023 forbidden-wording set is enforced in every banner.
    * It does NOT write to ``golden_samples/**``. The synthetic case_id lives
      under ``project_state/`` only.

Usage:
    python3 scripts/fm04a_synthetic_pipeline.py [--case-id CASE-FM04A-DEMO]
        [--repo-root .] [--print-spine]

The script's exit code is 0 when the candidate spine successfully consumes
all three sidecars and reports a ``candidate_observed`` ballistic block;
non-zero otherwise.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT_DEFAULT = Path(__file__).resolve().parents[1]


def _ensure_paths(repo_root: Path) -> None:
    """Make ``backend.app`` importable when this script runs as a CLI."""
    backend = repo_root / "backend"
    for candidate in (str(backend), str(repo_root)):
        if candidate not in sys.path:
            sys.path.insert(0, candidate)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    repo_root = Path(args.repo_root).resolve()
    _ensure_paths(repo_root)

    # imports happen after sys.path adjustment so the script is portable
    from app.parsers.frd_parser import FRDParser  # noqa: E402  (intentional after sys.path)
    from app.services import candidate_report_spine as spine_module  # noqa: E402
    from app.services.ballistics import (  # noqa: E402
        BallisticAnimationInput,
        BallisticEnergyAudit,
        BallisticExtractionInput,
        BallisticTimeSample,
        ConvergenceRun,
        MeshConvergenceInput,
        TimeStepConvergenceInput,
        write_ballistic_animation,
        write_ballistic_metrics,
        write_mesh_convergence,
        write_time_step_convergence,
    )
    from app.services.report_generator import ReportGenerator  # noqa: E402

    case_id = args.case_id
    synthetic_root = repo_root / "project_state" / "synthetic_cases"
    case_dir = synthetic_root / case_id
    runtime_root = repo_root / "project_state" / "graph_executor" / case_id

    print(_banner(case_id))

    # 1. Synthetic case lives under project_state/synthetic_cases/<case_id>/ to keep
    #    the HF1.7 golden_samples/ zone untouched. ReportGenerator is given this path
    #    as its gs_root below so the spine reads the synthetic expected_results.json
    #    without touching any real GS bundle.
    _seed_synthetic_case(case_dir, case_id)

    # 2. Synthesize the projectile trajectory and write ballistic_metrics.json
    samples = [
        BallisticTimeSample(
            t_s=0.0, position_m=(-0.05, 0.0, 0.0), velocity_m_per_s=(285.0, 0.0, 0.0)
        ),
        BallisticTimeSample(
            t_s=2.0e-4, position_m=(0.06, 0.0, 0.0), velocity_m_per_s=(142.0, 0.0, 0.0)
        ),
    ]
    extraction_input = BallisticExtractionInput(
        case_id=case_id,
        projectile_mass_kg=0.020,
        plate_back_face_x_m=0.012,
        plate_thickness_m=0.012,
        samples=samples,
        energy_audit=BallisticEnergyAudit(
            initial_kinetic_energy_j=812.0,
            plastic_dissipation_j=540.0,
            contact_friction_j=40.0,
            hourglass_energy_j=20.0,
            residual_kinetic_energy_j=212.0,
        ),
    )
    ballistic_dir = runtime_root / "ballistic"
    metrics_path = write_ballistic_metrics(extraction_input, ballistic_dir)
    print(f"  - wrote ballistic_metrics.json: {metrics_path.relative_to(repo_root)}")

    # 3. Synthetic time-step refinement sweep
    write_time_step_convergence(
        TimeStepConvergenceInput(
            case_id=case_id,
            metric="residual_velocity_candidate_m_per_s",
            runs=[
                ConvergenceRun("dt_baseline", 8.0e-9, 142.0),
                ConvergenceRun("dt_half", 4.0e-9, 141.0),
                ConvergenceRun("dt_quarter", 2.0e-9, 140.5),
            ],
            tolerance_pct=5.0,
            notes="synthetic candidate sweep; not benchmark agreement",
        ),
        ballistic_dir,
    )
    print(
        f"  - wrote time_step_convergence.json: "
        f"{(ballistic_dir / 'time_step_convergence.json').relative_to(repo_root)}"
    )

    # 4. Synthetic mesh refinement sweep
    mesh_dir = runtime_root / "mesh"
    write_mesh_convergence(
        MeshConvergenceInput(
            case_id=case_id,
            metric="max_plastic_strain",
            runs=[
                ConvergenceRun("coarse", 0.0, 0.42),
                ConvergenceRun("medium", 1.0, 0.435),
                ConvergenceRun("fine", 2.0, 0.438),
            ],
            tolerance_pct=5.0,
        ),
        mesh_dir,
    )
    print(
        f"  - wrote mesh_convergence.json: "
        f"{(mesh_dir / 'mesh_convergence.json').relative_to(repo_root)}"
    )

    # 4b. Optional Tier 1 candidate animation (side-view kinematic sketch).
    #     Written before the spine call so the spine picks up the manifest
    #     and surfaces it in animation_manifest as "available".
    if args.write_animation:
        anim_manifest_path = write_ballistic_animation(
            BallisticAnimationInput(
                case_id=case_id,
                samples=samples,
                plate_back_face_x_m=0.012,
                plate_thickness_m=0.012,
            ),
            ballistic_dir,
        )
        print(f"  - wrote animation_manifest.json: {anim_manifest_path.relative_to(repo_root)}")
        print(
            f"  - wrote candidate_animation.gif: "
            f"{(ballistic_dir / 'candidate_animation.gif').relative_to(repo_root)}"
        )

    # 5. Drive the spine through ReportGenerator using a real GS-001 FRD as the parsed
    #    input. The spine reads expected_results.json from the synthetic case dir;
    #    ballistic / mesh sidecars from runtime_root.
    frd_path = repo_root / "golden_samples" / "GS-001" / "gs001_result.frd"
    if not frd_path.exists():
        print(f"\nERROR: reference FRD missing: {frd_path}", file=sys.stderr)
        return 2

    # Re-target the spine module's REPO_ROOT so it discovers our synthetic runtime dir.
    spine_module.REPO_ROOT = repo_root  # type: ignore[attr-defined]

    parsed = FRDParser().parse(str(frd_path))
    report = ReportGenerator(synthetic_root).generate(
        parsed,
        case_id=case_id,
        source_path=frd_path,
        original_filename="gs001_result.frd",
    )

    spine = report.candidate_report_spine
    ballistic = spine["ballistic"]
    mesh_study = spine["mesh_evidence"]["convergence_study"]
    dt_study = ballistic["time_step_convergence_study"]

    # 6. Print the candidate banner + a Tier 1 health summary
    print()
    print("Spine summary")
    print(f"  schema_version       : {spine['schema_version']}")
    print(f"  claim_tier           : {spine['claim_tier']}")
    print(f"  no_overclaim         : {spine['no_overclaim']}")
    print()
    print("Ballistic candidate block")
    print(f"  status               : {ballistic['status']}")
    print(
        f"  V0 / vR              : "
        f"{ballistic['projectile_initial_velocity']['value_m_per_s']} m/s "
        f"-> {ballistic['residual_velocity_candidate']['value_m_per_s']} m/s"
    )
    print(f"  perforation_marker   : {ballistic['perforation_marker']['status']}")
    print(
        f"  energy_ratio         : "
        f"{ballistic['energy_balance_candidate']['energy_ratio']} (Tier 1 health indicator)"
    )
    print(f"  dt convergence       : {dt_study['candidate_stability']}")
    print(f"  mesh convergence     : {mesh_study['candidate_stability']}")
    print()
    print("Tier 2 blockers (always present at Tier 1):")
    for blocker in spine["tier2_blockers"]:
        print(f"  - {blocker}")

    if args.print_spine:
        print()
        print("Full spine payload:")
        print(json.dumps(spine, indent=2, sort_keys=True))

    if args.write_markdown:
        from app.services.candidate_report_markdown import (  # noqa: E402
            render_candidate_report,
        )

        runtime_root.mkdir(parents=True, exist_ok=True)
        md_path = runtime_root / "candidate_report.md"
        md_path.write_text(render_candidate_report(spine), encoding="utf-8")
        print()
        print(f"  - wrote candidate_report.md: {md_path.relative_to(repo_root)}")

    if ballistic["status"] != "candidate_observed":
        print(
            "\nERROR: spine ballistic block is not candidate_observed; pipeline failed.",
            file=sys.stderr,
        )
        return 3
    if dt_study["candidate_stability"] != "candidate_observed_stable":
        print(
            "\nERROR: dt convergence study did not reach candidate_observed_stable;"
            " pipeline failed.",
            file=sys.stderr,
        )
        return 4
    return 0


# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run the FM-04a Tier 1 ballistic candidate synthetic pipeline. "
            "This script does not invoke OpenRadioss and never claims "
            "benchmark agreement or signed validation."
        )
    )
    parser.add_argument(
        "--case-id",
        default="CASE-FM04A-SYNTHETIC",
        help="Synthetic case id (default: CASE-FM04A-SYNTHETIC)",
    )
    parser.add_argument(
        "--repo-root",
        default=str(REPO_ROOT_DEFAULT),
        help="Repository root (default: parent of this script)",
    )
    parser.add_argument(
        "--print-spine",
        action="store_true",
        help="Print the full spine payload as JSON after the summary",
    )
    parser.add_argument(
        "--write-markdown",
        action="store_true",
        help=(
            "Render the candidate spine as a Tier 1 Markdown report and "
            "write it to project_state/graph_executor/<case>/candidate_report.md "
            "(strictly Tier 1; never claims benchmark agreement or signed validation)"
        ),
    )
    parser.add_argument(
        "--write-animation",
        action="store_true",
        help=(
            "Render a Tier 1 side-view kinematic GIF and animation_manifest.json "
            "into project_state/graph_executor/<case>/ballistic/ (illustrative "
            "only; not benchmark agreement; not signed validation)"
        ),
    )
    return parser.parse_args(argv)


def _seed_synthetic_case(case_dir: Path, case_id: str) -> None:
    """Create a synthetic case directory under project_state/synthetic_cases/.

    Never writes under ``golden_samples/`` (HF1.7 zone). The synthetic case
    explicitly carries Tier 1 candidate wording and ``status =
    insufficient_evidence`` so the spine path treats it identically to a
    real engineering-candidate fixture.
    """
    expected_path = case_dir / "expected_results.json"
    if expected_path.exists():
        return
    case_dir.mkdir(parents=True, exist_ok=True)
    expected_path.write_text(
        json.dumps(
            {
                "case_id": case_id,
                "case_name": (
                    "FM-04a Tier 1 synthetic ballistic candidate (NOT signed; "
                    "demo only; not benchmark agreement)"
                ),
                "analysis_type": "explicit_dynamics_ballistic_candidate",
                "status": "insufficient_evidence",
                "status_reason": (
                    "synthetic candidate fixture authored by "
                    "scripts/fm04a_synthetic_pipeline.py; Tier 2 promotion "
                    "deferred to FM-04b"
                ),
                "failure_pattern_ref": "FP-pending-FM-04a",
                "ballistic": {"projectile_initial_velocity_m_per_s": 285.0},
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    (case_dir / "model.inp").write_text(
        "*NODE\n1,0,0,0\n*ELEMENT, TYPE=C3D4\n1,1,1,1,1\n", encoding="utf-8"
    )


def _banner(case_id: str) -> str:
    return (
        f"\nFM-04a Tier 1 candidate synthetic pipeline\n"
        f"  case_id     : {case_id}\n"
        f"  claim_tier  : Tier 1 engineering candidate\n"
        f"  boundary    : not signed validation; not benchmark agreement\n"
        f"  forbidden   : steel perforation completed / bullet-through-steel "
        f"complete / signed GS101 / validated physics\n"
    )


def run_for_test(repo_root: Path, case_id: str) -> dict[str, Any]:
    """Programmatic entry point used by tests; returns the spine payload."""
    rc = main(["--repo-root", str(repo_root), "--case-id", case_id])
    if rc != 0:
        raise RuntimeError(f"synthetic pipeline returned rc={rc}")
    spine_path = (
        repo_root
        / "project_state"
        / "graph_executor"
        / case_id
        / "ballistic"
        / "ballistic_metrics.json"
    )
    return json.loads(spine_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    raise SystemExit(main())
