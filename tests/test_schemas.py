"""Tests for schemas.sim_plan — validates the core contract model."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from schemas.sim_plan import (
    AnalysisType,
    GeometrySpec,
    MaterialSpec,
    SimPlan,
    SolverBackend,
)


class TestSimPlanConstruction:
    """SimPlan should be constructible with minimal required fields."""

    def test_minimal_valid(self):
        plan = SimPlan(
            case_id="AI-FEA-P0-10",
            geometry=GeometrySpec(kind="naca", parameters={"naca": "0012"}),
        )
        assert plan.analysis_type == AnalysisType.STATIC
        assert plan.solver.backend == SolverBackend.CALCULIX
        assert plan.material.youngs_modulus_pa == 210e9

    def test_case_id_pattern_reject(self):
        with pytest.raises(ValidationError):
            SimPlan(
                case_id="bad-id",
                geometry=GeometrySpec(kind="plate"),
            )

    def test_all_analysis_types(self):
        for atype in AnalysisType:
            plan = SimPlan(
                case_id="AI-FEA-P0-01",
                analysis_type=atype,
                geometry=GeometrySpec(kind="truss"),
            )
            assert plan.analysis_type == atype

    def test_material_defaults(self):
        mat = MaterialSpec()
        assert mat.name == "Steel"
        assert mat.poissons_ratio == 0.3

    def test_poisson_bounds(self):
        with pytest.raises(ValidationError):
            MaterialSpec(poissons_ratio=0.6)

    def test_round_trip_json(self):
        plan = SimPlan(
            case_id="AI-FEA-P0-10",
            geometry=GeometrySpec(kind="pressure_vessel", parameters={"radius": 0.5}),
            description="Round-trip test",
        )
        json_str = plan.model_dump_json()
        restored = SimPlan.model_validate_json(json_str)
        assert restored.case_id == plan.case_id
        assert restored.geometry.parameters["radius"] == 0.5
