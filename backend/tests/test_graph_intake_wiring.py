"""ADR-029 P0 — the LangGraph compiled-graph RUNTIME drives one live stage.

Every ADR-028 slice so far drove a stage by calling an agent node's ``run()`` DIRECTLY
through the facade; NONE exercised the actual LangGraph compiled-graph runtime. P0 closes
that gap minimally: a dedicated truncated ``START -> architect -> END`` graph is compiled and
``.invoke()``d to drive PROJECT_INTAKE, flag-gated (``workflow_graph_intake``, default off).

These tests pin the honesty floor + safety envelope:

* the COMPILED GRAPH RUNTIME ran (``.invoke``), not a direct ``architect.run`` (defeats the
  vacuous-pass trap — proving wiring, not a mocked shortcut);
* "node ran" vs "node authored content" are DISTINCT: keyless the architect authors no
  SimPlan, so ``graphNodeProducedPlan`` is False and the disclosure says the intake text is
  rule-based — never a fabricated agentic claim;
* the runtime swap does NOT change provenance or the N/13 agent-driven count (wiring is not
  coverage inflation);
* NO downstream node executes (no FreeCAD/gmsh/ccx subprocess, no Notion side-effect) —
  guaranteed by construction (the truncated graph has only the architect node);
* the reducer-managed SimState fields are seeded with their identity values (``[]`` / ``{}``),
  not ``None`` (the keyless architect returns a ``history`` delta that the append reducer
  would crash on).
"""

from __future__ import annotations

from app.core.config import settings
from app.services.workflow.mock_pipeline import MockWorkflowStore

import agents.architect as architect_mod
import agents.graph_runner as gr
from agents.graph_runner import run_intake_via_graph
from schemas.workflow_state import StageProvenance, WorkflowStage

_NACA = "分析这个机翼 NACA0012 的结构强度"


def _agent_driven(run) -> int:
    return sum(1 for s in run.stages if s.provenance is not StageProvenance.SCRIPTED_DEMO)


def _intake(run):
    return next(s for s in run.stages if s.stage is WorkflowStage.PROJECT_INTAKE)


# --- the compiled-graph RUNTIME actually ran (not a direct architect.run) ----


def test_run_intake_via_graph_invokes_compiled_graph(monkeypatch) -> None:
    """Spy the compiled graph's .invoke so the test proves the GRAPH RUNTIME drove the
    stage — not a direct architect.run() that merely stamps the metric (the vacuous-pass
    trap the design must defeat)."""
    real_build = gr.build_intake_graph
    seen: dict = {}

    class _SpyGraph:
        def __init__(self, real):
            self._real = real

        def invoke(self, state, *a, **k):
            seen["invoked"] = True
            seen["seed"] = state
            return self._real.invoke(state, *a, **k)

    monkeypatch.setattr(gr, "build_intake_graph", lambda: _SpyGraph(real_build()))
    st = run_intake_via_graph(_NACA, run_id="r")

    assert seen.get("invoked") is True  # the compiled-graph runtime ran
    # the reducer-identity seed was used (not None) — the keyless architect's history delta
    # would crash the append reducer otherwise
    assert seen["seed"]["history"] == []
    assert seen["seed"]["retry_budgets"] == {}
    assert st.stage is WorkflowStage.PROJECT_INTAKE


def test_seed_uses_reducer_identity_not_none() -> None:
    seed = gr._seed_state(_NACA, "r", None)
    assert seed["history"] == []  # append_history reducer identity
    assert seed["retry_budgets"] == {}  # update_retry_budget reducer identity
    assert seed["artifacts"] == []


# --- node-ran vs node-authored-content are distinct (the honesty line) -------


def test_keyless_architect_yields_no_plan_path(monkeypatch) -> None:
    """Force the keyless-equivalent path deterministically (architect authors NO plan).
    Monkeypatching the extractor to return None forces the no-plan branch WITHOUT faking a
    plan — the real graph still runs the real architect node, which now returns
    fault_class=unknown with no SimPlan. Assert the honest no-content disclosure."""
    monkeypatch.setattr(architect_mod, "_extract_structured_data", lambda **kw: None)
    st = run_intake_via_graph(_NACA, run_id="r")
    m = st.metrics.model_dump(by_alias=True, exclude_none=True)

    assert m["graphNodeRan"] is True
    assert m["graphNodeProducedPlan"] is False
    assert m["graphRunner"] == "langgraph-truncated-architect"
    assert st.provenance is StageProvenance.DETERMINISTIC_AGENT  # NOT a provenance flip
    expl = st.agent_explanation or ""
    assert "compiled graph .invoke" in expl  # discloses the runtime executed
    assert "未产出 SimPlan" in expl  # discloses the node authored nothing keyless
    assert "analyze_intake" in expl  # discloses the intake text is rule-based, not the node


