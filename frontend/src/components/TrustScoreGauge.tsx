// FM-04a Phase 6 E — Trust score gauge.
//
// Tier 1 engineering candidate; not signed validation; not benchmark agreement.
//
// Renders /api/v1/trust-score/<case-id> as a colored 0-100 bar +
// per-axis breakdown table. Surfaces schemaVersion + formulaVersion
// + the *exact* integer score (never rounded). Tone breakpoints come
// from the trustScoreClient SSOT, not magic numbers in the component.

import { useEffect, useState } from 'react'
import {
  TRUST_TONE_ACCENT_THRESHOLD,
  TRUST_TONE_WARNING_THRESHOLD,
  fetchTrustScore,
  trustTone,
  type TrustScore,
} from '../trustScoreClient.ts'
import { TIER1_BANNER } from '../trustCenterSummary.ts'

export interface TrustScoreGaugeProps {
  apiBase: string
  caseId: string | null
}

const SECTION_TITLE_STYLE = {
  fontSize: '0.7rem',
  textTransform: 'uppercase' as const,
  letterSpacing: '0.06em',
  color: 'var(--text-secondary)',
}

function toneColor(tone: ReturnType<typeof trustTone>): string {
  if (tone === 'accent') return 'var(--accent, #0a8a4a)'
  if (tone === 'warning') return 'var(--text-warning, #b8860b)'
  if (tone === 'danger') return 'var(--danger, #c0392b)'
  return 'var(--text-secondary)'
}

export function TrustScoreGauge({ apiBase, caseId }: TrustScoreGaugeProps) {
  const [score, setScore] = useState<TrustScore | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (!caseId) {
      setScore(null)
      setError(null)
      return
    }
    const ctrl = new AbortController()
    setLoading(true)
    void fetchTrustScore(apiBase, caseId, ctrl.signal).then((result) => {
      setLoading(false)
      if (result.trustScore) {
        setScore(result.trustScore)
        setError(null)
      } else {
        setScore(null)
        setError(result.error ?? 'unable to load trust score')
      }
    })
    return () => ctrl.abort()
  }, [apiBase, caseId])

  const tone = score ? trustTone(score.trustScore) : 'muted'
  const color = toneColor(tone)

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
        <h3 style={{ margin: 0, fontSize: '0.95rem' }}>Trust score</h3>
        <div style={{ fontSize: '0.7rem', color: 'var(--text-secondary)' }}>
          {TIER1_BANNER}
        </div>
      </header>

      {!caseId && (
        <div style={{ fontSize: '0.78rem', color: 'var(--text-secondary)' }}>
          select a candidate case to load its trust score
        </div>
      )}
      {caseId && loading && (
        <div style={{ fontSize: '0.78rem', color: 'var(--text-secondary)' }}>loading…</div>
      )}
      {caseId && error && !loading && (
        <div style={{ fontSize: '0.78rem', color: 'var(--danger, #c0392b)' }}>{error}</div>
      )}

      {score && (
        <div>
          <div
            style={{
              fontFamily: 'monospace',
              fontSize: '2rem',
              color,
              lineHeight: 1,
              marginBottom: '4px',
            }}
          >
            {/* render EXACT integer, never rounded - Phase 6 X guard */}
            {score.trustScore}
            <span
              style={{
                fontSize: '0.9rem',
                color: 'var(--text-secondary)',
                marginLeft: '4px',
              }}
            >
              / {score.trustScoreMax}
            </span>
          </div>

          <div
            style={{
              height: '8px',
              background: 'var(--border)',
              borderRadius: '4px',
              overflow: 'hidden',
              marginBottom: '8px',
            }}
          >
            <div
              style={{
                width: `${Math.max(0, Math.min(100, score.trustScore))}%`,
                height: '100%',
                background: color,
                transition: 'width 200ms ease',
              }}
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
            schema v{score.schemaVersion || '?'} · formula v{score.formulaVersion || '?'}
            {' '}· accent ≥ {TRUST_TONE_ACCENT_THRESHOLD} · warn ≥{' '}
            {TRUST_TONE_WARNING_THRESHOLD}
          </div>

          <div style={SECTION_TITLE_STYLE}>per-axis breakdown</div>
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: '1fr 60px 60px 60px',
              gap: '4px 12px',
              fontSize: '0.72rem',
              padding: '4px 0',
              borderBottom: '1px solid var(--border)',
              color: 'var(--text-secondary)',
            }}
          >
            <div>axis</div>
            <div style={{ textAlign: 'right' }}>weight</div>
            <div style={{ textAlign: 'right' }}>raw</div>
            <div style={{ textAlign: 'right' }}>weighted</div>
          </div>
          {score.breakdown.map((entry) => (
            <div key={entry.axis}>
              <div
                style={{
                  display: 'grid',
                  gridTemplateColumns: '1fr 60px 60px 60px',
                  gap: '4px 12px',
                  fontSize: '0.78rem',
                  padding: '4px 0',
                }}
              >
                <div style={{ fontFamily: 'monospace' }}>{entry.axis}</div>
                <div style={{ textAlign: 'right' }}>{entry.weight}</div>
                <div style={{ textAlign: 'right' }}>{entry.rawScore}</div>
                <div style={{ textAlign: 'right', fontWeight: 600 }}>
                  {entry.weighted}
                </div>
              </div>
              <div
                style={{
                  fontSize: '0.68rem',
                  color: 'var(--text-secondary)',
                  paddingLeft: '8px',
                  marginBottom: '4px',
                }}
              >
                {entry.rationale}
              </div>
            </div>
          ))}

          <div
            style={{
              fontSize: '0.7rem',
              color: 'var(--text-secondary)',
              marginTop: '8px',
            }}
          >
            {score.claimImpact}
          </div>
        </div>
      )}
    </section>
  )
}
