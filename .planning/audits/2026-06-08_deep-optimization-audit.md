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
- **Rank 7 (P3, wiring) — DONE** (`bd02b1d`, HF1.1 override, Codex R0 APPROVE): MOVED `_render_inp_deck`
  (a pure jinja2 deck-renderer, zero agent-layer deps) VERBATIM to a new low-layer `tools/inp_writer.py`
  as public `render_inp_deck`; `agents/solver.py` re-exports it under the old name (keeps the live path +
  the `agents.solver._render_inp_deck` mock target); `aeron` fallback now imports DOWNWARD from
  `tools.inp_writer`; and a new `test_low_layers_do_not_import_agents` AST guard scans aeron/ + tools/ for
  agents.* imports so the inversion can't return. Behavior-preserving (deck byte-output unchanged).
- **Rank 9 (P3, test_gap) — DONE** (`41a2b22`, HF1.1 override, owner chose "implement", Codex R0 APPROVE):
  a clean/empty/header-only `.sta` returned `converged=True` (false-positive green). Fix adds the positive
  marker `STA_INCREMENT_ROW` (ccx increment-completion data row; alpha header does NOT match) — convergence
  now requires the data-row regex AND no failure substring. 3 regressions (header-only/empty/garbage all
  assert `_check_convergence is False`); `test_clean_run` + `test_successful_solve` now use the real GS-003
  format. 21 pass; ruff clean. Codex confirmed the regex is linear (no backtracking) and a safe marker
  (no false-neg/false-pos on the reviewed shapes). **Residual (documented, not regressed):** the marker is
  evidenced on `*STATIC` `.sta` shapes (GS-002/003/cantilever); modal/eigenvalue `.sta` formats were NOT in
  the evidence base — if such a step is ever wired, re-confirm the two-leading-int-column assumption holds.
- **Rank 12 (P3, roadmap) — DONE** (`b26d60a`): NEW `backend/tests/test_graph_both_flags_wiring.py` (4
  tests, all values empirically ground-truthed) pins the both-flags-on composite (WARNING geometry+mesh
  crossings + FAILED solver halt + downstream PENDING + net-coverage off=6→on=7 + caseId handoff across
  all 4 crossings). Added to the required honesty-seam CI gate (now 6 files / 69 tests).
- **Rank 13 (P3, doc_drift) — SKIPPED:** ADR-028:48 cites `mock_pipeline.py:76-270` / "27 strings"
  (now STAGE_SPECS@101 + LE10_STAGE_SPECS@221, grep=26). Historical **Context** section (dated
  2026-06-04); rewriting a decision record's line-ref for near-zero value adds churn. Left as a dated
  record. Optionally add an "as-of authoring" qualifier later.

## NEW finding — the 11 pre-existing backend/tests failures root-caused (investigation `wz91qugqf`)

Doubly-shielded from CI (root `testpaths=["tests"]` excludes backend/tests entirely; `backend/pytest.ini`
deselects 4 `@pytest.mark.legacy`). NOT uniform test-rot — 4 distinct causes:

- **Cluster 1a — REAL PRODUCTION BUG — DONE** (`98dc932`, owner chose "fix now", Codex R0 APPROVE):
  `backend/app/api/nl.py:14` declared `APIRouter(prefix="/api/v1")` and `main.py:84` mounted it AGAIN with
  `prefix="/api/v1"` → the NL endpoints lived at the doubled `/api/v1/api/v1/parse-nl|supported-intents|...`.
  Every other router uses a relative prefix; nl.py was the only double. `frontend/.../ChatPanel.tsx:81`
  calls the correct `/api/v1/parse-nl` and was **silently broken**. Fix = drop the self-prefix (nl.py now
  matches the sibling-router convention) + update the one opt-out enumeration entry in `test_phase14`
  (`114-117`) from the doubled path to the correct single path. **Before/after proof** (fix stashed vs
  applied): `test_get_supported_intents` 404 FAIL → PASS; `TestNLAPI parse_natural_language/batch` now reach
  200 (route resolves; residual `success=False` is the no-`OPENAI_API_KEY` parser env = Cluster 2, out of
  scope); `test_phase14` 38 pass; `test_parse_result_file` fails both with/without → pre-existing (Cluster 1b).
- **Cluster 1b — STALE TEST:** the 3 `TestResultAPI` tests hit `/api/v1/supported-formats` /
  `/parse-result`, endpoints DELETED by RFC-001 §6.1 Bucket C (`main.py:83`). Already `@pytest.mark.legacy`.
  Cheap honest deletion.
- **Cluster 2 — ENV:** `test_parsers.py` NL-intent tests get a 401 from an invalid `OPENAI_API_KEY` in the
  env (the in-body skip guards only check for a MISSING key). No code bug; the parser degrades correctly.
- **Cluster 3 — ENV/DEP (legacy):** `test_knowledge_base_linkage` — chromadb references `np.float_`
  (removed in NumPy 2.0; env has numpy 2.4.4) → KB import fails. A requirements-pin decision over a frozen
  Sprint-2 module; do NOT blind-pin numpy<2 (the FEA code uses numpy 2.x).
- **Cluster 4 — STALE TEST:** `test_solver_run_router` asserts `status=="PENDING"` but the route returns
  `"RUNNING"` (solver.py:143; the sibling `test_solver_status_router` agrees). One-line test update.

Net: 1 real bug to surface (1a) + 2 trivial test cleanups (1b delete, 4 one-line) + 2 env/dep items.
Bundled as **surface-to-user** because the headline (1a) reshapes a public API path + ripples to a
CI-tracked test + the frontend.

## Note on workflow execution

The verifier agents over-explored the large untracked working tree (many `[stall]`/retry log lines) —
the same failure mode as `codex-review-relay --uncommitted`. Future audit workflows should pin scope
to tracked paths / specific dirs to cut wasted wall-clock.
