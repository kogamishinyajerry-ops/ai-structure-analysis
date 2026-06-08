# ADR-029 P3 — Solver Isolation Gate: Reconciled Implementation-Ready Design

**Status:** Implementation-ready (final synthesis). Reconciles the design plan with two adversarial
critiques (maximal-honesty skeptic + north-star/feasibility). All empirical claims re-verified by
direct execution on this host (`ccx` at `/opt/homebrew/bin/ccx`).
**Synthesizer:** Claude Opus 4.8 (1M), read-only research pass, 2026-06-08.
**Scope:** ADR-029 P3 — drive `SOLVER_RUN` through the truncated `architect→geometry→mesh→solver`
LangGraph compiled-graph runtime as `tier_0_dummy`, behind a default-off flag, fully reversible.

> **⚠ IMPLEMENTATION OUTCOME (2026-06-08) — read this first; the as-built design corrects this draft.**
> Ground-truthing the actual code during implementation refuted two of this draft's claims, and the
> shipped design (authoritative record: ADR-029 "P3 — what landed") differs accordingly:
> 1. **Status = `FAILED`, not `WARNING`.** `_overall` ranks PENDING above WARNING, so a WARNING-halt
>    would finalize a run as RUNNING; and the codebase's own real-ccx-solve-failure path already uses
>    FAILED+break. FAILED is more consistent and gives a clean terminal.
> 2. **The pipeline HALTS (break); N/13 is net ≈ 0, NOT "+1".** The scripted `CONVERGENCE_MONITORING`
>    spec asserts `converged=True` and downstream stages fabricate results, so continuing past a
>    faulted solver (this draft's plan) would be internally contradictory. Halting leaves downstream
>    PENDING (honest "not reached"); because RESULT_ANALYSIS routing is then not reached, the net
>    agent-driven count is ~unchanged — the deliverable is the wiring proof + honest halt, not coverage.
> The L2 (per-tick ccx), L3 (true-cause disclosure), L4 (non-tautological wiring fact), L5
> (measurement-key suppression) fixes below all hold as written. The `self._graph_solver_st` cache was
> dropped (the graph-solver feeds no downstream stage, so the M2 cross-call cache is unnecessary).

---

## 0. Ground-truth verification log (this session — not assumed)

Every load-bearing claim was executed, not taken on the plan's word:

| Claim | Result | Source |
|---|---|---|
| `ccx` present | `/opt/homebrew/bin/ccx` | `shutil.which("ccx")` |
| 4-node graph wall time | **0.360 s** (no hang) | live `.invoke()` of truncated graph |
| solver fault on dummy mesh | `rc=201`, `fault_class=solver_convergence`, `verdict=re-run` | `_failed_solve` shape |
| `SolveStatusCode` | `DIVERGED` (`"diverged"`) | `outcome.status.code` |
| `frd_path` / `solve_path` on fault | **`None`** | final SimState |
| `mesh_path` on fault | **PRESENT** (the fallback mesh) | final SimState — **mesh_path is NOT the solver wiring fact** |
| history nodes | **`['architect', 'solver']`** — geometry/mesh append no success history | the solver entry is the unique non-tautological wiring proof |
| solver history `msg` | **the ccx banner `'****…'` asterisks**, NOT the `*ERROR` line | confirms "never echo solver msg into disclosure" |
| dummy mesh `.inp` content | 4 nodes, 1 `C3D4`, **no `*NSET`/`*ELSET`** (Nall/Nfix/Eall undefined) | a green solve is structurally impossible |
| fault classification path | matches **no** SYNTAX/CONVERGENCE/TIMESTEP pattern → `returncode!=0` **catch-all** | "DIVERGED" is a catch-all MISlabel of a deck-parse error |
| `'fault_class' in final_state` | **always True** (seeded `FaultClass.NONE`, last-write key) → **tautological** | the design's OR-disjunct is a vacuous-pass hole |
| import closure of `agents.solver` | `well_harness`/`notion_sync`/`agents.graph` **absent** from `sys.modules` | no Notion side-effect, ADR-015 holds |
| `StageProvenance` members | exactly 3 (`scripted_demo`/`deterministic_agent`/`llm_agent`) | no room for a 4th value |
| `StageStatus` members | includes `warning` | the non-SUCCESS projection is expressible |
| `StageMetrics` extra keys | `extra="allow"` | `solverRan`/`graphNodeRan`/`solverAttempted` ride freely |
| `fidelity_metrics(tool_ran=True, disclosure="")` | **raises `ValueError`** for tier_0_dummy | empty-disclosure is a real crash class to guard |
| `_terminal_status` precedent | "a failed benchmark check is never shown as a plain green success (Codex M4 R0 P2)" | the binding honesty convention for status |
| async `_advance` ccx convention | real LE10 solve is `await asyncio.to_thread(self._run_real_le10, …)` **once**, then ticks read cached `solve_ctx` | the existing pattern the plan would regress |

---

## 1. fork5 — FINAL DECISION

**`attempt_real_ccx_with_disclosure`** (attempt a real ccx run on the dummy fallback mesh; project
the honest faulted outcome as `tier_0_dummy` with `dummyFidelityInputs=True`).

**This is the final decision and it does NOT require an owner gate** (see §7). Both critiques
independently affirmed the *direction* (`attempt_real_ccx`) after empirical verification; both
demanded corrections to the *projection*, not the fork. The corrections are folded in below.

### Rationale
- **North-star value (unique to this fork):** the verified end-to-end run produced
  `history nodes: ['architect','solver']` with a real `ccx` subprocess at `rc=201`. This is the
  **first and only** way to deliver the "solver node executed through the compiled-graph runtime +
  launched a real ccx subprocess" fact that is the entire ADR-029 north star. `hard_skip` carries
  the *identical* honesty envelope (still `tier_0_dummy` disclosure) with **zero** of this value —
  it proves nothing the mesh phase didn't and defers the point indefinitely to an unscoped future
  "real LE10 mesh" phase. ADR-029 §Open-Q5 explicitly frames the choice as "attempt a real ccx run
  … **or** hard-skip"; the ADR's own P3 spec line ("hard-blocks any Tier-1/2 implication **even on a
  green solve**") presupposes a real attempt.
- **Honesty risk bounded to zero by construction:** (a) a green solve is **structurally
  impossible** — the dummy `.inp` defines no `Nall/Nfix/Eall`, verified; (b) `dummyFidelityInputs=True`
  is reused unchanged and hard-blocks any Tier-1/2 implication; (c) the wiring fact is the **solver
  history entry**, never `frd_path` (absent); (d) ZERO measurement keys surfaced; (e) provenance
  stays `DETERMINISTIC_AGENT` (no 4th value).
- **`hybrid` (real-attempt with a `dry_run` fallback) rejected:** `dry_run=True` returns a fake OK
  and would force the disclosure to *lie* ("attempted" when it short-circuited). The empirical
  reality (real attempt → honest `rc=201`) is both available and strictly more honest.
- **Feasibility/reversibility:** 0.360 s wall, inside `tempfile.TemporaryDirectory` (auto-deleted,
  zero repo pollution), truncated graph structurally excludes `human_fallback`/`viz`/Notion.

**`reversible: true` · `requiresOwnerDecision: false`.**

---

## 2. Adversarial landmines → resolution (each FOLDED into the plan)

The design plan as submitted had **five real defects**. All are fixed below; the fixes are now part
of the canonical P3 plan, not optional.

### L1 (BLOCKING, honesty) — `status=SUCCESS` on a faulted solve
**Both critiques + verified.** The plan projected `SOLVER_RUN` with `status=SUCCESS` default. The
underlying ccx run **faulted** (`rc=201`). `_terminal_status` already enshrines the inverse rule
("a failed check is never shown as a plain green success", Codex M4 R0 P2). A green-checkmark solver
badge visually implies the solve worked. The wiring fact ("solver node ran") is honest; the
stage-status ("succeeded") is not.
**RESOLUTION (folded):** `graph_solver_to_stage_state` emits **`status=StageStatus.WARNING`**, not
SUCCESS. The solver NODE ran (honest wiring fact); the ccx SOLVE was rejected → the badge must not be
green. The runner and `mock_pipeline` branch must NOT pass `_terminal_status`'s SUCCESS through to
this projector — the projector itself pins WARNING regardless of the incoming `status` arg (it
ignores the caller's `status` for the terminal/value badge and hard-sets WARNING). Test asserts
`st.status is StageStatus.WARNING` (and `is not StageStatus.SUCCESS`).

### L2 (BLOCKING, correctness/architecture) — event-loop blocking + per-tick ccx
**Maximal-honesty critique + verified worse than stated.** The async `_advance` calls
`_build_stage_state` **once per progress tick** (`for p in _PROGRESS_TICKS:`, lines 890-901) **and**
once for the terminal status (line 933). Routing the ccx launch through the `_build_stage_state` seam
fires **~4 real ccx subprocesses per run, synchronously, on the event loop** — directly regressing
the same file's deliberate `await asyncio.to_thread(self._run_real_le10, …)` convention (line 917),
which runs the solve **once, off-thread**, then has ticks read the cached `solve_ctx`.
**RESOLUTION (folded) — the graph-solver branch must NOT live in the per-tick `_build_stage_state`
seam.** Mirror the real-LE10 architecture exactly:
  - Add a `MockWorkflowStore._run_graph_solver(run_id, user_request, upstream_case_id) -> StageState`
    helper that calls `run_node_via_graph(SOLVER_RUN, …)` **once** and caches the resulting StageState
    in a per-run dict (e.g. `self._graph_solver_st[run_id]`), analogous to `self._solve_ctx`.
  - In `run_sync` and `_advance`, gate it next to the existing `if real and stage is SOLVER_RUN:`
    block: `if settings.workflow_graph_solver and stage is WorkflowStage.SOLVER_RUN and
    <agent_inputs_ready-equivalent>:` → in `_advance` wrap with `await asyncio.to_thread(...)`; in
    `run_sync` call synchronously (tests use `run_sync`, no loop).
  - The per-tick `_build_stage_state` calls for SOLVER_RUN read the **cached** graph-solver StageState
    (or fall through to the scripted RUNNING spec while the solve is in flight) — they NEVER launch
    ccx. The terminal `_build_stage_state` for SOLVER_RUN returns the cached graph-solver StageState
    when present.
  - **This changes the plan's "single `_build_stage_state` seam" claim** (design `filesToTouch`
    mock_pipeline note (3)): P3 must touch `run_sync` / `_advance` (and add the cache + helper), NOT
    ride `_build_stage_state` alone. The plan's assertion "DO NOT touch run_one_stage/run_sync/_advance
    bodies" is **overruled** by this fix. (The `run_one_stage` external-path body also needs the
    same cache read for the M2 route — mirror how it reads `self._solve_ctx.get(run.run_id)` at
    line 797.)
