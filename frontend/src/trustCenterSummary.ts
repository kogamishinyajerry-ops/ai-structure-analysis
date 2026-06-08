// FM-04a Phase 2 D — Trust Center summary helpers.
//
// Tier 1 engineering candidate; not signed validation; not benchmark agreement.
//
// Pure tone-selection logic for the three industrial review cards added by
// Phase 2 D: energy_balance_status, convergence_study_status, and
// candidate_case_selection. Keeping the tone rules in a pure module makes
// them unit-testable without React.

export type TrustCenterTone = 'accent' | 'warning' | 'danger' | 'muted'

// -------------------- energy_balance_status --------------------

export type EnergyAuditStatus =
  | 'closed_aggregate'
  | 'partial_candidate'
  | 'unavailable'
  | string

export interface EnergyBalanceSummary {
  status: EnergyAuditStatus
  initialKineticEnergyJ: number | null
  residualKineticEnergyJ: number | null
  aggregateInternalEnergyJ: number | null
  externalWorkJ: number | null
  energyBalanceErrorPct: number | null
  claimImpact: string
}

export const ENERGY_BALANCE_ACCEPTABLE_ERROR_PCT = 5.0
export const ENERGY_BALANCE_WARNING_ERROR_PCT = 15.0

export function energyBalanceTone(summary: EnergyBalanceSummary): TrustCenterTone {
  if (summary.status === 'unavailable') return 'muted'
  if (summary.status !== 'closed_aggregate') return 'warning'
  const err = summary.energyBalanceErrorPct
  if (err === null || err === undefined) return 'warning'
  if (Math.abs(err) <= ENERGY_BALANCE_ACCEPTABLE_ERROR_PCT) return 'accent'
  if (Math.abs(err) <= ENERGY_BALANCE_WARNING_ERROR_PCT) return 'warning'
  return 'danger'
}

export function energyBalanceLabel(summary: EnergyBalanceSummary): string {
  if (summary.status === 'closed_aggregate') {
    const err = summary.energyBalanceErrorPct
    if (err === null || err === undefined) return 'closed aggregate · balance error unavailable'
    return `closed aggregate · balance error ${Math.abs(err).toFixed(3)}%`
  }
  if (summary.status === 'partial_candidate') return 'partial candidate · KE only'
  if (summary.status === 'unavailable') return 'unavailable'
  return summary.status
}

// -------------------- convergence_study_status --------------------

export type ConvergenceVerdict =
  | 'candidate_observed_stable'
  | 'candidate_observed_unstable'
  | 'insufficient_data'
  | string

export interface ConvergenceStudySummary {
  combinedVerdict: ConvergenceVerdict
  meshSweepStability: ConvergenceVerdict | 'unknown'
  dtSweepStability: ConvergenceVerdict | 'unknown'
  rowCount: number
  tolerancePct: number
}

export function convergenceTone(summary: ConvergenceStudySummary): TrustCenterTone {
  if (summary.combinedVerdict === 'candidate_observed_stable') return 'accent'
  if (summary.combinedVerdict === 'candidate_observed_unstable') return 'danger'
  return 'warning'
}

export function convergenceLabel(summary: ConvergenceStudySummary): string {
  return (
    `${summary.combinedVerdict} · mesh ${summary.meshSweepStability} · ` +
    `dt ${summary.dtSweepStability} · ${summary.rowCount} row(s) at ±${summary.tolerancePct}%`
  )
}

// -------------------- candidate_case_selection --------------------

export interface CandidateCaseSelectionSummary {
  caseId: string | null
  starterDeckRelpath: string | null
  engineDeckRelpath: string | null
  generatorScriptRelpath: string | null
  source: 'live' | 'fallback'
}

export function candidateCaseSelectionTone(
  summary: CandidateCaseSelectionSummary,
): TrustCenterTone {
  if (!summary.caseId) return 'warning'
  if (!summary.starterDeckRelpath || !summary.engineDeckRelpath) return 'warning'
  return summary.source === 'live' ? 'accent' : 'warning'
}

export function candidateCaseSelectionLabel(
  summary: CandidateCaseSelectionSummary,
): string {
  if (!summary.caseId) return 'no candidate case selected'
  const gen = summary.generatorScriptRelpath ?? 'no generator script'
  return (
    `${summary.caseId} · starter+engine + ${gen} · source ${summary.source}`
  )
}

// Shared Tier 1 boundary banner — every Trust Center card surfaces this so
// non-FM-04a-author readers never confuse Phase 2 D output with stronger claims.
export const TIER1_BANNER =
  'Tier 1 engineering candidate; not signed validation; not benchmark agreement'
