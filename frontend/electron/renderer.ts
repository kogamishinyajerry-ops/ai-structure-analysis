/**
 * Electron renderer — wires the form to the ``window.api`` bridge
 * exposed by preload.ts.
 *
 * No build dependencies beyond TypeScript. The renderer is
 * compiled to a single ``renderer.js`` and loaded from
 * renderer.html via a plain ``<script type="module">``.
 */

// Marks this file as a module so the ``declare global`` block below
// is a global augmentation rather than a script-scope rebinding.
export {};

interface RunReportRequest {
  frd: string;
  kind: "static" | "lifting-lug" | "pressure-vessel";
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

interface ElectronApi {
  openFrd: () => Promise<string | null>;
  saveDocx: (suggested: string) => Promise<string | null>;
  revealInFolder: (filepath: string) => Promise<boolean>;
  getDemoFrd: () => Promise<string | null>;
  runReport: (req: RunReportRequest) => Promise<RunReportResult>;
  onStdout: (cb: (text: string) => void) => () => void;
  onStderr: (cb: (text: string) => void) => () => void;
  onExit: (cb: (exitCode: number) => void) => () => void;
}

declare global {
  interface Window {
    api: ElectronApi;
  }
}

// --- DOM refs --------------------------------------------------------------

const $ = <T extends HTMLElement>(id: string): T => {
  const el = document.getElementById(id);
  if (!el) throw new Error(`missing element: #${id}`);
  return el as T;
};

const frdInput = $<HTMLInputElement>("frd");
const frdPick = $<HTMLButtonElement>("frd-pick");
const kindSelect = $<HTMLSelectElement>("kind");
const outputInput = $<HTMLInputElement>("output");
const outputPick = $<HTMLButtonElement>("output-pick");
const pvFieldset = $<HTMLFieldSetElement>("pv-fieldset");
const sclNodesInput = $<HTMLInputElement>("scl-nodes");
const sclDistancesInput = $<HTMLInputElement>("scl-distances");
const resampleInput = $<HTMLInputElement>("resample");
const runBtn = $<HTMLButtonElement>("run");
const revealBtn = $<HTMLButtonElement>("reveal");
const demoBtn = $<HTMLButtonElement>("demo-gs001");
const statusEl = $<HTMLDivElement>("statusEl");
const log = $<HTMLPreElement>("log");

// --- helpers ---------------------------------------------------------------

const setStatus = (text: string, kind: "idle" | "running" | "success" | "error" = "idle") => {
  statusEl.textContent = text;
  statusEl.classList.remove("running", "success", "error");
  if (kind !== "idle") statusEl.classList.add(kind);
};

const appendLog = (text: string) => {
  log.textContent += text;
  log.scrollTop = log.scrollHeight;
};

const clearLog = () => {
  log.textContent = "";
};

const updateFormState = () => {
  const isPv = kindSelect.value === "pressure-vessel";
  pvFieldset.classList.toggle("hidden", !isPv);
  const ready =
    Boolean(frdInput.value) &&
    Boolean(outputInput.value) &&
    (!isPv ||
      (Boolean(sclNodesInput.value.trim()) &&
        Boolean(sclDistancesInput.value.trim())));
  runBtn.disabled = !ready;
};

// --- file pickers ----------------------------------------------------------

frdPick.addEventListener("click", async () => {
  const picked = await window.api.openFrd();
  if (picked) {
    frdInput.value = picked;
    // Suggest an output path next to the .frd, with a .docx extension.
    if (!outputInput.value) {
      const base = picked.replace(/\.frd$/i, "");
      outputInput.value = `${base}.docx`;
    }
    updateFormState();
  }
});

outputPick.addEventListener("click", async () => {
  const suggested = outputInput.value || "report.docx";
  const picked = await window.api.saveDocx(suggested);
  if (picked) {
    outputInput.value = picked;
    updateFormState();
  }
});

revealBtn.addEventListener("click", () => {
  if (outputInput.value) void window.api.revealInFolder(outputInput.value);
});

kindSelect.addEventListener("change", updateFormState);
sclNodesInput.addEventListener("input", updateFormState);
sclDistancesInput.addEventListener("input", updateFormState);

// --- run ------------------------------------------------------------------

window.api.onStdout(appendLog);
window.api.onStderr(appendLog);

runBtn.addEventListener("click", async () => {
  runBtn.disabled = true;
  revealBtn.disabled = true;
  clearLog();
  setStatus("running…", "running");

  const kind = kindSelect.value as RunReportRequest["kind"];
  const resampleRaw = resampleInput.value.trim();
  const req: RunReportRequest = {
    frd: frdInput.value,
    kind,
    output: outputInput.value,
  };
  if (kind === "pressure-vessel") {
    req.sclNodes = sclNodesInput.value;
    req.sclDistances = sclDistancesInput.value;
    if (resampleRaw) req.resample = Number(resampleRaw);
  }

  const result = await window.api.runReport(req);

  if (!result.ok && result.violations) {
    setStatus(
      `refused (${result.violations.length} violation${
        result.violations.length === 1 ? "" : "s"
      })`,
      "error"
    );
    appendLog("\n--- input violations ---\n");
    for (const v of result.violations) appendLog(`  - ${v}\n`);
  } else if (!result.ok) {
    setStatus(`exited ${result.exitCode}`, "error");
  } else {
    setStatus(`done (exit ${result.exitCode})`, "success");
    revealBtn.disabled = false;
  }
  runBtn.disabled = false;
  updateFormState();
});

// --- GS-001 demo button ----------------------------------------------------

/**
 * Auto-fill the form with the bundled GS-001 sample case and trigger
 * Run. One-click smoke test for the demo audience: by the time they
 * blink, the L1→L4→DOCX pipeline has produced a real .docx on disk.
 *
 * The button is hidden if main.ts couldn't locate the .frd
 * (packaged builds without the bundled samples shouldn't advertise
 * a broken shortcut).
 */
demoBtn.addEventListener("click", () => {
  const demoFrd = demoBtn.dataset.frd;
  if (!demoFrd) return;
  frdInput.value = demoFrd;
  kindSelect.value = "static";
  outputInput.value = demoFrd.replace(/\.frd$/i, "_static.docx");
  // Pressure-vessel inputs are not needed for static; the form-state
  // recalc clears the requirement.
  updateFormState();
  runBtn.click();
});

void window.api.getDemoFrd().then((demoFrd) => {
  if (!demoFrd) return;
  demoBtn.dataset.frd = demoFrd;
  demoBtn.hidden = false;
});

// --- init ------------------------------------------------------------------

updateFormState();
setStatus("idle");
