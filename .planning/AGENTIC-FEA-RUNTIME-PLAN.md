# Agentic FEA Workflow Runtime — Implementation Plan

> Status: **DRAFT — awaiting path ratification** (see §0.3). Author: Opus 4.8 (总工).
> Date: 2026-06-03. Grounded by a 6-agent read-only recon of the repo + Trigger.dev research.
> This is a plan, not code. No production code is written until the path in §0.3 is chosen.

---

## 0. Executive summary & the two findings that change the request

### 0.1 The big finding: ~80% of the requested runtime **already exists — in Python**

The repo is NOT a blank slate. It already contains the bones of a staged, durable, resumable,
observable workflow runtime — built but **not wired together**:

| Requested capability | Already exists (where) | State |
|---|---|---|
| Staged pipeline (intent→geometry→mesh→solver→review→handoff) | `agents/graph.py` LangGraph `StateGraph` (architect→geometry→mesh→solver→reviewer→viz/human_fallback) | Built, **not connected to the FastAPI app** — invoked only from tests/demos |
| Per-run durable state | `schemas/sim_state.py` `SimState` TypedDict (run_id, plan, artifacts, `fault_class`, `retry_budgets` reducer, `history` reducer) | Built, in use by the graph |
| Stage-lifecycle **event protocol** | `schemas/ws_events.py` (ADR-014): 12 typed events — `run.started`, `node.entered/progress/exited`, `artifact.ready`, `reviewer.verdict`, `handoff.required`, `run.finished`; `Stage = intent\|geometry\|mesh\|solver\|review\|handoff` | **Schema complete + tested, but NO emitter exists.** `backend/app/runtime/{event_bus,langgraph_callbacks,ws_runs}.py` are the ADR-014 "Phase 2.0 deferred" — unbuilt |
| Recoverability / checkpoint / human-gate | `persistence/checkpointer.py` `SqliteSaver` (`runs/checkpoints.sqlite`) + `agents/human_fallback.py` `interrupt()` | Built, tested (resume-after-interrupt) |
| **Pluggable solver adapter** | `aeron/protocols/fea_backend.py` `FEABackend` `@runtime_checkable` Protocol (`prepare_case`/`solve`/`parse_results`/`health_check`); concrete `CalculiXFEABackend` + `OpenRadiossFEABackend` | Built, tested — exactly the §6 adapter the request asks for |
| Mock seam | `SolveOptions.dry_run=True` short-circuits the subprocess and returns a valid `SolveOutcome` | Built (but no full synthetic-artifact `MockFEABackend` yet) |
| Stage orchestrator prototype | `backend/app/well_harness/task_runner.py` (execute→parse→report→verify→persist, `HarnessRunStatus`, per-run JSON bundle under `project_state/runs/<case>/<run_id>/`) | Built, CLI-only |
| Live log streaming | `backend/app/services/solver.py` + WS `/api/v1/solver/ws/logs/{job_id}` | Built (in-memory, single-process) |
| Frontend stage-progress primitives | `SolverProgressPanel` + `solverProgress.ts` (log→%); `useSensitivityStudy` (start→poll→complete); `useUploadErrorRecovery`+`ErrorCard`; `*Client.ts` fetch pattern; CSS design tokens; Cmd-K palette | Built, tested |

**The missing 20%** = (a) the WSEvent **emitter** layer (specced in ADR-014, never built);
(b) wiring a runtime into the **HTTP API** + a **Monitor UI**; (c) a real `MockFEABackend`;
(d) the "agentic explanation / nextAction" layer the request adds on top.

### 0.2 The correction the request needs: **Trigger.dev v3 is end-of-life**

