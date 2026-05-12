#!/usr/bin/env python3
"""Safe GS-102 real OpenRadioss transient candidate pipeline.

Tier 1 engineering candidate. Not signed validation. Not benchmark agreement.

This script copies a GS-102 refined candidate deck into ``project_state/runs``,
patches the copied deck with an explicit projectile velocity, runs OpenRadioss
there, extracts candidate ballistic metrics, renders the real .A### output, and
writes a run report. It refuses to write runtime outputs inside
``golden_samples/**``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import subprocess
import sys
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT_DEFAULT = Path(__file__).resolve().parents[1]
DEFAULT_CASE_ID = "GS-102-transient-refined-v600-candidate-real"
DEFAULT_SOURCE_CASE_DIR = (
    REPO_ROOT_DEFAULT / "golden_samples" / "GS-102-refined-candidate" / "data"
)
DEFAULT_DOCKER_IMAGE = "openradioss-local-arm64:latest"
DEFAULT_DOCKER_PLATFORM = "linux/arm64"
DEFAULT_PROJECTILE_NODE_MAX_ID = 27
DEFAULT_PROJECTILE_MASS_KG = 0.005024

CLAIM_BOUNDARY = "Tier 1 engineering candidate; not signed validation; not benchmark agreement"

_ANIM_RE = re.compile(r"A\d{3,4}(?:\.gz)?$")
_DELETE_RE = re.compile(
    r"DELETE SOLID ELEMENT NUMBER\s+(\d+) AT TIME\s*:\s*([0-9.E+-]+)"
)


@dataclass(frozen=True)
class PipelineConfig:
    repo_root: Path
    case_id: str
    source_case_dir: Path
    run_data_dir: Path
    graph_case_dir: Path
    velocity_m_s: float
    docker_image: str
    docker_platform: str
    frame_duration_ms: int
    projectile_node_max_id: int
    projectile_mass_kg: float
    clean_run_dir: bool


@dataclass(frozen=True)
class SolverSummary:
    starter_error_count: int | None
    starter_warning_count: int | None
    engine_normal_termination: bool
    engine_cycle_count: int | None
    animation_frame_count: int
    deleted_elements: list[tuple[str, str]]
    live_solid_count: int | None
    total_solid_count: int | None


@dataclass(frozen=True)
class ProjectileFrameSample:
    sample_index: int
    t_s: float
    position_m: tuple[float, float, float]
    velocity_m_per_s: tuple[float, float, float]


def _ensure_backend_path(repo_root: Path) -> None:
    backend = repo_root / "backend"
    for candidate in (str(backend), str(repo_root)):
        if candidate not in sys.path:
            sys.path.insert(0, candidate)


def _relative_parts(path: Path, repo_root: Path) -> tuple[str, ...]:
    try:
        return path.resolve().relative_to(repo_root.resolve()).parts
    except ValueError:
        return path.resolve().parts


def _assert_safe_output_path(path: Path, repo_root: Path) -> None:
    parts = _relative_parts(path, repo_root)
    if "golden_samples" in parts:
        raise ValueError(f"refuses to write inside golden_samples/**: {path}")
    if "project_state" not in parts:
        raise ValueError(f"runtime output must live under project_state/: {path}")


def _clean_known_outputs(run_data_dir: Path) -> None:
    for pattern in (
        "model_00A*",
        "model_00T*",
        "model_00_*.out",
        "model_00_*.rst",
        "starter.log",
        "engine.log",
    ):
        for path in run_data_dir.glob(pattern):
            if path.is_file():
                path.unlink()


def prepare_runtime_decks(config: PipelineConfig) -> tuple[Path, Path]:
    """Copy decks into project_state and patch the copied starter velocity."""

    _assert_safe_output_path(config.run_data_dir, config.repo_root)
    _assert_safe_output_path(config.graph_case_dir, config.repo_root)

    source_starter = config.source_case_dir / "model_00_0000.rad"
    source_engine = config.source_case_dir / "model_00_0001.rad"
    if not source_starter.exists() or not source_engine.exists():
        raise FileNotFoundError(
            f"expected starter and engine decks under {config.source_case_dir}"
        )

    config.run_data_dir.mkdir(parents=True, exist_ok=True)
    if config.clean_run_dir:
        _clean_known_outputs(config.run_data_dir)

    starter = config.run_data_dir / "model_00_0000.rad"
    engine = config.run_data_dir / "model_00_0001.rad"
    starter.write_text(
        _patch_velocity(source_starter.read_text(encoding="utf-8"), config.velocity_m_s),
        encoding="utf-8",
    )
    engine.write_text(source_engine.read_text(encoding="utf-8"), encoding="utf-8")
    return starter, engine


def _patch_velocity(deck_text: str, velocity_m_s: float) -> str:
    velocity_line = _format_inivel_line(velocity_m_s)
    pattern = re.compile(
        r"^(?P<prefix>\s*)[-+]?\d+(?:\.\d+)?(?:[Ee][-+]?\d+)?"
        r"\s+0\s+0\s+100\s+0\s*$",
        re.MULTILINE,
    )
    patched, count = pattern.subn(velocity_line, deck_text, count=1)
    if count != 1:
        raise ValueError("could not find /INIVEL projectile velocity line to patch")
    return patched


def _format_inivel_line(velocity_m_s: float) -> str:
    return f"{velocity_m_s:20.12g}{0:20.12g}{0:20.12g}{100:10d}{0:10d}"


def build_openradioss_commands(config: PipelineConfig) -> tuple[list[str], list[str]]:
    mount = f"{config.run_data_dir}:/work"
    base = [
        "docker",
        "run",
        "--rm",
        "--platform",
        config.docker_platform,
        "-v",
        mount,
        "-w",
        "/work",
        config.docker_image,
        "bash",
        "-lc",
    ]
    starter = [
        *base,
        "starter_linuxa64 -i model_00_0000.rad 2>&1 | tee starter.log",
    ]
    engine = [
        *base,
        "engine_linuxa64 -i model_00_0001.rad 2>&1 | tee engine.log",
    ]
    return starter, engine


def run_openradioss_solver(
    config: PipelineConfig,
    *,
    runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> None:
    for cmd in build_openradioss_commands(config):
        runner(cmd, check=True, text=True)


def discover_animation_files(run_data_dir: Path) -> tuple[Path, ...]:
    return tuple(
        sorted(
            (path for path in run_data_dir.iterdir() if _ANIM_RE.search(path.name)),
            key=lambda path: path.name,
        )
    )


def extract_candidate_metrics(config: PipelineConfig, anim_files: Sequence[Path]) -> Path:
    if not anim_files:
        raise ValueError("no OpenRadioss .A### animation files found for metric extraction")

    _ensure_backend_path(config.repo_root)
    from app.services.ballistics.metric_extraction import (  # noqa: E402
        BallisticEnergyAudit,
        BallisticExtractionInput,
        BallisticTimeSample,
        write_ballistic_metrics,
    )
    from vortex_radioss.animtod3plot.RadiossReader import RadiossReader  # noqa: E402

    frame_arrays = [RadiossReader(str(path)).arrays for path in anim_files]
    samples = [
        _projectile_frame_sample(arrays, config.projectile_node_max_id, index)
        for index, arrays in enumerate(frame_arrays)
    ]
    plate_front_m, plate_back_m = _plate_faces_m(
        frame_arrays[0],
        config.projectile_node_max_id,
    )

    metrics_dir = config.graph_case_dir / "ballistic"
    metrics_path = write_ballistic_metrics(
        BallisticExtractionInput(
            case_id=config.case_id,
            projectile_mass_kg=config.projectile_mass_kg,
            plate_back_face_x_m=plate_back_m,
            plate_thickness_m=plate_back_m - plate_front_m,
            samples=[
                BallisticTimeSample(
                    sample.t_s,
                    sample.position_m,
                    sample.velocity_m_per_s,
                )
                for sample in samples
            ],
            impact_axis="x",
            energy_audit=BallisticEnergyAudit(),
        ),
        metrics_dir,
    )
    enrich_metrics_sidecar(
        metrics_path=metrics_path,
        samples=samples,
        plate_front_m=plate_front_m,
        plate_back_m=plate_back_m,
        impact_axis="x",
    )
    return metrics_path


def _projectile_frame_sample(
    arrays: dict,
    projectile_node_max_id: int,
    sample_index: int,
) -> ProjectileFrameSample:
    node_ids = list(arrays["node_ids"])
    coords = arrays["node_coordinates"]
    velocities = arrays["node_velocity"]
    indexes = [
        index for index, node_id in enumerate(node_ids) if int(node_id) <= projectile_node_max_id
    ]
    if not indexes:
        raise ValueError("no projectile nodes found in animation frame")

    position_mm = [
        sum(float(coords[index][axis]) for index in indexes) / len(indexes)
        for axis in range(3)
    ]
    velocity = [
        sum(float(velocities[index][axis]) for index in indexes) / len(indexes)
        for axis in range(3)
    ]
    return ProjectileFrameSample(
        sample_index=sample_index,
        t_s=float(arrays["timesteps"]) * 1e-3,
        position_m=tuple(value * 1e-3 for value in position_mm),
        velocity_m_per_s=tuple(velocity),
    )


def enrich_metrics_sidecar(
    *,
    metrics_path: Path,
    samples: Sequence[ProjectileFrameSample],
    plate_front_m: float,
    plate_back_m: float,
    impact_axis: str,
) -> None:
    if not samples:
        raise ValueError("cannot enrich metrics without projectile frame samples")

    payload = json.loads(metrics_path.read_text(encoding="utf-8"))
    payload["crossing_evidence"] = _crossing_evidence(
        samples,
        plate_front_m=plate_front_m,
        plate_back_m=plate_back_m,
        impact_axis=impact_axis,
    )
    payload["residual_velocity_trace"] = _residual_velocity_trace(samples, impact_axis)
    payload["partial_energy_audit"] = _partial_energy_audit(payload.get("energy_balance"))
    metrics_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def append_solver_evidence_to_metrics_sidecar(
    metrics_path: Path,
    summary: SolverSummary,
) -> None:
    payload = json.loads(metrics_path.read_text(encoding="utf-8"))
    payload["solver_evidence"] = {
        "status": (
            "candidate_observed"
            if summary.engine_normal_termination
            else "partial_candidate"
        ),
        "starter_error_count": summary.starter_error_count,
        "starter_warning_count": summary.starter_warning_count,
        "engine_normal_termination": summary.engine_normal_termination,
        "engine_cycle_count": summary.engine_cycle_count,
        "animation_frame_count": summary.animation_frame_count,
        "live_solid_count": summary.live_solid_count,
        "total_solid_count": summary.total_solid_count,
        "deleted_element_count": len(summary.deleted_elements),
        "deleted_elements": [
            {"element_id": element, "time_ms": time_ms}
            for element, time_ms in summary.deleted_elements[:20]
        ],
        "claim_impact": (
            "Tier 1 solver evidence only; not signed validation; "
            "not benchmark agreement."
        ),
    }
    metrics_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _crossing_evidence(
    samples: Sequence[ProjectileFrameSample],
    *,
    plate_front_m: float,
    plate_back_m: float,
    impact_axis: str,
) -> dict:
    axis_idx = _axis_index(impact_axis)
    initial_axis_pos = samples[0].position_m[axis_idx]
    final_axis_pos = samples[-1].position_m[axis_idx]
    direction_sign = 1.0 if initial_axis_pos < plate_back_m else -1.0

    front_crossing = _first_crossing(
        samples,
        axis_idx=axis_idx,
        threshold=plate_front_m if direction_sign > 0 else plate_back_m,
        direction_sign=direction_sign,
    )
    back_crossing = _first_crossing(
        samples,
        axis_idx=axis_idx,
        threshold=plate_back_m if direction_sign > 0 else plate_front_m,
        direction_sign=direction_sign,
    )

    front_crossed = front_crossing is not None
    back_crossed = back_crossing is not None
    status = "candidate_observed" if back_crossed else "partial_candidate"
    if not front_crossed:
        status = "not_observed"

    return {
        "status": status,
        "impact_axis": impact_axis,
        "plate_front_face_x_m": _round_float(plate_front_m),
        "plate_back_face_x_m": _round_float(plate_back_m),
        "initial_centroid_x_m": _round_float(initial_axis_pos),
        "final_centroid_x_m": _round_float(final_axis_pos),
        "front_face_crossed": front_crossed,
        "back_face_crossed": back_crossed,
        "first_front_face_crossing_sample_index": _sample_index(front_crossing),
        "first_front_face_crossing_t_s": _sample_time(front_crossing),
        "first_back_face_crossing_sample_index": _sample_index(back_crossing),
        "first_back_face_crossing_t_s": _sample_time(back_crossing),
        "claim_impact": (
            "Tier 1 candidate crossing evidence only; not signed validation; "
            "not benchmark agreement"
        ),
    }


def _first_crossing(
    samples: Sequence[ProjectileFrameSample],
    *,
    axis_idx: int,
    threshold: float,
    direction_sign: float,
) -> ProjectileFrameSample | None:
    for sample in samples:
        value = sample.position_m[axis_idx]
        if direction_sign > 0 and value >= threshold:
            return sample
        if direction_sign < 0 and value <= threshold:
            return sample
    return None


def _sample_index(sample: ProjectileFrameSample | None) -> int | None:
    return sample.sample_index if sample is not None else None


def _sample_time(sample: ProjectileFrameSample | None) -> float | None:
    return _round_float(sample.t_s) if sample is not None else None


def _residual_velocity_trace(
    samples: Sequence[ProjectileFrameSample],
    impact_axis: str,
) -> dict:
    axis_idx = _axis_index(impact_axis)
    speeds = [_speed(sample.velocity_m_per_s) for sample in samples]
    return {
        "status": "candidate_observed",
        "sample_count": len(samples),
        "impact_axis": impact_axis,
        "initial_speed_m_per_s": _round_float(speeds[0]),
        "final_speed_m_per_s": _round_float(speeds[-1]),
        "min_speed_m_per_s": _round_float(min(speeds)),
        "max_speed_m_per_s": _round_float(max(speeds)),
        "samples": [
            {
                "sample_index": sample.sample_index,
                "t_s": _round_float(sample.t_s),
                "centroid_axis_position_m": _round_float(sample.position_m[axis_idx]),
                "speed_m_per_s": _round_float(speed),
            }
            for sample, speed in zip(samples, speeds, strict=True)
        ],
    }


def _partial_energy_audit(energy_balance: object) -> dict:
    if not isinstance(energy_balance, dict):
        return {
            "status": "unavailable",
            "missing_terms": [
                "initial_kinetic_energy_j",
                "residual_kinetic_energy_j",
                "plastic_dissipation_j",
                "contact_friction_j",
                "hourglass_energy_j",
            ],
            "claim_impact": "Energy audit unavailable for this Tier 1 candidate run",
        }

    optional_terms = [
        "plastic_dissipation_j",
        "contact_friction_j",
        "hourglass_energy_j",
    ]
    missing_terms = [key for key in optional_terms if energy_balance.get(key) is None]
    status = "partial_candidate" if missing_terms else "available"
    return {
        "status": status,
        "initial_kinetic_energy_j": energy_balance.get("initial_kinetic_energy_j"),
        "residual_kinetic_energy_j": energy_balance.get("residual_kinetic_energy_j"),
        "plastic_dissipation_j": energy_balance.get("plastic_dissipation_j"),
        "contact_friction_j": energy_balance.get("contact_friction_j"),
        "hourglass_energy_j": energy_balance.get("hourglass_energy_j"),
        "missing_terms": missing_terms,
        "claim_impact": (
            "Partial Tier 1 energy audit; missing terms prevent any validation "
            "or benchmark-agreement claim"
        ),
    }


def _speed(velocity_m_per_s: Sequence[float]) -> float:
    return math.sqrt(sum(component * component for component in velocity_m_per_s))


def _axis_index(axis: str) -> int:
    return {"x": 0, "y": 1, "z": 2}[axis]


def _round_float(value: float) -> float:
    return round(float(value), 9)


def _plate_faces_m(arrays: dict, projectile_node_max_id: int) -> tuple[float, float]:
    xs = [
        float(arrays["node_coordinates"][index][0])
        for index, node_id in enumerate(arrays["node_ids"])
        if int(node_id) > projectile_node_max_id
    ]
    if not xs:
        raise ValueError("no plate nodes found in animation frame")
    return min(xs) * 1e-3, max(xs) * 1e-3


def render_real_animation(config: PipelineConfig, anim_files: Sequence[Path]) -> Path:
    if not anim_files:
        raise ValueError("no OpenRadioss .A### animation files found for rendering")

    _ensure_backend_path(config.repo_root)
    from app.services.openradioss_animation import (  # noqa: E402
        OpenRadiossAnimationInput,
        write_openradioss_animation,
    )

    title = (
        f"{config.case_id} V0={config.velocity_m_s:g} m/s "
        "transient candidate (REAL OpenRadioss)"
    )
    return write_openradioss_animation(
        OpenRadiossAnimationInput(
            case_id=config.case_id,
            anim_files=tuple(anim_files),
            deck_source=str(
                (config.run_data_dir / "model_00_0000.rad").relative_to(config.repo_root)
            ),
            title=title,
        ),
        config.graph_case_dir / "visualization",
        frame_duration_ms=config.frame_duration_ms,
    )


def summarize_solver_evidence(
    config: PipelineConfig,
    anim_files: Sequence[Path],
) -> SolverSummary:
    starter_log = _read_text(config.run_data_dir / "starter.log")
    engine_log = _read_text(config.run_data_dir / "engine.log")
    live_solid_count: int | None = None
    total_solid_count: int | None = None

    if anim_files:
        try:
            from vortex_radioss.animtod3plot.RadiossReader import RadiossReader

            arrays = RadiossReader(str(anim_files[-1])).arrays
            solids = arrays.get("element_solid_is_alive")
            if solids is not None:
                live_solid_count = int(sum(bool(value) for value in solids))
                total_solid_count = int(len(solids))
        except Exception:
            live_solid_count = None
            total_solid_count = None

    return SolverSummary(
        starter_error_count=_last_count(starter_log, "ERROR"),
        starter_warning_count=_last_count(starter_log, "WARNING"),
        engine_normal_termination="NORMAL TERMINATION" in engine_log,
        engine_cycle_count=_engine_cycle_count(engine_log),
        animation_frame_count=len(anim_files),
        deleted_elements=_DELETE_RE.findall(engine_log),
        live_solid_count=live_solid_count,
        total_solid_count=total_solid_count,
    )


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore") if path.exists() else ""


def _last_count(text: str, label: str) -> int | None:
    matches = re.findall(rf"(\d+)\s+{re.escape(label)}\(S\)", text)
    return int(matches[-1]) if matches else None


def _engine_cycle_count(text: str) -> int | None:
    match = re.search(r"TOTAL NUMBER OF CYCLES\s*:\s*(\d+)", text)
    return int(match.group(1)) if match else None


def write_run_report(
    *,
    config: PipelineConfig,
    summary: SolverSummary,
    metrics_path: Path,
    manifest_path: Path,
    gif_path: Path,
) -> Path:
    metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
    report_dir = config.repo_root / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / f"gs102_{config.case_id}_candidate_run.md"

    live_solids = (
        f"{summary.live_solid_count} / {summary.total_solid_count}"
        if summary.live_solid_count is not None and summary.total_solid_count is not None
        else "not extracted"
    )
    deleted_lines = "\n".join(
        f"  - element `{element}` at `{time_ms} ms`"
        for element, time_ms in summary.deleted_elements[:20]
    ) or "  - none recorded"
    crossing = metrics.get("crossing_evidence", {})
    velocity_trace = metrics.get("residual_velocity_trace", {})
    energy = metrics.get("partial_energy_audit", {})
    missing_energy_terms = ", ".join(energy.get("missing_terms", [])) or "none"

    text = f"""# GS-102 transient candidate run - {config.case_id}

