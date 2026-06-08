# ADR-029: Wire the LangGraph Compiled-Graph Runtime Behind the Live Pipeline (graph-driven execution)

- **Status:** **Accepted** (ratified 2026-06-07 by the human owner — "批准 ADR-029 + 继续 P1" — after
  the Codex relay governance review of the P0 slice closed **R0 APPROVE** (no findings;
  `reports/codex_tool_reports/adr029_p0_graph_runtime_review.md`). Drafted 2026-06-07 by Claude Opus
  4.8 (1M) under the standing owner directive "ultracode 全权授权你继续深度优化项目，记住它是多agent
  分工协作的智能体系统" + the 2026-06-07 owner decision, when offered the milestone fork, to take
  **path B — directly wire `agents/graph.py` (the real north star)**. The P0 slice it specifies is
  **additive + flag-gated OFF by default** (inert until explicitly enabled); P1 (architect→geometry
  cross-node dependency) proceeds under this ratification. The five §Open-questions remain owner
  decisions deferred to their phases (P3 solver gate, P4 Notion isolation, replace-vs-parallel
  default); the "no 4th provenance value" semantic is ratified as the standing default.)
- **Date:** 2026-06-07
- **Decider:** Human owner (path-B selection, 2026-06-07). Drafted by Claude Opus 4.8.
- **Extends (does not amend/reverse):** **ADR-028** (the product multi-agent repositioning). ADR-028
  established *that* the orphaned `agents/graph.py` should drive the runtime and wired individual
  nodes' `run()` through the facade (P1..P-handoff). This ADR specifies *how the actual LangGraph
  compiled-graph runtime* gets wired — the step ADR-028's per-node facade stubs were a stepping stone
  toward — and resolves the SimState↔StageState shape gap ADR-028 left open.
- **Does NOT touch (remain in force and CONSTRAIN this work):** ADR-011 HF path guards · ADR-013
  branch protection · ADR-015 facade discipline (the choke point this routes through) · ADR-023
  Tier 0/1/2 claim system (**bound by it**) · ADR-026 dev-team architecture · ADR-027 G-1/G-2
  guardrails · ADR-028 D2 anti-over-claim provenance gate (N/13 stays provenance-keyed) · solver
  truth · schemas · `golden_samples/**`.
- **Related:** ADR-028 (parent), ADR-015 (the seam), ADR-023 (claim tiers), `~/CLAUDE.md` honesty
  contract. Design adjudicated by workflow `wf_b4b13c99-5ee` (3 lens-diverse proposers → 3
  adversarial verifiers → synthesizer).

---

## Context

ADR-028 verified (2026-06-04) that `agents/graph.py` — a 7-node LangGraph (architect / geometry /
mesh / solver / reviewer / viz / human_fallback) with fault-class routing, per-node retry budgets,
an LLM architect with deterministic fallback, and an interrupt-based human_fallback — is **orphaned**:
`compile_graph`/`build_graph` have **zero non-test callers** and the backend drives the 13 stages
entirely through `mock_pipeline.py`. ADR-028's P1..P-handoff slices wired several nodes' `run()`
**directly** through the `agent_facade`, but **none exercised the actual LangGraph compiled-graph
runtime** (`.invoke`/`.stream` on a `CompiledGraph`). Closing that gap is ADR-028's north star.

### Three empirically-verified facts that constrain the wiring (this session, 2026-06-07)

The design workflow's adversarial verifiers **falsified three prior assumptions**; each was then
independently re-verified by direct inspection on this host:

1. **`ccx` IS present** at `/opt/homebrew/bin/ccx` (`shutil.which("ccx")` resolves it). The prior
   "live-solver crossing is hermetically infeasible (no ccx)" framing in earlier STATE/commit notes
   was **wrong on this dev host** (it may still hold in a clean CI container). **Honest correction:**
   the reason to defer the solver node is NOT "no ccx" — it is that ccx would run a real subprocess
   and **fault `rc=201` (convergence) on a dummy mesh**, i.e. garbage-in; even a *green* solve on a
   10-byte dummy STEP / hardcoded dummy `.inp` is dummy-fidelity (Tier 0), never a validation. This
   correction is recorded going forward; per the honesty contract, prior commits are NOT rewritten.
