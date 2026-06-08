// FM-04a Phase 4 E — Cohort dashboard panel.
//
// Tier 1 engineering candidate; not signed validation; not benchmark agreement.
//
// Renders the `/cohort-overview` payload as a sortable leaderboard
// table. "Drill" action sets the selected candidate-case id, anchoring
// at the existing Phase 3 reviewer panels. Tier 1 banner present;
// FM-04b blockers list rendered alongside the aggregate.

import { useEffect, useMemo, useState } from 'react'
// FM-04a Phase 19 D — adopt Phase 18 D primitives (UI agent round-2
// adoption finding).
import { EmptyStateCard } from './EmptyStateCard'
import { ErrorCard } from './ErrorCard'
import { SkeletonCard } from './SkeletonCard'
import type { CohortOverviewEntry, CohortSortKey } from '../cohortOverviewClient.ts'
import {
  fetchCohortOverview,
  scoreTone,
  sortCohortEntries,
  type CohortOverview,
} from '../cohortOverviewClient.ts'
import { TIER1_BANNER, type TrustCenterTone } from '../trustCenterSummary.ts'

export interface CohortDashboardPanelProps {
  apiBase: string
  selectedCaseId: string | null
  onSelectCase: (caseId: string) => void
}

const SECTION_TITLE_STYLE = {
  fontSize: '0.7rem',
  textTransform: 'uppercase' as const,
  letterSpacing: '0.06em',
  color: 'var(--text-secondary)',
}

function toneColor(tone: TrustCenterTone): string {
  if (tone === 'accent') return 'var(--success-500)'
  if (tone === 'warning') return 'var(--warn-400)'
  if (tone === 'danger') return 'var(--danger-400)'
  return 'var(--text-secondary)'
}

function CohortRow({
  entry,
  selected,
  onSelect,
}: {
  entry: CohortOverviewEntry
  selected: boolean
  onSelect: () => void
}) {
  const tone = scoreTone(entry.completenessScore)
  return (
    <div
      style={{
        display: 'grid',
        gridTemplateColumns: '1fr 60px 80px 110px 140px 90px 80px',
        gap: '8px',
        padding: '6px 0',
        borderBottom: '1px solid var(--border)',
        fontSize: '0.78rem',
        color: 'var(--text-primary)',
        alignItems: 'center',
        background: selected ? 'rgba(42,39,34,0.04)' : 'transparent',
      }}
      data-testid={`cohort-row-${entry.caseId}`}
    >
      <div style={{ display: 'flex', flexDirection: 'column', gap: '2px', overflow: 'hidden' }}>
        <code style={{ overflowWrap: 'anywhere' }}>{entry.caseId}</code>
        {entry.claimTier?.includes('Tier 2') ? (
          <span
            data-testid={`cohort-tier2-${entry.caseId}`}
            title={entry.claimTier}
            style={{
              alignSelf: 'flex-start',
              fontSize: '0.6rem',
              fontWeight: 600,
              padding: '1px 6px',
              borderRadius: '999px',
              color: 'var(--text-primary)',
              border: '1px solid var(--accent)',
              whiteSpace: 'nowrap',
            }}
          >
            ✓ Tier 2 real-solver validated
          </span>
        ) : null}
      </div>
      <strong style={{ color: toneColor(tone) }}>
        {entry.completenessScore}/{entry.completenessScoreMax}
      </strong>
      <code>{entry.perforationMarker ?? '—'}</code>
      <code>
        {entry.residualVelocityCandidateMPerS !== null
          ? `${entry.residualVelocityCandidateMPerS} m/s`
          : '—'}
      </code>
      <code>{entry.convergenceCombinedVerdict}</code>
      <code>{entry.energyAuditStatus}</code>
      <button
        type="button"
        onClick={onSelect}
        style={{
          padding: '4px 8px',
          borderRadius: '6px',
          border: '1px solid var(--border)',
          background: 'transparent',
          color: 'var(--text-primary)',
          fontSize: '0.72rem',
          cursor: 'pointer',
        }}
        data-testid={`cohort-drill-${entry.caseId}`}
      >
        Drill
      </button>
    </div>
  )
}