> Status: Tier 1 engineering candidate.
> Solver: OpenRadioss via `{config.docker_image}`.
> Claim boundary: not signed validation; not benchmark agreement.

## Purpose

Run a real OpenRadioss transient structural candidate for projectile impact on
a candidate plate. Runtime decks and solver outputs live under `project_state/`.
This script refuses runtime writes inside `golden_samples/**`.

## Candidate setup

- Source deck directory: `{_rel(config.source_case_dir, config.repo_root)}`
- Runtime deck directory: `{_rel(config.run_data_dir, config.repo_root)}`
- Projectile initial velocity: `{config.velocity_m_s:g} m/s`
- Projectile mass used by metrics: `{config.projectile_mass_kg:g} kg`
- Projectile node id range used by metrics: `1..{config.projectile_node_max_id}`

## Solver evidence

- Starter errors / warnings: `{summary.starter_error_count}` / `{summary.starter_warning_count}`
- Engine normal termination: `{summary.engine_normal_termination}`
- Engine cycle count: `{summary.engine_cycle_count}`
- Animation frame count: `{summary.animation_frame_count}`
- Last-frame live solids: `{live_solids}`
- Element deletion events:
{deleted_lines}

## Candidate metrics

- `perforation_marker`: `{metrics.get("perforation_marker")}`
- `projectile_initial_velocity_m_per_s`: `{metrics.get("projectile_initial_velocity_m_per_s")}`
- `residual_velocity_candidate_m_per_s`: `{metrics.get("residual_velocity_candidate_m_per_s")}`
- Metrics sidecar: `{_rel(metrics_path, config.repo_root)}`

