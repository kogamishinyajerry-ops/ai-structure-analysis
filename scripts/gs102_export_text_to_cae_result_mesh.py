#!/usr/bin/env python3
"""Export GS-102 OpenRadioss frames to Text-to-CAE-style viewer artifacts.

Writes ``result_mesh.json`` and per-frame VTU sidecars under
``project_state/visualizations/<case_id>/`` by default. Claim tier remains
Tier 1 engineering candidate; the output is not signed validation and not
benchmark agreement.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT_DEFAULT = Path(__file__).resolve().parents[1]


def _ensure_backend_path(repo_root: Path) -> None:
    backend = repo_root / "backend"
    for candidate in (str(backend), str(repo_root)):
        if candidate not in sys.path:
            sys.path.insert(0, candidate)


def _relative_parts(path: Path, repo_root: Path) -> tuple[str, ...]:
    try:
        return path.resolve().relative_to(repo_root.resolve()).parts
    except ValueError:
        return path.resolve().parts


def _assert_safe_output_path(path: Path, repo_root: Path) -> None:
    parts = _relative_parts(path, repo_root)
    if "golden_samples" in parts:
        raise ValueError(f"refuses to write inside golden_samples/**: {path}")
    if "project_state" not in parts:
        raise ValueError(f"visualization output must live under project_state/: {path}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Export OpenRadioss A-frame results to result_mesh.json + VTU sidecars.",
    )
    parser.add_argument("--case-id", required=True)
    parser.add_argument("--run-data-dir", required=True, type=Path)
    parser.add_argument("--repo-root", default=REPO_ROOT_DEFAULT, type=Path)
    parser.add_argument("--rootname", default="model_00")
    parser.add_argument(
        "--field",
        choices=("pressure_proxy", "pressure_delta", "von_mises", "plastic_strain"),
        default="von_mises",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        help="Defaults to <repo-root>/project_state/visualizations/<case-id>.",
    )
    parser.add_argument("--no-vtu", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    repo_root = args.repo_root.resolve()
    _ensure_backend_path(repo_root)

    from app.viz.openradioss_dynamic_result_exporter import export_dynamic_result_mesh

    output_dir = (
        args.output_dir.resolve()
        if args.output_dir is not None
        else repo_root / "project_state" / "visualizations" / args.case_id
    )
    _assert_safe_output_path(output_dir, repo_root)

    result = export_dynamic_result_mesh(
        run_data_dir=args.run_data_dir,
        output_dir=output_dir,
        case_id=args.case_id,
        field=args.field,
        rootname=args.rootname,
        source_root=str(args.run_data_dir),
        write_vtu=not args.no_vtu,
    )
    print(
        json.dumps(
            {
                "case_id": args.case_id,
                "frame_count": result.frame_count,
                "result_mesh": str(result.result_mesh_path),
                "vtu_manifest": str(result.vtu_manifest_path),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
