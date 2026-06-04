#!/usr/bin/env python3
"""FM-04a Phase 21 A — cantilever + plate-with-hole Kirsch cross-check CLI.

Tier 1 → Tier 2 promotion utility for the two Phase 20 candidates that
registered as ``tier_1_candidate`` baselines:
* ``cantilever-beam-candidate`` (registered Phase 20 B).
* ``plate-with-hole-candidate`` (registered Phase 20 C).

Both runners use the Phase 20 C meshed pipeline (real gmsh → C3D4 →
real ccx) with a discipline-appropriate analytical:
* cantilever → Euler-Bernoulli PL³/(3EI).
* plate-with-hole → Howland's K(2a/W) interpolated from Peterson's
  Stress Concentration Factors Table 4.1.

Writes ``cross_check_verdict.yaml`` to each case's ``golden_samples/``
dir on PASS. On next import of :mod:`app.services.reporting._claim_tier`,
the overlay reads the verdict files and promotes both candidates to
``tier_2_validated``.

Usage:

    python scripts/cross_check_phase21a.py
    python scripts/cross_check_phase21a.py --skip cantilever
    python scripts/cross_check_phase21a.py --gmsh /opt/homebrew/bin/gmsh \
                                            --ccx /opt/homebrew/bin/ccx

The script is the canonical Phase 21 A promotion path. Re-running it
overwrites the verdict files with fresh runs (so a future material
swap or geometry edit can refresh the artifact).
"""

from __future__ import annotations

import argparse
import contextlib
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND = REPO_ROOT / "backend"
sys.path.insert(0, str(BACKEND))

from app.services.cross_check import (  # noqa: E402
    run_cantilever_cross_check,
    run_plate_kirsch_cross_check,
    write_cantilever_verdict_yaml,
    write_plate_kirsch_verdict_yaml,
)


def _case_workspace(stack: contextlib.ExitStack, workdir: Path | None, prefix: str) -> Path:
    """Workspace root for a runner: a persistent --workdir if given (artifacts
    survive for downstream consumers, e.g. docs/demo/render_assets.py), else a
    TemporaryDirectory whose cleanup the caller's ExitStack owns (the historical
    default — deleted on exit, byte-identical behavior)."""
    if workdir is not None:
        workdir.mkdir(parents=True, exist_ok=True)
        return workdir
    return Path(stack.enter_context(tempfile.TemporaryDirectory(prefix=prefix)))


def _run_cantilever(
    *,
    ccx_binary: str,
    gmsh_binary: str,
    material_id: str,
    workdir: Path | None = None,
) -> int:
    case_id = "cantilever-beam-candidate"
    case_golden = REPO_ROOT / "golden_samples" / case_id
    src_geo = case_golden / "data" / "cantilever.geo"
    if not src_geo.is_file():
        print(f"error: missing {src_geo}", file=sys.stderr)
        return 2

    with contextlib.ExitStack() as stack:
        base = _case_workspace(stack, workdir, "phase21a-cantilever-")
        case_dir = base / case_id
        case_dir.mkdir(exist_ok=True)
        dst_geo = case_dir / "cantilever.geo"
        dst_geo.write_text(src_geo.read_text(encoding="utf-8"), encoding="utf-8")
        print(
            f"Running cantilever cross-check (L=1.0 m, h=b=0.1 m, "
            f"P=-1000 N, material={material_id!r}, cl=0.015 m)"
        )
        result = run_cantilever_cross_check(
            case_dir,
            case_id=case_id,
            material_id=material_id,
            geometry_path=dst_geo,
            length_m=1.0,
            section_depth_m=0.1,
            section_width_m=0.1,
            tip_load_n=-1000.0,
            characteristic_length_m=0.015,
            ccx_binary=ccx_binary,
            gmsh_binary=gmsh_binary,
            ccx_timeout_sec=240.0,
            gmsh_timeout_sec=180.0,
        )

    print(f"  nodes:      {result.node_count}")
    print(f"  elements:   {result.element_count}")
    print(f"  analytical: {result.analytical_m:.4e} m")
    print(f"  observed:   {result.observed_m:.4e} m")
    print(f"  residual:   {result.residual_pct:+.3f}%")
    print(f"  tolerance:  {result.tolerance_pct}%")
    print(f"  verdict:    {result.verdict}")

    artifact = write_cantilever_verdict_yaml(case_golden, result)
    print(f"  wrote: {artifact}")
    if result.verdict == "PASS":
        print(f"  → next import will promote {case_id!r} to tier_2_validated")
        return 0
    print(f"  → {case_id!r} stays at tier_1_candidate")
    return 1


