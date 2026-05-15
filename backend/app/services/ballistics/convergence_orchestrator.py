"""Tier 1 candidate convergence study orchestrator (FM-04a Phase 2 B).

Tier 1 engineering candidate. Not signed validation. Not benchmark agreement.

This module turns a mesh x time-step sweep of completed Tier 1 candidate
runs into one structured ``convergence_study.json`` artifact. It consumes
``ballistic_metrics.json`` outputs already written by
``backend.app.services.ballistics.metric_extraction.write_ballistic_metrics``
and reuses the per-axis verdict rule baked into
``convergence_writers._candidate_stability``.

Inputs are pre-extracted ``ConvergenceStudyRow`` records to keep the
orchestrator pure and easy to test without solver fixtures. A thin CLI
wrapper (``scripts/gs102_convergence_sweep.py``) reads metric sidecars
off disk and feeds the orchestrator.

Forbidden wording (per ADR-023 + ADR-024 lite): no ``benchmark agreement``,
no ``signed validation``, no ``perforation completed``, no
``bullet-through-steel complete``, no ``validated physics`` in any output.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .convergence_writers import (
    CLAIM_BOUNDARY_TIER1,
    DEFAULT_TOLERANCE_PCT,
)


@dataclass(frozen=True)
class ConvergenceStudyRow:
    """One (mesh, dt) point in a Tier 1 convergence study.

    The orchestrator does NOT recompute residual velocity or energy
    balance error; callers supply them after reading the corresponding
    ``ballistic_metrics.json`` sidecar. Keeping the orchestrator pure
    lets it run on synthetic inputs in tests and in CI without solver
    fixtures.
    """

    mesh_label: str
    mesh_axis_value: float
    dt_label: str
    dt_axis_value: float
    residual_velocity_m_per_s: float
    energy_balance_error_pct: float | None = None
    source_metrics_path: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class ConvergenceStudyInput:
    case_id: str
    rows: list[ConvergenceStudyRow]
    study_metric: str = "residual_velocity_m_per_s"
    mesh_axis_parameter: str = "mesh_level"
    dt_axis_parameter: str = "time_step_dt_s"
    tolerance_pct: float = DEFAULT_TOLERANCE_PCT
    claim_boundary: str = CLAIM_BOUNDARY_TIER1
    notes: str | None = None


# Combined verdicts surfaced in the JSON ``combined_verdict`` field.
VERDICT_STABLE = "candidate_observed_stable"
VERDICT_UNSTABLE = "candidate_observed_unstable"
VERDICT_INSUFFICIENT = "insufficient_data"


def build_convergence_study(inp: ConvergenceStudyInput) -> dict[str, Any]:
    """Build the ``convergence_study.json`` payload from study rows.

    The payload combines a 1-axis mesh sweep (rows sharing the most
    common dt value, ordered coarsest → finest by mesh_axis_value) and
    a 1-axis dt sweep (rows sharing the most common mesh level, ordered
    coarsest → finest by dt_axis_value).

    Verdict combination rules:

    * ``insufficient_data`` — either sweep has fewer than 2 unique rows.
    * ``candidate_observed_unstable`` — either sweep crosses the
      tolerance threshold.
    * ``candidate_observed_stable`` — both sweeps stay inside the
      tolerance threshold.
    """
    if not inp.rows:
        raise ValueError("convergence study must declare at least one row")
    if inp.tolerance_pct <= 0:
        raise ValueError("tolerance_pct must be > 0")

    mesh_sweep = _build_mesh_sweep(inp)
    dt_sweep = _build_dt_sweep(inp)

    combined_verdict = _combine_verdict(
        mesh_sweep.get("candidate_stability"),
        dt_sweep.get("candidate_stability"),
    )

    payload: dict[str, Any] = {
        "case_id": inp.case_id,
        "study_metric": inp.study_metric,
        "tolerance_pct": float(inp.tolerance_pct),
        "combined_verdict": combined_verdict,
        "mesh_sweep": mesh_sweep,
        "dt_sweep": dt_sweep,
        "row_count": len(inp.rows),
        "rows": [_row_dict(row) for row in inp.rows],
        "claim_boundary": inp.claim_boundary,
        "claim_impact": (
            "Tier 1 candidate mesh and time-step convergence study only; "
            "not signed validation; not benchmark agreement; tolerance "
            f"{inp.tolerance_pct:g}% applied to "
            f"`{inp.study_metric}` across each 1-axis sweep"
        ),
        "energy_balance_observation": _summarize_energy_balance(inp.rows),
    }
    if inp.notes:
        payload["notes"] = inp.notes
    return payload


def write_convergence_study(
    inp: ConvergenceStudyInput,
    output_dir: Path | str,
) -> Path:
    """Write ``convergence_study.json`` under ``output_dir``.

    Returns the absolute path of the written file. The orchestrator
    refuses to write under ``golden_samples/**`` — callers are expected
    to pass a ``project_state/`` path.
    """
    out_dir = Path(output_dir)
    _assert_not_in_golden_samples(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    payload = build_convergence_study(inp)
    out_path = out_dir / "convergence_study.json"
    out_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return out_path


# ---------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------


def _build_mesh_sweep(inp: ConvergenceStudyInput) -> dict[str, Any]:
    """Group rows that share the most-common dt value; order by mesh."""
    dt_value, dt_label = _most_common([(row.dt_axis_value, row.dt_label) for row in inp.rows])
    selected = [row for row in inp.rows if row.dt_axis_value == dt_value]
    selected = sorted(selected, key=lambda row: row.mesh_axis_value)
    metric_values = [
        (row.mesh_label, row.mesh_axis_value, row.residual_velocity_m_per_s) for row in selected
    ]
    relative_change_pct = _relative_change_pct(metric_values)
    stability = _classify(inp.tolerance_pct, relative_change_pct)
    return {
        "axis": inp.mesh_axis_parameter,
        "axis_label": "mesh_level",
        "held_dt_label": dt_label,
        "held_dt_axis_value": float(dt_value) if dt_value is not None else None,
        "run_count": len(selected),
        "relative_change_pct": (
            None if relative_change_pct is None else round(float(relative_change_pct), 6)
        ),
        "candidate_stability": stability,
        "runs": [
            {
                "label": label,
                "mesh_axis_value": float(mesh_axis_value),
                "metric_value": float(metric_value),
            }
            for label, mesh_axis_value, metric_value in metric_values
        ],
    }


def _build_dt_sweep(inp: ConvergenceStudyInput) -> dict[str, Any]:
    """Group rows that share the most-common mesh level; order by dt."""
    mesh_value, mesh_label = _most_common(
        [(row.mesh_axis_value, row.mesh_label) for row in inp.rows]
    )
    selected = [row for row in inp.rows if row.mesh_axis_value == mesh_value]
    selected = sorted(selected, key=lambda row: row.dt_axis_value)
    metric_values = [
        (row.dt_label, row.dt_axis_value, row.residual_velocity_m_per_s) for row in selected
    ]
    relative_change_pct = _relative_change_pct(metric_values)
    stability = _classify(inp.tolerance_pct, relative_change_pct)
    return {
        "axis": inp.dt_axis_parameter,
        "axis_label": "time_step_dt_s",
        "held_mesh_label": mesh_label,
        "held_mesh_axis_value": float(mesh_value) if mesh_value is not None else None,
        "run_count": len(selected),
        "relative_change_pct": (
            None if relative_change_pct is None else round(float(relative_change_pct), 6)
        ),
        "candidate_stability": stability,
        "runs": [
            {
                "label": label,
                "dt_axis_value": float(dt_axis_value),
                "metric_value": float(metric_value),
            }
            for label, dt_axis_value, metric_value in metric_values
        ],
    }


def _most_common(
    pairs: list[tuple[float, str]],
) -> tuple[float | None, str | None]:
    """Return the (value, label) pair that appears most often.

    Ties resolve to the value with the largest count, then to the
    smallest float for determinism. Returns ``(None, None)`` when the
    list is empty.
    """
    if not pairs:
        return (None, None)
    counts: dict[float, int] = {}
    labels: dict[float, str] = {}
    for value, label in pairs:
        counts[value] = counts.get(value, 0) + 1
        labels.setdefault(value, label)
    # Pick the value with the highest count; ties → smallest float (deterministic).
    winner = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[0][0]
    return (winner, labels[winner])


def _relative_change_pct(
    metric_values: list[tuple[str, float, float]],
) -> float | None:
    if len(metric_values) < 2:
        return None
    previous = metric_values[-2][2]
    final = metric_values[-1][2]
    if previous == 0.0:
        return None
    return abs(final - previous) / abs(previous) * 100.0


def _classify(tolerance_pct: float, relative_change_pct: float | None) -> str:
    if relative_change_pct is None:
        return "unknown"
    if abs(relative_change_pct) > float(tolerance_pct):
        return VERDICT_UNSTABLE
    return VERDICT_STABLE


def _combine_verdict(mesh_stability: str | None, dt_stability: str | None) -> str:
    if mesh_stability == "unknown" or dt_stability == "unknown":
        return VERDICT_INSUFFICIENT
    if mesh_stability == VERDICT_UNSTABLE or dt_stability == VERDICT_UNSTABLE:
        return VERDICT_UNSTABLE
    if mesh_stability == VERDICT_STABLE and dt_stability == VERDICT_STABLE:
        return VERDICT_STABLE
    return VERDICT_INSUFFICIENT


def _row_dict(row: ConvergenceStudyRow) -> dict[str, Any]:
    record: dict[str, Any] = {
        "mesh_label": row.mesh_label,
        "mesh_axis_value": float(row.mesh_axis_value),
        "dt_label": row.dt_label,
        "dt_axis_value": float(row.dt_axis_value),
        "residual_velocity_m_per_s": float(row.residual_velocity_m_per_s),
    }
    if row.energy_balance_error_pct is not None:
        record["energy_balance_error_pct"] = float(row.energy_balance_error_pct)
    if row.source_metrics_path is not None:
        record["source_metrics_path"] = row.source_metrics_path
    if row.extra:
        record.update(row.extra)
    return record


def _summarize_energy_balance(rows: list[ConvergenceStudyRow]) -> dict[str, Any]:
    """Aggregate energy balance errors across the study rows.

    Reports min/max/mean balance errors when at least one row supplies a
    balance error; never silently treats missing data as zero.
    """
    errors = [
        row.energy_balance_error_pct for row in rows if row.energy_balance_error_pct is not None
    ]
    if not errors:
        return {
            "status": "unavailable",
            "rows_with_balance_error": 0,
            "rows_total": len(rows),
        }
    return {
        "status": "candidate_observed",
        "rows_with_balance_error": len(errors),
        "rows_total": len(rows),
        "min_pct": round(min(errors), 6),
        "max_pct": round(max(errors), 6),
        "mean_pct": round(sum(errors) / len(errors), 6),
    }


def _assert_not_in_golden_samples(output_dir: Path) -> None:
    resolved = output_dir.resolve()
    for parent in (resolved, *resolved.parents):
        if parent.name == "golden_samples":
            raise ValueError(
                "convergence_study.json refuses writes under golden_samples/**; "
                "use project_state/<...>/convergence/ instead"
            )
