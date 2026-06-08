# Round-2 adversarial audit — AI-Structure-FEA (2026-06-09)

**Method:** ultracode Workflow `wf_265a7932-055` — 6 read-only lenses (solver-numerical ·
concurrency/state-machine · error-handling/fail-closed · API/schema-contract · security-boundary ·
honesty-tier-deep) → each finding adversarially refute-by-default verified by 3 independent skeptics
(survives only if ≥2/3 confirm real) → synthesis. 67 agents, ~4.2M tokens, ~28 min. Exclusion list
fed to finders = the round-1 fixes + known owner-gated items (so they dig for NEW issues).

**Result:** 20 raised → **15 survived** verification. The synthesis agent under-performed (degenerate
summary), so the ranking below is the **main session's own ground-truth** of each survivor (read the
live code; the workflow is a funnel, not the final word).

---

## Ground-truth status legend
- **CONFIRMED-LIVE** — real defect on a code path reachable by the live runtime today.
- **CONFIRMED-LATENT** — real defect, but its consumer is currently the runtime-orphaned 7-node
  `compile_graph` (viz/reviewer) — bites the moment that graph is wired (ADR-028/029 direction).
- **PARTIALLY-MITIGATED** — real inconsistency, but an upstream guard reduces exploitability.

---

## Tranche A — live honesty defects (the product's core identity) — FIX

- **A1 · `solver-rc0-completed-no-convergence` (P1, 3/3) — CONFIRMED-LIVE** ·
  `backend/app/services/solver.py:92-95`. The live async `SolverService._execute_solver` sets
  `job.status = "COMPLETED"` on `return_code == 0` with **zero** `.sta`/convergence inspection.
  CalculiX routinely exits 0 on a non-converged / cut-back-to-nothing solve → surfaced as COMPLETED
  to every consumer (`get_job_status`, sensitivity, copilot, candidate report). This is the **exact**
  gap `tools/calculix_driver._check_convergence` was hardened against in 41a2b22, in a parallel
  solver path. **Fix:** after rc==0, run the same positive-marker gate (reuse
  `_check_convergence(work_dir, jobname)`); non-converged → a non-COMPLETED status. Solver-truth →
  HF1.1 + Codex.

- **A2 · `candidate-spine-jobcompleted-overrides-failure-marker` (P1, 3/3) — CONFIRMED-LIVE** ·
  `backend/app/services/candidate_report_spine.py:790-792`. `_build_solver_status` tests
  `job_completed` FIRST and unconditionally sets `normal_termination="completed"`, never consulting
  the already-computed `has_failure_marker` (line 787). A COMPLETED job whose attached artifacts
  contain `failure_marker` ("no convergence"/"divergence"/"solver exited with code") is still
  rendered "completed" on the **Tier-1 candidate report** (`routes/report.py` feeds it). Independent
  of A1. **Fix:** demote `job_completed` below the failure-marker test; never report "completed" when
  `has_failure_marker`; don't gate the missing-`.sta` reason on `job_completed`. Honesty-critical → Codex.

- **A3 · `sensitivity-experiment-completed-on-rc0` (P3, 3/3) — CONFIRMED-LIVE (downstream of A1)** ·
  `backend/app/services/sensitivity.py:118-130`. Promotes a sweep run to completed iff SolverService
  status==COMPLETED → inherits A1's rc==0-trusts-success. Largely resolved by A1; defensive guard optional.

## Tranche B — trivial live bug — FIX

- **B1 · `report-pdf-missing-datetime-import` (P1, 3/3) — CONFIRMED-LIVE** ·
  `backend/app/api/routes/report.py:153` calls `datetime.now()` but the module never imports
  `datetime` (imports are lines 1-17). The PDF buffer is built one line earlier (151, succeeds), then
  line 153 raises `NameError` → caught by the `except` → HTTP 500. The one-click PDF export has been
  100% non-functional since repo init. **Fix:** add `from datetime import datetime`; add a 200/`application/pdf`
  route test. Trivial; no forbidden zone.

## Tranche C — security boundary (constitutional 命中即审) — FIX, but threat-model scope is owner's

