// FM-04a Phase 7 E — headless smoke for TrustScoreTimelineChart.
//
// Tier 1 engineering candidate; not signed validation; not benchmark agreement.

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { TrustScoreTimelineChart } from '../src/components/TrustScoreTimelineChart.tsx'
import { buildSparklinePath } from '../src/trustScoreTimelineClient.ts'

const BODY = {
  schema_version: '1.0.0',
  formula_version: '1.0.0',
  case_id: 'GS-A-candidate',
  claim_tier: 'Tier 1 engineering candidate',
  claim_boundary:
    'tier1_engineering_candidate; not_signed_validation; not_benchmark_agreement',
  generated_at_utc: '2026-05-16T00:00:00+00:00',
  point_count: 3,
  points: [
    {
      snapshot_label: '2026-05-16T100000Z',
      captured_at_utc: '2026-05-16T10:00:00+00:00',
      trust_score: 70,
      completeness_weighted: 35,
      convergence_weighted: 20,
      energy_audit_weighted: 15,
      reproducibility_weighted: 0,
    },
    {
      snapshot_label: '2026-05-16T200000Z',
      captured_at_utc: '2026-05-16T20:00:00+00:00',
      trust_score: 82,
      completeness_weighted: 40,
      convergence_weighted: 20,
      energy_audit_weighted: 15,
      reproducibility_weighted: 7,
    },
    {
      snapshot_label: '2026-05-16T300000Z',
      captured_at_utc: '2026-05-16T30:00:00+00:00',
      trust_score: 87,
      completeness_weighted: 45,
      convergence_weighted: 20,
      energy_audit_weighted: 15,
      reproducibility_weighted: 7,
    },
  ],
  claim_impact:
    'Tier 1 candidate trust score timeline only; not signed validation; not benchmark agreement',
}

function stubFetch(body: unknown, ok = true, status = 200) {
  global.fetch = vi.fn().mockResolvedValue({
    ok,
    status,
    json: async () => body,
  } as Response)
}

describe('TrustScoreTimelineChart', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('shows the candidate-case prompt when caseId is null', () => {
    render(<TrustScoreTimelineChart apiBase="/api/v1" caseId={null} />)
    expect(
      screen.getByText(/select a candidate case/i),
    ).toBeInTheDocument()
  })

  it('renders a sparkline SVG with the right viewport', async () => {
    stubFetch(BODY)
    render(
      <TrustScoreTimelineChart apiBase="/api/v1" caseId="GS-A-candidate" />,
    )
    await waitFor(() => {
      const svg = document.querySelector('svg[aria-label="trust score sparkline"]')
      expect(svg).not.toBeNull()
      expect(svg?.getAttribute('viewBox')).toBe('0 0 320 60')
    })
  })

  it('renders the per-snapshot table for each timeline point', async () => {
    stubFetch(BODY)
    render(
      <TrustScoreTimelineChart apiBase="/api/v1" caseId="GS-A-candidate" />,
    )
    await waitFor(() => {
      expect(screen.getByText('2026-05-16T100000Z')).toBeInTheDocument()
    })
    expect(screen.getByText('2026-05-16T200000Z')).toBeInTheDocument()
    expect(screen.getByText('2026-05-16T300000Z')).toBeInTheDocument()
  })

  it('surfaces the empty-state copy when point_count is 0', async () => {
    stubFetch({ ...BODY, point_count: 0, points: [] })
    render(
      <TrustScoreTimelineChart apiBase="/api/v1" caseId="GS-A-candidate" />,
    )
    await waitFor(() => {
      expect(
        screen.getByText(/no cohort snapshots/i),
      ).toBeInTheDocument()
    })
  })

  it('buildSparklinePath emits a valid SVG path for any non-empty point list', () => {
    const path = buildSparklinePath(
      [
        {
          snapshotLabel: 'a',
          capturedAtUtc: null,
          trustScore: 70,
          completenessWeighted: 35,
          convergenceWeighted: 20,
          energyAuditWeighted: 15,
          reproducibilityWeighted: 0,
        },
        {
          snapshotLabel: 'b',
          capturedAtUtc: null,
          trustScore: 87,
          completenessWeighted: 45,
          convergenceWeighted: 20,
          energyAuditWeighted: 15,
          reproducibilityWeighted: 7,
        },
      ],
      320,
      60,
    )
    expect(path).toMatch(/^M/)
    expect(path).toMatch(/L/)
  })

  it('buildSparklinePath emits empty string for empty points list', () => {
    expect(buildSparklinePath([], 320, 60)).toBe('')
  })
})
