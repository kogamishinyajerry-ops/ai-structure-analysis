"""ADR-029 — BOTH graph flags on at once (composite of P0-P3 + the Rank-3 WARNING fix).

The two flags own DISJOINT stage sets, so a both-on run lights up a path no single-flag test
covers: ``workflow_graph_intake`` drives the intake / geometry / mesh crossings
(``_GRAPH_REQUEST_STAGES`` in mock_pipeline._build_stage_state) and ``workflow_graph_solver``
separately drives the SOLVER_RUN halt. They never co-own a stage, so both-on simply composes all
four crossings in one pipeline. This module is the ONLY place that pins:

* the intake-flag WARNING tier_0_dummy crossings (geometry + mesh) and the solver-flag FAILED halt
  COEXIST correctly in one run (audit Rank 12);
* the halt fires AFTER the WARNING crossings ran to completion (stage order: geometry/mesh WARNING
  do NOT break the loop; only the FAILED solver does — mock_pipeline._advance break);
* the NET agent-driven coverage is still +1 (the single honest mesh increment): solver's +1 is
  cancelled by result_analysis going PENDING/unreached after the halt — neither flag double-counts;
* the caseId handoff survives ALL FOUR crossings (intake → geometry → mesh → solver);
* no downstream convergence/results are fabricated after the rejected solve.

Hermetic: monkeypatches FreeCAD/gmsh/ccx; never launches a real ccx subprocess.
"""

from __future__ import annotations

from app.core.config import settings
from app.services.workflow.mock_pipeline import MockWorkflowStore

import agents.architect as architect_mod
import agents.solver as solver_mod
from schemas.sim_state import FaultClass
from schemas.workflow_state import StageProvenance, StageStatus, WorkflowStage

_NACA = "分析这个机翼 NACA0012 的结构强度"

_DOWNSTREAM = (
    WorkflowStage.CONVERGENCE_MONITORING,
    WorkflowStage.POST_PROCESSING,
    WorkflowStage.RESULT_ANALYSIS,
    WorkflowStage.REPORT_GENERATION,
)


def _triple_dummy(monkeypatch) -> None:
    """The only honest tier_0 crossing regime: NACA + no FreeCAD + no gmsh, so the test is
    independent of whether the host/CI has a real FreeCAD or gmsh kernel installed."""
    monkeypatch.setattr("tools.freecad_driver.FREECAD_AVAILABLE", False)
    monkeypatch.setattr("tools.gmsh_driver.GMSH_AVAILABLE", False)


def _ccx_dummy_fault(monkeypatch) -> None:
    """Monkeypatch agents.solver.run to the canonical rc=201 SOLVER_SYNTAX faulted shape WITHOUT
    launching a real ccx subprocess — host-independent (mirrors test_graph_solver_wiring)."""

    def _fake_run(state):
        return {
            "fault_class": FaultClass.SOLVER_SYNTAX,
            "retry_budgets": {"solver": 1},
            "history": [
                {
                    "node": "solver",
                    "fault_class": FaultClass.SOLVER_SYNTAX.value,
                    "msg": "*ERROR reading *SOLID SECTION: element set Eall "
                    "has not yet been defined\n****",
                    "ccx_version": "2.23",
                    "returncode": 201,
                    "wall_time_s": 0.31,
                }
            ],
            "verdict": "re-run",
        }

    monkeypatch.setattr(solver_mod, "run", _fake_run)


def _agent_driven(run) -> int:
    return sum(1 for s in run.stages if s.provenance is not StageProvenance.SCRIPTED_DEMO)


def _stage(run, stage: WorkflowStage):
    return next(s for s in run.stages if s.stage is stage)


def _metrics(run, stage: WorkflowStage) -> dict:
    return _stage(run, stage).metrics.model_dump(by_alias=True, exclude_none=True)


def _both_flags_run(monkeypatch):
    _triple_dummy(monkeypatch)
    _ccx_dummy_fault(monkeypatch)
    monkeypatch.setattr(architect_mod, "_extract_structured_data", lambda **kw: None)
    monkeypatch.setattr(settings, "workflow_graph_intake", True)
    monkeypatch.setattr(settings, "workflow_graph_solver", True)
    return MockWorkflowStore().run_sync(user_request=_NACA)


