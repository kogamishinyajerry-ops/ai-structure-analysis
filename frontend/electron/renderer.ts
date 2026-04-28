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
  kind: "static" | "lifting-lug" | "pressure-vessel" | "ballistic";
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
  exitCode: number;
  scratchDir: string;
  rootname: string;
  violations?: string[];
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

interface MaterialOption {
  codeGrade: string;
  codeStandard: string;
  sigmaY: number;
  sigmaU: number;
  citation: string;
}

interface ElectronApi {
  openFrd: () => Promise<string | null>;
  saveDocx: (suggested: string) => Promise<string | null>;
  revealInFolder: (filepath: string) => Promise<boolean>;
  getDemoFrd: () => Promise<string | null>;
  openOpenradiossRoot: () => Promise<string | null>;
  getDemoGs101Deck: () => Promise<string | null>;
  bakeGs101Demo: () => Promise<BakeGs101Result>;
  listMaterials: () => Promise<MaterialOption[]>;
  runReport: (req: RunReportRequest) => Promise<RunReportResult>;
  onStdout: (cb: (text: string) => void) => () => void;
  onStderr: (cb: (text: string) => void) => () => void;
  onExit: (cb: (exitCode: number) => void) => () => void;
  onFigure: (cb: (path: string) => void) => () => void;
  onBakeStdout: (cb: (text: string) => void) => () => void;
  onBakeStderr: (cb: (text: string) => void) => () => void;
  onBakeExit: (cb: (exitCode: number) => void) => () => void;
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
const materialSelect = $<HTMLSelectElement>("material");
const outputInput = $<HTMLInputElement>("output");
const outputPick = $<HTMLButtonElement>("output-pick");
const pvFieldset = $<HTMLFieldSetElement>("pv-fieldset");
const sclNodesInput = $<HTMLInputElement>("scl-nodes");
const sclDistancesInput = $<HTMLInputElement>("scl-distances");
const resampleInput = $<HTMLInputElement>("resample");
const ballisticFieldset = $<HTMLFieldSetElement>("ballistic-fieldset");
const openradiossRootInput = $<HTMLInputElement>("openradioss-root");
const openradiossRootPick = $<HTMLButtonElement>("openradioss-root-pick");
const rootnameInput = $<HTMLInputElement>("rootname");
const bakeGs101Btn = $<HTMLButtonElement>("bake-gs101");
const runBtn = $<HTMLButtonElement>("run");
const revealBtn = $<HTMLButtonElement>("reveal");
const demoBtn = $<HTMLButtonElement>("demo-gs001");
const statusEl = $<HTMLDivElement>("statusEl");
const violationsBox = $<HTMLDivElement>("violations");
const violationsList = $<HTMLUListElement>("violations-list");
const figuresBox = $<HTMLDivElement>("figures");
const figuresGrid = $<HTMLDivElement>("figures-grid");
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

const showViolations = (violations: readonly string[]) => {
  violationsList.replaceChildren(
    ...violations.map((v) => {
      const li = document.createElement("li");
      // textContent (not innerHTML) — violation strings come from the
      // CLI's stderr-equivalent and may contain user-supplied paths
      // or values; treat as untrusted.
      li.textContent = v;
      return li;
    })
  );
  violationsBox.hidden = violations.length === 0;
};

const clearViolations = () => {
  violationsList.replaceChildren();
  violationsBox.hidden = true;
};

// --- figure gallery -------------------------------------------------------

const _basenameOf = (p: string): string => {
  const i = Math.max(p.lastIndexOf("/"), p.lastIndexOf("\\"));
  return i >= 0 ? p.slice(i + 1) : p;
};

/**
 * Mimic Node's ``url.pathToFileURL`` in the browser-side renderer
 * (no node:url available with contextIsolation). Handles:
 *   - Windows backslash → forward slash
 *   - Drive-letter prefix (C:\…) → /C:/… (file:// requires it)
 *   - percent-encoding of reserved chars # ? that would otherwise be
 *     parsed as fragment / query, plus the spaces / non-ASCII that
 *     ``encodeURI`` covers
 *
 * Codex R1 LOW renderer.ts:141 — raw ``file://${absPath}`` did not
 * percent-encode # ? (legal POSIX filename chars) and was fragile on
 * Windows.
 */
const _pathToFileURL = (absPath: string): string => {
  let p = absPath.replace(/\\/g, "/");
  if (!p.startsWith("/")) p = "/" + p;
  return (
    "file://" +
    encodeURI(p).replace(/#/g, "%23").replace(/\?/g, "%3F")
  );
};

const _openLightbox = (src: string) => {
  const overlay = document.createElement("div");
  overlay.className = "figure-lightbox";
  const img = document.createElement("img");
  img.src = src;
  overlay.appendChild(img);
  overlay.addEventListener("click", () => overlay.remove());
  document.body.appendChild(overlay);
};

const addFigure = (absPath: string) => {
  // Electron can load file:// URLs from the main-process filesystem
  // because we run with sandbox:false + no CSP restriction on img-src
  // for local files. Cache-bust with a timestamp so a re-run with the
  // same paths refreshes the image instead of showing the stale one.
  const fileUrl = `${_pathToFileURL(absPath)}?t=${Date.now()}`;
  const fig = document.createElement("figure");
  const img = document.createElement("img");
  img.src = fileUrl;
  img.alt = _basenameOf(absPath);
  img.addEventListener("click", () => _openLightbox(fileUrl));
  const cap = document.createElement("figcaption");
  cap.textContent = _basenameOf(absPath);
  fig.appendChild(img);
  fig.appendChild(cap);
  figuresGrid.appendChild(fig);
  figuresBox.hidden = false;
};

const clearFigures = () => {
  figuresGrid.replaceChildren();
  figuresBox.hidden = true;
};

const updateFormState = () => {
  const isPv = kindSelect.value === "pressure-vessel";
  const isBallistic = kindSelect.value === "ballistic";
  pvFieldset.classList.toggle("hidden", !isPv);
  ballisticFieldset.classList.toggle("hidden", !isBallistic);
  // .frd is unused for ballistic — relax the check so the engineer
  // can run a ballistic report without picking a (non-existent) .frd.
  const inputReady = isBallistic
    ? Boolean(openradiossRootInput.value) && Boolean(rootnameInput.value.trim())
    : Boolean(frdInput.value) &&
      (!isPv ||
        (Boolean(sclNodesInput.value.trim()) &&
          Boolean(sclDistancesInput.value.trim())));
  const ready = inputReady && Boolean(outputInput.value);
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
rootnameInput.addEventListener("input", updateFormState);

openradiossRootPick.addEventListener("click", async () => {
  const picked = await window.api.openOpenradiossRoot();
  if (picked) {
    openradiossRootInput.value = picked;
    // Suggest a default output path next to the chosen frames dir.
    if (!outputInput.value) {
      const root = rootnameInput.value.trim() || "ballistic";
      outputInput.value = `${picked}/${root}_ballistic.docx`;
    }
    updateFormState();
  }
});

// --- run ------------------------------------------------------------------

window.api.onStdout(appendLog);
window.api.onStderr(appendLog);
window.api.onFigure(addFigure);

runBtn.addEventListener("click", async () => {
  runBtn.disabled = true;
  revealBtn.disabled = true;
  clearLog();
  clearViolations();
  clearFigures();
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
  } else if (kind === "ballistic") {
    req.openradiossRoot = openradiossRootInput.value;
    req.rootname = rootnameInput.value.trim();
  }
  // Empty option means "no material section" — leave req.material unset
  // so main.ts doesn't pass --material to the CLI.
  if (materialSelect.value) {
    req.material = materialSelect.value;
  }

  const result = await window.api.runReport(req);

  if (!result.ok && result.violations) {
    setStatus(
      `refused (${result.violations.length} violation${
        result.violations.length === 1 ? "" : "s"
      })`,
      "error"
    );
    showViolations(result.violations);
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
  // W6a: default the demo to Q345B — the typical "设备基础" wedge
  // case material per ADR-019 §"Open questions". Engineers running
  // the demo see a populated § 材料属性 section out of the box,
  // matching what they'd see on a real signed report.
  materialSelect.value = "Q345B";
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

// --- GS-101 demo bake (ballistic) -----------------------------------------

/**
 * Wire the bake button to the docker bake handler. Streams docker
 * stdout/stderr into the same log pre that report-cli uses, so the
 * engineer sees a single unified output panel.
 *
 * On success, pre-fills the ballistic fieldset with the scratch dir +
 * canonical rootname so the engineer's next click is "Choose…" for
 * the output .docx and then Run.
 */
window.api.onBakeStdout(appendLog);
window.api.onBakeStderr(appendLog);

bakeGs101Btn.addEventListener("click", async () => {
  bakeGs101Btn.disabled = true;
  runBtn.disabled = true;
  clearLog();
  clearViolations();
  setStatus("baking GS-101 demo (docker)…", "running");
  const result = await window.api.bakeGs101Demo();
  if (!result.ok) {
    setStatus(`bake failed (exit ${result.exitCode})`, "error");
    if (result.violations) showViolations(result.violations);
  } else {
    setStatus(`bake done — frames in ${result.scratchDir}`, "success");
    openradiossRootInput.value = result.scratchDir;
    rootnameInput.value = result.rootname;
    if (!outputInput.value) {
      outputInput.value = `${result.scratchDir}/${result.rootname}_ballistic.docx`;
    }
    // Switch the kind dropdown to ballistic so updateFormState reveals
    // the right fieldset and Run becomes clickable.
    kindSelect.value = "ballistic";
  }
  bakeGs101Btn.disabled = false;
  updateFormState();
});

void window.api.getDemoGs101Deck().then((deckDir) => {
  // The deck path itself is not needed by the renderer (main.ts
  // re-resolves it on each bake); we only use the existence check
  // to decide whether to advertise the bake button.
  if (!deckDir) return;
  bakeGs101Btn.hidden = false;
});

// --- material dropdown population (Codex R1 LOW PR #91 fix) --------------

/**
 * Populate the material <select> from the CLI's list-materials output.
 * Codex R1 PR #91 LOW: HTML used to hardcode <option> values, so a 13th
 * grade in materials.json would silently fall off the dropdown. Now
 * materials.json is the single source of truth — main.ts shells out to
 * `report-cli --list-materials` and we append one option per row.
 *
 * The empty default option is left in place by HTML so a CLI failure
 * doesn't strand the user with a non-functional dropdown.
 */
const populateMaterialDropdown = async (): Promise<void> => {
  let mats: MaterialOption[] = [];
  try {
    mats = await window.api.listMaterials();
  } catch {
    // CLI not on PATH or threw — empty dropdown is the fallback.
    return;
  }
  if (mats.length === 0) return;

  // Group by code_standard so the optgroup structure matches the
  // engineer's mental model (GB vs ASME).
  const byStandard = new Map<string, MaterialOption[]>();
  for (const m of mats) {
    const list = byStandard.get(m.codeStandard) ?? [];
    list.push(m);
    byStandard.set(m.codeStandard, list);
  }
  for (const [standard, list] of byStandard) {
    const optgroup = document.createElement("optgroup");
    optgroup.label = standard;
    for (const m of list) {
      const opt = document.createElement("option");
      opt.value = m.codeGrade;
      opt.textContent =
        `${m.codeGrade} — σ_y=${m.sigmaY} MPa, σ_u=${m.sigmaU} MPa`;
      opt.title = m.citation;
      optgroup.appendChild(opt);
    }
    materialSelect.appendChild(optgroup);
  }
};

void populateMaterialDropdown();

// --- init ------------------------------------------------------------------

updateFormState();
setStatus("idle");
