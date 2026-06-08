#!/usr/bin/env python3
"""Generate a Tier 1 GS-102 design exploration plan from metrics sidecars."""

from __future__ import annotations

import argparse
import json
import math
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

REPO_ROOT_DEFAULT = Path(__file__).resolve().parents[1]
DEFAULT_CASE_IDS = (
    "GS-102-transient-refined-v150-bracket-20260512",
    "GS-102-transient-refined-v285-bracket-20260512",
    "GS-102-transient-refined-v600-bracket-20260512",
)
DEFAULT_OUTPUT = Path("reports/gs102_design_exploration_20260512.md")


@dataclass(frozen=True)
class VelocityRecord:
    case_id: str
    velocity_m_s: float
    marker: str
    residual_velocity_m_s: float | None
    back_face_crossed: bool | None
    crossing_status: str
    solver_normal_termination: bool | None
    metrics_path: Path

    @property
    def is_embedded(self) -> bool:
        return self.back_face_crossed is False or self.marker == "embedded_candidate"

    @property
    def is_perforated(self) -> bool:
        return self.back_face_crossed is True or self.marker == "perforated_candidate"


def render_design_exploration_report(
    *,
    repo_root: Path,
    case_ids: Sequence[str] = DEFAULT_CASE_IDS,
    report_date: str | None = None,
) -> str:
    report_date = report_date or date.today().isoformat()
    records = sorted(
        (_load_velocity_record(repo_root, case_id) for case_id in case_ids),
        key=lambda record: record.velocity_m_s,
    )
    transition_lines, probes = _transition_analysis(records)

    lines = [
        f"# GS-102 Design Exploration Plan - {report_date}",
        "",
        "> Status: Tier 1 design exploration plan.",
        "> Claim boundary: not signed validation; not benchmark agreement.",
        "",
        "## Purpose",
        "",
        "Use existing GS-102 velocity sidecars to choose the next candidate",
        "OpenRadioss runs. This plan is meant to loosen Tier 1 exploration speed",
        "without promoting any physical validation claim.",
        "",
        "## Current Evidence",
        "",
        "| V0 m/s | Marker | Back crossed | Residual m/s | Solver normal | Metrics |",
        "|---:|---|---|---:|---|---|",
    ]
    lines.extend(_record_row(record, repo_root) for record in records)
    lines.extend(["", *transition_lines, "", "## Recommended Next Runs", ""])
    lines.extend(["| V0 m/s | Reason | Claim tier |", "|---:|---|---|"])
    for probe, reason in probes:
        lines.append(f"| {probe} | {reason} | Tier 1 candidate only |")

    lines.extend(
        [
            "",
            "## AI Exploration Freedoms Used",
            "",
            "- The model may propose velocity probes and design hypotheses from",
            "  existing sidecars before a benchmark is locked.",
            "- The proposal may prioritize information gain over validation-packet",
            "  completeness.",
            "- The next run set may be changed quickly after each new sidecar lands.",
            "",
            "## Hard Boundaries",
            "",
            "- Do not write runtime outputs under `golden_samples/**`.",
            "- Do not treat recommended probes as signed physical results.",
            "- Do not claim benchmark agreement or completed bullet-through-steel",
            "  behavior from this plan.",
            "- Any Tier 2 promotion still needs benchmark source, tolerance,",
            "  convergence evidence, sealed hashes, and independent review.",
            "",
        ]
    )
    return "\n".join(lines)


def write_design_exploration_report(
    *,
    repo_root: Path,
    output_path: Path,
    case_ids: Sequence[str] = DEFAULT_CASE_IDS,
    report_date: str | None = None,
) -> Path:
    text = render_design_exploration_report(
        repo_root=repo_root,
        case_ids=case_ids,
        report_date=report_date,
    )
    output_path = output_path if output_path.is_absolute() else repo_root / output_path
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(text, encoding="utf-8")
    print(f"wrote: {_rel(output_path, repo_root)}")
    return output_path


def _load_velocity_record(repo_root: Path, case_id: str) -> VelocityRecord:
    metrics_path = (
        repo_root
        / "project_state"
        / "graph_executor"
        / case_id
        / "ballistic"
        / "ballistic_metrics.json"
    )
    if not metrics_path.exists():
        raise FileNotFoundError(f"missing GS-102 metrics sidecar: {metrics_path}")
    payload = json.loads(metrics_path.read_text(encoding="utf-8"))
    crossing = payload.get("crossing_evidence") or {}
    solver = payload.get("solver_evidence") or {}
    return VelocityRecord(
        case_id=str(payload.get("case_id") or case_id),
        velocity_m_s=float(payload["projectile_initial_velocity_m_per_s"]),
        marker=str(payload.get("perforation_marker") or "unknown"),
        residual_velocity_m_s=_optional_float(
            payload.get("residual_velocity_candidate_m_per_s")
        ),
        back_face_crossed=_optional_bool(crossing.get("back_face_crossed")),
        crossing_status=str(crossing.get("status") or "unknown"),
        solver_normal_termination=_optional_bool(
            solver.get("engine_normal_termination")
        ),
        metrics_path=metrics_path,
    )


