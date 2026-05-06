# ENG-42 Dynamic Operator State Smoke

- Date: 2026-05-07
- Issue: ENG-42
- Milestone: FM-01 Web Console Operator Shell
- Claim tier: Tier 0 sandbox/demo

## Scope Verified

The operator shell now derives session state from existing frontend state in
`frontend/src/App.tsx`:

- `activeCaseId`, uploaded `file`, and `availableCases` drive Active case.
- `solving`, `activeExperiment`, `loading`, and `report` drive Run state.
- `report` and `logs` drive Evidence state.
- `logs` drives Latest event.
- Next action changes based on case, loading, report, and solving state.

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

The Python and Node Playwright packages were not available in the current
environment, so the browser smoke used the installed Google Chrome headless
binary through the existing `webapp-testing` server helper.

Command shape:

```text
python /Users/Zhuanz/.codex/skills/webapp-testing/scripts/with_server.py \
  --server "cd frontend && npm run dev -- --host 127.0.0.1 --port 5176" \
  --port 5176 \
  --timeout 45 \
  -- sh -lc '"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
    --headless=new \
    --disable-gpu \
    --no-first-run \
    --user-data-dir=/tmp/chrome-eng42 \
    --window-size=1440,1000 \
    --virtual-time-budget=3000 \
    --screenshot=/tmp/eng42_dynamic_operator_state.png \
    http://127.0.0.1:5176'
```

Screenshot artifact:

- `reports/codex_tool_reports/eng42_dynamic_operator_state.png`

Visible browser evidence in the screenshot:

- `ENG-42`
- `Active case` -> `No active case`
- `Run state` -> `Idle`
- `Evidence state` -> `No run evidence yet`
- `Latest event` -> `No runtime log event`
- `Next action` -> `Select a gallery case or upload an FRD file`
- `software-path evidence only`

## Limitations

This is Tier 0 UI/browser smoke evidence only. It does not exercise a real
solver run and does not imply signed validation or physical accuracy.