**Net:** exactly one ccx subprocess per run, off the event loop in async, matching the established
convention. Test: assert the graph-solver helper is invoked at most once per run (spy).

### L3 (honesty, wording) — fault MISlabel "DIVERGED"/"convergence-failed" is wrong-cause
**Both critiques + verified.** The deck-parse error (undefined `Nall/Nfix/Eall`) matches **no**
SYNTAX/CONVERGENCE/TIMESTEP pattern; `fault_class=solver_convergence` and
`SolveStatusCode.DIVERGED` arise **only** via the driver's `returncode != 0` catch-all. The solve
never entered the equilibrium loop. The plan's prescribed disclosure/config strings ("convergence-
failed on dummy mesh", "rc=201, DIVERGED") assert a physics-shaped failure that did not happen.
**RESOLUTION (folded):** the disclosure (and the `config.py` docstring) must state the TRUE cause and
flag the catch-all. Canonical wording is fixed in §5. Do **NOT** write "DIVERGED"/"发散"/"convergence-
failed" as the literal physical outcome unqualified. The known-driver-limitation framing is mandatory.
**Do NOT touch `calculix_driver.py` in P3** — the mislabel is a pre-existing driver limitation; fixing
the classifier is a separate cleanup candidate (open risk OR-1). A test asserts the disclosure contains
the deck-error phrasing AND the "catch-all / driver-limitation / not numerical divergence" qualifier,
and does **not** contain "发散" unqualified.

