# ENG-43 Solver Job Provenance Claude Audit

- Date: 2026-05-07
- Reviewer: local Claude Opus 4.7, read-only
- Issue: ENG-43
- Milestone: FM-01 Web Console Operator Shell
- Claim tier: Tier 0 sandbox/demo
- Verdict: APPROVE

## Review Boundary

Claude reviewed the ENG-43 diff and smoke proof for displaying solver
job/provenance context in the Web Console operator shell. The reviewed change is
limited to `frontend/src/App.tsx`, `.planning/STATE.md`, and proof artifacts
under `reports/codex_tool_reports/`.

Confirmed boundaries:

- No backend/API/schema changes.
- No solver behavior or solver-truth changes.
- No `golden_samples/**` edits.
- No dependency or CI changes.
- No signed validation or physical accuracy claim.

## Reviewer Findings

Claude returned `APPROVE`.

Confirmed:

- The operator shell displays `Analysis mode` from frontend state captured at
  run start.
- The operator shell displays `Current job` as job id plus job status after the
  existing `/solver/run` path returns a `job_id`.
- Backend provenance changes between an idle "awaits solver job response" state
  and a job-specific `/solver/run` CalculiX path state.
- Evidence wording remains Tier 0 and says software-path evidence only or not
  signed validation where relevant.
- No new endpoint, schema, network path, solver behavior, or persistent storage
  contract was added.

Claude also confirmed state-transition safety:

- Case selection and uploaded FRD flows clear stale job context.
- Solver completion preserves the just-finished job while refreshing the report.
- Stop requests now use `currentJobId` state instead of parsing log strings.
- WebSocket errors transition the visible state to `connection_lost`.
- Copilot-triggered jobs seed the same current job/provenance state.

## Non-Blocking Notes

Claude noted two non-blocking edge cases:

- A silent WebSocket close without an error or finish message would leave the UI
  in `running` until another state change.
- The current `replace('_', ' ')` status display is enough for the current
  status vocabulary, but a future status with multiple underscores would need a
  broader formatter.

## Verification Reviewed

- `cd frontend && npm run build` -> pass.
- `cd frontend && npm run lint` -> pass.
- `git diff --check` -> pass.
- Chrome headless browser smoke captured
  `reports/codex_tool_reports/eng43_job_provenance.png`.
- Playwright package unavailability was documented honestly in the smoke report.

## Outcome

Claude concluded ENG-43 satisfies its Tier 0 acceptance, stays within allowed
frontend/state/proof scope, improves stop-job state handling, and is safe to
commit and open as a PR.
