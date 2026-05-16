// FM-04a Phase 5 E — Reproducibility manifest card.
//
// Tier 1 engineering candidate; not signed validation; not benchmark agreement.
//
// Renders the `/reproducibility-manifest/<case-id>` payload (Phase 5 B)
// as a compact card alongside the existing reviewer surface. Surfaces
// schemaVersion explicitly, plus git state, Python interpreter, and
// the list of tracked package versions + script fingerprints.

import { useEffect, useState } from 'react'
import {
  fetchReproducibilityManifest,
  gitStateLabel,
  shortenCommit,
  type ReproducibilityManifest,
} from '../reproducibilityManifestClient.ts'
import { TIER1_BANNER } from '../trustCenterSummary.ts'

export interface ReproducibilityManifestCardProps {
  apiBase: string
  caseId: string | null
}

const SECTION_TITLE_STYLE = {
  fontSize: '0.7rem',
  textTransform: 'uppercase' as const,
  letterSpacing: '0.06em',
  color: 'var(--text-secondary)',
}

export function ReproducibilityManifestCard({
  apiBase,
  caseId,
}: ReproducibilityManifestCardProps) {
  const [manifest, setManifest] = useState<ReproducibilityManifest | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (!caseId) {
      setManifest(null)
      setError(null)
      return
    }
    const ctrl = new AbortController()
    setLoading(true)
    void fetchReproducibilityManifest(apiBase, caseId, ctrl.signal).then((result) => {
      setLoading(false)
      if (result.manifest) {
        setManifest(result.manifest)
        setError(null)
      } else {
        setManifest(null)
        setError(result.error ?? 'unable to load reproducibility manifest')
      }
    })
    return () => ctrl.abort()
  }, [apiBase, caseId])

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
        <h3 style={{ margin: 0, fontSize: '0.95rem' }}>Reproducibility manifest</h3>
        <div style={{ fontSize: '0.7rem', color: 'var(--text-secondary)' }}>
          {TIER1_BANNER}
        </div>
      </header>

      {!caseId && (
        <div style={{ fontSize: '0.78rem', color: 'var(--text-secondary)' }}>
          select a candidate case to load its reproducibility manifest
        </div>
      )}
      {caseId && loading && (
        <div style={{ fontSize: '0.78rem', color: 'var(--text-secondary)' }}>loading…</div>
      )}
      {caseId && error && !loading && (
        <div style={{ fontSize: '0.78rem', color: 'var(--danger, #c0392b)' }}>{error}</div>
      )}
      {manifest && (
        <div>
          <div style={{ marginBottom: '8px' }}>
            <div style={SECTION_TITLE_STYLE}>case</div>
            <div style={{ fontSize: '0.85rem', fontFamily: 'monospace' }}>
              {manifest.caseId}
            </div>
            <div
              style={{
                fontSize: '0.7rem',
                color: 'var(--text-secondary)',
                fontFamily: 'monospace',
              }}
            >
              schema v{manifest.schemaVersion || '?'} · captured{' '}
              {manifest.generatedAtUtc}
            </div>
          </div>

          <div style={{ marginBottom: '8px' }}>
            <div style={SECTION_TITLE_STYLE}>git state</div>
            <div style={{ fontSize: '0.78rem', fontFamily: 'monospace' }}>
              {gitStateLabel(manifest)}
            </div>
            {manifest.gitCommitSha && (
              <div
                style={{
                  fontSize: '0.7rem',
                  color: 'var(--text-secondary)',
                  fontFamily: 'monospace',
                }}
              >
                full sha: {shortenCommit(manifest.gitCommitSha)} (
                {manifest.gitCommitSha.length} chars)
              </div>
            )}
          </div>

          <div style={{ marginBottom: '8px' }}>
            <div style={SECTION_TITLE_STYLE}>python</div>
            <div style={{ fontSize: '0.78rem' }}>
              {manifest.pythonImplementation} {manifest.pythonVersion}
            </div>
            <div style={{ fontSize: '0.7rem', color: 'var(--text-secondary)' }}>
              {manifest.platformSummary}
            </div>
          </div>

          {manifest.trackedPackages.length > 0 && (
            <div style={{ marginBottom: '8px' }}>
              <div style={SECTION_TITLE_STYLE}>tracked packages</div>
              <div
                style={{
                  display: 'grid',
                  gridTemplateColumns: '1fr auto',
                  gap: '4px 12px',
                  fontSize: '0.72rem',
                  fontFamily: 'monospace',
                }}
              >
                {manifest.trackedPackages.map((pkg) => (
                  <PackageRow key={pkg.name} name={pkg.name} version={pkg.version} />
                ))}
              </div>
            </div>
          )}

          {manifest.scripts.length > 0 && (
            <div style={{ marginBottom: '8px' }}>
              <div style={SECTION_TITLE_STYLE}>generator script SHA-256</div>
              {manifest.scripts.map((s) => (
                <div
                  key={s.relpath}
                  style={{ fontSize: '0.72rem', fontFamily: 'monospace', marginTop: '2px' }}
                >
                  <div>{s.relpath}</div>
                  <div style={{ color: 'var(--text-secondary)' }}>
                    {s.sha256.slice(0, 16)}…{s.sha256.slice(-8)} · {s.bytes} bytes
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
            {manifest.claimImpact}
          </div>
        </div>
      )}
    </section>
  )
}

function PackageRow({ name, version }: { name: string; version: string }) {
  const installed = version !== 'not_installed'
  return (
    <>
      <div>{name}</div>
      <div
        style={{
          color: installed ? 'var(--text-primary)' : 'var(--danger, #c0392b)',
        }}
      >
        {version}
      </div>
    </>
  )
}