def _run_plate_kirsch(
    *,
    ccx_binary: str,
    gmsh_binary: str,
    material_id: str,
    workdir: Path | None = None,
) -> int:
    case_id = "plate-with-hole-candidate"
    case_golden = REPO_ROOT / "golden_samples" / case_id
    src_geo = case_golden / "data" / "plate_with_hole.geo"
    if not src_geo.is_file():
        print(f"error: missing {src_geo}", file=sys.stderr)
        return 2

    with contextlib.ExitStack() as stack:
        base = _case_workspace(stack, workdir, "phase21a-kirsch-")
        case_dir = base / case_id
        case_dir.mkdir(exist_ok=True)
        dst_geo = case_dir / "plate_with_hole.geo"
        dst_geo.write_text(src_geo.read_text(encoding="utf-8"), encoding="utf-8")
        print(
            f"Running Kirsch cross-check (L=100, W=50, T=5, R=10 mm; "
            f"F=250 N → σ_∞=1.0 MPa; K≈3.74 at 2a/W=0.4; "
            f"material={material_id!r}, cl=0.003 m)"
        )
        result = run_plate_kirsch_cross_check(
            case_dir,
            case_id=case_id,
            material_id=material_id,
            geometry_path=dst_geo,
            plate_length_m=0.100,
            plate_width_m=0.050,
            plate_thickness_m=0.005,
            hole_radius_m=0.010,
            applied_force_n=250.0,
            characteristic_length_m=0.003,
            ccx_binary=ccx_binary,
            gmsh_binary=gmsh_binary,
            ccx_timeout_sec=240.0,
            gmsh_timeout_sec=180.0,
        )

    print(f"  nodes:        {result.node_count}")
    print(f"  elements:     {result.element_count}")
    print(f"  K (Howland):  {result.kirsch_k}")
    print(f"  σ_∞:          {result.far_field_pa:.3e} Pa")
    print(f"  analytical:   {result.analytical_pa:.3e} Pa")
    print(f"  observed:     {result.observed_pa:.3e} Pa")
    print(f"  residual:     {result.residual_pct:+.3f}%")
    print(f"  tolerance:    {result.tolerance_pct}%")
    print(f"  verdict:      {result.verdict}")

    artifact = write_plate_kirsch_verdict_yaml(case_golden, result)
    print(f"  wrote: {artifact}")
    if result.verdict == "PASS":
        print(f"  → next import will promote {case_id!r} to tier_2_validated")
        return 0
    print(f"  → {case_id!r} stays at tier_1_candidate")
    return 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--ccx",
        default="/opt/homebrew/bin/ccx",
        help="Path to the ccx binary",
    )
    parser.add_argument(
        "--gmsh",
        default="/opt/homebrew/bin/gmsh",
        help="Path to the gmsh binary",
    )
    parser.add_argument(
        "--material-id",
        default="steel-s355",
        help="Material library id (default: steel-s355)",
    )
    parser.add_argument(
        "--workdir",
        type=Path,
        default=None,
        help=(
            "Persistent workspace for solver artifacts (mesh/.inp/.frd). "
            "Default: a TemporaryDirectory deleted on exit. Pass a path to "
            "keep artifacts, e.g. for docs/demo/render_assets.py."
        ),
    )
    parser.add_argument(
        "--skip",
        choices=["cantilever", "plate"],
        action="append",
        default=[],
        help="Skip one of the runners (can be passed multiple times)",
    )
    args = parser.parse_args()

    rcs: list[int] = []
    if "cantilever" not in args.skip:
        rcs.append(
            _run_cantilever(
                ccx_binary=args.ccx,
                gmsh_binary=args.gmsh,
                material_id=args.material_id,
                workdir=args.workdir,
            )
        )
    if "plate" not in args.skip:
        rcs.append(
            _run_plate_kirsch(
                ccx_binary=args.ccx,
                gmsh_binary=args.gmsh,
                material_id=args.material_id,
                workdir=args.workdir,
            )
        )
    return max(rcs) if rcs else 0


if __name__ == "__main__":
    sys.exit(main())
