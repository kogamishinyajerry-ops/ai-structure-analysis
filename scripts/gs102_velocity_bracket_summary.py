#!/usr/bin/env python3
"""Generate the GS-102 velocity bracket summary from metrics sidecars."""

from __future__ import annotations

import argparse
import difflib
import json
from collections.abc import Sequence
from datetime import date
from pathlib import Path
from typing import Any

REPO_ROOT_DEFAULT = Path(__file__).resolve().parents[1]
DEFAULT_CASE_IDS = (
    "GS-102-transient-refined-v150-bracket-20260512",
    "GS-102-transient-refined-v285-bracket-20260512",
    "GS-102-transient-refined-v600-bracket-20260512",
)
DEFAULT_OUTPUT = Path("reports/gs102_velocity_bracket_20260512.md")


def render_velocity_bracket_summary(
    *,
    repo_root: Path,
    case_ids: Sequence[str] = DEFAULT_CASE_IDS,
    report_date: str | None = None,
) -> str:
    report_date = report_date or date.today().isoformat()
    records = [_load_case_record(repo_root, case_id) for case_id in case_ids]
    missing_terms = _merged_missing_terms(records)
    velocity_text = ", ".join(
        _number(record["payload"].get("projectile_initial_velocity_m_per_s"))
        for record in records
    )

    lines = [
        f"# GS-102 Velocity Bracket Summary - {report_date}",
        "",
        "> Status: Tier 1 engineering candidate.",
        "> Claim boundary: not signed validation; not benchmark agreement.",
        "",
        "## Purpose",
        "",
        "This report summarizes the current GS-102 refined OpenRadioss transient",
        f"candidate bracket at {velocity_text} m/s.",
        "Generated from `ballistic_metrics.json` sidecars.",
        "",
        "No new solver run is claimed by this report. It only summarizes existing",
        "candidate artifacts.",
        "",
        "## Bracket Results",
        "",
        "| Case | V0 m/s | Marker | Residual m/s | Crossing status | "
        "Back crossed | First back crossing s | Solver / cycles / frames / live solids |",
        "|---|---:|---|---:|---|---|---:|---|",
    ]
    lines.extend(_table_row(record) for record in records)
    lines.extend(
        [
            "",
            "## Candidate Interpretation",
            "",
            *_interpretation_lines(records, missing_terms),
            "",
            "## Artifact Index",
            "",
        ]
    )

    for record in records:
        lines.extend(_artifact_lines(record))

    lines.extend(
        [
            "## Review Notes",
            "",
            "- The bracket uses the refined fixture source decks from",
            "  `golden_samples/GS-102-refined-candidate/data`.",
            "- Runtime decks and outputs are kept under `project_state/runs`, not under",
            "  `golden_samples/**`.",
            "- Each metrics sidecar carries a `solver_evidence` block with normal",
            "  termination, cycle count, frame count, live solids, and deletion counts.",
            "- The current evidence supports a Tier 1 candidate trend only.",
            "- Do not promote this summary to Tier 2 without benchmark source lock,",
            "  tolerance definition, complete energy accounting, and independent",
            "  reviewer signoff.",
            "",
        ]
    )
    return "\n".join(lines)


def write_velocity_bracket_summary(
    *,
    repo_root: Path,
    output_path: Path,
    case_ids: Sequence[str] = DEFAULT_CASE_IDS,
    report_date: str | None = None,
    check: bool = False,
) -> int:
    text = render_velocity_bracket_summary(
        repo_root=repo_root,
        case_ids=case_ids,
        report_date=report_date,
    )
    output_path = output_path if output_path.is_absolute() else repo_root / output_path
    if check:
        existing = output_path.read_text(encoding="utf-8") if output_path.exists() else ""
        if existing == text:
            print(f"up to date: {_rel(output_path, repo_root)}")
            return 0
        diff = difflib.unified_diff(
            existing.splitlines(keepends=True),
            text.splitlines(keepends=True),
            fromfile=str(_rel(output_path, repo_root)),
            tofile="generated",
        )
        print("".join(diff), end="")
        return 1

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(text, encoding="utf-8")
    print(f"wrote: {_rel(output_path, repo_root)}")
    return 0


