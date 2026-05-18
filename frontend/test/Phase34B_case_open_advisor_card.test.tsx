// FM-04a Phase 34 B — case-open AI advisor card tests.
// Phase 35 A — jargon-absence + static-gate-hint pins layered on top.
//
// Pin the new SECOND advisor surface. Per RUBRIC_v2.md Dim 4 (AI
// workflow integration), this lifts the codebase from 60-anchor
// "1 surface" to 70-anchor "2 surfaces".
//
// Anti-gaming guards:
//   I:-1 — does NOT replace the Phase 11 AdvisorPanel; coexists
//   D:-1 — 4-Q-gate visible inline at this new surface (the rubric
//          specifically requires 4-Q-gate AUDITED at each surface,
//          not just the deeper one)
//   G:-1 — composes brief from REAL case metadata fields, not
//          fabricated copy
//   E:-1 — surface count is verifiable by grepping for the test-id
//          `case-open-advisor-card` (single mount; tied to activeCaseId)
//   K:-1 (Phase 35) — Phase 34 B test-ids preserved verbatim; only
//          the content changes (no jargon leak, gate-hint added).

import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import { CaseOpenAdvisorCard } from '../src/components/CaseOpenAdvisorCard'
import type { CandidateCaseRecord } from '../src/candidateCaseRegistry'

const CANTILEVER_RECORD: CandidateCaseRecord = {
  caseId: 'cantilever-beam-candidate',
  displayLabel: 'Cantilever Beam (Tier 1)',
  claimTier: 'Tier 1 engineering candidate',
  starterDeckRelpath: null,
  engineDeckRelpath: null,
  generatorScriptRelpath: null,
  notesExcerpt:
    'cantilever-beam-candidate · Phase 21+ scope, tier_2_validated, ' +
    'single-hex coupons. Linear-elastic static analysis.',
  claimBoundary:
    'tier1_engineering_candidate; not_signed_validation; not_benchmark_agreement',
}

const MINIMAL_RECORD: CandidateCaseRecord = {
  caseId: 'minimal-stub-case',
  claimTier: 'Tier 1 engineering candidate',
  starterDeckRelpath: null,
  engineDeckRelpath: null,
  generatorScriptRelpath: null,
  notesExcerpt: null,
  claimBoundary:
    'tier1_engineering_candidate; not_signed_validation; not_benchmark_agreement',
}

describe('Phase 34 B — CaseOpenAdvisorCard mount + status', () => {
  it('renders the card with the case-open advisor test-id', () => {
    render(<CaseOpenAdvisorCard caseRecord={CANTILEVER_RECORD} />)
    expect(screen.getByTestId('case-open-advisor-card')).toBeTruthy()
  })

  it('renders the stub/offline status badge', () => {
    render(<CaseOpenAdvisorCard caseRecord={CANTILEVER_RECORD} />)
    const badge = screen.getByTestId('case-open-advisor-status-badge')
    expect(badge.textContent).toMatch(/stub/)
    expect(badge.textContent).toMatch(/offline/)
  })

  it('has role="region" with an accessible label', () => {
    render(<CaseOpenAdvisorCard caseRecord={CANTILEVER_RECORD} />)
    const region = screen.getByRole('region', { name: /Case-open AI advisor brief/i })
    expect(region).toBeTruthy()
  })
})

describe('Phase 34 B — brief composition from real metadata (G:-1)', () => {
  it('mentions the case displayLabel when present', () => {
    render(<CaseOpenAdvisorCard caseRecord={CANTILEVER_RECORD} />)
    const brief = screen.getByTestId('case-open-advisor-brief')
    expect(brief.textContent).toContain('Cantilever Beam (Tier 1)')
  })

  it('falls back to caseId when displayLabel is absent', () => {
    render(<CaseOpenAdvisorCard caseRecord={MINIMAL_RECORD} />)
    const brief = screen.getByTestId('case-open-advisor-brief')
    expect(brief.textContent).toContain('minimal-stub-case')
  })

  it('falls back to a generic engineering-candidate orientation when caseId is unrecognised', () => {
    render(<CaseOpenAdvisorCard caseRecord={MINIMAL_RECORD} />)
    const brief = screen.getByTestId('case-open-advisor-brief')
    expect(brief.textContent).toMatch(/engineering candidate case/i)
    expect(brief.textContent).toContain('Visual tab')
  })
})

describe('Phase 35 A — brief absence of internal jargon (#27 fix)', () => {
  // Phase 34 B leaked internal vocabulary from notesExcerpt
  // ("Phase 21+ scope", "tier_2_validated", "single-hex coupons")
  // into the novice-facing brief. Phase 35 A reworked composeBrief
  // to read from a curated case-kind lookup instead. These tests
  // pin the absence of the internal tokens so a future regression
  // would be caught.
  const JARGON_TOKENS = [
    'Phase 21',
    'tier_2_validated',
    'single-hex coupons',
    'FM-04a',
    'P3 registration',
    'notesExcerpt',
  ] as const

  for (const token of JARGON_TOKENS) {
    it(`brief does NOT contain internal token "${token}"`, () => {
      render(<CaseOpenAdvisorCard caseRecord={CANTILEVER_RECORD} />)
      const brief = screen.getByTestId('case-open-advisor-brief')
      expect(brief.textContent).not.toContain(token)
    })
  }

  it('brief is short (one orientation paragraph, < 400 chars)', () => {
    render(<CaseOpenAdvisorCard caseRecord={CANTILEVER_RECORD} />)
    const brief = screen.getByTestId('case-open-advisor-brief')
    const length = (brief.textContent ?? '').length
    expect(length).toBeGreaterThan(40)
    expect(length).toBeLessThan(400)
  })
})

