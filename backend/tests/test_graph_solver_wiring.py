"""ADR-029 P3 — the 4-node architect→geometry→mesh→solver graph drives SOLVER_RUN.

P2 added the second cross-node edge (geometry→mesh). P3 adds the third (mesh→solver) and is the
FIRST graph to launch a real ``ccx`` subprocess from the LangGraph runtime — the SOLVER ISOLATION
GATE. The solver node consumes the mesh node's hardcoded 4-node/1-tet C3D4 *fallback* mesh and
really invokes ccx, which FAILS by construction (the dummy mesh defines no ``Nall/Nfix/Eall`` sets →
``rc=201`` deck-parse when ccx is present, ``PREFLIGHT_FAILED`` when absent). Flag-gated
``workflow_graph_solver`` (default off).

THE HONESTY ENVELOPE these tests pin:

* the 4-node COMPILED GRAPH RUNTIME ran (invoke-spied), not a direct solver.run;
* the solve is a FAILURE — projected ``status=FAILED`` (never a green SUCCESS), ``tier_0_dummy`` with
  ``dummyFidelityInputs=True``, ``solverAttempted=True`` + ``solverRan=False``, NO measurement-shaped
  key surfaced (anti-vacuous-pass), and the disclosure states the TRUE cause (deck-parse/preflight,
  NOT numerical divergence) + the driver catch-all mislabel;
* the WIRING FACT is the ``solver`` history entry — NOT a tautological ``fault_class`` key, NOT
  ``frd_path`` (absent on a faulted solve); no solver history → falls back to scripted;
* provenance stays ``deterministic_agent`` (no 4th value), but the pipeline HALTS at the faulted
  solver (mirrors the real-LE10 solve-failure break), so downstream stays PENDING — NO
  ``converged=True`` / stress results / safety factor are ever fabricated. Net agent-driven coverage
  is ~unchanged (the deliverable is the wiring proof + honest halt, not a coverage increase);
* the ccx subprocess launches EXACTLY ONCE per run, off the event loop in ``_advance`` (never in the
  per-tick ``_build_stage_state`` seam);
* the no-mislabel guards hold (real gmsh/FreeCAD kernel, or non-NACA → fall back to scripted);
* ``workflow_real_solver`` wins when both flags are on (the LE10 Tier-1 path owns SOLVER_RUN);
* every solver-driving test monkeypatches ``agents.solver.run`` to a canonical fault shape, so the
  suite is host-independent and NEVER launches a real ccx subprocess on a ccx-equipped CI runner.
"""

from __future__ import annotations

import asyncio
import shutil

import pytest

from app.core.config import settings
from app.services.workflow.mock_pipeline import MockWorkflowStore

import agents.architect as architect_mod
import agents.graph_runner as gr
import agents.solver as solver_mod
from agents.graph_runner import run_solver_via_graph
from agents.state_projection import _SOLVER_MEASUREMENT_KEYS
from schemas.sim_plan import GeometrySpec, SimPlan
from schemas.sim_state import FaultClass
from schemas.workflow_state import StageProvenance, StageStatus, WorkflowStage

_NACA = "分析这个机翼 NACA0012 的结构强度"
_BRACKET = "对支架做静力分析，关注应力与位移"


def _triple_dummy(monkeypatch) -> None:
    """Force the only honest tier_0 solver-crossing regime: NACA + no FreeCAD + no gmsh, so the
    test is independent of whether the host/CI has a real FreeCAD or gmsh kernel installed."""
    monkeypatch.setattr("tools.freecad_driver.FREECAD_AVAILABLE", False)
    monkeypatch.setattr("tools.gmsh_driver.GMSH_AVAILABLE", False)


def _ccx_dummy_fault(monkeypatch) -> dict:
    """Monkeypatch ``agents.solver.run`` to the canonical faulted-solve shape (``_failed_solve``
    rc=201) WITHOUT launching a real ccx subprocess — host-independent, so the suite never spawns
    ccx on a ccx-equipped CI runner. Returns the captured-call sink for spying."""
    calls: dict = {"count": 0}

    def _fake_run(state):
        calls["count"] += 1
        return {
            "fault_class": FaultClass.SOLVER_CONVERGENCE,
            "retry_budgets": {"solver": 1},
            "history": [
                {
                    "node": "solver",
                    "fault_class": FaultClass.SOLVER_CONVERGENCE.value,
                    "msg": "*ERROR reading *ELSET: Eall is not defined\n****",
                    "ccx_version": "2.23",
                    "returncode": 201,
                    "wall_time_s": 0.31,
                }
            ],
            "verdict": "re-run",
        }

    monkeypatch.setattr(solver_mod, "run", _fake_run)
    return calls


