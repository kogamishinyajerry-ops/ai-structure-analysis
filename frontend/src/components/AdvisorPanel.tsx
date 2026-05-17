// FM-04a Phase 11 E — AI advisor critique panel.
//
// Tier 1 engineering candidate; not signed validation; not benchmark agreement.
//
// Surfaces the AdvisorCritique payload from
// `GET /api/v1/advisor-critique/<case_id>?snapshot=<label>` as a UI
// panel adjacent to ProvenancePanel. The panel renders:
//   * advisor_status badge (online / offline / stub / unknown);
//   * a degrade_reason banner when the live LLM fell back to stub;
//   * the four-question gate checklist (4 green ticks or red X
//     per key, with the SSOT-pinned key label);
//   * four expandable sections: mesh concerns, BC questions,
//     failure modes, unhandled loads.
//
// Defensive design pillars (project north star + blueprint section 4):
//   * `parseAdvisorStatus` defaults unknown values to 'unknown' so a
//     future MINOR backend bump cannot crash the panel (X:-2).
//   * `isAdvisorEntrySafe` runs the client-side preview audit before
//     rendering any concern entry — defense in depth on top of the
//     backend forbidden-claim audit.
//   * The panel does NOT mutate any state; it only renders the
//     critique. Reviewer agency is preserved at every step.

import { useEffect, useState } from 'react'
// FM-04a Phase 18 E (round 3) — adopt the SSOT loading + error
// primitives in place of bespoke divs (UI agent round-2 finding).
import { ErrorCard } from './ErrorCard'
import { SkeletonCard } from './SkeletonCard'
import {
  FOUR_QUESTION_GATE_KEYS,
  REFUSED_CLAIMS_MAX_ITEMS,
  fetchAdvisorCritique,
  isAdvisorEntrySafe,
  type AdvisorCritique,
  type AdvisorStatus,
  type FourQuestionGateKey,
} from '../advisorCritiqueClient.ts'
import { TIER1_BANNER } from '../trustCenterSummary.ts'

export interface AdvisorPanelProps {
  apiBase: string
  caseId: string
  snapshotLabel: string
}

const _STATUS_COLOR: Record<AdvisorStatus, string> = {
  online: 'var(--accent)',
  offline: '#9b6b00',
  stub: '#666',
  unknown: '#888',
}

const _STATUS_LABEL: Record<AdvisorStatus, string> = {
  online: 'live LLM',
  offline: 'LLM unavailable (stub fallback)',
  stub: 'stub advisor',
  unknown: 'unknown advisor status (frontend out of date)',
}

const _GATE_KEY_LABEL: Record<FourQuestionGateKey, string> = {
  llm_offline_ok: 'LLM offline OK',
  artifacts_user_owned: 'artifacts user-owned',
  trustgate_explains: 'trust score explains',
  advisor_only: 'advisor-only (NOT driver)',
}

export function AdvisorPanel({ apiBase, caseId, snapshotLabel }: AdvisorPanelProps) {
  const [critique, setCritique] = useState<AdvisorCritique | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (!caseId || !snapshotLabel) {
      // App.tsx mounts this panel only when both are non-empty; the
      // guard is defense in depth so a malformed parent does not fire
      // a stray fetch with empty params.
      return
    }
    const ctrl = new AbortController()
    setLoading(true)
    void fetchAdvisorCritique(apiBase, caseId, snapshotLabel, ctrl.signal).then(
      (result) => {
        setLoading(false)
        if (result.critique) {
          setCritique(result.critique)
          setError(null)
        } else {
          setCritique(null)
          setError(result.error ?? 'unable to load advisor critique')
        }
      },
    )
    return () => ctrl.abort()
  }, [apiBase, caseId, snapshotLabel])

  return (
    <section
      data-testid="advisor-panel"
      style={{
        padding: '12px',
        border: '1px solid var(--border)',
        borderRadius: '6px',
        background: 'var(--surface)',
      }}
    >
      <header style={{ marginBottom: '8px' }}>
        <h3 style={{ margin: 0, fontSize: '0.95rem' }}>AI advisor critique</h3>
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
          {caseId} @ {snapshotLabel}
        </div>
      </header>

      {loading && (
        <div data-testid="advisor-panel-loading">
          <SkeletonCard lines={4} label="Loading advisor critique" />
        </div>
      )}

      {error && !loading && (
        <div data-testid="advisor-panel-error">
          <ErrorCard
            title="Could not load advisor critique"
            message={error}
            code="ADVISOR-LOAD"
            remediation={[
              'Check the backend /api/v1/advisor-critique/ route responds.',
              'If the live LLM is offline, the advisor falls back to a stub critique — that is expected behaviour.',
            ]}
          />
        </div>
      )}

      {critique && !loading && (
        <div>
          {/* advisor_status badge */}
          <div
            data-testid="advisor-status-badge"
            style={{
              display: 'inline-block',
              padding: '2px 8px',
              borderRadius: '999px',
              background: _STATUS_COLOR[critique.advisorStatus],
              color: '#fff',
              fontSize: '0.7rem',
              marginRight: '6px',
            }}
          >
            {_STATUS_LABEL[critique.advisorStatus]}
          </div>
          <span style={{ fontSize: '0.7rem', color: 'var(--text-secondary)' }}>
            backend: {critique.advisorBackend}
          </span>

          {/* degrade_reason banner */}
          {critique.degradeReason && (
            <div
              data-testid="advisor-degrade-reason"
              style={{
                marginTop: '8px',
                padding: '6px',
                background: '#fff4e0',
                border: '1px solid #d9a96b',
                fontSize: '0.7rem',
                fontFamily: 'monospace',
              }}
            >
              degraded: {critique.degradeReason}
            </div>
          )}

          {/* four-question gate checklist */}
          <div data-testid="advisor-gate-checklist" style={{ marginTop: '8px' }}>
            <div style={{ fontSize: '0.75rem', fontWeight: 600 }}>
              Four-question gate
            </div>
            <ul style={{ paddingLeft: '18px', margin: '4px 0', fontSize: '0.7rem' }}>
              {FOUR_QUESTION_GATE_KEYS.map((key) => {
                const value = critique.fourQuestionGate[key]
                const present = value === true
                return (
                  <li key={key} data-testid={`advisor-gate-${key}`}>
                    <span
                      style={{
                        color: present ? 'var(--accent)' : '#b00020',
                        fontWeight: 700,
                      }}
                    >
                      {present ? '✓' : value === false ? '✗' : '?'}
                    </span>{' '}
                    {_GATE_KEY_LABEL[key]}
                  </li>
                )
              })}
            </ul>
          </div>

          {/* four content sections */}
          <_Section
            testid="advisor-mesh-concerns"
            title="Mesh quality concerns"
            entries={critique.meshQualityConcerns}
          />
          <_Section
            testid="advisor-bc-questions"
            title="Boundary condition questions"
            entries={critique.boundaryConditionQuestions}
          />
          <_Section
            testid="advisor-failure-modes"
            title="Failure modes to consider"
            entries={critique.failureModesToConsider}
          />
          <_Section
            testid="advisor-unhandled-loads"
            title="Unhandled load cases"
            entries={critique.unhandledLoadCases}
          />

          {/*
            Phase 13 A — refused-claim suppression history. Only renders
            when at least one marker is present (collapsed visibility
            when empty). The markers name WHICH forbidden token tripped
            the per-section filter; the original positive-claim text
            was DISCARDED upstream and never reaches this panel.
          */}
          <_RefusedClaimsSection refusedClaims={critique.refusedClaims} />

          {/* footer disclaimer trio */}
          <footer
            data-testid="advisor-claim-footer"
            style={{
              marginTop: '8px',
              fontSize: '0.65rem',
              color: 'var(--text-secondary)',
              fontFamily: 'monospace',
            }}
          >
            <div>{critique.claimTier}</div>
            <div>{critique.claimBoundary}</div>
            <div>{critique.claimImpact}</div>
          </footer>
        </div>
      )}
    </section>
  )
}

