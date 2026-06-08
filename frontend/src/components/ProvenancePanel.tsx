// FM-04a Phase 9 E — Trust score provenance panel.
//
// Tier 1 engineering candidate; not signed validation; not benchmark agreement.
//
// Surfaces the provenance trace as a UI panel for a given (case,
// snapshot) pair. Reads the trust-score-provenance endpoint that the
// Phase 8 C service exposes and was extended in Phase 9 B to include
// the `generator` input kind. The defensive parser in
// `trustScoreProvenanceClient.ts` maps unknown kinds to 'unknown' so
// a future MINOR bump that adds a kind cannot crash this panel.

import { useEffect, useState } from 'react'
import {
  fetchTrustScoreProvenance,
  shortSha,
  type TrustScoreProvenanceReport,
} from '../trustScoreProvenanceClient.ts'
import { TIER1_BANNER } from '../trustCenterSummary.ts'

export interface ProvenancePanelProps {
  apiBase: string
  caseId: string
  snapshotLabel: string
}

export function ProvenancePanel({
  apiBase,
  caseId,
  snapshotLabel,
}: ProvenancePanelProps) {
  const [report, setReport] = useState<TrustScoreProvenanceReport | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (!caseId || !snapshotLabel) {
      // The panel only mounts with a known (caseId, snapshotLabel) pair
      // — App.tsx is responsible for not rendering it otherwise. This
      // guard is defense in depth so a malformed parent never triggers
      // a stray fetch with empty params (Phase 9 anti-gaming guard X: -2).
      return
    }
    const ctrl = new AbortController()
    setLoading(true)
    void fetchTrustScoreProvenance(apiBase, caseId, snapshotLabel, ctrl.signal).then(
      (result) => {
        setLoading(false)
        if (result.report) {
          setReport(result.report)
          setError(null)
        } else {
          setReport(null)
          setError(result.error ?? 'unable to load provenance trace')
        }
      },
    )
    return () => ctrl.abort()
  }, [apiBase, caseId, snapshotLabel])

  return (
    <section
      data-testid="provenance-panel"
      style={{
        padding: '12px',
        border: '1px solid var(--border)',
        borderRadius: '6px',
        background: 'var(--surface)',
      }}
    >
      <header style={{ marginBottom: '8px' }}>
        <h3 style={{ margin: 0, fontSize: '0.95rem' }}>Trust score provenance</h3>
        <div style={{ fontSize: '0.7rem', color: 'var(--text-secondary)' }}>
          {TIER1_BANNER}
        </div>
        <div
          style={{
            fontSize: '0.7rem',
            color: 'var(--text-secondary)',
            fontFamily: 'monospace',
          }}
        >
          {caseId} · {snapshotLabel}
        </div>
      </header>

      {loading && (
        <div style={{ fontSize: '0.78rem', color: 'var(--text-secondary)' }}>
          loading…
        </div>
      )}
      {error && !loading && (
        <div style={{ fontSize: '0.78rem', color: 'var(--danger, var(--danger-400))' }}>
          {error}
        </div>
      )}

      {report && (
        <div>
          <div
            style={{
              fontSize: '0.7rem',
              color: 'var(--text-secondary)',
              marginBottom: '6px',
              fontFamily: 'monospace',
            }}
          >
            schema v{report.schemaVersion} · formula v{report.formulaVersion} ·
            recomputed trust score{' '}
            <strong>
              {report.trustScore === null ? '—' : report.trustScore}
            </strong>
          </div>

          <div
            style={{
              display: 'grid',
              gridTemplateColumns: '110px 1fr 60px 110px',
              gap: '4px 10px',
              fontSize: '0.72rem',
              padding: '4px 0',
              borderBottom: '1px solid var(--border)',
              color: 'var(--text-secondary)',
            }}
          >
            <div>kind</div>
            <div>path</div>
            <div style={{ textAlign: 'right' }}>present</div>
            <div>sha-256 (first 12)</div>
          </div>
          {report.inputs.map((input, idx) => {
            const muted = !input.present
            // Phase 10 E — generator rows render an extra
            // "normalized SHA" cell so a reviewer can tell whether
            // two snapshots' generators are AST-equivalent even when
            // their raw bytes differ. Non-generator rows render `—`.
            const normalizedCell =
              input.normalizationError !== null && input.normalizationError !== undefined
                ? 'parse error'
                : shortSha(input.sha256Normalized)
            return (
              <div
                key={`${input.kind}-${input.path}-${idx}`}
                data-testid={`provenance-input-row-${input.kind}`}
                style={{
                  display: 'grid',
                  gridTemplateColumns: '100px 1fr 50px 100px 100px',
                  gap: '4px 10px',
                  fontSize: '0.78rem',
                  padding: '4px 0',
                  fontFamily: 'monospace',
                  color: muted ? 'var(--text-secondary)' : 'var(--text)',
                }}
              >
                <div>{input.kind}</div>
                <div>{input.path}</div>
                <div style={{ textAlign: 'right' }}>{input.present ? '✓' : '—'}</div>
                <div title="raw SHA-256">{shortSha(input.sha256)}</div>
                <div
                  title={
                    input.kind === 'generator'
                      ? input.normalizationError ??
                        'canonical AST-dump SHA — whitespace + comment insensitive'
                      : 'normalized SHA not applicable for this kind'
                  }
                  data-testid={`provenance-input-normalized-${input.kind}`}
                >
                  {normalizedCell}
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
