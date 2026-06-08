#!/usr/bin/env python3
"""Extract GS-102 CFL 0.85 element alive-state and centroid history.

Tier 1 engineering-candidate diagnostics only. This script reads existing
OpenRadioss animation frames under ``project_state/runs/**`` and writes
diagnostic sidecars under ``project_state/**`` plus a Markdown report. It does
not modify solver decks and does not promote any result to signed validation.
"""

from __future__ import annotations

import argparse
import json
import re
from collections.abc import Sequence
from datetime import date
from pathlib import Path
from typing import Any

REPO_ROOT_DEFAULT = Path(__file__).resolve().parents[1]
DEFAULT_CASE_IDS = (
    "GS-102-transient-refined-cfl085-v365-bracket-20260512",
    "GS-102-transient-refined-cfl085-v375-bracket-20260512",
    "GS-102-transient-refined-cfl085-v385-bracket-20260512",
)
DEFAULT_GROUPS: dict[str, tuple[int, ...]] = {
    "early_deleted_23_24_29_30": (23, 24, 29, 30),
    "late_deleted_22_25_28_31": (22, 25, 28, 31),
}
DEFAULT_JSON_OUTPUT = Path(
    "project_state/element_history/gs102_cfl085_element_history_20260512.json"
)
DEFAULT_REPORT_OUTPUT = Path("reports/gs102_cfl085_element_history_20260512.md")
DEFAULT_SYNC_GIF = Path("project_state/visualizations/gs102_cfl085_365_375_385_sync.gif")
CLAIM_BOUNDARY = "tier1_engineering_candidate; not_signed_validation; not_benchmark_agreement"
_ANIM_RE = re.compile(r"A\d{3,4}(?:\.gz)?$")


def build_element_history_payload(
    *,
    repo_root: Path,
    case_ids: Sequence[str] = DEFAULT_CASE_IDS,
    groups: dict[str, tuple[int, ...]] = DEFAULT_GROUPS,
    report_date: str | None = None,
) -> dict[str, Any]:
    report_date = report_date or date.today().isoformat()
    return {
        "report_date": report_date,
        "claim_boundary": CLAIM_BOUNDARY,
        "scope": "GS-102 CFL 0.85 element alive-state and centroid history",
        "source_deck_dir": "project_state/diagnostic_sources/GS-102-v365-cfl_085/data",
        "groups": {name: list(ids) for name, ids in groups.items()},
        "cases": [
            _build_case_history(repo_root=repo_root, case_id=case_id, groups=groups)
            for case_id in case_ids
        ],
        "limitations": [
            "Tier 1 diagnostic only; not signed validation; not benchmark agreement.",
            "Centroids are computed from RadiossReader node coordinates for "
            "selected solid elements.",
            "Alive-state comes from element_solid_is_alive; contact force history "
            "is not extracted.",
            "Raw animation timestep values are retained as frame-order evidence only.",
        ],
    }


