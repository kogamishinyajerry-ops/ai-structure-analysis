"""Tests for the safe GS-102 real OpenRadioss candidate pipeline.

Tier 1 engineering-candidate infrastructure only; not signed validation.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
PIPELINE_SCRIPT = REPO_ROOT / "scripts" / "gs102_transient_candidate_pipeline.py"


def _load_pipeline_module():
    spec = importlib.util.spec_from_file_location(
        "gs102_transient_candidate_pipeline",
        PIPELINE_SCRIPT,
    )
    if spec is None or spec.loader is None:  # pragma: no cover - defensive
        raise RuntimeError(f"could not load pipeline module from {PIPELINE_SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    sys.modules.setdefault("gs102_transient_candidate_pipeline", module)
    spec.loader.exec_module(module)
    return module


def _seed_source_case(repo_root: Path) -> Path:
    source = repo_root / "golden_samples" / "GS-102-refined-candidate" / "data"
    source.mkdir(parents=True)
    (source / "model_00_0000.rad").write_text(
        "\n".join(
            [
                "# copied source deck",
                "# /INIVEL - V0 = 150 m/s",
                "/INIVEL/TRA/1",
                "projectile_initial_velocity_candidate",
                "#                 Vx                  Vy                  Vz   Gnod_id   Skew_id",
                "                 150                   0                   0       100         0",
                "/END",
            ]
        ),
        encoding="utf-8",
    )
    (source / "model_00_0001.rad").write_text(
        "/RUN/gs102_refined_candidate/1/\n  0.15\n",
        encoding="utf-8",
    )
    return source


def _config(module, repo_root: Path, source: Path):
    case_id = "CASE-GS102-PIPELINE"
    return module.PipelineConfig(
        repo_root=repo_root,
        case_id=case_id,
        source_case_dir=source,
        run_data_dir=repo_root / "project_state" / "runs" / case_id / "data",
        graph_case_dir=repo_root / "project_state" / "graph_executor" / case_id,
        velocity_m_s=600.0,
        docker_image="openradioss-local-arm64:latest",
        docker_platform="linux/arm64",
        frame_duration_ms=80,
        projectile_node_max_id=27,
        projectile_mass_kg=0.005024,
        clean_run_dir=True,
    )


def test_prepare_runtime_decks_copies_and_patches_velocity_outside_golden_samples(
    tmp_path: Path,
) -> None:
    module = _load_pipeline_module()
    repo_root = tmp_path / "repo"
    source = _seed_source_case(repo_root)
    config = _config(module, repo_root, source)

    starter, engine = module.prepare_runtime_decks(config)

    assert starter == config.run_data_dir / "model_00_0000.rad"
    assert engine == config.run_data_dir / "model_00_0001.rad"
    assert "golden_samples" not in starter.relative_to(repo_root).parts
    assert "                 600                   0                   0       100         0" in (
        starter.read_text(encoding="utf-8")
    )
    assert "                 150                   0                   0       100         0" in (
        source / "model_00_0000.rad"
    ).read_text(encoding="utf-8")


def test_pipeline_rejects_runtime_output_inside_golden_samples(tmp_path: Path) -> None:
    module = _load_pipeline_module()
    repo_root = tmp_path / "repo"
    source = _seed_source_case(repo_root)
    config = _config(module, repo_root, source)
    config = module.PipelineConfig(
        **{
            **config.__dict__,
            "run_data_dir": repo_root / "golden_samples" / "bad-run" / "data",
        }
    )

    with pytest.raises(ValueError, match="refuses to write inside golden_samples"):
        module.prepare_runtime_decks(config)


def test_docker_commands_mount_runtime_dir_not_source_dir(tmp_path: Path) -> None:
    module = _load_pipeline_module()
    repo_root = tmp_path / "repo"
    source = _seed_source_case(repo_root)
    config = _config(module, repo_root, source)

    starter_cmd, engine_cmd = module.build_openradioss_commands(config)
    joined = "\n".join(" ".join(cmd) for cmd in (starter_cmd, engine_cmd))

    assert str(config.run_data_dir) in joined
    assert str(source) not in joined
    assert "starter_linuxa64 -i model_00_0000.rad" in joined
    assert "engine_linuxa64 -i model_00_0001.rad" in joined
    assert "--platform linux/arm64" in joined


def test_write_run_report_carries_tier1_evidence_without_overclaim(tmp_path: Path) -> None:
    module = _load_pipeline_module()
    repo_root = tmp_path / "repo"
    source = _seed_source_case(repo_root)
    config = _config(module, repo_root, source)
    metrics_path = config.graph_case_dir / "ballistic" / "ballistic_metrics.json"
    manifest_path = config.graph_case_dir / "visualization" / "openradioss_animation_manifest.json"
    gif_path = config.graph_case_dir / "visualization" / "openradioss_animation.gif"
    metrics_path.parent.mkdir(parents=True)
    manifest_path.parent.mkdir(parents=True)
    metrics_path.write_text(
        json.dumps(
            {
                "perforation_marker": "perforated_candidate",
                "projectile_initial_velocity_m_per_s": 600.0,
                "residual_velocity_candidate_m_per_s": 52.6,
                "crossing_evidence": {
                    "status": "candidate_observed",
                    "front_face_crossed": True,
                    "back_face_crossed": True,
                    "first_back_face_crossing_t_s": 0.02,
                },
                "residual_velocity_trace": {
                    "status": "candidate_observed",
                    "sample_count": 3,
                    "initial_speed_m_per_s": 600.0,
                    "final_speed_m_per_s": 52.6,
                },
                "partial_energy_audit": {
                    "status": "partial_candidate",
                    "initial_kinetic_energy_j": 904.32,
                    "residual_kinetic_energy_j": 6.97,
                    "missing_terms": [
                        "plastic_dissipation_j",
                        "contact_friction_j",
                        "hourglass_energy_j",
                    ],
                },
            }
        ),
        encoding="utf-8",
    )
    manifest_path.write_text("{}", encoding="utf-8")
    gif_path.write_bytes(b"GIF89a")
    summary = module.SolverSummary(
        starter_error_count=0,
        starter_warning_count=6,
        engine_normal_termination=True,
        engine_cycle_count=8831,
        animation_frame_count=150,
        deleted_elements=[("29", "2.1788E-02")],
        live_solid_count=68,
        total_solid_count=80,
    )

    report = module.write_run_report(
        config=config,
        summary=summary,
        metrics_path=metrics_path,
        manifest_path=manifest_path,
        gif_path=gif_path,
    )
    text = report.read_text(encoding="utf-8")

    assert report == repo_root / "reports" / "gs102_CASE-GS102-PIPELINE_candidate_run.md"
    assert "Tier 1 engineering candidate" in text
    assert "not signed validation" in text
    assert "not benchmark agreement" in text
    assert "perforated_candidate" in text
    assert "## Crossing and energy evidence" in text
    assert "first_back_face_crossing_t_s" in text
    assert "partial_candidate" in text
    assert "validated physics" not in text
    assert "benchmark agreement achieved" not in text
    assert "bullet-through-steel complete" not in text


def test_enrich_metrics_sidecar_adds_crossing_trace_and_partial_energy(
    tmp_path: Path,
) -> None:
    module = _load_pipeline_module()
    metrics_path = tmp_path / "ballistic_metrics.json"
    metrics_path.write_text(
        json.dumps(
            {
                "energy_balance": {
                    "initial_kinetic_energy_j": 904.32,
                    "residual_kinetic_energy_j": 6.97,
                    "plastic_dissipation_j": None,
                    "contact_friction_j": None,
                    "hourglass_energy_j": None,
                }
            }
        ),
        encoding="utf-8",
    )
    samples = [
        module.ProjectileFrameSample(
            sample_index=0,
            t_s=0.0,
            position_m=(0.02, 0.0, 0.0),
            velocity_m_per_s=(600.0, 0.0, 0.0),
        ),
        module.ProjectileFrameSample(
            sample_index=1,
            t_s=0.01,
            position_m=(0.033, 0.0, 0.0),
            velocity_m_per_s=(300.0, 0.0, 0.0),
        ),
        module.ProjectileFrameSample(
            sample_index=2,
            t_s=0.02,
            position_m=(0.041, 0.0, 0.0),
            velocity_m_per_s=(50.0, 0.0, 0.0),
        ),
    ]

    module.enrich_metrics_sidecar(
        metrics_path=metrics_path,
        samples=samples,
        plate_front_m=0.03,
        plate_back_m=0.036,
        impact_axis="x",
    )
    payload = json.loads(metrics_path.read_text(encoding="utf-8"))

    crossing = payload["crossing_evidence"]
    assert crossing["status"] == "candidate_observed"
    assert crossing["front_face_crossed"] is True
    assert crossing["back_face_crossed"] is True
    assert crossing["first_back_face_crossing_sample_index"] == 2

    trace = payload["residual_velocity_trace"]
    assert trace["status"] == "candidate_observed"
    assert trace["sample_count"] == 3
    assert trace["samples"][-1]["speed_m_per_s"] == 50.0

    energy = payload["partial_energy_audit"]
    assert energy["status"] == "partial_candidate"
    assert energy["initial_kinetic_energy_j"] == 904.32
    assert energy["residual_kinetic_energy_j"] == 6.97
    assert energy["missing_terms"] == [
        "plastic_dissipation_j",
        "contact_friction_j",
        "hourglass_energy_j",
    ]


def test_append_solver_evidence_to_metrics_sidecar(tmp_path: Path) -> None:
    module = _load_pipeline_module()
    metrics_path = tmp_path / "ballistic_metrics.json"
    metrics_path.write_text(
        json.dumps({"case_id": "CASE-GS102-SOLVER-EVIDENCE"}),
        encoding="utf-8",
    )
    summary = module.SolverSummary(
        starter_error_count=0,
        starter_warning_count=6,
        engine_normal_termination=True,
        engine_cycle_count=8831,
        animation_frame_count=150,
        deleted_elements=[("29", "2.1788E-02")],
        live_solid_count=68,
        total_solid_count=80,
    )

    module.append_solver_evidence_to_metrics_sidecar(metrics_path, summary)
    payload = json.loads(metrics_path.read_text(encoding="utf-8"))

    evidence = payload["solver_evidence"]
    assert evidence["status"] == "candidate_observed"
    assert evidence["starter_error_count"] == 0
    assert evidence["starter_warning_count"] == 6
    assert evidence["engine_normal_termination"] is True
    assert evidence["engine_cycle_count"] == 8831
    assert evidence["animation_frame_count"] == 150
    assert evidence["live_solid_count"] == 68
    assert evidence["total_solid_count"] == 80
    assert evidence["deleted_element_count"] == 1
    assert evidence["deleted_elements"] == [
        {"element_id": "29", "time_ms": "2.1788E-02"},
    ]
    assert "not signed validation" in evidence["claim_impact"]
