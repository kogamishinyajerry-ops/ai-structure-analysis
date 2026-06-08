"""ADR-029 P2 — the 3-node architect→geometry→mesh graph drives MESH_GENERATION.

P1 added the first cross-node EDGE (architect→geometry). P2 adds the second: a truncated
architect→geometry→mesh graph whose mesh node CONSUMES the ``geometry_path`` the geometry node
left in the shared SimState, then runs the REAL ``generate_mesh`` + ``check_mesh_quality`` code.
Still truncated before the solver (no ccx, no human_fallback/Notion node), flag-gated
``workflow_graph_intake`` (default off).

THE HONESTY ENVELOPE these tests pin:

* the 3-node COMPILED GRAPH RUNTIME ran (invoke-spied), not a direct node.run;
* the mesh crossing is ``tier_0_dummy`` with the NEW ``dummyFidelityInputs=True`` guard:
  ``check_mesh_quality`` IS a real numpy measurement, but over a hardcoded 4-node/1-tet C3D4
  *fallback* mesh of dummy geometry — so NO measurement-shaped key is surfaced (anti-vacuous-
  pass), ``meshKernelRan=False``, and the disclosure says all of it;
* "who authored the consumed plan" is disclosed (seed vs architect_llm), exactly as P1;
* provenance stays ``deterministic_agent`` (no 4th value) — but a REAL node now drives the
  stage, so N/13 rises by exactly 1 (scripted_demo → deterministic_agent at dummy fidelity);
* the no-mislabel guards hold: a real gmsh kernel, a real FreeCAD kernel, or a non-NACA family
  all fall back to the scripted mesh spec (NO graph crossing, NO tier_0 mislabel of a real mesh);
* NO downstream solver node executes — no ccx subprocess.
"""

from __future__ import annotations

from app.core.config import settings
from app.services.workflow.mock_pipeline import MockWorkflowStore

import agents.architect as architect_mod
import agents.graph_runner as gr
from agents.graph_runner import run_mesh_via_graph
from schemas.sim_plan import GeometrySpec, SimPlan
from schemas.workflow_state import StageProvenance, WorkflowStage

_NACA = "分析这个机翼 NACA0012 的结构强度"
_BRACKET = "对支架做静力分析，关注应力与位移"
# measurement-shaped mesh keys a tier_0_dummy producer MUST suppress (anti-vacuous-pass): a
# unit-tet fallback mesh trivially passes, so surfacing these would read as a measured validation.
_MESH_MEASUREMENT_KEYS = (
    "minScaledJacobian",
    "min_scaled_jacobian",
    "maxAspectRatio",
    "max_aspect_ratio",
    "badElements",
    "badElementCount",
    "nodes",
    "elements",
    "degeneratePct",
)


def _triple_dummy(monkeypatch) -> None:
    """Force the only honest tier_0 mesh-crossing regime: NACA + no FreeCAD + no gmsh, so the
    test is independent of whether the host/CI has a real FreeCAD or gmsh kernel installed."""
    monkeypatch.setattr("tools.freecad_driver.FREECAD_AVAILABLE", False)
    monkeypatch.setattr("tools.gmsh_driver.GMSH_AVAILABLE", False)


def _agent_driven(run) -> int:
    return sum(1 for s in run.stages if s.provenance is not StageProvenance.SCRIPTED_DEMO)


def _mesh(run):
    return next(s for s in run.stages if s.stage is WorkflowStage.MESH_GENERATION)


# --- the 3-node compiled-graph runtime ran (second cross-node edge) ----------


def test_run_mesh_via_graph_invokes_3node_graph(monkeypatch) -> None:
    """Spy the compiled 3-node graph's .invoke so the test proves the GRAPH RUNTIME drove the
    mesh stage (architect→geometry→mesh), not a direct mesh.run."""
    _triple_dummy(monkeypatch)
    monkeypatch.setattr(architect_mod, "_extract_structured_data", lambda **kw: None)
    real_build = gr.build_intake_geometry_mesh_graph
    seen: dict = {}

    class _SpyGraph:
        def __init__(self, real):
            self._real = real

        def invoke(self, state, *a, **k):
            seen["invoked"] = True
            return self._real.invoke(state, *a, **k)

    monkeypatch.setattr(gr, "build_intake_geometry_mesh_graph", lambda: _SpyGraph(real_build()))
    st = run_mesh_via_graph(_NACA, run_id="r")

    assert seen.get("invoked") is True  # the 3-node compiled-graph runtime ran
    assert st.stage is WorkflowStage.MESH_GENERATION


