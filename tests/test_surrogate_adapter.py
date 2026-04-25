"""Tests for agents/surrogate_adapter.py — SimPlan → surrogate input dict."""

from __future__ import annotations

import pytest

try:
    from agents.surrogate_adapter import (
        M4_TO_MM4,
        M_TO_MM,
        PA_TO_MPA,
        _extract_inertia_mm4,
        _extract_length_mm,
        _extract_load_N,
        _infer_beam_type,
        predict_for_simplan,
        simplan_to_sim_spec,
    )
    from schemas.sim_plan import GeometrySpec, LoadSpec, MaterialSpec, SimPlan
except ImportError as e:
    pytest.skip(f"adapter imports failed: {e}", allow_module_level=True)


# ---------------------------------------------------------------------------
# Unit constants
# ---------------------------------------------------------------------------


def test_unit_constants():
    assert PA_TO_MPA == 1e-6
    assert M_TO_MM == 1e3
    assert M4_TO_MM4 == 1e12


# ---------------------------------------------------------------------------
# _infer_beam_type
# ---------------------------------------------------------------------------


def test_infer_beam_type_from_ref():
    plan = SimPlan(case_id="AI-FEA-P1-01", geometry=GeometrySpec(ref="cantilever_beam"))
    assert _infer_beam_type(plan) == "cantilever"


def test_infer_beam_type_from_params_kind():
    plan = SimPlan(
        case_id="AI-FEA-P1-02",
        geometry=GeometrySpec(ref="custom", params={"kind": "cantilever"}),
    )
    assert _infer_beam_type(plan) == "cantilever"


def test_infer_beam_type_from_params_structure_type():
    plan = SimPlan(
        case_id="AI-FEA-P1-03",
        geometry=GeometrySpec(ref="x", params={"structure_type": "cantilever"}),
    )
    assert _infer_beam_type(plan) == "cantilever"


def test_infer_beam_type_unknown_returns_none():
    plan = SimPlan(case_id="AI-FEA-P1-04", geometry=GeometrySpec(ref="naca_airfoil"))
    assert _infer_beam_type(plan) is None


def test_infer_beam_type_no_geometry_returns_none():
    class FakePlan:
        pass

    assert _infer_beam_type(FakePlan()) is None


# ---------------------------------------------------------------------------
# Length extraction (Pa→MPa, m→mm conversions)
# ---------------------------------------------------------------------------


def test_extract_length_mm_from_length_m():
    plan = SimPlan(
        case_id="AI-FEA-P1-05",
        geometry=GeometrySpec(ref="cantilever", params={"length_m": 0.1}),
    )
    assert _extract_length_mm(plan) == 100.0


def test_extract_length_mm_from_length_mm_unchanged():
    plan = SimPlan(
        case_id="AI-FEA-P1-06",
        geometry=GeometrySpec(ref="cantilever", params={"length_mm": 100.0}),
    )
    assert _extract_length_mm(plan) == 100.0


def test_extract_length_mm_from_legacy_L_key():
    plan = SimPlan(
        case_id="AI-FEA-P1-07",
        geometry=GeometrySpec(ref="cantilever", params={"L": 0.5}),
    )
    assert _extract_length_mm(plan) == 500.0


def test_extract_length_mm_missing_returns_none():
    plan = SimPlan(case_id="AI-FEA-P1-08", geometry=GeometrySpec(ref="cantilever", params={}))
    assert _extract_length_mm(plan) is None


def test_extract_length_mm_unparseable_returns_none():
    plan = SimPlan(
        case_id="AI-FEA-P1-09",
        geometry=GeometrySpec(ref="cantilever", params={"length_m": "not-a-number"}),
    )
    assert _extract_length_mm(plan) is None


# ---------------------------------------------------------------------------
# Inertia extraction
# ---------------------------------------------------------------------------


def test_extract_inertia_mm4_from_I_m4():
    plan = SimPlan(
        case_id="AI-FEA-P1-10",
        geometry=GeometrySpec(ref="cantilever", params={"I_m4": 8.3333e-10}),
    )
    # 8.3333e-10 m⁴ = 833.33 mm⁴
    assert abs(_extract_inertia_mm4(plan) - 833.33) < 0.01


def test_extract_inertia_mm4_from_I_mm4_unchanged():
    plan = SimPlan(
        case_id="AI-FEA-P1-11",
        geometry=GeometrySpec(ref="cantilever", params={"I_mm4": 833.33}),
    )
    assert _extract_inertia_mm4(plan) == 833.33


