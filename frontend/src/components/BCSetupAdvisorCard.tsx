// FM-04a Phase 37 B — BC-setup AI advisor card.
//
// Tier 1 / Tier 2 engineering candidate; not signed validation;
// not benchmark agreement.
//
// **3rd advisor surface** in the workbench (after Phase 11
// AdvisorPanel at the Review stage + Phase 34 B CaseOpenAdvisorCard
// at the Case-open stage). Per RUBRIC_v2.md Dim 4 (AI workflow
// integration), this closes the 80-anchor sub-bullet "advisor at
// 3 workflow stages (case-open + setup + review)".
//
// Surfaces a contextual orientation AT THE BC-SETUP STAGE when a
// case is open but no BCs have been assigned yet. Renders:
//
//   * Status badge — "stub · offline-first" (same as case-open
//     surface; intentionally offline-first; no fetch / no LLM call).
//   * 1-paragraph CURATED BC orientation derived from the caseId
//     pattern (so the advisor reads as engineering BC copy a
//     first-time reviewer can act on, NOT internal phase vocab).
//   * 4-Q-gate inline checklist with the SAME static-gate-hint
//     subtitle pattern Phase 35 A introduced — semantic consistency
//     across the 2 stub advisor surfaces.
//
// Anti-gaming guards:
//   R:-1 (NEW Phase 37) — follows the Phase 34 B + 35 A envelope
//     verbatim: offline-first stub, curated copy from caseId
//     pattern, static 4-Q gate with the gate-hint subtitle for
//     visual consistency with CaseOpenAdvisorCard. No LLM call.
//     No fetch. Mount conditionally only when a case is open AND
//     BC state is unset.
//   I:-1 (Phase 34 carry) — does NOT degrade Phase 11 AdvisorPanel
//     or Phase 34 B CaseOpenAdvisorCard. Coexists.
//   D:-1 (rubric v2.0 carry) — 4-Q gate visible at this surface.
//   G:-1 (rubric v2.0 carry) — orientation copy is derived from
//     the physics + BC-conventions of each case kind; no
//     fabricated content; no LLM.

import type { CSSProperties } from 'react'
import { FOUR_QUESTION_GATE_KEYS } from '../advisorCritiqueClient'
import type { CandidateCaseRecord } from '../candidateCaseRegistry'
import { TIER1_BANNER } from '../trustCenterSummary'