- Trigger.dev **v4** is GA (2025-08-18). **v3 new deploys are blocked from 2026-04-01; all v3 runs stop 2026-07-01.** Building on v3 today is building on a dead runtime.
- → **Use Trigger.dev v4** (`@trigger.dev/sdk`, not `@trigger.dev/sdk/v3`). Every v3 task pattern in the request maps to v4 (`task()` + retry, `triggerAndWait` + `idempotencyKeys`, `wait.createToken/forToken`, `metadata.set/parent.set`, `useRealtimeRun`).
- **The枢纽 constraint (confirmed):** Trigger.dev is TypeScript/Node. The solver is Python (FastAPI + `ccx` subprocess). Trigger.dev **cannot "wrap each stage" natively** — a Trigger.dev task is TS code that *orchestrates* Python work. The two viable bridges:
  - **HTTP-callback (`wait.createToken`/`wait.forToken`)** — the TS task creates a webhook URL, calls FastAPI, and the run *truly suspends* (no thread/poll) until FastAPI POSTs the result back. Works on self-host. **Best for minutes-long ccx solves.**
  - **`@trigger.dev/python` subprocess** — Python ships in the task's container, run via `python.stream.runScript()`. Simpler, but couples the Node image to ccx/gmsh and grows it large.

### 0.3 The one decision that's yours (it changes execution order)

Given that a Python durable runtime already exists AND Trigger.dev is a second runtime in a second
language, "where + when does Trigger.dev sit" is a genuine product/architecture fork:

- **Path A — Trigger.dev v4 from day 1.** The orchestrator is a Trigger.dev TS service from Phase 1, even for the Mock pipeline. Pro: target architecture immediately; hosted dashboard/realtime/durability for free. Con: stand up TS package + (self-host) Postgres/Redis/object-store before you see a single pixel; two orchestration runtimes coexist (LangGraph + Trigger.dev).
- **Path B — Mock-first in pure Python, Trigger.dev v4 in Phase 2 (RECOMMENDED).** Phase 1 builds the missing ADR-014 emitter + Mock runtime + Monitor UI on the **existing** Python protocol — **zero new language, zero infra, fastest to "可视化流程"**. Phase 2 introduces Trigger.dev v4 as the **outer durable orchestrator** calling the proven Python stages via HTTP-callback. This is exactly your stated strategy ("先 Mock Runtime 先可视化 → 再 Industrial Solver") and avoids a premature two-headed system. Trigger.dev is still delivered — just after the stage contract is proven.
- **Path C — No Trigger.dev; finish the Python-native runtime.** The repo already has the bones; build the emitter + API + UI on LangGraph+SqliteSaver and stop. Pro: simplest, one runtime. Con: drops the explicit Trigger.dev requirement; reinvents durability/dashboard/multi-tenant that Trigger.dev gives free.

**总工 recommendation: Path B.** It honors your Trigger.dev requirement, honors your own "Mock-first"
strategy, reuses the most existing code, and defers infra until it earns its place.

### 0.4 DECISION (2026-06-03, ratified by user)

- **Path A chosen** — Trigger.dev v4 is the orchestrator from Phase 1 (it drives even the Mock pipeline).
  Milestones below are re-sequenced for Path A: Trigger.dev enters at **M2** (was M4 under Path B).
- **Deployment: deferred to M4** (not locked now). Reconciliation of "Path A from day 1" + "don't lock
  deployment": the **dev loop runs `npx trigger.dev dev` against the Cloud free-tier scheduler using ONLY
  synthetic Mock data in Phase 1** — no proprietary CAD touches it, so there is no data-residency exposure
  while iterating. The **production** topology (Cloud vs self-host Docker) is decided at M4 when the real
  solver + real data arrive. Self-host remains the likely prod end-state for proprietary CAD.
- Consequence to design around now: every contract (StageState / WSEvent / FEABackend) is defined so the
  same Python stage code runs identically whether the dev scheduler is Cloud or self-host.

---

## 1. Existing architecture summary (recon result)

**Backend** — FastAPI monolith (`backend/app/main.py`, ~30 routers under `/api/v1`), Python 3.11,
SQLAlchemy-async + SQLite (`structural_workbench.db`). **Two parallel solver paths**: (A) `SolverService`
(`services/solver.py`) — async `create_subprocess_exec` to `ccx`, in-memory job dict, WS log fan-out;
(B) `tier2_pipeline.py` / `CalculiXRunner` — blocking `subprocess.run`, stage-named `Tier2PipelineError`,
used by all 13+ cross-check runners. Path A has live logs but loses state on restart; Path B has no HTTP
surface. The **LangGraph DAG** (`agents/graph.py`) and **well-harness** (`well_harness/task_runner.py`)
are both real staged orchestrators but **neither is wired into the API** (`backend/app/workbench/__init__.py`,
the sanctioned ADR-015 bridge, is an empty stub).

