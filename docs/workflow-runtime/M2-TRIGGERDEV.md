# M2 — Trigger.dev v4 Orchestration Runbook

Status: **M2 landed.** The 13-stage Mock FEA pipeline can be driven three ways,
in increasing fidelity:

| Driver | Trigger.dev? | Node? | Account? | Use |
| --- | --- | --- | --- | --- |
| `test_m2_fake_orchestrator.py` | no | no | no | CI proof of the HTTP contract (13 tests) |
| `scripts/fake_orchestrator.py` | no | no | no | live smoke against the demo server |
| `trigger/` (this doc) | **yes** | yes | **yes** | real durable orchestration |

The first two need **nothing** but the Python backend. The third needs your own
Trigger.dev account and is what runs in production.

---

## 0. Topology (why it is shaped like this)

```
 Browser (Monitor)                Node                     Python (FastAPI)
 ─────────────────        ──────────────────────      ─────────────────────────
  POST /trigger-pipeline ─► triggerServer.ts
                              │  tasks.trigger(orchestrator)
                              │  └─ mints publicAccessToken   (JS SDK only)
                           ◄──┤  { feaRunId, orchRunId, token }
                              │
                          Trigger.dev cloud
                              │  feaPipelineOrchestrator
                              │   for stage in 13:
                              │     feaStageTask
                              │       createToken() ──────────► (token.url)
                              │       POST /workflow/stage/run ─────────────► run_one_stage(mock)
                              │         (X-Internal-Token,  ◄───────────────── POST {data: StageState}
                              │          callbackUrl)                          to token.url
                              │       wait.forToken ◄── resolves
  GET /workflow/runs/{id} ───────────────────────────────────► (poll detail)
```

**The load-bearing constraint:** a Trigger.dev *public access token* (the
credential the browser needs for `useRealtimeRun`) can only be minted by the
**JS SDK** — `tasks.trigger(...).publicAccessToken` or `auth.createPublicToken`.
The Python backend's REST trigger returns only `{id}`, no token. That is the
entire reason a thin Node layer (`trigger/src/triggerServer.ts`) exists: it owns
`TRIGGER_SECRET_KEY`, mints the browser token, and is the only new long-running
process M2 introduces. Python never sees the secret key.

The **internal** secret (`TRIGGER_INTERNAL_SECRET`) is a *different* secret: a
shared symmetric token authenticating the Trigger.dev worker → FastAPI
`POST /workflow/stage/run`. Two secrets, two trust edges:

- `TRIGGER_SECRET_KEY` — worker → Trigger.dev cloud (and token minting). Node-only.
- `TRIGGER_INTERNAL_SECRET` — worker → your FastAPI. Node **and** Python.

---

## 1. Run the contract with NO account (start here)

```bash
# CI proof — 13 tests, no server needed
source .venv/bin/activate
cd backend && python -m pytest tests/test_m2_fake_orchestrator.py -q

# live smoke — two terminals
python scripts/serve_workflow_demo.py        # terminal 1  (:8077, demo secret)
python scripts/fake_orchestrator.py          # terminal 2  (happy path)
python scripts/fake_orchestrator.py --fail solver_run   # failure injection
```

`fake_orchestrator.py` does *exactly* what `feaPipelineOrchestrator` does —
create an external (PENDING) run, then `POST /workflow/stage/run` per stage with
the `X-Internal-Token` header, then read the terminal run — but in stdlib Python
over HTTP. If this passes, the backend contract is sound; Trigger.dev only adds
durability/retry/observability on top of the same edges.

---

## 2. Run it for real with Trigger.dev (needs your account)

### 2.1 One-time account setup

1. Sign up at <https://cloud.trigger.dev> (free tier, no card for dev).
2. Create an org + project. Copy the **project ref** (`proj_…`).
3. API Keys page → copy the **DEV secret key** (`tr_dev_…`).

### 2.2 Configure `trigger/.env`

```bash
cd trigger
cp .env.example .env
# then edit:
#   TRIGGER_PROJECT_REF=proj_xxxxxxxxxxxx
#   TRIGGER_SECRET_KEY=tr_dev_xxxxxxxxxxxx        # SERVER-ONLY, never in the browser
#   TRIGGER_INTERNAL_SECRET=<long-random-string> # MUST equal the backend's value
#   FEA_API_BASE=http://localhost:8000/api/v1
#   TRIGGER_SERVER_PORT=3033
```