## Crossing and energy evidence

- `crossing_status`: `{crossing.get("status")}`
- `front_face_crossed`: `{crossing.get("front_face_crossed")}`
- `back_face_crossed`: `{crossing.get("back_face_crossed")}`
- `first_back_face_crossing_t_s`: `{crossing.get("first_back_face_crossing_t_s")}`
- `velocity_trace_sample_count`: `{velocity_trace.get("sample_count")}`
- `velocity_trace_final_speed_m_per_s`: `{velocity_trace.get("final_speed_m_per_s")}`
- `partial_energy_audit_status`: `{energy.get("status")}`
- `partial_energy_missing_terms`: `{missing_energy_terms}`

## Visualization artifacts

- GIF: `{_rel(gif_path, config.repo_root)}`
- Visualization manifest: `{_rel(manifest_path, config.repo_root)}`

## Artifact hashes

```text
{_hash_line(config.run_data_dir / "model_00_0000.rad", config.repo_root)}
{_hash_line(config.run_data_dir / "model_00_0001.rad", config.repo_root)}
{_hash_line(config.run_data_dir / "starter.log", config.repo_root)}
{_hash_line(config.run_data_dir / "engine.log", config.repo_root)}
{_hash_line(metrics_path, config.repo_root)}
{_hash_line(manifest_path, config.repo_root)}
{_hash_line(gif_path, config.repo_root)}
```