2. **`agents/human_fallback.py` imports `app.well_harness.notion_sync`** and fires a real
   `NotionRunRegistrar` writeback + `interrupt()`. So importing **`agents.graph`** transitively pulls
   backend (Notion) code into the agent-layer import closure, and *running the full graph* would
   produce a **non-revertible Notion side-effect** on the fault-recovery path. Importing
   **`agents.architect` alone pulls none of it** (verified: `well_harness` not in `sys.modules`).
3. **`agents.architect` authors a `SimPlan` only with an LLM key**; keyless it returns
   `fault_class=unknown` with **no plan**. So "the graph node EXECUTED" and "the graph node AUTHORED
   content" are **distinct facts** that must be surfaced separately — conflating them would be a
   fabricated agentic claim. (Confirmed by a real keyless `.invoke()` of a truncated graph:
   `plan=None`, `fault_class=unknown`, `history` len 1 — the reducer fired on the identity seed.)

Additional verified constraint: LangGraph's Pregel runner executes a node's **successor before
yielding**, so one cannot "stop the stream after architect" on the full graph — `geometry.run` would
already raise `ValueError("SimState is missing a SimPlan")` keyless. A **dedicated truncated graph**
is therefore the only safe minimal shape.

---

## Decision

Wire the LangGraph compiled-graph runtime behind the live pipeline **incrementally, behind a
dedicated truncated graph**, never by invoking the full `agents.graph.compile_graph()` until the ccx
and Notion side-effects are isolated. The non-negotiable invariants (all from the parent ADRs):

- **ADR-015 holds:** only `agent_facade.py` imports `agents.*`; `mock_pipeline.py` reads only
  already-projected `StageState` wire metrics; the SimState↔StageState projection lives in the agent
  layer; the agent-layer runner imports `agents.architect` directly, **never** `agents.graph`.
- **Honesty does not regress:** N/13 stays keyed PURELY on `StageProvenance`; **no 4th provenance
  value** (the FE `asProvenance()` would downgrade an unknown value to `scripted_demo` and *decrease*
  N/13, and would falsely imply graph-driven is a higher trust class than rule-based logic). The
  graph-execution fact rides **metrics** (`graphNodeRan` / `graphNodeProducedPlan` / `graphRunner`)
  + an honest disclosure — mirroring how `StageFidelityTier` rides metrics off the provenance axis.
- **"Node ran" ≠ "node authored content":** the projection branches on plan-presence and discloses
  which produced the stage text.
- **Claim tier:** a graph-driven run is **Tier 0** (P0, sandbox wiring proof) rising to at most
  **Tier 1** (full graph on dummy-fidelity inputs); **never Tier 2** (signed benchmark, deferred).

### Node→stage mapping (the granularity gap; consensus across all 3 proposals)

The 7 nodes fan out many-to-one onto the 13 stages, keyed on each node's SimState-delta: architect →
{PROJECT_INTAKE, MATERIAL_ASSIGNMENT, BOUNDARY_CONDITIONS, LOAD_CASES}; geometry → {CAD_IMPORT,
GEOMETRY_VALIDATION}; mesh → {MESH_GENERATION, MESH_QUALITY_CHECK}; solver → {SOLVER_RUN,
CONVERGENCE_MONITORING}; viz → {POST_PROCESSING, RESULT_ANALYSIS, REPORT_GENERATION}; reviewer → a
routing OVERLAY on RESULT_ANALYSIS (reuse `decide_route`/`decide_recovery`); human_fallback → a
run-level terminal disclosure, never a 13-stage slot. A node whose delta is absent/faulted leaves its
stages at the `scripted_demo` default — **never fabricated**. A node is credited as content-author
ONLY when its delta actually carried the field a stage projects.

### Phased roadmap (dependency-gated, NOT calendar-gated)

