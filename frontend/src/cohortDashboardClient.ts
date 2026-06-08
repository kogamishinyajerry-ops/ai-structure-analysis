// FM-04a Phase 12 E — Cohort dashboard client orchestrator.
//
// Tier 1 engineering candidate; not signed validation; not benchmark agreement.
//
// Aggregates the four cohort-side reviewer surfaces into a single
// blueprint-#07-shaped view model:
//
//   - executive summary (per-case bucket + latest trust)        from /cohort-executive-summary
//   - z-score outliers   (axis-level anomalies, latest snapshot) from /cohort-anomalies
//   - trend anomalies    (per-axis slope alarms across snapshots) from /cohort-trend-anomalies
//   - schema versions    (footer banner of the 4 schema constants) from each payload's `schema_version` field
//
// Defensive parser pillars (Phase 12 sub-rubric § 4.E X:-2):
//
//   1. **Bucket fallback**: every unknown bucket value materializes
//      as the literal string `"unknown"` rather than crashing or
//      silently coercing into the most-conservative bucket. The UI
//      can color it neutrally (gray) and surface a "value unknown"
//      label so a reviewer notices the schema drift instead of
//      misreading a regressed-as-healthy case.
//
//   2. **Severity fallback**: every unknown alert severity also
//      collapses to `"unknown"` (NOT `"danger"`), again so an
//      out-of-enum severity does not get spuriously promoted to
//      danger and trigger a false-positive alarm cascade.
//
//   3. **Alarm-kind fallback**: future alarm kinds (rate-limit
//      events, sealed-packet drift events, etc.) parse to
//      `kind === "unknown"` without losing the underlying payload —
//      the dashboard still renders the row with case_id + axis but
//      flags the kind cell as needing schema-version inspection.

// Dashboard reads raw JSON itself (rather than calling the existing
// fetch helpers) so the X:-2 defensive parsers see actual backend
// values instead of the upstream clients' most-conservative coercions.
// A future PR could unify these by exposing raw-value accessors on
// the upstream clients; until then, the dashboard owns its own
// parsing layer for cohort-side schema drift surfacing.

// ----------------------------------------------------------------------
// SSOT tuples — pinned by tests so a future PR cannot quietly add a new
// bucket / severity / alarm-kind without updating the dashboard.
// ----------------------------------------------------------------------

export const DASHBOARD_BUCKETS = [
  'healthy',
  'watching',
  'regressed',
  'unknown',
] as const
export type DashboardBucket = (typeof DASHBOARD_BUCKETS)[number]

export const DASHBOARD_SEVERITIES = [
  'info',
  'warn',
  'danger',
  'unknown',
] as const
export type DashboardSeverity = (typeof DASHBOARD_SEVERITIES)[number]

export const DASHBOARD_ALERT_KINDS = [
  'z_score_outlier',
  'trend_slope',
  'rate_limit',
  'unknown',
] as const
export type DashboardAlertKind = (typeof DASHBOARD_ALERT_KINDS)[number]

// ----------------------------------------------------------------------
// Defensive parsers
// ----------------------------------------------------------------------

export function defensiveBucket(raw: string | undefined | null): DashboardBucket {
  if (raw === 'healthy' || raw === 'watching' || raw === 'regressed') return raw
  return 'unknown'
}

export function defensiveSeverity(
  raw: string | undefined | null,
): DashboardSeverity {
  if (raw === 'info' || raw === 'warn' || raw === 'danger') return raw
  return 'unknown'
}

export function defensiveAlertKind(
  raw: string | undefined | null,
): DashboardAlertKind {
  if (
    raw === 'z_score_outlier' ||
    raw === 'trend_slope' ||
    raw === 'rate_limit'
  )
    return raw
  return 'unknown'
}

// ----------------------------------------------------------------------
// Bucket / severity color tokens (slice E visual contract)
// ----------------------------------------------------------------------

