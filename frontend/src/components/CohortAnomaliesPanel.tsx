// FM-04a Phase 8 E — Cohort anomalies panel.
//
// Tier 1 engineering candidate; not signed validation; not benchmark agreement.

import { useEffect, useState } from 'react'
import {
  fetchCohortAnomalies,
  type AnomalySeverity,
  type CohortAnomaliesReport,
} from '../cohortAnomaliesClient.ts'
import { TIER1_BANNER } from '../trustCenterSummary.ts'

export interface CohortAnomaliesPanelProps {
  apiBase: string
}

function severityColor(s: AnomalySeverity): string {
  if (s === 'info') return 'var(--info-400)'
  if (s === 'warn') return 'var(--warn-400)'
  return 'var(--danger-400)'
}

export function CohortAnomaliesPanel({ apiBase }: CohortAnomaliesPanelProps) {
  const [report, setReport] = useState<CohortAnomaliesReport | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    const ctrl = new AbortController()
    setLoading(true)
    void fetchCohortAnomalies(apiBase, ctrl.signal).then((result) => {
      setLoading(false)
      if (result.report) {
        setReport(result.report)
        setError(null)
      } else {
        setReport(null)
        setError(result.error ?? 'unable to load cohort anomalies')
      }
    })
    return () => ctrl.abort()
  }, [apiBase])

  return (
    <section
      style={{
        padding: '12px',
        border: '1px solid var(--border)',
        borderRadius: '6px',
        background: 'var(--bg-surface)',
      }}
    >
      <header style={{ marginBottom: '8px' }}>
        <h3 style={{ margin: 0, fontSize: '0.95rem' }}>Cohort anomalies</h3>
        <div style={{ fontSize: '0.7rem', color: 'var(--text-secondary)' }}>
          {TIER1_BANNER}
        </div>
      </header>

      {loading && (
        <div style={{ fontSize: '0.78rem', color: 'var(--text-secondary)' }}>loading…</div>
      )}
      {error && !loading && (
        <div style={{ fontSize: '0.78rem', color: 'var(--danger-400)' }}>{error}</div>
      )}

      {report && report.anomalyCount === 0 && (
        <div style={{ fontSize: '0.78rem', color: 'var(--text-secondary)' }}>
          no statistical outliers detected in the current cohort
          {report.cohortCount > 0 ? ` (size ${report.cohortCount})` : ''}.
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
            schema v{report.schemaVersion} · {report.anomalyCount} outlier
            {report.anomalyCount === 1 ? '' : 's'} · cohort {report.cohortCount}
          </div>

          <div
            style={{
              display: 'grid',
              gridTemplateColumns: '1fr 1fr 60px 60px 80px',
              gap: '4px 12px',
              fontSize: '0.72rem',
              padding: '4px 0',
              borderBottom: '1px solid var(--border)',
              color: 'var(--text-secondary)',
            }}
          >
            <div>case</div>
            <div>axis</div>
            <div style={{ textAlign: 'right' }}>z</div>
            <div style={{ textAlign: 'right' }}>score</div>
            <div style={{ textAlign: 'right' }}>severity</div>
          </div>
          {report.anomalies.map((a, idx) => {
            const color = severityColor(a.severity)
            return (
              <div
                key={`${a.caseId}-${a.axis}-${idx}`}
                style={{
                  display: 'grid',
                  gridTemplateColumns: '1fr 1fr 60px 60px 80px',
                  gap: '4px 12px',
                  fontSize: '0.78rem',
                  padding: '4px 0',
                  fontFamily: 'monospace',
                }}
              >
                <div>{a.caseId}</div>
                <div>{a.axis}</div>
                <div style={{ textAlign: 'right' }}>{a.zScore.toFixed(2)}</div>
                <div style={{ textAlign: 'right' }}>{a.score}</div>
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
