// FM-04a Phase 12 I — Cohort substantiation panel.
//
// Tier 1 engineering candidate; not signed validation; not benchmark agreement.
//
// Consumer-surface for the Phase 12 E `cohortDashboardClient.ts`
// orchestrator. Renders the unified Phase 12 E view-model
// (bucket distribution + per-case rows + alerts + schema-versions
// footer) for the blueprint-#07 substantiation dashboard.
//
// **Load-bearing X:-2 anti-gaming guard surface**: the panel reads
// the orchestrator's view-model `bucket: DashboardBucket` and
// `severity: DashboardSeverity` values DIRECTLY, then routes them
// through the orchestrator's `bucketColor` / `severityColor`
// helpers. An out-of-tuple bucket value lands at `'unknown'`
// (neutral gray), NOT at `'regressed'` (red) — surfacing schema
// drift instead of masking it as a regressed bucket. This is the
// consumer-side completion of the Phase 12 E orchestrator's
// defensive parsers; without this panel the orchestrator is
// proven correct in isolation but logically dead at the
// user-visible surface.
//
// Note: this component is wired into App.tsx as a SECOND cohort
// surface alongside the legacy `CohortDashboardPanel.tsx` (which
// renders the `/cohort-overview` evidence completeness leaderboard,
// a different surface that pre-dates the substantiation arc). The
// two panels are intentionally separate so the legacy surface
// remains untouched while the new substantiation surface stands
// up its own contract. Phase 13 may unify them once both are
// observed-stable.

import { useEffect, useState } from 'react'

import {
  type CohortDashboardViewModel,
  type DashboardAlertRow,
  type DashboardBucket,
  type DashboardCaseRow,
  bucketColor,
  fetchCohortDashboardViewModel,
  severityColor,
} from '../cohortDashboardClient.ts'
import { TIER1_BANNER } from '../trustCenterSummary.ts'

export interface CohortSubstantiationPanelProps {
  apiBase: string
  // The fetch helper is injected so tests can pass a deterministic
  // mock without monkey-patching `global.fetch`. Defaults to the
  // real `fetchCohortDashboardViewModel`.
  fetchViewModel?: typeof fetchCohortDashboardViewModel
}

const SECTION_TITLE_STYLE = {
  fontSize: '0.7rem',
  textTransform: 'uppercase' as const,
  letterSpacing: '0.06em',
  color: 'var(--text-secondary)',
}

function BucketChip({ bucket, count }: { bucket: DashboardBucket; count: number }) {
  return (
    <span
      data-testid={`substantiation-bucket-chip-${bucket}`}
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: '6px',
        padding: '4px 10px',
        borderRadius: '999px',
        border: `1px solid ${bucketColor(bucket)}`,
        color: bucketColor(bucket),
        fontSize: '0.72rem',
        marginRight: '8px',
      }}
    >
      <strong>{count}</strong>
      <span>{bucket}</span>
    </span>
  )
}

function CaseRow({ row }: { row: DashboardCaseRow }) {
  return (
    <div
      data-testid={`substantiation-case-row-${row.caseId}`}
      style={{
        display: 'grid',
        gridTemplateColumns: '1fr 90px 130px 140px 70px',
        gap: '8px',
        padding: '6px 0',
        borderBottom: '1px solid var(--border)',
        fontSize: '0.78rem',
        color: 'var(--text-primary)',
        alignItems: 'center',
      }}
    >
      <code style={{ overflowWrap: 'anywhere' }}>{row.caseId}</code>
      <span
        data-testid={`substantiation-bucket-${row.caseId}`}
        style={{ color: bucketColor(row.bucket), fontWeight: 600 }}
      >
        {row.bucket}
      </span>
      <code>{row.latestTrustScore !== null ? `${row.latestTrustScore}/100` : '—'}</code>
      <code>{row.latestSignoffVerdict ?? '—'}</code>
      <code>{row.alarmCount}</code>
    </div>
  )
}

function AlertRow({ alert }: { alert: DashboardAlertRow }) {
  return (
    <div
      data-testid={`substantiation-alert-row-${alert.caseId}-${alert.axis}`}
      style={{
        display: 'grid',
        gridTemplateColumns: '120px 1fr 100px 90px 90px',
        gap: '8px',
        padding: '5px 0',
        borderBottom: '1px solid var(--border)',
        fontSize: '0.75rem',
        color: 'var(--text-primary)',
        alignItems: 'center',
      }}
    >
      <code>{alert.kind}</code>
      <code style={{ overflowWrap: 'anywhere' }}>{alert.caseId}</code>
      <code>{alert.axis}</code>
      <span
        data-testid={`substantiation-severity-${alert.caseId}-${alert.axis}`}
        style={{ color: severityColor(alert.severity), fontWeight: 600 }}
      >
        {alert.severity}
      </span>
      <code>
        {alert.rawValue !== null
          ? alert.rawValue.toFixed(2)
          : alert.rawSlope !== null
            ? alert.rawSlope.toFixed(2)
            : '—'}
      </code>
    </div>
  )
}

