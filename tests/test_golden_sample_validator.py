"""Unit tests for tools.golden_sample_validator (no container needed).

These exercise the metric-reduction + tolerance logic against a
synthetic FRD parse, so the validator itself is protected from
regressions even when the real CalculiX image isn't available.
"""

from __future__ import annotations

import json
from unittest.mock import patch

import numpy as np
import pytest

from tools.golden_sample_validator import (
    MetricResult,
    ValidationResult,
    validate_frd,
)


def _fake_parsed() -> dict:
    """Minimal parsed-FRD dict shaped like tools.frd_parser.parse_frd output."""
    disp_vals = {
        11: np.array([-0.05, -0.76, -0.0], dtype=float),
        22: np.array([+0.05, -0.76, -0.0], dtype=float),
        33: np.array([-0.05, -0.76, +0.0], dtype=float),
        44: np.array([+0.05, -0.76, +0.0], dtype=float),
        1: np.zeros(3),
    }
    stress_vals = {
        12: np.array([244.0, 10.0, 0.0, 5.0, 0.0, 0.0], dtype=float),
        34: np.array([244.0, 10.0, 0.0, 5.0, 0.0, 0.0], dtype=float),
        1: np.array([-238.0, -8.0, 0.0, -5.0, 0.0, 0.0], dtype=float),
        23: np.array([-238.0, -8.0, 0.0, -5.0, 0.0, 0.0], dtype=float),
    }
    return {
        "nodes": {n: np.zeros(3) for n in (1, 11, 22, 33, 44, 12, 34, 23)},
        "fields": {
            "disp": {"values": disp_vals, "components": ["UX", "UY", "UZ"]},
            "stress": {
                "values": stress_vals,
                "components": ["SXX", "SYY", "SZZ", "SXY", "SYZ", "SZX"],
            },
        },
    }


REFS_GS001_5PCT = {
    "default_tolerance_pct": 5.0,
    "metrics": [
        {
            "id": "free_end_deflection_uy",
            "source": "disp",
            "reduction": "avg_magnitude_at_nodes",
            "nodes": [11, 22, 33, 44],
            "component": "UY",
            "reference": 0.7619,
            "unit": "mm",
        },
        {
            "id": "fixed_end_sxx_top",
            "source": "stress",
            "reduction": "avg_magnitude_at_nodes",
            "nodes": [12, 34],
            "component": "SXX",
            "reference": 240.0,
            "unit": "MPa",
        },
    ],
}


def test_passes_when_within_tolerance():
    with patch(
        "tools.golden_sample_validator.parse_frd",
        return_value=_fake_parsed(),
    ):
        res = validate_frd("/fake.frd", REFS_GS001_5PCT, case_id="GS-001")
    assert res.passed
    assert len(res.metrics) == 2
    uy = res.metrics[0]
    assert uy.metric_id == "free_end_deflection_uy"
    assert abs(uy.error_pct) < 1.0  # 0.76 vs 0.7619


def test_fails_when_out_of_tolerance():
    # Tighten tolerance to 0.1% so fake data fails on UY (~0.25% error).
    tight = {
        "default_tolerance_pct": 0.1,
        "metrics": [REFS_GS001_5PCT["metrics"][0]],
    }
    with patch(
        "tools.golden_sample_validator.parse_frd",
        return_value=_fake_parsed(),
    ):
        res = validate_frd("/fake.frd", tight, case_id="GS-001")
    assert not res.passed
    assert res.metrics[0].passed is False


def test_missing_field_flags_metric_as_failed():
    parsed = _fake_parsed()
    parsed["fields"].pop("stress")
    with patch("tools.golden_sample_validator.parse_frd", return_value=parsed):
        res = validate_frd("/fake.frd", REFS_GS001_5PCT, case_id="GS-001")
    assert not res.passed
    # Displacement still computes; stress metric records error.
    failed = [m for m in res.metrics if not m.passed]
    assert any("stress" in m.detail.lower() or "stress" in m.metric_id for m in failed)


def test_unknown_component_raises_on_compute():
    parsed = _fake_parsed()
    refs = {
        "metrics": [
            {
                "id": "bogus",
                "source": "disp",
                "reduction": "avg_magnitude_at_nodes",
                "nodes": [11],
                "component": "BOGUS",
                "reference": 1.0,
                "unit": "",
            }
        ]
    }
    with patch("tools.golden_sample_validator.parse_frd", return_value=parsed):
        res = validate_frd("/fake.frd", refs, case_id="X")
    assert not res.passed
    assert "Unknown component" in res.metrics[0].detail


def test_von_mises_reduction():
    parsed = _fake_parsed()
    # Pick up stress field-wide von-mises max.
    refs = {
        "metrics": [
            {
                "id": "vm_max",
                "source": "stress",
                "reduction": "von_mises_max",
                "reference": 250.0,
                "tolerance_pct": 20.0,
                "unit": "MPa",
            }
        ]
    }
    with patch("tools.golden_sample_validator.parse_frd", return_value=parsed):
        res = validate_frd("/fake.frd", refs, case_id="X")
    assert res.metrics[0].computed > 0.0


def test_summary_lines_human_readable():
    with patch(
        "tools.golden_sample_validator.parse_frd",
        return_value=_fake_parsed(),
    ):
        res = validate_frd("/fake.frd", REFS_GS001_5PCT, case_id="GS-001")
    lines = res.summary_lines()
    assert any("GS-001" in line for line in lines)
    assert any("PASS" in line for line in lines)


def test_to_dict_is_json_serializable():
    with patch(
        "tools.golden_sample_validator.parse_frd",
        return_value=_fake_parsed(),
    ):
        res = validate_frd("/fake.frd", REFS_GS001_5PCT, case_id="GS-001")
    blob = json.dumps(res.to_dict())
    assert "free_end_deflection_uy" in blob


def test_metric_result_dataclass():
    m = MetricResult(
        metric_id="x",
        reference=1.0,
        computed=1.01,
        error_pct=1.0,
        tolerance_pct=5.0,
        passed=True,
        unit="mm",
        detail="",
    )
    d = m.to_dict()
    assert d["passed"] is True


def test_empty_metrics_list_trivially_passes():
    parsed = _fake_parsed()
    with patch("tools.golden_sample_validator.parse_frd", return_value=parsed):
        res = validate_frd("/fake.frd", {"metrics": []}, case_id="X")
    assert res.passed
    assert res.metrics == []
