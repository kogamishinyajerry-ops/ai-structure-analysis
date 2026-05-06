# ENG-45 Solver Failure Recovery Smoke

Date: 2026-05-07
Issue: ENG-45
Claim tier: Tier 0 sandbox/demo

## Setup

- Frontend: `cd frontend && npm run dev -- --host 127.0.0.1 --port 5173`
- Backend: `uv run uvicorn app.main:app --host 127.0.0.1 --port 8000`
- Browser URL: `http://127.0.0.1:5173/`

## Reproduction Before Fix

1. Open the Web Console with the backend running.
2. Select `GS-001 / 悬臂梁静力学分析`.
3. Click `Run Solver` in the local environment without a usable `ccx` executable.
4. The frontend receives `System Error: [Errno 2] No such file or directory`, but remains in `running`.
5. Click `Stop`.
6. The backend returns `400 Bad Request` because the job is already failed, and the frontend remains in `stop requested`.
7. Switch to `GS-002`.
8. The frontend clears the job id, but stale `solving` and log state keep the operator shell in a running-like state with `Run Solver` disabled.

## Fixed Smoke Result

Browser DOM proof after selecting `GS-001` and clicking `Run Solver`:

- `Run Solver` re-enabled: `true`
- Failed state visible: `true`
- `Stop` button absent after failure: `true`
- Latest event: `System Error: [Errno 2] No such file or directory`
- Current job status: `<job id> / failed`
- Run state: `static analysis / failed`
- Next action: `Run a solver smoke or export the report with Tier 0 wording`

Browser DOM proof after switching to `GS-002`:

- `Run Solver` enabled: `true`
- Current job: `No solver job started`
- Run state: `Report loaded`
- Stale `System Error` log cleared: `true`
- `Stop` button absent: `true`

Screenshot:

- `reports/codex_tool_reports/eng45_solver_failure_recovery.png`

## Verification Commands

- `cd frontend && npm run build` -> passed
- `cd frontend && npm run lint` -> passed
- `git diff --check` -> passed

## Boundaries

- No backend API route, schema, solver-truth, persistent data, dependency, CI, or golden-sample changes.
- This proof only demonstrates UI recovery from a local backend solver-start failure.
- It does not claim solver correctness, physical accuracy, or signed validation.