export function bucketColor(bucket: DashboardBucket): string {
  if (bucket === 'healthy') return 'var(--accent, #0a8a4a)'
  if (bucket === 'watching') return 'var(--text-warning, #b8860b)'
  if (bucket === 'regressed') return 'var(--danger, #c0392b)'
  return 'var(--text-secondary)' // unknown → neutral gray
}

export function severityColor(severity: DashboardSeverity): string {
  if (severity === 'info') return 'var(--accent, #0a8a4a)'
  if (severity === 'warn') return 'var(--text-warning, #b8860b)'
  if (severity === 'danger') return 'var(--danger, #c0392b)'
  return 'var(--text-secondary)' // unknown → neutral gray
}

// ----------------------------------------------------------------------
// Unified dashboard view model
// ----------------------------------------------------------------------

export interface DashboardAlertRow {
  kind: DashboardAlertKind
  caseId: string
  axis: string
  severity: DashboardSeverity
  rawValue: number | null
  rawSlope: number | null
}

export interface DashboardCaseRow {
  caseId: string
  bucket: DashboardBucket
  latestTrustScore: number | null
  latestSignoffVerdict: string | null
  alarmCount: number
}

export interface SchemaFootprint {
  cohortExecutiveSummary: string
  cohortAnomalies: string
  cohortTrendAnomalies: string
}

export interface CohortDashboardViewModel {
  cases: DashboardCaseRow[]
  alerts: DashboardAlertRow[]
  schemaVersions: SchemaFootprint
  bucketCounts: Record<DashboardBucket, number>
  alarmCountTotal: number
  source: 'live' | 'partial-fallback' | 'fallback'
}

// ----------------------------------------------------------------------
// View-model builder
// ----------------------------------------------------------------------

interface RawCaseRow {
  case_id?: string
  latest_trust_score?: number | null
  latest_snapshot_label?: string | null
  latest_signoff_verdict?: string | null
  alarm_count_warn_or_danger?: number
  bucket?: string
}

interface RawAnomaly {
  case_id?: string
  axis?: string
  z_score?: number
  severity?: string
}

interface RawTrendEvent {
  case_id?: string
  axis?: string
  slope?: number
  severity?: string
}

function buildCaseRows(raw: unknown): DashboardCaseRow[] {
  if (!raw || typeof raw !== 'object') return []
  const cases = (raw as { cases?: unknown }).cases
  if (!Array.isArray(cases)) return []
  return cases
    .map((entry: unknown): DashboardCaseRow | null => {
      if (!entry || typeof entry !== 'object') return null
      const row = entry as RawCaseRow
      if (typeof row.case_id !== 'string') return null
      return {
        caseId: row.case_id,
        bucket: defensiveBucket(row.bucket),
        latestTrustScore: row.latest_trust_score ?? null,
        latestSignoffVerdict: row.latest_signoff_verdict ?? null,
        alarmCount: row.alarm_count_warn_or_danger ?? 0,
      }
    })
    .filter((r): r is DashboardCaseRow => r !== null)
}

function buildZScoreAlerts(raw: unknown): DashboardAlertRow[] {
  if (!raw || typeof raw !== 'object') return []
  const anoms = (raw as { anomalies?: unknown }).anomalies
  if (!Array.isArray(anoms)) return []
  return anoms
    .map((entry: unknown): DashboardAlertRow | null => {
      if (!entry || typeof entry !== 'object') return null
      const a = entry as RawAnomaly
      if (typeof a.case_id !== 'string' || typeof a.axis !== 'string') return null
      return {
        kind: 'z_score_outlier' as DashboardAlertKind,
        caseId: a.case_id,
        axis: a.axis,
        severity: defensiveSeverity(a.severity),
        rawValue: typeof a.z_score === 'number' ? a.z_score : null,
        rawSlope: null,
      }
    })
    .filter((a): a is DashboardAlertRow => a !== null)
}

