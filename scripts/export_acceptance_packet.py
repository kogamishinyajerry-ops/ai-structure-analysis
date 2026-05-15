#!/usr/bin/env python3
"""Export Tier 1 candidate acceptance evidence packet (FM-04a Phase 3 A).

Tier 1 engineering candidate. Not signed validation. Not benchmark
agreement. Not a sealed Tier 2 bundle.

Builds and writes `<case-id>_acceptance_packet.json` from on-disk
evidence under `project_state/` for one candidate case. Output lands
in `reports/` by default; refuses writes under `golden_samples/**`.
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
            "Export the Tier 1 candidate acceptance evidence packet for one "
            "case from existing project_state evidence."
        )
    )
    parser.add_argument("--case-id", required=True, help="Case id.")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Output dir (defaults to reports/). Refuses golden_samples/** paths.",
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=REPO_ROOT_DEFAULT,
        help="Repository root.",
    )
    args = parser.parse_args(argv)

    _ensure_backend_path(args.repo_root)
    from app.services.reporting.acceptance_packet import (  # noqa: E402
        AcceptancePacketInputs,
        build_acceptance_packet,
        write_acceptance_packet,
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
    starter_deck = (
        args.repo_root / "project_state" / "runs" / args.case_id / "data" / "model_00_0000.rad"
    )
    engine_deck = (
        args.repo_root / "project_state" / "runs" / args.case_id / "data" / "model_00_0001.rad"
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
        args.repo_root / "project_state" / "visualizations" / args.case_id / "result_mesh.json"
    )

    inputs = AcceptancePacketInputs(
        case_id=args.case_id,
        ballistic_metrics_path=metrics_path,
        convergence_study_path=(convergence_path if convergence_path.is_file() else None),
        starter_deck_path=starter_deck if starter_deck.is_file() else None,
        engine_deck_path=engine_deck if engine_deck.is_file() else None,
        blueprint_image_path=blueprint_path if blueprint_path.is_file() else None,
        animation_manifest_path=(
            animation_manifest_path if animation_manifest_path.is_file() else None
        ),
        result_mesh_path=result_mesh_path if result_mesh_path.is_file() else None,
        repo_root=args.repo_root,
    )
    packet = build_acceptance_packet(inputs)
    output_dir = args.output_dir or (args.repo_root / "reports")
    path = write_acceptance_packet(packet, output_dir)
    print(f"acceptance packet: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