- **C1 · `solver-run-inp-path-arbitrary-exec-dir` (P1, 3/3) — CONFIRMED-LIVE** ·
  `backend/app/api/routes/solver.py:107-110`. The legacy branch takes client `request.inp_path` into
  `Path(...)` with no containment / `.resolve()` / signed-registry guard, then `SolverService` spawns
  `ccx` with `cwd = inp_file.parent`. An existing `.inp` under a sealed `GS-NNN` dir → ccx writes
  outputs into it (corrupts reproducibility evidence). **Fix:** reject abs/`..`; resolve + assert
  `is_relative_to(gs_root)`; `assert_not_signed_registry` derived case_id.

- **C2 · `solver-run-case-id-path-traversal` (P1, 3/3) — CONFIRMED-LIVE** ·
  `backend/app/api/routes/solver.py:77,110,114`. `request.case_id` is interpolated into
  `gs_root/<case_id>` with **no** `_CASE_ID_RE` syntax check on any branch, and **no**
  `assert_not_signed_registry` on the legacy branch (the material_id branch guards at line 76).
  **Verified codebase-wide invariant:** ~16 sibling routes define `_CASE_ID_RE = ^[A-Za-z0-9_-]{1,64}$`
  + call `assert_not_signed_registry`; `solver.py` is the glaring exception. **Fix:** add `_CASE_ID_RE`
  fullmatch + `assert_not_signed_registry` on ALL branches (mirror the siblings).

- **C3 · `solver-run-unauthenticated-mutating` (P2, 2/3) — CONFIRMED-LIVE (posture)** ·
  `routes/solver.py` (`/run`, `/stop/{job_id}`, `/ws/logs/{job_id}`) carry no auth (only
  `Depends(get_db)`); only middleware is CORS `allow_origins=["*"]` (`main.py:76`). DoS via repeated
  `/run` (each a ≤600s ccx), cross-job `/stop` by id-guess. **Threat-model question (owner):** is the
  backend localhost-only (Electron) or deployed? Drives whether this is P2 or just dev-posture.

- **C4 · `cases-detail-unvalidated-case-id-read` (P3, 3/3) — PARTIALLY-MITIGATED** ·
  `backend/app/api/routes/cases.py:49`. `GS_ROOT / case_id / "expected_results.json"` read with no
  `_CASE_ID_RE`/registry guard, but gated by a prior `case_svc.get_case(db, case_id)` row lookup →
  needs a crafted DB id to exploit. **Fix:** add the standard guard for invariant-consistency.

## Tranche D — frd_parser contract (CONFIRMED-LATENT: consumers are the orphaned graph) — SURFACE

- **D1 · `frd-displacement-field-key-mismatch` (P1, 2/3) — CONFIRMED-LATENT** ·
  `tools/frd_parser.py:37-47`. `_field_name_from_header` resolves "displacement" only if literal
  "DISP" is in the 100C header text; real ccx headers carry the field name on the `-4` line, so the
  field is keyed `disp`. Every `extract_field_extremes(parsed, "displacement")` → `None`. Consumers
  `agents/reviewer.py:130` (approval gate → ACCEPT_WITH_NOTE despite skipping the displacement
  cross-check) + `agents/viz.py:82` are **runtime-orphaned today** (the 3rd skeptic refuted on live
  impact; the bug itself is real). Masked by a fixture (`1PDISP` text) real ccx never emits. **Fix:**
  resolve field name from `-4`/component labels (DISP/D1-3 → displacement); add a real-format test.

- **D2 · `frd-component-names-read-wrong-line` (P2, 3/3) — CONFIRMED-LATENT** · `tools/frd_parser.py:59-65`.
  Component names read from `-4` (field label) not `-5` (SXX/SYY/…) lines → `component_names==['STRESS']`.
  von Mises still works via the `component_count>=6` fallback; the label branch is dead on real data.