def _load_case_record(repo_root: Path, case_id: str) -> dict[str, Any]:
    metrics_path = _metrics_path(repo_root, case_id)
    if not metrics_path.exists():
        raise FileNotFoundError(f"missing metrics sidecar for {case_id}: {metrics_path}")
    payload = json.loads(metrics_path.read_text(encoding="utf-8"))
    return {
        "case_id": payload.get("case_id") or case_id,
        "repo_root": repo_root,
        "metrics_path": metrics_path,
        "payload": payload,
        "report_path": repo_root / "reports" / f"gs102_{case_id}_candidate_run.md",
        "run_data_dir": repo_root / "project_state" / "runs" / case_id / "data",
        "manifest_path": (
            repo_root
            / "project_state"
            / "graph_executor"
            / case_id
            / "visualization"
            / "openradioss_animation_manifest.json"
        ),
        "gif_path": (
            repo_root
            / "project_state"
            / "graph_executor"
            / case_id
            / "visualization"
            / "openradioss_animation.gif"
        ),
    }


def _metrics_path(repo_root: Path, case_id: str) -> Path:
    return (
        repo_root
        / "project_state"
        / "graph_executor"
        / case_id
        / "ballistic"
        / "ballistic_metrics.json"
    )


def _table_row(record: dict[str, Any]) -> str:
    payload = record["payload"]
    crossing = payload.get("crossing_evidence") or {}
    solver = payload.get("solver_evidence") or {}
    return (
        f"| `{record['case_id']}` | "
        f"{_number(payload.get('projectile_initial_velocity_m_per_s'))} | "
        f"`{_text(payload.get('perforation_marker'))}` | "
        f"{_number(payload.get('residual_velocity_candidate_m_per_s'))} | "
        f"`{_text(crossing.get('status'))}` | "
        f"{_bool(crossing.get('back_face_crossed'))} | "
        f"{_time(crossing.get('first_back_face_crossing_t_s'))} | "
        f"{_solver_summary(solver)} |"
    )


def _interpretation_lines(
    records: Sequence[dict[str, Any]],
    missing_terms: Sequence[str],
) -> list[str]:
    lines: list[str] = []
    for record in records:
        payload = record["payload"]
        velocity = _number(payload.get("projectile_initial_velocity_m_per_s"))
        marker = _text(payload.get("perforation_marker"))
        crossing = payload.get("crossing_evidence") or {}
        if crossing.get("back_face_crossed") is True:
            lines.extend(
                [
                    f"- {velocity} m/s is `{marker}`: back-face crossing is observed at",
                    "  "
                    f"`{_time(crossing.get('first_back_face_crossing_t_s'))} s` "
                    "with candidate residual velocity",
                    "  "
                    f"`{_number(payload.get('residual_velocity_candidate_m_per_s'))} m/s`.",
                ]
            )
        else:
            front_text = _front_crossing_text(crossing.get("front_face_crossed"))
            lines.extend(
                [
                    f"- {velocity} m/s remains `{marker}`: {front_text}, but",
                    "  back-face crossing is not observed in the sidecar.",
                ]
            )

    lines.extend(_non_monotonic_note_lines(records))

    terms = ", ".join(f"`{term}`" for term in missing_terms) or "`none`"
    lines.extend(
        [
            "- Energy audit is partial. Missing terms are",
            f"  {terms}.",
            "- These trends are engineering-candidate evidence only. They are not",
            "  signed validation and are not benchmark agreement.",
        ]
    )
    return lines


def _non_monotonic_note_lines(records: Sequence[dict[str, Any]]) -> list[str]:
    windows = _transition_windows(records)
    if len(windows) <= 1 and all(
        _classification(left) != "perforated" or _classification(right) != "embedded"
        for left, right in windows
    ):
        return []

    descriptions = "; ".join(
        (
            f"`{_velocity(left)} m/s -> {_velocity(right)} m/s`: "
            f"{_classification(left)} -> {_classification(right)}"
        )
        for left, right in windows
    )
    if not descriptions:
        return []
    return [
        "- Non-monotonic candidate response is present across adjacent velocities:",
        f"  {descriptions}.",
        "- Treat this as a Tier 1 diagnostic pattern, not a single physical threshold.",
    ]