def test_plan_present_path_is_llm_agent(monkeypatch) -> None:
    """When the architect node DOES author a SimPlan (LLM key opted in, simulated), the
    projection reuses the llm_agent intake projection and discloses node-authored content."""
    from schemas.sim_plan import GeometrySpec, SimPlan

    plan = SimPlan(
        case_id="AI-FEA-P0-12",
        geometry=GeometrySpec(kind="naca", parameters={"profile": "NACA0012"}),
    )
    monkeypatch.setattr(architect_mod, "_extract_structured_data", lambda **kw: plan)
    st = run_intake_via_graph(_NACA, run_id="r", existing_case_id="AI-FEA-P0-12")
    m = st.metrics.model_dump(by_alias=True, exclude_none=True)

    assert m["graphNodeRan"] is True
    assert m["graphNodeProducedPlan"] is True
    assert st.provenance is StageProvenance.LLM_AGENT
    assert "产出 SimPlan" in (st.agent_explanation or "")


def test_intake_stage_shape_parity(monkeypatch) -> None:
    """The graph-driven PROJECT_INTAKE keeps the wire shape of the direct path: same stage,
    deterministic_agent provenance, the deterministic _canonical_case_id, non-empty
    disclosure, and the graph-runtime fact in metrics."""
    monkeypatch.setattr(architect_mod, "_extract_structured_data", lambda **kw: None)
    st = run_intake_via_graph(_NACA, run_id="r")
    m = st.metrics.model_dump(by_alias=True, exclude_none=True)

    assert st.stage is WorkflowStage.PROJECT_INTAKE
    assert st.provenance is StageProvenance.DETERMINISTIC_AGENT
    assert m["caseId"].startswith("AI-FEA-P")  # naming-compliant deterministic case id
    assert m["graphNodeRan"] is True
    assert st.agent_explanation  # non-empty disclosure


# --- wiring is NOT coverage inflation: N/13 identical flag on vs off ----------


def test_n13_unchanged_with_flag(monkeypatch) -> None:
    monkeypatch.setattr(architect_mod, "_extract_structured_data", lambda **kw: None)
    off = MockWorkflowStore().run_sync(user_request=_NACA)
    monkeypatch.setattr(settings, "workflow_graph_intake", True)
    on = MockWorkflowStore().run_sync(user_request=_NACA)

    assert _agent_driven(off) == _agent_driven(on)  # wiring != coverage inflation
    assert _intake(off).provenance is StageProvenance.DETERMINISTIC_AGENT
    assert _intake(on).provenance is StageProvenance.DETERMINISTIC_AGENT
    # flag-on intake carries the graph-runtime fact; flag-off does not
    assert "graphNodeRan" not in _intake(off).metrics.model_dump(by_alias=True, exclude_none=True)
    assert _intake(on).metrics.model_dump(by_alias=True, exclude_none=True)["graphNodeRan"] is True


def test_flag_off_is_default_and_byte_identical(monkeypatch) -> None:
    """The flag defaults off, so the live pipeline is byte-identical to the pre-P0 path
    (the graph branch is dead) — intake carries no graph metric."""
    assert settings.workflow_graph_intake is False
    run = MockWorkflowStore().run_sync(user_request=_NACA)
    im = _intake(run).metrics.model_dump(by_alias=True, exclude_none=True)
    assert "graphNodeRan" not in im


# --- safety envelope: no downstream node, no ccx, no Notion ------------------


def test_no_downstream_node_executes(monkeypatch) -> None:
    """The truncated graph has ONLY the architect node, so geometry/mesh/solver can never
    run — no FreeCAD/gmsh/ccx subprocess, no Notion side-effect. Spy them to prove it."""
    import agents.geometry as geom
    import agents.mesh as mesh
    import agents.solver as solver

    calls: list[str] = []
    monkeypatch.setattr(geom, "run", lambda s: calls.append("geometry") or {})
    monkeypatch.setattr(mesh, "run", lambda s: calls.append("mesh") or {})
    monkeypatch.setattr(solver, "run", lambda s: calls.append("solver") or {})
    monkeypatch.setattr(architect_mod, "_extract_structured_data", lambda **kw: None)

    run_intake_via_graph(_NACA, run_id="r")
    assert calls == []  # no downstream node executed


def test_graph_runner_does_not_import_agents_graph() -> None:
    """ADR-029 safety pin: graph_runner builds its own truncated graph from agents.architect
    and must NOT import agents.graph (whose closure pulls app.well_harness.notion_sync, i.e.
    a real non-revertible Notion side-effect, into the agent layer). Checked via AST imports
    (not source text) so the docstring may freely EXPLAIN why agents.graph is avoided."""
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

    pulls_full_graph = any(
        m == "agents.graph" or m.startswith("agents.graph.") for m in imported
    )
    assert not pulls_full_graph, (
        f"graph_runner must not import agents.graph (the full graph pulls notion_sync); "
        f"imports={imported}"
    )
    # it DOES build its own graph from agents.architect directly:
    assert "agents.architect" in imported or "agents" in imported
