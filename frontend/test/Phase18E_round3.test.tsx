// FM-04a Phase 18 E (round 3) — UI primitive adoption + leak-case
// fallback + display-label tests.
//
// Tier 1 / Tier 2 engineering candidate; not signed validation; not
// benchmark agreement.

import { describe, expect, it, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { AdvisorPanel } from '../src/components/AdvisorPanel'
import {
  FALLBACK_CANDIDATE_CASES,
  findCandidateCase,
} from '../src/candidateCaseRegistry'

describe('candidateCaseRegistry round-3 surface', () => {
  it('FALLBACK_CANDIDATE_CASES includes the leak case', () => {
    const leak = findCandidateCase(
      FALLBACK_CANDIDATE_CASES,
      'rod-wave-impact-energy-leak-candidate',
    )
    expect(leak).not.toBeNull()
    expect(leak!.displayLabel).toMatch(/ENERGY LEAK/i)
  })

  it('every fallback case carries a human displayLabel', () => {
    for (const c of FALLBACK_CANDIDATE_CASES) {
      expect(c.displayLabel).toBeDefined()
      expect(c.displayLabel!.length).toBeGreaterThan(8)
    }
  })

  it('fallback case count grew to >=4 (Phase 18 E baseline; Phase 20 E added 3 more)', () => {
    // Phase 18 E (round 3) pinned this at exactly 4 (3 GS-102 + leak).
    // Phase 20 E (round-1 → round-2 fix) added cylinder-pv,
    // plate-with-hole, and cantilever-beam to close the UX agent's
    // "new candidates invisible in left rail" finding. Pin head-of-
    // list invariant rather than exact count so future additions
    // don't re-trip this test.
    expect(FALLBACK_CANDIDATE_CASES.length).toBeGreaterThanOrEqual(4)
    expect(FALLBACK_CANDIDATE_CASES[0].caseId).toBe('GS-102-candidate')
    expect(FALLBACK_CANDIDATE_CASES[3].caseId).toBe(
      'rod-wave-impact-energy-leak-candidate',
    )
  })

  it('leak case carries the Tier 1 boundary copy', () => {
    const leak = findCandidateCase(
      FALLBACK_CANDIDATE_CASES,
      'rod-wave-impact-energy-leak-candidate',
    )
    expect(leak!.claimBoundary).toContain('tier1_engineering_candidate')
    expect(leak!.claimBoundary).toContain('not_signed_validation')
  })
})

describe('AdvisorPanel round-3 primitive adoption', () => {
  it('renders a SkeletonCard while loading', async () => {
    // Use a fetch stub that never resolves so loading state persists.
    vi.stubGlobal(
      'fetch',
      vi.fn(() => new Promise(() => {})),
    )
    render(
      <AdvisorPanel
        apiBase="http://localhost:8000/api/v1"
        caseId="x-candidate"
        snapshotLabel="snap-1"
      />,
    )
    await waitFor(() =>
      expect(screen.getByTestId('advisor-panel-loading')).toBeInTheDocument(),
    )
    // SkeletonCard's outer wrapper carries data-testid skeleton-card.
    expect(
      screen
        .getByTestId('advisor-panel-loading')
        .querySelector('[data-testid="skeleton-card"]'),
    ).not.toBeNull()
  })

  it('renders an ErrorCard on fetch failure', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => {
        throw new Error('boom')
      }),
    )
    render(
      <AdvisorPanel
        apiBase="http://localhost:8000/api/v1"
        caseId="x-candidate"
        snapshotLabel="snap-1"
      />,
    )
    await waitFor(() =>
      expect(screen.getByTestId('advisor-panel-error')).toBeInTheDocument(),
    )
    expect(
      screen
        .getByTestId('advisor-panel-error')
        .querySelector('[data-testid="error-card"]'),
    ).not.toBeNull()
    expect(
      screen.getByTestId('advisor-panel-error'),
    ).toHaveTextContent('Could not load advisor critique')
    // Error code surfaces for log correlation.
    expect(
      screen.getByTestId('advisor-panel-error'),
    ).toHaveTextContent('ADVISOR-LOAD')
  })
})