def _agent_driven(run) -> int:
    return sum(1 for s in run.stages if s.provenance is not StageProvenance.SCRIPTED_DEMO)


def _stage(run, stage: WorkflowStage):
    return next(s for s in run.stages if s.stage is stage)


# --- the 4-node compiled-graph runtime ran (third cross-node edge) ------------


def test_run_solver_via_graph_invokes_4node_graph(monkeypatch) -> None:
    """Spy the compiled 4-node graph's .invoke so the test proves the GRAPH RUNTIME drove the
    solver stage (architect→geometry→mesh→solver), not a direct solver.run."""
    _triple_dummy(monkeypatch)
    _ccx_dummy_fault(monkeypatch)
    monkeypatch.setattr(architect_mod, "_extract_structured_data", lambda **kw: None)
    real_build = gr.build_intake_geometry_mesh_solver_graph
    seen: dict = {}

    class _SpyGraph:
        def __init__(self, real):
            self._real = real

        def invoke(self, state, *a, **k):
            seen["invoked"] = True
            return self._real.invoke(state, *a, **k)

    monkeypatch.setattr(
        gr, "build_intake_geometry_mesh_solver_graph", lambda: _SpyGraph(real_build())
    )
    st = run_solver_via_graph(_NACA, run_id="r")

    assert seen.get("invoked") is True  # the 4-node compiled-graph runtime ran
    assert st.stage is WorkflowStage.SOLVER_RUN


# --- faulted tier_0_dummy + the dummyFidelityInputs guard (the P3 deliverable) -


def test_keyless_solver_is_tier0_dummy_failed_with_guard(monkeypatch) -> None:
    """Keyless: a deterministic NACA plan is seeded; the solver node really attempts ccx over a
    DUMMY fallback mesh and FAILS → status FAILED, tier_0_dummy with dummyFidelityInputs=True,
    solverAttempted=True/solverRan=False, NO measurement key, provenance unchanged."""
    _triple_dummy(monkeypatch)
    _ccx_dummy_fault(monkeypatch)
    monkeypatch.setattr(architect_mod, "_extract_structured_data", lambda **kw: None)
    st = run_solver_via_graph(_NACA, run_id="r")
    m = st.metrics.model_dump(by_alias=True, exclude_none=True)

    assert st.status is StageStatus.FAILED  # the solve was rejected — never green
    assert st.provenance is StageProvenance.DETERMINISTIC_AGENT  # NOT a provenance flip
    assert m["graphNodeRan"] is True
    assert m["graphRunner"] == "langgraph-architect-geometry-mesh-solver"
    assert m["planAuthoredBy"] == "deterministic_seed"
    assert m["fidelityTier"] == "tier_0_dummy"
    assert m["solverAttempted"] is True
    assert m["ccxSubprocessLaunched"] is True  # rc=201 present → ccx genuinely launched
    assert m["solverRan"] is False
    assert m["dummyFidelityInputs"] is True  # the P3 load-bearing guard
    assert m["fidelity"]["dataReal"] is False
    for k in _SOLVER_MEASUREMENT_KEYS:
        assert k not in m  # anti-vacuous-pass: no result-shaped solver metric surfaced
    assert st.artifacts.model_dump(exclude_none=True) == {}  # nothing real persisted
    assert st.errors and st.errors[0].fault_class is FaultClass.SOLVER_CONVERGENCE


def test_faulted_solve_is_failed_not_success(monkeypatch) -> None:
    """The blocking honesty pin: a faulted ccx solve must NEVER be projected as a green SUCCESS."""
    _triple_dummy(monkeypatch)
    _ccx_dummy_fault(monkeypatch)
    monkeypatch.setattr(architect_mod, "_extract_structured_data", lambda **kw: None)
    st = run_solver_via_graph(_NACA, run_id="r")
    assert st.status is StageStatus.FAILED
    assert st.status is not StageStatus.SUCCESS