## Limitations

- Tier 1 only: no signed validation, no benchmark comparison, no tolerance
  agreement, and no independent reviewer signoff.
- This is a candidate workflow proof, not a locked validation configuration.
- Energy audit is partial unless future extraction adds plastic dissipation,
  hourglass energy, and contact friction to the metrics sidecar.
"""
    report_path.write_text(text, encoding="utf-8")
    return report_path


def _rel(path: Path, repo_root: Path) -> str:
    try:
        return str(path.resolve().relative_to(repo_root.resolve()))
    except ValueError:
        return str(path)


def _hash_line(path: Path, repo_root: Path) -> str:
    if not path.exists():
        return f"missing  {_rel(path, repo_root)}"
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return f"{digest}  {_rel(path, repo_root)}"


def run_pipeline(config: PipelineConfig, *, skip_solver: bool = False) -> dict[str, Path]:
    prepare_runtime_decks(config)
    if not skip_solver:
        run_openradioss_solver(config)

    anim_files = discover_animation_files(config.run_data_dir)
    metrics_path = extract_candidate_metrics(config, anim_files)
    manifest_path = render_real_animation(config, anim_files)
    gif_path = manifest_path.parent / "openradioss_animation.gif"
    summary = summarize_solver_evidence(config, anim_files)
    append_solver_evidence_to_metrics_sidecar(metrics_path, summary)
    report_path = write_run_report(
        config=config,
        summary=summary,
        metrics_path=metrics_path,
        manifest_path=manifest_path,
        gif_path=gif_path,
    )
    return {
        "metrics": metrics_path,
        "manifest": manifest_path,
        "gif": gif_path,
        "report": report_path,
    }


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=str(REPO_ROOT_DEFAULT))
    parser.add_argument("--case-id", default=DEFAULT_CASE_ID)
    parser.add_argument("--source-case-dir", default=str(DEFAULT_SOURCE_CASE_DIR))
    parser.add_argument("--velocity-m-s", type=float, default=600.0)
    parser.add_argument("--docker-image", default=DEFAULT_DOCKER_IMAGE)
    parser.add_argument("--docker-platform", default=DEFAULT_DOCKER_PLATFORM)
    parser.add_argument("--frame-duration-ms", type=int, default=80)
    parser.add_argument(
        "--projectile-node-max-id",
        type=int,
        default=DEFAULT_PROJECTILE_NODE_MAX_ID,
    )
    parser.add_argument("--projectile-mass-kg", type=float, default=DEFAULT_PROJECTILE_MASS_KG)
    parser.add_argument(
        "--skip-solver",
        action="store_true",
        help="reuse existing .A### outputs in the project_state run directory",
    )
    parser.add_argument(
        "--no-clean-run-dir",
        action="store_true",
        help="do not remove old OpenRadioss outputs before running the solver",
    )
    return parser.parse_args(argv)


def _config_from_args(args: argparse.Namespace) -> PipelineConfig:
    repo_root = Path(args.repo_root).resolve()
    case_id = str(args.case_id)
    return PipelineConfig(
        repo_root=repo_root,
        case_id=case_id,
        source_case_dir=Path(args.source_case_dir).resolve(),
        run_data_dir=repo_root / "project_state" / "runs" / case_id / "data",
        graph_case_dir=repo_root / "project_state" / "graph_executor" / case_id,
        velocity_m_s=float(args.velocity_m_s),
        docker_image=str(args.docker_image),
        docker_platform=str(args.docker_platform),
        frame_duration_ms=int(args.frame_duration_ms),
        projectile_node_max_id=int(args.projectile_node_max_id),
        projectile_mass_kg=float(args.projectile_mass_kg),
        clean_run_dir=not args.skip_solver and not args.no_clean_run_dir,
    )


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    config = _config_from_args(args)
    print(f"GS-102 transient candidate pipeline: {config.case_id}")
    print(CLAIM_BOUNDARY)
    artifacts = run_pipeline(config, skip_solver=args.skip_solver)
    for name, path in artifacts.items():
        print(f"{name}: {_rel(path, config.repo_root)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