# ---------------------------------------------------------------------------
# Load extraction
# ---------------------------------------------------------------------------


def test_extract_load_N_first_load_with_magnitude():
    plan = SimPlan(
        case_id="AI-FEA-P1-12",
        geometry=GeometrySpec(ref="cantilever"),
        loads=[
            LoadSpec(magnitude=400.0),
            LoadSpec(magnitude=999.0),
        ],
    )
    assert _extract_load_N(plan) == 400.0


def test_extract_load_N_skips_loads_without_magnitude():
    plan = SimPlan(
        case_id="AI-FEA-P1-13",
        geometry=GeometrySpec(ref="cantilever"),
        loads=[
            LoadSpec(magnitude=None),
            LoadSpec(magnitude=400.0),
        ],
    )
    assert _extract_load_N(plan) == 400.0


def test_extract_load_N_no_loads_returns_none():
    plan = SimPlan(
        case_id="AI-FEA-P1-14",
        geometry=GeometrySpec(ref="cantilever"),
        loads=[],
    )
    assert _extract_load_N(plan) is None


# ---------------------------------------------------------------------------
# simplan_to_sim_spec — full integration
# ---------------------------------------------------------------------------


def test_simplan_to_sim_spec_full_cantilever():
    """GS-001 numeric values → adapter → matches GS theory inputs."""
    plan = SimPlan(
        case_id="AI-FEA-P1-15",
        geometry=GeometrySpec(
            ref="cantilever_beam",
            params={"length_m": 0.1, "I_m4": 8.3333e-10},
        ),
        material=MaterialSpec(youngs_modulus_pa=210e9),
        loads=[LoadSpec(magnitude=400.0)],
    )
    spec = simplan_to_sim_spec(plan)
    assert spec["case_id"] == "AI-FEA-P1-15"
    assert spec["beam_type"] == "cantilever"
    assert spec["load_N"] == 400.0
    assert spec["length_mm"] == 100.0  # 0.1 m × 1000
    assert abs(spec["E_MPa"] - 210000.0) < 0.1  # 210e9 Pa × 1e-6
    assert abs(spec["I_mm4"] - 833.33) < 0.01


def test_simplan_to_sim_spec_handles_none_input():
    assert simplan_to_sim_spec(None) == {}


def test_simplan_to_sim_spec_minimal_plan():
    """A plan without geometry params + loads still gets case_id."""
    plan = SimPlan(case_id="X", geometry=GeometrySpec(ref="naca"))
    spec = simplan_to_sim_spec(plan)
    assert spec["case_id"] == "X"
    assert "load_N" not in spec
    assert "length_mm" not in spec


def test_simplan_to_sim_spec_omits_missing_e_modulus():
    """Material without parseable youngs_modulus_pa gets E_MPa omitted."""

    class WeirdMat:
        youngs_modulus_pa = "garbage"

    plan = SimPlan(case_id="X", geometry=GeometrySpec(ref="cantilever"))
    plan.material = WeirdMat()  # type: ignore[assignment]
    spec = simplan_to_sim_spec(plan)
    assert "E_MPa" not in spec


# ---------------------------------------------------------------------------
# predict_for_simplan end-to-end
# ---------------------------------------------------------------------------


def test_predict_for_simplan_full_cantilever_yields_hint():
    """Adapter + PlaceholderSurrogate → expected δ ≈ 0.7619mm for GS-001 inputs."""
    plan = SimPlan(
        case_id="AI-FEA-P1-20",
        geometry=GeometrySpec(
            ref="cantilever_beam",
            params={"length_m": 0.1, "I_m4": 8.3333e-10},
        ),
        material=MaterialSpec(youngs_modulus_pa=210e9),
        loads=[LoadSpec(magnitude=400.0)],
    )
    hint = predict_for_simplan(plan)
    assert hint.case_id == "AI-FEA-P1-20"
    assert len(hint.quantities) == 1
    q = hint.quantities[0]
    assert q.name == "max_displacement"
    assert q.unit == "mm"
    assert abs(q.value - 0.7619) < 0.01


def test_predict_for_simplan_unknown_geometry_yields_empty_hint():
    plan = SimPlan(case_id="X", geometry=GeometrySpec(ref="naca_airfoil"))
    hint = predict_for_simplan(plan)
    assert hint.quantities == []
    assert "not handled" in hint.notes or "cannot infer" in hint.notes