def test_disclosure_states_true_fault_cause_not_diverged(monkeypatch) -> None:
    """The disclosure states the TRUE cause (undefined sets / deck parse / preflight) and flags the
    driver's returncode!=0 catch-all — it must NOT assert numerical divergence, and must NOT echo
    the solver banner (the ccx '****' asterisks)."""
    _triple_dummy(monkeypatch)
    _ccx_dummy_fault(monkeypatch)
    monkeypatch.setattr(architect_mod, "_extract_structured_data", lambda **kw: None)
    st = run_solver_via_graph(_NACA, run_id="r")
    expl = st.agent_explanation or ""

    assert "ccx" in expl
    assert "Nall/Nfix/Eall" in expl or "未定义" in expl  # the real cause
    assert "rc=201" in expl  # the genuine returncode (read as an int, not the banner)
    assert "兜底" in expl or "catch-all" in expl  # the driver returncode!=0 catch-all named
    assert "非真实数值发散" in expl or "not numerical divergence" in expl  # NOT divergence
    assert "dummyFidelityInputs" in expl
    assert "tier_0_dummy" in expl  # the disclosure names the tier explicitly
    assert "真实启动 ccx 子进程" in expl  # rc present → ccx genuinely launched (then faulted)
    assert "****" not in expl  # never echo the ccx banner asterisks


def test_preflight_fault_does_not_claim_ccx_launched(monkeypatch) -> None:
    """Codex P1: a solver history entry with NO returncode (ccx absent → _preflight_failure, or a
    non-CalculiX backend → _unsupported_backend_failure) means the ccx subprocess NEVER launched.
    The projection must NOT claim an attempted solve / deck-parse fault: ccxSubprocessLaunched=False,
    solverAttempted=False, and the disclosure says ccx did not launch — while the solver NODE still
    ran (graphNodeRan=True) and the stage is still FAILED tier_0_dummy."""
    _triple_dummy(monkeypatch)
    monkeypatch.setattr(architect_mod, "_extract_structured_data", lambda **kw: None)

    def _preflight(state):
        # Mirrors agents.solver._preflight_failure: a solver history entry with NO returncode.
        return {
            "fault_class": FaultClass.UNKNOWN,
            "history": [{"node": "solver", "fault_class": "unknown", "msg": "ccx not found\n****"}],
        }

    monkeypatch.setattr(solver_mod, "run", _preflight)
    st = run_solver_via_graph(_NACA, run_id="r")
    m = st.metrics.model_dump(by_alias=True, exclude_none=True)

    assert st.status is StageStatus.FAILED
    assert m["graphNodeRan"] is True  # the solver NODE ran
    assert m["ccxSubprocessLaunched"] is False  # but ccx never launched
    assert m["solverAttempted"] is False  # so no attempted solve is claimed
    assert m["fidelityTier"] == "tier_0_dummy"
    assert m["dummyFidelityInputs"] is True
    expl = st.agent_explanation or ""
    assert "未启动" in expl  # the disclosure states ccx did not launch
    assert "rc=" not in expl  # no fabricated returncode / deck-parse claim
    assert "****" not in expl  # never echo the banner
    assert st.errors and st.errors[0].fault_class is FaultClass.UNKNOWN


def test_no_solver_history_falls_back_to_scripted(monkeypatch) -> None:
    """The non-tautological wiring guard: a graph whose solver node appends NO history entry (the
    bare missing-mesh early returns) is NOT honestly graph-driven → run_solver_via_graph raises
    NotImplementedError (the caller keeps the scripted solver spec), never projecting a crossing."""
    _triple_dummy(monkeypatch)
    monkeypatch.setattr(architect_mod, "_extract_structured_data", lambda **kw: None)
    # A solver that returns no history entry (mirrors solver.run's bare missing-mesh early returns).
    monkeypatch.setattr(solver_mod, "run", lambda state: {"fault_class": FaultClass.UNKNOWN})
    with pytest.raises(NotImplementedError):
        run_solver_via_graph(_NACA, run_id="r")


