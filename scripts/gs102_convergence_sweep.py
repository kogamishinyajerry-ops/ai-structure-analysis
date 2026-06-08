#!/usr/bin/env python3
"""GS-102 mesh x time-step convergence sweep CLI (FM-04a Phase 2 B).

Reads a list of completed Tier 1 candidate runs (each pointing at a
``project_state/graph_executor/<case-id>/ballistic/ballistic_metrics.json``
sidecar), groups them into a 2-axis convergence study, and writes one
``convergence_study.json`` under
``project_state/graph_executor/<study-id>/convergence/``.

This script does NOT run OpenRadioss. It assumes the per-run candidate
metrics already exist on disk (produced earlier by
``scripts/gs102_transient_candidate_pipeline.py``). The orchestrator
function is in
``backend/app/services/ballistics/convergence_orchestrator.py`` and is
the only place verdict logic lives — this CLI is a thin reader.

Tier 1 engineering candidate. Not signed validation. Not benchmark
agreement. Refuses writes under ``golden_samples/**``.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT_DEFAULT = Path(__file__).resolve().parents[1]


def _ensure_backend_path(repo_root: Path) -> None:
    backend = (repo_root / "backend").resolve()
    if backend.is_dir() and str(backend) not in sys.path:
        sys.path.insert(0, str(backend))


def _load_metric(metrics_path: Path) -> tuple[float, float | None]:
    """Return ``(residual_velocity_m_per_s, energy_balance_error_pct)``.

    Raises ``ValueError`` when the sidecar lacks the residual velocity
    field; energy balance error is optional.
    """
    if not metrics_path.is_file():
        raise FileNotFoundError(f"ballistic metrics sidecar not found: {metrics_path}")
    data = json.loads(metrics_path.read_text(encoding="utf-8"))
    residual = data.get("residual_velocity_candidate_m_per_s")
    if residual is None:
        raise ValueError(
            f"sidecar {metrics_path} has no residual_velocity_candidate_m_per_s"
        )
    audit = data.get("energy_audit") or {}
    balance_error = audit.get("energy_balance_error_pct")
    return float(residual), (None if balance_error is None else float(balance_error))


def _parse_rows_file(rows_path: Path) -> list[dict[str, Any]]:
    if not rows_path.is_file():
        raise FileNotFoundError(f"rows file not found: {rows_path}")
    text = rows_path.read_text(encoding="utf-8")
    payload = json.loads(text)
    if not isinstance(payload, list):
        raise ValueError(
            f"rows file {rows_path} must contain a JSON array of row records"
        )
    for row in payload:
        for required in (
            "mesh_label",
            "mesh_axis_value",
            "dt_label",
            "dt_axis_value",
            "ballistic_metrics_path",
        ):
            if required not in row:
                raise ValueError(
                    f"row missing required field {required!r}: {row!r}"
                )
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Build a Tier 1 candidate mesh x time-step convergence study "
            "from existing ballistic_metrics.json sidecars."
        )
    )
    parser.add_argument(
        "--rows-file",
        type=Path,
        required=True,
        help=(
            "Path to a JSON array of row records. Each row must have: "
            "mesh_label, mesh_axis_value, dt_label, dt_axis_value, "
            "ballistic_metrics_path."
        ),
    )
    parser.add_argument(
        "--case-id",
        required=True,
        help="Case id for the study (lands in convergence_study.json).",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        required=True,
        help=(
            "Output directory under project_state/<...>/. Refuses paths "
            "under golden_samples/**."
        ),
    )
    parser.add_argument(
        "--study-metric",
        default="residual_velocity_m_per_s",
        help="Quantity being studied (default residual_velocity_m_per_s).",
    )
    parser.add_argument(
        "--mesh-axis-parameter",
        default="mesh_level",
        help="Axis label for the mesh refinement parameter.",
    )
    parser.add_argument(
        "--dt-axis-parameter",
        default="time_step_dt_s",
        help="Axis label for the time-step refinement parameter.",
    )
    parser.add_argument(
        "--tolerance-pct",
        type=float,
        default=5.0,
        help="Per-axis tolerance for the candidate_observed_stable verdict.",
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=REPO_ROOT_DEFAULT,
        help="Repository root (used to resolve relative metrics paths).",
    )
    parser.add_argument(
        "--notes",
        default=None,
        help="Optional free-text note to attach to the study payload.",
    )

    args = parser.parse_args(argv)
    _ensure_backend_path(args.repo_root)
    from app.services.ballistics.convergence_orchestrator import (  # noqa: E402
        ConvergenceStudyInput,
        ConvergenceStudyRow,
        write_convergence_study,
    )

    raw_rows = _parse_rows_file(args.rows_file)
    study_rows: list[ConvergenceStudyRow] = []
    for row in raw_rows:
        metrics_path = Path(row["ballistic_metrics_path"])
        if not metrics_path.is_absolute():
            metrics_path = args.repo_root / metrics_path
        residual, balance = _load_metric(metrics_path)
        study_rows.append(
            ConvergenceStudyRow(
                mesh_label=str(row["mesh_label"]),
                mesh_axis_value=float(row["mesh_axis_value"]),
                dt_label=str(row["dt_label"]),
                dt_axis_value=float(row["dt_axis_value"]),
                residual_velocity_m_per_s=residual,
                energy_balance_error_pct=balance,
                source_metrics_path=str(
                    metrics_path.relative_to(args.repo_root)
                    if metrics_path.is_absolute() and args.repo_root in metrics_path.parents
                    else metrics_path
                ),
            )
        )

    inp = ConvergenceStudyInput(
        case_id=args.case_id,
        rows=study_rows,
        study_metric=args.study_metric,
        mesh_axis_parameter=args.mesh_axis_parameter,
        dt_axis_parameter=args.dt_axis_parameter,
        tolerance_pct=args.tolerance_pct,
        notes=args.notes,
    )
    out_path = write_convergence_study(inp, args.output_dir)
    print(f"convergence study written to {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