# --- tier_0_dummy + the dummyFidelityInputs guard (the P2 deliverable) -------


def test_keyless_mesh_is_tier0_dummy_with_guard(monkeypatch) -> None:
    """Keyless: a deterministic NACA plan is seeded; the mesh node runs the real
    generate_mesh+check_mesh_quality over a DUMMY fallback mesh → tier_0_dummy with
    dummyFidelityInputs=True, meshKernelRan=False, NO measurement key, provenance unchanged."""
    _triple_dummy(monkeypatch)
    monkeypatch.setattr(architect_mod, "_extract_structured_data", lambda **kw: None)
    st = run_mesh_via_graph(_NACA, run_id="r")
    m = st.metrics.model_dump(by_alias=True, exclude_none=True)

    assert st.provenance is StageProvenance.DETERMINISTIC_AGENT  # NOT a provenance flip
    assert m["graphNodeRan"] is True
    assert m["graphRunner"] == "langgraph-architect-geometry-mesh"
    assert m["planAuthoredBy"] == "deterministic_seed"
    assert m["fidelityTier"] == "tier_0_dummy"
    assert m["meshKernelRan"] is False
    assert m["dummyFidelityInputs"] is True  # the P2 load-bearing guard
    assert m["fidelity"]["dataReal"] is False
    for k in _MESH_MEASUREMENT_KEYS:
        assert k not in m  # anti-vacuous-pass: no real-but-tautological mesh metric surfaced
    expl = st.agent_explanation or ""
    assert "跨节点" in expl  # second cross-node dependency disclosed
    assert "fallback" in expl  # the dummy fallback mesh is named
    assert "tautological" in expl and "未验证任何真实网格" in expl  # honesty pins carried
    # next_action points to the genuine next stage (mesh quality check), NOT geometry-planning's
    # "进入材料赋予" — reusing analyze_geometry_plan's next_action would misdirect past the gate.
    assert "网格质量检查" in (st.next_action or "")
    assert "材料赋予" not in (st.next_action or "")


def test_architect_authored_plan_flows_to_mesh(monkeypatch) -> None:
    """When the LLM architect node authors a plan, THAT plan flows architect→geometry→mesh —
    the genuine cross-node authorship dependency. planAuthoredBy flips to architect_llm and the
    mesh stage still rides tier_0_dummy + the dummyFidelityInputs guard (dummy fallback mesh)."""
    _triple_dummy(monkeypatch)
    authored = SimPlan(
        case_id="AI-FEA-P0-77",
        geometry=GeometrySpec(kind="naca", parameters={"profile": "NACA0012"}),
    )
    monkeypatch.setattr(architect_mod, "_extract_structured_data", lambda **kw: authored)
    st = run_mesh_via_graph(_NACA, run_id="r", existing_case_id="AI-FEA-P0-77")
    m = st.metrics.model_dump(by_alias=True, exclude_none=True)

    assert m["planAuthoredBy"] == "architect_llm"  # architect authored, not the seed
    assert m["caseId"] == "AI-FEA-P0-77"  # the architect plan's case id reached mesh
    assert m["fidelityTier"] == "tier_0_dummy"
    assert m["dummyFidelityInputs"] is True
    assert st.provenance is StageProvenance.DETERMINISTIC_AGENT
    assert "architect→geometry→mesh 作者依赖" in (st.agent_explanation or "")


# --- wiring is honest coverage: N/13 rises by EXACTLY 1 ----------------------


def test_n13_rises_by_one_mesh_graph(monkeypatch) -> None:
    """Unlike P1 (geometry was already counted → N unchanged), P2 wires a stage that WAS
    scripted: mesh_generation flips scripted_demo → deterministic_agent, so N/13 rises by
    exactly 1 — honest architecture progress at dummy fidelity, NOT a validation."""
    _triple_dummy(monkeypatch)
    monkeypatch.setattr(architect_mod, "_extract_structured_data", lambda **kw: None)
    off = MockWorkflowStore().run_sync(user_request=_NACA)
    monkeypatch.setattr(settings, "workflow_graph_intake", True)
    on = MockWorkflowStore().run_sync(user_request=_NACA)

    assert _agent_driven(on) == _agent_driven(off) + 1  # exactly one honest increment
    assert _mesh(off).provenance is StageProvenance.SCRIPTED_DEMO  # scripted off-flag
    assert _mesh(on).provenance is StageProvenance.DETERMINISTIC_AGENT  # real node on-flag
    off_m = _mesh(off).metrics.model_dump(by_alias=True, exclude_none=True)
    on_m = _mesh(on).metrics.model_dump(by_alias=True, exclude_none=True)
    assert "graphNodeRan" not in off_m  # the scripted spec carries no graph fact
    assert on_m["graphNodeRan"] is True
    assert on_m["dummyFidelityInputs"] is True
    assert on_m["fidelityTier"] == "tier_0_dummy"  # the increment is DUMMY fidelity


