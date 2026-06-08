#!/usr/bin/env python3
"""Export Tier 1 candidate report packet (FM-04a Phase 2 E).

Tier 1 engineering candidate. Not signed validation. Not benchmark
agreement.

Reads the candidate evidence on disk for one case and writes both
`<case-id>_Tier1_candidate_report.md` and `_Tier1_candidate_report.docx`
under `reports/` (or any user-provided output dir). Refuses writes
under `golden_samples/**`.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT_DEFAULT = Path(__file__).resolve().parents[1]


def _ensure_backend_path(repo_root: Path) -> None:
    backend = (repo_root / "backend").resolve()
    if backend.is_dir() and str(backend) not in sys.path:
        sys.path.insert(0, str(backend))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Export a Tier 1 candidate report packet for one case "
            "from existing project_state evidence."
        )
    )
    parser.add_argument(
        "--case-id",
        required=True,
        help=(
            "Case id (used to locate ballistic_metrics.json + convergence_study.json "
            "+ animation manifest + result_mesh.json under project_state/)."
        ),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help=(
            "Output directory (defaults to reports/). Refuses paths under "
            "golden_samples/**."
        ),
    )
    parser.add_argument(
        "--starter-deck-relpath",
        default=None,
        help="Optional repo-relative path to the starter deck used for the case.",
    )
    parser.add_argument(
        "--engine-deck-relpath",
        default=None,
        help="Optional repo-relative path to the engine deck used for the case.",
    )
    parser.add_argument(
        "--generator-script-relpath",
        default=None,
        help="Optional repo-relative path to the deck generator script.",
    )
    parser.add_argument(
        "--notes",
        default=None,
        help="Optional free-text note attached to the report packet.",
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=REPO_ROOT_DEFAULT,
        help="Repository root.",
    )

    args = parser.parse_args(argv)
    _ensure_backend_path(args.repo_root)

    from app.services.reporting.tier1_candidate_report import (  # noqa: E402
        Tier1CandidateReportInputs,
        build_tier1_candidate_report,
        write_tier1_report_artifacts,
    )

    metrics_path = (
        args.repo_root
        / "project_state"
        / "graph_executor"
        / args.case_id
        / "ballistic"
        / "ballistic_metrics.json"
    )
    if not metrics_path.is_file():
        print(
            f"error: ballistic_metrics.json not found at {metrics_path}",
            file=sys.stderr,
        )
        return 1

    convergence_path = (
        args.repo_root
        / "project_state"
        / "graph_executor"
        / args.case_id
        / "convergence"
        / "convergence_study.json"
    )
    blueprint_path = (
        args.repo_root
        / "docs"
        / "visualization"
        / "blueprints"
        / "bullet_plate_target_blueprint.png"
    )
    animation_manifest_path = (
        args.repo_root
        / "project_state"
        / "graph_executor"
        / args.case_id
        / "visualization"
        / "openradioss_animation_manifest.json"
    )
    result_mesh_path = (
        args.repo_root
        / "project_state"
        / "visualizations"
        / args.case_id
        / "result_mesh.json"
    )

    inputs = Tier1CandidateReportInputs(
        case_id=args.case_id,
        ballistic_metrics_path=metrics_path,
        convergence_study_path=(
            convergence_path if convergence_path.is_file() else None
        ),
        blueprint_image_path=blueprint_path if blueprint_path.is_file() else None,
        animation_manifest_path=(
            animation_manifest_path if animation_manifest_path.is_file() else None
        ),
        result_mesh_path=result_mesh_path if result_mesh_path.is_file() else None,
        starter_deck_relpath=args.starter_deck_relpath,
        engine_deck_relpath=args.engine_deck_relpath,
        generator_script_relpath=args.generator_script_relpath,
        notes=args.notes,
        repo_root=args.repo_root,
    )
    report = build_tier1_candidate_report(inputs)
    output_dir = args.output_dir or (args.repo_root / "reports")
    paths = write_tier1_report_artifacts(report, output_dir)
    print(f"markdown: {paths['markdown']}")
    print(f"docx:     {paths['docx']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
