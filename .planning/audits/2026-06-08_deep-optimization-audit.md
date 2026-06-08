# Deep-optimization audit — 2026-06-08

> Multi-agent discovery audit (ultracode-authorized). Workflow `wf_43bd4454-2aa`: 5 read-only
> lenses (honesty/tier · wiring/dead-code · test-gaps · code↔doc drift · ADR-029 roadmap) →
> adversarial refute-by-default verifier per finding → synthesis. 26 agents, ~2.4M tokens,
> 13 findings survived verification. Each finding below was independently ground-truthed by the
> main session before any action (the workflow is a funnel, not the final word).

## Acted on this session (2 commits)

- **Rank 1 (P1, test_gap) — DONE** (`18c941e`): the ADR-028/029 honesty-seam suite (graph-wiring +
  fidelity-discriminator, the tier_0_dummy / dummyFidelityInputs / anti-vacuous-pass /
  FAILED-not-SUCCESS-solver guards) had ZERO CI protection — `testpaths=["tests"]` + `pytest tests/`
  exclude `backend/tests/`. Wired the **named honesty-seam subset** into the existing required
  `lint-and-test` job. **Ground-truth correction:** the audit said "gate the whole `backend/tests/`
  dir / 65 pass" — WRONG; the full dir has 11 pre-existing API/NL-parser/KB failures (1378 pass / 11
  fail), so the whole dir would make `main` red. Scoped to the 5 green honesty-seam files. HF1.9
  override (mirrors FM-04a frontend-gate precedent). Codex R0 APPROVE.
- **Rank 2 (P2, doc_drift) — DONE** (`3776b87`): `ADR-029:161` still claimed the dummy-deck error is
  "classified solver_convergence ONLY via the returncode!=0 catch-all" — the OR-1 sweep (`4aa0569`)
  missed it because a markdown backtick broke the exact-phrase grep. Now solver_syntax → SOLVER_ERROR.
- **Rank 8 (P3, doc_drift) — DONE** (`3776b87`): `agent_facade.py` stale **module** docstring (the
  function docstrings were already accurate). Now reflects run_node + run_node_via_graph wiring.
- **Rank 10 (P3, test_gap) — DONE** (`3776b87`): `test_graph_solver_wiring.py:329` `<=` → `==` to pin
  the documented net-ZERO coverage invariant.

## Owner decision → ADOPTED + DONE

- **Rank 3 (P2, honesty) — DONE** (owner chose "adopt"): the three tier_0_dummy "ran-clean"
  projectors (`geometry_dummy_exec_to_stage_state` [default path], `graph_geometry_to_stage_state`,
  `graph_mesh_to_stage_state`) now project `StageStatus.WARNING` ("passing-with-caveats") instead of
  green `SUCCESS`, via a new documented helper `_tier0_dummy_status()` (terminal SUCCESS→WARNING; any
  other status passes through). The real-geometry PLANNER path stays SUCCESS; the solver crossing
  stays hard-FAILED (it actually errors). **Blast-radius was an OVERESTIMATE** — the safe-refactor
  enumeration found NO test asserts these projectors' status (the honesty-seam tests assert
  provenance/tier/disclosure/N13, not the badge); the only SUCCESS asserts were intake + a bracket
  provenance test, both unaffected. Frontend already renders `warning` (mock_pipeline emits it for the
  demo `_WARNING_STAGES`), so no frontend change. Full backend suite identical to baseline (11 fail /
  1378 pass — the 11 are the pre-existing out-of-scope failures), root tests/ 2704 pass, +3 regression
  pins added. Codex gpt-5.5 diff-only R0 APPROVE (no findings). The honesty nuance still ALSO rides
  tier_0_dummy + disclosure + suppressed measurement keys; this makes the badge consistent with them.

## Deferred (real but non-surgical / lower value)

- **Rank 4 (P2, roadmap):** P4 = TWO distinct concerns — (P4a) `agents/human_fallback.py:6`
  unconditionally imports `app.well_harness.notion_sync` (also an ADR-015 agent-layer purity break) +
  `create_standalone_task` writeback (lines 25/29/51/54, no-op keyless but a configured host writes
  non-revertibly) → inject inert registrar / settings flag through the facade seam; (P4b) `interrupt()`
  (line 61) needs a LangGraph checkpointer instantiated NOWHERE outside tests → SqliteSaver in a
  dedicated runner, prove interrupt→Command(resume=...) round-trips. Resolve **Open-Q2**
  (replace-vs-parallel default) before starting.
- **Rank 5/11 (P2/P3, roadmap/deadcode):** the full 7-node `compile_graph()`/`build_graph()` is 100%
  orphaned (ZERO production callers); each phase builds a separate truncated StateGraph; `viz.run` +
  `human_fallback.run` are dead at runtime (2/7 nodes execute only in tests). ADR-028's "real compiled
  graph drives the live pipeline" is NOT met by the actual 7-node graph yet. Record as known-orphaned
  in ADR-029 status so it is never read as live 7-node coverage. P5 is multi-slice, NOT a thin P3 step.
- **Rank 6 (P2, test_gap):** the real ccx-subprocess solver leg (the headline P3 claim) is never
  exercised in CI — all 12 solver-driving tests use a fake; the one real test is skipif-ccx AND in the
  (now partially-gated) backend/tests/. Once a ccx-equipped CI job runs the graph-solver file, the
  terminal ccx-launch + rc=201 leg gets covered. Bounded: wiring/edges/projection/halt ARE covered.
- **Rank 7 (P3, wiring):** `aeron/drivers/calculix_backend.py:88` imports `agents.solver._render_inp_deck`
  — the only agents.* import outside the facade, reaching a PRIVATE helper of the high layer from a low
  driver; the ADR-015 test scans only `backend/app/workbench/`, so it is silently un-guarded. Either
  move `_render_inp_deck` to a shared lower module, or sanction it as a carve-out in ADR-015. Layering
  hygiene, no behavioral bug.
- **Rank 9 (P3, test_gap):** `_check_convergence` (tools/calculix_driver.py:164) asserts convergence by
  ABSENCE of failure substrings + .sta existence — a clean/empty .sta returns `converged=True`. Narrow
  exposure (named tier_1/2 benchmarks re-parse the .frd numerically). The proper fix (require a positive
  ccx completion marker) is a non-surgical solver-truth behavior change → its own slice + Codex + real-ccx
  verification. NOT a quick-win.
- **Rank 12 (P3, roadmap):** no test exercises both graph flags on together; Open-Q2 unresolved. Add one
  composite test (both flags on, NACA dummy) before P5.
- **Rank 13 (P3, doc_drift) — SKIPPED:** ADR-028:48 cites `mock_pipeline.py:76-270` / "27 strings"
  (now STAGE_SPECS@101 + LE10_STAGE_SPECS@221, grep=26). Historical **Context** section (dated
  2026-06-04); rewriting a decision record's line-ref for near-zero value adds churn. Left as a dated
  record. Optionally add an "as-of authoring" qualifier later.

## Note on workflow execution

The verifier agents over-explored the large untracked working tree (many `[stall]`/retry log lines) —
the same failure mode as `codex-review-relay --uncommitted`. Future audit workflows should pin scope
to tracked paths / specific dirs to cut wasted wall-clock.
