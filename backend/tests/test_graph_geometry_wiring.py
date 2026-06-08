"""ADR-029 P1 — the 2-node architect→geometry graph drives GEOMETRY_VALIDATION.

P0 proved the LangGraph compiled-graph runtime can drive ONE stage (a truncated architect-only
graph → PROJECT_INTAKE). P1 adds the first cross-node EDGE: a truncated architect→geometry graph
whose geometry node CONSUMES the SimPlan the architect step left in the shared SimState — the
first cross-node graph data dependency. Still truncated before mesh/solver (no gmsh/ccx, no
human_fallback/Notion node), flag-gated `workflow_graph_intake` (default off).

These tests pin the honesty floor + safety envelope:

* the 2-node COMPILED GRAPH RUNTIME ran (invoke-spied), not a direct node.run;
* "who authored the consumed plan" is disclosed: keyless → a deterministic plan is SEEDED so
  the geometry node has something to consume (planAuthoredBy=deterministic_seed); with the LLM
  architect authoring a plan, that plan flows architect→geometry (planAuthoredBy=architect_llm)
  — the genuine cross-node authorship dependency;
* the geometry crossing keeps the P-geomrun tier_0_dummy honesty pins (no measurement key,
  cadKernelRan/defectCheckRun False, the 10-byte STEP + tautological valid disclosed);
* provenance stays deterministic_agent → N/13 unchanged (flag on == off);
* non-NACA / FreeCAD-present fall back to the existing projector (no graph crossing, no mislabel);
* NO downstream node (mesh/solver) executes — no ccx subprocess.
"""

from __future__ import annotations

from app.core.config import settings
from app.services.workflow.mock_pipeline import MockWorkflowStore

import agents.architect as architect_mod
import agents.graph_runner as gr
from agents.graph_runner import run_geometry_via_graph
from schemas.sim_plan import GeometrySpec, SimPlan
from schemas.workflow_state import StageProvenance, WorkflowStage

_NACA = "分析这个机翼 NACA0012 的结构强度"
_BRACKET = "对支架做静力分析，关注应力与位移"
_GEOM_MEASUREMENT_KEYS = (
    "watertight",
    "manifold",
    "volume_m3",
    "minFeatureSizeM",
    "boundingBoxMm",
    "valid",
)


def _agent_driven(run) -> int:
    return sum(1 for s in run.stages if s.provenance is not StageProvenance.SCRIPTED_DEMO)


def _geom(run):
    return next(s for s in run.stages if s.stage is WorkflowStage.GEOMETRY_VALIDATION)


# --- the 2-node compiled-graph runtime ran (cross-node edge) -----------------


def test_run_geometry_via_graph_invokes_2node_graph(monkeypatch) -> None:
    """Spy the compiled 2-node graph's .invoke so the test proves the GRAPH RUNTIME drove the
    geometry stage (architect→geometry), not a direct geometry.run."""
    monkeypatch.setattr("tools.freecad_driver.FREECAD_AVAILABLE", False)
    monkeypatch.setattr(architect_mod, "_extract_structured_data", lambda **kw: None)
    real_build = gr.build_intake_geometry_graph
    seen: dict = {}

    class _SpyGraph:
        def __init__(self, real):
            self._real = real

        def invoke(self, state, *a, **k):
            seen["invoked"] = True
            return self._real.invoke(state, *a, **k)

    monkeypatch.setattr(gr, "build_intake_geometry_graph", lambda: _SpyGraph(real_build()))
    st = run_geometry_via_graph(_NACA, run_id="r")

    assert seen.get("invoked") is True  # the 2-node compiled-graph runtime ran
    assert st.stage is WorkflowStage.GEOMETRY_VALIDATION


# --- node-authored-content honesty: seed vs architect-authored --------------


def test_keyless_geometry_seeds_deterministic_plan(monkeypatch) -> None:
    """Keyless the architect authors no plan, so a DETERMINISTIC plan is seeded for the
    geometry node to consume — disclosed as planAuthoredBy=deterministic_seed, tier_0_dummy,
    provenance unchanged, no measurement key."""
    monkeypatch.setattr("tools.freecad_driver.FREECAD_AVAILABLE", False)
    monkeypatch.setattr(architect_mod, "_extract_structured_data", lambda **kw: None)
    st = run_geometry_via_graph(_NACA, run_id="r")
    m = st.metrics.model_dump(by_alias=True, exclude_none=True)

    assert st.provenance is StageProvenance.DETERMINISTIC_AGENT  # NOT a provenance flip
    assert m["graphNodeRan"] is True
    assert m["graphRunner"] == "langgraph-architect-geometry"
    assert m["planAuthoredBy"] == "deterministic_seed"
    assert m["fidelityTier"] == "tier_0_dummy"
    assert m["cadKernelRan"] is False
    assert m["defectCheckRun"] is False
    for k in _GEOM_MEASUREMENT_KEYS:
        assert k not in m  # anti-vacuous-pass: no measurement surfaced
    expl = st.agent_explanation or ""
    assert "跨节点" in expl  # cross-node dependency disclosed
    assert "deterministic" in expl.lower() or "确定性规则代理" in expl
    assert "tautology" in expl and "未验证" in expl  # P-geomrun honesty pins carried