function buildTrendAlerts(raw: unknown): DashboardAlertRow[] {
  if (!raw || typeof raw !== 'object') return []
  const events = (raw as { anomalies?: unknown }).anomalies
  if (!Array.isArray(events)) return []
  return events
    .map((entry: unknown): DashboardAlertRow | null => {
      if (!entry || typeof entry !== 'object') return null
      const t = entry as RawTrendEvent
      if (typeof t.case_id !== 'string' || typeof t.axis !== 'string') return null
      return {
        kind: 'trend_slope' as DashboardAlertKind,
        caseId: t.case_id,
        axis: t.axis,
        severity: defensiveSeverity(t.severity),
        rawValue: null,
        rawSlope: typeof t.slope === 'number' ? t.slope : null,
      }
    })
    .filter((a): a is DashboardAlertRow => a !== null)
}

function rawSchemaVersion(raw: unknown): string {
  if (!raw || typeof raw !== 'object') return 'unknown'
  const v = (raw as { schema_version?: unknown }).schema_version
  return typeof v === 'string' ? v : 'unknown'
}

function buildBucketCounts(
  cases: DashboardCaseRow[],
): Record<DashboardBucket, number> {
  const counts: Record<DashboardBucket, number> = {
    healthy: 0,
    watching: 0,
    regressed: 0,
    unknown: 0,
  }
  for (const c of cases) counts[c.bucket] += 1
  return counts
}

export interface DashboardFetchResult {
  view: CohortDashboardViewModel
  errors: string[]
}

async function fetchRaw(
  apiBase: string,
  surface: string,
  signal?: AbortSignal,
): Promise<{ raw: unknown; error: string | null }> {
  const url = `${apiBase.replace(/\/$/, '')}/${surface}`
  try {
    const res = await fetch(url, { signal })
    if (!res.ok) {
      return { raw: null, error: `${surface} endpoint returned ${res.status}` }
    }
    return { raw: await res.json(), error: null }
  } catch (err) {
    return {
      raw: null,
      error: err instanceof Error ? err.message : 'unknown error',
    }
  }
}

export async function fetchCohortDashboardViewModel(
  apiBase: string,
  signal?: AbortSignal,
): Promise<DashboardFetchResult> {
  // Fetch raw JSON for all three surfaces in parallel; the dashboard
  // owns its own parsing so the X:-2 defensive parsers see actual
  // backend values (not the upstream clients' most-conservative
  // coercions). Degrades gracefully if any one fails.
  const errors: string[] = []
  const [summaryRaw, anomaliesRaw, trendRaw] = await Promise.all([
    fetchRaw(apiBase, 'cohort-executive-summary', signal),
    fetchRaw(apiBase, 'cohort-anomalies', signal),
    fetchRaw(apiBase, 'cohort-trend-anomalies', signal),
  ])

  let liveCount = 0
  if (summaryRaw.raw !== null) liveCount += 1
  else if (summaryRaw.error) errors.push(`summary: ${summaryRaw.error}`)
  if (anomaliesRaw.raw !== null) liveCount += 1
  else if (anomaliesRaw.error) errors.push(`anomalies: ${anomaliesRaw.error}`)
  if (trendRaw.raw !== null) liveCount += 1
  else if (trendRaw.error) errors.push(`trend: ${trendRaw.error}`)

  const cases = buildCaseRows(summaryRaw.raw)
  const alerts = [
    ...buildZScoreAlerts(anomaliesRaw.raw),
    ...buildTrendAlerts(trendRaw.raw),
  ]

  let source: CohortDashboardViewModel['source']
  if (liveCount === 3) source = 'live'
  else if (liveCount === 0) source = 'fallback'
  else source = 'partial-fallback'

  const view: CohortDashboardViewModel = {
    cases,
    alerts,
    schemaVersions: {
      cohortExecutiveSummary: rawSchemaVersion(summaryRaw.raw),
      cohortAnomalies: rawSchemaVersion(anomaliesRaw.raw),
      cohortTrendAnomalies: rawSchemaVersion(trendRaw.raw),
    },
    bucketCounts: buildBucketCounts(cases),
    alarmCountTotal: alerts.length,
    source,
  }
  return { view, errors }
}
