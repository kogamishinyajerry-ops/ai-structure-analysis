"""Tests for schemas.sim_plan — validates the canonical contract model."""

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
    """SimPlan should accept canonical PRD fields and legacy aliases."""

    def test_minimal_valid_canonical_shape(self):
        plan = SimPlan(
            case_id="AI-FEA-P0-10",
            physics={"type": "static"},
            geometry={"mode": "knowledge", "ref": "naca", "params": {"profile": "NACA0012"}},
        )

        assert plan.physics.type == AnalysisType.STATIC
        assert plan.analysis_type == AnalysisType.STATIC
        assert plan.solver.name == SolverBackend.CALCULIX
        assert plan.solver.backend == SolverBackend.CALCULIX
        assert plan.reference.tol_pct == 5.0

    def test_legacy_shape_is_upgraded(self):
        plan = SimPlan(
            case_id="AI-FEA-P0-12",
            analysis_type=AnalysisType.MODAL,
            geometry=GeometrySpec(kind="naca", parameters={"profile": "NACA0012"}),
            boundary_conditions=[{"kind": "fixed", "parameters": {"node_set": "Nroot"}}],
            reference_values={"displacement": 1.0e-3},
            solver={"backend": "calculix"},
        )

        assert plan.physics.type == AnalysisType.MODAL
        assert plan.geometry.mode == "knowledge"
        assert plan.geometry.ref == "naca"
        assert plan.geometry.kind == "naca"
        assert plan.boundary_conditions[0].parameters["node_set"] == "Nroot"
        assert plan.reference.value["displacement"] == 1.0e-3
        assert plan.reference_values["displacement"] == 1.0e-3
        assert plan.solver.name == SolverBackend.CALCULIX

    def test_case_id_pattern_reject(self):
        with pytest.raises(ValidationError):
            SimPlan(
                case_id="bad-id",
                physics={"type": "static"},
                geometry={"mode": "knowledge", "ref": "naca", "params": {}},
            )

    def test_all_analysis_types(self):
        for analysis_type in AnalysisType:
            plan = SimPlan(
                case_id="AI-FEA-P0-01",
                physics={"type": analysis_type},
                geometry={"mode": "knowledge", "ref": "truss", "params": {}},
            )
            assert plan.analysis_type == analysis_type

    def test_material_defaults(self):
        mat = MaterialSpec()
        assert mat.name == "Aluminum 7075"
        assert mat.poissons_ratio == 0.33

    def test_poisson_bounds(self):
        with pytest.raises(ValidationError):
            MaterialSpec(poissons_ratio=0.6)

    def test_round_trip_json(self):
        plan = SimPlan(
            case_id="AI-FEA-P0-10",
            physics={"type": "static"},
            geometry={"mode": "knowledge", "ref": "pressure_vessel", "params": {"radius": 0.5}},
            description="Round-trip test",
        )
        json_str = plan.model_dump_json()
        restored = SimPlan.model_validate_json(json_str)
        assert restored.case_id == plan.case_id
        assert restored.geometry.params["radius"] == 0.5
