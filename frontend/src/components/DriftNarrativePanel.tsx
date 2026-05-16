// FM-04a Phase 6 E — Drift narrative panel.
//
// Tier 1 engineering candidate; not signed validation; not benchmark agreement.
//
// Reads /api/v1/snapshot-narrative?a=&b= using two snapshot labels the
// reviewer picks in CohortSnapshotPanel. Surfaces the templated drift
// sentences grouped by severity.

import { useEffect, useState } from 'react'
import {
  fetchSnapshotNarrative,
  groupBySeverity,
  type Severity,
  type SnapshotNarrative,
} from '../snapshotNarrativeClient.ts'
import { TIER1_BANNER } from '../trustCenterSummary.ts'

export interface DriftNarrativePanelProps {
  apiBase: string
  labelA: string | null
  labelB: string | null
}

function severityColor(severity: Severity): string {
  if (severity === 'danger') return 'var(--danger, #c0392b)'
  if (severity === 'warn') return 'var(--text-warning, #b8860b)'
  return 'var(--text-secondary)'
}

function severityLabel(severity: Severity): string {
  if (severity === 'danger') return 'danger'
  if (severity === 'warn') return 'warn'
  return 'info'
}

export function DriftNarrativePanel({
  apiBase,
  labelA,
  labelB,
}: DriftNarrativePanelProps) {
  const [narrative, setNarrative] = useState<SnapshotNarrative | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (!labelA || !labelB || labelA === labelB) {
      setNarrative(null)
      setError(null)
      return
    }
    const ctrl = new AbortController()
    setLoading(true)
    void fetchSnapshotNarrative(apiBase, labelA, labelB, ctrl.signal).then(
      (result) => {
        setLoading(false)
        if (result.narrative) {
          setNarrative(result.narrative)
          setError(null)
        } else {
          setNarrative(null)
          setError(result.error ?? 'unable to load snapshot narrative')
        }
      },
    )
    return () => ctrl.abort()
  }, [apiBase, labelA, labelB])

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
        <h3 style={{ margin: 0, fontSize: '0.95rem' }}>Drift narrative</h3>
        <div style={{ fontSize: '0.7rem', color: 'var(--text-secondary)' }}>
          {TIER1_BANNER}
        </div>
      </header>

      {(!labelA || !labelB) && (
        <div style={{ fontSize: '0.78rem', color: 'var(--text-secondary)' }}>
          pick two snapshots in the cohort snapshot panel to load a narrative
        </div>
      )}
      {labelA && labelB && labelA === labelB && (
        <div style={{ fontSize: '0.78rem', color: 'var(--text-secondary)' }}>
          snapshot A and B must differ
        </div>
      )}
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

      {narrative && (
        <div>
          <div
            style={{
              fontSize: '0.7rem',
              color: 'var(--text-secondary)',
              marginBottom: '8px',
              fontFamily: 'monospace',
            }}
          >
            {narrative.snapshotALabel} → {narrative.snapshotBLabel} · schema v
            {narrative.schemaVersion || '?'}
          </div>

          {narrative.narratives.length === 0 && (
            <div style={{ fontSize: '0.78rem', color: 'var(--text-secondary)' }}>
              no cases shared between the two snapshots
            </div>
          )}

          {narrative.narratives.map((caseNarrative) => {
            const grouped = groupBySeverity(caseNarrative.lines)
            return (
              <div
                key={caseNarrative.caseId}
                style={{
                  marginBottom: '12px',
                  borderBottom: '1px solid var(--border)',
                  paddingBottom: '8px',
                }}
              >
                <div
                  style={{ fontFamily: 'monospace', fontSize: '0.82rem', marginBottom: '4px' }}
                >
                  {caseNarrative.caseId}
                </div>
                {caseNarrative.lines.length === 0 && (
                  <div style={{ fontSize: '0.72rem', color: 'var(--text-secondary)' }}>
                    no drift detected
                  </div>
                )}
                {(['danger', 'warn', 'info'] as Severity[]).map((sev) =>
                  grouped[sev].map((line, idx) => (
                    <div
                      key={`${sev}-${idx}-${line.templateId}`}
                      style={{
                        fontSize: '0.78rem',
                        color: severityColor(sev),
                        marginTop: '2px',
                      }}
                    >
                      <span
                        style={{
                          fontFamily: 'monospace',
                          fontSize: '0.7rem',
                          padding: '1px 4px',
                          marginRight: '6px',
                          border: `1px solid ${severityColor(sev)}`,
                          borderRadius: '3px',
                        }}
                      >
                        {severityLabel(sev)}
                      </span>
                      {line.text}
                    </div>
                  )),
                )}
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
            {narrative.claimImpact}
          </div>
        </div>
      )}
    </section>
  )
}
