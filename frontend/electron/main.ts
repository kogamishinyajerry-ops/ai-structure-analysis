/**
 * Electron main process — RFC-001 W5 workbench shell.
 *
 * The shell's job is to give an engineer a single window with a
 * file picker for the .frd, a kind dropdown, an output picker, and a
 * "Run" button that spawns the ``report-cli`` console_script and
 * streams its stdout / stderr back into the UI panel. The shell is
 * intentionally thin — every piece of substantive logic lives in
 * the Python CLI (RFC-001 §3 wedge), so this main process is
 * almost entirely IPC plumbing.
 *
 * The renderer is plain HTML+TS (no React) to keep this PR's diff
 * small and the dependency surface contained. The repo's existing
 * React app (frontend/src/App.tsx) is a separate Vite SPA wired
 * against the frozen Sprint-2 FastAPI backend; this Electron shell
 * does not touch it.
 *
 * Wire-up:
 *   * single ipcMain handler ``run-report`` → spawn ``report-cli``
 *     and stream events ``report:stdout``, ``report:stderr``,
 *     ``report:exit`` back to the renderer over the webContents.
 *   * dialog handlers ``open-frd`` and ``save-docx`` → native file
 *     pickers; the renderer never touches the filesystem directly.
 *
 * Security: ``contextIsolation=true``, ``nodeIntegration=false``.
 * The renderer reaches the main process only via the typed
 * ``window.api`` surface declared in preload.ts.
 */

import { app, BrowserWindow, dialog, ipcMain, shell } from "electron";
import { spawn } from "node:child_process";
import * as fs from "node:fs";
import * as path from "node:path";
import * as url from "node:url";

// ESM-style __dirname (Vite/electron-builder both load this as ESM).
const __filename = url.fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const REPORT_KINDS = ["static", "lifting-lug", "pressure-vessel"] as const;
type ReportKind = (typeof REPORT_KINDS)[number];

interface RunReportRequest {
  frd: string;
  kind: ReportKind;
  output: string;
  // pressure-vessel only
  sclNodes?: string;
  sclDistances?: string;
  resample?: number | null;
  // W6a — built-in material code_grade (e.g. "Q345B"). Empty/undefined
  // means no § 材料属性 section in the DOCX.
  material?: string;
}

