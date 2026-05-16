// FM-04a Phase 7 E — headless smoke for DriftNarrativePanel.
//
// Tier 1 engineering candidate; not signed validation; not benchmark agreement.

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { DriftNarrativePanel } from '../src/components/DriftNarrativePanel.tsx'

const BODY = {
  schema_version: '1.1.0',
  snapshot_a_label: '2026-05-16T100000Z',
  snapshot_b_label: '2026-05-16T200000Z',
  generated_at_utc: '2026-05-16T00:00:00+00:00',
  claim_tier: 'Tier 1 engineering candidate',
  claim_boundary:
    'tier1_engineering_candidate; not_signed_validation; not_benchmark_agreement',
  locale: 'en-US',
  narratives: [
    {
      case_id: 'GS-A-candidate',
      lines: [
        {
          template_id: 'residual_velocity_delta',
          severity: 'info',
          text: 'Residual velocity changed from 75 to 80 m/s (+6.67%).',
        },
        {
          template_id: 'script_sha_changed',
          severity: 'warn',
          text: 'Generator script SHA-256 changed (scripts/gen_gsa_deck.py); regression risk.',
        },
        {
          template_id: 'convergence_verdict_changed',
          severity: 'danger',
          text: "Convergence verdict changed from 'candidate_observed_stable' to 'candidate_observed_unstable'.",
        },
      ],
    },
  ],
  claim_impact:
    'Tier 1 candidate snapshot drift narrative only; not signed validation; not benchmark agreement',
}

function stubFetch(body: unknown, ok = true, status = 200) {
  global.fetch = vi.fn().mockResolvedValue({
    ok,
    status,
    json: async () => body,
  } as Response)
}

describe('DriftNarrativePanel', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('shows the prompt when both labels are missing', () => {
    render(
      <DriftNarrativePanel apiBase="/api/v1" labelA={null} labelB={null} />,
    )
    expect(
      screen.getByText(/pick two snapshots/i),
    ).toBeInTheDocument()
  })

  it('shows the A==B error when both labels equal', () => {
    render(
      <DriftNarrativePanel
        apiBase="/api/v1"
        labelA="2026-05-16T100000Z"
        labelB="2026-05-16T100000Z"
      />,
    )
    expect(
      screen.getByText(/snapshot A and B must differ/i),
    ).toBeInTheDocument()
  })

  it('renders narrative lines with severity-pill labels', async () => {
    stubFetch(BODY)
    render(
      <DriftNarrativePanel
        apiBase="/api/v1"
        labelA="2026-05-16T100000Z"
        labelB="2026-05-16T200000Z"
      />,
    )
    await waitFor(() => {
      expect(
        screen.getByText(/Residual velocity changed/),
      ).toBeInTheDocument()
    })
    expect(screen.getByText(/Generator script SHA-256/)).toBeInTheDocument()
    expect(screen.getByText(/Convergence verdict changed/)).toBeInTheDocument()
    // severity pill text is one of info/warn/danger
    expect(screen.getAllByText(/danger/).length).toBeGreaterThan(0)
    expect(screen.getAllByText(/warn/).length).toBeGreaterThan(0)
    expect(screen.getAllByText(/info/).length).toBeGreaterThan(0)
  })

  it('renders the case_id header for each narrative', async () => {
    stubFetch(BODY)
    render(
      <DriftNarrativePanel
        apiBase="/api/v1"
        labelA="2026-05-16T100000Z"
        labelB="2026-05-16T200000Z"
      />,
    )
    await waitFor(() => {
      expect(screen.getByText('GS-A-candidate')).toBeInTheDocument()
    })
  })

  it('shows error on fetch failure', async () => {
    stubFetch({}, false, 500)
    render(
      <DriftNarrativePanel
        apiBase="/api/v1"
        labelA="2026-05-16T100000Z"
        labelB="2026-05-16T200000Z"
      />,
    )
    await waitFor(() => {
      expect(screen.getByText(/unable|error|500/i)).toBeInTheDocument()
    })
  })
})
