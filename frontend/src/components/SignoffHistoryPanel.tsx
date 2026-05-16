// FM-04a Phase 8 B — Signoff history panel.
//
// Tier 1 engineering candidate; not signed validation; not benchmark agreement.
//
// Renders /api/v1/signoff-history/<case-id> as a chronological list with
// verdict pills. Verdict tone is driven by `toneForVerdict()` SSOT from the
// client; never inline hex codes (Phase 8 anti-gaming guard X: -2).

import { useEffect, useState } from 'react'
import {
  fetchSignoffHistory,
  toneForVerdict,
  type SignoffHistoryReport,
  type SignoffVerdict,
  type VerdictTone,
} from '../signoffHistoryClient.ts'
import { TIER1_BANNER } from '../trustCenterSummary.ts'
import { SignoffSubmissionForm } from './SignoffSubmissionForm.tsx'

export interface SignoffHistoryPanelProps {
  apiBase: string
  caseId: string | null
  /**
   * Phase 8 B — invoked with the latest signoff record (or null if the
   * case has no signoffs) every time the panel finishes loading. Lets
   * App.tsx mirror the latest verdict onto the TrustScoreGauge subline
   * without duplicating the fetch.
   */
  onLatestRecord?: (record: import('../signoffHistoryClient.ts').SignoffRecord | null) => void
}

function toneBackground(tone: VerdictTone): string {
  if (tone === 'info') return 'var(--accent-bg, #e6f3ec)'
  if (tone === 'warn') return 'var(--warning-bg, #fff3d6)'
  return 'var(--danger-bg, #fbe6e3)'
}

function toneForeground(tone: VerdictTone): string {
  if (tone === 'info') return 'var(--accent, #0a8a4a)'
  if (tone === 'warn') return 'var(--text-warning, #b8860b)'
  return 'var(--danger, #c0392b)'
}

function VerdictPill({ verdict }: { verdict: SignoffVerdict }) {
  const tone = toneForVerdict(verdict)
  return (
    <span
      style={{
        background: toneBackground(tone),
        color: toneForeground(tone),
        padding: '2px 8px',
        borderRadius: '4px',
        fontSize: '0.7rem',
        fontWeight: 600,
        fontFamily: 'monospace',
      }}
    >
      {verdict}
    </span>
  )
}

export function SignoffHistoryPanel({
  apiBase,
  caseId,
  onLatestRecord,
}: SignoffHistoryPanelProps) {
  const [report, setReport] = useState<SignoffHistoryReport | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  // Phase 10 A — bump refreshKey on successful POST so the
  // history effect re-runs exactly once per submit.
  const [refreshKey, setRefreshKey] = useState(0)

  useEffect(() => {
    if (!caseId) {
      setReport(null)
      setError(null)
      onLatestRecord?.(null)
      return
    }
    const ctrl = new AbortController()
    setLoading(true)
    void fetchSignoffHistory(apiBase, caseId, ctrl.signal).then((result) => {
      setLoading(false)
      if (result.report) {
        setReport(result.report)
        setError(null)
        const records = result.report.records
        onLatestRecord?.(records.length > 0 ? records[records.length - 1] : null)
      } else {
        setReport(null)
        setError(result.error ?? 'unable to load signoff history')
        onLatestRecord?.(null)
      }
    })
    return () => ctrl.abort()
  }, [apiBase, caseId, onLatestRecord, refreshKey])

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
        <h3 style={{ margin: 0, fontSize: '0.95rem' }}>Reviewer signoffs</h3>
        <div style={{ fontSize: '0.7rem', color: 'var(--text-secondary)' }}>
          {TIER1_BANNER}
        </div>
      </header>

      {!caseId && (
        <div style={{ fontSize: '0.78rem', color: 'var(--text-secondary)' }}>
          select a candidate case to load its signoff history
        </div>
      )}
      {caseId && (
        <SignoffSubmissionForm
          apiBase={apiBase}
          caseId={caseId}
          onSubmitSuccess={() => setRefreshKey((n) => n + 1)}
        />
      )}
      {caseId && loading && (
        <div style={{ fontSize: '0.78rem', color: 'var(--text-secondary)' }}>loading…</div>
      )}
      {caseId && error && !loading && (
        <div style={{ fontSize: '0.78rem', color: 'var(--danger, #c0392b)' }}>{error}</div>
      )}

      {report && report.recordCount === 0 && (
        <div style={{ fontSize: '0.78rem', color: 'var(--text-secondary)' }}>
          no signoffs yet for this candidate.
        </div>
      )}

      {report && report.recordCount > 0 && (
        <div>
          <div
            style={{
              fontSize: '0.7rem',
              color: 'var(--text-secondary)',
              marginBottom: '8px',
              fontFamily: 'monospace',
            }}
          >
            schema v{report.schemaVersion} · {report.recordCount} record
            {report.recordCount === 1 ? '' : 's'}
          </div>
          <ol
            style={{
              listStyle: 'none',
              margin: 0,
              padding: 0,
              display: 'flex',
              flexDirection: 'column',
              gap: '8px',
            }}
          >
            {report.records.map((r) => (
              <li
                key={`${r.signoffUtc}-${r.reviewer}`}
                style={{
                  borderLeft: '3px solid var(--border)',
                  paddingLeft: '8px',
                }}
              >
                <div
                  style={{
                    display: 'flex',
                    gap: '8px',
                    alignItems: 'center',
                    marginBottom: '2px',
                  }}
                >
                  <VerdictPill verdict={r.verdict} />
                  <span style={{ fontSize: '0.78rem', fontWeight: 600 }}>{r.reviewer}</span>
                  <span
                    style={{
                      fontSize: '0.7rem',
                      color: 'var(--text-secondary)',
                      fontFamily: 'monospace',
                    }}
                  >
                    {r.signoffUtc}
                  </span>
                </div>
                {r.notes && (
                  <div
                    style={{
                      fontSize: '0.72rem',
                      color: 'var(--text-secondary)',
                      paddingLeft: '4px',
                    }}
                  >
                    {r.notes}
                  </div>
                )}
              </li>
            ))}
          </ol>
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
