// FM-04a Phase 4 E — Cohort overview client.
//
// Tier 1 engineering candidate; not signed validation; not benchmark agreement.
//
// Typed fetch helper for `/api/v1/cohort-overview` + snake-to-camel
// parser + tone bands. Per-row score tone follows the reviewer-facing
// thresholds: ≥80 accent, ≥50 warning, <50 danger. The score is an
// evidence-presence signal only; the FM-04b blockers list is always
// rendered alongside.

import type { TrustCenterTone } from './trustCenterSummary.ts'

export interface CohortOverviewEntry {
  caseId: string
  completenessScore: number
  completenessScoreMax: number
  perforationMarker: string | null
  projectileInitialVelocityMPerS: number | null
  residualVelocityCandidateMPerS: number | null
  energyBalanceErrorPct: number | null
  energyAuditStatus: string
  convergenceCombinedVerdict: string
  lastModifiedUtc: string | null
  missingEvidenceCount: number
}

export interface CohortOverview {
  schemaVersion: string
  generatedAtUtc: string
  claimTier: string
  claimBoundary: string
  cohortCount: number
  meanScore: number | null
  completenessDistribution: Record<string, number>
  entries: CohortOverviewEntry[]
  tier2BlockersRemaining: string[]
  claimImpact: string
}

interface RawEntry {
  case_id?: string
  completeness_score?: number
  completeness_score_max?: number
  perforation_marker?: string | null
  projectile_initial_velocity_m_per_s?: number | null
  residual_velocity_candidate_m_per_s?: number | null
  energy_balance_error_pct?: number | null
  energy_audit_status?: string
  convergence_combined_verdict?: string
  last_modified_utc?: string | null
  missing_evidence_count?: number
}

interface RawCohortOverview {
  schema_version?: string
  generated_at_utc?: string
  claim_tier?: string
  claim_boundary?: string
  cohort_count?: number
  mean_score?: number | null
  completeness_distribution?: Record<string, number>
  entries?: RawEntry[]
  tier2_blockers_remaining?: string[]
  claim_impact?: string
}

function parseEntry(raw: RawEntry | null | undefined): CohortOverviewEntry | null {
  if (!raw || typeof raw !== 'object') return null
  if (typeof raw.case_id !== 'string') return null
  return {
    caseId: raw.case_id,
    completenessScore: raw.completeness_score ?? 0,
    completenessScoreMax: raw.completeness_score_max ?? 100,
    perforationMarker: raw.perforation_marker ?? null,
    projectileInitialVelocityMPerS: raw.projectile_initial_velocity_m_per_s ?? null,
    residualVelocityCandidateMPerS: raw.residual_velocity_candidate_m_per_s ?? null,
    energyBalanceErrorPct: raw.energy_balance_error_pct ?? null,
    energyAuditStatus: raw.energy_audit_status ?? 'unavailable',
    convergenceCombinedVerdict: raw.convergence_combined_verdict ?? 'insufficient_data',
    lastModifiedUtc: raw.last_modified_utc ?? null,
    missingEvidenceCount: raw.missing_evidence_count ?? 0,
  }
}

export function parseCohortOverview(
  raw: RawCohortOverview | null | undefined,
): CohortOverview | null {
  if (!raw || typeof raw !== 'object') return null
  if (!Array.isArray(raw.entries) && raw.entries !== undefined) return null
  return {
    schemaVersion: raw.schema_version ?? '',
    generatedAtUtc: raw.generated_at_utc ?? '',
    claimTier: raw.claim_tier ?? '',
    claimBoundary: raw.claim_boundary ?? '',
    cohortCount: raw.cohort_count ?? 0,
    meanScore: raw.mean_score ?? null,
    completenessDistribution: raw.completeness_distribution ?? {},
    entries: (raw.entries ?? [])
      .map(parseEntry)
      .filter((e): e is CohortOverviewEntry => e !== null),
    tier2BlockersRemaining: raw.tier2_blockers_remaining ?? [],
    claimImpact: raw.claim_impact ?? '',
  }
}

export interface CohortOverviewFetchResult {
  overview: CohortOverview | null
  source: 'live' | 'fallback'
  error?: string
}

export async function fetchCohortOverview(
  apiBase: string,
  signal?: AbortSignal,
): Promise<CohortOverviewFetchResult> {
  const url = `${apiBase.replace(/\/$/, '')}/cohort-overview`
  try {
    const res = await fetch(url, { signal })
    if (!res.ok) {
      throw new Error(`cohort-overview endpoint returned ${res.status}`)
    }
    const raw = (await res.json()) as RawCohortOverview
    const parsed = parseCohortOverview(raw)
    if (!parsed) {
      throw new Error('cohort-overview payload missing entries')
    }
    return { overview: parsed, source: 'live' }
  } catch (err) {
    return {
      overview: null,
      source: 'fallback',
      error: err instanceof Error ? err.message : String(err),
    }
  }
}

// Score tone bands: ≥80 accent (green), ≥50 warning (amber), <50 danger (red).
// 0 score is muted to avoid a sea of red on empty fixtures.
export function scoreTone(score: number): TrustCenterTone {
  if (score === 0) return 'muted'
  if (score >= 80) return 'accent'
  if (score >= 50) return 'warning'
  return 'danger'
}

export type CohortSortKey = 'score_desc' | 'score_asc' | 'case_id_asc' | 'recency_desc'

export function sortCohortEntries(
  entries: CohortOverviewEntry[], key: CohortSortKey,
): CohortOverviewEntry[] {
  const copy = [...entries]
  if (key === 'score_desc') {
    return copy.sort((a, b) => b.completenessScore - a.completenessScore)
  }
  if (key === 'score_asc') {
    return copy.sort((a, b) => a.completenessScore - b.completenessScore)
  }
  if (key === 'recency_desc') {
    return copy.sort((a, b) => {
      const at = a.lastModifiedUtc ?? ''
      const bt = b.lastModifiedUtc ?? ''
      if (at === bt) return 0
      return bt < at ? -1 : 1
    })
  }
  // case_id_asc fallback (also alphabetical default)
  return copy.sort((a, b) => a.caseId.localeCompare(b.caseId))
}
