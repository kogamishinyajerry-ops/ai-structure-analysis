"""Layer-4 report CLI — RFC-001 §3 thin engineer-facing driver.

Exercises the full L1 → L4 stack from a terminal:
  1. Open a CalculiX ``.frd`` via ``CalculiXReader`` (Layer 1)
  2. Pull DISPLACEMENT + STRESS_TENSOR fields (Layer 2)
  3. Compute the templated quantities (Layer 3 derivations)
  4. Build (ReportSpec, EvidenceBundle) (Layer 4 schema)
  5. Validate against the chosen template (Layer 4 templates)
  6. Export DOCX with ADR-012 audit trail (Layer 4 exporter)

Three report kinds are supported, matching the three MVP templates:

  * ``static`` — equipment-foundation static-strength check
  * ``lifting-lug`` — lifting-lug strength assessment under hoist load
  * ``pressure-vessel`` — local stress assessment along an SCL
                         (requires ``--scl-nodes`` + ``--scl-distances``)

Exit codes:
  0  success — DOCX written
  2  argparse / input error
  3  domain refusal (ADR-012 violation, missing field, etc.)
  4  unexpected internal error

The CLI is intentionally thin — every substantive piece of work lives
in the L1-L4 modules. This module's job is *plumbing*: turn argv
strings into typed parameters, surface refusals legibly, and write
the .docx. No engineering decisions hide here.
"""

from __future__ import annotations

import argparse
import sys
import traceback
from pathlib import Path
from typing import List, Optional

from app.adapters.calculix import CalculiXReader
from app.core.types import UnitSystem
from app.models import EvidenceBundle, ReportSpec
from app.services.report.draft import (
    generate_lifting_lug_summary,
    generate_pressure_vessel_local_stress_summary,
    generate_static_strength_summary,
)
from app.services.report.exporter import ExportError, export_docx
from app.services.report.templates import (
    EQUIPMENT_FOUNDATION_STATIC,
    LIFTING_LUG,
    PRESSURE_VESSEL_LOCAL_STRESS,
    TemplateSpec,
    TemplateValidationError,
)


__all__ = ["main", "build_parser"]


_REPORT_KINDS = ("static", "lifting-lug", "pressure-vessel")
_UNIT_SYSTEMS = {
    "si": UnitSystem.SI,
    "si-mm": UnitSystem.SI_MM,
    "english": UnitSystem.ENGLISH,
    "unknown": UnitSystem.UNKNOWN,
}


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="report-cli",
        description=(
            "Generate a structural-analysis report (.docx) from a "
            "CalculiX .frd result file."
        ),
    )
    p.add_argument(
        "--frd",
        required=True,
        type=Path,
        help="Path to the CalculiX .frd result file.",
    )
    p.add_argument(
        "--kind",
        required=True,
        choices=_REPORT_KINDS,
        help=(
            "Which report template to produce. 'pressure-vessel' "
            "additionally requires --scl-nodes and --scl-distances."
        ),
    )
    p.add_argument(
        "--output",
        type=Path,
        default=Path("report.docx"),
        help="Output .docx path (default: ./report.docx).",
    )
    p.add_argument(
        "--unit-system",
        choices=sorted(_UNIT_SYSTEMS),
        default="si-mm",
        help="UnitSystem the .frd was produced in (default: si-mm).",
    )
    # Identity flags. Defaults are derived from the .frd stem so a
    # quick run doesn't need every ID specified explicitly.
    p.add_argument("--project-id", default=None)
    p.add_argument("--task-id", default=None)
    p.add_argument("--report-id", default=None)
    p.add_argument("--bundle-id", default=None)
    p.add_argument(
        "--step-id",
        type=int,
        default=None,
        help=(
            "Optional solution-state ID. Defaults to the final state."
        ),
    )
    p.add_argument(
        "--scl-nodes",
        default=None,
        help=(
            "Comma-separated node IDs along the SCL (inner→outer). "
            "Required for --kind=pressure-vessel."
        ),
    )
    p.add_argument(
        "--scl-distances",
        default=None,
        help=(
            "Comma-separated per-node distances along the SCL "
            "(uniformly spaced). Required for --kind=pressure-vessel."
        ),
    )
    p.add_argument(
        "--validate-template",
        action=argparse.BooleanOptionalAction,
        default=True,
        help=(
            "Validate the produced report against the matching "
            "template before export (default: on). Disabling skips "
            "title-and-citation contract checks but does NOT skip "
            "ADR-012 cited-evidence checks in the exporter."
        ),
    )
    return p


