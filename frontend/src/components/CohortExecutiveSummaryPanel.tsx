// FM-04a Phase 8 D — Cohort executive summary panel.
//
// Tier 1 engineering candidate; not signed validation; not benchmark agreement.

import { useEffect, useState } from 'react'
import {
  bucketTone,
  fetchCohortExecutiveSummary,
  type CohortExecutiveSummary,
  type HealthBucket,
} from '../cohortExecutiveSummaryClient.ts'
import { TIER1_BANNER } from '../trustCenterSummary.ts'

export interface CohortExecutiveSummaryPanelProps {
  apiBase: string
}

function toneColor(t: 'info' | 'warn' | 'danger'): string {
  if (t === 'info') return 'var(--info-400)'
  if (t === 'warn') return 'var(--warn-400)'
  return 'var(--danger-400)'
}

function BucketCounter({
  label,
  count,
  bucket,
}: {
  label: string
  count: number
  bucket: HealthBucket
}) {
  const color = toneColor(bucketTone(bucket))
  return (
    <div
      style={{
        flex: 1,
        padding: '8px 12px',
        border: `1px solid ${color}`,
        borderRadius: '6px',
        textAlign: 'center',
      }}
    >
      <div style={{ fontSize: '1.6rem', fontWeight: 700, color }}>{count}</div>
      <div style={{ fontSize: '0.7rem', color: 'var(--text-secondary)' }}>{label}</div>
    </div>
  )
}

export function CohortExecutiveSummaryPanel({
  apiBase,
}: CohortExecutiveSummaryPanelProps) {
  const [summary, setSummary] = useState<CohortExecutiveSummary | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    const ctrl = new AbortController()
    setLoading(true)
    void fetchCohortExecutiveSummary(apiBase, ctrl.signal).then((result) => {
      setLoading(false)
      if (result.summary) {
        setSummary(result.summary)
        setError(null)
      } else {
        setSummary(null)
        setError(result.error ?? 'unable to load cohort summary')
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
        <h3 style={{ margin: 0, fontSize: '0.95rem' }}>Cohort scorecard</h3>
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

      {summary && (
        <div>
          <div style={{ display: 'flex', gap: '8px', marginBottom: '8px' }}>
            <BucketCounter label="healthy" count={summary.healthyCount} bucket="healthy" />
            <BucketCounter label="watching" count={summary.watchingCount} bucket="watching" />
            <BucketCounter
              label="regressed"
              count={summary.regressedCount}
              bucket="regressed"
            />
          </div>
          <div
            style={{
              fontSize: '0.7rem',
              color: 'var(--text-secondary)',
              marginBottom: '8px',
              fontFamily: 'monospace',
            }}
          >
            schema v{summary.schemaVersion} · {summary.cohortCount} candidate
            {summary.cohortCount === 1 ? '' : 's'}
          </div>

          {summary.cases.length > 0 && (
            <div
              style={{
                display: 'grid',
                gridTemplateColumns: '1fr 60px 80px 60px',
                gap: '4px 12px',
                fontSize: '0.72rem',
                padding: '4px 0',
                borderBottom: '1px solid var(--border)',
                color: 'var(--text-secondary)',
              }}
            >
              <div>case</div>
              <div style={{ textAlign: 'right' }}>score</div>
              <div style={{ textAlign: 'right' }}>alarms</div>
              <div style={{ textAlign: 'right' }}>bucket</div>
            </div>
          )}
          {summary.cases.map((c) => {
            const color = toneColor(bucketTone(c.bucket))
            return (
              <div
                key={c.caseId}
                style={{
                  display: 'grid',
                  gridTemplateColumns: '1fr 60px 80px 60px',
                  gap: '4px 12px',
                  fontSize: '0.78rem',
                  padding: '4px 0',
                  fontFamily: 'monospace',
                }}
              >
                <div>{c.caseId}</div>
                <div style={{ textAlign: 'right' }}>
                  {c.latestTrustScore !== null ? c.latestTrustScore : '—'}
                </div>
                <div style={{ textAlign: 'right' }}>
                  {c.alarmCountWarnOrDanger > 0 ? c.alarmCountWarnOrDanger : '—'}
                </div>
                <div style={{ textAlign: 'right', color, fontWeight: 600 }}>
                  {c.bucket}
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
            {summary.claimImpact}
          </div>
        </div>
      )}
    </section>
  )
}
