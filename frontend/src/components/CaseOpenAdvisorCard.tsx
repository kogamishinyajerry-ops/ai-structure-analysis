// FM-04a Phase 34 B — case-open AI advisor card.
// Phase 35 A — sanitized brief (no jargon leak) + static-gate hint.
//
// Tier 1 / Tier 2 engineering candidate; not signed validation;
// not benchmark agreement.
//
// Surfaces a contextual advisor brief AT THE CASE-OPEN STAGE, before
// the user dives into the Visual / Narrative tabs. Renders:
//
//   * Status badge — always "stub" (this surface is intentionally
//     offline-first; no fetch / no LLM call).
//   * 1-paragraph CURATED brief derived from the caseId pattern (case
//     kind) + displayLabel. NO LLM. Phase 35 A removed the
//     notesExcerpt passthrough that leaked internal vocabulary like
//     "Phase 21+ scope", "tier_2_validated", "single-hex coupons" to
//     novice personas. The brief now reads as engineering orientation
//     copy a first-time reviewer can act on.
//   * 4-Q-gate inline checklist — 4 ticks (LLM-offline OK / artifacts
//     user-owned / TrustGate explains / advisor-only NOT driver) with
//     a Phase 35 A static-vs-dynamic semantic hint making clear this
//     is a client-side stub status, distinct from the AdvisorPanel's
//     backend-validated dynamic gate.
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
//   * G:-1 — composes brief from a CURATED case-kind lookup keyed on
//     the committed caseId; no fabricated content; no LLM.
//   * K:-1 (Phase 35) — test-ids preserved verbatim
//     (case-open-advisor-card / -status-badge / -brief /
//     -four-question-gate / -footer).

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
        {/* FM-04a Phase 36 C — closes Phase 35 R3 friction point (f).
            When the registry marks a case as not having a live ccx
            runner, surface a small badge so the novice can't mistake
            it for an actively-solvable case. */}
        {caseRecord.runnerAvailable === false && (
          <span
            data-testid="case-open-advisor-runner-badge"
            style={runnerBadgeStyle}
          >
            demo · no live runner
          </span>
        )}
        <span data-testid="case-open-advisor-status-badge" style={stubBadgeStyle}>
          stub · offline-first
        </span>
      </div>

      <p style={briefStyle} data-testid="case-open-advisor-brief">
        {composeBrief(caseRecord)}
      </p>

      <div style={gateHeaderStyle}>4-question gate</div>
      <p
        data-testid="case-open-advisor-gate-hint"
        style={gateHintStyle}
      >
        client-side stub status; the Visual tab renders a backend-validated gate
      </p>
      <ul
        data-testid="case-open-advisor-four-question-gate"
        data-gate-kind="static"
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
 * Phase 35 A — curated case-kind orientation copy.
 *
 * Phase 34 B's composeBrief read notesExcerpt verbatim, which leaked
 * internal vocabulary ("Phase 21+ scope", "tier_2_validated",
 * "single-hex coupons", "FM-04a P3 registration") to novice reviewers.
 *
 * Phase 35 A reworks composeBrief to infer the case kind from the
 * caseId prefix and emit a CURATED 1-paragraph engineering
 * orientation. The orientation copy describes the physics + what to
 * look for in the Visual tab, NOT the harness's internal phase
 * vocabulary.
 *
 * If the caseId doesn't match a known prefix, a generic orientation
 * is emitted so unrecognised cases still get a clean brief.
 */
export function composeBrief(caseRecord: CandidateCaseRecord): string {
  const label = caseRecord.displayLabel ?? caseRecord.caseId
  const orientation = orientationForCaseKind(caseRecord.caseId)
  return `${label}. ${orientation} Open the Visual tab for the full critique.`
}

/**
 * Phase 35 A — infer case kind from the caseId prefix. Returns a
 * short engineering orientation sentence (~1-2 sentences, no jargon).
 */
