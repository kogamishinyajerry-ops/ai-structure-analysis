# ENG-40 FM-01 Operator Shell Smoke

- **Issue:** ENG-40
- **Milestone:** FM-01 — Web Console Operator Shell
- **Claim tier:** Tier 0 sandbox/demo
- **Evidence wording:** software-path evidence only
- **Branch:** `codex/ENG-40-fm01-operator-shell`

## Discovered Entry Point

- Frontend shell: `frontend/src/App.tsx`
- Styling surface: `frontend/src/index.css`
- Frontend verification root: `frontend/package.json`

No backend API, schema, solver protocol, dependency, CI, solver deck, or
`golden_samples/**` change was required for this slice.

## Rendered Surface

The Web Console now renders an operator status panel with:

- milestone: `FM-01 Web Console Operator Shell`;
- Linear issue: `ENG-40`;
- claim tier: `Tier 0 sandbox/demo`;
- backend provenance note for AERON L0 / CalculiX metadata availability;
- next action: select or upload a case and run a software-path smoke only;
- no-overclaim label: `software-path evidence only`.

Screenshot artifact:

- `reports/codex_tool_reports/eng40_fm01_operator_shell.png`

## Verification

```bash
cd frontend && npm run build
cd frontend && npm run lint
python /Users/Zhuanz/.codex/skills/webapp-testing/scripts/with_server.py \
  --server "cd frontend && npm run dev -- --host 127.0.0.1 --port 5174" \
  --port 5174 \
  --timeout 40 \
  -- bash -lc 'python3 - <<PY
from pathlib import Path
from playwright.sync_api import sync_playwright
url = "http://127.0.0.1:5174"
out = Path("/tmp/eng40_operator_shell.png")
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1440, "height": 1000})
    page.goto(url)
    page.wait_for_load_state("networkidle")
    body = page.locator("body").inner_text().lower()
    required = [
        "operator status",
        "milestone control surface",
        "fm-01 web console operator shell",
        "eng-40",
        "tier 0 sandbox/demo",
        "software-path evidence only",
        "aeron l0 / calculix path",
        "select or upload a case",
    ]
    missing = [text for text in required if text not in body]
    page.screenshot(path=str(out), full_page=True)
    browser.close()
if missing:
    raise SystemExit("Missing rendered text: " + ", ".join(missing))
print("FM-01 operator shell smoke passed")
print(out)
PY'
```

Result:

- `npm run build`: passed.
- `npm run lint`: passed.
- Playwright smoke: passed and produced `/tmp/eng40_operator_shell.png`.