def test_real_frd_present_refuses_tier0_mislabel(monkeypatch) -> None:
    """Defense-in-depth: if the final state carries a real frd_path (a SUCCESSFUL solve), the
    tier_0_dummy faulted-solve projector must refuse — never mislabel a real solve."""
    _triple_dummy(monkeypatch)
    monkeypatch.setattr(architect_mod, "_extract_structured_data", lambda **kw: None)

    def _green(state):
        return {
            "fault_class": FaultClass.NONE,
            "frd_path": "/tmp/solve.frd",
            "history": [{"node": "solver", "returncode": 0}],
        }

    monkeypatch.setattr(solver_mod, "run", _green)
    # run_solver_via_graph swallows the projector's RuntimeError into NotImplementedError (fall back).
    with pytest.raises(NotImplementedError):
        run_solver_via_graph(_NACA, run_id="r")


def test_architect_authored_plan_flows_to_solver(monkeypatch) -> None:
    """When the LLM architect node authors a plan, THAT plan flows architect→geometry→mesh→solver.
    planAuthoredBy flips to architect_llm and the solver stage still rides FAILED tier_0_dummy."""
    _triple_dummy(monkeypatch)
    _ccx_dummy_fault(monkeypatch)
    authored = SimPlan(
        case_id="AI-FEA-P0-77",
        geometry=GeometrySpec(kind="naca", parameters={"profile": "NACA0012"}),
    )
    monkeypatch.setattr(architect_mod, "_extract_structured_data", lambda **kw: authored)
    st = run_solver_via_graph(_NACA, run_id="r", existing_case_id="AI-FEA-P0-77")
    m = st.metrics.model_dump(by_alias=True, exclude_none=True)

    assert m["planAuthoredBy"] == "architect_llm"  # architect authored, not the seed
    assert m["caseId"] == "AI-FEA-P0-77"  # the architect plan's case id reached solver
    assert m["fidelityTier"] == "tier_0_dummy"
    assert m["dummyFidelityInputs"] is True
    assert st.status is StageStatus.FAILED
    assert st.provenance is StageProvenance.DETERMINISTIC_AGENT
    assert "architect→geometry→mesh→solver 作者依赖" in (st.agent_explanation or "")


# --- the HALT: the faulted solver halts the pipeline, no downstream fabrication


def test_graph_solver_halts_pipeline_no_fabrication(monkeypatch) -> None:
    """Flag on: run_sync drives the real solver node, the dummy-mesh ccx solve faults → SOLVER_RUN
    FAILED + the pipeline HALTS. Downstream stays PENDING (never reached), so NO converged=True /
    stress results are fabricated. SOLVER_RUN flips scripted_demo → deterministic_agent, but because
    the pipeline halts the downstream RESULT_ANALYSIS routing is not reached → net agent-driven
    coverage is ~unchanged (wiring proof, NOT a coverage increase)."""
    _triple_dummy(monkeypatch)
    _ccx_dummy_fault(monkeypatch)
    monkeypatch.setattr(architect_mod, "_extract_structured_data", lambda **kw: None)

    off = MockWorkflowStore().run_sync(user_request=_NACA)
    monkeypatch.setattr(settings, "workflow_graph_solver", True)
    on = MockWorkflowStore().run_sync(user_request=_NACA)

    solver_off = _stage(off, WorkflowStage.SOLVER_RUN)
    solver_on = _stage(on, WorkflowStage.SOLVER_RUN)

    # off-flag: scripted solver, full pipeline runs to completion.
    assert solver_off.provenance is StageProvenance.SCRIPTED_DEMO
    assert "graphNodeRan" not in solver_off.metrics.model_dump(by_alias=True, exclude_none=True)

    # on-flag: real solver node drove SOLVER_RUN, faulted → FAILED + deterministic_agent.
    on_m = solver_on.metrics.model_dump(by_alias=True, exclude_none=True)
    assert solver_on.status is StageStatus.FAILED
    assert solver_on.provenance is StageProvenance.DETERMINISTIC_AGENT
    assert on_m["graphNodeRan"] is True
    assert on_m["dummyFidelityInputs"] is True
    assert on_m["fidelityTier"] == "tier_0_dummy"

    # the pipeline HALTED: every downstream stage is PENDING (not reached) — nothing fabricated.
    downstream = [
        WorkflowStage.CONVERGENCE_MONITORING,
        WorkflowStage.POST_PROCESSING,
        WorkflowStage.RESULT_ANALYSIS,
        WorkflowStage.REPORT_GENERATION,
    ]
    for stage in downstream:
        s = _stage(on, stage)
        assert s.status is StageStatus.PENDING  # never reached
        dm = s.metrics.model_dump(by_alias=True, exclude_none=True)
        assert dm.get("converged") is not True  # NO fabricated convergence after a rejected solve
    assert on.status is StageStatus.FAILED  # the run honestly halted FAILED

    # net agent-driven coverage ~ unchanged: solver gained, result_analysis (routing) not reached.
    assert _stage(off, WorkflowStage.RESULT_ANALYSIS).provenance is StageProvenance.DETERMINISTIC_AGENT
    assert _stage(on, WorkflowStage.RESULT_ANALYSIS).status is StageStatus.PENDING
    assert _agent_driven(on) <= _agent_driven(off)  # NOT a coverage increase (the honest framing)


