// FM-04a Phase 3 D — Convergence study client.
//
// Tier 1 engineering candidate; not signed validation; not benchmark agreement.
//
// Typed fetch helper for `/api/v1/convergence-study/<case-id>` plus a
// snake-to-camel parser for the orchestrator payload produced by the
// Phase 2 B convergence_orchestrator builder. Schema is two 1-axis
// sweeps (mesh + dt) each with their own candidate_stability verdict,
// plus a combined verdict at the top level.

import { convergenceTone, type TrustCenterTone } from './trustCenterSummary.ts'

export interface ConvergenceStudyRun {
  label: string
  axisValue: number
  metricValue: number
}

export interface ConvergenceStudyAxis {
  axis: string
  axisLabel: string
  runCount: number
  relativeChangePct: number | null
  candidateStability: string
  runs: ConvergenceStudyRun[]
  heldValueLabel: string
  heldValue: number | null
}

export interface EnergyBalanceObservation {
  status: string
  rowsWithBalanceError: number
  rowsTotal: number
  minPct: number | null
  maxPct: number | null
  meanPct: number | null
}

export interface ConvergenceStudy {
  schemaVersion: string
  caseId: string
  studyMetric: string
  combinedVerdict: string
  rowCount: number
  tolerancePct: number
  meshSweep: ConvergenceStudyAxis
  dtSweep: ConvergenceStudyAxis
  claimBoundary: string
  claimImpact: string
  energyBalanceObservation: EnergyBalanceObservation
}

interface RawRun {
  label?: string
  mesh_axis_value?: number
  dt_axis_value?: number
  metric_value?: number
}

interface RawAxis {
  axis?: string
  axis_label?: string
  run_count?: number
  relative_change_pct?: number | null
  candidate_stability?: string
  runs?: RawRun[]
  held_dt_label?: string
  held_dt_axis_value?: number | null
  held_mesh_label?: string
  held_mesh_axis_value?: number | null
}

interface RawEnergyBalanceObservation {
  status?: string
  rows_with_balance_error?: number
  rows_total?: number
  min_pct?: number | null
  max_pct?: number | null
  mean_pct?: number | null
}

interface RawConvergenceStudy {
  schema_version?: string
  case_id?: string
  study_metric?: string
  combined_verdict?: string
  row_count?: number
  tolerance_pct?: number
  mesh_sweep?: RawAxis
  dt_sweep?: RawAxis
  claim_boundary?: string
  claim_impact?: string
  energy_balance_observation?: RawEnergyBalanceObservation
}

function parseRunMesh(raw: RawRun): ConvergenceStudyRun {
  return {
    label: raw.label ?? '',
    axisValue: raw.mesh_axis_value ?? 0,
    metricValue: raw.metric_value ?? 0,
  }
}

function parseRunDt(raw: RawRun): ConvergenceStudyRun {
  return {
    label: raw.label ?? '',
    axisValue: raw.dt_axis_value ?? 0,
    metricValue: raw.metric_value ?? 0,
  }
}

function parseMeshAxis(raw: RawAxis | undefined): ConvergenceStudyAxis {
  return {
    axis: raw?.axis ?? 'unknown',
    axisLabel: raw?.axis_label ?? '',
    runCount: raw?.run_count ?? 0,
    relativeChangePct: raw?.relative_change_pct ?? null,
    candidateStability: raw?.candidate_stability ?? 'unknown',
    runs: (raw?.runs ?? []).map(parseRunMesh),
    heldValueLabel: raw?.held_dt_label ?? '',
    heldValue: raw?.held_dt_axis_value ?? null,
  }
}

function parseDtAxis(raw: RawAxis | undefined): ConvergenceStudyAxis {
  return {
    axis: raw?.axis ?? 'unknown',
    axisLabel: raw?.axis_label ?? '',
    runCount: raw?.run_count ?? 0,
    relativeChangePct: raw?.relative_change_pct ?? null,
    candidateStability: raw?.candidate_stability ?? 'unknown',
    runs: (raw?.runs ?? []).map(parseRunDt),
    heldValueLabel: raw?.held_mesh_label ?? '',
    heldValue: raw?.held_mesh_axis_value ?? null,
  }
}

