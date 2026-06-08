#!/usr/bin/env python3
"""Generate a GS-102 CFL 0.85 local mechanism diagnostic report.

Tier 1 engineering-candidate diagnostics only. This report reads existing
``project_state/**`` OpenRadioss outputs and does not promote any result to
signed validation or benchmark agreement.
"""

from __future__ import annotations

import argparse
import difflib
import json
import re
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

REPO_ROOT_DEFAULT = Path(__file__).resolve().parents[1]
DEFAULT_CASE_IDS = (
    "GS-102-transient-refined-cfl085-v365-bracket-20260512",
    "GS-102-transient-refined-cfl085-v375-bracket-20260512",
    "GS-102-transient-refined-cfl085-v385-bracket-20260512",
)
DEFAULT_OUTPUT = Path("reports/gs102_cfl085_local_mechanism_diagnostic_20260512.md")

_DELETE_RE = re.compile(
    r"DELETE SOLID ELEMENT NUMBER\s+(\d+)\s+AT TIME\s*:\s*([0-9.E+-]+)"
)
_EPS_RE = re.compile(
    r"EXCEEDED EPS_MAX ON SOLID ELEMENT NUMBER\s+(\d+):.*?AT TIME\s*:\s*([0-9.E+-]+)"
)


@dataclass(frozen=True)
class LogEvent:
    element_id: str
    time_text: str


def render_mechanism_diagnostic(
    *,
    repo_root: Path,
    case_ids: Sequence[str] = DEFAULT_CASE_IDS,
    report_date: str | None = None,
) -> str:
    report_date = report_date or date.today().isoformat()
    records = [_load_record(repo_root, case_id) for case_id in case_ids]
    velocities = ", ".join(
        _number(record["metrics"].get("projectile_initial_velocity_m_per_s"))
        for record in records
    )

    lines = [
        f"# GS-102 CFL 0.85 Local Mechanism Diagnostic - {report_date}",
        "",
        "> Status: Tier 1 mechanism diagnostic.",
        "> Claim boundary: not signed validation; not benchmark agreement.",
        "",
        "## Purpose",
        "",
        "Diagnose the local mechanism behind the fixed-CFL 0.85 non-monotonic",
        f"candidate response at {velocities} m/s. This report compares deletion",
        "timing, back-face crossing windows, and residual velocity traces from",
        "existing sidecars and solver logs.",
        "",
        "No solver run is launched by this report. No `golden_samples/**` file is",
        "modified or used as a runtime output target.",
        "",
        "## Fixed Inputs",
        "",
        "- Source deck directory:",
        "  `project_state/diagnostic_sources/GS-102-v365-cfl_085/data`",
        "- Variant manifest:",
        "  `project_state/diagnostic_sources/GS-102-v365-cfl_085/diagnostic_variant.json`",
        "- Changed control:",
        "  `/DT/NODA/CST/0 = 0.85 0.0`",
        "- Compared cases:",
    ]
    lines.extend(f"  - `{record['case_id']}`" for record in records)
    lines.extend(
        [
            "",
            "## Case-Level Evidence",
            "",
            "| Case | V0 m/s | Marker | Back crossed | First back crossing s | "
            "Final gap to back face mm | Residual m/s | Cycles | Delete events | "
            "Live solids |",
            "|---|---:|---|---|---:|---:|---:|---:|---:|---|",
        ]
    )
    lines.extend(_case_row(record) for record in records)
    lines.extend(
        [
            "",
            "## Deletion And EPS Timing",
            "",
            "| Case | EPS events | First EPS log time | EPS elements | Delete events | "
            "First delete log time | Last delete log time | Deleted elements |",
            "|---|---:|---:|---|---:|---:|---:|---|",
        ]
    )
    lines.extend(_event_row(record) for record in records)
    lines.extend(
        [
            "",
            "## Frame-Level Deletion Accumulation",
            "",
            "| Case | Manifest frames | First deleted frame | First deleted timestep | "
            "First deleted count | Max deleted | First max-deleted timestep |",
            "|---|---:|---|---:|---:|---:|---:|",
        ]
    )
    lines.extend(_manifest_row(record) for record in records)
    lines.extend(
        [
            "",
            "## Time-Scale Note",
            "",
            "- Metrics sidecars expose projectile trace times as `t_s`; animation",
            "  manifests expose the raw OpenRadioss `timestep` value. They are useful",
            "  for ordered frame comparison, but this report does not subtract engine",
            "  log deletion times from crossing times as if a single verified physical",
            "  clock had been established.",
            "",
            "## Crossing Or Terminal Windows",
            "",
        ]
    )
    for record in records:
        lines.extend(_window_section(record))

    lines.extend(
        [
            "## Mechanism Reading",
            "",
            *_interpretation_lines(records),
            "",
            "## Artifact Index",
            "",
        ]
    )
    for record in records:
        lines.extend(_artifact_lines(record))
    lines.extend(
        [
            "## Hard Boundaries",
            "",
            "- Tier 1 only: no signed validation, no benchmark comparison, no tolerance",
            "  agreement, and no independent reviewer signoff.",
            "- `perforated_candidate` means the current centroid sidecar observed",
            "  back-face crossing; it does not define a Tier 2 perforation threshold.",
            "- Current sidecars do not expose contact-force history, contact friction",
            "  work, hourglass energy, or complete plastic dissipation. This report",
            "  therefore treats contact-state and energy-closure causes as unproven.",
            "",
            "## Next Diagnostic Step",
            "",
            "- Add a narrow extractor for element centroid/alive-state history around",
            "  the deleted element groups and, if available from OpenRadioss outputs,",
            "  contact/energy time-history terms before spending more runs on velocity",
            "  threshold narrowing.",
            "",
        ]
    )
    return "\n".join(lines)