def _transition_windows(
    records: Sequence[dict[str, Any]],
) -> list[tuple[dict[str, Any], dict[str, Any]]]:
    windows: list[tuple[dict[str, Any], dict[str, Any]]] = []
    for left, right in zip(records, records[1:], strict=False):
        left_class = _classification(left)
        right_class = _classification(right)
        if "unknown" in {left_class, right_class}:
            continue
        if left_class != right_class:
            windows.append((left, right))
    return windows


def _classification(record: dict[str, Any]) -> str:
    payload = record["payload"]
    crossing = payload.get("crossing_evidence") or {}
    marker = payload.get("perforation_marker")
    if crossing.get("back_face_crossed") is True or marker == "perforated_candidate":
        return "perforated"
    if crossing.get("back_face_crossed") is False or marker == "embedded_candidate":
        return "embedded"
    return "unknown"


def _velocity(record: dict[str, Any]) -> str:
    return _number(record["payload"].get("projectile_initial_velocity_m_per_s"))


def _artifact_lines(record: dict[str, Any]) -> list[str]:
    velocity = _number(record["payload"].get("projectile_initial_velocity_m_per_s"))
    repo_root = record["repo_root"]
    return [
        f"### {velocity} m/s",
        "",
        "- Case report:",
        f"  `{_rel(record['report_path'], repo_root)}`",
        "- Runtime deck/log directory:",
        f"  `{_rel(record['run_data_dir'], repo_root)}`",
        "- Metrics:",
        f"  `{_rel(record['metrics_path'], repo_root)}`",
        "- Visualization manifest:",
        f"  `{_rel(record['manifest_path'], repo_root)}`",
        "- GIF:",
        f"  `{_rel(record['gif_path'], repo_root)}`",
        "",
    ]


def _merged_missing_terms(records: Sequence[dict[str, Any]]) -> list[str]:
    terms: list[str] = []
    for record in records:
        audit = record["payload"].get("partial_energy_audit") or {}
        for term in audit.get("missing_terms") or []:
            if isinstance(term, str) and term not in terms:
                terms.append(term)
    return terms


def _solver_summary(solver: dict[str, Any]) -> str:
    live = solver.get("live_solid_count")
    total = solver.get("total_solid_count")
    live_text = f"{live} of {total}" if live is not None and total is not None else "n/a"
    return (
        f"{_bool(solver.get('engine_normal_termination'))} / "
        f"{_number(solver.get('engine_cycle_count'))} / "
        f"{_number(solver.get('animation_frame_count'))} / {live_text}"
    )


def _front_crossing_text(value: Any) -> str:
    if value is True:
        return "front-face crossing is observed"
    if value is False:
        return "front-face crossing is not observed"
    return "front-face crossing is not confirmed"


def _number(value: Any) -> str:
    if isinstance(value, bool) or value is None:
        return "n/a"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        if value != value:
            return "n/a"
        if value.is_integer():
            return str(int(value))
        return f"{value:.6f}".rstrip("0").rstrip(".")
    return str(value)


def _time(value: Any) -> str:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return "n/a"
    return f"{float(value):.9f}"


def _bool(value: Any) -> str:
    if value is True:
        return "true"
    if value is False:
        return "false"
    return "n/a"


def _text(value: Any) -> str:
    return str(value) if value is not None else "n/a"


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
    parser.add_argument("--check", action="store_true")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    return write_velocity_bracket_summary(
        repo_root=Path(args.repo_root),
        output_path=Path(args.output),
        case_ids=tuple(args.case_ids) if args.case_ids else DEFAULT_CASE_IDS,
        report_date=args.report_date,
        check=args.check,
    )


if __name__ == "__main__":
    raise SystemExit(main())