interface _SectionProps {
  testid: string
  title: string
  entries: string[]
}

interface _RefusedClaimsSectionProps {
  refusedClaims: string[]
}

function _RefusedClaimsSection({ refusedClaims }: _RefusedClaimsSectionProps) {
  // Phase 13 A — render the suppression history. Only mount when at
  // least one marker is present so a clean envelope doesn't carry
  // panel chrome for an empty section. The marker text is rendered
  // verbatim; the marker is reviewer-readable and contains NO original
  // positive-claim content (per the methodology doc).
  if (refusedClaims.length === 0) return null
  const shown = refusedClaims.slice(0, REFUSED_CLAIMS_MAX_ITEMS)
  const truncated = refusedClaims.length - shown.length
  return (
    <div
      data-testid="advisor-refused-claims"
      style={{
        marginTop: '8px',
        padding: '6px 10px',
        borderRadius: '6px',
        border: '1px solid var(--text-warning, #b8860b)',
        background: 'rgba(184, 134, 11, 0.06)',
      }}
    >
      <div
        data-testid="advisor-refused-claims-header"
        style={{
          fontSize: '0.72rem',
          fontWeight: 600,
          color: 'var(--text-warning, #b8860b)',
        }}
      >
        Refused LLM claims ({refusedClaims.length})
      </div>
      <div
        style={{
          fontSize: '0.62rem',
          color: 'var(--text-secondary)',
          marginBottom: '4px',
        }}
      >
        Advisor content containing a forbidden positive claim outside `not
        &lt;claim&gt;` disclaimer form was filtered out. The marker names
        WHICH token tripped the audit; the original entry text has been
        discarded.
      </div>
      <ul style={{ paddingLeft: '18px', margin: '4px 0', fontSize: '0.7rem' }}>
        {shown.map((marker, idx) => (
          <li
            key={`refused-${idx}`}
            data-testid={`advisor-refused-claims-item-${idx}`}
            style={{ fontFamily: 'monospace' }}
          >
            {marker}
          </li>
        ))}
        {truncated > 0 && (
          <li
            data-testid="advisor-refused-claims-truncated"
            style={{ color: 'var(--text-secondary)' }}
          >
            … {truncated} more refused claim(s) not shown.
          </li>
        )}
      </ul>
    </div>
  )
}

interface _SectionProps {
  testid: string
  title: string
  entries: string[]
}

function _Section({ testid, title, entries }: _SectionProps) {
  return (
    <div data-testid={testid} style={{ marginTop: '8px' }}>
      <div style={{ fontSize: '0.75rem', fontWeight: 600 }}>{title}</div>
      {entries.length === 0 ? (
        <div style={{ fontSize: '0.7rem', color: 'var(--text-secondary)' }}>
          (none surfaced)
        </div>
      ) : (
        <ul style={{ paddingLeft: '18px', margin: '4px 0', fontSize: '0.7rem' }}>
          {entries.map((entry, idx) => {
            const safe = isAdvisorEntrySafe(entry)
            return (
              <li
                key={`${testid}-${idx}`}
                data-testid={`${testid}-item-${idx}`}
                data-safe={safe ? 'true' : 'false'}
                style={{
                  color: safe ? undefined : '#b00020',
                  fontStyle: safe ? undefined : 'italic',
                }}
              >
                {safe
                  ? entry
                  : '[entry suppressed — contains a forbidden positive claim outside `not <claim>` form]'}
              </li>
            )
          })}
        </ul>
      )}
    </div>
  )
}
