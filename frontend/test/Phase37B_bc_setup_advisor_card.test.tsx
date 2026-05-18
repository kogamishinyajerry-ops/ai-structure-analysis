// FM-04a Phase 37 B — BCSetupAdvisorCard tests.
//
// Pin the 3rd advisor surface (after Phase 11 AdvisorPanel + Phase
// 34 B CaseOpenAdvisorCard). Per RUBRIC_v2.md Dim 4 (AI workflow
// integration), this closes the 80-anchor sub-bullet "advisor at 3
// workflow stages (case-open + setup + review)".
//
// Anti-gaming guards:
//   R:-1 (NEW Phase 37) — follows the Phase 34 B + 35 A envelope
//     verbatim: offline-first stub, curated copy from caseId
//     pattern, static 4-Q gate with gate-hint subtitle for visual
//     consistency with CaseOpenAdvisorCard. No LLM call. No fetch.
//   I:-1 (Phase 34 carry) — does NOT modify Phase 11 AdvisorPanel
//     or Phase 34 B CaseOpenAdvisorCard.
//   D:-1 — 4-Q gate visible at this surface.

import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import { BCSetupAdvisorCard } from '../src/components/BCSetupAdvisorCard'
import {
  bcOrientationForCaseKind,
  composeBCBrief,
} from '../src/components/BCSetupAdvisorCard'
import type { CandidateCaseRecord } from '../src/candidateCaseRegistry'

const CANTILEVER_RECORD: CandidateCaseRecord = {
  caseId: 'cantilever-beam-candidate',
  displayLabel: 'Cantilever Beam',
  claimTier: 'Tier 1 engineering candidate',
  starterDeckRelpath: null,
  engineDeckRelpath: null,
  generatorScriptRelpath: null,
  notesExcerpt: null,
  claimBoundary:
    'tier1_engineering_candidate; not_signed_validation; not_benchmark_agreement',
}

const MINIMAL_RECORD: CandidateCaseRecord = {
  caseId: 'mystery-case-without-prefix',
  claimTier: 'Tier 1 engineering candidate',
  starterDeckRelpath: null,
  engineDeckRelpath: null,
  generatorScriptRelpath: null,
  notesExcerpt: null,
  claimBoundary:
    'tier1_engineering_candidate; not_signed_validation; not_benchmark_agreement',
}

describe('Phase 37 B — BCSetupAdvisorCard mount + status', () => {
  it('renders the card with the bc-setup-advisor test-id', () => {
    render(<BCSetupAdvisorCard caseRecord={CANTILEVER_RECORD} />)
    expect(screen.getByTestId('bc-setup-advisor-card')).toBeTruthy()
  })

  it('renders the stub/offline status badge', () => {
    render(<BCSetupAdvisorCard caseRecord={CANTILEVER_RECORD} />)
    const badge = screen.getByTestId('bc-setup-advisor-status-badge')
    expect(badge.textContent).toMatch(/stub/)
    expect(badge.textContent).toMatch(/offline/)
  })

  it('has role="region" with an accessible label', () => {
    render(<BCSetupAdvisorCard caseRecord={CANTILEVER_RECORD} />)
    expect(
      screen.getByRole('region', { name: /BC-setup AI advisor/i }),
    ).toBeTruthy()
  })
})

describe('Phase 37 B — brief composition (G:-1, R:-1)', () => {
  it('mentions the case displayLabel when present', () => {
    render(<BCSetupAdvisorCard caseRecord={CANTILEVER_RECORD} />)
    const brief = screen.getByTestId('bc-setup-advisor-brief')
    expect(brief.textContent).toContain('Cantilever Beam')
  })

  it('falls back to caseId when displayLabel is absent', () => {
    render(<BCSetupAdvisorCard caseRecord={MINIMAL_RECORD} />)
    const brief = screen.getByTestId('bc-setup-advisor-brief')
    expect(brief.textContent).toContain('mystery-case-without-prefix')
  })

  it('does NOT contain internal phase vocabulary tokens', () => {
    const JARGON = ['Phase 21', 'tier_2_validated', 'single-hex coupons', 'FM-04a']
    render(<BCSetupAdvisorCard caseRecord={CANTILEVER_RECORD} />)
    const brief = screen.getByTestId('bc-setup-advisor-brief')
    for (const token of JARGON) {
      expect(brief.textContent).not.toContain(token)
    }
  })

  it('renders an engineering BC orientation, not raw notesExcerpt', () => {
    render(<BCSetupAdvisorCard caseRecord={CANTILEVER_RECORD} />)
    const brief = screen.getByTestId('bc-setup-advisor-brief')
    // Cantilever BC orientation mentions fixed end + point load
    expect(brief.textContent).toMatch(/fixed end/i)
    expect(brief.textContent).toMatch(/point load/i)
  })
})

