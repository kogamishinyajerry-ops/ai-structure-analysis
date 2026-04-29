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
import * as os from "node:os";
import * as path from "node:path";
import * as url from "node:url";

// ESM-style __dirname (Vite/electron-builder both load this as ESM).
const __filename = url.fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const REPORT_KINDS = [
  "static",
  "lifting-lug",
  "pressure-vessel",
  "ballistic",
] as const;
type ReportKind = (typeof REPORT_KINDS)[number];

interface RunReportRequest {
  // .frd is required for static / lifting-lug / pressure-vessel; ignored
  // for ballistic (which feeds OpenRadioss A-frames instead).
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
  // ballistic only — directory containing OpenRadioss A-frames
  // (<rootname>A001.gz, ...) and rootname prefix.
  openradiossRoot?: string;
  rootname?: string;
}

// Conservative whitelist for --material values. Only forward strings
// that match standard CalculiX/ASME grade designations — letters,
// digits, dash, hash, slash. The renderer's <select> already produces
// safe values, but main.ts is the trust boundary, so re-validate here.
// Codex R1 LOW-style defense (cf. PR #90 R1 #3): never trust IPC payload.
const MATERIAL_GRADE_RE = /^[A-Za-z0-9][A-Za-z0-9_\-./#+]{0,63}$/;

// Whitelist for OpenRadioss --rootname values. Mirrors the upstream
// convention of letters/digits/underscore/dash; refuses path separators
// and shell metacharacters since this string ends up on the report-cli
// argv vector (and via report-cli into the adapter's frame globber).
const ROOTNAME_RE = /^[A-Za-z0-9][A-Za-z0-9_\-]{0,63}$/;

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

// --- IPC: ballistic / OpenRadioss helpers ----------------------------------

/**
 * Guarded ``evt.sender.send`` that no-ops when the renderer's
 * ``webContents`` has been destroyed (window closed, navigated, etc.).
 *
 * Codex R2 MEDIUM (main.ts:353): the bake handler streams events
 * across multiple async callbacks long after the IPC invoke handler
 * returned. If the user closes the window mid-bake, a later ``send``
 * on a destroyed ``webContents`` throws an unhandled exception in
 * the main process. This helper centralizes the guard.
 */
function _safeSend(
  evt: Electron.IpcMainInvokeEvent,
  channel: string,
  payload: unknown,
): void {
  if (!evt.sender.isDestroyed()) {
    evt.sender.send(channel, payload);
  }
}

/**
 * Native folder picker for the OpenRadioss --openradioss-root argument.
 * Returns the absolute path of the chosen directory, or null if the
 * user canceled. The renderer never touches fs directly — main.ts is
 * the trust boundary.
 */
ipcMain.handle("open-openradioss-root", async () => {
  if (!mainWindow) return null;
  const result = await dialog.showOpenDialog(mainWindow, {
    title: "Select OpenRadioss output directory (containing A###.gz frames)",
    properties: ["openDirectory"],
  });
  return result.canceled ? null : result.filePaths[0];
});

/**
 * Resolve the bundled GS-101-demo-unsigned data dir if discoverable.
 *
 * Returns the absolute path to ``golden_samples/GS-101-demo-unsigned/data/``
 * (which holds the upstream-derived ``model_00_0000.rad`` /
 * ``model_00_0001.rad`` deck files), or null on packaged builds without
 * the bundled fixture. The renderer hides the GS-101 demo button on null.
 *
 * NOTE: this returns the *deck* dir, not a baked-frames dir. The bake
 * step (see ``bake-gs101-demo`` below) copies these decks to a scratch
 * directory and runs the OpenRadioss starter+engine inside Docker; the
 * resulting A###.gz frames land in the scratch dir, not in golden_samples
 * (per ADR-011 §HF1.7 forbidden-zone protection).
 */
/**
 * Locate the bundled GS-101-demo-unsigned deck dir on disk by probing
 * a fixed list of candidates relative to the Electron bundle. This is
 * the *only* function allowed to mint a deck path used by the bake
 * handler — see ``_resolveDemoGs101Deck`` consumers below.
 */
function _resolveDemoGs101Deck(): string | null {
  const rel = path.join("golden_samples", "GS-101-demo-unsigned", "data");
  const candidates = [
    path.resolve(__dirname, "..", "..", rel),
    path.resolve(process.cwd(), rel),
    path.resolve(process.cwd(), "..", rel),
  ];
  for (const candidate of candidates) {
    const starter = path.join(candidate, "model_00_0000.rad");
    const engine = path.join(candidate, "model_00_0001.rad");
    if (fs.existsSync(starter) && fs.existsSync(engine)) return candidate;
  }
  return null;
}

ipcMain.handle("get-demo-gs101-deck", () => _resolveDemoGs101Deck());

/**
 * Bake the GS-101-demo-unsigned deck via the ``openradioss:arm64`` Docker
 * image. Produces the A001.gz..A011.gz animation frames in a scratch
 * directory under ``os.tmpdir()/gs101-demo-bake-<timestamp>/`` so the
 * golden_samples/ tree is not modified (ADR-011 §HF1.7 forbidden-zone).
 *
 * Streams docker stdout/stderr back to the renderer over the
 * ``bake:stdout`` / ``bake:stderr`` events. On success, returns the
 * scratch path so the renderer can pre-fill --openradioss-root.
 *
 * NOTE: this assumes the engineer has already built the
 * ``openradioss:arm64`` image per ``tools/openradioss/README.md``.
 * If the image is missing, docker exits non-zero and the renderer
 * surfaces the stderr to the user.
 */
ipcMain.handle("bake-gs101-demo", async (evt: Electron.IpcMainInvokeEvent) => {
  // Trust boundary: the renderer is not allowed to nominate the deck
  // dir. We re-resolve it on the main side from the same fixed
  // candidate list as ``get-demo-gs101-deck`` so a compromised
  // renderer can't redirect docker at an attacker-controlled path
  // (the bake handler will end up reading and copying whatever lives
  // under that path into a scratch dir).
  const deckDir = _resolveDemoGs101Deck();
  const violations: string[] = [];
  if (!deckDir) {
    violations.push("GS-101-demo-unsigned deck not found in bundled fixtures.");
  } else if (!fs.existsSync(path.join(deckDir, "model_00_0000.rad"))) {
    violations.push(`Missing model_00_0000.rad in ${deckDir}`);
  } else if (!fs.existsSync(path.join(deckDir, "model_00_0001.rad"))) {
    violations.push(`Missing model_00_0001.rad in ${deckDir}`);
  }
  if (violations.length > 0 || !deckDir) {
    return { ok: false as const, violations };
  }
  const resolvedDeckDir: string = deckDir;

  // Stage decks into a scratch dir under the OS temp root so docker can
  // mount it read-write without touching golden_samples/.
  //
  // Use ``fs.mkdtempSync`` (not ``mkdirSync(predictable_path, recursive:
  // true)``) to atomically create a uniquely-named dir owned by the
  // current user — closes the same-user TOCTOU window where another
  // local process could pre-create or symlink the predictable
  // ``gs101-demo-bake-<timestamp>`` path before docker mounts it
  // (Codex R1 LOW).
  let scratch: string;
  try {
    scratch = fs.mkdtempSync(path.join(os.tmpdir(), "gs101-demo-bake-"));
  } catch (err) {
    return {
      ok: false as const,
      violations: [`Failed to allocate bake scratch dir: ${(err as Error).message}`],
    };
  }
  try {
    fs.copyFileSync(
      path.join(resolvedDeckDir, "model_00_0000.rad"),
      path.join(scratch, "model_00_0000.rad"),
    );
    fs.copyFileSync(
      path.join(resolvedDeckDir, "model_00_0001.rad"),
      path.join(scratch, "model_00_0001.rad"),
    );
  } catch (err) {
    // Codex R2 LOW: clean up the freshly-allocated scratch dir on
    // partial-stage failure so we don't leak under os.tmpdir().
    try {
      fs.rmSync(scratch, { recursive: true, force: true });
    } catch {
      // Best-effort; if rmSync also fails (permissions, weird state)
      // we'd rather surface the original copy error than mask it.
    }
    return {
      ok: false as const,
      violations: [`Failed to stage decks: ${(err as Error).message}`],
    };
  }

  _safeSend(
    evt,
    "bake:stdout",
    `[bake] staged decks into ${scratch}\n[bake] launching docker run openradioss:arm64 …\n`,
  );

  const dockerArgs = [
    "run", "--rm",
    "-v", `${scratch}:/work`,
    "openradioss:arm64",
    "bash", "-c",
    "cd /work && starter_linuxa64 -i model_00_0000.rad -np 1 && " +
      "engine_linuxa64 -i model_00_0001.rad",
  ];
  const child = spawn("docker", dockerArgs, { stdio: ["ignore", "pipe", "pipe"] });
  child.stdout.on("data", (chunk: Buffer) => {
    _safeSend(evt, "bake:stdout", chunk.toString("utf-8"));
  });
  child.stderr.on("data", (chunk: Buffer) => {
    _safeSend(evt, "bake:stderr", chunk.toString("utf-8"));
  });

  return new Promise<{
    ok: boolean;
    exitCode: number;
    scratchDir: string;
    rootname: string;
    violations?: string[];
  }>((resolve) => {
    child.on("close", (code) => {
      const exitCode = code ?? -1;
      _safeSend(evt, "bake:exit", exitCode);
      resolve({
        ok: exitCode === 0,
        exitCode,
        scratchDir: scratch,
        rootname: "model_00",
      });
    });
    child.on("error", (err) => {
      _safeSend(
        evt,
        "bake:stderr",
        `failed to spawn docker: ${err.message}\n` +
          `Hint: build the image first per tools/openradioss/README.md\n`,
      );
      _safeSend(evt, "bake:exit", -1);
      // Codex R2 LOW: docker never started, so no useful artifacts
      // landed in scratch — clean it up rather than leak under
      // os.tmpdir(). On a successful or partial-failure docker run
      // we KEEP the scratch dir intact so the engineer can inspect
      // engine logs / diagnose. Only the "spawn never happened"
      // path is purely a leak.
      try {
        fs.rmSync(scratch, { recursive: true, force: true });
      } catch {
        // Best-effort cleanup.
      }
      resolve({
        ok: false,
        exitCode: -1,
        scratchDir: scratch,
        rootname: "model_00",
        violations: [`docker spawn failed: ${err.message}`],
      });
    });
  });
});

// --- IPC: report-cli subprocess --------------------------------------------

ipcMain.handle("run-report", async (evt: Electron.IpcMainInvokeEvent, req: RunReportRequest) => {
  // Validate up-front — easier to reason about here than inside the
  // streaming subprocess flow. Each violation surfaces as one
  // structured error the renderer can render in the violations panel.
  const violations: string[] = [];
  if (!REPORT_KINDS.includes(req.kind)) {
    violations.push(`Unknown report kind: ${String(req.kind)}`);
  }
  if (!req.output) violations.push("No output .docx path chosen.");
  if (req.kind === "ballistic") {
    if (!req.openradiossRoot?.trim()) {
      violations.push("--openradioss-root required for ballistic.");
    }
    if (!req.rootname?.trim()) {
      violations.push("--rootname required for ballistic.");
    } else if (!ROOTNAME_RE.test(req.rootname.trim())) {
      violations.push(
        `Invalid --rootname: ${req.rootname.slice(0, 60)} ` +
          `(letters/digits/_- only, ≤64 chars).`,
      );
    }
  } else {
    if (!req.frd) violations.push("No .frd file selected.");
    if (req.kind === "pressure-vessel") {
      if (!req.sclNodes?.trim()) {
        violations.push("--scl-nodes required for pressure-vessel.");
      }
      if (!req.sclDistances?.trim()) {
        violations.push("--scl-distances required for pressure-vessel.");
      }
    }
  }
  if (violations.length > 0) {
    return { ok: false as const, violations };
  }

  const args = ["--kind", req.kind, "--output", req.output];
  if (req.kind === "ballistic") {
    args.push("--openradioss-root", req.openradiossRoot!.trim());
    args.push("--rootname", req.rootname!.trim());
    // The CLI's W5f figure renderer is CalculiX-FRD-only and
    // ``cli.py`` hard-errors on ``--kind=ballistic`` with figures
    // enabled (services/report/cli.py:612-622). The default of
    // ``--figures`` is True, so we must explicitly opt out — every
    // UI-driven ballistic run would otherwise fail at CLI validation
    // before any A-frame is read. The DOCX still embeds the W7c
    // animation montage for ballistic visualization. (Codex R1 HIGH.)
    args.push("--no-figures");
  } else {
    args.push("--frd", req.frd);
  }
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

  // W8a — auto-derive the viewport output dir for ballistic runs so
  // the renderer can spawn the W8b native viewport without an extra
  // path picker. The directory is sibling to the DOCX, named
  // <output>.viewport/. Other kinds skip the flag entirely.
  let viewportDir: string | undefined;
  if (req.kind === "ballistic") {
    viewportDir = path.resolve(
      path.dirname(req.output),
      path.basename(req.output, path.extname(req.output)) + ".viewport",
    );
    args.push("--viewport-out", viewportDir);
  }

  // ``report-cli`` is the console_script registered by
  // pyproject.toml [project.scripts]. We assume it's on PATH —
  // bundling Python is the customer-demo scope (W5+, separate PR).
  const child = spawn("report-cli", args, { stdio: ["ignore", "pipe", "pipe"] });

  // Codex R3 MEDIUM: route every send through ``_safeSend`` so a
  // window-close mid-report does not throw on a destroyed
  // webContents (R2 fixed this for bake; R3 closes the inconsistency
  // for run-report. On macOS the app stays alive after the only
  // window closes — see app.on("window-all-closed") above — so this
  // is a real lifecycle bug, not a theoretical one.)
  child.stdout.on("data", (chunk: Buffer) => {
    _safeSend(evt, "report:stdout", chunk.toString("utf-8"));
  });
  // Buffer stderr by line so a "figure: <path>" announcement isn't
  // split across two chunks. The CLI flushes after each line so the
  // boundary is reliable; we just need to reassemble across TCP-style
  // chunk arbitrariness.
  let stderrBuf = "";
  child.stderr.on("data", (chunk: Buffer) => {
    const text = chunk.toString("utf-8");
    _safeSend(evt, "report:stderr", text);
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
          _safeSend(evt, "report:figure", candidate);
        }
      }
    }
  });

  return new Promise<{
    ok: boolean;
    exitCode: number;
    outputPath: string;
    viewportManifestPath?: string;
  }>((resolve) => {
    child.on("close", (code) => {
      const exitCode = code ?? -1;
      _safeSend(evt, "report:exit", exitCode);
      // W8a — surface the viewport manifest path on success so the
      // renderer can offer "Open viewport" without re-deriving the
      // path. We check existence rather than assuming the export
      // succeeded: viewport-export failures degrade to warning-only
      // per cli.py and the manifest may be absent.
      let viewportManifestPath: string | undefined;
      if (exitCode === 0 && viewportDir) {
        const candidate = path.join(viewportDir, "viewport_manifest.json");
        if (fs.existsSync(candidate)) {
          viewportManifestPath = candidate;
        }
      }
      resolve({
        ok: exitCode === 0,
        exitCode,
        outputPath: req.output,
        viewportManifestPath,
      });
    });
    child.on("error", (err) => {
      _safeSend(
        evt,
        "report:stderr",
        `failed to spawn report-cli: ${err.message}\n` +
          `Hint: pip install -e . from the repo root, then make sure ` +
          `the venv's bin/ is on PATH. Once installed, run\n` +
          `  report-cli --doctor\n` +
          `from the same shell that launches this app to verify the ` +
          `install is healthy.\n`
      );
      _safeSend(evt, "report:exit", -1);
      resolve({ ok: false, exitCode: -1, outputPath: req.output });
    });
  });
});


