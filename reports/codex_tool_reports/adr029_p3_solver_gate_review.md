# Codex relay review — ADR-029 P3 (solver isolation gate)

- **Date:** 2026-06-08
- **Relay:** `codex-relay-with gpt-5.5` (86gs, reasoning xhigh), diff-only static review
  (governance-tier trigger: solver-truth path + new honesty-seam projector + 6-file change).
  `codex-review-relay --uncommitted` / repo-walking runs over-explored the large untracked working
  tree and produced no verdict (the documented failure mode); the diff-only re-run is canonical.
- **Scope reviewed:** the staged P3 diff — `agents/graph_runner.py`, `agents/state_projection.py`,
  `backend/app/core/config.py`, `backend/app/services/workflow/mock_pipeline.py`,
  `backend/app/workbench/agent_facade.py`, `backend/tests/test_graph_solver_wiring.py`,
  `docs/adr/ADR-029-graph-runtime-wiring.md`, `.planning/ADR029_P3_SOLVER_GATE_DESIGN.md`.

## R0 — CHANGES_REQUIRED (1×P1, 2×P2, 1×P3)

- **P1 (honesty):** the wiring fact `any(node=='solver')` accepted *any* solver history as proof a
  ccx subprocess launched, but `_preflight_failure` (ccx absent) and `_unsupported_backend_failure`
  (non-CalculiX) also emit solver history with **no** ccx launch — so `solverAttempted=True` + the
  "ccx launched / deck-parse rc=201" disclosure over-claimed. **Fix:** distinguish "solver node ran"
  (`graphNodeRan`, always) from "ccx subprocess launched" (`ccxSubprocessLaunched` ⇔ `returncode is
  not None`); gate `solverAttempted` + the launch/deck-parse disclosure on the returncode; add an
  honest "ccx did not launch (preflight / unsupported / deck-prep)" branch.
- **P2a:** `test_real_solver_flag_wins_over_graph_solver` passed `fail_at_stage=SOLVER_RUN`, hitting
  the injected-failure branch before either solver path — proving nothing. **Fix:** stub
  `_run_real_le10`, spy `_run_graph_solver`, both flags on → assert the graph helper is never called.
- **P2b:** ADR-029 still said "convergence-failed / failed-to-converge". **Fix:** deck-parse/preflight
  wording, explicitly "not numerical divergence".
- **P3:** tautological test assertion `assert "tier_0_dummy" not in expl or True`. **Fix:** assert
  concrete disclosure/metric behavior (+ a new preflight test).

## R1 — APPROVE (diff-only re-run)

All four R0 findings confirmed resolved at `state_projection.py` (returncode-gated
`solverAttempted`/`ccxSubprocessLaunched` + "ccx did not launch" path), the rewritten flag-collision
test, the ADR wording, and the de-tautologized tests. No new blocking issues. Codex re-verified the
honesty invariants directly: solver stage stays **FAILED**, downstream **PENDING** on the halt, **no**
measurement keys / artifacts, **no** 4th provenance value, **no** N/13 inflation, async solver
offloaded **once** in `_advance`, the real-solver flag wins, and `mock_pipeline` imports **only** the
facade (never `agents.*`). **VERDICT: APPROVE.**

## R1 (repo-walking pass) — 2 doc-consistency over-claims (folded in)

A parallel R1 invocation that walked the committed tree (rather than the diff alone) caught two
code↔doc inconsistencies the diff-only pass missed: the P1 code fix (`ccxSubprocessLaunched` /
`solverAttempted` gated on `returncode`) had not propagated to (a) the `config.py`
`workflow_graph_solver` docstring ("ccx subprocess genuinely ran", unconditional) and (b) the
ADR-029 "P3 — what landed" line (`solverAttempted=True`, unconditional) — both reintroducing the very
R0 P1 over-claim for preflight/unsupported faults. Both were corrected (documented as returncode-gated,
false for no-returncode failures). Lesson: for a change touching both code and the docs/comments that
describe it, follow a diff-only review with a consistency sweep (or one repo-walking pass).

Round cap respected (R0 + 1 fix round + doc-consistency sweep). Local commit, no push, flag default-off.