export function CohortSubstantiationPanel({
  apiBase,
  fetchViewModel = fetchCohortDashboardViewModel,
}: CohortSubstantiationPanelProps) {
  const [view, setView] = useState<CohortDashboardViewModel | null>(null)
  const [errors, setErrors] = useState<string[]>([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    const controller = new AbortController()
    setLoading(true)
    fetchViewModel(apiBase, controller.signal)
      .then((result) => {
        setView(result.view)
        setErrors(result.errors)
      })
      .finally(() => setLoading(false))
    return () => controller.abort()
  }, [apiBase, fetchViewModel])

  return (
    <div
      data-testid="cohort-substantiation-panel"
      style={{
        padding: '12px 16px',
        borderRadius: '10px',
        border: '1px solid var(--border)',
        background: 'var(--bg-surface)',
        display: 'flex',
        flexDirection: 'column',
        gap: '10px',
      }}
    >
      <div>
        <div style={{ ...SECTION_TITLE_STYLE, color: 'var(--text-warning, #b8860b)' }}>
          Cohort substantiation dashboard
        </div>
        <div style={{ fontSize: '0.65rem', color: 'var(--text-secondary)' }}>
          {TIER1_BANNER} · multi-snapshot evidence view
        </div>
      </div>

      {loading && (
        <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
          loading cohort substantiation view…
        </div>
      )}

      {!loading && view && (
        <>
          <div data-testid="substantiation-source-badge" style={{ fontSize: '0.7rem' }}>
            source: <strong>{view.source}</strong> · cases {view.cases.length} · alerts{' '}
            {view.alarmCountTotal}
          </div>

          <div data-testid="substantiation-bucket-summary">
            <BucketChip bucket="healthy" count={view.bucketCounts.healthy} />
            <BucketChip bucket="watching" count={view.bucketCounts.watching} />
            <BucketChip bucket="regressed" count={view.bucketCounts.regressed} />
            <BucketChip bucket="unknown" count={view.bucketCounts.unknown} />
          </div>

          {view.cases.length > 0 && (
            <>
              <div
                style={{
                  display: 'grid',
                  gridTemplateColumns: '1fr 90px 130px 140px 70px',
                  gap: '8px',
                  fontSize: '0.65rem',
                  color: 'var(--text-secondary)',
                  padding: '4px 0',
                  borderBottom: '1px solid var(--border)',
                  textTransform: 'uppercase',
                  letterSpacing: '0.06em',
                }}
              >
                <span>case_id</span>
                <span>bucket</span>
                <span>trust</span>
                <span>verdict</span>
                <span>alarms</span>
              </div>
              {view.cases.map((row) => (
                <CaseRow key={row.caseId} row={row} />
              ))}
            </>
          )}

          {view.alerts.length > 0 && (
            <>
              <div
                style={{
                  fontSize: '0.65rem',
                  color: 'var(--text-secondary)',
                  marginTop: '4px',
                  textTransform: 'uppercase',
                  letterSpacing: '0.06em',
                }}
              >
                alerts ({view.alarmCountTotal})
              </div>
              <div
                style={{
                  display: 'grid',
                  gridTemplateColumns: '120px 1fr 100px 90px 90px',
                  gap: '8px',
                  fontSize: '0.65rem',
                  color: 'var(--text-secondary)',
                  padding: '4px 0',
                  borderBottom: '1px solid var(--border)',
                  textTransform: 'uppercase',
                  letterSpacing: '0.06em',
                }}
              >
                <span>kind</span>
                <span>case_id</span>
                <span>axis</span>
                <span>severity</span>
                <span>value</span>
              </div>
              {view.alerts.map((alert, idx) => (
                <AlertRow
                  key={`${alert.kind}-${alert.caseId}-${alert.axis}-${idx}`}
                  alert={alert}
                />
              ))}
            </>
          )}

          <div
            data-testid="substantiation-schema-versions"
            style={{
              fontSize: '0.65rem',
              color: 'var(--text-secondary)',
              borderTop: '1px solid var(--border)',
              paddingTop: '6px',
            }}
          >
            schema versions: exec={view.schemaVersions.cohortExecutiveSummary} ·
            anomalies={view.schemaVersions.cohortAnomalies} · trend=
            {view.schemaVersions.cohortTrendAnomalies}
          </div>

          {errors.length > 0 && (
            <div
              data-testid="substantiation-errors"
              style={{ fontSize: '0.65rem', color: 'var(--text-warning, #b8860b)' }}
            >
              {errors.join(' · ')}
            </div>
          )}
        </>
      )}
    </div>
  )
}
