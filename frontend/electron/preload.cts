/**
 * Electron preload — typed bridge between renderer and main process.
 *
 * The renderer is sandboxed (contextIsolation=true, nodeIntegration=
 * false), so it can't reach Node APIs directly. This preload script
 * exposes a single ``window.api`` object whose surface is the only
 * channel by which the renderer talks to the rest of the system.
 *
 * Keep this surface tight. Adding a method here adds it to the
 * renderer's blast radius — every IPC channel is a potential target
 * for a malicious .frd that somehow trips an injection bug. We
 * accept input strings only as opaque file paths or values fed
 * directly to the report-cli argv vector; the renderer never gets
 * shell, fs, or process access.
 */

import { contextBridge, ipcRenderer } from "electron";

type ReportKind = "static" | "lifting-lug" | "pressure-vessel" | "ballistic";

interface RunReportRequest {
  frd: string;
  kind: ReportKind;
  output: string;
  sclNodes?: string;
  sclDistances?: string;
  resample?: number | null;
  material?: string;
  openradiossRoot?: string;
  rootname?: string;
}

interface BakeGs101Result {
  ok: boolean;
  // Optional because early-failure paths (missing deck, mkdtempSync /
  // copyFileSync errors) return before docker spawns — there is no
  // process exit code to report. The renderer renders these as
  // "bake refused (input violations)".
  exitCode?: number;
  scratchDir?: string;
  rootname?: string;
  violations?: string[];
}

interface MaterialOption {
  codeGrade: string;
  codeStandard: string;
  sigmaY: number;
  sigmaU: number;
  citation: string;
}

interface RunReportSuccess {
  ok: true;
  exitCode: number;
  outputPath: string;
  // W8a — set on ballistic runs when the viewport export ran cleanly.
  // Renderer offers an "Open viewport" button when this is present.
  viewportManifestPath?: string;
}

interface RunReportFailure {
  ok: false;
  exitCode?: number;
  outputPath?: string;
  violations?: string[];
}

type RunReportResult = RunReportSuccess | RunReportFailure;

interface OpenViewportResult {
  ok: boolean;
  pid?: number;
  error?: string;
}

interface OpenViewportOptions {
  // W8d — when true, viewport-cli is invoked with --live so the slider
  // grows as the streaming exporter appends new states.
  live?: boolean;
  // Optional override of the live-mode poll cadence. Must be a positive
  // integer in milliseconds; main.ts ignores out-of-range values.
  pollIntervalMs?: number;
}

interface StartLiveBakeResult {
  ok: boolean;
  // Absolute path to the OpenRadioss scratch dir holding the live
  // A###.gz frames as docker writes them.
  scratchDir?: string;
  // Absolute path to the dir holding viewport_manifest.json + states/.
  viewportDir?: string;
  // Convenience — same as ``<viewportDir>/viewport_manifest.json``,
  // ready to feed to ``openViewport``.
  manifestPath?: string;
  rootname?: string;
  bakePid?: number;
  watchPid?: number;
  violations?: string[];
  error?: string;
}

