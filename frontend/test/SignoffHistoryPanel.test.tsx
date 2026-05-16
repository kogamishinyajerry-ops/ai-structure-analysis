// FM-04a Phase 8 B — headless smoke for SignoffHistoryPanel.
//
// Tier 1 engineering candidate; not signed validation; not benchmark agreement.

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { SignoffHistoryPanel } from '../src/components/SignoffHistoryPanel.tsx'
import {
  SUPPORTED_SIGNOFF_VERDICTS,
  toneForVerdict,
} from '../src/signoffHistoryClient.ts'

const BODY = {
  schema_version: '1.0.0',
  case_id: 'GS-A-candidate',
  claim_tier: 'Tier 1 engineering candidate',
  claim_boundary:
    'tier1_engineering_candidate; not_signed_validation; not_benchmark_agreement',
  generated_at_utc: '2026-05-16T00:00:00+00:00',
  record_count: 2,
  records: [
    {
      schema_version: '1.0.0',
      case_id: 'GS-A-candidate',
      reviewer: 'alice',
      verdict: 'watching',
      signoff_utc: '2026-05-16T100000Z',
      notes: 'Tier 1 monitoring round.',
      claim_tier: 'Tier 1 engineering candidate',
      claim_boundary:
        'tier1_engineering_candidate; not_signed_validation; not_benchmark_agreement',
      claim_impact:
        'Tier 1 candidate review judgments only; not signed validation; not benchmark agreement.',
    },
    {
      schema_version: '1.0.0',
      case_id: 'GS-A-candidate',
      reviewer: 'bob',
      verdict: 'needs_more_convergence',
      signoff_utc: '2026-05-16T140000Z',
      notes: 'Wants tighter mesh sweep.',
      claim_tier: 'Tier 1 engineering candidate',
      claim_boundary:
        'tier1_engineering_candidate; not_signed_validation; not_benchmark_agreement',
      claim_impact:
        'Tier 1 candidate review judgments only; not signed validation; not benchmark agreement.',
    },
  ],
  claim_impact:
    'Tier 1 candidate review judgments only; not signed validation; not benchmark agreement.',
}

function stubFetch(body: unknown, ok = true, status = 200) {
  global.fetch = vi.fn().mockResolvedValue({
    ok,
    status,
    json: async () => body,
  } as Response)
}

describe('SignoffHistoryPanel', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('shows the candidate-case prompt when caseId is null', () => {
    render(<SignoffHistoryPanel apiBase="/api/v1" caseId={null} />)
    expect(
      screen.getByText(/select a candidate case/i),
    ).toBeInTheDocument()
  })

  it('renders the empty-state copy when record_count is 0', async () => {
    stubFetch({ ...BODY, record_count: 0, records: [] })
    render(
      <SignoffHistoryPanel apiBase="/api/v1" caseId="GS-A-candidate" />,
    )
    await waitFor(() => {
      expect(screen.getByText(/no signoffs yet/i)).toBeInTheDocument()
    })
  })

  it('renders all signoff records with verdict pills', async () => {
    stubFetch(BODY)
    render(
      <SignoffHistoryPanel apiBase="/api/v1" caseId="GS-A-candidate" />,
    )
    await waitFor(() => {
      expect(screen.getByText('alice')).toBeInTheDocument()
    })
    expect(screen.getByText('bob')).toBeInTheDocument()
    expect(screen.getByText('watching')).toBeInTheDocument()
    expect(screen.getByText('needs_more_convergence')).toBeInTheDocument()
    // notes bodies surface
    expect(screen.getByText(/monitoring round/i)).toBeInTheDocument()
    expect(screen.getByText(/tighter mesh sweep/i)).toBeInTheDocument()
  })

  it('shows error on fetch failure', async () => {
    stubFetch({}, false, 500)
    render(
      <SignoffHistoryPanel apiBase="/api/v1" caseId="GS-A-candidate" />,
    )
    await waitFor(() => {
      expect(screen.getByText(/unable|error|500/i)).toBeInTheDocument()
    })
  })

  it('fires onLatestRecord with the chronologically last record', async () => {
    stubFetch(BODY)
    const onLatestRecord = vi.fn()
    render(
      <SignoffHistoryPanel
        apiBase="/api/v1"
        caseId="GS-A-candidate"
        onLatestRecord={onLatestRecord}
      />,
    )
    await waitFor(() => {
      expect(onLatestRecord).toHaveBeenCalled()
    })
    const lastCall = onLatestRecord.mock.calls.at(-1)
    expect(lastCall?.[0]?.reviewer).toBe('bob')
    expect(lastCall?.[0]?.verdict).toBe('needs_more_convergence')
  })

  it('exports every supported verdict in the whitelist constant', () => {
    // Phase 8 anti-gaming guard X: -2 — UI consumes the whitelist, not
    // a hardcoded list. This test pins the constant so a regression
    // (duplicate inline list) fails the suite.
    expect(SUPPORTED_SIGNOFF_VERDICTS).toEqual([
      'watching',
      'needs_more_evidence',
      'needs_more_convergence',
      'blocked_pending_input',
    ])
  })

  it('toneForVerdict maps verdicts to documented severity buckets', () => {
    expect(toneForVerdict('watching')).toBe('info')
    expect(toneForVerdict('needs_more_evidence')).toBe('warn')
    expect(toneForVerdict('needs_more_convergence')).toBe('warn')
    expect(toneForVerdict('blocked_pending_input')).toBe('danger')
  })
})