def test_convergence_never_claims_converged_under_graph_solver(monkeypatch) -> None:
    """The faulted dummy solve must NEVER imply convergence: CONVERGENCE_MONITORING is not reached
    (PENDING) and therefore never shows the scripted converged=True after a rejected solve."""
    _triple_dummy(monkeypatch)
    _ccx_dummy_fault(monkeypatch)
    monkeypatch.setattr(architect_mod, "_extract_structured_data", lambda **kw: None)
    monkeypatch.setattr(settings, "workflow_graph_solver", True)
    run = MockWorkflowStore().run_sync(user_request=_NACA)
    conv = _stage(run, WorkflowStage.CONVERGENCE_MONITORING)
    assert conv.status is StageStatus.PENDING
    assert conv.metrics.model_dump(by_alias=True, exclude_none=True).get("converged") is not True


def test_solver_case_id_handoff_preserved_through_graph(monkeypatch) -> None:
    """P-handoff invariant survives the third crossing: solver's caseId equals intake's
    request-derived case id (it flows intake→geometry→mesh→solver through the seeded plan)."""
    _triple_dummy(monkeypatch)
    _ccx_dummy_fault(monkeypatch)
    monkeypatch.setattr(architect_mod, "_extract_structured_data", lambda **kw: None)
    monkeypatch.setattr(settings, "workflow_graph_solver", True)
    run = MockWorkflowStore().run_sync(user_request=_NACA)
    intake_m = _stage(run, WorkflowStage.PROJECT_INTAKE).metrics.model_dump(
        by_alias=True, exclude_none=True
    )
    solver_m = _stage(run, WorkflowStage.SOLVER_RUN).metrics.model_dump(
        by_alias=True, exclude_none=True
    )
    assert solver_m["caseId"] == intake_m["caseId"]
    assert solver_m["caseId"] != "AI-FEA-P0-05"


# --- L2: exactly one ccx subprocess per run, off the event loop --------------


def test_graph_solver_runs_once_per_run_not_per_tick(monkeypatch) -> None:
    """L2 guard: the graph-solver must NOT live in the per-tick _build_stage_state seam. Across a
    full run_sync the solver node (and thus ccx) is invoked EXACTLY ONCE — not ~4× (3 progress
    ticks + terminal)."""
    _triple_dummy(monkeypatch)
    calls = _ccx_dummy_fault(monkeypatch)
    monkeypatch.setattr(architect_mod, "_extract_structured_data", lambda **kw: None)
    monkeypatch.setattr(settings, "workflow_graph_solver", True)
    MockWorkflowStore().run_sync(user_request=_NACA)
    assert calls["count"] == 1  # exactly one solve, never per-tick


