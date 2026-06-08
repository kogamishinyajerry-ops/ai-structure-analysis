// FM-04a Phase 5 E — Cohort snapshot picker + drift panel.
//
// Tier 1 engineering candidate; not signed validation; not benchmark agreement.
//
// Lists past snapshots from `/cohort-snapshots` (Phase 5 C) and lets
// the reviewer pick two of them to diff via `/cohort-snapshot-diff`
// (Phase 5 D). Surfaces:
//   - cohort membership delta (added / removed)
//   - per-case completeness score delta (improved / regressed)
//   - per-case reproducibility drift (git / python / scripts)
//
// Every emitted line carries the Tier 1 disclaimer trio surfaced via
// the TIER1_BANNER constant. schemaVersion is rendered visibly on
// every snapshot row so a reviewer can spot when the underlying
// contract changed between snapshots.

import { useEffect, useMemo, useState } from 'react'
import {
  fetchCohortSnapshotDiff,
  fetchSnapshotListing,
  summarizeCompletenessDrift,
  summarizeReproDrift,
  type CohortSnapshotDiff,
  type SnapshotListing,
  type SnapshotListingEntry,
} from '../cohortSnapshotClient.ts'
import { TIER1_BANNER } from '../trustCenterSummary.ts'

export interface CohortSnapshotPanelProps {
  apiBase: string
  /**
   * Phase 6 E — optional controlled label state. When the parent passes
   * `selectedLabelA` / `selectedLabelB` + `onSelectLabelA` / `onSelectLabelB`,
   * the panel becomes a controlled component. Otherwise it owns the labels
   * internally (Phase 5 behavior).
   */
  selectedLabelA?: string | null
  selectedLabelB?: string | null
  onSelectLabelA?: (label: string) => void
  onSelectLabelB?: (label: string) => void
}

const SECTION_TITLE_STYLE = {
  fontSize: '0.7rem',
  textTransform: 'uppercase' as const,
  letterSpacing: '0.06em',
  color: 'var(--text-secondary)',
}

function deltaTone(delta: number | null): string {
  if (delta === null) return 'var(--text-secondary)'
  if (delta > 0) return 'var(--success-500)'
  if (delta < 0) return 'var(--danger-400)'
  return 'var(--text-primary)'
}

function formatDelta(delta: number | null): string {
  if (delta === null) return 'n/a'
  if (delta > 0) return `+${delta}`
  return `${delta}`
}

function SnapshotRow({
  entry,
  selectedA,
  selectedB,
  onClickA,
  onClickB,
}: {
  entry: SnapshotListingEntry
  selectedA: boolean
  selectedB: boolean
  onClickA: () => void
  onClickB: () => void
}) {
  return (
    <div
      style={{
        display: 'grid',
        gridTemplateColumns: '180px 70px 1fr 70px 60px 60px',
        gap: '8px',
        padding: '6px 0',
        borderBottom: '1px solid var(--border)',
        fontSize: '0.78rem',
        color: 'var(--text-primary)',
        alignItems: 'center',
      }}
    >
      <div style={{ fontFamily: 'monospace' }}>{entry.snapshotLabel}</div>
      <div style={{ fontFamily: 'monospace', color: 'var(--text-secondary)' }}>
        v{entry.schemaVersion || '?'}
      </div>
      <div style={{ fontSize: '0.72rem', color: 'var(--text-secondary)' }}>
        {entry.cases.slice(0, 3).join(', ')}
        {entry.cases.length > 3 ? `, +${entry.cases.length - 3}` : ''}
      </div>
      <div style={{ textAlign: 'right' }}>{entry.cohortCount}</div>
      <button
        type="button"
        onClick={onClickA}
        style={{
          background: selectedA ? 'var(--accent)' : 'transparent',
          color: selectedA ? '#fff' : 'var(--text-primary)',
          border: '1px solid var(--border)',
          padding: '3px 8px',
          borderRadius: '4px',
          cursor: 'pointer',
          fontSize: '0.72rem',
        }}
      >
        A
      </button>
      <button
        type="button"
        onClick={onClickB}
        style={{
          background: selectedB ? 'var(--accent)' : 'transparent',
          color: selectedB ? '#fff' : 'var(--text-primary)',
          border: '1px solid var(--border)',
          padding: '3px 8px',
          borderRadius: '4px',
          cursor: 'pointer',
          fontSize: '0.72rem',
        }}
      >
        B
      </button>
    </div>
  )
}

