// FM-04a Phase 7 C — Trust score regression alarms client.
//
// Tier 1 engineering candidate; not signed validation; not benchmark agreement.
//
// Typed fetch helper for `/api/v1/trust-score-alerts/<case-id>`. Preserves
// schemaVersion + per-alert severity for tone-coded UI rendering.

export type AlertSeverity = 'info' | 'warn' | 'danger'

export interface AxisDeltas {
  completeness: number
  convergenceStability: number
  energyAuditClosure: number
  reproducibilityClean: number
}

export interface TrustScoreAlertEvent {
  fromSnapshot: string
  toSnapshot: string
  fromTrustScore: number
  toTrustScore: number
  delta: number
  severity: AlertSeverity
  primaryAxisShift: string
  axisDeltas: AxisDeltas
}

export interface TrustScoreAlertReport {
  schemaVersion: string
  caseId: string
  claimTier: string
  claimBoundary: string
  generatedAtUtc: string
  thresholdDelta: number
  alertCount: number
  alerts: TrustScoreAlertEvent[]
  claimImpact: string
}

interface RawAxisDeltas {
  completeness?: number
  convergence_stability?: number
  energy_audit_closure?: number
  reproducibility_clean?: number
}

interface RawAlertEvent {
  from_snapshot?: string
  to_snapshot?: string
  from_trust_score?: number
  to_trust_score?: number
  delta?: number
  severity?: string
  primary_axis_shift?: string
  axis_deltas?: RawAxisDeltas
}

interface RawAlertReport {
  schema_version?: string
  case_id?: string
  claim_tier?: string
  claim_boundary?: string
  generated_at_utc?: string
  threshold_delta?: number
  alert_count?: number
  alerts?: RawAlertEvent[]
  claim_impact?: string
}

function parseSeverity(raw: string | undefined): AlertSeverity {
  if (raw === 'warn' || raw === 'danger') return raw
  return 'info'
}

function parseAxisDeltas(raw: RawAxisDeltas | undefined): AxisDeltas {
  return {
    completeness: raw?.completeness ?? 0,
    convergenceStability: raw?.convergence_stability ?? 0,
    energyAuditClosure: raw?.energy_audit_closure ?? 0,
    reproducibilityClean: raw?.reproducibility_clean ?? 0,
  }
}

function parseAlertEvent(
  raw: RawAlertEvent | null | undefined,
): TrustScoreAlertEvent | null {
  if (!raw || typeof raw !== 'object') return null
  if (
    typeof raw.from_snapshot !== 'string' ||
    typeof raw.to_snapshot !== 'string'
  ) {
    return null
  }
  return {
    fromSnapshot: raw.from_snapshot,
    toSnapshot: raw.to_snapshot,
    fromTrustScore: raw.from_trust_score ?? 0,
    toTrustScore: raw.to_trust_score ?? 0,
    delta: raw.delta ?? 0,
    severity: parseSeverity(raw.severity),
    primaryAxisShift: raw.primary_axis_shift ?? '',
    axisDeltas: parseAxisDeltas(raw.axis_deltas),
  }
}

export function parseTrustScoreAlertReport(
  raw: RawAlertReport | null | undefined,
): TrustScoreAlertReport | null {
  if (!raw || typeof raw !== 'object') return null
  if (typeof raw.case_id !== 'string') return null
  return {
    schemaVersion: raw.schema_version ?? '',
    caseId: raw.case_id,
    claimTier: raw.claim_tier ?? '',
    claimBoundary: raw.claim_boundary ?? '',
    generatedAtUtc: raw.generated_at_utc ?? '',
    thresholdDelta: raw.threshold_delta ?? 10,
    alertCount: raw.alert_count ?? 0,
    alerts: (raw.alerts ?? [])
      .map(parseAlertEvent)
      .filter((a): a is TrustScoreAlertEvent => a !== null),
    claimImpact: raw.claim_impact ?? '',
  }
}

export interface TrustScoreAlertsFetchResult {
  report: TrustScoreAlertReport | null
  source: 'live' | 'fallback'
  error?: string
}

export async function fetchTrustScoreAlerts(
  apiBase: string,
  caseId: string,
  signal?: AbortSignal,
  thresholdDelta = 10,
): Promise<TrustScoreAlertsFetchResult> {
  const params = new URLSearchParams({
    threshold_delta: String(thresholdDelta),
  })
  const url = `${apiBase.replace(/\/$/, '')}/trust-score-alerts/${encodeURIComponent(
    caseId,
  )}?${params.toString()}`
  try {
    const res = await fetch(url, { signal })
    if (!res.ok) {
      throw new Error(`trust-score-alerts endpoint returned ${res.status}`)
    }
    const raw = (await res.json()) as RawAlertReport
    const parsed = parseTrustScoreAlertReport(raw)
    if (!parsed) {
      throw new Error('trust-score-alerts payload is malformed')
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
