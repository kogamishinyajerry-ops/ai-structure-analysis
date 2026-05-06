# ENG-43 Solver Job Provenance Smoke

- Date: 2026-05-07
- Issue: ENG-43
- Milestone: FM-01 Web Console Operator Shell
- Claim tier: Tier 0 sandbox/demo

## Scope Verified

The operator shell now exposes solver job/provenance context from existing
frontend session state in `frontend/src/App.tsx`:

- `currentJobId` records the `job_id` returned by the existing `/solver/run`
  and Copilot execution paths.
- `currentJobStatus` records starting, running, stop requested, completed,
  failed, or connection-lost states from existing request and WebSocket events.
- `currentJobAnalysis` records the active analysis mode at the start of the
  solver run.
- The operator shell displays Analysis mode, Current job, Run state, Evidence
  state, Backend provenance, Latest event, and Next action.

No backend endpoint, schema, solver behavior, dependency, CI, or
`golden_samples/**` change was introduced.

## Local Verification

```text
cd frontend && npm run build
```

Result: pass.

```text
cd frontend && npm run lint
```

Result: pass.

```text
git diff --check
```

Result: pass.

## Browser Smoke

As in ENG-42, Python and Node Playwright packages were unavailable in the
current environment, so the browser smoke used the installed Google Chrome
headless binary through the existing `webapp-testing` server helper.

Command shape:

```text
python /Users/Zhuanz/.codex/skills/webapp-testing/scripts/with_server.py \
  --server "cd frontend && npm run dev -- --host 127.0.0.1 --port 5177" \
  --port 5177 \
  --timeout 45 \
  -- sh -lc '"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
    --headless=new \
    --disable-gpu \
    --no-first-run \
    --user-data-dir=/tmp/chrome-eng43 \
    --window-size=1440,1000 \
    --virtual-time-budget=3000 \
    --screenshot=/tmp/eng43_job_provenance.png \
    http://127.0.0.1:5177'
```

The screenshot was written successfully. Chrome's updater process kept the
wrapper session open after the screenshot write, so the Chrome and Vite
processes were terminated after proof capture.

Screenshot artifact:

- `reports/codex_tool_reports/eng43_job_provenance.png`

Visible browser evidence in the screenshot:

- `ENG-43`
- `Analysis mode` -> `static analysis`
- `Current job` -> `No solver job started`
- `Run state` -> `Idle`
- `Evidence state` -> `No run evidence yet`
- `Backend provenance` -> `AERON L0 / CalculiX path awaits a solver job response`
- `software-path evidence only`

## Limitations

This is Tier 0 UI/browser smoke evidence only. It confirms the operator shell
idle-state surface and does not exercise a real solver run. It does not imply
signed validation or physical accuracy.
