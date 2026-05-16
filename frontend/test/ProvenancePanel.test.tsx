// FM-04a Phase 9 E — headless smoke for ProvenancePanel + typed client.
//
// Tier 1 engineering candidate; not signed validation; not benchmark agreement.

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { ProvenancePanel } from '../src/components/ProvenancePanel.tsx'
import {
  PROVENANCE_INPUT_KINDS,
  parseTrustScoreProvenanceReport,
  shortSha,
} from '../src/trustScoreProvenanceClient.ts'

const FULL_BODY = {
  schema_version: '1.1.0',
  formula_version: '1.0.0',
  case_id: 'GS-A-candidate',
  snapshot_label: '2026-05-16T100000Z',
  generated_at_utc: '2026-05-16T10:00:00+00:00',
  trust_score: 87,
  axes: [
    { axis: 'completeness', weighted: 22 },
    { axis: 'convergence', weighted: 23 },
    { axis: 'energy_audit', weighted: 22 },
    { axis: 'reproducibility', weighted: 20 },
  ],
  inputs: [
    {
      kind: 'metrics',
      path: 'metrics/GS-A-candidate.json',
      present: true,
      sha256: 'a'.repeat(64),
    },
    {
      kind: 'convergence',
      path: 'convergence/GS-A-candidate.json',
      present: true,
      sha256: 'b'.repeat(64),
    },
    {
      kind: 'completeness',
      path: 'completeness/GS-A-candidate.json',
      present: true,
      sha256: 'c'.repeat(64),
    },
    {
      kind: 'reproducibility',
      path: 'reproducibility/GS-A-candidate.json',
      present: false,
      sha256: null,
    },
    {
      kind: 'generator',
      path: 'generator/GS-A-candidate.py',
      present: true,
      sha256: 'd'.repeat(64),
    },
  ],
  claim_tier: 'Tier 1 engineering candidate',
  claim_boundary:
    'tier1_engineering_candidate; not_signed_validation; not_benchmark_agreement',
  claim_impact:
    'Tier 1 candidate trust score provenance trace only; not signed validation; not benchmark agreement.',
}

function stubFetch(body: unknown, ok = true, status = 200) {
  global.fetch = vi.fn().mockResolvedValue({
    ok,
    status,
    json: async () => body,
  } as Response)
}

describe('PROVENANCE_INPUT_KINDS tuple SSOT', () => {
  it('matches the backend Phase 9 B tuple shape exactly', () => {
    expect(PROVENANCE_INPUT_KINDS).toEqual([
      'metrics',
      'convergence',
      'completeness',
      'reproducibility',
      'generator',
    ])
    expect(PROVENANCE_INPUT_KINDS.length).toBe(5)
  })
})

describe('parseTrustScoreProvenanceReport defensive parser', () => {
  it('rejects null / non-object input', () => {
    expect(parseTrustScoreProvenanceReport(null)).toBeNull()
    expect(parseTrustScoreProvenanceReport(undefined)).toBeNull()
  })

  it('rejects payload missing case_id', () => {
    expect(
      parseTrustScoreProvenanceReport({
        snapshot_label: 'x',
      } as Parameters<typeof parseTrustScoreProvenanceReport>[0]),
    ).toBeNull()
  })

  it('falls back to unknown for kinds not in the SSOT tuple', () => {
    const parsed = parseTrustScoreProvenanceReport({
      ...FULL_BODY,
      inputs: [
        {
          kind: 'some_future_kind',
          path: 'future/GS-A-candidate.json',
          present: true,
          sha256: 'e'.repeat(64),
        },
      ],
    })
    expect(parsed).not.toBeNull()
    expect(parsed!.inputs[0].kind).toBe('unknown')
  })
})

describe('shortSha helper', () => {
  it('returns dash on null', () => {
    expect(shortSha(null)).toBe('—')
  })

  it('returns first 12 chars on a full SHA', () => {
    expect(shortSha('abcdef1234567890abcdef')).toBe('abcdef123456')
  })
})

describe('ProvenancePanel', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('renders all 5 input rows for a full provenance payload', async () => {
    stubFetch(FULL_BODY)
    render(
      <ProvenancePanel
        apiBase="/api/v1"
        caseId="GS-A-candidate"
        snapshotLabel="2026-05-16T100000Z"
      />,
    )
    for (const kind of PROVENANCE_INPUT_KINDS) {
      await waitFor(() => {
        expect(
          screen.getByTestId(`provenance-input-row-${kind}`),
        ).toBeInTheDocument()
      })
    }
  })

  it('renders sha-256 short chip on a present input row', async () => {
    stubFetch(FULL_BODY)
    render(
      <ProvenancePanel
        apiBase="/api/v1"
        caseId="GS-A-candidate"
        snapshotLabel="2026-05-16T100000Z"
      />,
    )
    await waitFor(() => {
      // 12 chars of 'a' for the metrics row.
      expect(screen.getByText('a'.repeat(12))).toBeInTheDocument()
    })
  })

  it('renders muted dash for a present=false input row', async () => {
    stubFetch(FULL_BODY)
    render(
      <ProvenancePanel
        apiBase="/api/v1"
        caseId="GS-A-candidate"
        snapshotLabel="2026-05-16T100000Z"
      />,
    )
    await waitFor(() => {
      // The reproducibility row has present=false. The em-dash shows up
      // in the present column for that row.
      const reproRow = screen.getByTestId('provenance-input-row-reproducibility')
      expect(reproRow.textContent).toContain('—')
    })
  })

  it('renders trust score recompute + formula version + schema version', async () => {
    stubFetch(FULL_BODY)
    render(
      <ProvenancePanel
        apiBase="/api/v1"
        caseId="GS-A-candidate"
        snapshotLabel="2026-05-16T100000Z"
      />,
    )
    await waitFor(() => {
      // The header line includes "schema v1.1.0 · formula v1.0.0".
      expect(screen.getByText(/schema v1\.1\.0/)).toBeInTheDocument()
      expect(screen.getByText(/formula v1\.0\.0/)).toBeInTheDocument()
    })
    expect(screen.getByText('87')).toBeInTheDocument()
  })

  it('surfaces tier 1 disclaimer trio in the panel body', async () => {
    stubFetch(FULL_BODY)
    const { container } = render(
      <ProvenancePanel
        apiBase="/api/v1"
        caseId="GS-A-candidate"
        snapshotLabel="2026-05-16T100000Z"
      />,
    )
    await waitFor(() => {
      expect(screen.getByText(/schema v1\.1\.0/)).toBeInTheDocument()
    })
    const text = container.textContent?.toLowerCase() ?? ''
    expect(text).toContain('tier 1 engineering candidate')
    expect(text).toContain('not signed validation')
    expect(text).toContain('not benchmark agreement')
  })

  it('shows error on fetch failure', async () => {
    stubFetch({}, false, 500)
    render(
      <ProvenancePanel
        apiBase="/api/v1"
        caseId="GS-A-candidate"
        snapshotLabel="2026-05-16T100000Z"
      />,
    )
    await waitFor(() => {
      expect(screen.getByText(/unable|error|500/i)).toBeInTheDocument()
    })
  })

  it('skips fetch when caseId or snapshotLabel is empty', () => {
    const fetchSpy = vi.fn()
    global.fetch = fetchSpy
    render(<ProvenancePanel apiBase="/api/v1" caseId="" snapshotLabel="" />)
    expect(fetchSpy).not.toHaveBeenCalled()
  })
})
