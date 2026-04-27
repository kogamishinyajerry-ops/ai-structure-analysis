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

type ReportKind = "static" | "lifting-lug" | "pressure-vessel";

interface RunReportRequest {
  frd: string;
  kind: ReportKind;
  output: string;
  sclNodes?: string;
  sclDistances?: string;
  resample?: number | null;
}

interface RunReportSuccess {
  ok: true;
  exitCode: number;
  outputPath: string;
}

interface RunReportFailure {
  ok: false;
  exitCode?: number;
  outputPath?: string;
  violations?: string[];
}

type RunReportResult = RunReportSuccess | RunReportFailure;

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

  // Run the report. The promise resolves *after* the subprocess
  // exits; intermediate stdout/stderr arrive as events.
  runReport: (req: RunReportRequest): Promise<RunReportResult> =>
    ipcRenderer.invoke("run-report", req),

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
