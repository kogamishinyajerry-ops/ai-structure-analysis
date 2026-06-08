// FM-04a Phase 4 F — Archived packet diff panel.
//
// Tier 1 engineering candidate; not signed validation; not benchmark agreement.
//
// Two text fields for archived JSON paths (relative to reports/) +
// "Compute diff" button → renders the structured diff using the same
// axis vocabulary as Phase 3 C's CaseComparisonPanel.

import { useState } from 'react'
import type {
  AbsoluteDelta,
  ArchivedPacketDiff,
  NumericDelta,
} from '../archivedPacketDiffClient.ts'
import { fetchArchivedPacketDiff } from '../archivedPacketDiffClient.ts'
import { TIER1_BANNER, type TrustCenterTone } from '../trustCenterSummary.ts'

export interface ArchivedPacketDiffPanelProps {
  apiBase: string
}

const SECTION_TITLE_STYLE = {
  fontSize: '0.7rem',
  textTransform: 'uppercase' as const,
  letterSpacing: '0.06em',
  color: 'var(--text-secondary)',
}

function deltaTone(absPct: number | null | undefined): TrustCenterTone {
  if (absPct === null || absPct === undefined) return 'muted'
  const abs = Math.abs(absPct)
  if (abs <= 5) return 'accent'
  if (abs <= 15) return 'warning'
  return 'danger'
}

function numericDeltaTone(delta: NumericDelta): TrustCenterTone {
  return deltaTone(delta.deltaPct)
}

function absoluteDeltaTone(delta: AbsoluteDelta): TrustCenterTone {
  return deltaTone(delta.deltaAbsPct)
}

function toneColor(tone: TrustCenterTone): string {
  if (tone === 'accent') return 'var(--accent, #bd5d3a)'
  if (tone === 'warning') return 'var(--text-warning, var(--warn-400))'
  if (tone === 'danger') return 'var(--danger, var(--danger-400))'
  return 'var(--text-secondary)'
}

function DiffRow({
  axis,
  a,
  b,
  delta,
  tone,
}: {
  axis: string
  a: string
  b: string
  delta: string
  tone: TrustCenterTone
}) {
  return (
    <div
      style={{
        display: 'grid',
        gridTemplateColumns: '200px 1fr 1fr 140px',
        gap: '8px',
        fontSize: '0.78rem',
        padding: '4px 0',
        borderBottom: '1px solid var(--border)',
        color: 'var(--text-primary)',
        alignItems: 'baseline',
      }}
    >
      <span style={{ color: 'var(--text-secondary)' }}>{axis}</span>
      <code style={{ overflowWrap: 'anywhere' }}>{a}</code>
      <code style={{ overflowWrap: 'anywhere' }}>{b}</code>
      <strong style={{ color: toneColor(tone) }}>{delta}</strong>
    </div>
  )
}

