// FM-04a Phase 10 B — Cohort trend-slope anomaly client.
//
// Tier 1 engineering candidate; not signed validation; not benchmark agreement.
//
// Mirrors `cohortAnomaliesClient.ts` (Phase 8 E) but reads
// `/api/v1/cohort-trend-anomalies` (Phase 9 D). Trend anomalies are
// per-case within-timeline slope events, orthogonal to the z-score
// cohort outlier endpoint.
//
// Defensive `parseSeverity` falls back to `'info'` for unknown values
// so the panel never silently surfaces an unrecognized severity bucket
// (Phase 10 anti-gaming guard X: -2 — most-conservative fallback).

export const SUPPORTED_TREND_SEVERITIES = ['info', 'warn', 'danger'] as const
export type TrendSeverity = (typeof SUPPORTED_TREND_SEVERITIES)[number]

export interface TrendEvent {
  caseId: string
  axis: string
  slope: number
  pointCount: number
  severity: TrendSeverity
}

export interface CohortTrendAnomaliesReport {
  schemaVersion: string
  generatedAtUtc: string
  claimTier: string
  claimBoundary: string
  cohortCount: number
  pointCountFloor: number
  anomalyCount: number
  anomalies: TrendEvent[]
  claimImpact: string
}

interface RawEvent {
  case_id?: string
  axis?: string
  slope?: number
  point_count?: number
  severity?: string
}

interface RawReport {
  schema_version?: string
  generated_at_utc?: string
  claim_tier?: string
  claim_boundary?: string
  cohort_count?: number
  point_count_floor?: number
  anomaly_count?: number
  anomalies?: RawEvent[]
  claim_impact?: string
}

function parseSeverity(raw: string | undefined): TrendSeverity {
  if (raw === 'warn' || raw === 'danger') return raw
  return 'info'
}

function parseEvent(raw: RawEvent | null | undefined): TrendEvent | null {
  if (!raw || typeof raw !== 'object') return null
  if (typeof raw.case_id !== 'string' || typeof raw.axis !== 'string') return null
  return {
    caseId: raw.case_id,
    axis: raw.axis,
    slope: raw.slope ?? 0,
    pointCount: raw.point_count ?? 0,
    severity: parseSeverity(raw.severity),
  }
}

export function parseCohortTrendAnomaliesReport(
  raw: RawReport | null | undefined,
): CohortTrendAnomaliesReport | null {
  if (!raw || typeof raw !== 'object') return null
  return {
    schemaVersion: raw.schema_version ?? '',
    generatedAtUtc: raw.generated_at_utc ?? '',
    claimTier: raw.claim_tier ?? '',
    claimBoundary: raw.claim_boundary ?? '',
    cohortCount: raw.cohort_count ?? 0,
    pointCountFloor: raw.point_count_floor ?? 3,
    anomalyCount: raw.anomaly_count ?? 0,
    anomalies: (raw.anomalies ?? [])
      .map(parseEvent)
      .filter((e): e is TrendEvent => e !== null),
    claimImpact: raw.claim_impact ?? '',
  }
}

export interface CohortTrendAnomaliesFetchResult {
  report: CohortTrendAnomaliesReport | null
  source: 'live' | 'fallback'
  error?: string
}

export async function fetchCohortTrendAnomalies(
  apiBase: string,
  signal?: AbortSignal,
): Promise<CohortTrendAnomaliesFetchResult> {
  const url = `${apiBase.replace(/\/$/, '')}/cohort-trend-anomalies`
  try {
    const res = await fetch(url, { signal })
    if (!res.ok) {
      throw new Error(`cohort-trend-anomalies endpoint returned ${res.status}`)
    }
    const raw = (await res.json()) as RawReport
    const parsed = parseCohortTrendAnomaliesReport(raw)
    if (!parsed) {
      throw new Error('cohort-trend-anomalies payload is malformed')
    }
    return { report: parsed, source: 'live' }
  } catch (err) {
    return {
      report: null,
      source: 'fallback',
      error: err instanceof Error ? err.message : 'unknown error',
    }
  }
}