contextBridge.exposeInMainWorld("api", {
  // Native dialogs
  openFrd: (): Promise<string | null> => ipcRenderer.invoke("open-frd"),
  saveDocx: (suggested: string): Promise<string | null> =>
    ipcRenderer.invoke("save-docx", suggested),
  revealInFolder: (filepath: string): Promise<boolean> =>
    ipcRenderer.invoke("reveal-in-folder", filepath),

  // Returns the bundled GS-001 sample's .frd path if discoverable,
  // else null (the renderer hides the demo button on null).
  getDemoFrd: (): Promise<string | null> =>
    ipcRenderer.invoke("get-demo-frd"),

  // Native folder picker for --openradioss-root (ballistic kind).
  openOpenradiossRoot: (): Promise<string | null> =>
    ipcRenderer.invoke("open-openradioss-root"),

  // Returns the bundled GS-101-demo-unsigned deck dir if discoverable,
  // else null. The renderer hides the GS-101 bake button on null.
  getDemoGs101Deck: (): Promise<string | null> =>
    ipcRenderer.invoke("get-demo-gs101-deck"),

  // Run the OpenRadioss starter+engine inside the openradioss:arm64
  // Docker image against the GS-101-demo-unsigned deck. The deck path
  // is resolved by the main process from a fixed candidate list — the
  // renderer cannot redirect the bake at an attacker-controlled dir.
  // Resolves with the scratch dir holding the baked A###.gz frames.
  bakeGs101Demo: (): Promise<BakeGs101Result> =>
    ipcRenderer.invoke("bake-gs101-demo"),

  // Streaming events from the docker bake subprocess.
  onBakeStdout: (cb: (text: string) => void): (() => void) => {
    const handler = (_e: unknown, text: string) => cb(text);
    ipcRenderer.on("bake:stdout", handler);
    return () => ipcRenderer.removeListener("bake:stdout", handler);
  },
  onBakeStderr: (cb: (text: string) => void): (() => void) => {
    const handler = (_e: unknown, text: string) => cb(text);
    ipcRenderer.on("bake:stderr", handler);
    return () => ipcRenderer.removeListener("bake:stderr", handler);
  },
  // No onBakeExit — the bake handler resolves the IPC promise with
  // {ok, exitCode, ...} so the renderer reads exit through the await,
  // not a separate event subscription. The "bake:exit" channel is
  // still emitted by main.ts in case a future feature needs it.

  // W6a / Codex R1 PR #91 LOW: single source of truth is
  // backend/app/data/materials.json. The renderer pulls the dropdown
  // contents from `report-cli --list-materials` so adding a 13th
  // grade is a JSON-only PR, no HTML edit. Returns [] if report-cli
  // is broken / not on PATH; the dropdown then falls back to a
  // non-functional empty state and the engineer can still type
  // --material via CLI.
  listMaterials: (): Promise<MaterialOption[]> =>
    ipcRenderer.invoke("list-materials"),

  // Run the report. The promise resolves *after* the subprocess
  // exits; intermediate stdout/stderr arrive as events.
  runReport: (req: RunReportRequest): Promise<RunReportResult> =>
    ipcRenderer.invoke("run-report", req),

  // W8b — spawn the PyVista native viewport against a manifest path
  // (returned in RunReportResult.viewportManifestPath). Resolves with
  // {ok, pid?, error?}. The viewport window outlives the call.
  //
  // W8d — pass ``{ live: true }`` to start the viewport in
  // live-polling mode (slider grows as new states append). Used after
  // ``startLiveGs101Bake`` when the manifest path returned from that
  // call has at least one state.
  openViewport: (
    manifestPath: string,
    options?: OpenViewportOptions,
  ): Promise<OpenViewportResult> =>
    ipcRenderer.invoke("open-viewport", manifestPath, options),

  // W8d — single-click live ballistic demo. Spawns docker (engine) +
  // viewport-watch-cli (manifest writer) in parallel, waits for the
  // first frame to land, then resolves with the manifest path so the
  // renderer can call openViewport(manifestPath, { live: true }).
  // The renderer also subscribes to ``onWatchStdout`` /
  // ``onWatchStderr`` for live output from the watcher process.
  startLiveGs101Bake: (): Promise<StartLiveBakeResult> =>
    ipcRenderer.invoke("start-live-gs101-bake"),

  // Streaming events from the W8d viewport-watch-cli subprocess.
  onWatchStdout: (cb: (text: string) => void): (() => void) => {
    const handler = (_e: unknown, text: string) => cb(text);
    ipcRenderer.on("watch:stdout", handler);
    return () => ipcRenderer.removeListener("watch:stdout", handler);
  },
  onWatchStderr: (cb: (text: string) => void): (() => void) => {
    const handler = (_e: unknown, text: string) => cb(text);
    ipcRenderer.on("watch:stderr", handler);
    return () => ipcRenderer.removeListener("watch:stderr", handler);
  },

  // Streaming events from the running report-cli subprocess.
  onStdout: (cb: (text: string) => void): (() => void) => {
    const handler = (_e: unknown, text: string) => cb(text);
    ipcRenderer.on("report:stdout", handler);
    return () => ipcRenderer.removeListener("report:stdout", handler);
  },
  onStderr: (cb: (text: string) => void): (() => void) => {
    const handler = (_e: unknown, text: string) => cb(text);
    ipcRenderer.on("report:stderr", handler);
    return () => ipcRenderer.removeListener("report:stderr", handler);
  },
  onExit: (cb: (exitCode: number) => void): (() => void) => {
    const handler = (_e: unknown, code: number) => cb(code);
    ipcRenderer.on("report:exit", handler);
    return () => ipcRenderer.removeListener("report:exit", handler);
  },
  // Each "figure: <path>" line on report-cli stderr triggers one
  // event; the renderer loads the PNG at <path> in its gallery.
  onFigure: (cb: (path: string) => void): (() => void) => {
    const handler = (_e: unknown, path: string) => cb(path);
    ipcRenderer.on("report:figure", handler);
    return () => ipcRenderer.removeListener("report:figure", handler);
  },
});