- **D3 · `reviewer-all-fields-missing-accept-with-note` (P2, 3/3) — CONFIRMED-LATENT** ·
  `agents/reviewer.py:122-188`. All-fields-missing → `max_error_found` stays 0.0 → tolerance branches
  skipped → `VERDICT_ACCEPT_WITH_NOTE` (a passing tier). Missing verification evidence treated as
  acceptance. Same orphaned-consumer caveat as D1. **Fix:** if reference_values non-empty but zero
  comparisons ran → NEEDS_REVIEW/Reject, fault_class=REFERENCE_MISMATCH.

## Tranche E — graph-intake regime (flag-gated `workflow_graph_intake`, default off) — SURFACE

- **E1 · `tier0-dummy-mesh-no-halt-downstream-fabrication` (P2, 3/3) — CONFIRMED (flag-gated)** ·
  `backend/app/services/workflow/mock_pipeline.py:993-1004`. With `workflow_graph_intake` on (and
  `workflow_graph_solver` off) in the triple-dummy regime, MESH_GENERATION projects a tier_0_dummy
  WARNING over a 4-node fallback mesh, but the loop does NOT break — it proceeds to
  MESH_QUALITY_CHECK + SOLVER_RUN over SCRIPTED specs → a green quality check (11260 elements) and a
  green solve one stage after an honest "dummy mesh" WARNING. Honesty-seam gap. **Fix:** a tier_0_dummy
  mesh must halt the pipeline like the tier_0_dummy solver does (break; downstream PENDING).

- **E2 · `graph-mesh-geometry-per-tick-eventloop-block` / `advance-pertick-graph-reexec`
  (P2, 3/3, two finders same root) — CONFIRMED (flag-gated)** ·
  `mock_pipeline.py:942-953` (per-tick loop) × `445-456` (graph dispatch). With `workflow_graph_intake`
  on, `_build_stage_state` rebuilds + `.invoke()`s a fresh LangGraph (real FreeCAD/gmsh fallback I/O +
  numpy) for GEOMETRY/MESH on **every** progress tick (~4×/stage), synchronously on the FastAPI event
  loop (no `to_thread`) → blocks all concurrent runs. **Fix:** mirror the solver discipline — invoke
  the graph once per stage, off-loop via `asyncio.to_thread`.

## Tranche F — UX/correctness — SURFACE

- **F1 · `chat-history-reoffers-actions` (P3, 3/3) — CONFIRMED-LIVE** · `backend/app/api/nl.py:81-89`.
  `/parse-nl` persists every parse's first action onto the stored assistant message regardless of
  whether it was executed; `/history/{case_id}` returns it as `proposedAction` with no executed flag →
  on reload the frontend re-offers a confirm button that re-launches a `run_simulation`/`run_study`.
  **Fix:** record execution state on the ChatMessage; suppress the re-offer for already-run actions.

---

## Disposition

### DONE this session (live honesty tranche)
- **B1 — DONE** (`2fecbc2`): `from datetime import datetime` added; symbol-presence regression. No
  HF1/Codex trigger (missing-import on a route). PDF export no longer NameErrors.
- **A1 + A2 — DONE** (`b15ac30`, Codex R0 APPROVE; paths NOT in HF1 zone): solver.py gates COMPLETED
  on the hardened `_check_convergence` marker (rc==0 + no `.sta` increment row → FAILED, not
  COMPLETED); candidate_report_spine makes a failure_marker dispositive over `job_completed` and
  always discloses a missing `.sta`. 2 spine regressions; 60 consumer tests green. P3 (Codex,
  non-blocking): rc0→FAILED could false-negative a solver mode that legitimately omits `.sta`
  increment rows (same documented residual as 41a2b22). Incidental pre-commit ruff-0.15 hygiene on
  the two files (typing modernization + unused-import + whitespace) noted in the commit.
- **A3 — RESOLVED by A1** (downstream): once solver.py no longer marks non-converged solves COMPLETED,
  the sensitivity sweep's `== "COMPLETED"` rollup inherits the honest status. No separate change.

