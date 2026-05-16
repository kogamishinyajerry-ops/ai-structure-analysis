// FM-04a Phase 8 E — headless smoke for CohortAnomaliesPanel.

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { CohortAnomaliesPanel } from '../src/components/CohortAnomaliesPanel.tsx'
import { SUPPORTED_ANOMALY_SEVERITIES } from '../src/cohortAnomaliesClient.ts'

const EMPTY = {
  schema_version: '1.0.0',
  generated_at_utc: '2026-05-16T00:00:00+00:00',
  claim_tier: 'Tier 1 engineering candidate',
  claim_boundary:
    'tier1_engineering_candidate; not_signed_validation; not_benchmark_agreement',
  cohort_count: 3,
  anomaly_count: 0,
  anomalies: [],
  claim_impact:
    'Tier 1 candidate cohort statistical outliers only; not signed validation; not benchmark agreement.',
}

const WITH_OUTLIER = {
  ...EMPTY,
  cohort_count: 5,
  anomaly_count: 1,
  anomalies: [
    {
      case_id: 'GS-Z-candidate',
      axis: 'completeness',
      score: 5,
      cohort_mean: 35.0,
      cohort_stdev: 15.0,
      z_score: -2.0,
      severity: 'info',
    },
  ],
}

function stubFetch(body: unknown, ok = true, status = 200) {
  global.fetch = vi.fn().mockResolvedValue({
    ok,
    status,
    json: async () => body,
  } as Response)
}

describe('CohortAnomaliesPanel', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('renders empty-state copy when anomaly_count is 0', async () => {
    stubFetch(EMPTY)
    render(<CohortAnomaliesPanel apiBase="/api/v1" />)
    await waitFor(() => {
      expect(screen.getByText(/no statistical outliers/i)).toBeInTheDocument()
    })
  })

  it('renders an outlier row with z-score + severity', async () => {
    stubFetch(WITH_OUTLIER)
    render(<CohortAnomaliesPanel apiBase="/api/v1" />)
    await waitFor(() => {
      expect(screen.getByText('GS-Z-candidate')).toBeInTheDocument()
    })
    expect(screen.getByText('completeness')).toBeInTheDocument()
    expect(screen.getByText('-2.00')).toBeInTheDocument()
    expect(screen.getByText('info')).toBeInTheDocument()
  })

  it('shows error on fetch failure', async () => {
    stubFetch({}, false, 500)
    render(<CohortAnomaliesPanel apiBase="/api/v1" />)
    await waitFor(() => {
      expect(screen.getByText(/unable|error|500/i)).toBeInTheDocument()
    })
  })

  it('exports the severity whitelist constant', () => {
    expect(SUPPORTED_ANOMALY_SEVERITIES).toEqual(['info', 'warn', 'danger'])
  })
})
