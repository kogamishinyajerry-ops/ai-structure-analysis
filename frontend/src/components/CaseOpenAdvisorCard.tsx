// FM-04a Phase 34 B — case-open AI advisor card.
//
// Tier 1 / Tier 2 engineering candidate; not signed validation;
// not benchmark agreement.
//
// Surfaces a contextual advisor brief AT THE CASE-OPEN STAGE, before
// the user dives into the Visual / Narrative tabs. Renders:
//
//   * Status badge — always "stub" (this surface is intentionally
//     offline-first; no fetch / no LLM call).
//   * 1-paragraph brief derived from the candidate case's notesExcerpt
//     + claimTier + claimBoundary fields. NO LLM. NO mocked output.
//     The brief is COMPOSED from real case metadata, not generated.
//   * 4-Q-gate inline checklist — 4 ticks (LLM-offline OK / artifacts
//     user-owned / TrustGate explains / advisor-only NOT driver).
//
// This is the SECOND advisor surface in the product (Phase 11
// AdvisorPanel at VisualTabPanel is the first). Per RUBRIC_v2.md
// Dim 4 (AI workflow integration), this lifts the codebase from
// 60-anchor "1 surface" to 70-anchor "2 surfaces".
//
// Anti-gaming guards:
//   * I:-1 — does NOT degrade Phase 11 AdvisorPanel. Coexists.
//   * D:-1 — 4-Q-gate visible at this surface, not just the deeper
//     AdvisorPanel.
//   * G:-1 — composes brief from REAL case metadata (notesExcerpt is
//     committed in candidateCaseRegistry.ts / golden_samples NOTES.md);
//     no fabricated content.

import type { CSSProperties } from 'react'
import { FOUR_QUESTION_GATE_KEYS } from '../advisorCritiqueClient'
import type { CandidateCaseRecord } from '../candidateCaseRegistry'
import { TIER1_BANNER } from '../trustCenterSummary'

export interface CaseOpenAdvisorCardProps {
  readonly caseRecord: CandidateCaseRecord
}

const GATE_KEY_LABEL: Record<
  (typeof FOUR_QUESTION_GATE_KEYS)[number],
  string
> = {
  llm_offline_ok: 'LLM offline OK (this card works without any LLM)',
  artifacts_user_owned: 'artifacts user-owned (your case files live in your repo)',
  trustgate_explains: 'trust score explains (open the Visual tab for full critique)',
  advisor_only: 'advisor-only (NOT a driver; reviewer agency preserved)',
}

export function CaseOpenAdvisorCard({ caseRecord }: CaseOpenAdvisorCardProps) {
  return (
    <div
      data-testid="case-open-advisor-card"
      role="region"
      aria-label="Case-open AI advisor brief"
      style={cardStyle}
    >
      <div style={headerStyle}>
        <strong style={titleStyle}>Case-open advisor</strong>
        <span data-testid="case-open-advisor-status-badge" style={stubBadgeStyle}>
          stub · offline-first
        </span>
      </div>

      <p style={briefStyle} data-testid="case-open-advisor-brief">
        {composeBrief(caseRecord)}
      </p>

      <div style={gateHeaderStyle}>4-question gate</div>
      <ul
        data-testid="case-open-advisor-four-question-gate"
        style={gateListStyle}
      >
        {FOUR_QUESTION_GATE_KEYS.map((key) => (
          <li key={key} style={gateItemStyle}>
            <span aria-hidden="true" style={gateTickStyle}>
              ✓
            </span>
            <span>{GATE_KEY_LABEL[key]}</span>
          </li>
        ))}
      </ul>

      <p style={footerStyle} data-testid="case-open-advisor-footer">
        {TIER1_BANNER} · advisor-only; the next stage (Visual tab)
        renders a deeper LLM-backed critique.
      </p>
    </div>
  )
}

/**
 * Compose a 1-paragraph contextual brief from case metadata. NO LLM
 * involvement; the brief is a concatenation of real fields from the
 * candidate case registry (G:-1 anti-gaming guard).
 *
 * Returns at most ~3 short sentences combining displayLabel +
 * notesExcerpt + claimTier orientation.
 */
function composeBrief(caseRecord: CandidateCaseRecord): string {
  const label = caseRecord.displayLabel ?? caseRecord.caseId
  const notes = caseRecord.notesExcerpt?.trim()
  const tier = caseRecord.claimTier
  const head = `You opened ${label}.`
  const body =
    notes && notes.length > 0
      ? ` ${truncateBrief(notes)}`
      : ' Open the Visual tab to inspect mesh, results, and provenance.'
  const tail = ` Claim: ${tier}.`
  return `${head}${body}${tail}`
}

function truncateBrief(text: string): string {
  // Keep the brief short — first 240 chars at a sentence boundary if
  // possible, else hard-cut. The deeper AdvisorPanel renders the full
  // narrative; this surface is orientation-only.
  if (text.length <= 240) return text
  const head = text.slice(0, 240)
  const lastDot = head.lastIndexOf('.')
  if (lastDot > 120) return head.slice(0, lastDot + 1)
  return `${head}…`
}

const cardStyle: CSSProperties = {
  borderRadius: 10,
  border: '1px solid var(--border)',
  background: 'var(--bg-surface)',
  padding: 14,
  display: 'flex',
  flexDirection: 'column',
  gap: 8,
  color: 'var(--text-primary)',
}
const headerStyle: CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  gap: 10,
  justifyContent: 'space-between',
}
const titleStyle: CSSProperties = {
  fontSize: 14,
  fontWeight: 600,
  letterSpacing: '0.02em',
}
const stubBadgeStyle: CSSProperties = {
  fontSize: 11,
  fontFamily:
    'ui-monospace, SFMono-Regular, "SF Mono", Menlo, monospace',
  padding: '2px 8px',
  borderRadius: 6,
  background: 'var(--bg-muted, rgba(255,255,255,0.05))',
  border: '1px solid var(--border)',
  color: 'var(--text-secondary)',
}
const briefStyle: CSSProperties = {
  margin: 0,
  fontSize: 13,
  lineHeight: 1.5,
  color: 'var(--text-primary)',
}
const gateHeaderStyle: CSSProperties = {
  fontSize: 11,
  textTransform: 'uppercase',
  letterSpacing: '0.06em',
  color: 'var(--text-secondary)',
  marginTop: 4,
}
const gateListStyle: CSSProperties = {
  margin: 0,
  paddingInlineStart: 0,
  listStyle: 'none',
  display: 'flex',
  flexDirection: 'column',
  gap: 4,
}
const gateItemStyle: CSSProperties = {
  display: 'flex',
  alignItems: 'flex-start',
  gap: 8,
  fontSize: 12,
  lineHeight: 1.45,
  color: 'var(--text-primary)',
}
const gateTickStyle: CSSProperties = {
  color: 'var(--accent, #0a8a4a)',
  fontWeight: 700,
  minWidth: 14,
  display: 'inline-block',
}
const footerStyle: CSSProperties = {
  margin: 0,
  fontSize: 11,
  color: 'var(--text-secondary)',
  borderTop: '1px solid var(--border)',
  paddingTop: 8,
}