**Solver/adapters** — `FEABackend` Protocol (`aeron/protocols/fea_backend.py`) is the clean pluggable seam
(4 methods). Two ccx subprocess layers exist and are **not unified**: `tools/calculix_driver.run_solve()`
(dict, used by AERON) vs `backend/app/adapters/calculix/runner.CalculiXRunner` (dataclass, used by
cross-check runners). `FaultClass` enum (8 values) drives retry routing. Signed-registry guard
(`^GS-\d{3}$`) hard-stops solves in two places (but **not** in well-harness — a gap).

**Frontend** — React 19 + Vite + TS SPA, **no router** (tab-based: `activeTab` in `App.tsx`, pinned <1500 LOC),
local `useState` + custom hooks (no Redux/Query/SWR). Talks to backend via bare `fetch` to hardcoded
`http://localhost:8000/api/v1` + one WS for solver logs. Viz = hand-rolled Three.js viewport
(`ResultMeshWebGLViewport`) + a Plotly `<iframe>` + inline-SVG sparklines. **No node-graph library.**
Reusable: `SolverProgressPanel`, `useSensitivityStudy`, `useUploadErrorRecovery`/`ErrorCard`, `*Client.ts`,
CSS tokens, Cmd-K palette.

**Build/CI** — monorepo, **no server-side Node** (Node = SPA build + Electron shell only). uvicorn :8000,
Vite :5173. CI (`ci.yml`) one job: ruff + pytest(xvfb) + `tsc -b` + eslint(≤70) + vitest; required checks
also `calibration-cap-check`, `trailer-check`, `golden-samples-validation`. Docker `p1-base` image (ccx +
FreeCAD + gmsh) exists but isn't used in the main CI job. Commit trailers enforced.

---

## 2. Minimal Trigger.dev v4 integration plan (the target topology)

Recommended topology (Trigger.dev research "Option D + Option B"):

```
React <—useRealtimeRun(orchRunId, accessToken)—  Trigger.dev v4 Cloud/self-host
  │                                                   │
  │  POST /api/v1/workflow/trigger ──────────────────►│ feaPipelineOrchestrator (TS task)
  │  ◄── { orchRunId, publicAccessToken }             │   for stage in 13 stages:
  │                                                    │     await stageTask.triggerAndWait(
  │                                                    │        {jobId, stage}, {idempotencyKey})  ← passed stages not re-run
  │                                                    │     stageTask:
  │                                                    │        token = wait.createToken({timeout:'2h'})
  │                                                    │        fetch FastAPI /workflow/stage/run {callbackUrl: token.url}
  │                                                    │        result = await wait.forToken(token)   ← run SUSPENDS during ccx
  │                                                    │        metadata.parent.set(stage, status, progress, metrics…)
  ▼                                                    ▼
FastAPI  ──runs Python stage (Mock or real FEABackend)──► POST token.url with StageState result
```

**Net-new code (small, thin):**
- `trigger/` — a new TS package (outside `frontend/` to avoid the eslint-70 ceiling): `trigger.config.ts`,
  `src/orchestrator.task.ts`, `src/stages/*.task.ts` (or one generic `stage.task.ts` parameterized by stage).
- FastAPI `backend/app/api/routes/workflow.py` — `POST /workflow/trigger` (mints orchRun + public token,
  returns them), `POST /workflow/stage/run` (executes one stage, POSTs `StageState` to `callbackUrl`),
  `GET /workflow/runs/{id}` (read model for the non-Trigger path / fallback).
- `backend/app/runtime/` — the ADR-014 emitter (see §3), shared by Mock and real, Trigger and non-Trigger.

**Min-change principle:** Trigger.dev tasks stay thin. The **contracts** are the existing Pydantic models —
`SimPlan` (input), `StageState`/`WSEvent` (progress), `FEABackend`/`SolveOutcome` (solver I/O). Trigger.dev
adds durability + realtime + dashboard; it does **not** own domain logic.