- **P0 (this slice, LANDED behind `workflow_graph_intake=False`):** a dedicated truncated
  `START→architect→END` graph, compiled and `.invoke()`d, drives PROJECT_INTAKE. Proves the
  compiled-graph RUNTIME (not a direct `architect.run`) drives one live stage. Plan-presence-branched
  dual disclosure. N/13 provably unchanged. No downstream node, no ccx, no Notion.
- **P1:** extend the dedicated subgraph to architect→geometry (GEOMETRY_VALIDATION via the existing
  `geometry_dummy_exec_to_stage_state` tier_0_dummy projector). First cross-node graph data
  dependency. Introduce the run-level `graphDriven` qualifier + the machine-checkable invariant
  `stagesAuthored == provenanceCoverage.agentDriven`. (Geometry needs a SimPlan → P1 either opts into
  the LLM architect OR seeds the plan deterministically from `analyze_intake`/`analyze_geometry_plan`,
  disclosing which.)
- **P2:** add mesh (MESH_GENERATION, MESH_QUALITY_CHECK). `check_mesh_quality` is a real numpy
  measurement but of dummy geometry → tier_0_dummy with a new `dummyFidelityInputs=True` guard.
- **P3 — SOLVER ISOLATION GATE (blocking):** before any solver node runs in the backend:
  `workflow_graph_solver` flag default-off; an honest "ccx attempted on the dummy mesh and FAILED at
  **deck parse** (rc=201; no `Nall/Nfix/Eall` sets) — or **preflight-failed** when ccx is absent;
  **not numerical divergence**" disclosure; `dummyFidelityInputs=True` hard-blocks any Tier-1/2
  implication even on a green solve. *(As-landed; see "P3 — what landed".)*
- **P4 — HUMAN_FALLBACK / NOTION ISOLATION GATE (blocking):** before wiring the full
  `compile_graph()`, inject a no-op/test-double `NotionRunRegistrar` OR a settings flag that disables
  the Notion side-effect for graph-driven runs, plus a checkpointer for `interrupt` resumption.
- **P5:** `stream()`-driven live Monitor over the full 7-node graph with per-tick RUNNING synthesis;
  `mock_pipeline` graph-replay branch behind `workflow_graph_driven`. Only safe AFTER P3 + P4.

---

## P0 — what landed (additive, flag-off, reversible)

- `agents/graph_runner.py` (NEW): `build_intake_graph()` (dedicated truncated `StateGraph(SimState)`,
  architect-only, imports `agents.architect` directly) + `run_intake_via_graph(...)` (seeds a hermetic
  SimState with reducer-identity `history=[]`/`retry_budgets={}`, `.invoke()`s in a try/except that
  degrades to the deterministic intake projection on any runtime error).
- `agents/state_projection.py`: `graph_intake_to_stage_state(final_sim_state, ...)` — branches on
  plan-presence; reuses `sim_state_to_stage_state` (plan → llm_agent) or `analyze_intake` +
  `intake_outcome_to_stage_state` (no plan → deterministic_agent); stamps
  `graphNodeRan`/`graphNodeProducedPlan`/`graphRunner` + dual disclosure WITHOUT changing provenance.
- `backend/app/workbench/agent_facade.py`: `run_node_via_graph(...)` (sole `agents.*` importer;
  imports `agents.graph_runner`; never `schemas.sim_state`). Only PROJECT_INTAKE wired; others raise.
- `backend/app/core/config.py`: `workflow_graph_intake: bool = False` (mirrors `workflow_real_solver`).
- `backend/app/services/workflow/mock_pipeline.py`: one flag-gated branch in `_build_stage_state`'s
  PROJECT_INTAKE path (lazy facade import; no `agents.*` import).
- `backend/tests/test_graph_intake_wiring.py` (NEW): the compiled-graph runtime ran (invoke-spied);
  keyless → `graphNodeProducedPlan=False` + honest disclosure; plan-present → llm_agent; N/13
  identical flag on vs off; flag-off byte-identical default; no downstream node executes; reducer
  identity seed; graph_runner does not import `agents.graph` (AST-checked).

---

## P3 — what landed (additive, flag-off, reversible) — 2026-06-08

