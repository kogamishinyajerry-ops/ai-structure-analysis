// FM-04a Phase 4 E — Case completeness inline card.
//
// Tier 1 engineering candidate; not signed validation; not benchmark agreement.
//
// Renders the rubric breakdown for the selected case alongside the
// verbatim FM-04b blockers list. Reviewer uses this to see which
// evidence is missing and what each entry contributes to the score.

import { useEffect, useState } from 'react'
import type {
  CaseCompletenessScore,
  CompletenessBreakdownEntry,
} from '../caseCompletenessClient.ts'
import { fetchCaseCompleteness } from '../caseCompletenessClient.ts'
import { TIER1_BANNER, type TrustCenterTone } from '../trustCenterSummary.ts'

export interface CaseCompletenessCardProps {
  apiBase: string
  caseId: string | null
}

const SECTION_TITLE_STYLE = {
  fontSize: '0.7rem',
  textTransform: 'uppercase' as const,
  letterSpacing: '0.06em',
  color: 'var(--text-secondary)',
}

function entryTone(entry: CompletenessBreakdownEntry): TrustCenterTone {
  if (entry.pointsAwarded === entry.pointsMax) return 'accent'
  if (entry.pointsAwarded > 0) return 'warning'
  return 'danger'
}

function toneColor(tone: TrustCenterTone): string {
  if (tone === 'accent') return 'var(--accent, #0a8a4a)'
  if (tone === 'warning') return 'var(--text-warning, #b8860b)'
  if (tone === 'danger') return 'var(--danger, #c0392b)'
  return 'var(--text-secondary)'
}

function BreakdownRow({ entry }: { entry: CompletenessBreakdownEntry }) {
  const tone = entryTone(entry)
  return (
    <div
      style={{
        display: 'grid',
        gridTemplateColumns: '160px 90px 1fr',
        gap: '8px',
        fontSize: '0.72rem',
        padding: '3px 0',
        borderBottom: '1px solid var(--border)',
        color: toneColor(tone),
      }}
    >
      <code style={{ overflowWrap: 'anywhere' }}>{entry.label}</code>
      <strong>{entry.pointsAwarded}/{entry.pointsMax}</strong>
      <code style={{ color: 'var(--text-primary)' }}>
        {entry.evidenceStatus}
        {entry.notes ? ` · ${entry.notes}` : ''}
      </code>
    </div>
  )
}

export function CaseCompletenessCard({ apiBase, caseId }: CaseCompletenessCardProps) {
  const [score, setScore] = useState<CaseCompletenessScore | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (!caseId) {
      setScore(null)
      setError(null)
      return
    }
    const controller = new AbortController()
    setLoading(true)
    fetchCaseCompleteness(apiBase, caseId, controller.signal)
      .then((result) => {
        setScore(result.score)
        setError(result.error ?? null)
      })
      .finally(() => setLoading(false))
    return () => controller.abort()
  }, [apiBase, caseId])

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
      data-testid="case-completeness-card"
    >
      <div>
        <div style={{ ...SECTION_TITLE_STYLE, color: 'var(--text-warning, #b8860b)' }}>
          Case completeness rubric
        </div>
        <div style={{ fontSize: '0.65rem', color: 'var(--text-secondary)' }}>
          {TIER1_BANNER} · evidence-presence only (a 100/100 score does NOT
          authorize Tier 2 promotion)
        </div>
      </div>

      {loading && (
        <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
          loading completeness score…
        </div>
      )}

      {!loading && !score && (
        <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
          {!caseId
            ? 'Select a candidate case above.'
            : (error ?? 'No completeness score available.')}
        </div>
      )}

      {score && (
        <>
          <div style={{ fontSize: '0.85rem', color: 'var(--text-primary)' }}>
            {score.caseId} · total <strong>{score.score}/{score.scoreMax}</strong>{' '}
            · missing {score.missingEvidence.length} item(s)
          </div>

          <div
            style={{
              display: 'grid',
              gridTemplateColumns: '160px 90px 1fr',
              gap: '8px',
              fontSize: '0.65rem',
              color: 'var(--text-secondary)',
              padding: '4px 0',
              borderBottom: '1px solid var(--border)',
              textTransform: 'uppercase',
              letterSpacing: '0.06em',
            }}
          >
            <span>rubric entry</span>
            <span>points</span>
            <span>evidence status</span>
          </div>

          {score.breakdown.map((entry) => (
            <BreakdownRow key={entry.label} entry={entry} />
          ))}

          <div>
            <div style={SECTION_TITLE_STYLE}>FM-04b blockers still remaining</div>
            <ul
              style={{
                margin: 0,
                paddingLeft: '20px',
                fontSize: '0.7rem',
                color: 'var(--text-secondary)',
              }}
            >
              {score.tier2BlockersRemaining.map((blocker) => (
                <li key={blocker}>{blocker}</li>
              ))}
            </ul>
          </div>

          <div style={{ fontSize: '0.65rem', color: 'var(--text-secondary)' }}>
            {score.claimImpact}
          </div>
        </>
      )}
    </div>
  )
}