def test_async_advance_offloads_graph_solver(monkeypatch) -> None:
    """L2 guard (async): in _advance the graph-solver runs via asyncio.to_thread (off the event
    loop) and exactly once."""
    _triple_dummy(monkeypatch)
    calls = _ccx_dummy_fault(monkeypatch)
    monkeypatch.setattr(architect_mod, "_extract_structured_data", lambda **kw: None)
    monkeypatch.setattr(settings, "workflow_graph_solver", True)

    to_thread_calls: dict = {"count": 0}
    real_to_thread = asyncio.to_thread

    async def _spy_to_thread(fn, *a, **k):
        if getattr(fn, "__name__", "") == "_run_graph_solver":
            to_thread_calls["count"] += 1
        return await real_to_thread(fn, *a, **k)

    monkeypatch.setattr(asyncio, "to_thread", _spy_to_thread)

    store = MockWorkflowStore()
    run = store._new_run(label=None, fail_at_stage=None, user_request=_NACA)
    asyncio.run(store._advance(run.run_id, tick_delay_s=0.0))

    assert calls["count"] == 1  # one ccx solve
    assert to_thread_calls["count"] == 1  # routed off the event loop
    assert _stage(run, WorkflowStage.SOLVER_RUN).status is StageStatus.FAILED


# --- no-mislabel guards: a real kernel / non-NACA never crosses via the graph -


def test_gmsh_present_falls_back_no_mislabel(monkeypatch) -> None:
    """A real gmsh kernel would mesh into a REAL mesh whose solve is tier_1; the crossing must
    REFUSE (NotImplementedError → scripted solver spec)."""
    monkeypatch.setattr("tools.freecad_driver.FREECAD_AVAILABLE", False)
    monkeypatch.setattr("tools.gmsh_driver.GMSH_AVAILABLE", True)
    with pytest.raises(NotImplementedError):
        run_solver_via_graph(_NACA, run_id="r")


def test_freecad_present_falls_back_no_mislabel(monkeypatch) -> None:
    """A real FreeCAD kernel would yield real geometry; the solver crossing must refuse."""
    monkeypatch.setattr("tools.freecad_driver.FREECAD_AVAILABLE", True)
    monkeypatch.setattr("tools.gmsh_driver.GMSH_AVAILABLE", False)
    with pytest.raises(NotImplementedError):
        run_solver_via_graph(_NACA, run_id="r")


def test_non_naca_falls_back_no_mislabel(monkeypatch) -> None:
    """A non-NACA family has no dummy mesh path; the crossing must refuse (→ scripted)."""
    _triple_dummy(monkeypatch)
    with pytest.raises(NotImplementedError):
        run_solver_via_graph(_BRACKET, run_id="r")


def test_bracket_flag_on_solver_stays_scripted(monkeypatch) -> None:
    """End-to-end: with the flag on, a bracket run's solver stage stays scripted_demo (the graph
    crossing refused → fell through to the scripted spec) and the full pipeline completes."""
    _triple_dummy(monkeypatch)
    monkeypatch.setattr(settings, "workflow_graph_solver", True)
    run = MockWorkflowStore().run_sync(user_request=_BRACKET)
    solver = _stage(run, WorkflowStage.SOLVER_RUN)
    assert solver.provenance is StageProvenance.SCRIPTED_DEMO
    assert "graphNodeRan" not in solver.metrics.model_dump(by_alias=True, exclude_none=True)
    # the pipeline did NOT halt (no graph crossing) — report generation was reached.
    assert _stage(run, WorkflowStage.REPORT_GENERATION).status is not StageStatus.PENDING


