import importlib.util
import json
import sys
from pathlib import Path

SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "gs102_cfl085_element_history.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("gs102_cfl085_element_history", SCRIPT_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _frame(source: str, timestep: float, alive: list[bool]) -> dict:
    return {
        "source": source,
        "timestep": timestep,
        "element_solid_ids": [23, 24],
        "element_solid_node_indexes": [
            [0, 1, 2, 3],
            [1, 2, 3, 4],
        ],
        "element_solid_is_alive": alive,
        "node_coordinates": [
            [0.0, 0.0, 0.0],
            [4.0, 0.0, 0.0],
            [4.0, 4.0, 0.0],
            [0.0, 4.0, 0.0],
            [8.0, 4.0, 0.0],
        ],
    }


def test_case_history_extracts_first_dead_and_centroids() -> None:
    module = _load_module()
    metrics = {
        "projectile_initial_velocity_m_per_s": 375.0,
        "perforation_marker": "perforated_candidate",
        "residual_velocity_candidate_m_per_s": 35.4,
        "crossing_evidence": {
            "back_face_crossed": True,
            "first_back_face_crossing_t_s": 0.000072,
        },
    }
    history = module._case_history_from_frames(
        case_id="CASE",
        metrics=metrics,
        frame_items=[
            _frame("model_00A001", 0.0, [True, True]),
            _frame("model_00A002", 0.036, [False, True]),
            _frame("model_00A003", 0.12, [False, False]),
        ],
        groups={"sample_group": (23, 24)},
    )

    group = history["groups"]["sample_group"]
    assert group["final_alive_count"] == 0
    assert group["first_any_dead"]["source"] == "model_00A002"
    assert group["first_all_dead"]["source"] == "model_00A003"
    assert group["elements"][0]["initial_centroid_mm"] == [2.0, 2.0, 0.0]
    assert group["elements"][1]["final_alive"] is False


def test_render_element_history_report_preserves_tier1_boundaries() -> None:
    module = _load_module()
    graph_root = "project_state/graph_executor/CASE"
    payload = {
        "report_date": "2026-05-12",
        "cases": [
            {
                "case_id": "CASE",
                "perforation_marker": "perforated_candidate",
                "back_face_crossed": True,
                "metrics_path": f"{graph_root}/ballistic/ballistic_metrics.json",
                "run_data_dir": "project_state/runs/CASE/data",
                "report_path": "reports/gs102_CASE_candidate_run.md",
                "animation_gif_path": f"{graph_root}/visualization/openradioss_animation.gif",
                "animation_manifest_path": (
                    f"{graph_root}/visualization/openradioss_animation_manifest.json"
                ),
                "groups": {
                    "sample_group": {
                        "final_alive_count": 0,
                        "total_count": 1,
                        "first_any_dead": {
                            "source": "model_00A002",
                            "timestep": 0.036,
                        },
                        "first_all_dead": {
                            "source": "model_00A002",
                            "timestep": 0.036,
                        },
                        "final_centroid_x_range_mm": [1.0, 2.0],
                        "elements": [
                            {
                                "element_id": 23,
                                "initial_centroid_mm": [1.0, 2.0, 3.0],
                                "final_centroid_mm": [4.0, 5.0, 6.0],
                                "final_alive": False,
                                "first_dead": {
                                    "source": "model_00A002",
                                    "timestep": 0.036,
                                },
                            }
                        ],
                    }
                },
            }
        ],
    }

    text = module.render_element_history_report(payload)

    assert "Element-Level History Summary" in text
    assert "Full-flow animation GIF" in text
    assert "not signed validation" in text
    assert "not benchmark agreement" in text
    forbidden_phrase = "validated" + " physics"
    assert forbidden_phrase not in text


def test_write_element_history_rejects_golden_sample_json_output(tmp_path: Path) -> None:
    module = _load_module()
    payload = {
        "report_date": "2026-05-12",
        "claim_boundary": module.CLAIM_BOUNDARY,
        "cases": [],
    }
    json_path = tmp_path / "golden_samples" / "bad.json"
    report_path = tmp_path / "reports" / "ok.md"
    try:
        module.write_element_history_outputs(
            repo_root=tmp_path,
            json_output=json_path,
            report_output=report_path,
            case_ids=(),
            check=False,
        )
    except ValueError as exc:
        assert "golden_samples" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("expected golden_samples output rejection")

    # Keep payload referenced so future refactors do not remove the boundary fixture.
    assert json.loads(json.dumps(payload))["claim_boundary"] == module.CLAIM_BOUNDARY
