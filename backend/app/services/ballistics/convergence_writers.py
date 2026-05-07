"""Tier 1 candidate convergence sidecar writers (mesh + time-step).

Tier 1 engineering candidate. Not signed validation. Not benchmark agreement.

These are pure-Python writers that produce the sidecar shapes consumed by
``backend.app.services.candidate_report_spine``:

* ``write_mesh_convergence(...)`` writes ``mesh_convergence.json`` under
  ``project_state/.../mesh/``.
* ``write_time_step_convergence(...)`` writes ``time_step_convergence.json``
  under ``project_state/.../ballistic/``.

The writers:

* Compute ``relative_change_pct`` honestly from the run sequence (last vs the
  most-refined run; falls back to None when fewer than 2 runs are provided).
* Carry the Tier 1 ``candidate_observed_stable`` / ``candidate_observed_
  unstable`` rule from the spine via a derived ``status`` field, so consumers
  that read the sidecar directly (without going through the spine) still see
  the verdict.
* Always stamp ``claim_boundary = "tier1_engineering_candidate;
  not_signed_validation; not_benchmark_agreement"`` (configurable but the
  default is locked to Tier 1).

Forbidden wording (per ADR-023 + ADR-024 lite): no ``benchmark agreement``,
no ``signed validation``, no ``perforation completed``, no
``bullet-through-steel complete``, no ``validated physics`` in any output.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional


CLAIM_BOUNDARY_TIER1 = (
    "tier1_engineering_candidate; not_signed_validation; not_benchmark_agreement"
)
DEFAULT_TOLERANCE_PCT = 5.0


@dataclass(frozen=True)
class ConvergenceRun:
    """One candidate run in a refinement sweep.

    ``parameter_value`` is the refinement-axis value (mesh level index, dt
    in seconds, etc.). ``metric_value`` is the observed quantity at that
    refinement level. Both are stored as floats for stable serialisation.
    """

    label: str
    parameter_value: float
    metric_value: float
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class MeshConvergenceInput:
    case_id: str
    metric: str
    runs: list[ConvergenceRun]
    parameter: str = "mesh_level"
    tolerance_pct: float = DEFAULT_TOLERANCE_PCT
    claim_boundary: str = CLAIM_BOUNDARY_TIER1
    notes: Optional[str] = None


@dataclass
class TimeStepConvergenceInput:
    case_id: str
    metric: str
    runs: list[ConvergenceRun]
    parameter: str = "time_step_dt"
    tolerance_pct: float = DEFAULT_TOLERANCE_PCT
    claim_boundary: str = CLAIM_BOUNDARY_TIER1
    notes: Optional[str] = None


def write_mesh_convergence(inp: MeshConvergenceInput, output_dir: Path | str) -> Path:
    """Write a Tier 1 candidate mesh refinement convergence sidecar."""
    return _write_convergence(
        inp=inp,
        sidecar_name="mesh_convergence.json",
        output_dir=output_dir,
        default_status_message="candidate_observed",
    )


def write_time_step_convergence(
    inp: TimeStepConvergenceInput, output_dir: Path | str
) -> Path:
    """Write a Tier 1 candidate time-step refinement convergence sidecar."""
    return _write_convergence(
        inp=inp,
        sidecar_name="time_step_convergence.json",
        output_dir=output_dir,
        default_status_message="candidate_observed",
    )


# ---------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------


def _write_convergence(
    *,
    inp: MeshConvergenceInput | TimeStepConvergenceInput,
    sidecar_name: str,
    output_dir: Path | str,
    default_status_message: str,
) -> Path:
    if not inp.runs:
        raise ValueError(
            f"convergence input must declare at least one run for case {inp.case_id!r}"
        )
    if inp.tolerance_pct <= 0:
        raise ValueError("tolerance_pct must be > 0")

    relative_change_pct = _relative_change_pct(inp.runs)
    candidate_stability = _candidate_stability(inp.tolerance_pct, relative_change_pct)

    payload: dict[str, Any] = {
        "case_id": inp.case_id,
        "status": default_status_message,
        "candidate_stability": candidate_stability,
        "parameter": inp.parameter,
        "metric": inp.metric,
        "tolerance_pct": float(inp.tolerance_pct),
        "relative_change_pct": (
            None if relative_change_pct is None else round(float(relative_change_pct), 6)
        ),
        "runs": [_run_dict(run) for run in inp.runs],
        "claim_boundary": inp.claim_boundary,
        "claim_impact": (
            "Tier 1 candidate convergence evidence only; benchmark agreement and "
            "signed validation remain blocked"
        ),
    }
    if inp.notes:
        payload["notes"] = inp.notes

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / sidecar_name
    out_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return out_path


def _run_dict(run: ConvergenceRun) -> dict[str, Any]:
    record: dict[str, Any] = {
        "label": run.label,
        "parameter_value": float(run.parameter_value),
        "metric_value": float(run.metric_value),
    }
    if run.extra:
        record.update(run.extra)
    return record


def _relative_change_pct(runs: list[ConvergenceRun]) -> Optional[float]:
    """Relative change between the last two runs in absolute percent of the previous metric.

    Returns None if fewer than two runs, or if the previous run's metric is zero.
    The "previous" run is the one immediately before the most-refined run as
    listed in ``runs`` — callers are expected to supply runs ordered
    coarsest → finest. We do not re-sort here because some refinement axes
    (mesh level, dt) order naturally in opposite directions.
    """
    if len(runs) < 2:
        return None
    previous = runs[-2].metric_value
    final = runs[-1].metric_value
    if previous == 0.0:
        return None
    return abs(final - previous) / abs(previous) * 100.0


def _candidate_stability(tolerance_pct: float, relative_change_pct: Optional[float]) -> str:
    if relative_change_pct is None:
        return "unknown"
    if abs(relative_change_pct) > float(tolerance_pct):
        return "candidate_observed_unstable"
    return "candidate_observed_stable"