Also set `TRIGGER_PROJECT_REF` in `trigger.config.ts`'s environment, or export it
in the shell — the config reads `process.env.TRIGGER_PROJECT_REF`.

### 2.3 Configure the backend's matching secret

The FastAPI side must share `TRIGGER_INTERNAL_SECRET`. It is **secure by
default**: if unset, `POST /workflow/stage/run` returns **503** (refuses to run an
unauthenticated operator endpoint) — it does not silently allow-all.

```bash
# backend .env  (or real env)
TRIGGER_INTERNAL_SECRET=<the same long-random-string as trigger/.env>
# TRIGGER_API_BASE defaults to https://api.trigger.dev — only override if self-hosting.
```

> The demo launcher `scripts/serve_workflow_demo.py` injects
> `demo-internal-secret` if none is set, so the no-account path above just works.
> **Never** rely on that default in a real deployment.

### 2.4 Install + typecheck the Node package

```bash
cd trigger
npm install                  # ~379 packages; node_modules/ is gitignored
npx tsc --noEmit             # must be clean (exit 0)
```

### 2.5 Boot everything (4 processes)

```bash
# 1. FastAPI backend (with TRIGGER_INTERNAL_SECRET set)
source .venv/bin/activate && cd backend && uvicorn app.main:app --port 8000

# 2. Trigger.dev dev worker — registers tasks, runs them locally against the cloud
cd trigger && npx trigger.dev@latest dev

# 3. The thin trigger server (mints the browser token)
cd trigger && npx tsx src/triggerServer.ts

# 4. The Monitor UI
open docs/demo/workflow_monitor.html      # point its API base at :8000
```

### 2.6 Kick a real pipeline

```bash
curl -sS -X POST http://localhost:3033/trigger-pipeline \
  -H 'Content-Type: application/json' \
  -d '{"failAtStage": null}' | python3 -m json.tool
# -> { feaRunId, orchRunId, publicAccessToken }
```

`feaRunId` is the FastAPI run id the Monitor polls. `orchRunId` +
`publicAccessToken` are what an `useRealtimeRun(orchRunId, {accessToken})` React
hook will consume at **M3**. Inject a failure with
`{"failAtStage": "solver_run"}`.

---

## 3. Security model (what the review checks)

| Surface | Control | Where |
| --- | --- | --- |
| `POST /workflow/stage/run` auth | `X-Internal-Token` must equal `TRIGGER_INTERNAL_SECRET`, compared with `hmac.compare_digest` (constant-time); **503 if unconfigured** (secure-by-default), **401 on mismatch** | `_require_internal`, `api/routes/workflow.py` |
| Callback SSRF | `callbackUrl` scheme must be http/https **and**, for the production path, the **full origin** (scheme + host + port) must equal `TRIGGER_API_BASE` — so `https://host:<other-port>/` is rejected, not just other hosts. Loopback (any port) is allowed **only** when `TRIGGER_ALLOW_LOOPBACK_CALLBACK=true` (self-host/dev — off by default). Validated **before** any stage work. Redirects are not followed. | `_validate_callback_host` |
| Callback delivery | a non-2xx / unreachable callback → **502** (stage is committed + idempotent, so the worker retry re-delivers instead of hanging on its token) | `_post_callback`, `run_stage` |
| Stage double-execution | `run_one_stage` check-and-set is under a process lock; concurrent same-stage calls run once, the rest replay | `mock_pipeline._stage_lock` |
| Signed-registry abuse | a `^GS-\d{3}$` case id hard-stops the CalculiX executor (ADR-011 §HF1.7a) | `well_harness/executors.py` |
| Secret-key leakage | `TRIGGER_SECRET_KEY` lives **only** in Node; Python config documents the deliberate absence | `core/config.py`, `trigger/.env` |
| CORS credentials | `allow_credentials=False` (no cookie auth; the internal token is a header) | `app/main.py` |
| Stage ordering / replay | out-of-order or post-failure stage → **409**; terminal stage is idempotent (returns existing) | `mock_pipeline.run_one_stage` |
| Trigger server exposure | binds `127.0.0.1` by default; **no CORS header by default** (a cross-origin page cannot read the minted token); **DNS-rebinding Host guard** (non-loopback `Host` → 403); optional `TRIGGER_SERVER_TOKEN` bearer gate | `trigger/src/triggerServer.ts` |