**Deployment (decision Q2):** Cloud (zero infra, warm starts, CRIU true-suspend; data leaves the machine) vs
self-host Docker Compose (Postgres + Redis + object store + SMTP; data stays on-prem; `wait.forToken` still
true-suspends in Postgres without CRIU). For an FEA tool with possibly-proprietary CAD, self-host is the
likely end state; **Cloud is far faster for the M4 spike** — recommend spike on Cloud, plan self-host for prod.

---

## 3. Workflow state schema (reuse + extend, do NOT invent a parallel one)

**SSOT = one Pydantic model, `schemas/workflow_state.py`, that EXTENDS the existing ADR-014 vocabulary.**
The request's per-task JSON maps onto it 1:1; the frontend gets a mirrored TS type (`frontend/src/types/WorkflowTypes.ts`, generated/hand-mirrored like the existing `*Client` types).

```python
# schemas/workflow_state.py  (Python SSOT; TS mirror in frontend)
class WorkflowStage(StrEnum):           # the 13 requested stages (finer than ws_events.Stage's 6)
    PROJECT_INTAKE; CAD_IMPORT; GEOMETRY_VALIDATION; MATERIAL_ASSIGNMENT; BOUNDARY_CONDITIONS;
    LOAD_CASES; MESH_GENERATION; MESH_QUALITY; SOLVER_RUN; CONVERGENCE_MONITOR;
    POST_PROCESSING; RESULT_ANALYSIS; REPORT_GENERATION
    # NOTE: map each to the coarse ws_events.Stage (intent/geometry/mesh/solver/review/handoff) for back-compat

class StageStatus(StrEnum):             # aligns with HarnessRunStatus + frontend JobStatus
    PENDING; RUNNING; SUCCESS; WARNING; FAILED

class StageState(BaseModel):            # == the request's per-task JSON, typed
    run_id: str                         # reuse SimState.run_id format {case}_{ISO8601}
    stage: WorkflowStage
    status: StageStatus
    progress: float = 0.0               # 0..1
    current_object: str | None          # "bracket_hole_region"
    description: str                     # human-facing, zh ok
    metrics: StageMetrics               # nodes/elements/badElements/maxAspectRatio/minJacobian/estimatedSolveTime…
    warnings: list[str] = []
    errors: list[StageError] = []       # carries FaultClass (existing enum) per error
    artifacts: StageArtifacts           # geometryPreview/meshPreview/resultPreview/logFile/reportFile (paths/urls)
    agent_explanation: str              # NEW agentic layer — what/why/found/suggest
    next_action: str                    # NEW — recommended next step / remediation
```

- **Events**: keep `schemas/ws_events.py` as the wire protocol; a `StageState` change emits the matching
  `NodeEntered/NodeProgress/NodeExited/ArtifactReady` event. No new event types needed for MVP.
- **Persistence**: reuse `well_harness/project_state.py` bundle layout (`project_state/runs/<case>/<run_id>/`)
  + add a per-stage `stage_<name>.json`. The `SimulationJob` ORM row gains a `trigger_run_id` column (Path B)
  to correlate with Trigger.dev runs.
- **Metrics/artifacts** reuse `CalculiXRunResult` fields (frd/dat/log paths, runtime_sec) and the FRD reader.

---

## 4. Mock FEA pipeline (Phase-1 deliverable, no real solver)

- **`MockFEABackend`** implementing the `FEABackend` Protocol (the recon flagged: nothing beyond `dry_run`).
  Returns **synthetic but plausible** artifacts: a small fake `.frd`/result-mesh payload, fake metrics
  (nodes/elements/badElements/aspectRatio/jacobian), and—critically—**injectable warnings/failures** so the
  Monitor's `warning`/`failed`/`nextAction` paths are exercised (e.g. "mesh_quality: 142 bad elements at
  bracket_hole_region → suggest local refinement").
- **`MockPipelineRunner`** walks all 13 `WorkflowStage`s, emitting `StageState`/`WSEvent` per stage with
  realistic timing, reusing the well-harness execute→…→persist decomposition. One config flag injects a
  failure at a chosen stage to demo recovery + `agent_explanation`/`next_action`.