def test_real_solver_flag_wins_over_graph_solver(monkeypatch) -> None:
    """When BOTH workflow_real_solver and workflow_graph_solver are on, the LE10 Tier-1 path owns
    SOLVER_RUN (`real=True` → specs=LE10_STAGE_SPECS → the graph-solver gate's `not real` predicate
    suppresses it). The two flags never both own the stage. (Codex P2: the prior version passed
    fail_at_stage=SOLVER_RUN, which hit the injected-failure branch BEFORE either solver path ran, so
    it proved nothing — here we instead stub the real LE10 solve and spy the graph-solver helper.)"""
    _triple_dummy(monkeypatch)
    calls = _ccx_dummy_fault(monkeypatch)  # the graph's solver fake — must NEVER be reached
    monkeypatch.setattr(architect_mod, "_extract_structured_data", lambda **kw: None)

    graph_helper_calls = {"count": 0}
    real_run_graph_solver = MockWorkflowStore._run_graph_solver

    def _spy_graph_solver(self, run):
        graph_helper_calls["count"] += 1
        return real_run_graph_solver(self, run)

    monkeypatch.setattr(MockWorkflowStore, "_run_graph_solver", _spy_graph_solver)

    # Stub the real LE10 ccx solve so the test stays fast + host-independent (no real ccx / fixture).
    fake_ctx = {
        "ccx_version": "2.23",
        "wall_time_s": 1.0,
        "converged": True,
        "node_count": 22815,
        "frd_path": None,
        "benchmark": {
            "sigma_yy_pa": -5.38e6,
            "target_pa": -5.38e6,
            "residual_pct": 0.0,
            "tolerance_pct": 3.0,
            "verdict": "PASS",
        },
    }
    monkeypatch.setattr(MockWorkflowStore, "_run_real_le10", lambda self, run_id: fake_ctx)

    monkeypatch.setattr(settings, "workflow_real_solver", True)
    monkeypatch.setattr(settings, "workflow_graph_solver", True)
    run = MockWorkflowStore().run_sync(user_request=_NACA)

    # The graph-solver helper + the graph's solver node were never reached (the LE10 path owns it).
    assert graph_helper_calls["count"] == 0
    assert calls["count"] == 0
    solver = _stage(run, WorkflowStage.SOLVER_RUN)
    solver_m = solver.metrics.model_dump(by_alias=True, exclude_none=True)
    assert solver_m.get("graphRunner") != "langgraph-architect-geometry-mesh-solver"
    assert "graphNodeRan" not in solver_m  # the LE10 real path carries no graph fact
    assert solver.status is not StageStatus.FAILED  # the LE10 solve succeeded (stubbed PASS)


# --- flag-off byte-identical default + ADR-015 import discipline --------------


def test_flag_off_byte_identical_default_path(monkeypatch) -> None:
    """workflow_graph_solver=False (default): SOLVER_RUN is the scripted spec (SCRIPTED_DEMO, no
    graphNodeRan) and the full 13-stage pipeline runs — byte-identical to pre-P3."""
    _triple_dummy(monkeypatch)
    monkeypatch.setattr(architect_mod, "_extract_structured_data", lambda **kw: None)
    run = MockWorkflowStore().run_sync(user_request=_NACA)  # flag default off
    solver = _stage(run, WorkflowStage.SOLVER_RUN)
    assert solver.provenance is StageProvenance.SCRIPTED_DEMO
    assert "graphNodeRan" not in solver.metrics.model_dump(by_alias=True, exclude_none=True)
    assert _stage(run, WorkflowStage.REPORT_GENERATION).status is not StageStatus.PENDING


def test_graph_runner_avoids_agents_graph_adds_solver() -> None:
    """The 4-node builder adds agents.solver but must STILL never import agents.graph (ADR-015)."""
    import ast
    import inspect

    imported: set[str] = set()
    for node in ast.walk(ast.parse(inspect.getsource(gr))):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            imported.add(mod)
            imported.update(f"{mod}.{alias.name}" for alias in node.names)
    assert not any(m == "agents.graph" or m.startswith("agents.graph.") for m in imported)
    assert "agents.solver" in imported or "agents" in imported


# --- bonus: the REAL ccx subprocess genuinely faults (ccx-equipped hosts only) -


@pytest.mark.skipif(shutil.which("ccx") is None, reason="real ccx not on PATH")
def test_real_ccx_subprocess_faults_and_projects_failed(monkeypatch) -> None:
    """On a ccx-equipped host, exercise the REAL deliverable end-to-end: the 4-node graph launches
    an actual ccx subprocess on the dummy mesh, it faults, and the stage projects FAILED
    tier_0_dummy. NOT monkeypatched — this is the genuine ccx path (skipped on ccx-less CI)."""
    _triple_dummy(monkeypatch)
    monkeypatch.setattr(architect_mod, "_extract_structured_data", lambda **kw: None)
    st = run_solver_via_graph(_NACA, run_id="r")
    m = st.metrics.model_dump(by_alias=True, exclude_none=True)
    assert st.status is StageStatus.FAILED
    assert m["fidelityTier"] == "tier_0_dummy"
    assert m["dummyFidelityInputs"] is True
    assert m["solverAttempted"] is True
    for k in _SOLVER_MEASUREMENT_KEYS:
        assert k not in m