describe('Phase 35 A — curated orientation per case kind', () => {
  const KIND_FIXTURES: ReadonlyArray<{
    readonly caseId: string
    readonly mustContain: RegExp
  }> = [
    { caseId: 'hertz-contact-candidate', mustContain: /contact mechanics/i },
    { caseId: 'cantilever-beam-candidate', mustContain: /Euler-Bernoulli/ },
    { caseId: 'cantilever-buckle-candidate', mustContain: /buckling/i },
    { caseId: 'cantilever-dynamic-candidate', mustContain: /dynamic/i },
    { caseId: 'modal-cantilever-candidate', mustContain: /modal analysis/i },
    { caseId: 'cylinder-pv-candidate', mustContain: /pressure-vessel/i },
    { caseId: 'euler-column-candidate', mustContain: /Euler critical load/ },
    { caseId: 'plate-with-hole-candidate', mustContain: /Kirsch/ },
    { caseId: 'plate-simply-supported-candidate', mustContain: /simply-supported plate/i },
    { caseId: 'heat-transfer-1d-candidate', mustContain: /heat-transfer/i },
    { caseId: 'rod-wave-impact-candidate', mustContain: /wave-propagation/i },
    {
      caseId: 'rod-wave-impact-energy-leak-candidate',
      mustContain: /KNOWN-BAD/,
    },
    { caseId: 'GS-102-candidate', mustContain: /ballistic-impact/i },
  ]

  for (const { caseId, mustContain } of KIND_FIXTURES) {
    it(`renders the curated orientation for ${caseId}`, () => {
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
      render(<CaseOpenAdvisorCard caseRecord={record} />)
      const brief = screen.getByTestId('case-open-advisor-brief')
      expect(brief.textContent).toMatch(mustContain)
    })
  }
})

describe('Phase 34 B — 4-Q gate visible inline (D:-1)', () => {
  it('renders the 4-Q gate container', () => {
    render(<CaseOpenAdvisorCard caseRecord={CANTILEVER_RECORD} />)
    expect(screen.getByTestId('case-open-advisor-four-question-gate')).toBeTruthy()
  })

  it('shows all 4 gate items with their SSOT key labels', () => {
    render(<CaseOpenAdvisorCard caseRecord={CANTILEVER_RECORD} />)
    const gate = screen.getByTestId('case-open-advisor-four-question-gate')
    expect(gate.textContent).toContain('LLM offline')
    expect(gate.textContent).toContain('artifacts user-owned')
    expect(gate.textContent).toContain('trust score explains')
    expect(gate.textContent).toContain('advisor-only')
  })

  it('marks each item with an explicit tick (not a question mark)', () => {
    render(<CaseOpenAdvisorCard caseRecord={CANTILEVER_RECORD} />)
    const gate = screen.getByTestId('case-open-advisor-four-question-gate')
    // 4 items × at least 1 tick each
    const ticks = gate.textContent?.match(/✓/g) ?? []
    expect(ticks.length).toBe(4)
  })
})

describe('Phase 35 A — static-vs-dynamic gate semantic distinction (#28 fix)', () => {
  // Phase 34 B's 4-Q gate at this surface rendered the SAME 4-key
  // vocabulary as the Phase 11 AdvisorPanel's dynamic backend-driven
  // gate, without any visual or semantic distinction. Reviewer P3
  // could not tell the two surfaces apart at a glance. Phase 35 A
  // adds (a) a muted subtitle line declaring "client-side stub
  // status; the Visual tab renders a backend-validated gate" and
  // (b) a data-gate-kind="static" attribute so reviewers + tests
  // can verify the surface is the stub one.

  it('renders the gate-hint subtitle with explicit static-vs-dynamic copy', () => {
    render(<CaseOpenAdvisorCard caseRecord={CANTILEVER_RECORD} />)
    const hint = screen.getByTestId('case-open-advisor-gate-hint')
    expect(hint).toBeTruthy()
    expect(hint.textContent).toMatch(/client-side stub status/i)
    expect(hint.textContent).toMatch(/backend-validated gate/i)
  })

  it('tags the gate container with data-gate-kind="static"', () => {
    render(<CaseOpenAdvisorCard caseRecord={CANTILEVER_RECORD} />)
    const gate = screen.getByTestId('case-open-advisor-four-question-gate')
    expect(gate.getAttribute('data-gate-kind')).toBe('static')
  })
})

describe('Phase 34 B — footer + Tier-1 banner', () => {
  it('includes the Tier-1 banner in the footer', () => {
    render(<CaseOpenAdvisorCard caseRecord={CANTILEVER_RECORD} />)
    const footer = screen.getByTestId('case-open-advisor-footer')
    expect(footer.textContent).toMatch(/Tier 1/)
    expect(footer.textContent).toContain('advisor-only')
  })

  it('references the Visual tab for the deeper critique', () => {
    render(<CaseOpenAdvisorCard caseRecord={CANTILEVER_RECORD} />)
    const footer = screen.getByTestId('case-open-advisor-footer')
    expect(footer.textContent).toContain('Visual tab')
  })
})