def _transition_bracket(records: Sequence[VelocityRecord]) -> tuple[VelocityRecord, VelocityRecord]:
    embedded = [record for record in records if record.is_embedded]
    perforated = [record for record in records if record.is_perforated]
    if not embedded or not perforated:
        raise ValueError("need at least one embedded and one perforated candidate")
    low = max(embedded, key=lambda record: record.velocity_m_s)
    high = min(perforated, key=lambda record: record.velocity_m_s)
    if low.velocity_m_s >= high.velocity_m_s:
        raise ValueError("candidate records do not form a valid transition bracket")
    return low, high


def _transition_analysis(
    records: Sequence[VelocityRecord],
) -> tuple[list[str], list[tuple[int, str]]]:
    windows = _transition_windows(records)
    if not windows:
        raise ValueError("need at least one embedded/perforated transition window")
    if len(windows) == 1 and _classification(windows[0][0]) == "embedded":
        low, high = windows[0]
        return (
            [
                "## Transition Bracket",
                "",
                (
                    f"Current transition bracket: `{_number(low.velocity_m_s)} m/s` to "
                    f"`{_number(high.velocity_m_s)} m/s`."
                ),
                "",
                "- Lower anchor: highest non-back-crossing / embedded candidate.",
                "- Upper anchor: lowest back-crossing / perforated candidate.",
                "- This bracket is a Tier 1 candidate heuristic only.",
            ],
            _recommended_velocity_probes(low.velocity_m_s, high.velocity_m_s),
        )

    transition_descriptions = [
        (
            f"- `{_number(left.velocity_m_s)} m/s` to "
            f"`{_number(right.velocity_m_s)} m/s`: "
            f"{_classification(left)} -> {_classification(right)}"
        )
        for left, right in windows
    ]
    return (
        [
            "## Transition Bracket",
            "",
            "Non-monotonic candidate response detected.",
            "",
            *transition_descriptions,
            "",
            "- Treat this as a Tier 1 diagnostic signal, not a physical threshold.",
            "- Prefer diagnostic probes before narrowing a single transition bracket.",
        ],
        _non_monotonic_velocity_probes(windows),
    )


def _transition_windows(
    records: Sequence[VelocityRecord],
) -> list[tuple[VelocityRecord, VelocityRecord]]:
    windows: list[tuple[VelocityRecord, VelocityRecord]] = []
    for left, right in zip(records, records[1:], strict=False):
        left_class = _classification(left)
        right_class = _classification(right)
        if "unknown" in {left_class, right_class}:
            continue
        if left_class != right_class:
            windows.append((left, right))
    return windows


def _classification(record: VelocityRecord) -> str:
    if record.is_perforated:
        return "perforated"
    if record.is_embedded:
        return "embedded"
    return "unknown"


def _recommended_velocity_probes(low: float, high: float) -> list[tuple[int, str]]:
    midpoint = (low + high) / 2.0
    lower_half = (low + midpoint) / 2.0
    upper_half = (midpoint + high) / 2.0
    return [
        (_round_to_nearest(lower_half, 5), "refine lower half of transition bracket"),
        (_round_to_nearest(midpoint, 5), "midpoint transition probe"),
        (_round_to_nearest(upper_half, 5), "refine upper half of transition bracket"),
    ]


def _non_monotonic_velocity_probes(
    windows: Sequence[tuple[VelocityRecord, VelocityRecord]],
) -> list[tuple[int, str]]:
    probes: list[tuple[int, str]] = []
    for index, (left, right) in enumerate(windows):
        midpoint = _round_to_nearest((left.velocity_m_s + right.velocity_m_s) / 2.0, 5)
        if _classification(left) == "perforated" and _classification(right) == "embedded":
            reason = "diagnose non-monotonic reversal window"
        elif index == 0:
            reason = "refine lower transition window"
        elif index == len(windows) - 1:
            reason = "refine upper transition window"
        else:
            reason = "refine additional transition window"
        probes.append((midpoint, reason))
    return probes


def _record_row(record: VelocityRecord, repo_root: Path) -> str:
    return (
        f"| {_number(record.velocity_m_s)} | `{record.marker}` | "
        f"{_bool_text(record.back_face_crossed)} | "
        f"{_number(record.residual_velocity_m_s)} | "
        f"{_bool_text(record.solver_normal_termination)} | "
        f"`{_rel(record.metrics_path, repo_root)}` |"
    )


def _round_to_nearest(value: float, step: int) -> int:
    return int(math.floor((value / step) + 0.5) * step)


def _optional_float(value: Any) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _optional_bool(value: Any) -> bool | None:
    return value if isinstance(value, bool) else None


def _bool_text(value: bool | None) -> str:
    if value is True:
        return "true"
    if value is False:
        return "false"
    return "n/a"


def _number(value: float | None) -> str:
    if value is None:
        return "n/a"
    if float(value).is_integer():
        return str(int(value))
    return f"{value:.6f}".rstrip("0").rstrip(".")


def _rel(path: Path, repo_root: Path) -> str:
    try:
        return str(path.resolve().relative_to(repo_root.resolve()))
    except ValueError:
        return str(path)


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=str(REPO_ROOT_DEFAULT))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--report-date", default="2026-05-12")
    parser.add_argument("--case-id", action="append", dest="case_ids")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    write_design_exploration_report(
        repo_root=Path(args.repo_root),
        output_path=Path(args.output),
        case_ids=tuple(args.case_ids) if args.case_ids else DEFAULT_CASE_IDS,
        report_date=args.report_date,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