// W8b — spawn the PyVista native viewport against a viewport manifest.
// The handler validates the manifest path is absolute and points at a
// file named ``viewport_manifest.json`` to defend the python module
// invocation against a renderer-side spoof. The viewport runs in its
// own process so closing it does NOT affect the report-cli stream.
ipcMain.handle(
  "open-viewport",
  async (
    _evt: Electron.IpcMainInvokeEvent,
    manifestPath: string,
  ): Promise<{ ok: boolean; pid?: number; error?: string }> => {
    if (typeof manifestPath !== "string" || !manifestPath) {
      return { ok: false, error: "manifest path missing" };
    }
    if (!path.isAbsolute(manifestPath)) {
      return { ok: false, error: "manifest path must be absolute" };
    }
    if (path.basename(manifestPath) !== "viewport_manifest.json") {
      return {
        ok: false,
        error:
          "manifest path must end in viewport_manifest.json (renderer-side spoof guard)",
      };
    }
    if (!fs.existsSync(manifestPath)) {
      return { ok: false, error: `manifest not found: ${manifestPath}` };
    }
    // python -m app.viz.viewport_native <manifest>. Detached so the
    // viewport can outlive the Electron renderer if the engineer
    // closes the workbench while still inspecting the run.
    const child = spawn(
      "python",
      ["-m", "app.viz.viewport_native", manifestPath],
      {
        stdio: ["ignore", "ignore", "pipe"],
        detached: true,
      },
    );
    let stderrBuf = "";
    child.stderr.on("data", (chunk: Buffer) => {
      stderrBuf += chunk.toString("utf-8");
      // Cap accumulator — do not buffer indefinitely.
      if (stderrBuf.length > 4096) {
        stderrBuf = stderrBuf.slice(-2048);
      }
    });
    return new Promise((resolve) => {
      let resolved = false;
      child.on("error", (err) => {
        if (resolved) return;
        resolved = true;
        resolve({
          ok: false,
          error:
            `failed to spawn python viewport: ${err.message}. ` +
            `Hint: pip install -e .[viz] from the repo root.`,
        });
      });
      // Give the python module ~600ms to crash on bad manifest /
      // missing pyvista. If it's still running by then, we resolve
      // with success and let the user interact with the window.
      setTimeout(() => {
        if (resolved) return;
        if (child.exitCode !== null && child.exitCode !== 0) {
          resolved = true;
          resolve({
            ok: false,
            error:
              `viewport exited ${child.exitCode}: ` +
              (stderrBuf.trim().split("\n").pop() ?? "see python stderr"),
          });
          return;
        }
        // Detach so node can exit without waiting on the viewport.
        child.unref();
        resolved = true;
        resolve({ ok: true, pid: child.pid });
      }, 600);
    });
  },
);