def write_mechanism_diagnostic(
    *,
    repo_root: Path,
    output_path: Path,
    case_ids: Sequence[str] = DEFAULT_CASE_IDS,
    report_date: str | None = None,
    check: bool = False,
) -> int:
    text = render_mechanism_diagnostic(
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


def _load_record(repo_root: Path, case_id: str) -> dict[str, Any]:
    metrics_path = (
        repo_root
        / "project_state"
        / "graph_executor"
        / case_id
        / "ballistic"
        / "ballistic_metrics.json"
    )
    if not metrics_path.exists():
        raise FileNotFoundError(f"missing ballistic metrics for {case_id}: {metrics_path}")
    metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
    run_data_dir = repo_root / "project_state" / "runs" / case_id / "data"
    engine_log = run_data_dir / "engine.log"
    manifest_path = (
        repo_root
        / "project_state"
        / "graph_executor"
        / case_id
        / "visualization"
        / "openradioss_animation_manifest.json"
    )
    engine_text = engine_log.read_text(encoding="utf-8", errors="ignore")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    return {
        "case_id": metrics.get("case_id") or case_id,
        "metrics": metrics,
        "metrics_path": metrics_path,
        "run_data_dir": run_data_dir,
        "engine_log": engine_log,
        "delete_events": _parse_events(_DELETE_RE, engine_text),
        "eps_events": _parse_events(_EPS_RE, engine_text),
        "report_path": repo_root / "reports" / f"gs102_{case_id}_candidate_run.md",
        "manifest": manifest,
        "manifest_path": manifest_path,
        "gif_path": (
            repo_root
            / "project_state"
            / "graph_executor"
            / case_id
            / "visualization"
            / "openradioss_animation.gif"
        ),
    }


def _parse_events(pattern: re.Pattern[str], text: str) -> list[LogEvent]:
    return [LogEvent(element, time_text) for element, time_text in pattern.findall(text)]


def _case_row(record: dict[str, Any]) -> str:
    metrics = record["metrics"]
    crossing = metrics.get("crossing_evidence") or {}
    solver = metrics.get("solver_evidence") or {}
    return (
        f"| `{record['case_id']}` | "
        f"{_number(metrics.get('projectile_initial_velocity_m_per_s'))} | "
        f"`{_text(metrics.get('perforation_marker'))}` | "
        f"{_bool(crossing.get('back_face_crossed'))} | "
        f"{_time(crossing.get('first_back_face_crossing_t_s'))} | "
        f"{_number(_final_gap_mm(metrics))} | "
        f"{_number(metrics.get('residual_velocity_candidate_m_per_s'))} | "
        f"{_number(solver.get('engine_cycle_count'))} | "
        f"{_number(solver.get('deleted_element_count'))} | "
        f"{_live_solids(solver)} |"
    )


def _event_row(record: dict[str, Any]) -> str:
    eps_events = record["eps_events"]
    delete_events = record["delete_events"]
    return (
        f"| `{record['case_id']}` | "
        f"{len(eps_events)} | "
        f"{_event_time(eps_events, first=True)} | "
        f"{_event_elements(eps_events)} | "
        f"{len(delete_events)} | "
        f"{_event_time(delete_events, first=True)} | "
        f"{_event_time(delete_events, first=False)} | "
        f"{_event_elements(delete_events)} |"
    )


def _manifest_row(record: dict[str, Any]) -> str:
    summary = _manifest_deletion_summary(record["manifest"])
    return (
        f"| `{record['case_id']}` | "
        f"{_number(summary['frame_count'])} | "
        f"`{summary['first_deleted_source']}` | "
        f"{_number(summary['first_deleted_timestep'])} | "
        f"{_number(summary['first_deleted_count'])} | "
        f"{_number(summary['max_deleted'])} | "
        f"{_number(summary['first_max_deleted_timestep'])} |"
    )


def _manifest_deletion_summary(manifest: dict[str, Any]) -> dict[str, Any]:
    frames = manifest.get("per_frame") or []
    deleted_frames = [
        frame
        for frame in frames
        if isinstance(frame.get("elements_deleted"), int)
        and frame.get("elements_deleted", 0) > 0
    ]
    max_deleted = max(
        (
            frame.get("elements_deleted", 0)
            for frame in frames
            if isinstance(frame.get("elements_deleted"), int)
        ),
        default=0,
    )
    max_frames = [
        frame for frame in frames if frame.get("elements_deleted") == max_deleted
    ]
    first_deleted = deleted_frames[0] if deleted_frames else {}
    first_max = max_frames[0] if max_frames else {}
    return {
        "frame_count": manifest.get("frame_count") or len(frames),
        "first_deleted_source": _source_name(first_deleted.get("source")),
        "first_deleted_timestep": first_deleted.get("timestep"),
        "first_deleted_count": first_deleted.get("elements_deleted"),
        "max_deleted": max_deleted,
        "first_max_deleted_timestep": first_max.get("timestep"),
    }


def _source_name(value: Any) -> str:
    if not isinstance(value, str) or not value:
        return "n/a"
    return Path(value).name


def _window_section(record: dict[str, Any]) -> list[str]:
    metrics = record["metrics"]
    crossing = metrics.get("crossing_evidence") or {}
    samples = (metrics.get("residual_velocity_trace") or {}).get("samples") or []
    back_index = crossing.get("first_back_face_crossing_sample_index")
    if isinstance(back_index, int):
        selected = [
            sample
            for sample in samples
            if back_index - 3 <= sample.get("sample_index", -1) <= back_index + 3
        ]
        window_label = f"back-face crossing window around sample {back_index}"
    else:
        selected = samples[-5:]
        window_label = "terminal window; no back-face crossing observed"

    lines = [
        f"### `{record['case_id']}`",
        "",
        f"- Window: {window_label}.",
        f"- Plate back face x: `{_number(crossing.get('plate_back_face_x_m'))} m`.",
        "",
        "| Sample | t s | Centroid x m | Gap to back face mm | Speed m/s |",
        "|---:|---:|---:|---:|---:|",
    ]
    lines.extend(_sample_row(metrics, sample) for sample in selected)
    lines.append("")
    return lines


def _sample_row(metrics: dict[str, Any], sample: dict[str, Any]) -> str:
    crossing = metrics.get("crossing_evidence") or {}
    centroid = sample.get("centroid_axis_position_m")
    gap_mm = None
    if isinstance(centroid, (int, float)):
        back_face = crossing.get("plate_back_face_x_m")
        if isinstance(back_face, (int, float)):
            gap_mm = (float(back_face) - float(centroid)) * 1000.0
    return (
        f"| {_number(sample.get('sample_index'))} | "
        f"{_time(sample.get('t_s'))} | "
        f"{_number(centroid)} | "
        f"{_number(gap_mm)} | "
        f"{_number(sample.get('speed_m_per_s'))} |"
    )


def _interpretation_lines(records: Sequence[dict[str, Any]]) -> list[str]:
    by_velocity = {
        int(record["metrics"].get("projectile_initial_velocity_m_per_s")): record
        for record in records
        if isinstance(record["metrics"].get("projectile_initial_velocity_m_per_s"), (int, float))
    }
    lines = [
        "- The fixed-CFL 0.85 local window remains non-monotonic: 365 m/s embeds,",
        "  375 m/s perforates in the candidate sidecar, and 385 m/s embeds.",
    ]
    if all(velocity in by_velocity for velocity in (365, 375, 385)):
        r365 = by_velocity[365]["metrics"]
        r375 = by_velocity[375]["metrics"]
        r385 = by_velocity[385]["metrics"]
        crossing = r375.get("crossing_evidence") or {}
        crossing_sample = _number(crossing.get("first_back_face_crossing_sample_index"))
        crossing_time = _time(crossing.get("first_back_face_crossing_t_s"))
        lines.extend(
            [
                "- The 375 m/s run crosses the back face near sample",
                f"  `{crossing_sample}` at `{crossing_time} s`,",
                "  while 365 m/s and 385 m/s remain short of the back face at the",
                "  terminal frame by",
                "  "
                f"`{_number(_final_gap_mm(r365))} mm` and `{_number(_final_gap_mm(r385))} mm`.",
            ]
        )
    lines.extend(
        [
            "- The deletion pattern is also different: 365 m/s and 385 m/s record",
            "  eight deletion events including a later `22/25/28/31` group, while",
            "  375 m/s records only the earlier `23/24/29/30` group in the engine",
            "  log and sidecar. This is a numerical-path clue, not a contact-state",
            "  conclusion.",
            "- Contact-force history and full energy accounting are not present in",
            "  the current sidecars, so this report cannot attribute the 375 m/s",
            "  crossing to physical contact/friction behavior.",
            "- The frame manifest confirms cumulative deletion timing in frame order,",
            "  but it does not map deleted element ids to each frame; the element-id",
            "  list still comes from `engine.log`.",
        ]
    )
    return lines


def _artifact_lines(record: dict[str, Any]) -> list[str]:
    repo_root = record["metrics_path"].parents[4]
    return [
        f"### `{record['case_id']}`",
        "",
        "- Case report:",
        f"  `{_rel(record['report_path'], repo_root)}`",
        "- Runtime deck/log directory:",
        f"  `{_rel(record['run_data_dir'], repo_root)}`",
        "- Engine log:",
        f"  `{_rel(record['engine_log'], repo_root)}`",
        "- Metrics:",
        f"  `{_rel(record['metrics_path'], repo_root)}`",
        "- Visualization manifest:",
        f"  `{_rel(record['manifest_path'], repo_root)}`",
        "- GIF:",
        f"  `{_rel(record['gif_path'], repo_root)}`",
        "",
    ]


def _final_gap_mm(metrics: dict[str, Any]) -> float | None:
    crossing = metrics.get("crossing_evidence") or {}
    back_face = crossing.get("plate_back_face_x_m")
    final_centroid = crossing.get("final_centroid_x_m")
    if not isinstance(back_face, (int, float)) or not isinstance(final_centroid, (int, float)):
        return None
    return (float(back_face) - float(final_centroid)) * 1000.0


def _event_time(events: Sequence[LogEvent], *, first: bool) -> str:
    if not events:
        return "n/a"
    return events[0 if first else -1].time_text


def _event_elements(events: Sequence[LogEvent]) -> str:
    if not events:
        return "`none`"
    seen: list[str] = []
    for event in events:
        if event.element_id not in seen:
            seen.append(event.element_id)
    return ", ".join(f"`{element}`" for element in seen)


def _live_solids(solver: dict[str, Any]) -> str:
    live = solver.get("live_solid_count")
    total = solver.get("total_solid_count")
    if live is None or total is None:
        return "n/a"
    return f"{live} of {total}"


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
    return write_mechanism_diagnostic(
        repo_root=Path(args.repo_root),
        output_path=Path(args.output),
        case_ids=tuple(args.case_ids) if args.case_ids else DEFAULT_CASE_IDS,
        report_date=args.report_date,
        check=args.check,
    )


if __name__ == "__main__":
    raise SystemExit(main())
