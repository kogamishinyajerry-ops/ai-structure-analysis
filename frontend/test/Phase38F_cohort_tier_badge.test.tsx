/**
 * FM-04a Phase 38 F — cohort dashboard surfaces per-case Tier-2 promotion.
 *
 * Eval-fleet finding #1 (Phase 38 E): the backend never emitted per-case
 * `claim_tier`, and the cohort panel never rendered it, so a real-solver
 * promotion (tier_2_validated) was invisible. The backend now emits it
 * (cohortOverviewClient already mapped `raw.claim_tier`); this test pins the
 * panel rendering: a Tier-2 entry shows the badge, a Tier-1 entry does not.
 *
 * Tier 1 / Tier 2 engineering candidate; not signed validation; not benchmark
 * agreement.
 */

import { afterEach, describe, expect, it, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'

import { CohortDashboardPanel } from '../src/components/CohortDashboardPanel'
import { boundaryDisclaimer } from '../src/components/CandidateCasePicker'

function entry(caseId: string, claim_tier: string) {
  return {
    case_id: caseId,
    claim_tier,
    completeness_score: 7,
    completeness_score_max: 7,
    perforation_marker: null,
    residual_velocity_candidate_m_per_s: null,
    energy_balance_error_pct: null,
    energy_audit_status: 'unavailable',
    convergence_combined_verdict: 'insufficient_data',
    last_modified_utc: '2026-05-24T00:00:00+00:00',
    missing_evidence_count: 0,
  }
}

function stubFetch(payload: unknown) {
  global.fetch = vi.fn().mockResolvedValue({
    ok: true,
    json: async () => payload,
  }) as unknown as typeof fetch
}

afterEach(() => {
  vi.restoreAllMocks()
})

describe('CohortDashboardPanel per-case Tier-2 badge (Phase 38 F)', () => {
  const payload = {
    schema_version: '1.1.0', // 1.1.0 carries per-entry claim_tier (Phase 38 F)
    generated_at_utc: '2026-05-24T00:00:00+00:00',
    claim_tier: 'Tier 1 engineering candidate', // cohort floor stays Tier 1
    claim_boundary: 'tier1',
    cohort_count: 2,
    mean_score: 7,
    completeness_distribution: {},
    entries: [
      entry('cylinder-pv-candidate', 'Tier 2 real-solver validated'),
      entry('ballistic-plate-candidate', 'Tier 1 engineering candidate'),
    ],
    tier2_blockers_remaining: [],
    claim_impact: 'mixed cohort',
  }

  it('renders the Tier-2 badge for a validated case', async () => {
    stubFetch(payload)
    render(
      <CohortDashboardPanel
        apiBase="/api/v1"
        selectedCaseId={null}
        onSelectCase={vi.fn()}
      />,
    )
    await waitFor(() => {
      expect(
        screen.getByTestId('cohort-tier2-cylinder-pv-candidate'),
      ).toBeInTheDocument()
    })
    expect(
      screen.getByText('✓ Tier 2 real-solver validated'),
    ).toBeInTheDocument()
  })

  it('does NOT render the badge for a Tier-1 case (no over-claim)', async () => {
    stubFetch(payload)
    render(
      <CohortDashboardPanel
        apiBase="/api/v1"
        selectedCaseId={null}
        onSelectCase={vi.fn()}
      />,
    )
    // wait until the rows have rendered, then assert the tier-1 row has no badge
    await waitFor(() => {
      expect(
        screen.getByTestId('cohort-row-ballistic-plate-candidate'),
      ).toBeInTheDocument()
    })
    expect(
      screen.queryByTestId('cohort-tier2-ballistic-plate-candidate'),
    ).toBeNull()
  })
})

describe('boundaryDisclaimer — picker banner suffix (Phase 38 F, Codex R3)', () => {
  it('tier-1 boundary → unchanged legacy disclaimer', () => {
    expect(
      boundaryDisclaimer(
        'tier1_engineering_candidate; not_signed_validation; not_benchmark_agreement',
      ),
    ).toBe('not signed validation · not benchmark agreement')
  })

  it('tier-2 boundary → surfaces cross_check_against_analytical (no Tier-1 suffix)', () => {
    const out = boundaryDisclaimer(
      'tier2_real_solver_validated; not_signed_validation; cross_check_against_analytical',
    )
    expect(out).toBe('not signed validation · cross check against analytical')
    // The bug was a hard-coded Tier-1 suffix on Tier-2 rows: must NOT appear.
    expect(out).not.toContain('not benchmark agreement')
  })

  it('undefined boundary → safe Tier-1 fallback', () => {
    expect(boundaryDisclaimer(undefined)).toBe(
      'not signed validation · not benchmark agreement',
    )
  })
})
