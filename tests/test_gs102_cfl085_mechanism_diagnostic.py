import importlib.util
import json
import sys
from pathlib import Path

SCRIPT_PATH = (
    Path(__file__).resolve().parents[1] / "scripts" / "gs102_cfl085_mechanism_diagnostic.py"
)


def _load_module():
    spec = importlib.util.spec_from_file_location(
        "gs102_cfl085_mechanism_diagnostic",
        SCRIPT_PATH,
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _write_case(
    repo_root: Path,
    *,
    case_id: str,
    velocity: int,
    back_crossed: bool,
    final_centroid_x_m: float,
    deleted_elements: list[str],
) -> None:
    metrics_dir = repo_root / "project_state" / "graph_executor" / case_id / "ballistic"
    manifest_dir = repo_root / "project_state" / "graph_executor" / case_id / "visualization"
    run_dir = repo_root / "project_state" / "runs" / case_id / "data"
    metrics_dir.mkdir(parents=True, exist_ok=True)
    manifest_dir.mkdir(parents=True, exist_ok=True)
    run_dir.mkdir(parents=True, exist_ok=True)

    samples = [
        {
            "sample_index": index,
            "t_s": index * 0.000001,
            "centroid_axis_position_m": 0.035 + index * 0.0002,
            "speed_m_per_s": 10.0 + index,
        }
        for index in range(10)
    ]
    first_back_index = 5 if back_crossed else None
    payload = {
        "case_id": case_id,
        "claim_boundary": (
            "tier1_engineering_candidate; not_signed_validation; not_benchmark_agreement"
        ),
        "projectile_initial_velocity_m_per_s": float(velocity),
        "perforation_marker": ("perforated_candidate" if back_crossed else "embedded_candidate"),
        "residual_velocity_candidate_m_per_s": 35.4 if back_crossed else 10.4,
        "crossing_evidence": {
            "plate_back_face_x_m": 0.036,
            "final_centroid_x_m": final_centroid_x_m,
            "front_face_crossed": True,
            "back_face_crossed": back_crossed,
            "first_back_face_crossing_sample_index": first_back_index,
            "first_back_face_crossing_t_s": 0.000005 if back_crossed else None,
        },
        "residual_velocity_trace": {
            "sample_count": len(samples),
            "samples": samples,
        },
        "solver_evidence": {
            "engine_normal_termination": True,
            "engine_cycle_count": 3000 + velocity,
            "animation_frame_count": 10,
            "live_solid_count": 80 - len(deleted_elements),
            "total_solid_count": 80,
            "deleted_element_count": len(deleted_elements),
            "deleted_elements": [
                {"element_id": element_id, "time_ms": "3.5E-02"} for element_id in deleted_elements
            ],
        },
    }
    (metrics_dir / "ballistic_metrics.json").write_text(
        json.dumps(payload),
        encoding="utf-8",
    )
    manifest = {
        "case_id": case_id,
        "frame_count": 4,
        "per_frame": [
            {"source": str(run_dir / "model_00A001"), "timestep": 0.0, "elements_deleted": 0},
            {"source": str(run_dir / "model_00A002"), "timestep": 0.036, "elements_deleted": 4},
            {
                "source": str(run_dir / "model_00A003"),
                "timestep": 0.12,
                "elements_deleted": len(deleted_elements),
            },
            {
                "source": str(run_dir / "model_00A004"),
                "timestep": 0.15,
                "elements_deleted": len(deleted_elements),
            },
        ],
    }
    (manifest_dir / "openradioss_animation_manifest.json").write_text(
        json.dumps(manifest),
        encoding="utf-8",
    )
    log_lines = [
        (
            "EXCEEDED EPS_MAX ON SOLID ELEMENT NUMBER         23: "
            "DEVIATORIC STRESS SET TO 0 ON INTEGRATION POINT     1 "
            "AT TIME : 0.3500E-01"
        )
    ]
    log_lines.extend(
        f"DELETE SOLID ELEMENT NUMBER         {element_id} AT TIME :  3.5000E-02"
        for element_id in deleted_elements
    )
    (run_dir / "engine.log").write_text("\n".join(log_lines), encoding="utf-8")


def test_render_mechanism_diagnostic_compares_crossing_and_terminal_windows(
    tmp_path: Path,
) -> None:
    module = _load_module()
    case_ids = [
        "GS-102-transient-refined-cfl085-v365-bracket-20260512",
        "GS-102-transient-refined-cfl085-v375-bracket-20260512",
        "GS-102-transient-refined-cfl085-v385-bracket-20260512",
    ]
    _write_case(
        tmp_path,
        case_id=case_ids[0],
        velocity=365,
        back_crossed=False,
        final_centroid_x_m=0.0355,
        deleted_elements=["23", "29", "24", "30", "22", "31", "28", "25"],
    )
    _write_case(
        tmp_path,
        case_id=case_ids[1],
        velocity=375,
        back_crossed=True,
        final_centroid_x_m=0.0385,
        deleted_elements=["23", "29", "24", "30"],
    )
    _write_case(
        tmp_path,
        case_id=case_ids[2],
        velocity=385,
        back_crossed=False,
        final_centroid_x_m=0.0356,
        deleted_elements=["23", "29", "24", "30", "22", "31", "28", "25"],
    )

    text = module.render_mechanism_diagnostic(
        repo_root=tmp_path,
        case_ids=case_ids,
        report_date="2026-05-12",
    )

    assert text.startswith("# GS-102 CFL 0.85 Local Mechanism Diagnostic")
    assert "Frame-Level Deletion Accumulation" in text
    assert "Time-Scale Note" in text
    assert "back-face crossing window around sample 5" in text
    assert "terminal window; no back-face crossing observed" in text
    assert "`model_00A002`" in text
    assert "`23`, `29`, `24`, `30`" in text
    assert "not signed validation" in text
    assert "not benchmark agreement" in text
    forbidden_phrase = "validated" + " physics"
    assert forbidden_phrase not in text