function DriftSummary({ diff }: { diff: CohortSnapshotDiff }) {
  const completeness = useMemo(() => summarizeCompletenessDrift(diff), [diff])
  const repro = useMemo(() => summarizeReproDrift(diff), [diff])
  return (
    <div
      style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(3, 1fr)',
        gap: '12px',
        marginBottom: '12px',
      }}
    >
      <div style={{ padding: '8px', border: '1px solid var(--border)', borderRadius: '4px' }}>
        <div style={SECTION_TITLE_STYLE}>cohort membership</div>
        <div style={{ fontSize: '0.78rem' }}>
          + {diff.cohortAdded.length} added · − {diff.cohortRemoved.length} removed
        </div>
        <div style={{ fontSize: '0.72rem', color: 'var(--text-secondary)' }}>
          shared: {diff.cohortShared.length}
        </div>
      </div>
      <div style={{ padding: '8px', border: '1px solid var(--border)', borderRadius: '4px' }}>
        <div style={SECTION_TITLE_STYLE}>completeness drift</div>
        <div style={{ fontSize: '0.78rem' }}>
          ↑ {completeness.improved} · ↓ {completeness.regressed} · = {completeness.unchanged}
        </div>
      </div>
      <div style={{ padding: '8px', border: '1px solid var(--border)', borderRadius: '4px' }}>
        <div style={SECTION_TITLE_STYLE}>reproducibility drift</div>
        <div style={{ fontSize: '0.78rem' }}>
          git: {repro.gitChanged} · python: {repro.pythonChanged} · scripts: {repro.scriptsChanged}
        </div>
      </div>
    </div>
  )
}

function CompletenessTable({ diff }: { diff: CohortSnapshotDiff }) {
  if (diff.completenessDeltas.length === 0) {
    return (
      <div style={{ fontSize: '0.78rem', color: 'var(--text-secondary)' }}>
        no shared cases — completeness drift not computed
      </div>
    )
  }
  return (
    <div>
      <div style={SECTION_TITLE_STYLE}>per-case completeness delta</div>
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: '1fr 70px 70px 70px',
          gap: '8px',
          fontSize: '0.72rem',
          color: 'var(--text-secondary)',
          padding: '4px 0',
          borderBottom: '1px solid var(--border)',
        }}
      >
        <div>case_id</div>
        <div style={{ textAlign: 'right' }}>A</div>
        <div style={{ textAlign: 'right' }}>B</div>
        <div style={{ textAlign: 'right' }}>Δ</div>
      </div>
      {diff.completenessDeltas.map((d) => (
        <div
          key={d.caseId}
          style={{
            display: 'grid',
            gridTemplateColumns: '1fr 70px 70px 70px',
            gap: '8px',
            fontSize: '0.78rem',
            padding: '4px 0',
            borderBottom: '1px solid var(--border-subtle, var(--border))',
          }}
        >
          <div style={{ fontFamily: 'monospace' }}>{d.caseId}</div>
          <div style={{ textAlign: 'right' }}>{d.aScore ?? '—'}</div>
          <div style={{ textAlign: 'right' }}>{d.bScore ?? '—'}</div>
          <div style={{ textAlign: 'right', color: deltaTone(d.delta), fontWeight: 600 }}>
            {formatDelta(d.delta)}
          </div>
        </div>
      ))}
    </div>
  )
}

function ReproDriftTable({ diff }: { diff: CohortSnapshotDiff }) {
  if (diff.reproducibilityDeltas.length === 0) {
    return null
  }
  return (
    <div style={{ marginTop: '12px' }}>
      <div style={SECTION_TITLE_STYLE}>per-case reproducibility drift</div>
      {diff.reproducibilityDeltas.map((d) => {
        const hasDrift =
          d.gitShaChanged ||
          d.dirtyChanged ||
          d.pythonVersionChanged ||
          d.packageVersionChanges.length > 0 ||
          d.scriptShaChanges.length > 0
        return (
          <div
            key={d.caseId}
            style={{
              padding: '6px 0',
              borderBottom: '1px solid var(--border)',
              fontSize: '0.78rem',
            }}
          >
            <div style={{ fontFamily: 'monospace' }}>{d.caseId}</div>
            {!hasDrift && (
              <div style={{ color: 'var(--text-secondary)', fontSize: '0.72rem' }}>
                no drift detected
              </div>
            )}
            {d.gitShaChanged && (
              <div style={{ color: 'var(--warn-400)', fontSize: '0.72rem' }}>
                git sha drift
              </div>
            )}
            {d.pythonVersionChanged && (
              <div style={{ color: 'var(--warn-400)', fontSize: '0.72rem' }}>
                python: {d.aPythonVersion} → {d.bPythonVersion}
              </div>
            )}
            {d.packageVersionChanges.length > 0 && (
              <div style={{ fontSize: '0.72rem' }}>
                packages:{' '}
                {d.packageVersionChanges
                  .map((p) => `${p.name} ${p.aVersion} → ${p.bVersion}`)
                  .join('; ')}
              </div>
            )}
            {d.scriptShaChanges.length > 0 && (
              <div style={{ fontSize: '0.72rem' }}>
                script SHAs changed: {d.scriptShaChanges.map((s) => s.relpath).join(', ')}
              </div>
            )}
          </div>
        )
      })}
    </div>
  )
}

