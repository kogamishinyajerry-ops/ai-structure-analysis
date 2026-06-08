"""Tests for FM-04a P6 candidate ballistic metric extraction.

Tier 1 engineering candidate. Not signed validation. Not benchmark agreement.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.parsers.frd_parser import FRDParser
from app.services import candidate_report_spine as spine_module
from app.services.ballistics import (
    BallisticEnergyAudit,
    BallisticExtractionInput,
    BallisticTimeSample,
    write_ballistic_metrics,
)
from app.services.ballistics.metric_extraction import (
    CLAIM_BOUNDARY,
    PERFORATION_STATES,
)
from app.services.report_generator import ReportGenerator


REPO_ROOT = Path(__file__).resolve().parents[2]
GS001_FRD = REPO_ROOT / "golden_samples" / "GS-001" / "gs001_result.frd"


def _input(samples, **overrides) -> BallisticExtractionInput:
    defaults = dict(
        case_id="CASE-EXTRACT",
        projectile_mass_kg=0.020,
        plate_back_face_x_m=0.012,
        plate_thickness_m=0.012,
        samples=samples,
    )
    defaults.update(overrides)
    return BallisticExtractionInput(**defaults)


def test_writes_perforated_candidate_when_projectile_crosses_with_speed(tmp_path: Path) -> None:
    samples = [
        BallisticTimeSample(t_s=0.0, position_m=(-0.05, 0.0, 0.0), velocity_m_per_s=(285.0, 0.0, 0.0)),
        BallisticTimeSample(t_s=2.0e-4, position_m=(0.06, 0.0, 0.0), velocity_m_per_s=(142.0, 0.0, 0.0)),
    ]
    inp = _input(
        samples,
        energy_audit=BallisticEnergyAudit(
            initial_kinetic_energy_j=812.0,
            plastic_dissipation_j=540.0,
            contact_friction_j=40.0,
            hourglass_energy_j=20.0,
            residual_kinetic_energy_j=212.0,
        ),
    )

    out_path = write_ballistic_metrics(inp, tmp_path)
    assert out_path.name == "ballistic_metrics.json"

    payload = json.loads(out_path.read_text(encoding="utf-8"))
    assert payload["status"] == "candidate_observed"
    assert payload["claim_boundary"] == CLAIM_BOUNDARY
    assert payload["perforation_marker"] == "perforated_candidate"
    assert payload["projectile_initial_velocity_m_per_s"] == pytest.approx(285.0)
    assert payload["residual_velocity_candidate_m_per_s"] == pytest.approx(142.0)
    energy = payload["energy_balance"]
    assert energy["initial_kinetic_energy_j"] == pytest.approx(812.0)
    assert energy["plastic_dissipation_j"] == pytest.approx(540.0)
    assert "claim_impact" in payload["extraction_metadata"]


def test_writes_embedded_candidate_when_final_position_inside_plate(tmp_path: Path) -> None:
    samples = [
        BallisticTimeSample(t_s=0.0, position_m=(-0.05, 0.0, 0.0), velocity_m_per_s=(150.0, 0.0, 0.0)),
        BallisticTimeSample(t_s=3.0e-4, position_m=(0.006, 0.0, 0.0), velocity_m_per_s=(0.0, 0.0, 0.0)),
    ]
    inp = _input(samples)

    out_path = write_ballistic_metrics(inp, tmp_path)
    payload = json.loads(out_path.read_text(encoding="utf-8"))
    assert payload["perforation_marker"] == "embedded_candidate"
    assert payload["residual_velocity_candidate_m_per_s"] == pytest.approx(0.0)


def test_writes_stopped_candidate_when_speed_below_floor_in_front_of_plate(tmp_path: Path) -> None:
    samples = [
        BallisticTimeSample(t_s=0.0, position_m=(-0.05, 0.0, 0.0), velocity_m_per_s=(80.0, 0.0, 0.0)),
        BallisticTimeSample(t_s=4.0e-4, position_m=(-0.001, 0.0, 0.0), velocity_m_per_s=(0.5, 0.0, 0.0)),
    ]
    inp = _input(samples, residual_velocity_floor_m_per_s=5.0)

    payload = json.loads(write_ballistic_metrics(inp, tmp_path).read_text(encoding="utf-8"))
    assert payload["perforation_marker"] == "stopped_candidate"


def test_crossed_with_negligible_speed_marks_stopped_not_perforated(tmp_path: Path) -> None:
    """A grazing crossing with near-zero residual speed is honestly NOT a perforation claim."""
    samples = [
        BallisticTimeSample(t_s=0.0, position_m=(-0.05, 0.0, 0.0), velocity_m_per_s=(150.0, 0.0, 0.0)),
        BallisticTimeSample(t_s=5.0e-4, position_m=(0.020, 0.0, 0.0), velocity_m_per_s=(2.0, 0.0, 0.0)),
    ]
    inp = _input(samples, residual_velocity_floor_m_per_s=5.0)

    payload = json.loads(write_ballistic_metrics(inp, tmp_path).read_text(encoding="utf-8"))
    assert payload["perforation_marker"] == "stopped_candidate"


def test_marker_set_is_closed() -> None:
    """The extractor must only emit markers from the closed set the spine accepts."""
    assert PERFORATION_STATES == {
        "still",
        "embedded_candidate",
        "perforated_candidate",
        "stopped_candidate",
        "unknown",
    }


def test_input_validation_rejects_bad_axis_or_zero_mass() -> None:
    samples = [
        BallisticTimeSample(t_s=0.0, position_m=(0.0, 0.0, 0.0), velocity_m_per_s=(1.0, 0.0, 0.0))
    ]
    with pytest.raises(ValueError, match="impact_axis"):
        _input(samples, impact_axis="w")
    with pytest.raises(ValueError, match="projectile_mass_kg"):
        _input(samples, projectile_mass_kg=0.0)
    with pytest.raises(ValueError, match="plate_thickness_m"):
        _input(samples, plate_thickness_m=0.0)


def test_extractor_payload_is_consumable_by_candidate_report_spine(
    tmp_path: Path, monkeypatch
) -> None:
    """End-to-end: extractor writes sidecar; spine consumes it; ballistic block populated."""
    if not GS001_FRD.exists():
        pytest.skip(f"GS-001 FRD fixture missing at {GS001_FRD}")

    case_id = "CASE-EXTRACT-E2E"
    monkeypatch.setattr(spine_module, "REPO_ROOT", tmp_path)

    case_dir = tmp_path / "golden_samples" / case_id
    case_dir.mkdir(parents=True)
    (case_dir / "expected_results.json").write_text(
        json.dumps(
            {
                "case_id": case_id,
                "case_name": "End-to-end extractor fixture",
                "status": "insufficient_evidence",
                "status_reason": "Tier 1 candidate; not signed validation",
                "failure_pattern_ref": "FP-TEST-EXTRACT",
                "ballistic": {"projectile_initial_velocity_m_per_s": 285.0},
            }
        ),
        encoding="utf-8",
    )
    (case_dir / "model.inp").write_text(
        "*NODE\n1,0,0,0\n*ELEMENT, TYPE=C3D4\n1,1,1,1,1\n", encoding="utf-8"
    )

    runtime_ballistic_dir = (
        tmp_path / "project_state" / "graph_executor" / case_id / "ballistic"
    )

    samples = [
        BallisticTimeSample(t_s=0.0, position_m=(-0.05, 0.0, 0.0), velocity_m_per_s=(285.0, 0.0, 0.0)),
        BallisticTimeSample(t_s=2.0e-4, position_m=(0.06, 0.0, 0.0), velocity_m_per_s=(142.0, 0.0, 0.0)),
    ]
    inp = _input(
        samples,
        case_id=case_id,
        energy_audit=BallisticEnergyAudit(
            initial_kinetic_energy_j=812.0,
            plastic_dissipation_j=540.0,
            contact_friction_j=40.0,
            hourglass_energy_j=20.0,
            residual_kinetic_energy_j=212.0,
        ),
    )
    write_ballistic_metrics(inp, runtime_ballistic_dir)

    parsed = FRDParser().parse(str(GS001_FRD))
    report = ReportGenerator(case_dir.parent).generate(
        parsed,
        case_id=case_id,
        source_path=GS001_FRD,
        original_filename="gs001_result.frd",
    )

    ballistic = report.candidate_report_spine["ballistic"]
    assert ballistic["status"] == "candidate_observed"
    assert ballistic["claim_boundary"] == CLAIM_BOUNDARY
    assert ballistic["projectile_initial_velocity"]["status"] == "declared"
    assert ballistic["projectile_initial_velocity"]["value_m_per_s"] == pytest.approx(285.0)
    assert ballistic["residual_velocity_candidate"]["status"] == "candidate_observed"
    assert ballistic["residual_velocity_candidate"]["value_m_per_s"] == pytest.approx(142.0)
    assert ballistic["perforation_marker"]["status"] == "perforated_candidate"
    energy = ballistic["energy_balance_candidate"]
    assert energy["status"] == "available"
    assert energy["initial_kinetic_energy_j"] == pytest.approx(812.0)
    # plastic + contact + hourglass + residual = 540 + 40 + 20 + 212 = 812; ratio 1.0
    assert energy["energy_ratio"] == pytest.approx(1.0)
    assert "energy ratio is a Tier 1 candidate health indicator only" in energy["claim_impact"]
    assert "ballistic candidate evidence is unavailable" not in report.candidate_report_spine["limitations"]