**SOLVER ISOLATION GATE closed.** `workflow_graph_solver=False` (default) gates SOLVER_RUN through a
new truncated `architect→geometry→mesh→solver` compiled graph — **the first graph to launch a real
`ccx` subprocess from the runtime**. **Open-Question #5 is RESOLVED: attempt a real ccx run** (the
`hard_skip` alternative carries the identical honesty envelope with zero north-star value). Two
empirical facts (re-verified this session, incl. a guarded real-ccx test):

1. The solver node consumes the mesh node's hardcoded **4-node/1-tet C3D4 fallback mesh** (no gmsh
   kernel) and really invokes ccx, which **FAILS by construction** — the dummy mesh defines no
   `Nall/Nfix/Eall` sets, so a ccx-present host fatal-errors at deck parse (**`rc=201`**, classified
   `solver_convergence` ONLY via the driver's `returncode!=0` catch-all — a known driver limitation,
   **NOT numerical divergence**), and a ccx-less host `PREFLIGHT_FAIL`s. Either way **no solve occurs**.
2. The wiring fact is the **`solver` history entry** (`any(h['node']=='solver')`) — NOT a tautological
   `fault_class` key (the seed sets it unconditionally), NOT `frd_path` (absent on a faulted solve).

**Honest correction to the synthesized design (documented per the honesty contract, not score-gaming):**
the design draft (`.planning/ADR029_P3_SOLVER_GATE_DESIGN.md`) projected the faulted solver as
`status=WARNING` and let the pipeline **continue**, claiming **N/13 +1**. Ground-truthing the actual
code refuted this: the scripted `CONVERGENCE_MONITORING` spec asserts **`converged=True`** and the
downstream stages fabricate stress results, so a faulted-solver-then-continue would render an
internally **contradictory** narrative ("solve rejected → converged → here are your results"). The
implemented design instead:

- projects SOLVER_RUN **`status=FAILED`** (never green; mirrors the real-LE10 solve-failure
  projection + Codex M4 R0 P2 "a failed solve is never a plain green success"), `tier_0_dummy` with
  `dummyFidelityInputs=True`, `solverRan=False`, and `graphNodeRan=True` always — but
  `ccxSubprocessLaunched`/`solverAttempted` ride **returncode-present** (true only for the
  `_failed_solve` rc=201 path; **false** for `_preflight_failure`/`_unsupported_backend_failure`/
  `_solver_syntax_failure`, where the node ran but ccx never launched — Codex R0 P1), **zero**
  measurement keys
  (anti-vacuous-pass, machine-checked against `_SOLVER_MEASUREMENT_KEYS`), empty artifacts, a
  disclosure stating the TRUE cause (deck-parse/preflight, the catch-all mislabel) authored from
  static knowledge (never the ccx banner `****`), and provenance `deterministic_agent` (**no 4th
  value**);
- **HALTS the pipeline** at the faulted solver (`break`, the physically-correct behavior — a rejected
  deck cannot be convergence-monitored / post-processed), so downstream stays **PENDING** and **no**
  `converged=True`/results/safety-factor are ever fabricated;
