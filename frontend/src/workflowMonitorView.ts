// FM-04a M3 — Workflow Monitor view helpers (pure; no React).
//
// Status→token color map, the bracket-with-hole specimen geometry, and the
// "which layers are active at stage N" logic — ported faithfully from the M2
// prototype docs/demo/workflow_monitor.html so the in-app tab matches it, but
// recolored onto the warm-light design tokens (index.css) instead of the
// prototype's dark palette. The von-Mises field stays a literal scientific
// colormap (intentionally theme-independent, as on a real FEA viewport).
//
// Tier 1 / Tier 2 engineering candidate; not signed validation; not
// benchmark agreement.

import type { StageCatalogEntry, WorkflowRun, WorkflowStatus } from './workflowClient'

/** Status → warm-light design token (index.css). */
export const STATUS_TOKEN: Readonly<Record<WorkflowStatus, string>> = {
  pending: 'var(--text-muted)',
  running: 'var(--info-400)',
  success: 'var(--success-500)',
  warning: 'var(--warn-400)',
  failed: 'var(--danger-400)',
}

/** Short badge label per status (matches the prototype run-badge). */
export const STATUS_LABEL: Readonly<Record<WorkflowStatus, string>> = {
  pending: 'pending',
  running: 'running',
  success: 'SUCCESS',
  warning: 'WARNING',
  failed: 'FAILED',
}

/** The index of the stage currently in focus: selected → running → last-done. */
export function activeStageIndex(
  catalog: readonly StageCatalogEntry[],
  run: WorkflowRun | null,
  selectedStage: string | null,
): number {
  const indexOf = (stage: string | null): number =>
    stage === null ? -1 : catalog.findIndex((c) => c.stage === stage)
  if (selectedStage !== null) return indexOf(selectedStage)
  if (run !== null && run.currentStage !== null) return indexOf(run.currentStage)
  if (run !== null) {
    let last = -1
    for (const st of run.stages) {
      if (st.status !== 'pending') last = Math.max(last, indexOf(st.stage))
    }
    return last
  }
  return -1
}

/** Format a metric the way the prototype did (exponential for extreme magnitudes). */
export function formatMetric(v: number | string): string {
  if (typeof v === 'number') {
    if (Math.abs(v) >= 1e6 || (v !== 0 && Math.abs(v) < 1e-3)) return v.toExponential(3)
    return String(v)
  }
  return v
}

/** True once the active stage index has reached `stage`'s position in the catalog. */
export function stageReached(
  catalog: readonly StageCatalogEntry[],
  activeIdx: number,
  stage: string,
): boolean {
  const idx = catalog.findIndex((c) => c.stage === stage)
  return idx >= 0 && activeIdx >= idx
}

// --- bracket-with-hole specimen geometry (verbatim from the prototype) -------
export const VIZ_W = 520
export const VIZ_H = 300
export const PLATE_PATH =
  'M40 60 H440 a30 30 0 0 1 30 30 V210 a30 30 0 0 1 -30 30 H40 a30 30 0 0 1 -30 -30 V90 a30 30 0 0 1 30 -30 Z'
export const DEFORM_PATH = 'M40 64 H444 a30 30 0 0 1 30 30 V214 a30 30 0 0 1 -30 30 H40'
export const HOLE: Readonly<{ cx: number; cy: number; r: number }> = { cx: 330, cy: 150, r: 46 }

/** The stage id each cumulative SVG layer first appears at. */
export const LAYER_STAGE = {
  mesh: 'mesh_generation',
  quality: 'mesh_quality_check',
  stress: 'solver_run',
  bc: 'boundary_conditions',
  load: 'load_cases',
  deform: 'result_analysis',
} as const

/** Vertical + horizontal mesh-grid line coordinates (prototype spacing). */
export function meshGridLines(): { vertical: number[]; horizontal: number[] } {
  const vertical: number[] = []
  for (let x = 40; x <= 440; x += 26) vertical.push(x)
  const horizontal: number[] = []
  for (let y = 60; y <= 240; y += 24) horizontal.push(y)
  return { vertical, horizontal }
}

/** Fixed-edge BC hatch segment y-origins (left edge). */
export function bcHatchRows(): number[] {
  const rows: number[] = []
  for (let y = 66; y <= 234; y += 12) rows.push(y)
  return rows
}

/** Load-arrow x positions across the top edge. */
export function loadArrowColumns(): number[] {
  const cols: number[] = []
  for (let x = 120; x <= 400; x += 60) cols.push(x)
  return cols
}