export function parseConvergenceStudy(
  raw: RawConvergenceStudy | null | undefined,
): ConvergenceStudy | null {
  if (!raw || typeof raw !== 'object') return null
  if (typeof raw.case_id !== 'string') return null
  const energy = raw.energy_balance_observation ?? {}
  return {
    schemaVersion: raw.schema_version ?? '',
    caseId: raw.case_id,
    studyMetric: raw.study_metric ?? 'residual_velocity_m_per_s',
    combinedVerdict: raw.combined_verdict ?? 'insufficient_data',
    rowCount: raw.row_count ?? 0,
    tolerancePct: raw.tolerance_pct ?? 5,
    meshSweep: parseMeshAxis(raw.mesh_sweep),
    dtSweep: parseDtAxis(raw.dt_sweep),
    claimBoundary: raw.claim_boundary ?? '',
    claimImpact: raw.claim_impact ?? '',
    energyBalanceObservation: {
      status: energy.status ?? 'unavailable',
      rowsWithBalanceError: energy.rows_with_balance_error ?? 0,
      rowsTotal: energy.rows_total ?? 0,
      minPct: energy.min_pct ?? null,
      maxPct: energy.max_pct ?? null,
      meanPct: energy.mean_pct ?? null,
    },
  }
}

export interface ConvergenceStudyFetchResult {
  study: ConvergenceStudy | null
  source: 'live' | 'fallback'
  error?: string
}

export async function fetchConvergenceStudy(
  apiBase: string,
  caseId: string,
  signal?: AbortSignal,
): Promise<ConvergenceStudyFetchResult> {
  const url = `${apiBase.replace(/\/$/, '')}/convergence-study/${encodeURIComponent(caseId)}`
  try {
    const res = await fetch(url, { signal })
    if (!res.ok) {
      throw new Error(`convergence-study endpoint returned ${res.status}`)
    }
    const raw = (await res.json()) as RawConvergenceStudy
    const parsed = parseConvergenceStudy(raw)
    if (!parsed) {
      throw new Error('convergence-study payload missing case_id')
    }
    return { study: parsed, source: 'live' }
  } catch (err) {
    return {
      study: null,
      source: 'fallback',
      error: err instanceof Error ? err.message : String(err),
    }
  }
}

// Per-axis tone routes through trustCenterSummary.convergenceTone so the
// viewer and the Trust Center card stay aligned.
export function axisTone(axisStability: string): TrustCenterTone {
  return convergenceTone({
    combinedVerdict: axisStability,
    meshSweepStability: axisStability,
    dtSweepStability: axisStability,
    rowCount: 1,
    tolerancePct: 5,
  })
}

export function combinedVerdictTone(study: ConvergenceStudy): TrustCenterTone {
  return convergenceTone({
    combinedVerdict: study.combinedVerdict,
    meshSweepStability: study.meshSweep.candidateStability,
    dtSweepStability: study.dtSweep.candidateStability,
    rowCount: study.rowCount,
    tolerancePct: study.tolerancePct,
  })
}

export function rowDeviationTone(
  reference: number,
  runMetric: number,
  tolerancePct: number,
): TrustCenterTone {
  if (reference === 0) return 'muted'
  const abs = Math.abs((runMetric - reference) / reference) * 100
  if (abs <= 0.01) return 'accent'
  if (abs <= tolerancePct) return 'accent'
  if (abs <= tolerancePct * 3) return 'warning'
  return 'danger'
}

export function combinedVerdictLabel(study: ConvergenceStudy): string {
  return (
    `${study.combinedVerdict} · mesh ${study.meshSweep.candidateStability} · ` +
    `dt ${study.dtSweep.candidateStability} · ${study.rowCount} row(s) at ±${study.tolerancePct}%`
  )
}