def render_element_history_report(payload: dict[str, Any]) -> str:
    lines = [
        f"# GS-102 CFL 0.85 Element History - {payload['report_date']}",
        "",
        "> Status: Tier 1 element-history diagnostic.",
        "> Claim boundary: not signed validation; not benchmark agreement.",
        "",
        "## Purpose",
        "",
        "Map selected solid-element alive-state and centroid histories for the",
        "fixed-CFL 0.85 GS-102 local window. The focus is the early deleted group",
        "`23/24/29/30` and the later deleted group `22/25/28/31` across 365,",
        "375, and 385 m/s candidate runs.",
        "",
        "No solver run is launched by this report. Runtime inputs and outputs stay",
        "under `project_state/**`; `golden_samples/**` is not modified.",
        "",
        "## Group Summary",
        "",
        "| Case | Marker | Back crossed | Group | Final live / total | "
        "First any-dead frame | First all-dead frame | First all-dead timestep | "
        "Final centroid-x range mm |",
        "|---|---|---|---|---:|---|---|---:|---:|",
    ]
    for case in payload["cases"]:
        for group_name, group in case["groups"].items():
            lines.append(_group_summary_row(case, group_name, group))

    lines.extend(
        [
            "",
            "## Element-Level History Summary",
            "",
            "| Case | Group | Element | First dead frame | First dead timestep | "
            "Final alive | Initial centroid mm | Final centroid mm |",
            "|---|---|---:|---|---:|---|---|---|",
        ]
    )
    for case in payload["cases"]:
        for group_name, group in case["groups"].items():
            for element in group["elements"]:
                lines.append(_element_summary_row(case, group_name, element))

    lines.extend(
        [
            "",
            "## Mechanism Reading",
            "",
            "- The 375 m/s case is the only selected fixed-CFL 0.85 run whose centroid",
            "  trace crosses the back face. In that run, the later `22/25/28/31`",
            "  group remains alive through the final animation frame.",
            "- The 365 m/s and 385 m/s cases do not show back-face crossing, and both",
            "  eventually lose the later `22/25/28/31` group. This means deletion",
            "  count alone is not a perforation explanation for this local window.",
            "- Treat this as a numerical-path clue. The available sidecars do not",
            "  expose contact-force history, contact friction work, hourglass energy,",
            "  or full plastic-dissipation accounting.",
            "- Raw animation timesteps are retained for frame-order comparison only;",
            "  this report does not claim a unified physical clock between metrics,",
            "  manifests, and engine-log text.",
            "",
            "## Visual Comparison",
            "",
            "- Synchronized full-flow GIF:",
            f"  `{DEFAULT_SYNC_GIF}`",
            "",
            "## Artifact Index",
            "",
        ]
    )
    for case in payload["cases"]:
        lines.extend(_artifact_lines(case))

    lines.extend(
        [
            "## Hard Boundaries",
            "",
            "- Tier 1 only: no signed validation, no benchmark comparison, no tolerance",
            "  agreement, and no independent reviewer signoff.",
            "- `perforated_candidate` means the current centroid sidecar observed",
            "  back-face crossing; it does not define a Tier 2 perforation threshold.",
            "- The full-flow animation is visual evidence for the run sequence, not a",
            "  substitute for element-level contact or energy accounting.",
            "",
        ]
    )
    return "\n".join(lines)


def write_element_history_outputs(
    *,
    repo_root: Path,
    json_output: Path,
    report_output: Path,
    case_ids: Sequence[str] = DEFAULT_CASE_IDS,
    groups: dict[str, tuple[int, ...]] = DEFAULT_GROUPS,
    report_date: str | None = None,
    check: bool = False,
) -> int:
    payload = build_element_history_payload(
        repo_root=repo_root,
        case_ids=case_ids,
        groups=groups,
        report_date=report_date,
    )
    report_text = render_element_history_report(payload)
    json_path = _resolve(repo_root, json_output)
    report_path = _resolve(repo_root, report_output)
    json_text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if check:
        if json_path.read_text(encoding="utf-8") != json_text:
            print(f"out of date: {_rel(json_path, repo_root)}")
            return 1
        if report_path.read_text(encoding="utf-8") != report_text:
            print(f"out of date: {_rel(report_path, repo_root)}")
            return 1
        print(f"up to date: {_rel(json_path, repo_root)}")
        print(f"up to date: {_rel(report_path, repo_root)}")
        return 0

    _assert_project_state_output(json_path, repo_root)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json_text, encoding="utf-8")
    report_path.write_text(report_text, encoding="utf-8")
    print(f"wrote: {_rel(json_path, repo_root)}")
    print(f"wrote: {_rel(report_path, repo_root)}")
    return 0


def _build_case_history(
    *,
    repo_root: Path,
    case_id: str,
    groups: dict[str, tuple[int, ...]],
) -> dict[str, Any]:
    metrics_path = (
        repo_root
        / "project_state"
        / "graph_executor"
        / case_id
        / "ballistic"
        / "ballistic_metrics.json"
    )
    metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
    run_data_dir = repo_root / "project_state" / "runs" / case_id / "data"
    frame_paths = _animation_files(run_data_dir)
    frame_items = [_load_frame_item(path) for path in frame_paths]
    case = _case_history_from_frames(
        case_id=case_id,
        metrics=metrics,
        frame_items=frame_items,
        groups=groups,
    )
    case.update(
        {
            "metrics_path": _rel(metrics_path, repo_root),
            "run_data_dir": _rel(run_data_dir, repo_root),
            "report_path": f"reports/gs102_{case_id}_candidate_run.md",
            "animation_manifest_path": (
                "project_state/graph_executor/"
                f"{case_id}/visualization/openradioss_animation_manifest.json"
            ),
            "animation_gif_path": (
                "project_state/graph_executor/"
                f"{case_id}/visualization/openradioss_animation.gif"
            ),
        }
    )
    return case