export interface BCSetupAdvisorCardProps {
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

export function BCSetupAdvisorCard({ caseRecord }: BCSetupAdvisorCardProps) {
  return (
    <div
      data-testid="bc-setup-advisor-card"
      role="region"
      aria-label="BC-setup AI advisor"
      style={cardStyle}
    >
      <div style={headerStyle}>
        <strong style={titleStyle}>BC-setup advisor</strong>
        <span data-testid="bc-setup-advisor-status-badge" style={stubBadgeStyle}>
          stub · offline-first
        </span>
      </div>

      <p style={briefStyle} data-testid="bc-setup-advisor-brief">
        {composeBCBrief(caseRecord)}
      </p>

      <div style={gateHeaderStyle}>4-question gate</div>
      <p
        data-testid="bc-setup-advisor-gate-hint"
        style={gateHintStyle}
      >
        client-side stub status; the Visual tab renders a backend-validated gate
      </p>
      <ul
        data-testid="bc-setup-advisor-four-question-gate"
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

      <p style={footerStyle} data-testid="bc-setup-advisor-footer">
        {TIER1_BANNER} · advisor-only; the next stage (Visual tab)
        renders a deeper LLM-backed critique once the solve completes.
      </p>
    </div>
  )
}

/** Phase 37 B — curated BC-setup orientation copy keyed on caseId
 * prefix. Same lookup pattern as Phase 35 A `orientationForCaseKind`,
 * but the copy describes the EXPECTED BCs (what a reviewer would
 * set), not the analytical reference. */
export function composeBCBrief(caseRecord: CandidateCaseRecord): string {
  const label = caseRecord.displayLabel ?? caseRecord.caseId
  const orientation = bcOrientationForCaseKind(caseRecord.caseId)
  return `${label}. ${orientation} These BCs are fixed by the case definition (read-only — no setup step here); run the solver and the Visual tab renders the resulting field once the job completes.`
}

/** Phase 37 B — infer expected-BC orientation from caseId prefix.
 * Returns a short BC-conventions sentence (~1-2 sentences, no
 * internal jargon). */
export function bcOrientationForCaseKind(caseId: string): string {
  const id = caseId.toLowerCase()
  if (id.startsWith('hertz-contact-')) {
    return (
      'Expected BCs: top-face compression load on the punch + ' +
      'fixed-displacement on the substrate bottom face + a ' +
      'contact-pair between the two interfacing faces.'
    )
  }
  if (id.startsWith('cantilever-buckle')) {
    return (
      'Expected BCs: fixed end at one tip + axial reference load at ' +
      'the free tip + an eigenvalue step requesting the first mode.'
    )
  }
  if (id.startsWith('cantilever-dynamic')) {
    return (
      'Expected BCs: fixed end at one tip + a time-varying impulse ' +
      'load at the free tip + a dynamic explicit / implicit step.'
    )
  }
  if (id.startsWith('cantilever-beam-modal') || id.startsWith('modal-cantilever')) {
    return (
      'Expected BCs: fixed end at one tip; a modal step requests ' +
      'the lowest n natural frequencies (no applied load needed).'
    )
  }
  if (id.startsWith('cantilever-')) {
    return (
      'Expected BCs: fixed end at one tip + a point load at the ' +
      'free tip + a linear static step.'
    )
  }
  if (id.startsWith('cylinder-pv-')) {
    return (
      'Expected BCs: internal-pressure load on the inner wall + ' +
      'axial constraint on one end face to remove rigid-body ' +
      'translation + a linear static step.'
    )
  }
  if (id.startsWith('euler-column')) {
    return (
      'Expected BCs: pinned-pinned end conditions + axial reference ' +
      'load at one tip + an eigenvalue step requesting the first ' +
      'buckling mode.'
    )
  }
  if (id.startsWith('plate-with-hole')) {
    return (
      'Expected BCs: in-plane tension on two opposite edges + an ' +
      'in-plane fixed reference on the perpendicular edges + a ' +
      'linear static step.'
    )
  }
  if (id.startsWith('plate-simply-supported') || id.startsWith('plate-ss-shell')) {
    return (
      'Expected BCs: simply-supported edges on all four sides + a ' +
      'uniform pressure load on the top face + a linear static step.'
    )
  }
  if (id.startsWith('heat-transfer-')) {
    return (
      'Expected BCs: a fixed temperature on each of two opposite ' +
      'faces (typically a hot face + a cold face) + a steady-state ' +
      'heat-transfer step.'
    )
  }
  if (id.startsWith('rod-wave-impact-energy-leak')) {
    return (
      'Expected BCs: free-free rod with a velocity initial condition ' +
      'at one end (the impactor) + an explicit dynamic step. The ' +
      'energy balance does not close in this known-bad configuration.'
    )
  }
  if (id.startsWith('rod-wave-impact-')) {
    return (
      'Expected BCs: free-free rod with a velocity initial condition ' +
      'at one end (the impactor) + an explicit dynamic step.'
    )
  }
  if (id.startsWith('gs-1')) {
    return (
      'Expected BCs: a small projectile with a prescribed initial ' +
      'velocity + a plate clamped on its periphery + an explicit ' +
      'dynamic step.'
    )
  }
  return (
    'Open the Visual tab once BCs are wired to inspect the resulting ' +
    'field — the workbench does not enforce a fixed BC template here.'
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
  color: 'var(--text-secondary)',
}
const gateItemStyle: CSSProperties = {
  display: 'flex',
  alignItems: 'flex-start',
  gap: 8,
  fontSize: 12,
  lineHeight: 1.45,
}
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
