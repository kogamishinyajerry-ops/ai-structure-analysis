// FM-04a Phase 8 D — Cohort executive summary client.
//
// Tier 1 engineering candidate; not signed validation; not benchmark agreement.

export const HEALTH_BUCKETS = ['healthy', 'watching', 'regressed'] as const
export type HealthBucket = (typeof HEALTH_BUCKETS)[number]

export interface CohortExecutiveCaseRow {
  caseId: string
  latestTrustScore: number | null
  latestSnapshotLabel: string | null
  latestSignoffVerdict: string | null
  alarmCountWarnOrDanger: number
  bucket: HealthBucket
}

export interface CohortExecutiveSummary {
  schemaVersion: string
  generatedAtUtc: string
  claimTier: string
  claimBoundary: string
  cohortCount: number
  healthyCount: number
  watchingCount: number
  regressedCount: number
  cases: CohortExecutiveCaseRow[]
  claimImpact: string
}

interface RawCaseRow {
  case_id?: string
  latest_trust_score?: number | null
  latest_snapshot_label?: string | null
  latest_signoff_verdict?: string | null
  alarm_count_warn_or_danger?: number
  bucket?: string
}

interface RawSummary {
  schema_version?: string
  generated_at_utc?: string
  claim_tier?: string
  claim_boundary?: string
  cohort_count?: number
  healthy_count?: number
  watching_count?: number
  regressed_count?: number
  cases?: RawCaseRow[]
  claim_impact?: string
}

function parseBucket(raw: string | undefined): HealthBucket {
  if (raw === 'healthy' || raw === 'watching' || raw === 'regressed') return raw
  return 'regressed' // most conservative fallback
}

function parseRow(raw: RawCaseRow | null | undefined): CohortExecutiveCaseRow | null {
  if (!raw || typeof raw !== 'object') return null
  if (typeof raw.case_id !== 'string') return null
  return {
    caseId: raw.case_id,
    latestTrustScore: raw.latest_trust_score ?? null,
    latestSnapshotLabel: raw.latest_snapshot_label ?? null,
    latestSignoffVerdict: raw.latest_signoff_verdict ?? null,
    alarmCountWarnOrDanger: raw.alarm_count_warn_or_danger ?? 0,
    bucket: parseBucket(raw.bucket),
  }
}

export function parseCohortExecutiveSummary(
  raw: RawSummary | null | undefined,
): CohortExecutiveSummary | null {
  if (!raw || typeof raw !== 'object') return null
  return {
    schemaVersion: raw.schema_version ?? '',
    generatedAtUtc: raw.generated_at_utc ?? '',
    claimTier: raw.claim_tier ?? '',
    claimBoundary: raw.claim_boundary ?? '',
    cohortCount: raw.cohort_count ?? 0,
    healthyCount: raw.healthy_count ?? 0,
    watchingCount: raw.watching_count ?? 0,
    regressedCount: raw.regressed_count ?? 0,
    cases: (raw.cases ?? [])
      .map(parseRow)
      .filter((r): r is CohortExecutiveCaseRow => r !== null),
    claimImpact: raw.claim_impact ?? '',
  }
}

export interface CohortExecutiveSummaryFetchResult {
  summary: CohortExecutiveSummary | null
  source: 'live' | 'fallback'
  error?: string
}

export async function fetchCohortExecutiveSummary(
  apiBase: string,
  signal?: AbortSignal,
): Promise<CohortExecutiveSummaryFetchResult> {
  const url = `${apiBase.replace(/\/$/, '')}/cohort-executive-summary`
  try {
    const res = await fetch(url, { signal })
    if (!res.ok) {
      throw new Error(`cohort-executive-summary endpoint returned ${res.status}`)
    }
    const raw = (await res.json()) as RawSummary
    const parsed = parseCohortExecutiveSummary(raw)
    if (!parsed) {
      throw new Error('cohort-executive-summary payload is malformed')
    }
    return { summary: parsed, source: 'live' }
  } catch (err) {
    return {
      summary: null,
      source: 'fallback',
      error: err instanceof Error ? err.message : 'unknown error',
    }
  }
}

export function bucketTone(bucket: HealthBucket): 'info' | 'warn' | 'danger' {
  if (bucket === 'healthy') return 'info'
  if (bucket === 'watching') return 'warn'
  return 'danger'
}
