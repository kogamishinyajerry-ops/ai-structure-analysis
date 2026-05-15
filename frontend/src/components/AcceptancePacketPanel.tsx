// FM-04a Phase 3 C — Acceptance evidence packet reviewer panel.
//
// Tier 1 engineering candidate; not signed validation; not benchmark agreement.
//
// Renders the Tier 1 candidate acceptance packet for the selected case.
// "Download JSON" links straight to the `/api/v1/acceptance-packet/<id>`
// endpoint so reviewers can archive the manifest without going through
// the React state. Read-only over project_state/ + golden_samples/**.

import { useEffect, useState } from 'react'
import type {
  AcceptancePacket,
  AcceptanceArtifact,
} from '../acceptancePacketClient'
import {
  acceptancePacketDownloadUrl,
  fetchAcceptancePacket,
} from '../acceptancePacketClient'
import { TIER1_BANNER } from '../trustCenterSummary'

export interface AcceptancePacketPanelProps {
  apiBase: string
  caseId: string | null
}

const SECTION_TITLE_STYLE = {
  fontSize: '0.7rem',
  textTransform: 'uppercase' as const,
  letterSpacing: '0.06em',
  color: 'var(--text-secondary)',
}

function ArtifactRow({ artifact }: { artifact: AcceptanceArtifact }) {
  return (
    <div
      style={{
        display: 'grid',
        gridTemplateColumns: '120px 1fr 90px 110px',
        gap: '8px',
        fontSize: '0.72rem',
        color: 'var(--text-primary)',
        padding: '3px 0',
        borderBottom: '1px solid var(--border)',
      }}
    >
      <span style={{ color: 'var(--text-secondary)' }}>{artifact.kind}</span>
      <code style={{ overflowWrap: 'anywhere' }}>{artifact.relpath}</code>
      <span>{artifact.bytes !== null ? `${artifact.bytes} B` : '—'}</span>
      <code
        title={artifact.sha256 ?? 'no hash'}
        style={{ overflowWrap: 'anywhere' }}
      >
        {artifact.sha256 ? artifact.sha256.slice(0, 12) + '…' : '—'}
      </code>
    </div>
  )
}

export function AcceptancePacketPanel({ apiBase, caseId }: AcceptancePacketPanelProps) {
  const [packet, setPacket] = useState<AcceptancePacket | null>(null)
  const [source, setSource] = useState<'live' | 'fallback'>('fallback')
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (!caseId) {
      setPacket(null)
      setError(null)
      setSource('fallback')
      return
    }
    const controller = new AbortController()
    setLoading(true)
    fetchAcceptancePacket(apiBase, caseId, controller.signal)
      .then((result) => {
        setPacket(result.packet)
        setSource(result.source)
        setError(result.error ?? null)
      })
      .finally(() => setLoading(false))
    return () => controller.abort()
  }, [apiBase, caseId])

  const downloadHref = caseId ? acceptancePacketDownloadUrl(apiBase, caseId) : null

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
      data-testid="acceptance-packet-panel"
    >
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
        }}
      >
        <div>
          <div style={{ ...SECTION_TITLE_STYLE, color: 'var(--text-warning, #b8860b)' }}>
            Acceptance evidence packet
          </div>
          <div style={{ fontSize: '0.85rem', color: 'var(--text-primary)' }}>
            {caseId ?? 'Select a candidate case above'}
          </div>
          <div style={{ fontSize: '0.65rem', color: 'var(--text-secondary)' }}>
            {TIER1_BANNER}
          </div>
        </div>
        {downloadHref && (
          <a
            href={downloadHref}
            download
            data-testid="acceptance-packet-download"
            style={{
              padding: '6px 12px',
              borderRadius: '8px',
              border: '1px solid var(--border)',
              fontSize: '0.75rem',
              color: 'var(--text-primary)',
              background: 'var(--bg-secondary, transparent)',
              textDecoration: 'none',
            }}
          >
            Download JSON
          </a>
        )}
      </div>

      {loading && (
        <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
          loading acceptance packet…
        </div>
      )}

      {!loading && !packet && (
        <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
          {error ?? 'No acceptance packet available for the selected case.'}
        </div>
      )}

      {packet && (
        <>
          <div style={{ fontSize: '0.7rem', color: 'var(--text-secondary)' }}>
            generated {packet.generatedAtUtc} · source: {source}{' '}
            {error ? `(${error})` : ''}
          </div>

          <div>
            <div style={SECTION_TITLE_STYLE}>Ballistic summary</div>
            <div style={{ fontSize: '0.78rem', color: 'var(--text-primary)' }}>
              marker:{' '}
              <strong>
                {packet.ballisticMetricsSummary.perforationMarker ?? '—'}
              </strong>{' '}
              · V₀={packet.ballisticMetricsSummary.projectileInitialVelocityMPerS ?? '—'} m/s ·
              V_res=
              {packet.ballisticMetricsSummary.residualVelocityCandidateMPerS ?? '—'} m/s
            </div>
          </div>

          <div>
            <div style={SECTION_TITLE_STYLE}>Energy audit</div>
            <div style={{ fontSize: '0.78rem', color: 'var(--text-primary)' }}>
              status: <strong>{packet.energyAuditSummary.status}</strong> · balance_err:{' '}
              {packet.energyAuditSummary.energyBalanceErrorPct !== null
                ? `${packet.energyAuditSummary.energyBalanceErrorPct.toFixed(2)}%`
                : 'n/a'}{' '}
              · breakdown: {packet.energyAuditSummary.breakdownStatus}
            </div>
          </div>

          <div>
            <div style={SECTION_TITLE_STYLE}>Convergence study</div>
            <div style={{ fontSize: '0.78rem', color: 'var(--text-primary)' }}>
              status: <strong>{packet.convergenceStudySummary.status}</strong> · verdict:{' '}
              {packet.convergenceStudySummary.combinedVerdict} · mesh:{' '}
              {packet.convergenceStudySummary.meshSweepStability} · dt:{' '}
              {packet.convergenceStudySummary.dtSweepStability}
            </div>
          </div>

          {packet.deckArtifacts.length + packet.evidenceArtifacts.length > 0 && (
            <div>
              <div style={SECTION_TITLE_STYLE}>Artifacts</div>
              <div
                style={{
                  display: 'grid',
                  gridTemplateColumns: '120px 1fr 90px 110px',
                  gap: '8px',
                  fontSize: '0.65rem',
                  color: 'var(--text-secondary)',
                  padding: '3px 0',
                  borderBottom: '1px solid var(--border)',
                }}
              >
                <span>kind</span>
                <span>relpath</span>
                <span>bytes</span>
                <span>sha256</span>
              </div>
              {[
                ...packet.deckArtifacts,
                ...packet.evidenceArtifacts,
                ...packet.visualizationArtifacts,
              ].map((art) => (
                <ArtifactRow key={`${art.kind}:${art.relpath}`} artifact={art} />
              ))}
            </div>
          )}

          <div>
            <div style={SECTION_TITLE_STYLE}>FM-04b blockers still remaining</div>
            <ul
              style={{
                margin: 0,
                paddingLeft: '20px',
                fontSize: '0.72rem',
                color: 'var(--text-secondary)',
              }}
            >
              {packet.tier2BlockersRemaining.map((b) => (
                <li key={b}>{b}</li>
              ))}
            </ul>
          </div>

          <div style={{ fontSize: '0.65rem', color: 'var(--text-secondary)' }}>
            {packet.claimImpact}
          </div>
        </>
      )}
    </div>
  )
}
