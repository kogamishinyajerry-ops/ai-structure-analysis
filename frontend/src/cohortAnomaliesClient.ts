// FM-04a Phase 8 E — Cohort anomaly detection client.
//
// Tier 1 engineering candidate; not signed validation; not benchmark agreement.

export const SUPPORTED_ANOMALY_SEVERITIES = ['info', 'warn', 'danger'] as const
export type AnomalySeverity = (typeof SUPPORTED_ANOMALY_SEVERITIES)[number]

export interface AnomalyEvent {
  caseId: string
  axis: string
  score: number
  cohortMean: number
  cohortStdev: number
  zScore: number
  severity: AnomalySeverity
}

export interface CohortAnomaliesReport {
  schemaVersion: string
  generatedAtUtc: string
  claimTier: string
  claimBoundary: string
  cohortCount: number
  anomalyCount: number
  anomalies: AnomalyEvent[]
  claimImpact: string
}

interface RawAnomaly {
  case_id?: string
  axis?: string
  score?: number
  cohort_mean?: number
  cohort_stdev?: number
  z_score?: number
  severity?: string
}

interface RawReport {
  schema_version?: string
  generated_at_utc?: string
  claim_tier?: string
  claim_boundary?: string
  cohort_count?: number
  anomaly_count?: number
  anomalies?: RawAnomaly[]
  claim_impact?: string
}

function parseSeverity(raw: string | undefined): AnomalySeverity {
  if (raw === 'warn' || raw === 'danger') return raw
  return 'info'
}

function parseAnomaly(raw: RawAnomaly | null | undefined): AnomalyEvent | null {
  if (!raw || typeof raw !== 'object') return null
  if (typeof raw.case_id !== 'string' || typeof raw.axis !== 'string') return null
  return {
    caseId: raw.case_id,
    axis: raw.axis,
    score: raw.score ?? 0,
    cohortMean: raw.cohort_mean ?? 0,
    cohortStdev: raw.cohort_stdev ?? 0,
    zScore: raw.z_score ?? 0,
    severity: parseSeverity(raw.severity),
  }
}

export function parseCohortAnomaliesReport(
  raw: RawReport | null | undefined,
): CohortAnomaliesReport | null {
  if (!raw || typeof raw !== 'object') return null
  return {
    schemaVersion: raw.schema_version ?? '',
    generatedAtUtc: raw.generated_at_utc ?? '',
    claimTier: raw.claim_tier ?? '',
    claimBoundary: raw.claim_boundary ?? '',
    cohortCount: raw.cohort_count ?? 0,
    anomalyCount: raw.anomaly_count ?? 0,
    anomalies: (raw.anomalies ?? [])
      .map(parseAnomaly)
      .filter((a): a is AnomalyEvent => a !== null),
    claimImpact: raw.claim_impact ?? '',
  }
}

export interface CohortAnomaliesFetchResult {
  report: CohortAnomaliesReport | null
  source: 'live' | 'fallback'
  error?: string
}

export async function fetchCohortAnomalies(
  apiBase: string,
  signal?: AbortSignal,
): Promise<CohortAnomaliesFetchResult> {
  const url = `${apiBase.replace(/\/$/, '')}/cohort-anomalies`
  try {
    const res = await fetch(url, { signal })
    if (!res.ok) {
      throw new Error(`cohort-anomalies endpoint returned ${res.status}`)
    }
    const raw = (await res.json()) as RawReport
    const parsed = parseCohortAnomaliesReport(raw)
    if (!parsed) {
      throw new Error('cohort-anomalies payload is malformed')
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