- consequently **N/13 is ~unchanged (net ≈ 0)**, NOT +1: SOLVER_RUN gains `deterministic_agent`, but
  the halt means the downstream RESULT_ANALYSIS routing is not reached. **The deliverable is the
  wiring proof + the honest halt, NOT a coverage increase** (mirrors P-geomrun's framing).

**L2 correctness fix (folded in, verified):** `_build_stage_state` is called ~4×/stage in `_advance`
(3 `_PROGRESS_TICKS` + terminal), so routing ccx through that per-tick seam would fire ~4 subprocesses
synchronously on the event loop. The graph-solver therefore runs **once**, off-thread via
`asyncio.to_thread` in `_advance` (mirroring the real-LE10 `_run_real_le10` convention), via a new
`MockWorkflowStore._run_graph_solver` helper — never in the per-tick seam. `workflow_real_solver` wins
when both flags are on (the `not real` predicate suppresses the graph-solver; the LE10 Tier-1 path owns
SOLVER_RUN). The dropped design claims (a fictitious "60s SolveOptions timeout"; a `self._graph_solver_st`
cache the M2 path doesn't need since the graph-solver feeds no downstream stage) are noted here.

- **Files:** `backend/app/core/config.py` (`workflow_graph_solver`) · `agents/graph_runner.py`
  (`build_intake_geometry_mesh_solver_graph` + `run_solver_via_graph`) · `agents/state_projection.py`
  (`graph_solver_to_stage_state` + `_SOLVER_MEASUREMENT_KEYS`) · `backend/app/workbench/agent_facade.py`
  (SOLVER_RUN branch) · `backend/app/services/workflow/mock_pipeline.py` (`_run_graph_solver` + the
  HALT in `run_sync`/`_advance`/`run_one_stage`) · NEW `backend/tests/test_graph_solver_wiring.py` (20
  tests incl. a `skipif`-guarded REAL-ccx subprocess test). 49/49 graph-wiring tests green; the 11
  pre-existing suite failures (API 404s / NL-parser / KB-linkage) are unrelated (verified by stash).
  `CONVERGENCE_MONITORING` stays scripted (no separate graph node; it is simply never reached).

---

## Consequences

- **Positive:** the orphaned graph machinery now genuinely touches the live runtime (the ADR-028
  north star), via the smallest honest, reversible step. Establishes the node-ran-vs-authored honesty
  primitive and the dedicated-truncated-graph pattern that the dependency-gated later phases reuse.
  Default-off ⇒ zero blast radius on the contract suite.
- **Negative / cost:** end-user value of P0 is ~zero (PROJECT_INTAKE was already deterministic_agent;
  only its *driver* changed). Value is architectural. The full graph-driven runtime is gated behind
  real isolation work (P3 ccx, P4 Notion) that prior naive designs missed.
- **Risk register (carried):** false-hermeticity (ccx present → P3 gate); non-revertible Notion
  side-effect (P4 gate); silent-fabrication fork (resolved by plan-presence branch); reducer-identity
  crash (resolved by `[]`/`{}` seed); vacuous-pass test (resolved by invoke-spy + genuine keyless
  path); async `_advance` blocking on synchronous `.invoke` (low for 1-node intake; flagged for P5).

## Open questions for ratification (genuine owner decisions)

1. **Ratify ADR-029** as the graph-wiring roadmap (extends ADR-028), or request a dual-blind Codex
   second opinion on the P3/P4 isolation gates first?
2. **Replace-vs-parallel default:** P0 runs alongside `mock_pipeline` behind a default-off flag.
   Long-run intent — augment-then-flip (graph becomes the per-stage default as each phase proves out)
   vs permanent parallel paths? (Sets whether the flag eventually defaults True.)
3. **Notion isolation (P4):** should a graph-driven run EVER create Notion review tasks, or is that
   dev-harness-only (→ disable the side-effect for graph-driven runs)?
4. **No 4th provenance value:** confirm the graph-execution fact lives ONLY in metrics + the run-level
   `graphDriven` qualifier, never in `StageProvenance`. (The single most important irreversible
   semantic choice.)
5. **P3 solver gate:** should the graph-driven solver ever attempt a real ccx run on dummy data
   (honest disclosure), or hard-skip the solver node until a real (LE10-class) mesh is wired? —
   **RESOLVED 2026-06-08 (see "P3 — what landed"): attempt a real ccx run.** The failed solve is
   projected FAILED `tier_0_dummy` and HALTS the pipeline (no downstream fabrication). The failure is
   a **deck-parse** rejection (rc=201; no `Nall/Nfix/Eall` sets) when ccx is present, or a
   **preflight** failure when absent — **NOT numerical divergence**; and "solver node ran" is held
   distinct from "ccx subprocess launched" (`ccxSubprocessLaunched`/`solverAttempted` ride the
   returncode, so a preflight/unsupported fault never over-claims an attempted solve — Codex R0 P1).
   `dummyFidelityInputs=True` hard-blocks any Tier-1/2 implication. Reversible (flag-off default), so
   no separate owner gate was required beyond the standing "ultracode 全权授权"
   directive + the mandatory Codex relay review.
