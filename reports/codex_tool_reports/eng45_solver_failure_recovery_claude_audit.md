# ENG-45 Claude Opus 4.7 Review

Date: 2026-05-07
Issue: ENG-45
Reviewer: local Claude Opus 4.7
Mode: read-only issue-level owner gate

## Verdict

APPROVE

## Merge Decision

APPROVE_TO_MERGE

## Findings

- `clearJobContext` now resets `solving`, `logs`, and `showConsole` alongside job id/status, which correctly clears the stale `running` / `stop_requested` lockout when switching cases.
- Solver-start path now handles non-OK HTTP and JSON parse failure, surfaces `[ERROR] Solver start failed: ...`, and resets `solving` / `currentJobStatus='failed'`.
- Stop path checks `response.ok`, distinguishes accepted and failed stops, transitions accepted stops to `stopped`, and always clears `solving`; this matches the smoke reproduction where the backend returned 400 because the job had already failed.
- WebSocket log handling adds an early failure branch for `System Error:`, `Solver exited with code:`, `Error: Job not found`, and `Socket Error:`, plus a `[SYSTEM] Job terminated` -> `stopped` branch.
- `JobStatus` is internally consistent with the new `stopped` state, and `runStateTone` marks `failed` / `connection_lost` as warning.
- `STATE.md` consistently updates the main hash to `9d77042`, records ENG-44 as merged, opens ENG-45 as active polish, and keeps FM-01 human acceptance pending.

## Evidence Check

- Smoke report documents before/after DOM state, `Run Solver` re-enabled, `Stop` button absence, stale log clearing on case switch, and screenshot `reports/codex_tool_reports/eng45_solver_failure_recovery.png`.
- Verification commands listed as passed: `npm run build`, `npm run lint`, `git diff --check`.
- Tier 0 sandbox wording is preserved; no signed-validation or solver-correctness claims are made.

## Boundary Check

- Diff is limited to `frontend/src/App.tsx` and `.planning/STATE.md`, plus repo-local evidence files.
- No backend route, schema, solver code, golden sample, dependency, or CI changes.
- Existing `/solver/run` and `/solver/stop/{id}` contracts are unchanged.
- ENG-45 scope is honored.

## Non-Blocking Observations

- The new `stopped` status is acceptable for Tier 0 polish; confirm visible label behavior on a future pass if stop-success UX becomes important.
- `SOLVER_FAILURE_MARKERS` uses substring matching; benign logs quoting those markers would also flip to `failed`. Acceptable for sandbox/demo.
