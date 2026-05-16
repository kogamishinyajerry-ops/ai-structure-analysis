// FM-04a Phase 10 B — Cohort trend-slope anomalies panel.
//
// Tier 1 engineering candidate; not signed validation; not benchmark agreement.
//
// Mirrors `CohortAnomaliesPanel.tsx` (Phase 8 E) but reads the trend
// endpoint. Renders one row per case-axis trend event with slope +
// point count + severity. Orthogonal to the z-score outlier panel —
// a case can fire one, both, or neither, by design.

import { useEffect, useState } from 'react'
import {
  fetchCohortTrendAnomalies,
  type CohortTrendAnomaliesReport,
  type TrendSeverity,
} from '../cohortTrendAnomaliesClient.ts'
import { TIER1_BANNER } from '../trustCenterSummary.ts'

export interface CohortTrendAnomaliesPanelProps {
  apiBase: string
}

function severityColor(s: TrendSeverity): string {
  if (s === 'info') return 'var(--accent, #0a8a4a)'
  if (s === 'warn') return 'var(--text-warning, #b8860b)'
  return 'var(--danger, #c0392b)'
}

export function CohortTrendAnomaliesPanel({
  apiBase,
}: CohortTrendAnomaliesPanelProps) {
  const [report, setReport] = useState<CohortTrendAnomaliesReport | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    const ctrl = new AbortController()
    setLoading(true)
    void fetchCohortTrendAnomalies(apiBase, ctrl.signal).then((result) => {
      setLoading(false)
      if (result.report) {
        setReport(result.report)
        setError(null)
      } else {
        setReport(null)
        setError(result.error ?? 'unable to load cohort trend anomalies')
      }
    })
    return () => ctrl.abort()
  }, [apiBase])

  return (
    <section
      data-testid="cohort-trend-anomalies-panel"
      style={{
        padding: '12px',
        border: '1px solid var(--border)',
        borderRadius: '6px',
        background: 'var(--surface)',
      }}
    >
      <header style={{ marginBottom: '8px' }}>
        <h3 style={{ margin: 0, fontSize: '0.95rem' }}>Cohort trend anomalies</h3>
        <div style={{ fontSize: '0.7rem', color: 'var(--text-secondary)' }}>
          {TIER1_BANNER}
        </div>
      </header>

      {loading && (
        <div style={{ fontSize: '0.78rem', color: 'var(--text-secondary)' }}>
          loading…
        </div>
      )}
      {error && !loading && (
        <div style={{ fontSize: '0.78rem', color: 'var(--danger, #c0392b)' }}>
          {error}
        </div>
      )}

      {report && report.anomalyCount === 0 && (
        <div
          data-testid="cohort-trend-anomalies-empty"
          style={{ fontSize: '0.78rem', color: 'var(--text-secondary)' }}
        >
          no trend regressions detected
          {report.cohortCount > 0 ? ` (cohort ${report.cohortCount}` : ''}
          {report.cohortCount > 0
            ? `, point-count floor ${report.pointCountFloor})`
            : ''}
          .
        </div>
      )}

      {report && report.anomalyCount > 0 && (
        <div>
          <div
            style={{
              fontSize: '0.7rem',
              color: 'var(--text-secondary)',
              marginBottom: '8px',
              fontFamily: 'monospace',
            }}
          >
            schema v{report.schemaVersion} · {report.anomalyCount} trend event
            {report.anomalyCount === 1 ? '' : 's'} · cohort {report.cohortCount} ·
            floor {report.pointCountFloor}
          </div>

          <div
            style={{
              display: 'grid',
              gridTemplateColumns: '1fr 1fr 70px 50px 80px',
              gap: '4px 12px',
              fontSize: '0.72rem',
              padding: '4px 0',
              borderBottom: '1px solid var(--border)',
              color: 'var(--text-secondary)',
            }}
          >
            <div>case</div>
            <div>axis</div>
            <div style={{ textAlign: 'right' }}>slope</div>
            <div style={{ textAlign: 'right' }}>points</div>
            <div style={{ textAlign: 'right' }}>severity</div>
          </div>
          {report.anomalies.map((a, idx) => {
            const color = severityColor(a.severity)
            return (
              <div
                key={`${a.caseId}-${a.axis}-${idx}`}
                data-testid={`trend-event-row-${a.caseId}-${a.axis}`}
                style={{
                  display: 'grid',
                  gridTemplateColumns: '1fr 1fr 70px 50px 80px',
                  gap: '4px 12px',
                  fontSize: '0.78rem',
                  padding: '4px 0',
                  fontFamily: 'monospace',
                }}
              >
                <div>{a.caseId}</div>
                <div>{a.axis}</div>
                <div style={{ textAlign: 'right' }}>{a.slope.toFixed(2)}</div>
                <div style={{ textAlign: 'right' }}>{a.pointCount}</div>
                <div style={{ textAlign: 'right', color, fontWeight: 600 }}>
                  {a.severity}
                </div>
              </div>
            )
          })}

          <div
            style={{
              fontSize: '0.7rem',
              color: 'var(--text-secondary)',
              marginTop: '8px',
            }}
          >
            {report.claimImpact}
          </div>
        </div>
      )}
    </section>
  )
}
