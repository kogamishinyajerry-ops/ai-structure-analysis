# Codex Review — ADR-028 P3 router node behind the facade (R0 → R1 APPROVE)

**Scope (core honesty surface, NOT HF1):** wire the real router node
(`agents.router.route_reviewer`) behind the workbench facade so the reviewer gate's
"next step" is a genuine division-of-labor decision instead of a hardcoded string. The
HF1-protected `agents/router.py` is **called, never edited**, so no HF1 override applies.

## Files

- `agents/state_projection.py` — `RouteOutcome` + `decide_route(verdict, fault_class,
  retry_budgets, verdict_source)`: builds a router input and runs the **real**
  `route_reviewer` (ADR-004 `FAULT_TO_NODE` + 3-retry cap); returns the chosen node + an
  honest explanation; `provenance=deterministic_agent`. Lives in the agent layer so the
  `FaultClass` enum conversion stays out of the workbench package (ADR-015 rule 3).
- `backend/app/workbench/agent_facade.py` — `decide_route(...)` thin wrapper taking a
  **plain** `fault_class` wire string; the only `agents.*` importer; no `schemas.sim_state`.
- `backend/app/services/workflow/mock_pipeline.py` — at RESULT_ANALYSIS, on the mock-demo
  happy path only (`error is None AND specs is STAGE_SPECS AND solve_ctx is None AND status
  in {SUCCESS,WARNING}`), the hardcoded `next_action` is replaced by the real routing
  decision + a `routedTo` metric, and that ONE stage's provenance flips to
  `deterministic_agent`. Every other stage stays `scripted_demo` (ADR-028 D2).
- `backend/tests/test_agent_facade_routing.py` — **new**, 14 tests: every router branch
  (accept→viz, re-run within budget→node, retry cap→human_fallback, reference→architect,
  needs-review→human_fallback), explanation transparency, enum input, and the live pipeline
  positive + 3 negatives (failure injection, real-LE10 specs, real solve_ctx all stay scripted).
- `backend/tests/test_agent_facade_intake.py` — the "all other stages scripted" assertion
  updated to the new honest reality: intake + routing are the two agent-driven stages.

## Review tooling note (honest)

`codex-review-relay --uncommitted` was NOT used (it ran away 3× earlier this milestone). The
review was run **contained**: the exact staged diff + a honesty-focused checklist were fed
directly to the same xhigh model (`codex-relay-with gpt-5.5`, 86gs) with an explicit
"review ONLY this diff" directive. Same governance model, minus the runaway repo-walk.

## R0 — CHANGES_REQUIRED (2 findings)

- **P1 (claimed blocking) — FALSE POSITIVE, rejected with evidence.** Codex inferred that
  passing Title-Case `"Accept"`/`"Accept with Note"` would route to `human_fallback` (it
  assumed `route_reviewer` needs lowercase tokens, having been told not to read `router.py`).
  Ground truth: `router._normalize_verdict` does `.strip().lower()...` → `"Accept"` → `"accept"`
  → `route_reviewer` returns `"viz"`; and the **real** `reviewer.py` emits Title-Case
  (`VERDICT_ACCEPT="Accept"`, `VERDICT_ACCEPT_WITH_NOTE="Accept with Note"`), so the demo
  tokens are *faithful* to the real reviewer's output. Proven by passing tests
  (`test_accept_routes_to_viz`, `test_accept_with_note_routes_to_viz`, and the pipeline test
  asserting `routedTo=="viz"`). No code change. (R1 confirmed the rejection given the cited
  normalization.)
- **P2 (valid) — fixed verbatim.** The demo `decide_route` call left `verdict_source` generic,
  so the `deterministic_agent` provenance risked being misread as "the result was computed by
  an agent." Fix: pass `verdict_source="本阶段 demo 评审状态（脚本化，非 agent 计算）"`, so the
  explanation states the verdict is scripted demo state and **only the routing** is
  agent-authored. Pinned by `assert "脚本化" in result.agent_explanation`.

## R1 — **APPROVE** (no remaining findings)

Verbatim: *"R0 P1 is resolved: given the provided `_normalize_verdict`, `Accept` and `Accept
with Note` normalize to `accept`, so routing to `viz` is faithful to the real reviewer output.
R0 P2 is resolved: the demo verdict source now explicitly says it is scripted and
non-agent-computed... The original honesty checklist is satisfied. VERDICT: APPROVE."*

## Honest coverage delta (D2)

Default no-request demo run: **0/13 → 1/13** agent-driven (the routing decision genuinely runs
every run). A run WITH a user request: **1/13 → 2/13** (intake + routing). Downstream
geometry/mesh/solver/viz remain `scripted_demo` (they need FreeCAD/gmsh/ccx + prior-stage
artifacts — out of hermetic-CI scope, deferred). The demo happy path only exercises accept→viz;
the re-run / human_fallback branches are real code, proven by unit tests not the canned demo.

## Gates

- routing + intake + pipeline + le10 + ADR-015 facade-discipline → all pass (36 + 40).
- Full root suite `pytest tests/` → **2680 passed, 6 skipped**.
- Full backend suite → **1231 passed, 26 skipped, 1 xfailed** (minus 3–4 pre-existing
  local-only `openai/httpx` `proxies` collection errors in untouched files: test_report /
  test_solver / test_api).
- `ruff check agents` clean; new test file ruff+format clean.

**Closure:** R0 CHANGES_REQUIRED → P1 rejected-with-evidence + P2 fixed-verbatim → **R1 APPROVE**.
