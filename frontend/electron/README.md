# Electron workbench shell — RFC-001 W5

Minimal Electron desktop shell over the `report-cli` console_script.
Engineer picks a `.frd`, picks a kind, picks an output path, clicks
**Run**, watches `report-cli`'s stdout/stderr, and gets a signed `.docx`.

The shell is intentionally **thin**. Every piece of substantive logic
— FRD reading, derivations, template validation, DOCX export —
lives in the Python CLI (RFC-001 §3 wedge). The Electron tree is
plumbing only.

## Files

| Path | Role |
|------|------|
| `main.ts` | Electron main process: window + IPC handlers (`open-frd`, `save-docx`, `run-report`, `reveal-in-folder`) |
| `preload.ts` | Sandboxed bridge exposing `window.api` to the renderer (typed surface, no fs/shell/process leakage) |
| `renderer.html` / `.css` / `.ts` | Single-page UI: form, status line, log panel |
| `tsconfig.json` | Compiles the three TS files into `frontend/dist-electron/` |
| `README.md` | This file |

## Running the shell (developer flow)

Prerequisites: Node 18+, `report-cli` on PATH (i.e. the repo's
Python project is `pip install -e .`'d into the active venv and
that venv's `bin/` is on the shell PATH).

```bash
cd frontend
npm install              # picks up electron from devDependencies
npm run electron:build   # compiles main.ts/preload.ts/renderer.ts → dist-electron/
npm run electron:dev     # launches the shell window
```

Dev tip: when iterating on TS, run `npm run electron:build:watch`
in one terminal and `npm run electron:dev` in another; reload the
window with `Cmd+R` (macOS) / `Ctrl+R` (Win/Linux).

## What's deliberately NOT in this PR

- **Bundled Python / CalculiX**. Customer-demo scope (W5+). Today
  the shell assumes the engineer already has a working
  `report-cli`; if it isn't on PATH, the spawn fails and the log
  panel shows the error message + a hint pointing at
  `pip install -e .`.
- **electron-builder packaging** (.dmg / .exe / .AppImage).
  Follow-up PR; this PR just makes the shell runnable in dev mode
  so we have something to demo.
- **React reuse**. `frontend/src/App.tsx` is a Vite SPA wired
  against the frozen Sprint-2 FastAPI backend (RFC-001 Bucket B).
  We did not touch it. The Electron renderer is plain HTML+TS to
  keep the diff small and the dependency surface contained;
  promoting it to React if needed is a future call.
- **Pre-flight CalculiX install probe**, **GS-001 demo button**,
  **violation-panel UI**. All sensible follow-ups; today the shell
  surfaces failures via the raw stderr stream.

## Security posture

- `contextIsolation: true`, `nodeIntegration: false`, `sandbox: true`.
- Renderer has zero direct access to fs / shell / process. It can
  only call the four IPC channels declared in `preload.ts`.
- `report-cli`'s argv is built in main.ts from typed inputs; the
  renderer never sees a shell command line.
- CSP in `renderer.html` blocks remote scripts/styles.

## Testing

This first PR ships **no automated tests** for the Electron tree —
running an Electron app under a CI matrix is meaningfully more
infra than the wedge calls for. Verification is manual smoke:

1. `npm run electron:build`
2. `npm run electron:dev`
3. Pick `golden_samples/GS-001/gs001_result.frd`
4. Choose `static`, pick an output, click **Run**.
5. Status flips to **done (exit 0)**. Log shows the
   `wrote /path/to/report.docx (template=…)` summary line.
6. Click **Reveal output** → file manager opens at the .docx.

Repeat for `lifting-lug` and `pressure-vessel` (with `--scl-nodes`
+ `--scl-distances` and optional `--resample 21`).