### DONE this session (tranches C + D1; owner picked C/D/E, localhost threat model)
- **C1/C2/C4 — DONE** (`10923ea`, Codex R0 CHANGES_REQUIRED → R1 APPROVE; paths NOT in HF1 zone):
  solver-run gets a top-of-route `_CASE_ID_RE` (400) + `assert_not_signed_registry` (422) covering ALL
  branches; a client `inp_path` is refused if its lexical OR resolved parts contain a GS-NNN segment
  (Codex R0 P1: the resolve()-only check missed a lexical-GS-NNN symlink — fixed to check both);
  cases.py gets the `_CASE_ID_RE` syntax check only (documented signed-registry opt-out, serves GS-NNN).
  `test_solver_run_router` corrected (non-signed id + real RUNNING return) + 3 guard tests. **C3
  (auth/CORS) DEFERRED** — owner confirmed localhost-only (Electron); no-auth + CORS `*` is accepted
  dev posture, not a live threat. Re-open if the backend is ever network-deployed.
- **D1 — DONE** (`220d7f3`, Codex R0 APPROVE; not in HF1 zone): `_field_name_from_header` now inspects
  the `-4` label (component_names) as well as the header, so a real ccx `.frd` keys `displacement`
  (was `disp` → every `extract_field_extremes(.., "displacement")` returned None). Verified on GS-002;
  +1 real-format regression; 8 synthetic + 34 consumer tests pass. Still latent (reviewer/viz consumers
  orphaned) but fixed while cheap — bites the moment the graph is wired.

### REMAINING — deferred / needs design
- **D2 — DEFER (latent dead code):** component names read from the `-4` field-label line, not the `-5`
  component lines. von Mises still works via the `component_count>=6` fallback; only future
  component-label consumers (VTP annotations) are affected. Fix when those land.
- **D3 — DEFER (defense-in-depth, orphaned):** `agents/reviewer.py` returns ACCEPT_WITH_NOTE when ALL
  reference fields are missing (zero comparisons → max_error 0.0 → passing tier). With D1 fixed the
  primary mislabel cause is gone; this is the residual all-fields-missing guard. In the orphaned
  reviewer → fix alongside D2 when the graph is wired.
- **Tranche E — NEEDS DESIGN DECISION (not a surgical fix):** ground-truthing E1 shows it is a
  **halt-placement design choice**, not a quick fix, and it entangles the ADR-029 honesty seam:
  - **E1** (`mock_pipeline.py`): with `workflow_graph_intake` ON + `workflow_graph_solver` OFF, a
    tier_0_dummy MESH_GENERATION (WARNING over a 4-node fallback) does NOT halt → MESH_QUALITY_CHECK +
    SOLVER_RUN run over SCRIPTED specs → a green quality check (11260 elements) + green solve one stage
    after an honest "dummy mesh" WARNING. Real honesty gap. **BUT** making a tier_0_dummy mesh halt
    changes the both-flags composite that `test_graph_both_flags_wiring` (Rank 12, `b26d60a`) pins as
    "WARNING mesh → FAILED **solver** halt" — i.e. today the SOLVER halts, not the mesh. Options: (a)
    halt at the dummy mesh always (most honest; mesh-halt replaces solver-halt when both-on → update the
    Rank-12 test + reconsider N/13 coverage semantics); (b) halt at the dummy mesh ONLY when
    graph_solver is OFF (preserves both-flags solver-halt); (c) keep proceeding but project the scripted
    downstream stages as tier_0_dummy WARNING too (no green fabrication, no halt). **Owner call** —
    each has different N/13-coverage + both-flags-test implications. Flag is default-OFF (not live-biting).
  - **E2** (`mock_pipeline.py`): per-tick `_build_stage_state` rebuilds + `.invoke()`s the graph for
    GEOMETRY/MESH ~4×/stage synchronously on the FastAPI event loop (no `to_thread`) → blocks concurrent
    runs. Structural async refactor (mirror the solver's once-per-run + `asyncio.to_thread` discipline);
    real but flag-gated. → bundle with the E1 decision.
- **F1 (chat history re-offers actions, live) — NOT this round** (owner did not select F1):
  `/parse-nl` persists unexecuted actions; reload re-offers a confirm button that re-launches a solve.
  Needs a small `executed`-flag schema add. Available next.

**Protocol held:** each fix ground-truthed in the main session before edit; solver-truth/security/schema
→ Codex R0 before local commit (round cap respected: C went R0→R1); local-commit/no-push.