export function CohortSnapshotPanel({
  apiBase,
  selectedLabelA,
  selectedLabelB,
  onSelectLabelA,
  onSelectLabelB,
}: CohortSnapshotPanelProps) {
  const [listing, setListing] = useState<SnapshotListing | null>(null)
  const [listingError, setListingError] = useState<string | null>(null)
  const [internalLabelA, setInternalLabelA] = useState<string | null>(null)
  const [internalLabelB, setInternalLabelB] = useState<string | null>(null)
  const isControlled = selectedLabelA !== undefined || selectedLabelB !== undefined
  const labelA = isControlled ? selectedLabelA ?? null : internalLabelA
  const labelB = isControlled ? selectedLabelB ?? null : internalLabelB
  const setLabelA = (label: string) => {
    if (onSelectLabelA) onSelectLabelA(label)
    if (!isControlled) setInternalLabelA(label)
  }
  const setLabelB = (label: string) => {
    if (onSelectLabelB) onSelectLabelB(label)
    if (!isControlled) setInternalLabelB(label)
  }
  const [diff, setDiff] = useState<CohortSnapshotDiff | null>(null)
  const [diffError, setDiffError] = useState<string | null>(null)
  const [diffLoading, setDiffLoading] = useState(false)

  useEffect(() => {
    const ctrl = new AbortController()
    void fetchSnapshotListing(apiBase, ctrl.signal).then((result) => {
      if (result.listing) {
        setListing(result.listing)
        setListingError(null)
      } else {
        setListing(null)
        setListingError(result.error ?? 'unable to load snapshot listing')
      }
    })
    return () => ctrl.abort()
  }, [apiBase])

  useEffect(() => {
    if (!labelA || !labelB) {
      setDiff(null)
      setDiffError(null)
      return
    }
    if (labelA === labelB) {
      setDiff(null)
      setDiffError('snapshot A and B must differ')
      return
    }
    const ctrl = new AbortController()
    setDiffLoading(true)
    void fetchCohortSnapshotDiff(apiBase, labelA, labelB, ctrl.signal).then((result) => {
      setDiffLoading(false)
      if (result.diff) {
        setDiff(result.diff)
        setDiffError(null)
      } else {
        setDiff(null)
        setDiffError(result.error ?? 'unable to load snapshot diff')
      }
    })
    return () => ctrl.abort()
  }, [apiBase, labelA, labelB])

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
        <h3 style={{ margin: 0, fontSize: '0.95rem' }}>Cohort snapshot drift</h3>
        <div style={{ fontSize: '0.7rem', color: 'var(--text-secondary)' }}>{TIER1_BANNER}</div>
      </header>

      <div style={{ marginBottom: '12px' }}>
        <div style={SECTION_TITLE_STYLE}>available snapshots</div>
        {listingError && (
          <div style={{ fontSize: '0.78rem', color: 'var(--danger-400)' }}>
            {listingError}
          </div>
        )}
        {!listingError && listing && listing.snapshots.length === 0 && (
          <div style={{ fontSize: '0.78rem', color: 'var(--text-secondary)' }}>
            no snapshots written yet — run scripts/write_cohort_snapshot.py
          </div>
        )}
        {listing && listing.snapshots.length > 0 && (
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: '180px 70px 1fr 70px 60px 60px',
              gap: '8px',
              fontSize: '0.7rem',
              color: 'var(--text-secondary)',
              padding: '4px 0',
              borderBottom: '1px solid var(--border)',
            }}
          >
            <div>snapshot</div>
            <div>schema</div>
            <div>cases</div>
            <div style={{ textAlign: 'right' }}>count</div>
            <div></div>
            <div></div>
          </div>
        )}
        {listing?.snapshots.map((entry) => (
          <SnapshotRow
            key={entry.snapshotLabel}
            entry={entry}
            selectedA={labelA === entry.snapshotLabel}
            selectedB={labelB === entry.snapshotLabel}
            onClickA={() => setLabelA(entry.snapshotLabel)}
            onClickB={() => setLabelB(entry.snapshotLabel)}
          />
        ))}
      </div>

      {diffError && (
        <div style={{ fontSize: '0.78rem', color: 'var(--danger-400)' }}>
          {diffError}
        </div>
      )}
      {diffLoading && (
        <div style={{ fontSize: '0.78rem', color: 'var(--text-secondary)' }}>
          loading diff…
        </div>
      )}
      {diff && (
        <div>
          <div
            style={{
              fontSize: '0.72rem',
              color: 'var(--text-secondary)',
              marginBottom: '8px',
            }}
          >
            diffing {diff.snapshotALabel} → {diff.snapshotBLabel} · schema
            v{diff.schemaVersion || '?'}
          </div>
          <DriftSummary diff={diff} />
          <CompletenessTable diff={diff} />
          <ReproDriftTable diff={diff} />
          <div
            style={{
              fontSize: '0.7rem',
              color: 'var(--text-secondary)',
              marginTop: '12px',
            }}
          >
            {diff.claimImpact}
          </div>
        </div>
      )}
    </section>
  )
}
