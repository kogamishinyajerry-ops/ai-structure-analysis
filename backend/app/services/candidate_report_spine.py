"""Candidate Report Spine builder for Tier 1 report evidence.

This module is intentionally additive: it does not validate physics or promote
signed claims. It packages the evidence the report path can actually see and
labels unavailable Tier 1/Tier 2 evidence explicitly.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Optional

from ..parsers.frd_parser import FRDParseResult


REPO_ROOT = Path(__file__).resolve().parents[3]


def build_candidate_report_spine(
    *,
    result: FRDParseResult,
    metrics: Mapping[str, Any],
    validation: Mapping[str, Any],
    case_id: Optional[str],
    golden_samples_root: Path,
    source_path: Optional[Path] = None,
    original_filename: Optional[str] = None,
    solver_job_status: Optional[Mapping[str, Any]] = None,
) -> dict[str, Any]:
    """Build the FM-03 candidate reproducibility package payload."""

    expected = _load_expected_results(golden_samples_root, case_id)
    case_dir = golden_samples_root / case_id if case_id else None
    input_deck = _find_input_deck(case_dir)
    solver_log_artifacts = _find_solver_log_artifacts(case_dir, case_id)
    mesh_meta_artifacts = _find_mesh_meta_artifacts(case_id)
    mesh_quality_artifacts = _find_mesh_quality_artifacts(case_id)
    mesh_convergence_artifacts = _find_mesh_convergence_artifacts(case_id)

    artifacts = []
    if source_path is not None:
        artifacts.append(
            _artifact_record(
                "result_frd",
                source_path,
                "Uploaded or selected CalculiX FRD result consumed by report generation",
                display_path=f"upload:{original_filename or source_path.name}",
            )
        )
    if input_deck is not None:
        artifacts.append(
            _artifact_record(
                "input_deck",
                input_deck,
                "CalculiX input deck associated with the selected case",
            )
        )
    if case_id:
        expected_path = golden_samples_root / case_id / "expected_results.json"
        if expected_path.exists():
            artifacts.append(
                _artifact_record(
                    "expected_results",
                    expected_path,
                    "Golden-sample reference payload used for report comparison",
                )
            )
    artifacts.extend(
        _artifact_record("solver_log", path, "Solver-side log/status artifact found beside the case deck")
        for path in solver_log_artifacts
    )
    artifacts.extend(
        _artifact_record("mesh_metadata", path, "Mesh generation metadata artifact visible to the report path")
        for path in mesh_meta_artifacts
    )
    artifacts.extend(
        _artifact_record("mesh_quality", path, "Mesh quality sidecar artifact visible to the report path")
        for path in mesh_quality_artifacts
    )
    artifacts.extend(
        _artifact_record(
            "mesh_convergence",
            path,
            "Mesh refinement convergence-study artifact visible to the report path",
        )
        for path in mesh_convergence_artifacts
    )

    artifact_hashes = [item for item in artifacts if item["status"] == "available"]
    manifest_id = _manifest_id(case_id, source_path, artifact_hashes)
    assumptions = _build_assumptions(expected)
    solver_logs = _build_solver_logs(solver_job_status, solver_log_artifacts)
    mesh_evidence = _build_mesh_evidence(
        result,
        input_deck,
        mesh_meta_artifacts,
        mesh_quality_artifacts,
        mesh_convergence_artifacts,
    )
    convergence_evidence = _build_convergence_evidence(
        solver_job_status,
        solver_log_artifacts,
        mesh_evidence["convergence_study"],
    )
    reviewer_summary = _build_reviewer_summary(
        expected,
        validation,
        assumptions,
        solver_logs,
        mesh_evidence,
        convergence_evidence,
    )

    return {
        "schema_version": "fm03-candidate-report-spine.v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "claim_tier": "Tier 1 engineering candidate",
        "allowed_claim": "engineering candidate, not signed validation",
        "no_overclaim": "not signed validation",
        "case": {
            "case_id": case_id or "uploaded-artifact",
            "case_name": _expected_value(expected, "case_name", result.file_name),
            "expected_results_status": _expected_value(expected, "status", "unavailable"),
            "status_reason": _expected_value(expected, "status_reason", "No expected_results.json loaded"),
            "failure_pattern_ref": _expected_value(expected, "failure_pattern_ref", "not surfaced"),
        },
        "provenance": {
            "report_surface": "POST /api/v1/report/generate",
            "parser": "FRDParser",
            "result_file_name": result.file_name,
            "original_filename": original_filename or result.file_name,
            "file_size_bytes": result.file_size,
            "parse_time_s": round(result.parse_time, 6),
            "is_binary_frd": result.is_binary,
            "node_count": len(result.nodes),
            "element_count": len(result.elements),
            "increment_count": len(result.increments),
            "solver_truth_source": "CalculiX FRD artifact; fresh solve provenance depends on linked solver job/log artifacts",
        },
        "solver": {
            "truth_source": "CalculiX artifact",
            "latest_job_id": None if solver_job_status is None else solver_job_status.get("job_id"),
            "latest_job_status": None if solver_job_status is None else solver_job_status.get("status"),
            "normal_termination_state": _normal_termination_state(solver_job_status),
            "logs": solver_logs,
        },
        "assumptions": assumptions,
        "mesh_evidence": mesh_evidence,
        "convergence_evidence": convergence_evidence,
        "metrics": {
            "output_metric_keys": sorted(str(key) for key in metrics.keys()),
            "values": dict(metrics),
            "extraction_command": "POST /api/v1/report/generate with a CalculiX .frd upload or selected case artifact",
        },
        "validation": dict(validation),
        "artifact_manifest": {
            "manifest_id": manifest_id,
            "hash_algorithm": "sha256",
            "hash_count": len(artifact_hashes),
            "items": artifacts,
        },
        "limitations": _build_limitations(assumptions, solver_logs, mesh_evidence, convergence_evidence),
        "reviewer_summary": reviewer_summary,
        "tier2_blockers": [
            "public benchmark/source is not attached",
            "Tier 2 tolerance comparison and signed convergence evidence are not attached",
            "independent reviewer/signoff is not attached",
            "this payload is explicitly not signed validation",
        ],
    }


def _load_expected_results(root: Path, case_id: Optional[str]) -> dict[str, Any]:
    if not case_id:
        return {}
    path = root / case_id / "expected_results.json"
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def _expected_value(expected: Mapping[str, Any], key: str, default: str) -> str:
    value = expected.get(key)
    return str(value) if value not in (None, "") else default


def _find_input_deck(case_dir: Optional[Path]) -> Optional[Path]:
    if case_dir is None or not case_dir.exists():
        return None
    matches = sorted(case_dir.glob("*.inp"))
    return matches[0] if matches else None


def _find_solver_log_artifacts(case_dir: Optional[Path], case_id: Optional[str]) -> list[Path]:
    search_dirs: list[Path] = []
    if case_dir is not None and case_dir.exists():
        search_dirs.append(case_dir)
    search_dirs.extend(_case_runtime_dirs(case_id, "solver"))

    matches: list[Path] = []
    for search_dir in search_dirs:
        for pattern in ("*.dat", "*.sta", "*.cvg", "spooles.out"):
            matches.extend(sorted(search_dir.glob(pattern)))
    return _dedupe_paths(matches)


def _find_mesh_meta_artifacts(case_id: Optional[str]) -> list[Path]:
    matches: list[Path] = []
    for search_dir in _case_runtime_dirs(case_id, "mesh"):
        meta_path = search_dir / "mesh_meta.json"
        if meta_path.exists():
            matches.append(meta_path)
    return _dedupe_paths(matches)


def _find_mesh_quality_artifacts(case_id: Optional[str]) -> list[Path]:
    matches: list[Path] = []
    for search_dir in _case_runtime_dirs(case_id, "mesh"):
        quality_path = search_dir / "mesh_quality.json"
        if quality_path.exists():
            matches.append(quality_path)
    return _dedupe_paths(matches)


def _find_mesh_convergence_artifacts(case_id: Optional[str]) -> list[Path]:
    matches: list[Path] = []
    for search_dir in _case_runtime_dirs(case_id, "mesh"):
        for file_name in ("mesh_convergence.json", "mesh_refinement_convergence.json"):
            study_path = search_dir / file_name
            if study_path.exists():
                matches.append(study_path)
    return _dedupe_paths(matches)


def _case_runtime_dirs(case_id: Optional[str], stage: str) -> list[Path]:
    if not case_id:
        return []

    dirs = [REPO_ROOT / "project_state" / "graph_executor" / case_id / stage]
    runs_root = REPO_ROOT / "project_state" / "runs" / case_id
    if runs_root.exists():
        dirs.extend(
            sorted(
                runs_root.glob(f"*/executor/{stage}"),
                key=lambda path: path.stat().st_mtime if path.exists() else 0.0,
                reverse=True,
            )
        )
    return [path for path in dirs if path.exists() and path.is_dir()]


def _dedupe_paths(paths: list[Path]) -> list[Path]:
    seen: set[str] = set()
    deduped: list[Path] = []
    for path in paths:
        key = str(path.resolve())
        if key in seen:
            continue
        seen.add(key)
        deduped.append(path)
    return deduped


def _artifact_record(
    kind: str,
    path: Path,
    description: str,
    *,
    display_path: Optional[str] = None,
) -> dict[str, Any]:
    if not path.exists() or not path.is_file():
        return {
            "kind": kind,
            "status": "unavailable",
            "path": display_path or _safe_path(path),
            "description": description,
            "unavailable_reason": "file does not exist",
        }
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return {
        "kind": kind,
        "status": "available",
        "path": display_path or _safe_path(path),
        "file_name": path.name,
        "size_bytes": path.stat().st_size,
        "sha256": digest.hexdigest(),
        "description": description,
    }


def _safe_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return path.name


def _manifest_id(
    case_id: Optional[str],
    source_path: Optional[Path],
    artifact_hashes: list[dict[str, Any]],
) -> str:
    seed = case_id or (source_path.name if source_path else "uploaded-artifact")
    if artifact_hashes:
        return f"fm03-{seed}-{artifact_hashes[0]['sha256'][:12]}"
    return f"fm03-{seed}-nohash"


def _build_assumptions(expected: Mapping[str, Any]) -> dict[str, Any]:
    material = (
        expected.get("material_params")
        or expected.get("material_properties")
        or expected.get("structure_params", {}).get("material")
    )
    input_params = expected.get("input_file_params", {})
    structure_params = expected.get("structure_params", {})
    supports = [
        {"node": node.get("id"), "support": node.get("support")}
        for node in structure_params.get("nodes", [])
        if isinstance(node, Mapping) and node.get("support")
    ]
    load = input_params.get("load") if isinstance(input_params, Mapping) else None

    return {
        "unit_system": {
            "status": "partially_declared",
            "stress_unit": "MPa per current ReportGenerator convention",
            "length_unit": "model-dependent; FRD does not carry explicit unit metadata",
        },
        "material": _declared_or_unavailable(material, "material source is not declared in expected_results.json"),
        "boundary_conditions": _declared_or_unavailable(
            {"supports": supports, "load": load} if supports or load else None,
            "boundary/load conditions are not surfaced by the current report payload",
        ),
        "contact": {
            "status": "unavailable",
            "unavailable_reason": "contact assumptions are not surfaced by the current report payload",
        },
    }


def _declared_or_unavailable(value: Any, unavailable_reason: str) -> dict[str, Any]:
    if value:
        return {"status": "declared", "value": value}
    return {"status": "unavailable", "unavailable_reason": unavailable_reason}


def _build_mesh_evidence(
    result: FRDParseResult,
    input_deck: Optional[Path],
    mesh_meta_artifacts: list[Path],
    mesh_quality_artifacts: list[Path],
    mesh_convergence_artifacts: list[Path],
) -> dict[str, Any]:
    deck_summary = _parse_input_deck_mesh(input_deck)
    metadata_summary = _mesh_metadata_summary(mesh_meta_artifacts)
    quality_summary = _mesh_quality_summary(metadata_summary, mesh_quality_artifacts)
    convergence_study = _mesh_convergence_study_summary(mesh_convergence_artifacts)

    return {
        "status": "partial" if deck_summary["status"] == "available" or result.nodes else "unavailable",
        "claim_impact": (
            "mesh topology is surfaced for Tier 1 reproducibility only; "
            "mesh adequacy or convergence is not proven"
        ),
        "result_mesh": {
            "source": "FRDParser",
            "node_count": len(result.nodes),
            "element_count": len(result.elements),
            "increment_count": len(result.increments),
        },
        "input_deck": deck_summary,
        "metadata": metadata_summary,
        "quality": quality_summary,
        "convergence_study": convergence_study,
    }


def _parse_input_deck_mesh(input_deck: Optional[Path]) -> dict[str, Any]:
    if input_deck is None:
        return {
            "status": "unavailable",
            "unavailable_reason": "no CalculiX .inp deck is visible to the report path",
        }

    try:
        lines = input_deck.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError as exc:
        return {
            "status": "unavailable",
            "path": _safe_path(input_deck),
            "unavailable_reason": f"failed to read input deck: {exc}",
        }

    section: Optional[str] = None
    current_element_type = "UNKNOWN"
    node_count = 0
    element_count = 0
    element_types: dict[str, int] = {}
    include_count = 0

    for raw_line in lines:
        line = raw_line.strip()
        if not line or line.startswith("**"):
            continue

        if line.startswith("*"):
            keyword = line.split(",", 1)[0].upper()
            if keyword == "*NODE":
                section = "node"
            elif keyword == "*ELEMENT":
                section = "element"
                current_element_type = _extract_inp_option(line, "TYPE") or "UNKNOWN"
            else:
                section = None
                if keyword == "*INCLUDE":
                    include_count += 1
            continue

        first_token = line.split(",", 1)[0].strip()
        if not first_token.isdigit():
            continue
        if section == "node":
            node_count += 1
        elif section == "element":
            element_count += 1
            element_types[current_element_type] = element_types.get(current_element_type, 0) + 1

    summary = {
        "status": "available",
        "path": _safe_path(input_deck),
        "node_count": node_count,
        "element_count": element_count,
        "element_types": dict(sorted(element_types.items())),
        "include_count": include_count,
    }
    if include_count:
        summary["limitation"] = "include files are referenced but not expanded by this Tier 1 report spine"
    return summary


def _extract_inp_option(keyword_line: str, option: str) -> Optional[str]:
    prefix = f"{option.upper()}="
    for part in keyword_line.split(",")[1:]:
        token = part.strip()
        if token.upper().startswith(prefix):
            return token.split("=", 1)[1].strip().upper()
    return None


def _mesh_metadata_summary(mesh_meta_artifacts: list[Path]) -> dict[str, Any]:
    artifact_records = [
        _artifact_record("mesh_metadata", path, "Mesh generation metadata artifact")
        for path in mesh_meta_artifacts
    ]
    if not mesh_meta_artifacts:
        return {
            "status": "unavailable",
            "artifacts": [],
            "unavailable_reason": "no mesh_meta.json artifact is visible to the report path",
        }

    first_path = mesh_meta_artifacts[0]
    try:
        payload = json.loads(first_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {
            "status": "unavailable",
            "artifacts": artifact_records,
            "unavailable_reason": f"mesh metadata is unreadable: {exc}",
        }

    field_config = payload.get("field_config") if isinstance(payload, Mapping) else None
    return {
        "status": "metadata_only",
        "source": _safe_path(first_path),
        "artifacts": artifact_records,
        "generation_mode": payload.get("generation_mode", "unavailable"),
        "mesh_level": field_config.get("mesh_level") if isinstance(field_config, Mapping) else None,
        "element_order": field_config.get("element_order") if isinstance(field_config, Mapping) else None,
        "thin_wall_detected": field_config.get("thin_wall_detected") if isinstance(field_config, Mapping) else None,
    }


def _mesh_quality_summary(
    metadata_summary: Mapping[str, Any],
    mesh_quality_artifacts: list[Path],
) -> dict[str, Any]:
    if mesh_quality_artifacts:
        return _available_mesh_quality_summary(mesh_quality_artifacts[0])

    artifacts = metadata_summary.get("artifacts") or []
    source = metadata_summary.get("source")
    metrics = {
        key: metadata_summary.get(key)
        for key in ("generation_mode", "mesh_level", "element_order", "thin_wall_detected")
        if metadata_summary.get(key) is not None
    }
    if metadata_summary.get("status") == "metadata_only":
        return {
            "status": "metadata_only",
            "source": source,
            "metrics": metrics,
            "unavailable_reason": (
                "mesh metadata is present, but scaled-Jacobian/aspect-ratio quality metrics "
                "are not attached; not signed validation"
            ),
        }

    return {
        "status": "unavailable",
        "source": None,
        "metrics": {},
        "artifact_count": len(artifacts),
        "unavailable_reason": (
            "mesh quality metric artifact is not attached; not signed validation"
        ),
    }


def _available_mesh_quality_summary(path: Path) -> dict[str, Any]:
    artifact = _artifact_record("mesh_quality", path, "Mesh quality sidecar artifact")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {
            "status": "unavailable",
            "source": _safe_path(path),
            "artifact": artifact,
            "metrics": {},
            "unavailable_reason": f"mesh quality artifact is unreadable: {exc}",
        }

    metrics = payload.get("metrics") if isinstance(payload, Mapping) else None
    thresholds = payload.get("thresholds") if isinstance(payload, Mapping) else None
    findings = payload.get("findings") if isinstance(payload, Mapping) else None
    return {
        "status": "available",
        "source": _safe_path(path),
        "artifact": artifact,
        "metrics": dict(metrics) if isinstance(metrics, Mapping) else {},
        "thresholds": dict(thresholds) if isinstance(thresholds, Mapping) else {},
        "findings": findings if isinstance(findings, list) else [],
        "claim_impact": "Tier 1 only; mesh quality metrics do not prove mesh convergence or signed validation",
    }


def _mesh_convergence_study_summary(mesh_convergence_artifacts: list[Path]) -> dict[str, Any]:
    if not mesh_convergence_artifacts:
        return {
            "status": "unavailable",
            "unavailable_reason": "mesh refinement convergence-study artifact is not attached",
        }

    path = mesh_convergence_artifacts[0]
    artifact = _artifact_record("mesh_convergence", path, "Mesh refinement convergence-study artifact")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {
            "status": "unavailable",
            "source": _safe_path(path),
            "artifact": artifact,
            "unavailable_reason": f"mesh convergence artifact is unreadable: {exc}",
        }

    runs = payload.get("runs") if isinstance(payload, Mapping) else None
    return {
        "status": "available",
        "source": _safe_path(path),
        "artifact": artifact,
        "study_status": str(payload.get("status", "candidate_observed")),
        "parameter": payload.get("parameter"),
        "metric": payload.get("metric"),
        "tolerance_pct": payload.get("tolerance_pct"),
        "relative_change_pct": payload.get("relative_change_pct"),
        "run_count": len(runs) if isinstance(runs, list) else 0,
        "runs": runs if isinstance(runs, list) else [],
        "claim_boundary": str(payload.get("claim_boundary", "tier1_engineering_candidate; not_signed_validation")),
        "claim_impact": "Tier 1 candidate convergence evidence only; benchmark agreement and signed validation remain blocked",
    }


def _build_convergence_evidence(
    solver_job_status: Optional[Mapping[str, Any]],
    solver_log_artifacts: list[Path],
    mesh_convergence_study: Mapping[str, Any],
) -> dict[str, Any]:
    source_artifacts = [_solver_artifact_record(path) for path in solver_log_artifacts]
    artifact_kinds = {str(item.get("kind")) for item in source_artifacts if item.get("status") == "available"}
    all_signals = [
        signal
        for item in source_artifacts
        for signal in item.get("signals", [])
    ]
    job_status = str(solver_job_status.get("status")) if solver_job_status is not None else None
    job_completed = job_status is not None and job_status.upper() == "COMPLETED"
    has_failure_marker = "failure_marker" in all_signals
    has_converged_signal = any(signal in all_signals for signal in ("converged_token", "normal_termination"))

    if job_completed:
        status = "job_completed"
        normal_termination = "completed"
    elif has_converged_signal and not has_failure_marker:
        status = "solver_artifact_converged"
        normal_termination = "available"
    elif source_artifacts:
        status = "artifact_reference_only"
        normal_termination = "unavailable"
    else:
        status = "unavailable"
        normal_termination = "unavailable"

    missing_reasons: list[str] = []
    if "sta" not in artifact_kinds and not job_completed:
        missing_reasons.append("CalculiX .sta normal-termination artifact is not attached")
    if "cvg" not in artifact_kinds:
        missing_reasons.append("CalculiX .cvg iteration/convergence history is not attached")
    if not source_artifacts and solver_job_status is None:
        missing_reasons.append("no solver job status or solver-side convergence artifact is visible")
    if mesh_convergence_study.get("status") != "available":
        missing_reasons.append("mesh refinement convergence study is not attached")

    return {
        "status": status,
        "claim_impact": (
            "solver status artifacts are surfaced for Tier 1 review only; "
            "this is not a mesh convergence study or signed validation"
        ),
        "normal_termination": normal_termination,
        "latest_job_status": job_status,
        "source_artifacts": source_artifacts,
        "mesh_refinement_study": dict(mesh_convergence_study),
        "signals": sorted(set(all_signals)),
        "missing_reasons": missing_reasons,
    }


def _solver_artifact_record(path: Path) -> dict[str, Any]:
    kind = path.suffix.lstrip(".").lower() or path.name.lower()
    record = _artifact_record(kind, path, "Solver convergence/status artifact")
    if record["status"] == "available":
        record["signals"] = _solver_artifact_signals(path)
    return record


def _solver_artifact_signals(path: Path) -> list[str]:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")[:200_000]
    except OSError:
        return []

    normalized = text.lower()
    signals: list[str] = []
    if "converged" in normalized:
        signals.append("converged_token")
    if "normal termination" in normalized:
        signals.append("normal_termination")
    if "analysis completed" in normalized or "分析完成" in text:
        signals.append("completion_text")
    if path.suffix.lower() == ".cvg" and text.strip():
        signals.append("iteration_history_present")
    failure_markers = (
        "error",
        "no convergence",
        "convergence not reached",
        "divergence",
        "solver exited with code",
    )
    if any(marker in normalized for marker in failure_markers):
        signals.append("failure_marker")
    return signals


def _build_solver_logs(
    solver_job_status: Optional[Mapping[str, Any]],
    solver_log_artifacts: list[Path],
) -> dict[str, Any]:
    if solver_job_status is not None:
        logs = solver_job_status.get("logs") or []
        return {
            "status": "available" if logs else "job_status_available_without_logs",
            "line_count": len(logs),
            "tail": logs[-10:],
            "artifact_paths": [_safe_path(path) for path in solver_log_artifacts],
        }
    if solver_log_artifacts:
        return {
            "status": "artifact_reference_only",
            "line_count": None,
            "tail": [],
            "artifact_paths": [_safe_path(path) for path in solver_log_artifacts],
            "unavailable_reason": "solver logs exist as artifacts but are not attached to an active in-memory job",
        }
    return {
        "status": "unavailable",
        "line_count": 0,
        "tail": [],
        "artifact_paths": [],
        "unavailable_reason": "no solver job logs or log artifacts are visible to the report path",
    }


def _normal_termination_state(solver_job_status: Optional[Mapping[str, Any]]) -> str:
    if solver_job_status is None:
        return "unavailable"
    status = str(solver_job_status.get("status") or "unknown").upper()
    if status == "COMPLETED":
        return "completed"
    if status == "FAILED":
        return "failed"
    return "not_finished"


def _build_limitations(
    assumptions: Mapping[str, Any],
    solver_logs: Mapping[str, Any],
    mesh_evidence: Mapping[str, Any],
    convergence_evidence: Mapping[str, Any],
) -> list[str]:
    limitations = [
        "not signed validation",
        "no public benchmark agreement is claimed",
        "independent reviewer/signoff is not attached",
    ]
    if assumptions["material"]["status"] != "declared":
        limitations.append("material provenance is unavailable")
    if assumptions["boundary_conditions"]["status"] != "declared":
        limitations.append("boundary-condition provenance is unavailable")
    if solver_logs["status"] == "unavailable":
        limitations.append("solver log evidence is unavailable")
    if mesh_evidence["quality"]["status"] != "available":
        limitations.append("mesh quality metric evidence is unavailable")
    if mesh_evidence["convergence_study"]["status"] != "available":
        limitations.append("mesh convergence evidence is not attached")
    if convergence_evidence["status"] not in {"job_completed", "solver_artifact_converged"}:
        limitations.append("solver convergence evidence is incomplete")
    return limitations


def _build_reviewer_summary(
    expected: Mapping[str, Any],
    validation: Mapping[str, Any],
    assumptions: Mapping[str, Any],
    solver_logs: Mapping[str, Any],
    mesh_evidence: Mapping[str, Any],
    convergence_evidence: Mapping[str, Any],
) -> dict[str, Any]:
    blockers: list[str] = []
    if expected.get("status") == "insufficient_evidence":
        blockers.append(str(expected.get("status_reason") or "expected_results status is insufficient_evidence"))
    if validation.get("status") == "FAIL":
        blockers.append("report validation returned FAIL")
    if assumptions["material"]["status"] != "declared":
        blockers.append("material provenance unavailable")
    if assumptions["boundary_conditions"]["status"] != "declared":
        blockers.append("boundary-condition provenance unavailable")
    if solver_logs["status"] == "unavailable":
        blockers.append("solver logs unavailable")
    if mesh_evidence["quality"]["status"] != "available":
        blockers.append("mesh quality metric evidence unavailable")
    if "mesh refinement convergence study is not attached" in convergence_evidence["missing_reasons"]:
        blockers.append("mesh refinement convergence study unavailable")

    verdict = "candidate_ready_for_review" if not blockers else "needs_review"
    return {
        "verdict": verdict,
        "summary": (
            "Candidate spine is reproducible enough for review; no signed validation is claimed."
            if verdict == "candidate_ready_for_review"
            else "Candidate spine is generated, but blockers must be resolved before stronger claims."
        ),
        "blocked_findings": blockers,
        "next_actions": [
            "attach reviewer/signoff evidence before any claim promotion",
            "attach convergence and benchmark evidence before Tier 2 signed validation",
        ],
    }