export function ArchivedPacketDiffPanel({ apiBase }: ArchivedPacketDiffPanelProps) {
  const [pathA, setPathA] = useState('')
  const [pathB, setPathB] = useState('')
  const [diff, setDiff] = useState<ArchivedPacketDiff | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  async function compute() {
    if (!pathA.trim() || !pathB.trim()) {
      setError('both archive paths are required')
      setDiff(null)
      return
    }
    setLoading(true)
    setError(null)
    const result = await fetchArchivedPacketDiff(apiBase, pathA.trim(), pathB.trim())
    setLoading(false)
    setDiff(result.diff)
    setError(result.error ?? null)
  }

  return (
    <div
      style={{
        padding: '12px 16px',
        borderRadius: '10px',
        border: '1px solid var(--border)',
        background: 'var(--bg-surface)',
        display: 'flex',
        flexDirection: 'column',
        gap: '10px',
      }}
      data-testid="archived-packet-diff-panel"
    >
      <div>
        <div style={{ ...SECTION_TITLE_STYLE, color: 'var(--text-warning, var(--warn-400))' }}>
          Archived packet diff
        </div>
        <div style={{ fontSize: '0.65rem', color: 'var(--text-secondary)' }}>
          {TIER1_BANNER} · archive-vs-archive (does not re-run live builders)
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 110px', gap: '8px' }}>
        <input
          type="text"
          placeholder="reports/case-a_acceptance_packet.json"
          value={pathA}
          onChange={(event) => setPathA(event.target.value)}
          style={{
            padding: '6px 8px',
            borderRadius: '6px',
            border: '1px solid var(--border)',
            background: 'var(--bg-surface)',
            color: 'var(--text-primary)',
            fontSize: '0.78rem',
          }}
          data-testid="archived-diff-path-a"
        />
        <input
          type="text"
          placeholder="reports/case-b_acceptance_packet.json"
          value={pathB}
          onChange={(event) => setPathB(event.target.value)}
          style={{
            padding: '6px 8px',
            borderRadius: '6px',
            border: '1px solid var(--border)',
            background: 'var(--bg-surface)',
            color: 'var(--text-primary)',
            fontSize: '0.78rem',
          }}
          data-testid="archived-diff-path-b"
        />
        <button
          type="button"
          onClick={compute}
          disabled={loading}
          style={{
            padding: '6px 10px',
            borderRadius: '6px',
            border: '1px solid var(--border)',
            background: 'transparent',
            color: 'var(--text-primary)',
            fontSize: '0.78rem',
            cursor: loading ? 'wait' : 'pointer',
          }}
          data-testid="archived-diff-compute"
        >
          {loading ? '…' : 'Compute'}
        </button>
      </div>

      {error && (
        <div style={{ fontSize: '0.72rem', color: 'var(--danger, var(--danger-400))' }}>
          {error}
        </div>
      )}

      {diff && (
        <>
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: '200px 1fr 1fr 140px',
              gap: '8px',
              fontSize: '0.65rem',
              color: 'var(--text-secondary)',
              padding: '4px 0',
              borderBottom: '1px solid var(--border)',
              textTransform: 'uppercase',
              letterSpacing: '0.06em',
            }}
          >
            <span>axis</span>
            <span>archive A · {diff.archiveA.caseId}</span>
            <span>archive B · {diff.archiveB.caseId}</span>
            <span>delta</span>
          </div>

          <DiffRow
            axis="residual velocity"
            a={
              diff.residualVelocityDiff.a !== null
                ? `${diff.residualVelocityDiff.a} m/s`
                : '—'
            }
            b={
              diff.residualVelocityDiff.b !== null
                ? `${diff.residualVelocityDiff.b} m/s`
                : '—'
            }
            delta={
              diff.residualVelocityDiff.deltaPct !== null
                ? `${diff.residualVelocityDiff.deltaPct.toFixed(2)}%`
                : '—'
            }
            tone={numericDeltaTone(diff.residualVelocityDiff)}
          />
          <DiffRow
            axis="perforation marker"
            a={diff.perforationMarkerDiff.a ?? '—'}
            b={diff.perforationMarkerDiff.b ?? '—'}
            delta={diff.perforationMarkerDiff.sameMarker ? 'same' : 'differ'}
            tone={diff.perforationMarkerDiff.sameMarker ? 'accent' : 'danger'}
          />
          <DiffRow
            axis="energy balance error"
            a={
              diff.energyBalanceErrorDiff.a !== null
                ? `${diff.energyBalanceErrorDiff.a}%`
                : '—'
            }
            b={
              diff.energyBalanceErrorDiff.b !== null
                ? `${diff.energyBalanceErrorDiff.b}%`
                : '—'
            }
            delta={
              diff.energyBalanceErrorDiff.deltaAbsPct !== null
                ? `${diff.energyBalanceErrorDiff.deltaAbsPct.toFixed(2)}%`
                : '—'
            }
            tone={absoluteDeltaTone(diff.energyBalanceErrorDiff)}
          />
          <DiffRow
            axis="energy audit status"
            a={diff.energyAuditStatusDiff.a}
            b={diff.energyAuditStatusDiff.b}
            delta={diff.energyAuditStatusDiff.bothClosed ? 'both closed' : 'differ'}
            tone={diff.energyAuditStatusDiff.bothClosed ? 'accent' : 'warning'}
          />
          <DiffRow
            axis="convergence verdict"
            a={diff.convergenceVerdictDiff.a}
            b={diff.convergenceVerdictDiff.b}
            delta={diff.convergenceVerdictDiff.sameVerdict ? 'same' : 'differ'}
            tone={diff.convergenceVerdictDiff.sameVerdict ? 'accent' : 'warning'}
          />

          <div style={{ fontSize: '0.65rem', color: 'var(--text-secondary)' }}>
            archive A · sha256 <code>{diff.archiveA.sha256.slice(0, 12)}…</code> ·{' '}
            mtime {diff.archiveA.mtimeUtc}
          </div>
          <div style={{ fontSize: '0.65rem', color: 'var(--text-secondary)' }}>
            archive B · sha256 <code>{diff.archiveB.sha256.slice(0, 12)}…</code> ·{' '}
            mtime {diff.archiveB.mtimeUtc}
          </div>
          <div style={{ fontSize: '0.65rem', color: 'var(--text-secondary)' }}>
            {diff.claimImpact}
          </div>
        </>
      )}
    </div>
  )
}
