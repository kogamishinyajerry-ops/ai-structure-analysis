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

Exit codes (engineers script around these — treat as a contract):
  0  success — DOCX written
  2  argparse / input error (missing flag, malformed CSV, NaN, length
     mismatch between --scl-nodes and --scl-distances, etc.)
  3  domain refusal (ADR-012 violation, missing field, template-
     validation refusal, export refusal, etc.)
  4  unexpected internal error

Invocation (run from the ``backend/`` directory until the project's
top-level packaging is reorganized — tracked separately from this
PR; the existing ``run-well-harness`` script entry has the same
limitation)::

    cd backend
    python -m app.services.report.cli --frd path/to/result.frd \\
        --kind static --output report.docx

The CLI is intentionally thin — every substantive piece of work lives
in the L1-L4 modules. This module's job is *plumbing*: turn argv
strings into typed parameters, surface refusals legibly, and write
the .docx. No engineering decisions hide here.
"""

from __future__ import annotations

import argparse
import math
import sys
import traceback
from pathlib import Path
from typing import List, NoReturn, Optional

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
        # No console_script entry is registered (see pyproject.toml);
        # the engineer-facing invocation is the module form, so the
        # usage banner reflects that rather than advertising a
        # non-existent ``report-cli`` shell command.
        prog="python -m app.services.report.cli",
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


def _input_error(msg: str) -> NoReturn:
    """Print an input-error message to stderr and exit with code 2.

    Centralizes the exit-code contract: argparse-style refusals are
    code 2 regardless of which call site raised them. ``SystemExit("...")``
    with a string argument exits with code 1, which would silently break
    the engineer-facing exit-code contract documented in the module
    docstring. Always go through this helper for argparse-level errors.
    """
    print(f"error: {msg}", file=sys.stderr)
    raise SystemExit(2)


def _parse_int_csv(label: str, raw: str) -> List[int]:
    """Parse a strict comma-separated list of integers.

    Empty fields (e.g. trailing comma, repeated commas) are an error,
    not silently dropped. Calls ``_input_error`` (exit 2) on any
    malformed input.
    """
    pieces = raw.split(",")
    out: List[int] = []
    for piece in pieces:
        stripped = piece.strip()
        if not stripped:
            _input_error(
                f"--{label}: empty field in comma-separated list "
                f"(got {raw!r})"
            )
        try:
            out.append(int(stripped))
        except ValueError as exc:
            _input_error(
                f"--{label}: expected comma-separated integers, got "
                f"{raw!r} ({exc})"
            )
    if not out:
        _input_error(f"--{label}: empty value")
    return out


def _parse_float_csv(label: str, raw: str) -> List[float]:
    """Parse a strict comma-separated list of finite floats.

    Empty fields are rejected. NaN and ±Inf are rejected — the
    pressure-vessel SCL contract requires finite, ordered, uniformly-
    spaced distances.
    """
    pieces = raw.split(",")
    out: List[float] = []
    for piece in pieces:
        stripped = piece.strip()
        if not stripped:
            _input_error(
                f"--{label}: empty field in comma-separated list "
                f"(got {raw!r})"
            )
        try:
            value = float(stripped)
        except ValueError as exc:
            _input_error(
                f"--{label}: expected comma-separated floats, got "
                f"{raw!r} ({exc})"
            )
        if not math.isfinite(value):
            _input_error(
                f"--{label}: non-finite value {stripped!r} "
                f"(NaN/Inf not allowed)"
            )
        out.append(value)
    if not out:
        _input_error(f"--{label}: empty value")
    return out


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
        _input_error(
            "--kind=pressure-vessel requires --scl-nodes and "
            "--scl-distances."
        )
    nodes = _parse_int_csv("scl-nodes", args.scl_nodes)
    distances = _parse_float_csv("scl-distances", args.scl_distances)
    if len(nodes) != len(distances):
        _input_error(
            f"--scl-nodes ({len(nodes)} values) and --scl-distances "
            f"({len(distances)} values) must have equal length"
        )
    report, bundle = generate_pressure_vessel_local_stress_summary(
        reader,
        scl_node_ids=nodes,
        scl_distances=distances,
        **common_kwargs,
    )
    return report, bundle, PRESSURE_VESSEL_LOCAL_STRESS


def main(argv: Optional[List[str]] = None) -> int:
    """Programmatic entry point.

    Returns an exit code on success and on caught domain refusals.
    Input-validation errors (argparse, malformed CSV, missing required
    SCL args, length mismatch) raise ``SystemExit(2)`` per the contract
    documented in the module docstring; ``argparse`` and ``_input_error``
    both honour exit code 2.

    Domain refusals (ADR-012 / template / export-error / producer
    ``ValueError``) are caught and reported on stderr with exit code 3.
    Unexpected exceptions surface as exit code 4 with a traceback.
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