- Same runner drives Mock and (later) real — only the `FEABackend` impl swaps. The orchestrator (Python in
  Path B M2; Trigger.dev in M4) calls this runner.
- **Each stage independently testable** (request §9): every stage = a pure function `(StageInput) -> StageState`.

---

## 5. Workflow Monitor UI (Phase-1 deliverable)

- **Mount**: a 4th tab in `App.tsx` (widen `activeTab` union → add `'workflow'`; add a `TabButton`; render a
  new `WorkflowMonitorPanel` peer of `VisualTabPanel/...`). No router. Add a Cmd-K command "Open Workflow Monitor".
- **Layout** (request §4): left = **stage node-graph**; center = previews (reuse `ResultMeshPlaybackPanel`
  for mesh/stress/displacement + the Plotly `<iframe>` for contours); right = **agent-explanation log**
  (renders `agent_explanation`/`next_action` per stage); bottom = **timeline + warnings + errors + artifact
  downloads**. Each node shows `pending/running/success/warning/failed`.
- **Node graph**: the 13 stages are essentially linear → **hand-rolled inline-SVG stepper-DAG** in the existing
  sparkline idiom (zero new dep). (Decision: add `react-flow` only if a true branching DAG view is wanted later.)
- **Data**: `useWorkflowRun(runId)` hook mirroring `useSensitivityStudy` (start→poll→complete) +
  `workflowRunClient.ts` mirroring `convergenceStudyClient.ts`. Path B M3 polls `GET /workflow/runs/{id}`;
  Path B M4 swaps to `useRealtimeRun` from `@trigger.dev/react-hooks` (the hook boundary is the only change).
- **Reuse**: `SolverProgressPanel`+`parseSolverProgress` per stage; `ErrorCard`+`useUploadErrorRecovery` for
  failures; CSS tokens; keep `App.tsx` under the <1500 LOC pin by extracting all state into the hook.
- **Honesty**: status is computed from real `StageState` (never optimistic); failures surface `FaultClass` +
  `next_action`; "Mock" runs are badge-labeled so a demo is never mistaken for a real solve.

---

## 6. Tests + docs

- **Backend**: per-stage unit tests (13); `MockPipelineRunner` E2E (happy path + injected failure → warning/
  failed surfaces + correct `next_action`); WSEvent emitter tests; `StageState`/`WorkflowStage`↔`ws_events.Stage`
  mapping test. Honor `requires_solver` marker (mock tests need no binary → run in CI).
- **Frontend**: vitest for `useWorkflowRun`, `workflowRunClient`, `WorkflowMonitorPanel` (jsdom; mock the
  poll/realtime transport). A behavioral test per the existing `test/Phase<N>*.test.tsx` convention.
- **Trigger.dev (M4)**: vitest in `trigger/`; a task-level test that the orchestrator fans out 13 stages with
  idempotency keys and relays metadata.
- **Docs**: `docs/workflow-runtime/README.md` — run the Mock pipeline, open the Monitor, env vars, the
  `StageState` schema, and (M4) the `npx trigger.dev dev` loop + deployment notes.
