# Codex Review — ADR-029 P0: LangGraph compiled-graph runtime drives a live stage (R0 APPROVE)

**Scope (risk-tier: NEW runtime path + agent-layer + cross-≥3-file + new ADR governance record):**
the first time the orphaned `agents/graph.py` machinery touches the backend live runtime (ADR-028
north star, owner-chosen path B). A DEDICATED truncated `START→architect→END` `StateGraph(SimState)`
is compiled and `.invoke()`d to drive PROJECT_INTAKE, flag-gated `workflow_graph_intake=False`.

## Design adjudicated, not guessed (workflow wf_b4b13c99-5ee)

3 lens-diverse proposers (minimal-reversible / north-star-direct / honesty-first) → 3 adversarial
verifiers → synthesizer. The verifiers FALSIFIED three prior assumptions; each was then
independently re-verified by direct inspection before any code:

1. **`ccx` IS present** (`/opt/homebrew/bin/ccx`). "Solver hermetically infeasible" was wrong on
   this host. Honest correction recorded in ADR-029 (prior commits NOT rewritten).
2. **`agents/human_fallback.py` imports `app.well_harness.notion_sync`** → `import agents.graph`
   pulls backend Notion code into the agent-layer closure + the full graph fires a NON-REVERTIBLE
   Notion writeback. `import agents.architect` alone pulls none of it (verified `well_harness` /
   `app` absent from `sys.modules` after importing `agents.graph_runner`).
3. **keyless `architect.run` authors NO plan** → "node ran" ≠ "node authored content".

→ The only safe minimal shape is a dedicated truncated graph built from `agents.architect`, truncated
before geometry/mesh/solver (no ccx, no Notion, no downstream node by construction).

## Honesty contract upheld (machine-pinned)

- **N/13 UNCHANGED:** PROJECT_INTAKE is already `deterministic_agent`; flipping its DRIVER from a
  direct `architect.run` to a truncated `compile().invoke()` keeps provenance. The graph-execution
  fact rides metrics (`graphNodeRan` / `graphNodeProducedPlan` / `graphRunner`) — a contract test
  asserts N/13(flag-on) == N/13(flag-off) for the same request.
- **No 4th provenance value** (the FE `asProvenance()` would downgrade an unknown to scripted_demo
  and DECREASE N/13).
- **Node-ran vs node-authored distinguished:** keyless → `graphNodeProducedPlan=False` + a disclosure
  stating the architect node executed but authored nothing without an LLM key, so the intake text is
  the rule-based `analyze_intake` projection — never a fabricated agentic claim.
- **Reducer-identity seed** (`history=[]`/`retry_budgets={}`) so the keyless architect's history delta
  does not crash the append reducer; `.invoke()` wrapped to degrade gracefully to the deterministic
  intake projection on any runtime error.
- **Claim tier:** Tier 0 (P0 sandbox wiring proof); the full graph caps at Tier 1 (dummy-fidelity);
  never Tier 2.

## ADR-015 intact

`graph_runner.py` (agent layer) imports `agents.architect` + `agents.state_projection` + `schemas.*`
+ `langgraph`; NO backend (`app.*`) import (verified at runtime). The facade `run_node_via_graph`
imports only `agents.graph_runner`, NOT `schemas.sim_state` (the SimState dict is built inside the
runner). `mock_pipeline.py`'s flag-gated branch does a lazy facade import; NO `agents.*` import. The
facade-discipline test (27) passes unchanged.

## R0 — **APPROVE** (gpt-5.5 xhigh, static diff review, no fix rounds)

Verbatim: *"APPROVE."* (no P1/P2/P3 findings).

## Files

- `agents/graph_runner.py` (NEW): `build_intake_graph()` + `run_intake_via_graph(...)`.
- `agents/state_projection.py`: `graph_intake_to_stage_state(...)` (branches on plan-presence; reuses
  the existing intake projectors; stamps graph metrics + dual disclosure; provenance unchanged).
- `backend/app/workbench/agent_facade.py`: `run_node_via_graph(...)` (sole agents.* importer).
- `backend/app/core/config.py`: `workflow_graph_intake: bool = False`.
- `backend/app/services/workflow/mock_pipeline.py`: one flag-gated PROJECT_INTAKE branch.
- `backend/tests/test_graph_intake_wiring.py` (NEW, 9 tests): invoke-spied runtime proof; keyless
  no-plan honesty; plan-present llm_agent; N/13 unchanged; flag-off byte-identical; no downstream
  node; reducer identity; AST-checked no-agents.graph-import.
- `docs/adr/ADR-029-graph-runtime-wiring.md` (NEW, Status: Proposed — pending user ratification).

## Gates

- P0 wiring suite **9 pass**; intake/geomplan/recovery/fidelity/handoff facade regressions **53 pass**;
  ADR-015 facade-discipline **27 pass**; HF1 path guard EXIT=0; full backend **1321 pass / 21 skip /
  1 xfail / 4 fail**. The 4 failures (`test_parsers` NL-intent ×3, `test_compliance`
  knowledge_base_linkage) are PRE-EXISTING + environmental (`code: invalid_api_key`), identical on
  clean HEAD — NOT a P0 regression. P0 added 9 passing tests (1312→1321), zero new failures.

## Open risks (carried — gated to later ADR-029 phases)

- ccx-present (P3 solver isolation gate), Notion side-effect (P4 isolation gate), async `_advance`
  blocking on synchronous `.invoke` (low for 1-node intake; flagged for P5 stream design).
- End-user value of P0 ~zero (PROJECT_INTAKE was already deterministic_agent; only the driver
  changed). Value is architectural. Framed as such; never a coverage or capability claim.

**Closure:** R0 **APPROVE** (no fix rounds). Local commit, `confidence: med`, no push, flag default-off
(inert until ratified + enabled). ADR-029 Status: Proposed — surfaced to the owner for ratification.