export function CohortDashboardPanel({
  apiBase,
  selectedCaseId,
  onSelectCase,
}: CohortDashboardPanelProps) {
  const [overview, setOverview] = useState<CohortOverview | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [sortKey, setSortKey] = useState<CohortSortKey>('score_desc')

  useEffect(() => {
    const controller = new AbortController()
    setLoading(true)
    fetchCohortOverview(apiBase, controller.signal)
      .then((result) => {
        setOverview(result.overview)
        setError(result.error ?? null)
      })
      .finally(() => setLoading(false))
    return () => controller.abort()
  }, [apiBase])

  const sortedEntries = useMemo(() => {
    if (!overview) return []
    return sortCohortEntries(overview.entries, sortKey)
  }, [overview, sortKey])

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
      data-testid="cohort-dashboard-panel"
    >
      <div
        style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}
      >
        <div>
          <div style={{ ...SECTION_TITLE_STYLE, color: 'var(--warn-400)' }}>
            Cohort dashboard
          </div>
          <div style={{ fontSize: '0.65rem', color: 'var(--text-secondary)' }}>
            {TIER1_BANNER} · evidence-presence score only (not validation quality)
          </div>
        </div>
        <select
          value={sortKey}
          onChange={(event) => setSortKey(event.target.value as CohortSortKey)}
          style={{
            padding: '4px 6px',
            borderRadius: '6px',
            border: '1px solid var(--border)',
            background: 'var(--bg-surface)',
            color: 'var(--text-primary)',
            fontSize: '0.72rem',
          }}
          data-testid="cohort-sort-select"
        >
          <option value="score_desc">Score ↓</option>
          <option value="score_asc">Score ↑</option>
          <option value="case_id_asc">Case ID</option>
          <option value="recency_desc">Most recently modified</option>
        </select>
      </div>

      {loading && (
        <div data-testid="cohort-dashboard-loading">
          <SkeletonCard lines={4} label="Loading cohort overview" />
        </div>
      )}

      {!loading && error && (
        <div data-testid="cohort-dashboard-error">
          <ErrorCard
            title="Could not load cohort overview"
            message={error}
            code="COHORT-LOAD"
            remediation={[
              'Check the backend /api/v1/cohort-overview route responds.',
              'Verify at least one *-candidate dir exists in golden_samples/.',
            ]}
          />
        </div>
      )}

      {!loading && !error && (!overview || overview.cohortCount === 0) && (
        <div data-testid="cohort-dashboard-empty">
          <EmptyStateCard
            headline="No Tier 1 candidate cases yet"
            body="The cohort is empty. Add a *-candidate directory under golden_samples/ to populate this view."
            glyph="∅"
          />
        </div>
      )}

      {overview && overview.cohortCount > 0 && (
        <>
          <div style={{ fontSize: '0.72rem', color: 'var(--text-primary)' }}>
            cohort {overview.cohortCount} cases · mean score{' '}
            {overview.meanScore === null ? '—' : overview.meanScore.toFixed(1)}/100 ·{' '}
            distribution: 100=<strong>{overview.completenessDistribution['100'] ?? 0}</strong>{' '}
            · 80-99=<strong>{overview.completenessDistribution['80-99'] ?? 0}</strong>{' '}
            · 50-79=<strong>{overview.completenessDistribution['50-79'] ?? 0}</strong>{' '}
            · 0-49=<strong>{overview.completenessDistribution['0-49'] ?? 0}</strong>
          </div>

          <div
            style={{
              display: 'grid',
              gridTemplateColumns: '1fr 60px 80px 110px 140px 90px 80px',
              gap: '8px',
              fontSize: '0.65rem',
              color: 'var(--text-secondary)',
              padding: '4px 0',
              borderBottom: '1px solid var(--border)',
              textTransform: 'uppercase',
              letterSpacing: '0.06em',
            }}
          >
            <span>case_id</span>
            <span>score</span>
            <span>marker</span>
            <span>V_res</span>
            <span>convergence</span>
            <span>audit</span>
            <span></span>
          </div>

          {sortedEntries.map((entry) => (
            <CohortRow
              key={entry.caseId}
              entry={entry}
              selected={selectedCaseId === entry.caseId}
              onSelect={() => onSelectCase(entry.caseId)}
            />
          ))}

          <div style={{ fontSize: '0.65rem', color: 'var(--text-secondary)' }}>
            FM-04b blockers still remaining ({overview.tier2BlockersRemaining.length}):{' '}
            {overview.tier2BlockersRemaining.slice(0, 2).join(' · ')}{' '}
            {overview.tier2BlockersRemaining.length > 2 ? '…' : ''}
          </div>
          <div style={{ fontSize: '0.65rem', color: 'var(--text-secondary)' }}>
            {overview.claimImpact}
          </div>
        </>
      )}
    </div>
  )
}