### L4 (honesty, vacuous-pass) — tautological wiring fact (`'fault_class' key present`)
**North-star critique + verified.** `_seed_state` seeds `fault_class=FaultClass.NONE`; the SimState
`fault_class` field is a plain last-write key, so `'fault_class' in final_state` is **always True**,
even if the solver node never ran. The OR-disjunct lets `toolRan=True` be claimed on a graph where
the solver did not execute — exactly the vacuous-pass class the invariant forbids ("node ran ≠ node
authored; refuse toolRan without the wiring fact").
**RESOLUTION (folded):** the solver wiring fact is **EXACTLY**
`any(h.get('node') == 'solver' for h in final_state.get('history', []))`. **Drop the `'fault_class'
key present` disjunct entirely.** Empirically the solver history entry is the sole non-tautological
signal (history nodes were `['architect','solver']`; geometry/mesh append no success history). Note
the two bare-`{"fault_class": FaultClass.UNKNOWN}` early returns in `solver.run` (lines 164, 183 —
missing-mesh / mesh-input validation) append **no** history entry; with our seeded mesh those paths
are unreachable, but the wiring fact correctly treats them as "solver did not produce its node
contract" → runner falls back to scripted. Tests: (a) inject a state with no solver history entry →
runner raises `NotImplementedError` (falls back to scripted), does NOT project; (b) the
expected-fault path (solver history present, `frd_path` absent) DOES project a tier_0_dummy stage.

### L5 (honesty, anti-leak completeness) + disclosure provenance
**Both critiques.** (a) `_SOLVER_MEASUREMENT_KEYS` must cover **every** result-shaped key
`agents.solver.run`'s green path could surface — its green return adds `frd_path`/`solve_path`/
`solve_metadata` and result artifacts. Today the seed can't green-solve, but the projector is the
load-bearing seam; the anti-leak invariant must be machine-checked, not "structurally true today".
(b) The disclosure must be authored from the projector's **own static knowledge**, NEVER from the
solver history `msg`/`outcome.status.message` (empirically the banner `'****'` asterisks).
**RESOLUTION (folded):** (a) `_SOLVER_MEASUREMENT_KEYS` (both camel + snake) = `frdPath/frd_path`,
`solvePath/solve_path`, `solveMetadata/solve_metadata`, `maxVonMises*/max_von_mises*`,
`maxDisplacement*/max_displacement*`, `safetyFactor/safety_factor`, `residual`, `converged`,
`wallTimeS/wall_time_s`, `ccxVersion/ccx_version`, `frames`, `fields`. Test asserts each absent AND
`st.artifacts` is empty (`StageArtifacts()` all-None). (b) `graph_solver_to_stage_state` builds the
disclosure as a literal string constant (§5); a test asserts the projected disclosure contains `ccx`
+ deck-error phrasing and does **NOT** contain a run of `****` asterisks.

### Additional correction — false "60s timeout isolation gate" claim
**North-star critique + verified.** `agents.solver.run` constructs `SolveOptions()` with no args
(line 187) → `timeout_s=None`. The plan's "explicit short 60s SolveOptions timeout" **does not exist
in the code path**. Given the empirical <1 s fault, **drop the "60s timeout"/"belt-and-suspenders
isolation gate" language** from rationale, disclosure, and ADR P3 section; state the honest empirical
bound ("deck-parse fault in <1 s") instead. Installing a real timeout would require threading
`timeout_s` through `agents/solver.py:187` — a wider change to flag to Codex; **not** done in P3.
The tempdir auto-clean + the structurally-truncated graph remain the real (sufficient) isolation
guarantees.

---

## 3. Files to touch (reconciled)

> All additive, flag-OFF by default, byte-identical default path, fully reversible.

1. **`backend/app/core/config.py`** — ADD `workflow_graph_solver: bool = False` immediately after
   `workflow_graph_intake` (line 66). Docstring mirrors `workflow_graph_intake` but: gates ONLY
   `SOLVER_RUN` through the truncated `architect→geometry→mesh→solver` graph as `tier_0_dummy`; the
   ccx subprocess runs on the dummy fallback mesh and **fatal-errors at deck parse (`rc=201`)** because
   the fallback mesh defines no `Nall/Nfix/Eall` sets — classified `solver_convergence` only via the
   driver's `returncode!=0` catch-all (a known driver limitation; **not** numerical divergence);
   `dummyFidelityInputs=True` hard-blocks any Tier-1/2 implication even on a (structurally impossible)
   green solve; the faulted solve is shown as **WARNING, never green SUCCESS**; default False so CI +
   contract suite are byte-identical. **NEVER overload `workflow_real_solver` or `workflow_graph_intake`.**

2. **`agents/graph_runner.py`** —
   - ADD `build_intake_geometry_mesh_solver_graph()`: clone of `build_intake_geometry_mesh_graph`
     (@236); lazy `from agents import solver` (+ reuse lazy `from agents import mesh`);
     `add_node('solver', solver.run)`; edges `architect→geometry→mesh→solver→END`. First graph to
     launch a real ccx subprocess. NEVER imports `agents.graph`.
   - ADD `run_solver_via_graph(user_request, *, run_id, existing_case_id=None, status=…, progress=…)`:
     triple-dummy gate identical to `run_mesh_via_graph` (`naca_wing AND not FREECAD_AVAILABLE AND not
     GMSH_AVAILABLE`) else raise `NotImplementedError`. Seed the SOLVER-complete NACA `SimPlan`
     (`_SEED_SENTINEL`; default `material`/`solver` via Field factories so `_render_inp_deck` reaches
     the ccx attempt; `loads=[]/bcs=[]` → undefined sets → guaranteed `rc=201`). Invoke inside
     `tempfile.TemporaryDirectory(prefix="graph_solver_")`. Derive `plan_authored_by` from the
     sentinel. **WIRING FACT = `any(h.get('node')=='solver' for h in final_state.get('history',[]))`**
     (NOT `frd_path`, NOT the `fault_class` key). **Control flow:** if a solver history entry exists →
     project via `graph_solver_to_stage_state` (the expected ccx-fault IS the deliverable). If **no**
     solver history entry → raise `NotImplementedError` (graph never reached solver / genuine runtime
     bug → scripted fallback). Outer `except Exception` → re-raise as `NotImplementedError`. ADD both
     symbols to `__all__`.

3. **`agents/state_projection.py`** —
   - ADD constants near @1170: `_GRAPH_SOLVER_RUNNER_TAG = "langgraph-architect-geometry-mesh-solver"`,
     `_SOLVER_CURRENT_OBJECT = "solver_model"`, and the literal disclosure (§5).
   - ADD `graph_solver_to_stage_state(final_sim_state, user_request, *, run_id, plan_authored_by,
     status=…, progress=…) -> StageState` (clone of `graph_mesh_to_stage_state` @1269):
       - extract `plan` (SimPlan; raise if absent);
       - `tool_ran = any(h.get('node')=='solver' for h in final_sim_state.get('history',[]))`; refuse
         `toolRan=True` without it (raise);
       - **`status` is hard-set to `StageStatus.WARNING`** (ignore the incoming SUCCESS — L1);
       - metrics `= {geometryFamily, caseId, solverRan: False, solverAttempted: True,
         dummyFidelityInputs: True, graphNodeRan: True, graphRunner: _GRAPH_SOLVER_RUNNER_TAG,
         planAuthoredBy}`; then `metrics.update(fidelity_metrics(tool_ran=tool_ran, data_real=False,
         disclosure=<§5>))`;
       - `provenance=DETERMINISTIC_AGENT` (no 4th value); `artifacts=StageArtifacts()` EMPTY;
         `current_object=_SOLVER_CURRENT_OBJECT`;
       - `next_action='进入收敛监控（convergence_monitoring）。'` (genuine next stage, not a reused
         upstream string);
       - **surface ZERO `_SOLVER_MEASUREMENT_KEYS`** (anti-vacuous-pass).
   - The `solverRan: False` + `solverAttempted: True` + `graphNodeRan: True` + WARNING quartet is the
     single unambiguous wire story (L-frame): the solver NODE executed, the ccx SOLVE was attempted
     and rejected, nothing was solved. The disclosure (§5) states this in words; a test pins the
     `未求解 / 求解被拒` phrasing co-located with `solver 节点已执行`.

4. **`backend/app/workbench/agent_facade.py`** — in `run_node_via_graph` (@153), ADD before the
   terminal raise (@204):
   ```python
   if stage is WorkflowStage.SOLVER_RUN:
       return graph_runner.run_solver_via_graph(
           user_request or "", run_id=run_id, existing_case_id=existing_case_id,
           status=status, progress=progress,
       )
   ```
   UPDATE the terminal `NotImplementedError` message (currently "the solver stage lands in a later
   phase behind the ccx-subprocess isolation gate") → solver IS wired now; mention only still-unwired
   stages (convergence_monitoring / post_processing / result_analysis / …). Facade imports ONLY
   `agents.graph_runner` (ADR-015 ok). **No `CONVERGENCE_MONITORING` branch** (no graph node; stays
   scripted, mirroring P2's `MESH_QUALITY_CHECK`).

5. **`backend/app/services/workflow/mock_pipeline.py`** —
   - ADD `WorkflowStage.SOLVER_RUN` to a new graph-solver gate set (do **not** widen
     `_GRAPH_REQUEST_STAGES`, which is keyed to `workflow_graph_intake`; keep the two flags cleanly
     separated). Simplest: a module const `_GRAPH_SOLVER_STAGES = frozenset({WorkflowStage.SOLVER_RUN})`.
   - **Do NOT route the solve through `_build_stage_state`'s per-tick seam (L2).** Instead, add a
     per-run cache `self._graph_solver_st: dict[str, StageState]` and a helper
     `_run_graph_solver(run_id, user_request, upstream_case_id) -> StageState` that calls
     `run_node_via_graph(SOLVER_RUN, …)` once. Gate it in `run_sync` / `_advance` / `run_one_stage`
     next to the existing `if real and stage is SOLVER_RUN:` block:
       - `_advance`: `solve_st = await asyncio.to_thread(self._run_graph_solver, …)` once; cache it.
       - `run_sync`: call synchronously once; cache it.
       - `run_one_stage`: read `self._graph_solver_st.get(run.run_id)` (mirror line 797 `solve_ctx`).
     The flag predicate must include the `_agent_inputs_ready`-equivalent (`specs is STAGE_SPECS` +
     non-empty user_request + `error is None`), so it auto-suppresses whenever `workflow_real_solver`
     swaps to `LE10_STAGE_SPECS` (the LE10 Tier-1 path wins; the two flags never collide on
     SOLVER_RUN).
   - `_build_stage_state` for SOLVER_RUN: when a cached graph-solver StageState exists, return it
     (terminal) / its RUNNING shadow (ticks); else the scripted spec. Wrap the helper call in
     `try/except NotImplementedError: pass` so an out-of-regime crossing (bracket / real kernel)
     falls through to the scripted SOLVER_RUN spec instead of hard-crashing — the swallow-allowlist
     equivalent the plan described, relocated out of the per-tick seam.
   - **Do NOT add `CONVERGENCE_MONITORING`** to any graph set (stays scripted; mirrors P2's
     `MESH_QUALITY_CHECK`).

6. **`backend/tests/test_graph_solver_wiring.py`** (NEW) — mirrors `test_graph_mesh_wiring.py`. Full
   matrix in §4. Flag toggled is `settings.workflow_graph_solver`. Shared fixtures: `_triple_dummy`,
   `_ccx_dummy_fault` (monkeypatches `agents.solver.run` → canonical `_failed_solve` shape with a
   `history=[{'node':'solver','returncode':201,…}]` entry, so tests are **host-independent / never
   launch a live ccx**), `_agent_driven`, `_SOLVER_MEASUREMENT_KEYS`.

7. **`docs/adr/ADR-029-graph-runtime-wiring.md`** — ADD a "P3 — what landed" section (mirror P0/P2)
   and **RESOLVE Open-Question #5 inline**: the graph-driven solver DOES attempt a real ccx run on the
   dummy mesh (honest faulted disclosure, `dummyFidelityInputs=True`, **WARNING status**), not
   hard-skip. Record the empirical facts: `rc=201` via the `returncode!=0` catch-all (NOT numerical
   divergence; pre-existing driver limitation), `frd_path` absent, wiring fact = solver history entry,
   <1 s fault (no real timeout installed). Note `CONVERGENCE_MONITORING` stays scripted (mirrors P2's
   `MESH_QUALITY_CHECK`); N/13 rises by exactly **+1** (SOLVER_RUN only).

---

## 4. Test matrix (reconciled — design tests + folded-in adversarial tests)

| # | Test | Asserts |
|---|---|---|
| 1 | `test_run_solver_via_graph_invokes_4node_graph` | Spy `build_intake_geometry_mesh_solver_graph().invoke` → invoked True; returned `st.stage is SOLVER_RUN`. Proves the COMPILED 4-node runtime drove it, not a direct `solver.run`. |
| 2 | `test_keyless_solver_is_tier0_dummy_with_guard` | `_triple_dummy`+`_ccx_dummy_fault`+keyless. `provenance is DETERMINISTIC_AGENT`; `graphNodeRan True`; `graphRunner=='langgraph-architect-geometry-mesh-solver'`; `planAuthoredBy=='deterministic_seed'`; `fidelityTier=='tier_0_dummy'`; `solverRan False`; `solverAttempted True`; `dummyFidelityInputs True`; `fidelity['dataReal'] False`; for k in `_SOLVER_MEASUREMENT_KEYS`: k not in m; `st.artifacts` empty; explanation contains `ccx`/`dummy`/deck-error phrase/`tautological`/`dummyFidelityInputs`/`未验证`/`未求解`; `next_action` contains `收敛监控`, not a misdirecting upstream string. |
| 3 | **`test_faulted_solve_is_warning_not_success`** (L1) | `status is StageStatus.WARNING` and `is not StageStatus.SUCCESS`. The blocking honesty pin. |
| 4 | `test_architect_authored_plan_flows_to_solver` | `+_ccx_dummy_fault`+architect plan w/o sentinel (`case_id='AI-FEA-P0-77'`). `planAuthoredBy=='architect_llm'`; `caseId=='AI-FEA-P0-77'`; `fidelityTier=='tier_0_dummy'`; `dummyFidelityInputs True`; provenance DETERMINISTIC_AGENT. |
| 5 | **`test_expected_ccx_fault_projects_not_falls_back`** (L4) | The expected ccx-fault path (solver history entry present, `frd_path` absent) PROJECTS a tier_0_dummy SOLVER_RUN stage and does NOT fall through to scripted. Proves P3 is not a hollow stub. |
| 6 | **`test_no_solver_history_falls_back_to_scripted`** (L4) | Inject a graph state with NO `node=='solver'` history entry → `run_solver_via_graph` raises `NotImplementedError`. The non-tautological wiring guard. |
| 7 | **`test_disclosure_states_true_fault_cause_not_diverged`** (L3) | Disclosure contains `ccx` + the undefined-set/deck-parse phrasing + the "catch-all / driver limitation / 非数值发散" qualifier; does NOT contain a run of `****` asterisks; does NOT assert `发散` as the literal physical outcome unqualified. |
| 8 | **`test_solver_measurement_keys_and_artifacts_absent`** (L5) | for k in `_SOLVER_MEASUREMENT_KEYS` (camel+snake, incl. `frdPath/frd_path/solvePath/solve_path/solveMetadata/maxVonMises/maxDisplacement/safetyFactor/residual/converged/wallTimeS/ccxVersion`): k not in m; `st.artifacts == StageArtifacts()`. |
| 9 | `test_n13_rises_by_one_solver_graph` | off `run_sync`; then `workflow_graph_solver=True`+`_ccx_dummy_fault`; on `run_sync`. `_agent_driven(on)==_agent_driven(off)+1`; off SOLVER_RUN SCRIPTED_DEMO (no `graphNodeRan`); on SOLVER_RUN DETERMINISTIC_AGENT + `graphNodeRan`+`dummyFidelityInputs`+`tier_0_dummy`. CONVERGENCE_MONITORING scripted on both. |
| 10 | `test_convergence_monitoring_stays_scripted` | Flag on. CONVERGENCE_MONITORING SCRIPTED_DEMO, no `graphNodeRan`, no `converged` claim. The faulted dummy solve must NEVER imply convergence. Mirrors P2 leaving MESH_QUALITY_CHECK scripted. |
| 11 | `test_solver_case_id_handoff_preserved_through_graph` | Flag on. solver `caseId` == intake `caseId` (flows intake→geometry→mesh→solver via seeded plan), `!= 'AI-FEA-P0-05'`. |
| 12 | `test_gmsh_present_falls_back_no_mislabel` | FREECAD False, GMSH True → `run_solver_via_graph` raises `NotImplementedError` (a real mesh would make a real solve tier_1; refuse tier_0). |
| 13 | `test_freecad_present_falls_back_no_mislabel` | FREECAD True, GMSH False → raises `NotImplementedError`. |
| 14 | `test_non_naca_falls_back_no_mislabel` | `_triple_dummy`+bracket request → raises `NotImplementedError`. |
| 15 | `test_bracket_flag_on_solver_stays_scripted` | E2E: `_triple_dummy`+flag on+bracket → SOLVER_RUN stays SCRIPTED_DEMO (crossing refused, `NotImplementedError` swallowed → scripted), no `graphNodeRan`. |
| 16 | `test_real_solver_flag_wins_over_graph_solver` | BOTH `workflow_real_solver=True` AND `workflow_graph_solver=True`. SOLVER_RUN follows LE10 Tier-1 path (`specs=LE10_STAGE_SPECS` → graph-solver gate suppressed); NOT tier_0_dummy graph-driven. Two flags never collide. |
| 17 | `test_no_downstream_node_past_solver_executes` | `_triple_dummy`+spy `agents.viz.run`/`agents.human_fallback.run` → calls == []. Solver is terminal. |
| 18 | `test_graph_runner_avoids_agents_graph_adds_solver` | AST-walk `inspect.getsource(graph_runner)`: no `agents.graph`/`agents.graph.*` import; `agents.solver`/`agents` imported. |
| 19 | `test_flag_off_byte_identical_default_path` | `workflow_graph_solver=False` (default): SOLVER_RUN byte-identical to pre-P3 scripted spec (SCRIPTED_DEMO, no `graphNodeRan`). |
| 20 | `test_disclosure_non_empty_enforced` | `graph_solver_to_stage_state` w/ `tool_ran=True` always passes a non-empty disclosure to `fidelity_metrics` (data_real=False) → no `ValueError`; `fidelityTier=='tier_0_dummy'`. Guards the empty-disclosure crash class. |
| 21 | **`test_graph_solver_runs_ccx_at_most_once_per_run`** (L2) | Spy `_run_graph_solver` / the graph `.invoke` across a full `run_sync`: invoked ≤1×. Proves the per-tick `_build_stage_state` seam never launches ccx. |
| 22 | **`test_async_advance_offloads_graph_solver`** (L2) | In `_advance`, the graph-solver helper is invoked via `asyncio.to_thread` (spy `to_thread` or assert no synchronous ccx on the loop). The event-loop-blocking guard. (May be merged with #21 if `to_thread` is spied.) |

> **CI host-with-ccx hazard:** EVERY solver-driving test uses `_ccx_dummy_fault` (or asserts the
> honest `PREFLIGHT_FAILED` disclosure) — never lets a test launch a real ccx subprocess on a CI
> runner that happens to have ccx. Enforced via the single shared fixture.

---

## 5. Canonical disclosure text (authored from the projector's OWN static knowledge — L3/L5)

> Authored as a literal constant in `state_projection.py`. NEVER built from the solver history `msg`
> or `outcome.status.message` (empirically the banner `'****'` asterisks).

```
4-node 图 architect→geometry→mesh→solver 经真实 LangGraph 运行时（compiled graph .invoke）执行；
solver 节点从共享图状态消费 mesh_path（dummy fallback 网格）并真实启动 ccx 子进程（dry_run=False，
于 tempdir 内隔离，部署即删）。{authored 子句：plan 由 LLM architect 节点产出 / 由确定性规则代理 seed}。
但上游无 gmsh 内核，generate_mesh 仅写出硬编码 4-node/1-tet C3D4 占位网格（generation_mode=fallback），
其上游是 10 字节占位 STEP（非 ISO-10303）。该 dummy 网格未定义任何节点集/单元集（Nall/Nfix/Eall），
故 ccx 在 deck 解析阶段即致命报错 rc=201（deck/preflight 错误，*ERROR reading … 引用未定义单元集）——
这是 deck 解析失败，solver 从未进入平衡迭代回路；驱动层仅凭 returncode!=0 兜底将其归类为 solver_convergence /
SolveStatusCode.DIVERGED（已知驱动局限，非真实数值发散，详见 OR-1）。即便某 seed 令其绿色求解，其输入仍为
dummy 保真（单位四面体 + 占位 STEP），任何求解数值均为 tautological garbage-in（dummyFidelityInputs=True）。
故本阶段状态记为 WARNING（求解被拒，未求解），绝不显示为绿色 SUCCESS；不 surface 任何测量形态 solver 指标
（maxVonMises / maxDisplacement / safetyFactor / residual / converged / frdPath 一律抑制，
anti-vacuous-pass）；不产出任何持久 artifact（ccx scratch 随 tempdir 删除）。唯一净增事实 = 真实 solver
节点经 4-node 图驱动 SOLVER_RUN 并真实启动了 ccx 子进程（N/13 +1），保真度为 dummy。CONVERGENCE_MONITORING
仍为 scripted（无独立图节点；绝不从失败的 dummy 求解伪造 converged=True）。
[EN: the 4-node compiled graph ran; ccx was really attempted on the dummy fallback mesh and FATAL-
ERRORED AT DECK PARSE (rc=201) because the dummy mesh defines no Nall/Nfix/Eall sets — a deck/preflight
error, NOT numerical divergence; the driver labels it solver_convergence/DIVERGED only via its
returncode!=0 catch-all (a known driver limitation). Even a green solve would be dummy-fidelity.
The stage is WARNING (solve rejected, nothing solved), never green SUCCESS. Zero measurement keys
surfaced; dummyFidelityInputs=True hard-blocks any Tier-1/2 implication; tier_0_dummy. The only
net-new fact is a real solver node was graph-driven and a real ccx subprocess launched.]
```

**Required substrings tests pin:** `ccx`, `Nall/Nfix/Eall` (or `未定义…单元集`), `deck` (or `解析`),
`returncode!=0` (or `兜底`/`catch-all`), `驱动局限` (or `driver limitation`), `非真实数值发散`
(or `not numerical divergence`), `dummyFidelityInputs`, `WARNING`/`未求解`, `tier_0_dummy`,
`未验证`. **Forbidden:** a run of `****`; `发散` unqualified as the literal outcome.

---

## 6. Codex risk-tier flags (MANDATORY review BEFORE local commit)

Per `CLAUDE.md` risk-tier triggers, P3 fires **multiple** hard gates → a Codex relay review is
required before local commit (not optional):

1. **CalculiX adapter / solver-truth path** — P3 is the FIRST graph to launch a real ccx subprocess
   from the LangGraph runtime (`run_solver_via_graph` + `build_intake_geometry_mesh_solver_graph`).
2. **New honesty-seam projector** — `graph_solver_to_stage_state` introduces a new wiring-fact
   definition (solver history entry, non-tautological) and the WARNING-status pin; Codex must
   adversarially confirm it can NEVER imply a green/validated solve and the wiring fact is
   non-tautological.
3. **Cross-≥3-file change** — config + graph_runner + state_projection + agent_facade + mock_pipeline
   + new test (6 files), and the L2 fix additionally touches `run_sync`/`_advance`/`run_one_stage` +
   a new per-run cache.
4. **Flag-collision composition** — `workflow_graph_solver` vs `workflow_real_solver` on the same
   SOLVER_RUN stage; Codex confirms the LE10 path deterministically wins (`specs is STAGE_SPECS`
   guard) and the two flags never both own the stage.

Recommended relay: governance-tier (`codex-review-relay --uncommitted`) given the solver-truth +
honesty-seam surface. Round cap = 3.

---

## 7. Owner-decision question — NOT required

`requiresOwnerDecision: false`. Reasoning, against the brief's strict bar ("true ONLY if both
branches are honest AND materially value-defining/irreversible enough that ADR-029 reserved it for
the owner — a reversible flag-default the ADR's own framing leans toward does NOT require asking"):

- **Both branches honest?** Yes — `hard_skip` and `attempt_real_ccx_with_disclosure` are both honest
  (both carry the `tier_0_dummy` envelope). So the first conjunct is met.
- **Materially value-defining / irreversible?** **No.** The decision is a **reversible, additive,
  default-OFF flag** (`workflow_graph_solver=False`); the default code path stays byte-identical and
  revert = delete the additions. ADR-029 §Open-Q5 frames the choice with its own lean toward a real
  attempt (the P3 spec line presupposes "even on a green solve"). Both adversarial verifiers, after
  empirical falsification attempts, **affirmed** `attempt_real_ccx` and found the four invariants
  unbreakable. No irreversible semantic is at stake here — the genuinely irreversible Open-Q (#4, "no
  4th provenance value") is already ratified and is **preserved unchanged** by this design.
- ADR-029 listed Open-Q5 as a "genuine owner decision deferred to its phase," but the substance it
  reserved was *attempt-vs-skip* — a question both critiques have now empirically resolved toward
  attempt, with zero residual honesty risk and full reversibility. Surfacing it as a blocking either/or
  would be ceremony, not a real fork.

Therefore: **proceed to implement** (with the Codex relay review as the gating step before local
commit), no owner sign-off required first.

---

## 8. Open risks (carried, not fixed in P3)

- **OR-1 (driver mislabel) — RESOLVED 2026-06-08 (separate surgical commit, post-P3):** the
  `calculix_driver.classify_solver_failure` `SYNTAX_PATTERNS` were extended with the real ccx
  deck-parse wording (`*error reading` / `*error in calinput` / `has not yet been defined`), so an
  undefined-set deck error now classifies **`SOLVER_SYNTAX` → `SolveStatusCode.SOLVER_ERROR`**, never
  `SOLVER_CONVERGENCE` / `DIVERGED`. Verified safe via safe-refactor consumer enumeration (router +
  reviewer treat SYNTAX and CONVERGENCE identically; the DIVERGED mapping keys only on
  SOLVER_CONVERGENCE; no existing test feeds these patterns). Regression tests:
  `test_calculix_driver.test_deck_parse_undefined_set_is_not_convergence` +
  `test_aeron_calculix_backend.test_failure_status_code_deck_parse_is_solver_error_not_diverged`.
  **Coupled FOLLOW-UP — DONE (separate commit, post-c6ecb3e):** because the dummy deck's undefined-set
  parse error now classifies `solver_syntax` (not `solver_convergence` via the old catch-all), the P3
  graph-solver disclosure made a now-FALSE claim about the driver's classification. Propagated the
  reclassification through every live spot: `state_projection.graph_solver_to_stage_state` (docstring +
  zh/en disclosure prose + the hard-set `StageError.fault_class` SOLVER_CONVERGENCE→SOLVER_SYNTAX +
  detail), `config.py` workflow_graph_solver comment, `docs/adr/ADR-029` "what landed" line, and the
  `test_graph_solver_wiring.py` `_ccx_dummy_fault` fixture (fault_class + realistic "has not yet been
  defined" wording) + `test_disclosure_states_true_fault_cause_not_diverged` (now asserts `solver_syntax`
  named, `catch-all` GONE). The disclosure's core point (deck-parse, NOT numerical divergence, dummy
  fidelity) is unchanged and now accurately sourced. The historical design-draft fence above (§ with the
  pre-correction WARNING wording) is left as a dated record, not rewritten. Possible future robustness
  (NOT done — out of scope): have the projector READ `solver_entries[-1]['fault_class']` instead of
  hard-coding the known dummy-deck outcome, so it can never drift if the classifier changes again.
- **OR-2 (CONVERGENCE_MONITORING stays scripted):** node→stage map (ADR @94) maps both SOLVER_RUN and
  CONVERGENCE_MONITORING to the solver node, but there is no separate graph node. P3 deliberately
  leaves CONVERGENCE_MONITORING scripted (+1 only, SOLVER_RUN), mirroring P2's MESH_QUALITY_CHECK.
  `test_convergence_monitoring_stays_scripted` guards against fabricating `converged=True`. If a
  future reviewer expects +2, defend via the P2 precedent.
- **OR-3 (timeout not installed):** `agents.solver.run` uses `SolveOptions()` (timeout None →
  driver default 600 s). Empirical fault <1 s makes this moot today; if a future non-dummy seed ever
  reaches a slow solve it would run to the driver default. Threading `timeout_s` through
  `agents/solver.py:187` is a wider change deferred to a later phase (flag to Codex if pursued). The
  P3 disclosure does NOT claim a timeout guard.
- **OR-4 (outer-except masks real bugs):** `run_solver_via_graph`'s outer `except → NotImplementedError`
  converts ANY exception (incl. a genuine runtime bug) into a scripted fallback, surfacing only a
  `logger.warning`. Acceptable per the no-hard-crash invariant; the EXPECTED ccx fault (solver
  history present) is distinguished from a graph-runtime error (no solver history) so the deliverable
  still projects. Reduces debug signal — accepted.
- **OR-5 (CI ccx-absence):** production launches real ccx when present; tests monkeypatch
  `agents.solver.run` to the canonical fault shape (host-independent). A future test that forgets the
  monkeypatch on a ccx-equipped CI runner would launch a real subprocess — mitigated by routing every
  solver test through the single `_ccx_dummy_fault` fixture.

---

## 9. Reversibility statement

Fully reversible and additive. New flag `workflow_graph_solver` defaults False → the default code path
is byte-identical (the graph-solver branch is dead). New symbols are pure additions
(`build_intake_geometry_mesh_solver_graph`, `run_solver_via_graph`, `graph_solver_to_stage_state`,
the disclosure constant, 2 module constants, `__all__` entries, 1 facade branch, 1
`_GRAPH_SOLVER_STAGES` set, the `_run_graph_solver` helper + per-run cache, the gated calls in
`run_sync`/`_advance`/`run_one_stage`, 1 new test file). No existing function signature/return shape
changes; no schema field; no 4th `StageProvenance` value; `fidelity_metrics` reused unchanged. All
ccx scratch lives in a `tempfile.TemporaryDirectory` (auto-deleted) — zero repo/golden_samples
pollution, no Notion/network side-effect (truncated graph structurally excludes
human_fallback/viz/Notion). Revert = delete the additions (flag already off). The P2 mesh wiring is
untouched; `test_graph_mesh_wiring.py` stays valid.
```