def test_both_flags_on_composite_pipeline(monkeypatch) -> None:
    """The full per-stage composite: intake SUCCESS, geometry+mesh WARNING tier_0_dummy crossings,
    solver FAILED, all downstream PENDING (no fabrication), run FAILED — all in ONE run."""
    run = _both_flags_run(monkeypatch)

    # PROJECT_INTAKE — graph-driven, a deterministic plan (no tier; intake carries no fidelity tier)
    intake = _stage(run, WorkflowStage.PROJECT_INTAKE)
    assert intake.status is StageStatus.SUCCESS
    assert intake.provenance is StageProvenance.DETERMINISTIC_AGENT
    assert _metrics(run, WorkflowStage.PROJECT_INTAKE)["graphNodeRan"] is True

    # GEOMETRY_VALIDATION — tier_0_dummy graph crossing → WARNING (Rank-3), never green
    geom = _stage(run, WorkflowStage.GEOMETRY_VALIDATION)
    assert geom.status is StageStatus.WARNING
    assert geom.provenance is StageProvenance.DETERMINISTIC_AGENT
    gm = _metrics(run, WorkflowStage.GEOMETRY_VALIDATION)
    assert gm["graphNodeRan"] is True
    assert gm["graphRunner"] == "langgraph-architect-geometry"
    assert gm["fidelityTier"] == "tier_0_dummy"

    # MESH_GENERATION — tier_0_dummy graph crossing → WARNING, with the P2 dummyFidelityInputs guard
    mesh = _stage(run, WorkflowStage.MESH_GENERATION)
    assert mesh.status is StageStatus.WARNING
    assert mesh.provenance is StageProvenance.DETERMINISTIC_AGENT
    mm = _metrics(run, WorkflowStage.MESH_GENERATION)
    assert mm["graphNodeRan"] is True
    assert mm["graphRunner"] == "langgraph-architect-geometry-mesh"
    assert mm["fidelityTier"] == "tier_0_dummy"
    assert mm["dummyFidelityInputs"] is True

    # SOLVER_RUN — graph-driven, FAILED (ccx rejected the dummy deck), tier_0_dummy, no artifacts
    solver = _stage(run, WorkflowStage.SOLVER_RUN)
    assert solver.status is StageStatus.FAILED
    assert solver.provenance is StageProvenance.DETERMINISTIC_AGENT
    sm = _metrics(run, WorkflowStage.SOLVER_RUN)
    assert sm["graphNodeRan"] is True
    assert sm["graphRunner"] == "langgraph-architect-geometry-mesh-solver"
    assert sm["fidelityTier"] == "tier_0_dummy"
    assert sm["dummyFidelityInputs"] is True
    assert sm["solverAttempted"] is True
    assert sm["ccxSubprocessLaunched"] is True
    assert sm["solverRan"] is False
    assert solver.errors and solver.errors[0].fault_class is FaultClass.SOLVER_SYNTAX
    assert solver.artifacts.model_dump(exclude_none=True) == {}

    # The halt: every downstream stage stays PENDING and never fabricates convergence
    for stage in _DOWNSTREAM:
        s = _stage(run, stage)
        assert s.status is StageStatus.PENDING, stage
        assert s.metrics.model_dump(by_alias=True, exclude_none=True).get("converged") is not True

    assert run.status is StageStatus.FAILED  # overall honestly halted


def test_both_flags_net_coverage_is_single_mesh_increment(monkeypatch) -> None:
    """The composite NET-coverage invariant no single-flag test can observe: both-on adds exactly
    ONE net agent-driven stage over both-off (the honest mesh increment). solver's +1 is cancelled
    by result_analysis going PENDING/unreached after the halt → net == the single mesh flip."""
    # both OFF baseline
    _triple_dummy(monkeypatch)
    _ccx_dummy_fault(monkeypatch)
    monkeypatch.setattr(architect_mod, "_extract_structured_data", lambda **kw: None)
    monkeypatch.setattr(settings, "workflow_graph_intake", False)
    monkeypatch.setattr(settings, "workflow_graph_solver", False)
    off = MockWorkflowStore().run_sync(user_request=_NACA)

    # both ON
    monkeypatch.setattr(settings, "workflow_graph_intake", True)
    monkeypatch.setattr(settings, "workflow_graph_solver", True)
    on = MockWorkflowStore().run_sync(user_request=_NACA)

    assert _agent_driven(off) == 6
    assert _agent_driven(on) == 7  # net +1, NOT +4

    # the mechanism: mesh flips scripted_demo → deterministic_agent (the +1)...
    assert _stage(off, WorkflowStage.MESH_GENERATION).provenance is StageProvenance.SCRIPTED_DEMO
    on_mesh = _stage(on, WorkflowStage.MESH_GENERATION)
    assert on_mesh.provenance is StageProvenance.DETERMINISTIC_AGENT
    # ...while solver's +1 is cancelled by result_analysis (deterministic_agent off-flag) going
    # PENDING/unreached after the halt (so it no longer counts as agent-driven).
    off_ra = _stage(off, WorkflowStage.RESULT_ANALYSIS)
    assert off_ra.provenance is StageProvenance.DETERMINISTIC_AGENT
    assert _stage(on, WorkflowStage.RESULT_ANALYSIS).status is StageStatus.PENDING


def test_caseid_survives_all_four_crossings(monkeypatch) -> None:
    """The composite of the four per-stage handoff tests: the intake-derived caseId flows
    intake → geometry → mesh → solver through the seeded plan in ONE both-flags run."""
    run = _both_flags_run(monkeypatch)
    case_id = _metrics(run, WorkflowStage.PROJECT_INTAKE)["caseId"]
    assert case_id != "AI-FEA-P0-05"  # NOT the legacy stand-in
    for stage in (
        WorkflowStage.GEOMETRY_VALIDATION,
        WorkflowStage.MESH_GENERATION,
        WorkflowStage.SOLVER_RUN,
    ):
        assert _metrics(run, stage)["caseId"] == case_id


def test_warning_crossings_precede_solver_halt(monkeypatch) -> None:
    """Halt ordering: the WARNING tier_0_dummy crossings (geometry idx2, mesh idx6) ran to
    completion and did NOT break the loop — only the FAILED solver (idx8) halts it, leaving the
    downstream PENDING. Proves the WARNING badges are not failures."""
    run = _both_flags_run(monkeypatch)
    assert _stage(run, WorkflowStage.GEOMETRY_VALIDATION).status is StageStatus.WARNING
    assert _stage(run, WorkflowStage.MESH_GENERATION).status is StageStatus.WARNING
    assert _stage(run, WorkflowStage.SOLVER_RUN).status is StageStatus.FAILED
    # downstream unreached → the FAILED solver (not the WARNINGs) is what halted the pipeline
    assert _stage(run, WorkflowStage.CONVERGENCE_MONITORING).status is StageStatus.PENDING
