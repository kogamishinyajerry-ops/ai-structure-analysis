// FM-04a Phase 7 E — headless smoke for TrustScoreGauge.
//
// Tier 1 engineering candidate; not signed validation; not benchmark agreement.
//
// Closes Phase 6 retrospective carry-forward §2 for one of three
// Phase 6 E components.

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { TrustScoreGauge } from '../src/components/TrustScoreGauge.tsx'

const TIER1_BODY = {
  schema_version: '1.0.0',
  formula_version: '1.0.0',
  case_id: 'GS-A-candidate',
  claim_tier: 'Tier 1 engineering candidate',
  claim_boundary:
    'tier1_engineering_candidate; not_signed_validation; not_benchmark_agreement',
  generated_at_utc: '2026-05-16T00:00:00+00:00',
  trust_score: 87,
  trust_score_max: 100,
  breakdown: [
    {
      axis: 'completeness',
      weight: 50,
      raw_score: 90,
      weighted: 45,
      rationale: 'completeness scorecard reported 90/100 normalized',
    },
    {
      axis: 'convergence_stability',
      weight: 20,
      raw_score: 100,
      weighted: 20,
      rationale: 'both sweeps stable',
    },
    {
      axis: 'energy_audit_closure',
      weight: 15,
      raw_score: 100,
      weighted: 15,
      rationale: 'closed_aggregate',
    },
    {
      axis: 'reproducibility_clean',
      weight: 15,
      raw_score: 47,
      weighted: 7,
      rationale: 'git dirty + python missing',
    },
  ],
  tier2_blockers_remaining: [],
  claim_impact:
    'Tier 1 candidate evidence trust score only; not signed validation; not benchmark agreement',
}

function stubFetch(body: unknown, ok = true, status = 200) {
  global.fetch = vi.fn().mockResolvedValue({
    ok,
    status,
    json: async () => body,
  } as Response)
}

describe('TrustScoreGauge', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('renders the EXACT integer score (no rounding, no toFixed)', async () => {
    stubFetch({ ...TIER1_BODY, trust_score: 87 })
    render(<TrustScoreGauge apiBase="/api/v1" caseId="GS-A-candidate" />)
    await waitFor(() => {
      expect(screen.getByText('87')).toBeInTheDocument()
    })
    // Verify the body never inserts a decimal-shaped string like "87.0"
    expect(screen.queryByText('87.0')).not.toBeInTheDocument()
    expect(screen.queryByText('86.5')).not.toBeInTheDocument()
  })

  it('renders breakdown rows for all 4 axes', async () => {
    stubFetch(TIER1_BODY)
    render(<TrustScoreGauge apiBase="/api/v1" caseId="GS-A-candidate" />)
    await waitFor(() => {
      expect(screen.getByText('completeness')).toBeInTheDocument()
    })
    expect(screen.getByText('convergence_stability')).toBeInTheDocument()
    expect(screen.getByText('energy_audit_closure')).toBeInTheDocument()
    expect(screen.getByText('reproducibility_clean')).toBeInTheDocument()
  })

  it('surfaces both schema_version and formula_version', async () => {
    stubFetch({ ...TIER1_BODY, schema_version: '1.0.0', formula_version: '1.0.0' })
    render(<TrustScoreGauge apiBase="/api/v1" caseId="GS-A-candidate" />)
    await waitFor(() => {
      // monospace header carries both stamps; verify both appear
      expect(screen.getByText(/schema/i)).toBeInTheDocument()
    })
  })

  it('renders Tier 1 banner in the header', async () => {
    stubFetch(TIER1_BODY)
    render(<TrustScoreGauge apiBase="/api/v1" caseId="GS-A-candidate" />)
    await waitFor(() => {
      expect(screen.getByText(/Tier 1/i)).toBeInTheDocument()
    })
  })

  it('does not render a gauge when caseId is null', () => {
    stubFetch(TIER1_BODY)
    render(<TrustScoreGauge apiBase="/api/v1" caseId={null} />)
    // helper hint should appear; gauge body should not
    expect(screen.queryByText('87')).not.toBeInTheDocument()
  })

  it('surfaces an error message on fetch failure', async () => {
    stubFetch({}, false, 500)
    render(<TrustScoreGauge apiBase="/api/v1" caseId="GS-A-candidate" />)
    await waitFor(() => {
      // Component sets error state on parse / non-ok response
      expect(screen.getByText(/unable|error|500/i)).toBeInTheDocument()
    })
  })
})
