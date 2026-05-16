// FM-04a Phase 8 D — headless smoke for CohortExecutiveSummaryPanel.

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { CohortExecutiveSummaryPanel } from '../src/components/CohortExecutiveSummaryPanel.tsx'
import { bucketTone, HEALTH_BUCKETS } from '../src/cohortExecutiveSummaryClient.ts'

const BODY = {
  schema_version: '1.0.0',
  generated_at_utc: '2026-05-16T00:00:00+00:00',
  claim_tier: 'Tier 1 engineering candidate',
  claim_boundary:
    'tier1_engineering_candidate; not_signed_validation; not_benchmark_agreement',
  cohort_count: 3,
  healthy_count: 1,
  watching_count: 1,
  regressed_count: 1,
  cases: [
    {
      case_id: 'GS-A-candidate',
      latest_trust_score: 85,
      latest_snapshot_label: '2026-05-16T100000Z',
      latest_signoff_verdict: null,
      alarm_count_warn_or_danger: 0,
      bucket: 'healthy',
    },
    {
      case_id: 'GS-B-candidate',
      latest_trust_score: 65,
      latest_snapshot_label: '2026-05-16T100000Z',
      latest_signoff_verdict: 'watching',
      alarm_count_warn_or_danger: 0,
      bucket: 'watching',
    },
    {
      case_id: 'GS-C-candidate',
      latest_trust_score: 30,
      latest_snapshot_label: '2026-05-16T100000Z',
      latest_signoff_verdict: 'blocked_pending_input',
      alarm_count_warn_or_danger: 2,
      bucket: 'regressed',
    },
  ],
  claim_impact:
    'Tier 1 candidate cohort scorecard only; not signed validation; not benchmark agreement.',
}

function stubFetch(body: unknown, ok = true, status = 200) {
  global.fetch = vi.fn().mockResolvedValue({
    ok,
    status,
    json: async () => body,
  } as Response)
}

describe('CohortExecutiveSummaryPanel', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('renders three bucket counters with the documented counts', async () => {
    stubFetch(BODY)
    render(<CohortExecutiveSummaryPanel apiBase="/api/v1" />)
    await waitFor(() => {
      // counter labels appear once for each bucket; per-case rows also
      // surface the bucket label, so getAllByText is the right matcher.
      expect(screen.getAllByText('healthy').length).toBeGreaterThanOrEqual(1)
    })
    expect(screen.getAllByText('watching').length).toBeGreaterThanOrEqual(1)
    expect(screen.getAllByText('regressed').length).toBeGreaterThanOrEqual(1)
    // Bucket counts surface as bold numbers
    expect(screen.getAllByText('1').length).toBeGreaterThanOrEqual(3)
  })

  it('renders per-case rows with case_id + trust score + alarm count', async () => {
    stubFetch(BODY)
    render(<CohortExecutiveSummaryPanel apiBase="/api/v1" />)
    await waitFor(() => {
      expect(screen.getByText('GS-A-candidate')).toBeInTheDocument()
    })
    expect(screen.getByText('GS-B-candidate')).toBeInTheDocument()
    expect(screen.getByText('GS-C-candidate')).toBeInTheDocument()
    expect(screen.getByText('85')).toBeInTheDocument()
    expect(screen.getByText('65')).toBeInTheDocument()
    expect(screen.getByText('30')).toBeInTheDocument()
  })

  it('shows error on fetch failure', async () => {
    stubFetch({}, false, 500)
    render(<CohortExecutiveSummaryPanel apiBase="/api/v1" />)
    await waitFor(() => {
      expect(screen.getByText(/unable|error|500/i)).toBeInTheDocument()
    })
  })

  it('exports the 3-bucket whitelist constant', () => {
    expect(HEALTH_BUCKETS).toEqual(['healthy', 'watching', 'regressed'])
  })

  it('bucketTone maps buckets to documented tone buckets', () => {
    expect(bucketTone('healthy')).toBe('info')
    expect(bucketTone('watching')).toBe('warn')
    expect(bucketTone('regressed')).toBe('danger')
  })
})