// Conservative whitelist for --material values. Only forward strings
// that match standard CalculiX/ASME grade designations — letters,
// digits, dash, hash, slash. The renderer's <select> already produces
// safe values, but main.ts is the trust boundary, so re-validate here.
// Codex R1 LOW-style defense (cf. PR #90 R1 #3): never trust IPC payload.
const MATERIAL_GRADE_RE = /^[A-Za-z0-9][A-Za-z0-9_\-./#+]{0,63}$/;

let mainWindow: BrowserWindow | null = null;

function createWindow(): void {
  mainWindow = new BrowserWindow({
    width: 960,
    height: 720,
    title: "AI-FEA Structural Report",
    webPreferences: {
      // The preload entry is sourced as ``preload.cts`` (CommonJS)
      // because Electron's preload sandbox loader uses ``require()``,
      // which throws ERR_REQUIRE_ESM on an ES-module preload — the
      // surrounding ``frontend/package.json`` sets ``"type": "module"``
      // (the Vite SPA needs that), so a vanilla ``preload.ts`` →
      // ``preload.js`` would be picked up as ESM and fail at runtime.
      // Using a ``.cts`` source produces a ``.cjs`` output which is
      // CJS regardless of the package's ``type`` field.
      preload: path.join(__dirname, "preload.cjs"),
      contextIsolation: true,
      nodeIntegration: false,
      // The ``.cts`` source above is what guarantees the preload
      // emits as CJS — this preserves the existing runtime model
      // (sandbox:false + contextIsolation:true + nodeIntegration:
      // false) without depending on Electron's sandbox loader to
      // re-shape the module format.
      sandbox: false,
    },
  });
  mainWindow.loadFile(path.join(__dirname, "renderer.html"));
}

app.whenReady().then(() => {
  createWindow();
  app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") app.quit();
});

// --- IPC: native dialogs ---------------------------------------------------

ipcMain.handle("open-frd", async () => {
  if (!mainWindow) return null;
  const result = await dialog.showOpenDialog(mainWindow, {
    title: "Select CalculiX .frd result file",
    filters: [
      { name: "CalculiX result", extensions: ["frd"] },
      { name: "All files", extensions: ["*"] },
    ],
    properties: ["openFile"],
  });
  return result.canceled ? null : result.filePaths[0];
});

ipcMain.handle("save-docx", async (_evt: unknown, suggested: string) => {
  if (!mainWindow) return null;
  const result = await dialog.showSaveDialog(mainWindow, {
    title: "Save report .docx",
    defaultPath: suggested || "report.docx",
    filters: [{ name: "Word document", extensions: ["docx"] }],
  });
  return result.canceled ? null : result.filePath;
});

ipcMain.handle("reveal-in-folder", (_evt: unknown, filepath: string) => {
  if (!filepath) return false;
  shell.showItemInFolder(filepath);
  return true;
});

/**
 * Resolve the bundled GS-001 sample's .frd path if it's discoverable.
 *
 * In dev mode, the Electron main entry sits at
 * ``frontend/dist-electron/main.js``, so the repo root is two
 * levels up. We probe a few candidate paths (compiled, source-tree,
 * cwd) to be robust to different launch contexts. Returns ``null``
 * when nothing is found — the renderer hides the demo button in
 * that case so packaged builds without the bundled samples don't
 * advertise a broken shortcut.
 */
ipcMain.handle("get-demo-frd", () => {
  const rel = path.join("golden_samples", "GS-001", "gs001_result.frd");
  const candidates = [
    // dev mode: __dirname is .../frontend/dist-electron
    path.resolve(__dirname, "..", "..", rel),
    // launched from repo root with `electron frontend/dist-electron/main.js`
    path.resolve(process.cwd(), rel),
    // launched from frontend/
    path.resolve(process.cwd(), "..", rel),
  ];
  for (const candidate of candidates) {
    if (fs.existsSync(candidate)) return candidate;
  }
  return null;
});

/**
 * Pull the built-in material library list by invoking
 * ``report-cli --list-materials`` and parsing its tab-separated stdout.
 *
 * Codex R1 PR #91 LOW fix: the renderer used to hardcode option values,
 * which drifts from materials.json. Now materials.json is the single
 * source of truth — the renderer asks the CLI at startup.
 *
 * Returns ``[]`` on any failure (CLI not on PATH, malformed output,
 * non-zero exit). The renderer treats an empty list as "no
 * materials available, type one via CLI"; the dropdown's empty
 * default option remains usable.
 *
 * NOTE: this uses ``execFile`` with no shell, and the `--list-materials`
 * args are constants — no injection surface.
 */
ipcMain.handle("list-materials", async (): Promise<unknown[]> => {
  return new Promise((resolve) => {
    const proc = spawn("report-cli", ["--list-materials"], {
      stdio: ["ignore", "pipe", "pipe"],
    });
    let out = "";
    proc.stdout.on("data", (chunk: Buffer) => {
      out += chunk.toString("utf-8");
    });
    proc.on("error", () => resolve([]));
    proc.on("close", (code) => {
      if (code !== 0) return resolve([]);
      const rows: unknown[] = [];
      for (const line of out.split(/\r?\n/)) {
        if (!line || line.startsWith("#")) continue;
        const parts = line.split("\t");
        if (parts.length < 5) continue;
        const sigmaY = Number(parts[2]);
        const sigmaU = Number(parts[3]);
        if (!Number.isFinite(sigmaY) || !Number.isFinite(sigmaU)) continue;
        rows.push({
          codeGrade: parts[0],
          codeStandard: parts[1],
          sigmaY,
          sigmaU,
          citation: parts[4],
        });
      }
      resolve(rows);
    });
  });
});

// --- IPC: report-cli subprocess --------------------------------------------

ipcMain.handle("run-report", async (evt: Electron.IpcMainInvokeEvent, req: RunReportRequest) => {
  // Validate up-front — easier to reason about here than inside the
  // streaming subprocess flow. Each violation surfaces as one
  // structured error the renderer can render in the violations panel.
  const violations: string[] = [];
  if (!req.frd) violations.push("No .frd file selected.");
  if (!REPORT_KINDS.includes(req.kind)) {
    violations.push(`Unknown report kind: ${String(req.kind)}`);
  }
  if (!req.output) violations.push("No output .docx path chosen.");
  if (req.kind === "pressure-vessel") {
    if (!req.sclNodes?.trim()) {
      violations.push("--scl-nodes required for pressure-vessel.");
    }
    if (!req.sclDistances?.trim()) {
      violations.push("--scl-distances required for pressure-vessel.");
    }
  }
  if (violations.length > 0) {
    return { ok: false as const, violations };
  }

  const args = [
    "--frd", req.frd,
    "--kind", req.kind,
    "--output", req.output,
  ];
  if (req.kind === "pressure-vessel") {
    args.push("--scl-nodes", req.sclNodes!);
    args.push("--scl-distances", req.sclDistances!);
    if (req.resample != null) {
      args.push("--resample", String(req.resample));
    }
  }
  if (req.material) {
    if (!MATERIAL_GRADE_RE.test(req.material)) {
      return {
        ok: false as const,
        violations: [
          `Invalid material code grade: ${req.material!.slice(0, 60)} ` +
            `(expected built-in code like Q345B / SA-516-70).`,
        ],
      };
    }
    args.push("--material", req.material);
  }

  // Mirror the CLI's default figs_dir derivation: <output>.figs/.
  // Forwarded `figure:` paths must live under this directory, be
  // absolute, and end in .png. Anything else is dropped — defends
  // the renderer's permissive img-src against a stderr-line
  // injection (Codex R1 LOW main.ts:202).
  const expectedFigsDir = path.resolve(
    path.dirname(req.output),
    path.basename(req.output, path.extname(req.output)) + ".figs",
  );

  // ``report-cli`` is the console_script registered by
  // pyproject.toml [project.scripts]. We assume it's on PATH —
  // bundling Python is the customer-demo scope (W5+, separate PR).
  const child = spawn("report-cli", args, { stdio: ["ignore", "pipe", "pipe"] });

  child.stdout.on("data", (chunk: Buffer) => {
    evt.sender.send("report:stdout", chunk.toString("utf-8"));
  });
  // Buffer stderr by line so a "figure: <path>" announcement isn't
  // split across two chunks. The CLI flushes after each line so the
  // boundary is reliable; we just need to reassemble across TCP-style
  // chunk arbitrariness.
  let stderrBuf = "";
  child.stderr.on("data", (chunk: Buffer) => {
    const text = chunk.toString("utf-8");
    evt.sender.send("report:stderr", text);
    stderrBuf += text;
    let nl: number;
    while ((nl = stderrBuf.indexOf("\n")) >= 0) {
      const line = stderrBuf.slice(0, nl);
      stderrBuf = stderrBuf.slice(nl + 1);
      const m = /^figure:\s+(.+)$/.exec(line.trim());
      if (m && m[1]) {
        const candidate = path.resolve(m[1]);
        const rel = path.relative(expectedFigsDir, candidate);
        const insideFigsDir = !!rel && !rel.startsWith("..") && !path.isAbsolute(rel);
        if (
          path.isAbsolute(m[1]) &&
          candidate.toLowerCase().endsWith(".png") &&
          insideFigsDir
        ) {
          evt.sender.send("report:figure", candidate);
        }
      }
    }
  });

  return new Promise<{ ok: boolean; exitCode: number; outputPath: string }>((resolve) => {
    child.on("close", (code) => {
      const exitCode = code ?? -1;
      evt.sender.send("report:exit", exitCode);
      resolve({ ok: exitCode === 0, exitCode, outputPath: req.output });
    });
    child.on("error", (err) => {
      evt.sender.send(
        "report:stderr",
        `failed to spawn report-cli: ${err.message}\n` +
          `Hint: pip install -e . from the repo root, then make sure ` +
          `the venv's bin/ is on PATH. Once installed, run\n` +
          `  report-cli --doctor\n` +
          `from the same shell that launches this app to verify the ` +
          `install is healthy.\n`
      );
      evt.sender.send("report:exit", -1);
      resolve({ ok: false, exitCode: -1, outputPath: req.output });
    });
  });
});