def _resolve_identity_defaults(args: argparse.Namespace) -> None:
    """Auto-fill project_id/task_id/report_id/bundle_id from the .frd
    stem when the engineer didn't supply them explicitly."""
    stem = args.frd.stem or "report"
    if args.project_id is None:
        args.project_id = f"P-{stem}"
    if args.task_id is None:
        args.task_id = f"T-{stem}"
    if args.report_id is None:
        args.report_id = f"R-{stem}"
    if args.bundle_id is None:
        args.bundle_id = f"B-{stem}"


def _parse_int_csv(label: str, raw: str) -> List[int]:
    try:
        return [int(piece.strip()) for piece in raw.split(",") if piece.strip()]
    except ValueError as exc:
        raise SystemExit(
            f"--{label}: expected comma-separated integers, got "
            f"{raw!r} ({exc})"
        )


def _parse_float_csv(label: str, raw: str) -> List[float]:
    try:
        return [float(piece.strip()) for piece in raw.split(",") if piece.strip()]
    except ValueError as exc:
        raise SystemExit(
            f"--{label}: expected comma-separated floats, got "
            f"{raw!r} ({exc})"
        )


def _produce(
    args: argparse.Namespace,
    reader: CalculiXReader,
) -> tuple[ReportSpec, EvidenceBundle, TemplateSpec]:
    """Dispatch to the matching producer + return the template that
    the report should validate against."""
    common_kwargs = dict(
        project_id=args.project_id,
        task_id=args.task_id,
        report_id=args.report_id,
        bundle_id=args.bundle_id,
        step_id=args.step_id,
    )
    if args.kind == "static":
        report, bundle = generate_static_strength_summary(
            reader, **common_kwargs
        )
        return report, bundle, EQUIPMENT_FOUNDATION_STATIC
    if args.kind == "lifting-lug":
        report, bundle = generate_lifting_lug_summary(
            reader, **common_kwargs
        )
        return report, bundle, LIFTING_LUG
    # pressure-vessel
    if args.scl_nodes is None or args.scl_distances is None:
        raise SystemExit(
            "--kind=pressure-vessel requires --scl-nodes and "
            "--scl-distances."
        )
    nodes = _parse_int_csv("scl-nodes", args.scl_nodes)
    distances = _parse_float_csv("scl-distances", args.scl_distances)
    report, bundle = generate_pressure_vessel_local_stress_summary(
        reader,
        scl_node_ids=nodes,
        scl_distances=distances,
        **common_kwargs,
    )
    return report, bundle, PRESSURE_VESSEL_LOCAL_STRESS


def main(argv: Optional[List[str]] = None) -> int:
    """Programmatic entry point (also wired as ``report-cli`` script).

    Returns an exit code; argparse-level errors raise SystemExit
    directly per stdlib convention. Domain refusals (ADR-012 / template
    / export-error) are caught and reported on stderr with exit code 3.
    """
    parser = build_parser()
    args = parser.parse_args(argv)

    if not args.frd.is_file():
        print(
            f"error: --frd path {args.frd} is not a file",
            file=sys.stderr,
        )
        return 2

    _resolve_identity_defaults(args)
    unit_system = _UNIT_SYSTEMS[args.unit_system]

    try:
        reader = CalculiXReader(args.frd, unit_system=unit_system)
    except Exception as exc:
        print(f"error: failed to open {args.frd}: {exc}", file=sys.stderr)
        return 3

    try:
        report, bundle, template = _produce(args, reader)
    except SystemExit:
        # _produce raises SystemExit for argparse-style input errors
        # we surfaced ourselves; re-raise to keep argparse's own flow.
        raise
    except (ValueError, KeyError) as exc:
        print(f"error: producer refused: {exc}", file=sys.stderr)
        return 3
    except Exception:  # pragma: no cover — defensive guard
        print(
            "internal error during report production:\n"
            + traceback.format_exc(),
            file=sys.stderr,
        )
        return 4

    try:
        out = export_docx(
            report,
            bundle,
            output_path=args.output,
            template=template if args.validate_template else None,
        )
    except (ExportError, TemplateValidationError) as exc:
        print(f"error: export refused: {exc}", file=sys.stderr)
        return 3
    except Exception:  # pragma: no cover — defensive guard
        print(
            "internal error during DOCX export:\n"
            + traceback.format_exc(),
            file=sys.stderr,
        )
        return 4

    cited_count = len(bundle.evidence_items)
    print(
        f"wrote {out} (template={template.template_id}, "
        f"evidence_count={cited_count}, bundle_id={bundle.bundle_id})"
    )
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
