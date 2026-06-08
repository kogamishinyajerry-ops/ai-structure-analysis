import importlib.util
import json
from pathlib import Path

SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "gs102_velocity_bracket_summary.py"


def _load_summary_module():
    spec = importlib.util.spec_from_file_location("gs102_velocity_bracket_summary", SCRIPT_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write_metrics(repo_root: Path, *, case_id: str, v0: int, perforated: bool) -> None:
    metrics_dir = repo_root / "project_state" / "graph_executor" / case_id / "ballistic"
    metrics_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "case_id": case_id,
        "claim_boundary": (
            "tier1_engineering_candidate; not_signed_validation; not_benchmark_agreement"
        ),
        "perforation_marker": ("perforated_candidate" if perforated else "embedded_candidate"),
        "projectile_initial_velocity_m_per_s": float(v0),
        "residual_velocity_candidate_m_per_s": 12.345678 if perforated else 0.125,
        "crossing_evidence": {
            "status": "candidate_observed" if perforated else "partial_candidate",
            "back_face_crossed": perforated,
            "first_back_face_crossing_t_s": 0.000049014 if perforated else None,
        },
        "partial_energy_audit": {
            "status": "partial_candidate",
            "missing_terms": [
                "plastic_dissipation_j",
                "contact_friction_j",
                "hourglass_energy_j",
            ],
        },
        "solver_evidence": {
            "engine_normal_termination": True,
            "engine_cycle_count": v0 * 10,
            "animation_frame_count": 150,
            "live_solid_count": 68 if perforated else 76,
            "total_solid_count": 80,
        },
    }
    (metrics_dir / "ballistic_metrics.json").write_text(
        json.dumps(payload),
        encoding="utf-8",
    )


def test_render_velocity_bracket_summary_reads_metrics_sidecars(tmp_path: Path) -> None:
    module = _load_summary_module()
    case_ids = [
        "GS-102-transient-refined-v150-bracket-20260512",
        "GS-102-transient-refined-v285-bracket-20260512",
        "GS-102-transient-refined-v600-bracket-20260512",
    ]
    _write_metrics(tmp_path, case_id=case_ids[0], v0=150, perforated=False)
    _write_metrics(tmp_path, case_id=case_ids[1], v0=285, perforated=False)
    _write_metrics(tmp_path, case_id=case_ids[2], v0=600, perforated=True)

    text = module.render_velocity_bracket_summary(
        repo_root=tmp_path,
        case_ids=case_ids,
        report_date="2026-05-12",
    )

    assert text.startswith("# GS-102 Velocity Bracket Summary - 2026-05-12")
    assert "Generated from `ballistic_metrics.json` sidecars." in text
    assert (
        "| `GS-102-transient-refined-v600-bracket-20260512` | 600 | "
        "`perforated_candidate` | 12.345678 | `candidate_observed` | true | "
        "0.000049014 | true / 6000 / 150 / 68 of 80 |"
    ) in text
    assert (
        "project_state/graph_executor/"
        "GS-102-transient-refined-v600-bracket-20260512/ballistic/"
        "ballistic_metrics.json"
    ) in text
    assert "not signed validation" in text
    assert "benchmark agreement" in text
    assert "validated physics" not in text


def test_render_velocity_bracket_summary_flags_non_monotonic_candidates(
    tmp_path: Path,
) -> None:
    module = _load_summary_module()
    case_specs = [
        ("GS-102-transient-refined-v285-bracket-20260512", 285, False),
        ("GS-102-transient-refined-v365-explore-20260512", 365, True),
        ("GS-102-transient-refined-v445-explore-20260512", 445, False),
        ("GS-102-transient-refined-v520-explore-20260512", 520, True),
    ]
    for case_id, velocity, perforated in case_specs:
        _write_metrics(tmp_path, case_id=case_id, v0=velocity, perforated=perforated)

    text = module.render_velocity_bracket_summary(
        repo_root=tmp_path,
        case_ids=[case_id for case_id, *_ in case_specs],
        report_date="2026-05-12",
    )

    assert "Non-monotonic candidate response is present" in text
    assert "`285 m/s -> 365 m/s`: embedded -> perforated" in text
    assert "`365 m/s -> 445 m/s`: perforated -> embedded" in text
    assert "`445 m/s -> 520 m/s`: embedded -> perforated" in text
    assert "not a single physical threshold" in text
    assert "validated physics" not in text