- **Guards to respect**: `App.tsx` <1500 LOC pin; ruff (note `backend/` is excluded — new Python under
  `backend/` won't be linted, decide whether to fix the exclude); eslint ≤70; commit trailers; **enforce the
  signed-registry `^GS-\d{3}$` guard in the new workflow path** (the well-harness gap the recon flagged).

---

## 7. Real solver接入 (Phase-2+, after Mock + Monitor proven)

- Swap `MockFEABackend` → `CalculiXFEABackend` (**already exists**). Stage contract unchanged. The
  `wait.forToken` HTTP-callback wraps the real (minutes-long) ccx run so the Trigger.dev run truly suspends.
- **Unify the two ccx subprocess paths** (`calculix_driver` vs `CalculiXRunner`) behind the `FEABackend`
  adapter — pay down the divergence the recon flagged.
- **More solvers** = implement `FEABackend` (Code_Aster / Abaqus / Ansys / custom Python kernel); the Protocol
  + adapter stub dirs (`backend/app/adapters/{ansys,abaqus,nastran}/`) already exist.
- **Worker image**: the `p1-base` Docker image (ccx+gmsh+FreeCAD) becomes the Trigger.dev worker image (self-host)
  or the FastAPI solver container (HTTP-callback). **Artifact storage** → object store (local absolute paths in
  `control_plane_sync.json` aren't portable to distributed workers).
- **Convergence/post-processing**: the recon flagged `parse_results` returns raw paths only (by ADR-001 design);
  von Mises/principal/safety-factor derivation (request §7) needs the Layer-3 domain step fleshed out
  (`stress_derivatives` referenced but unverified).

---

## 8. Carried risks / constraints (from recon — must be designed around)

1. Two divergent ccx subprocess paths — unify behind `FEABackend` (M5).
2. In-memory `SolverService.jobs` loses state on restart — Trigger.dev/durable store fixes it.
3. Signed-registry guard missing in well-harness path — add it to the new runtime.
4. `App.tsx` <1500 LOC pin — extract all new state to hooks.
5. No auth — Trigger.dev needs an API key/public token; inject via Electron preload or `VITE_` build var.
6. Local absolute artifact paths — move to object store before distributed workers.
7. `backend/` excluded from ruff; `requirements.txt`(pinned old) vs `pyproject.toml`(>=) divergence.
8. `OPENAI_API_KEY` needed for the LLM agents (architect/reviewer/viz) — optional today; Trigger.dev env secret.
9. Self-host Trigger.dev = Postgres + Redis + object store + SMTP; size workers for blocking self-host waits.

---

## 9. Milestones (dependency-ordered, no date gating — **Path A, ratified**)

- **M0** — ✅ Ratify path + deployment (§0.4). Done 2026-06-03.
- **M1 — Python contracts + Mock substrate** (path-independent foundation Trigger.dev will call):
  - `schemas/workflow_state.py` (`WorkflowStage` ×13, `StageStatus` ×5, `StageState`/`StageMetrics`/
    `StageArtifacts`/`StageError`, camelCase wire aliases matching the request JSON, mapping to the
    existing `ws_events.Stage`/`FaultClass`). **← first commit (this turn).**
  - `backend/app/runtime/` WSEvent emitter (the ADR-014 deferred layer: event_bus + emit helpers).
  - `MockFEABackend` (synthetic artifacts/metrics, injectable warning/failure) + `MockPipelineRunner`
    (all 13 stages, emits StageState/WSEvent) + per-stage tests.
  - `GET /api/v1/workflow/runs/{id}` read surface.
- **M2 — Trigger.dev v4 orchestration** (the chosen Phase-1 orchestrator):
  - `trigger/` TS package: `trigger.config.ts`, `feaPipelineOrchestrator` task, generic `stage.task.ts`
    (idempotencyKeys so passed stages don't re-run), `wait.createToken`/`wait.forToken` HTTP-callback.
  - FastAPI `POST /api/v1/workflow/trigger` (mint orchestrator run + public access token) +
    `POST /api/v1/workflow/stage/run` (execute one Mock stage, POST `StageState` to `callbackUrl`).
  - `npx trigger.dev dev` loop wired; Mock pipeline now driven end-to-end by Trigger.dev v4 (Cloud
    free-tier scheduler, synthetic data per §0.4).
- **M3 — Workflow Monitor UI** (4th `App.tsx` tab): node-graph + previews (reuse `ResultMeshPlaybackPanel`
  + Plotly iframe) + agent-explanation log + timeline; `useRealtimeRun` from `@trigger.dev/react-hooks`
  (fallback `useWorkflowRun` poll); frontend tests. **← first "可视化流程" demo.**
- **M4 — Real CalculiX + prod deployment** — swap `MockFEABackend`→`CalculiXFEABackend`; unify the two ccx
  subprocess paths; worker containerization (`p1-base`); object-store artifacts; **decide Cloud vs self-host**;
  flesh out adapter stubs (Code_Aster/Abaqus/Ansys/custom).

Each milestone: small atomic commits, `confidence:` trailer. **Codex architecture review at M2 entry**
(new-language/new-infra boundary: TS package + Trigger.dev runtime) and **M4 entry** (real solver + prod
infra), per ADR-026. M1 is pure-Python contract/Mock work on existing patterns — Codex review at M1 close.