def _case_history_from_frames(
    *,
    case_id: str,
    metrics: dict[str, Any],
    frame_items: Sequence[dict[str, Any]],
    groups: dict[str, tuple[int, ...]],
) -> dict[str, Any]:
    if not frame_items:
        raise ValueError(f"{case_id}: no animation frames available")
    case: dict[str, Any] = {
        "case_id": case_id,
        "projectile_initial_velocity_m_per_s": metrics.get(
            "projectile_initial_velocity_m_per_s"
        ),
        "perforation_marker": metrics.get("perforation_marker"),
        "back_face_crossed": (metrics.get("crossing_evidence") or {}).get(
            "back_face_crossed"
        ),
        "first_back_face_crossing_t_s": (metrics.get("crossing_evidence") or {}).get(
            "first_back_face_crossing_t_s"
        ),
        "residual_velocity_candidate_m_per_s": metrics.get(
            "residual_velocity_candidate_m_per_s"
        ),
        "frame_count": len(frame_items),
        "groups": {},
    }
    for group_name, element_ids in groups.items():
        elements = [
            _element_history_from_frames(frame_items, int(element_id))
            for element_id in element_ids
        ]
        case["groups"][group_name] = _summarize_group(element_ids, elements)
    return case


def _element_history_from_frames(
    frame_items: Sequence[dict[str, Any]],
    element_id: int,
) -> dict[str, Any]:
    history: list[dict[str, Any]] = []
    first_dead: dict[str, Any] | None = None
    for frame_index, frame in enumerate(frame_items):
        element_index = _element_index(frame, element_id)
        node_indexes = _resolve_node_indexes(
            frame["element_solid_node_indexes"][element_index],
            len(frame["node_coordinates"]),
        )
        centroid = _centroid_mm(frame["node_coordinates"], node_indexes)
        alive = bool(frame["element_solid_is_alive"][element_index])
        source = Path(str(frame["source"])).name
        sample = {
            "frame_index": frame_index,
            "source": source,
            "timestep": frame.get("timestep"),
            "alive": alive,
            "centroid_mm": centroid,
        }
        history.append(sample)
        if first_dead is None and not alive:
            first_dead = {
                "frame_index": frame_index,
                "source": source,
                "timestep": frame.get("timestep"),
            }
    return {
        "element_id": element_id,
        "initial_centroid_mm": history[0]["centroid_mm"],
        "final_centroid_mm": history[-1]["centroid_mm"],
        "final_alive": history[-1]["alive"],
        "first_dead": first_dead,
        "history": history,
    }


def _summarize_group(
    element_ids: Sequence[int],
    elements: Sequence[dict[str, Any]],
) -> dict[str, Any]:
    final_alive_count = sum(1 for element in elements if element["final_alive"])
    first_any_dead = min(
        (element["first_dead"] for element in elements if element["first_dead"]),
        key=lambda item: item["frame_index"],
        default=None,
    )
    first_all_dead = _first_all_dead(elements)
    final_x_values = [element["final_centroid_mm"][0] for element in elements]
    return {
        "element_ids": list(element_ids),
        "final_alive_count": final_alive_count,
        "total_count": len(elements),
        "first_any_dead": first_any_dead,
        "first_all_dead": first_all_dead,
        "final_centroid_x_range_mm": [
            _round(min(final_x_values)),
            _round(max(final_x_values)),
        ],
        "elements": list(elements),
    }


def _first_all_dead(elements: Sequence[dict[str, Any]]) -> dict[str, Any] | None:
    if not elements:
        return None
    frame_count = len(elements[0]["history"])
    for frame_index in range(frame_count):
        if all(not element["history"][frame_index]["alive"] for element in elements):
            frame = elements[0]["history"][frame_index]
            return {
                "frame_index": frame_index,
                "source": frame["source"],
                "timestep": frame["timestep"],
            }
    return None


def _load_frame_item(path: Path) -> dict[str, Any]:
    from vortex_radioss.animtod3plot.RadiossReader import RadiossReader

    arrays = RadiossReader(str(path)).arrays
    return {
        "source": str(path),
        "timestep": float(arrays.get("timesteps", 0.0) or 0.0),
        "element_solid_ids": arrays["element_solid_ids"],
        "element_solid_node_indexes": arrays["element_solid_node_indexes"],
        "element_solid_is_alive": arrays["element_solid_is_alive"],
        "node_coordinates": arrays["node_coordinates"],
    }


def _animation_files(run_data_dir: Path) -> tuple[Path, ...]:
    return tuple(
        sorted(
            path
            for path in run_data_dir.iterdir()
            if path.is_file() and _ANIM_RE.search(path.name)
        )
    )


def _element_index(frame: dict[str, Any], element_id: int) -> int:
    ids = [int(value) for value in frame["element_solid_ids"]]
    try:
        return ids.index(element_id)
    except ValueError as exc:
        raise ValueError(f"element {element_id} not present in frame {frame['source']}") from exc


