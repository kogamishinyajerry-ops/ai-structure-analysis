// FM-04a Phase 6 E — Trust score timeline chart.
//
// Tier 1 engineering candidate; not signed validation; not benchmark agreement.
//
// Reads /api/v1/trust-score-timeline/<case-id> and renders the trust
// score evolution as an inline SVG sparkline + a table of per-snapshot
// per-axis weighted scores. No external chart library.

import { useEffect, useState } from 'react'
import {
  buildSparklinePath,
  fetchTrustScoreTimeline,
  type TrustScoreTimeline,
} from '../trustScoreTimelineClient.ts'
import { TIER1_BANNER } from '../trustCenterSummary.ts'

export interface TrustScoreTimelineChartProps {
  apiBase: string
  caseId: string | null
}

const SPARKLINE_WIDTH = 320
const SPARKLINE_HEIGHT = 60

export function TrustScoreTimelineChart({
  apiBase,
  caseId,
}: TrustScoreTimelineChartProps) {
  const [timeline, setTimeline] = useState<TrustScoreTimeline | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (!caseId) {
      setTimeline(null)
      setError(null)
      return
    }
    const ctrl = new AbortController()
    setLoading(true)
    void fetchTrustScoreTimeline(apiBase, caseId, ctrl.signal).then((result) => {
      setLoading(false)
      if (result.timeline) {
        setTimeline(result.timeline)
        setError(null)
      } else {
        setTimeline(null)
        setError(result.error ?? 'unable to load trust score timeline')
      }
    })
    return () => ctrl.abort()
  }, [apiBase, caseId])

  const path = timeline
    ? buildSparklinePath(timeline.points, SPARKLINE_WIDTH, SPARKLINE_HEIGHT)
    : ''

  return (
    <section
      style={{
        padding: '12px',
        border: '1px solid var(--border)',
        borderRadius: '6px',
        background: 'var(--surface)',
      }}
    >
      <header style={{ marginBottom: '8px' }}>
        <h3 style={{ margin: 0, fontSize: '0.95rem' }}>Trust score timeline</h3>
        <div style={{ fontSize: '0.7rem', color: 'var(--text-secondary)' }}>
          {TIER1_BANNER}
        </div>
      </header>

      {!caseId && (
        <div style={{ fontSize: '0.78rem', color: 'var(--text-secondary)' }}>
          select a candidate case to load its trust score timeline
        </div>
      )}
      {caseId && loading && (
        <div style={{ fontSize: '0.78rem', color: 'var(--text-secondary)' }}>
          loading…
        </div>
      )}
      {caseId && error && !loading && (
        <div style={{ fontSize: '0.78rem', color: 'var(--danger, #c0392b)' }}>
          {error}
        </div>
      )}

      {timeline && (
        <div>
          <div
            style={{
              fontSize: '0.7rem',
              color: 'var(--text-secondary)',
              marginBottom: '8px',
              fontFamily: 'monospace',
            }}
          >
            schema v{timeline.schemaVersion || '?'} · formula v
            {timeline.formulaVersion || '?'} · {timeline.pointCount} snapshot
            {timeline.pointCount === 1 ? '' : 's'}
          </div>

          {timeline.points.length === 0 && (
            <div style={{ fontSize: '0.78rem', color: 'var(--text-secondary)' }}>
              no cohort snapshots contain this case yet
            </div>
          )}

          {timeline.points.length > 0 && (
            <svg
              width={SPARKLINE_WIDTH}
              height={SPARKLINE_HEIGHT}
              viewBox={`0 0 ${SPARKLINE_WIDTH} ${SPARKLINE_HEIGHT}`}
              style={{
                background: 'var(--background, transparent)',
                border: '1px solid var(--border)',
                marginBottom: '8px',
                display: 'block',
              }}
              role="img"
              aria-label="trust score sparkline"
            >
              {/* gridline at 80 (accent threshold) */}
              <line
                x1={0}
                y1={SPARKLINE_HEIGHT * 0.2}
                x2={SPARKLINE_WIDTH}
                y2={SPARKLINE_HEIGHT * 0.2}
                stroke="var(--accent, #0a8a4a)"
                strokeDasharray="2 4"
                opacity={0.4}
              />
              {/* gridline at 50 (warn threshold) */}
              <line
                x1={0}
                y1={SPARKLINE_HEIGHT * 0.5}
                x2={SPARKLINE_WIDTH}
                y2={SPARKLINE_HEIGHT * 0.5}
                stroke="var(--text-warning, #b8860b)"
                strokeDasharray="2 4"
                opacity={0.4}
              />
              <path
                d={path}
                fill="none"
                stroke="var(--accent, #0a8a4a)"
                strokeWidth={2}
                strokeLinejoin="round"
                strokeLinecap="round"
              />
            </svg>
          )}

          {timeline.points.length > 0 && (
            <div>
              <div
                style={{
                  display: 'grid',
                  gridTemplateColumns: '180px 60px 60px 60px 60px 60px',
                  gap: '4px 8px',
                  fontSize: '0.7rem',
                  color: 'var(--text-secondary)',
                  padding: '4px 0',
                  borderBottom: '1px solid var(--border)',
                }}
              >
                <div>snapshot</div>
                <div style={{ textAlign: 'right' }}>trust</div>
                <div style={{ textAlign: 'right' }}>comp</div>
                <div style={{ textAlign: 'right' }}>conv</div>
                <div style={{ textAlign: 'right' }}>energy</div>
                <div style={{ textAlign: 'right' }}>repro</div>
              </div>
              {timeline.points.map((point) => (
                <div
                  key={point.snapshotLabel}
                  style={{
                    display: 'grid',
                    gridTemplateColumns: '180px 60px 60px 60px 60px 60px',
                    gap: '4px 8px',
                    fontSize: '0.78rem',
                    padding: '4px 0',
                    borderBottom: '1px solid var(--border-subtle, var(--border))',
                    fontFamily: 'monospace',
                  }}
                >
                  <div>{point.snapshotLabel}</div>
                  <div style={{ textAlign: 'right', fontWeight: 600 }}>
                    {point.trustScore}
                  </div>
                  <div style={{ textAlign: 'right' }}>{point.completenessWeighted}</div>
                  <div style={{ textAlign: 'right' }}>{point.convergenceWeighted}</div>
                  <div style={{ textAlign: 'right' }}>{point.energyAuditWeighted}</div>
                  <div style={{ textAlign: 'right' }}>
                    {point.reproducibilityWeighted}
                  </div>
                </div>
              ))}
            </div>
          )}

          <div
            style={{
              fontSize: '0.7rem',
              color: 'var(--text-secondary)',
              marginTop: '8px',
            }}
          >
            {timeline.claimImpact}
          </div>
        </div>
      )}
    </section>
  )
}