The internal secret is **not** a substitute for network policy — in production the
stage endpoint should also be unreachable from the public internet, and the Node
trigger server stays loopback-bound (or token-gated) unless fronted by your own auth.

These controls were hardened over a Codex adversarial review (R0 CHANGES_REQUIRED
→ R1 CHANGES_REQUIRED → R2): SSRF loopback is opt-in + scheme-restricted + the
production callback is pinned to the full Trigger.dev origin (scheme/host/port);
callback failure surfaces 502 (was swallowed); `run_one_stage` is concurrency-safe;
the Node server is loopback-bound, has a DNS-rebinding Host guard, emits no CORS
header by default, and is token-gateable; and the secret compare is constant-time.

---

## 4. Files

```
trigger/
  trigger.config.ts          defineConfig (project ref, dirs, retries, maxDuration)
  src/feaPipeline.ts         feaStageTask + feaPipelineOrchestrator (the 13-stage loop)
  src/triggerServer.ts       Node http server: POST /trigger-pipeline -> mint token
  package.json / tsconfig.json / .env.example / .gitignore

backend/app/
  api/routes/workflow.py     POST /workflow/stage/run (+ auth, SSRF guard, callback POST)
  services/workflow/mock_pipeline.py   create_run / run_one_stage (ordering + idempotency)
  core/config.py             trigger_internal_secret, trigger_api_base
  well_harness/executors.py  signed-registry hard-stop

backend/tests/test_m2_fake_orchestrator.py   13 contract tests (no Trigger.dev)
scripts/fake_orchestrator.py                 live smoke driver (no Trigger.dev)
scripts/serve_workflow_demo.py               dependency-light demo server (:8077)
```

## 5. What M2 deliberately does NOT do

- **No real solver.** Every stage is the Mock backend; `solver_run` synthesizes a
  safety factor. Real CalculiX is M4 — it swaps the backend inside `run_one_stage`
  with *no change* to `trigger/`.
- **No deployment.** `npx trigger.dev dev` only. `deploy` is M4.

> **M3 update (landed):** the Monitor is now a native in-app React tab —
> `frontend/src/components/WorkflowMonitorTabPanel.tsx` (+ `workflowClient.ts` /
> `workflowMonitorView.ts`), wired as the 4th App tab ("Workflow"), faithfully
> porting `docs/demo/workflow_monitor.html`.

> **M3.5 update (landed — true realtime):** the Monitor now streams the
> orchestrator run live via `useRealtimeRun` (`@trigger.dev/react-hooks`). When
> `triggerServerBase` (App.tsx `TRIGGER_SERVER_BASE`, default
> `http://localhost:3033`) is set, the Run button triggers through the Node
> server, receives `{feaRunId, orchRunId, publicAccessToken}`, and subscribes —
> each live tick refreshes the per-stage detail from FastAPI. A live-mode chip
> ("● realtime" / "○ polling") shows which path engaged; if the Node layer is
> unreachable it **falls back to the poll-only path** (so the no-account demo
> still works). New file: `frontend/src/workflowRealtimeClient.ts`.
>
> **Live verification (2026-06-03, project `proj_elnboiduwewmhadaoiol`):** the
> worker registered (`Local worker ready -> 20260603.2`); a real run through the
> Node server drove all 13 stages to `success` on FastAPI; and a run-scoped
> public-token subscription (`runs.subscribeToRun` — the mechanism behind
> `useRealtimeRun`) streamed `status=COMPLETED feaRunId=… completedStages=13/13`
> with the full `stageHistory`. Frontend: 13/13 Monitor tests + full 1300-test
> suite green, eslint 70, App.tsx 1494, `vite build` clean. **Note:** the in-app
> tab points `apiBase` at `:8000`; to use realtime you must run your backend on
> `:8000` *with* `TRIGGER_INTERNAL_SECRET` set (M2 added the workflow routes — a
> pre-M2 backend will 404 them).