def test_architect_authored_plan_flows_to_geometry(monkeypatch) -> None:
    """When the LLM architect node authors a plan, THAT plan (not the seed) flows
    architect→geometry — the genuine cross-node authorship dependency. planAuthoredBy flips to
    architect_llm and the geometry stage consumes the architect plan's case id."""
    monkeypatch.setattr("tools.freecad_driver.FREECAD_AVAILABLE", False)
    authored = SimPlan(
        case_id="AI-FEA-P0-77",
        geometry=GeometrySpec(kind="naca", parameters={"profile": "NACA0012"}),
    )
    monkeypatch.setattr(architect_mod, "_extract_structured_data", lambda **kw: authored)
    st = run_geometry_via_graph(_NACA, run_id="r", existing_case_id="AI-FEA-P0-77")
    m = st.metrics.model_dump(by_alias=True, exclude_none=True)

    assert m["planAuthoredBy"] == "architect_llm"  # architect authored, not the seed
    assert m["caseId"] == "AI-FEA-P0-77"  # the architect plan's case id reached geometry
    assert m["fidelityTier"] == "tier_0_dummy"
    assert st.provenance is StageProvenance.DETERMINISTIC_AGENT
    assert "architect→geometry 作者依赖" in (st.agent_explanation or "")


# --- wiring is not coverage inflation: N/13 unchanged ------------------------


def test_n13_unchanged_geometry_graph(monkeypatch) -> None:
    # ISOLATE geometry's N-neutrality from ADR-029 P2: the same flag also enables the mesh
    # crossing, which legitimately adds +1 (scripted_demo → deterministic_agent at tier_0_dummy,
    # asserted in test_graph_mesh_wiring). Hold a gmsh kernel "present" so run_mesh_via_graph
    # refuses (→ scripted), keeping this test measuring GEOMETRY's effect alone (still == 6).
    monkeypatch.setattr("tools.freecad_driver.FREECAD_AVAILABLE", False)
    monkeypatch.setattr("tools.gmsh_driver.GMSH_AVAILABLE", True)
    monkeypatch.setattr(architect_mod, "_extract_structured_data", lambda **kw: None)
    off = MockWorkflowStore().run_sync(user_request=_NACA)
    monkeypatch.setattr(settings, "workflow_graph_intake", True)
    on = MockWorkflowStore().run_sync(user_request=_NACA)

    assert _agent_driven(off) == _agent_driven(on) == 6  # geometry wiring != coverage inflation
    assert _geom(off).provenance is StageProvenance.DETERMINISTIC_AGENT
    assert _geom(on).provenance is StageProvenance.DETERMINISTIC_AGENT
    # flag-on geometry carries the 2-node graph fact; flag-off (P-geomrun direct path) does not
    assert "graphNodeRan" not in _geom(off).metrics.model_dump(by_alias=True, exclude_none=True)
    assert _geom(on).metrics.model_dump(by_alias=True, exclude_none=True)["graphNodeRan"] is True


def test_geometry_case_id_handoff_preserved_through_graph(monkeypatch) -> None:
    """P-handoff invariant survives the graph crossing: geometry's caseId equals intake's
    request-derived case id (it flows through the seeded plan), not the AI-FEA-P0-05 stand-in."""
    monkeypatch.setattr("tools.freecad_driver.FREECAD_AVAILABLE", False)
    monkeypatch.setattr(architect_mod, "_extract_structured_data", lambda **kw: None)
    monkeypatch.setattr(settings, "workflow_graph_intake", True)
    run = MockWorkflowStore().run_sync(user_request=_NACA)
    intake_m = next(
        s for s in run.stages if s.stage is WorkflowStage.PROJECT_INTAKE
    ).metrics.model_dump(by_alias=True, exclude_none=True)
    geom_m = _geom(run).metrics.model_dump(by_alias=True, exclude_none=True)
    assert geom_m["caseId"] == intake_m["caseId"]
    assert geom_m["caseId"] != "AI-FEA-P0-05"


# --- fallbacks: non-NACA / FreeCAD-present do not cross via the graph --------


def test_non_naca_falls_back_to_existing_path(monkeypatch) -> None:
    monkeypatch.setattr("tools.freecad_driver.FREECAD_AVAILABLE", False)
    st = run_geometry_via_graph(_BRACKET, run_id="r")
    m = st.metrics.model_dump(by_alias=True, exclude_none=True)
    assert "graphNodeRan" not in m  # bracket stays on the planning stand-in, no graph crossing
    assert "fidelityTier" not in m


def test_freecad_present_falls_back_no_mislabel(monkeypatch) -> None:
    monkeypatch.setattr("tools.freecad_driver.FREECAD_AVAILABLE", True)
    st = run_geometry_via_graph(_NACA, run_id="r")
    m = st.metrics.model_dump(by_alias=True, exclude_none=True)
    assert "graphNodeRan" not in m  # a real kernel must not be mislabeled tier_0 via the graph


# --- safety envelope: no mesh/solver node, no ccx ---------------------------


def test_no_downstream_solver_node_executes(monkeypatch) -> None:
    """The truncated graph stops at geometry — mesh/solver can never run (no gmsh/ccx)."""
    import agents.mesh as mesh
    import agents.solver as solver

    calls: list[str] = []
    monkeypatch.setattr("tools.freecad_driver.FREECAD_AVAILABLE", False)
    monkeypatch.setattr(mesh, "run", lambda s: calls.append("mesh") or {})
    monkeypatch.setattr(solver, "run", lambda s: calls.append("solver") or {})
    monkeypatch.setattr(architect_mod, "_extract_structured_data", lambda **kw: None)

    run_geometry_via_graph(_NACA, run_id="r")
    assert calls == []  # no downstream node executed


def test_graph_runner_still_avoids_agents_graph() -> None:
    """The 2-node builder adds agents.geometry but must STILL never import agents.graph."""
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
    assert "agents.geometry" in imported or "agents" in imported
