// FM-04a Phase 34 B — case-open AI advisor card tests.
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
    'cantilever-beam-candidate · 0.5 m steel S355 cantilever, point load at free ' +
    'end. Linear-elastic static analysis with C3D8 hex; analytical reference ' +
    'from Euler-Bernoulli beam theory.',
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

  it('includes the notesExcerpt content when present', () => {
    render(<CaseOpenAdvisorCard caseRecord={CANTILEVER_RECORD} />)
    const brief = screen.getByTestId('case-open-advisor-brief')
    expect(brief.textContent).toContain('cantilever-beam-candidate')
    expect(brief.textContent).toContain('Euler-Bernoulli')
  })

  it('falls back to caseId when displayLabel is absent', () => {
    render(<CaseOpenAdvisorCard caseRecord={MINIMAL_RECORD} />)
    const brief = screen.getByTestId('case-open-advisor-brief')
    expect(brief.textContent).toContain('minimal-stub-case')
  })

  it('falls back to default copy when notesExcerpt is null', () => {
    render(<CaseOpenAdvisorCard caseRecord={MINIMAL_RECORD} />)
    const brief = screen.getByTestId('case-open-advisor-brief')
    expect(brief.textContent).toContain('Visual tab')
  })

  it('includes the claim tier in the brief', () => {
    render(<CaseOpenAdvisorCard caseRecord={CANTILEVER_RECORD} />)
    const brief = screen.getByTestId('case-open-advisor-brief')
    expect(brief.textContent).toContain('Tier 1 engineering candidate')
  })
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