describe('Phase 37 B — BC orientation per case kind', () => {
  const KIND_FIXTURES: ReadonlyArray<{
    readonly caseId: string
    readonly mustContain: RegExp
  }> = [
    { caseId: 'hertz-contact-candidate', mustContain: /contact-pair/i },
    { caseId: 'cantilever-buckle-candidate', mustContain: /eigenvalue/i },
    { caseId: 'cantilever-dynamic-candidate', mustContain: /impulse/i },
    { caseId: 'cantilever-beam-modal-candidate', mustContain: /modal step/i },
    { caseId: 'cantilever-beam-candidate', mustContain: /point load/i },
    { caseId: 'cylinder-pv-candidate', mustContain: /internal-pressure/i },
    { caseId: 'euler-column-candidate', mustContain: /pinned-pinned/i },
    { caseId: 'plate-with-hole-candidate', mustContain: /in-plane tension/i },
    { caseId: 'plate-simply-supported-candidate', mustContain: /simply-supported edges/i },
    { caseId: 'heat-transfer-1d-candidate', mustContain: /fixed temperature/i },
    {
      caseId: 'rod-wave-impact-energy-leak-candidate',
      mustContain: /known-bad/i,
    },
    { caseId: 'rod-wave-impact-candidate', mustContain: /velocity initial condition/i },
    { caseId: 'GS-102-candidate', mustContain: /projectile/i },
  ]

  for (const { caseId, mustContain } of KIND_FIXTURES) {
    it(`renders the BC orientation for ${caseId}`, () => {
      const record: CandidateCaseRecord = {
        caseId,
        claimTier: 'Tier 1 engineering candidate',
        starterDeckRelpath: null,
        engineDeckRelpath: null,
        generatorScriptRelpath: null,
        notesExcerpt: null,
        claimBoundary:
          'tier1_engineering_candidate; not_signed_validation; not_benchmark_agreement',
      }
      render(<BCSetupAdvisorCard caseRecord={record} />)
      const brief = screen.getByTestId('bc-setup-advisor-brief')
      expect(brief.textContent).toMatch(mustContain)
    })
  }
})

describe('Phase 37 B — 4-Q gate visible inline (D:-1)', () => {
  it('renders the 4-Q gate container with data-gate-kind="static"', () => {
    render(<BCSetupAdvisorCard caseRecord={CANTILEVER_RECORD} />)
    const gate = screen.getByTestId('bc-setup-advisor-four-question-gate')
    expect(gate).toBeTruthy()
    expect(gate.getAttribute('data-gate-kind')).toBe('static')
  })

  it('renders the static-vs-dynamic gate hint subtitle', () => {
    render(<BCSetupAdvisorCard caseRecord={CANTILEVER_RECORD} />)
    const hint = screen.getByTestId('bc-setup-advisor-gate-hint')
    expect(hint.textContent).toMatch(/client-side stub status/i)
    expect(hint.textContent).toMatch(/backend-validated gate/i)
  })

  it('shows all 4 gate items with their SSOT key labels', () => {
    render(<BCSetupAdvisorCard caseRecord={CANTILEVER_RECORD} />)
    const gate = screen.getByTestId('bc-setup-advisor-four-question-gate')
    expect(gate.textContent).toContain('LLM offline')
    expect(gate.textContent).toContain('artifacts user-owned')
    expect(gate.textContent).toContain('trust score explains')
    expect(gate.textContent).toContain('advisor-only')
  })

  it('marks each item with an explicit tick (not a question mark)', () => {
    render(<BCSetupAdvisorCard caseRecord={CANTILEVER_RECORD} />)
    const gate = screen.getByTestId('bc-setup-advisor-four-question-gate')
    const ticks = gate.textContent?.match(/✓/g) ?? []
    expect(ticks.length).toBe(4)
  })
})

describe('Phase 37 B — footer + Tier-1 banner', () => {
  it('includes the Tier-1 banner in the footer', () => {
    render(<BCSetupAdvisorCard caseRecord={CANTILEVER_RECORD} />)
    const footer = screen.getByTestId('bc-setup-advisor-footer')
    expect(footer.textContent).toMatch(/Tier 1/)
    expect(footer.textContent).toContain('advisor-only')
  })

  it('references the Visual tab for the deeper critique', () => {
    render(<BCSetupAdvisorCard caseRecord={CANTILEVER_RECORD} />)
    const footer = screen.getByTestId('bc-setup-advisor-footer')
    expect(footer.textContent).toContain('Visual tab')
  })
})

describe('Phase 37 B — pure helpers', () => {
  it('composeBCBrief returns label + orientation + Visual-tab cue', () => {
    const brief = composeBCBrief(CANTILEVER_RECORD)
    expect(brief).toContain('Cantilever Beam')
    expect(brief).toMatch(/Visual tab/i)
    expect(brief).toMatch(/Set the BCs/i)
  })

  it('bcOrientationForCaseKind returns generic copy for unknown prefix', () => {
    const result = bcOrientationForCaseKind('totally-unknown-case')
    expect(result).toMatch(/Visual tab/i)
    expect(result).toMatch(/does not enforce a fixed BC template/i)
  })
})