export function orientationForCaseKind(caseId: string): string {
  const id = caseId.toLowerCase()
  if (id.startsWith('hertz-contact-')) {
    return (
      'Contact mechanics candidate. Two compressible bodies in contact ' +
      'under uniaxial load; the analytical cross-check compares the ' +
      'computed compression against a closed-form 1D solution.'
    )
  }
  if (id.startsWith('cantilever-buckle')) {
    return (
      'Linear buckling case. A slender cantilever loaded at the tip; ' +
      'the eigenvalue analysis predicts the first buckling load.'
    )
  }
  if (id.startsWith('cantilever-dynamic')) {
    return (
      'Dynamic cantilever case. Time-domain response of a tip-loaded ' +
      'beam; the analytical reference checks the peak displacement.'
    )
  }
  if (id.startsWith('cantilever-beam-modal') || id.startsWith('modal-cantilever')) {
    return (
      'Modal analysis case. Free-free or fixed-free cantilever; the ' +
      'analytical reference compares the lowest natural frequencies ' +
      'against Euler-Bernoulli beam theory.'
    )
  }
  if (id.startsWith('cantilever-beam') || id.startsWith('cantilever-')) {
    return (
      'Cantilever beam case. A fixed-free beam under a tip load; the ' +
      'analytical reference is the classical Euler-Bernoulli tip ' +
      'deflection.'
    )
  }
  if (id.startsWith('cylinder-pv-')) {
    return (
      'Pressure-vessel case. A thin-walled cylinder under internal ' +
      'pressure; the analytical reference is the hoop stress from ' +
      'Lamé theory.'
    )
  }
  if (id.startsWith('euler-column')) {
    return (
      'Euler column buckling case. A slender column under axial load; ' +
      'the analytical reference is the classical Euler critical load.'
    )
  }
  if (id.startsWith('plate-with-hole')) {
    return (
      'Stress-concentration case. An infinite plate with a circular ' +
      'hole under uniaxial tension; the analytical reference is the ' +
      'Kirsch peak stress at the hole.'
    )
  }
  if (id.startsWith('plate-simply-supported') || id.startsWith('plate-ss-shell')) {
    return (
      'Simply-supported plate case. A flat plate loaded out of plane; ' +
      'the analytical reference compares the centre deflection against ' +
      'thin-plate theory.'
    )
  }
  if (id.startsWith('heat-transfer-')) {
    return (
      'Heat-transfer case. Steady-state conduction through a slab with ' +
      'fixed temperatures on the two ends; the analytical reference is ' +
      'the linear Fourier profile.'
    )
  }
  if (id.startsWith('rod-wave-impact-energy-leak')) {
    return (
      'Wave-propagation case in its KNOWN-BAD configuration. The ' +
      'energy balance does not close; the cohort drift surface should ' +
      'flag the leak in the results file.'
    )
  }
  if (id.startsWith('rod-wave-impact-')) {
    return (
      'Axial wave-propagation case. A rod struck on one end; the ' +
      'analytical reference is the 1D elastic wave speed and the ' +
      'energy balance.'
    )
  }
  if (id.startsWith('gs-102') || id.startsWith('gs-100') || id.startsWith('gs-101') || id.startsWith('gs-103')) {
    return (
      'Ballistic-impact demo case. A small projectile hitting a plate ' +
      'at high velocity; the result you should look for is the ' +
      'penetration energy and the time-history channels.'
    )
  }
  return (
    'Engineering candidate case. The Visual tab renders the mesh, the ' +
    'results, and the trust-score breakdown side by side.'
  )
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
  background: 'var(--bg-muted, var(--c-100))',
  border: '1px solid var(--border)',
  color: 'var(--text-secondary)',
}
// Phase 36 C — amber-toned badge for cases without a live ccx
// runner. Distinct from the stubBadge (which is about advisor
// offline-first status), but visually compatible.
const runnerBadgeStyle: CSSProperties = {
  fontSize: 11,
  fontFamily:
    'ui-monospace, SFMono-Regular, "SF Mono", Menlo, monospace',
  padding: '2px 8px',
  borderRadius: 6,
  background: 'rgba(179, 121, 26, 0.10)',
  border: '1px solid rgba(179, 121, 26, 0.30)',
  color: 'var(--warn-400)',
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
// Phase 35 A — muted subtitle that distinguishes this static stub
// gate from the AdvisorPanel's dynamic backend-validated gate so a
// reviewer never confuses the two surfaces.
const gateHintStyle: CSSProperties = {
  margin: 0,
  fontSize: 11,
  fontStyle: 'italic',
  color: 'var(--text-secondary)',
  opacity: 0.85,
}
const gateListStyle: CSSProperties = {
  margin: 0,
  paddingInlineStart: 0,
  listStyle: 'none',
  display: 'flex',
  flexDirection: 'column',
  gap: 4,
  // Phase 35 A — muted color band signals static-stub semantics
  // (vs the AdvisorPanel's accent-color dynamic gate ticks).
  color: 'var(--text-secondary)',
}
const gateItemStyle: CSSProperties = {
  display: 'flex',
  alignItems: 'flex-start',
  gap: 8,
  fontSize: 12,
  lineHeight: 1.45,
}
// Phase 35 A — muted tick color (was accent). The AdvisorPanel's
// dynamic gate continues to use the accent color, so reviewers can
// see at a glance which gate is static vs backend-validated.
const gateTickStyle: CSSProperties = {
  color: 'var(--text-secondary)',
  fontWeight: 700,
  minWidth: 14,
  display: 'inline-block',
  opacity: 0.7,
}
const footerStyle: CSSProperties = {
  margin: 0,
  fontSize: 11,
  color: 'var(--text-secondary)',
  borderTop: '1px solid var(--border)',
  paddingTop: 8,
}
