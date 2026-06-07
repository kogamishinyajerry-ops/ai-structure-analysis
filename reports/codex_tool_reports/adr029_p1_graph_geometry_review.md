# Codex Review — ADR-029 P1: 2-node architect→geometry graph drives GEOMETRY_VALIDATION (R0 APPROVE)

**Scope (risk-tier: agent-layer + cross-≥3-file + new runtime path):** extend the dedicated truncated
graph from P0 (architect-only → PROJECT_INTAKE) to `START→architect→geometry→END` driving
GEOMETRY_VALIDATION — the FIRST cross-node graph data dependency (the geometry node consumes the
SimPlan the architect step left in the shared SimState). Flag-gated `workflow_graph_intake=False`
(name retained from P0; now gates intake + geometry).

## Honesty contract upheld (machine-pinned)

- **Cross-node dependency, honestly attributed:** keyless the architect authors no plan and
  `geometry.run` requires one, so a DETERMINISTIC plan (rule-based intake case id + fixed NACA spec)
  is seeded with a `description` SENTINEL. The projector reports `planAuthoredBy=deterministic_seed`
  when the sentinel survives (keyless — architect authored nothing, pass-through) vs `architect_llm`
  when the architect's plan overwrote it (the genuine architect→geometry authorship dependency).
  Sentinel detection is runtime-accurate and needs NO backend/env import (ADR-015).
- **tier_0_dummy pins carried from P-geomrun:** NO measurement key surfaced
  (watertight/manifold/volume/minFeatureSizeM/boundingBoxMm/valid); `cadKernelRan`/`defectCheckRun`
  pinned False; disclosure states the 10-byte placeholder STEP (ADR-008 N-3), the tautological
  `valid=True`, and `未验证`. `toolRan` enforced (refuses to build a SUCCESS stage without the
  `geometry_path` wiring fact).
- **N/13 UNCHANGED:** the geometry graph stage stays `deterministic_agent` (same as the flag-off
  P-geomrun path); the graph facts ride metrics (`graphNodeRan`/`graphRunner`/`planAuthoredBy`), NOT
  provenance; no 4th provenance value. A contract test asserts N/13(flag-on)==N/13(flag-off)==6.
- **P-handoff invariant preserved through the graph:** geometry's `caseId` equals intake's
  request-derived case id (it flows through the seeded plan), not the `AI-FEA-P0-05` stand-in.
- **Claim tier:** Tier 0 (dummy-fidelity); never Tier 2.

## Safety envelope (verified)

- graph_runner builds its own graph from `agents.architect` + `agents.geometry` directly, NEVER
  `agents.graph` (AST-checked in test). Importing `agents.graph_runner` keeps `well_harness`/`app`
  OUT of the agent-layer import closure (re-verified at runtime even with `agents.geometry` added).
- Truncated BEFORE mesh/solver → no gmsh/ccx subprocess, no human_fallback/Notion node reachable
  (spy test asserts mesh/solver never run).
- Non-NACA family AND any FreeCAD-present host fall back to the existing `geometry_stage_state`
  (no graph crossing, no tier_0 mislabel). `.invoke()` wrapped to degrade gracefully on any error.
- ADR-015: facade `run_node_via_graph` imports only `agents.graph_runner` (never `schemas.sim_state`);
  mock_pipeline's flag branch does a lazy facade import (no `agents.*`). Facade-discipline test (27)
  passes unchanged.

## R0 — **APPROVE** (gpt-5.5 xhigh, static diff review, no fix rounds)

Verbatim: *"APPROVE."* (no P1/P2/P3 findings).

## Files

- `agents/state_projection.py`: `graph_geometry_to_stage_state(final_sim_state, ..., plan_authored_by)`
  — projects the graph's final state (geometry already ran inside the graph; NOT re-run), tier_0_dummy
  pins + cross-node/authorship disclosure.
- `agents/graph_runner.py`: `build_intake_geometry_graph()` (START→architect→geometry→END) +
  `run_geometry_via_graph(...)` (NACA+not-FREECAD gate; seed deterministic plan w/ sentinel;
  graceful fallback to `geometry_stage_state`).
- `backend/app/workbench/agent_facade.py`: `run_node_via_graph` handles GEOMETRY_VALIDATION.
- `backend/app/services/workflow/mock_pipeline.py`: flag branch extended to GEOMETRY_VALIDATION.
- `backend/app/core/config.py`: flag docstring updated (now gates intake + geometry).
- `backend/tests/test_graph_geometry_wiring.py` (NEW, 9 tests): invoke-spied 2-node runtime;
  keyless→deterministic_seed honesty; architect-authored plan flows architect→geometry; N/13
  unchanged; P-handoff caseId preserved through the graph; non-NACA + FreeCAD-present fallbacks;
  no downstream mesh/solver; AST no-agents.graph-import.

## Gates

- P1 geometry 9 pass; P0 intake 9; flag-off regressions (fidelity/handoff/geomplan/intake/recovery)
  71 pass total; ADR-015 facade-discipline 27 pass; HF1 path guard EXIT=0; import-closure verified
  backend-free. Full backend suite: pending green (the 4 pre-existing `invalid_api_key`
  NL-parser/compliance failures excluded as environmental, identical on clean HEAD).

## Open risks (carried — gated to later ADR-029 phases)

- P2 mesh tier_0_dummy + dummyFidelityInputs guard; P3 SOLVER ISOLATION GATE (ccx present); P4
  NOTION ISOLATION GATE (human_fallback side-effect); P5 stream()-driven full graph + run-level
  graphDriven qualifier. The deterministic-seed dependency keyless is honest but the LLM-authored
  cross-node flow only runs with a key (exercised in tests via a mocked architect).

**Closure:** R0 **APPROVE** (no fix rounds). Local commit, `confidence: med`, no push, flag default-off.
