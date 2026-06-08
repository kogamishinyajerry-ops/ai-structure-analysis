import importlib.util
import json
import sys
from pathlib import Path

SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "gs102_design_exploration.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("gs102_design_exploration", SCRIPT_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _write_metrics(
    repo_root: Path,
    *,
    case_id: str,
    velocity: int,
    marker: str,
    back_crossed: bool,
    residual: float,
) -> None:
    metrics_dir = repo_root / "project_state" / "graph_executor" / case_id / "ballistic"
    metrics_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "case_id": case_id,
        "perforation_marker": marker,
        "projectile_initial_velocity_m_per_s": velocity,
        "residual_velocity_candidate_m_per_s": residual,
        "claim_boundary": (
            "tier1_engineering_candidate; not_signed_validation; not_benchmark_agreement"
        ),
        "crossing_evidence": {
            "status": "candidate_observed" if back_crossed else "partial_candidate",
            "front_face_crossed": True,
            "back_face_crossed": back_crossed,
            "first_back_face_crossing_t_s": 0.000049014 if back_crossed else None,
        },
        "solver_evidence": {
            "engine_normal_termination": True,
            "engine_cycle_count": velocity * 10,
            "animation_frame_count": 150,
            "live_solid_count": 68 if back_crossed else 76,
            "total_solid_count": 80,
        },
    }
    (metrics_dir / "ballistic_metrics.json").write_text(
        json.dumps(payload),
        encoding="utf-8",
    )


def test_render_design_exploration_recommends_next_velocity_bracket(
    tmp_path: Path,
) -> None:
    module = _load_module()
    case_ids = [
        "GS-102-transient-refined-v150-bracket-20260512",
        "GS-102-transient-refined-v285-bracket-20260512",
        "GS-102-transient-refined-v600-bracket-20260512",
    ]
    _write_metrics(
        tmp_path,
        case_id=case_ids[0],
        velocity=150,
        marker="embedded_candidate",
        back_crossed=False,
        residual=1.189671,
    )
    _write_metrics(
        tmp_path,
        case_id=case_ids[1],
        velocity=285,
        marker="embedded_candidate",
        back_crossed=False,
        residual=4.667462,
    )
    _write_metrics(
        tmp_path,
        case_id=case_ids[2],
        velocity=600,
        marker="perforated_candidate",
        back_crossed=True,
        residual=52.676288,
    )

    report = module.render_design_exploration_report(
        repo_root=tmp_path,
        case_ids=case_ids,
        report_date="2026-05-12",
    )

    assert "Tier 1 design exploration plan" in report
    assert "Current transition bracket: `285 m/s` to `600 m/s`" in report
    assert "| 365 | refine lower half of transition bracket |" in report
    assert "| 445 | midpoint transition probe |" in report
    assert "| 520 | refine upper half of transition bracket |" in report
    assert "not signed validation" in report
    assert "not benchmark agreement" in report
    assert "validated physics" not in report


def test_render_design_exploration_handles_non_monotonic_candidates(
    tmp_path: Path,
) -> None:
    module = _load_module()
    case_specs = [
        ("GS-102-transient-refined-v150-bracket-20260512", 150, "embedded_candidate", False, 1.0),
        ("GS-102-transient-refined-v285-bracket-20260512", 285, "embedded_candidate", False, 4.0),
        ("GS-102-transient-refined-v365-explore-20260512", 365, "perforated_candidate", True, 34.0),
        ("GS-102-transient-refined-v445-explore-20260512", 445, "embedded_candidate", False, 12.0),
        ("GS-102-transient-refined-v520-explore-20260512", 520, "perforated_candidate", True, 19.0),
        ("GS-102-transient-refined-v600-bracket-20260512", 600, "perforated_candidate", True, 52.0),
    ]
    for case_id, velocity, marker, back_crossed, residual in case_specs:
        _write_metrics(
            tmp_path,
            case_id=case_id,
            velocity=velocity,
            marker=marker,
            back_crossed=back_crossed,
            residual=residual,
        )

    report = module.render_design_exploration_report(
        repo_root=tmp_path,
        case_ids=[case_id for case_id, *_ in case_specs],
        report_date="2026-05-12",
    )

    assert "Non-monotonic candidate response detected" in report
    assert "- `285 m/s` to `365 m/s`: embedded -> perforated" in report
    assert "- `365 m/s` to `445 m/s`: perforated -> embedded" in report
    assert "- `445 m/s` to `520 m/s`: embedded -> perforated" in report
    assert "| 325 | refine lower transition window |" in report
    assert "| 405 | diagnose non-monotonic reversal window |" in report
    assert "| 485 | refine upper transition window |" in report
    assert "not signed validation" in report
    assert "validated physics" not in report