def _resolve_node_indexes(indexes: Any, node_count: int) -> list[int]:
    values = [int(value) for value in indexes]
    if not values:
        return values
    if min(values) >= 0 and max(values) < node_count:
        return values
    if min(values) >= 1 and max(values) <= node_count:
        return [value - 1 for value in values]
    raise ValueError(f"node indexes out of bounds for node_count={node_count}: {values}")


def _centroid_mm(node_coordinates: Any, node_indexes: Sequence[int]) -> list[float]:
    return [
        _round(
            sum(float(node_coordinates[index][axis]) for index in node_indexes)
            / len(node_indexes)
        )
        for axis in range(3)
    ]


def _group_summary_row(case: dict[str, Any], group_name: str, group: dict[str, Any]) -> str:
    first_any = group["first_any_dead"] or {}
    first_all = group["first_all_dead"] or {}
    return (
        f"| `{case['case_id']}` | "
        f"`{case.get('perforation_marker')}` | "
        f"{_bool(case.get('back_face_crossed'))} | "
        f"`{group_name}` | "
        f"{group['final_alive_count']} / {group['total_count']} | "
        f"`{first_any.get('source', 'n/a')}` | "
        f"`{first_all.get('source', 'n/a')}` | "
        f"{_number(first_all.get('timestep'))} | "
        f"{_range(group['final_centroid_x_range_mm'])} |"
    )


def _element_summary_row(
    case: dict[str, Any],
    group_name: str,
    element: dict[str, Any],
) -> str:
    first_dead = element["first_dead"] or {}
    return (
        f"| `{case['case_id']}` | "
        f"`{group_name}` | "
        f"{element['element_id']} | "
        f"`{first_dead.get('source', 'n/a')}` | "
        f"{_number(first_dead.get('timestep'))} | "
        f"{_bool(element['final_alive'])} | "
        f"{_centroid_text(element['initial_centroid_mm'])} | "
        f"{_centroid_text(element['final_centroid_mm'])} |"
    )


def _artifact_lines(case: dict[str, Any]) -> list[str]:
    return [
        f"### `{case['case_id']}`",
        "",
        "- Metrics:",
        f"  `{case['metrics_path']}`",
        "- Runtime animation frames:",
        f"  `{case['run_data_dir']}`",
        "- Case report:",
        f"  `{case['report_path']}`",
        "- Full-flow animation GIF:",
        f"  `{case['animation_gif_path']}`",
        "- Animation manifest:",
        f"  `{case['animation_manifest_path']}`",
        "",
    ]


def _centroid_text(values: Sequence[float]) -> str:
    return f"({_number(values[0])}, {_number(values[1])}, {_number(values[2])})"


def _range(values: Sequence[float]) -> str:
    return f"{_number(values[0])}..{_number(values[1])}"


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


def _bool(value: Any) -> str:
    if value is True:
        return "true"
    if value is False:
        return "false"
    return "n/a"


def _round(value: float) -> float:
    return round(float(value), 6)


def _resolve(repo_root: Path, path: Path) -> Path:
    return path if path.is_absolute() else repo_root / path


def _rel(path: Path, repo_root: Path) -> str:
    try:
        return str(path.resolve().relative_to(repo_root.resolve()))
    except ValueError:
        return str(path)


def _assert_project_state_output(path: Path, repo_root: Path) -> None:
    try:
        parts = path.resolve().relative_to(repo_root.resolve()).parts
    except ValueError:
        parts = path.resolve().parts
    if "golden_samples" in parts:
        raise ValueError(f"refuses to write inside golden_samples/**: {path}")
    if "project_state" not in parts:
        raise ValueError(f"runtime diagnostic output must live under project_state/: {path}")


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=str(REPO_ROOT_DEFAULT))
    parser.add_argument("--json-output", default=str(DEFAULT_JSON_OUTPUT))
    parser.add_argument("--report-output", default=str(DEFAULT_REPORT_OUTPUT))
    parser.add_argument("--report-date", default="2026-05-12")
    parser.add_argument("--case-id", action="append", dest="case_ids")
    parser.add_argument("--check", action="store_true")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    return write_element_history_outputs(
        repo_root=Path(args.repo_root),
        json_output=Path(args.json_output),
        report_output=Path(args.report_output),
        case_ids=tuple(args.case_ids) if args.case_ids else DEFAULT_CASE_IDS,
        report_date=args.report_date,
        check=args.check,
    )


if __name__ == "__main__":
    raise SystemExit(main())
