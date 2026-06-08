// FM-04a Phase 10 B — headless smoke for CohortTrendAnomaliesPanel.
//
// Tier 1 engineering candidate; not signed validation; not benchmark agreement.

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { CohortTrendAnomaliesPanel } from '../src/components/CohortTrendAnomaliesPanel.tsx'
import {
  SUPPORTED_TREND_SEVERITIES,
  parseCohortTrendAnomaliesReport,
} from '../src/cohortTrendAnomaliesClient.ts'

const EMPTY = {
  schema_version: '1.0.0',
  generated_at_utc: '2026-05-16T00:00:00+00:00',
  claim_tier: 'Tier 1 engineering candidate',
  claim_boundary:
    'tier1_engineering_candidate; not_signed_validation; not_benchmark_agreement',
  cohort_count: 3,
  point_count_floor: 3,
  anomaly_count: 0,
  anomalies: [],
  claim_impact:
    'Tier 1 candidate cohort trend-slope outliers only; not signed validation; not benchmark agreement.',
}

const WITH_DANGER = {
  ...EMPTY,
  cohort_count: 1,
  anomaly_count: 1,
  anomalies: [
    {
      case_id: 'GS-A-candidate',
      axis: 'completeness',
      slope: -5.0,
      point_count: 5,
      severity: 'danger',
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

describe('SUPPORTED_TREND_SEVERITIES as-const tuple', () => {
  it('matches backend severity literal set', () => {
    expect(SUPPORTED_TREND_SEVERITIES).toEqual(['info', 'warn', 'danger'])
  })
})

describe('parseCohortTrendAnomaliesReport defensive parser', () => {
  it('rejects null / non-object input', () => {
    expect(parseCohortTrendAnomaliesReport(null)).toBeNull()
    expect(parseCohortTrendAnomaliesReport(undefined)).toBeNull()
  })

  it('maps unknown severity to info (most conservative)', () => {
    const parsed = parseCohortTrendAnomaliesReport({
      ...EMPTY,
      anomalies: [
        {
          case_id: 'GS-X',
          axis: 'completeness',
          slope: -2.0,
          point_count: 4,
          severity: 'catastrophic',
        },
      ],
    })
    expect(parsed?.anomalies[0].severity).toBe('info')
  })

  it('preserves point_count_floor default of 3 when payload omits it', () => {
    const parsed = parseCohortTrendAnomaliesReport({
      ...EMPTY,
      point_count_floor: undefined,
    })
    expect(parsed?.pointCountFloor).toBe(3)
  })
})

describe('CohortTrendAnomaliesPanel', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('renders empty-state copy when anomaly_count is 0', async () => {
    stubFetch(EMPTY)
    render(<CohortTrendAnomaliesPanel apiBase="/api/v1" />)
    await waitFor(() => {
      expect(screen.getByTestId('cohort-trend-anomalies-empty')).toBeInTheDocument()
    })
  })

  it('renders a trend event row with slope + severity', async () => {
    stubFetch(WITH_DANGER)
    render(<CohortTrendAnomaliesPanel apiBase="/api/v1" />)
    await waitFor(() => {
      expect(
        screen.getByTestId('trend-event-row-GS-A-candidate-completeness'),
      ).toBeInTheDocument()
    })
    expect(screen.getByText('-5.00')).toBeInTheDocument()
    expect(screen.getByText('danger')).toBeInTheDocument()
  })

  it('renders Tier 1 disclaimer trio in panel body', async () => {
    stubFetch(WITH_DANGER)
    const { container } = render(<CohortTrendAnomaliesPanel apiBase="/api/v1" />)
    await waitFor(() => {
      expect(
        screen.getByTestId('trend-event-row-GS-A-candidate-completeness'),
      ).toBeInTheDocument()
    })
    const text = container.textContent?.toLowerCase() ?? ''
    expect(text).toContain('tier 1 engineering candidate')
    expect(text).toContain('not signed validation')
    expect(text).toContain('not benchmark agreement')
  })

  it('shows error on fetch failure', async () => {
    stubFetch({}, false, 500)
    render(<CohortTrendAnomaliesPanel apiBase="/api/v1" />)
    await waitFor(() => {
      expect(screen.getByText(/unable|error|500/i)).toBeInTheDocument()
    })
  })

  it('renders schema version + point count floor in header', async () => {
    stubFetch(WITH_DANGER)
    render(<CohortTrendAnomaliesPanel apiBase="/api/v1" />)
    await waitFor(() => {
      expect(screen.getByText(/schema v1\.0\.0/)).toBeInTheDocument()
    })
    expect(screen.getByText(/floor 3/)).toBeInTheDocument()
  })
})
