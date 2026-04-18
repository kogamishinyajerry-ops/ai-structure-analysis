"""Visualization & Analysis Agent — report, VTP, and FAIR manifest generation."""

from __future__ import annotations

import platform
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

from reporters.markdown import generate_report
from reporters.vtp import export_vtp
from schemas.sim_state import FaultClass, SimState
from tools.frd_parser import extract_field_extremes, parse_frd


def _git_output(*args: str) -> str:
    repo_root = Path(__file__).resolve().parent.parent
    try:
        return subprocess.check_output(list(args), cwd=repo_root, text=True).strip()
    except Exception:
        return "unknown"


def _run_id_from_state(state: SimState, project_dir: Path) -> str:
    return str(state.get("run_id") or project_dir.name)


def _build_manifest(state: SimState, plan: Any, project_dir: Path) -> dict[str, Any]:
    solve_metadata = state.get("solve_metadata") or {}
    return {
        "case_id": plan.case_id,
        "run_id": _run_id_from_state(state, project_dir),
        "generated_at": datetime.now(UTC).isoformat(),
        "git": {
            "branch": _git_output("git", "rev-parse", "--abbrev-ref", "HEAD"),
            "sha": _git_output("git", "rev-parse", "HEAD"),
        },
        "tool_versions": {
            "calculix": solve_metadata.get("ccx_version", "unknown"),
            "python": platform.python_version(),
            "frd_parser": "ascii-v2",
            "reporter": "markdown-v2",
            "vtp_exporter": "point-cloud-v1",
        },
        "seed": state.get("seed"),
    }


def _write_manifest(manifest: dict[str, Any], project_dir: Path) -> Path:
    manifest_path = project_dir / "manifest.yaml"
    manifest_path.write_text(yaml.safe_dump(manifest, sort_keys=False), encoding="utf-8")
    return manifest_path


def run(state: SimState) -> dict[str, Any]:
    """Viz agent entrypoint (LangGraph node signature)."""
    plan = state.get("plan")
    if not plan:
        raise ValueError("SimState is missing a SimPlan.")

    project_dir = Path(state.get("project_state_dir", "."))
    report_dir = project_dir / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)

    frd_path_str = state.get("frd_path")
    if not frd_path_str:
        artifacts = state.get("artifacts", [])
        frd_path_str = next((path for path in artifacts if path.endswith(".frd")), None)
    if not frd_path_str:
        return {"fault_class": FaultClass.UNKNOWN}

    parsed = parse_frd(Path(frd_path_str))
    approval_metrics = []
    for field_name in ("displacement", "stress"):
        field_metric = extract_field_extremes(parsed, field_name)
        if field_metric.get("max_magnitude") is not None:
            approval_metrics.append(field_metric)

    manifest = _build_manifest(state, plan, project_dir)
    manifest_path = _write_manifest(manifest, project_dir)

    report_ctx: dict[str, Any] = {
        "case_id": plan.case_id,
        "description": plan.description,
        "verdict": state.get("verdict", "Needs Review"),
        "fields": approval_metrics,
        "reference_values": plan.reference_values,
        "wall_time_s": (state.get("solve_metadata") or {}).get("wall_time_s"),
        "manifest_path": str(manifest_path),
    }
    report_path = generate_report(report_ctx, report_dir)

    reports = {"markdown": str(report_path), "manifest": str(manifest_path)}
    artifacts = state.get("artifacts", []).copy()
    artifacts.extend([str(report_path), str(manifest_path)])

    if getattr(plan.objectives, "export_vtp", False):
        vtp_path = export_vtp(parsed, report_dir)
        reports["vtp"] = str(vtp_path)
        artifacts.append(str(vtp_path))

    return {
        "fault_class": FaultClass.NONE,
        "reports": reports,
        "artifacts": artifacts,
    }