def test_mesh_case_id_handoff_preserved_through_graph(monkeypatch) -> None:
    """P-handoff invariant survives the second crossing: mesh's caseId equals intake's
    request-derived case id (it flows intake→geometry→mesh through the seeded plan)."""
    _triple_dummy(monkeypatch)
    monkeypatch.setattr(architect_mod, "_extract_structured_data", lambda **kw: None)
    monkeypatch.setattr(settings, "workflow_graph_intake", True)
    run = MockWorkflowStore().run_sync(user_request=_NACA)
    intake_m = next(
        s for s in run.stages if s.stage is WorkflowStage.PROJECT_INTAKE
    ).metrics.model_dump(by_alias=True, exclude_none=True)
    mesh_m = _mesh(run).metrics.model_dump(by_alias=True, exclude_none=True)
    assert mesh_m["caseId"] == intake_m["caseId"]
    assert mesh_m["caseId"] != "AI-FEA-P0-05"


# --- no-mislabel guards: a real kernel / non-NACA never crosses via the graph -


def test_gmsh_present_falls_back_no_mislabel(monkeypatch) -> None:
    """A real gmsh kernel would mesh into a REAL mesh; run_mesh_via_graph must REFUSE to project
    it tier_0 — it raises NotImplementedError so the caller uses the scripted mesh spec."""
    monkeypatch.setattr("tools.freecad_driver.FREECAD_AVAILABLE", False)
    monkeypatch.setattr("tools.gmsh_driver.GMSH_AVAILABLE", True)
    try:
        run_mesh_via_graph(_NACA, run_id="r")
        raise AssertionError("expected NotImplementedError when a real gmsh kernel is present")
    except NotImplementedError:
        pass


def test_freecad_present_falls_back_no_mislabel(monkeypatch) -> None:
    """A real FreeCAD kernel would yield real geometry; the mesh crossing must refuse."""
    monkeypatch.setattr("tools.freecad_driver.FREECAD_AVAILABLE", True)
    monkeypatch.setattr("tools.gmsh_driver.GMSH_AVAILABLE", False)
    try:
        run_mesh_via_graph(_NACA, run_id="r")
        raise AssertionError("expected NotImplementedError when a real FreeCAD kernel is present")
    except NotImplementedError:
        pass


def test_non_naca_falls_back_no_mislabel(monkeypatch) -> None:
    """A non-NACA family has no dummy mesh path; the crossing must refuse (→ scripted)."""
    _triple_dummy(monkeypatch)
    try:
        run_mesh_via_graph(_BRACKET, run_id="r")
        raise AssertionError("expected NotImplementedError for a non-NACA family")
    except NotImplementedError:
        pass


def test_bracket_flag_on_mesh_stays_scripted(monkeypatch) -> None:
    """End-to-end: with the flag on, a bracket run's mesh stage stays scripted_demo (the graph
    crossing refused and the pipeline fell through to the scripted spec)."""
    _triple_dummy(monkeypatch)
    monkeypatch.setattr(settings, "workflow_graph_intake", True)
    run = MockWorkflowStore().run_sync(user_request=_BRACKET)
    assert _mesh(run).provenance is StageProvenance.SCRIPTED_DEMO
    assert "graphNodeRan" not in _mesh(run).metrics.model_dump(by_alias=True, exclude_none=True)


# --- safety envelope: no solver node, still no agents.graph import -----------


def test_no_downstream_solver_node_executes(monkeypatch) -> None:
    """The truncated graph stops at mesh — the solver node can never run (no ccx subprocess)."""
    import agents.solver as solver

    calls: list[str] = []
    _triple_dummy(monkeypatch)
    monkeypatch.setattr(solver, "run", lambda s: calls.append("solver") or {})
    monkeypatch.setattr(architect_mod, "_extract_structured_data", lambda **kw: None)

    run_mesh_via_graph(_NACA, run_id="r")
    assert calls == []  # no solver node executed


def test_graph_runner_still_avoids_agents_graph() -> None:
    """The 3-node builder adds agents.mesh but must STILL never import agents.graph (ADR-015)."""
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
    assert "agents.mesh" in imported or "agents" in imported
