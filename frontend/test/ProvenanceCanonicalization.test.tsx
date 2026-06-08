// FM-04a Phase 10 E — frontend smoke for canonical SHA fields on
// trust-score-provenance rows.
//
// Tier 1 engineering candidate; not signed validation; not benchmark agreement.
//
// Pins:
// * Parser tolerates a 1.1.0-era payload (no canonical fields) and
//   surfaces `null` for all three new fields without throwing — the
//   load-bearing forward-compat property of the MINOR bump.
// * Parser plumbs `sha256_normalized` + `normalization_method` +
//   `normalization_error` straight through onto the JS row.
// * Panel renders the generator-row's normalized SHA (short form);
//   non-generator rows render `—`.
// * Panel renders the literal text `parse error` (not the canonical
//   SHA) when `normalizationError` is non-null on a generator row.

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { ProvenancePanel } from '../src/components/ProvenancePanel.tsx'
import { parseTrustScoreProvenanceReport } from '../src/trustScoreProvenanceClient.ts'

const FULL_BODY_WITH_CANONICAL = {
  schema_version: '1.2.0',
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
      sha256_normalized: null,
      normalization_method: null,
      normalization_error: null,
    },
    {
      kind: 'generator',
      path: 'generator/GS-A-candidate.py',
      present: true,
      sha256: 'b'.repeat(64),
      sha256_normalized: 'c'.repeat(64),
      normalization_method: 'python-ast-dump-v1',
      normalization_error: null,
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

describe('Phase 10 E — canonical SHA forward-compat parsing', () => {
  it('parses a 1.1.0-era payload without canonical fields and surfaces null', () => {
    const legacyPayload = {
      schema_version: '1.1.0',
      formula_version: '1.0.0',
      case_id: 'GS-A-candidate',
      snapshot_label: '2026-05-16T100000Z',
      inputs: [
        {
          kind: 'generator',
          path: 'generator/GS-A-candidate.py',
          present: true,
          sha256: 'a'.repeat(64),
        },
      ],
      claim_tier: 'Tier 1 engineering candidate',
      claim_boundary: '',
      claim_impact: '',
    }
    const parsed = parseTrustScoreProvenanceReport(legacyPayload)
    expect(parsed).not.toBeNull()
    expect(parsed!.inputs[0].sha256Normalized).toBeNull()
    expect(parsed!.inputs[0].normalizationMethod).toBeNull()
    expect(parsed!.inputs[0].normalizationError).toBeNull()
  })

  it('plumbs all three canonical fields from a 1.2.0 payload', () => {
    const parsed = parseTrustScoreProvenanceReport(FULL_BODY_WITH_CANONICAL)
    expect(parsed).not.toBeNull()
    const gen = parsed!.inputs.find((i) => i.kind === 'generator')!
    expect(gen.sha256Normalized).toBe('c'.repeat(64))
    expect(gen.normalizationMethod).toBe('python-ast-dump-v1')
    expect(gen.normalizationError).toBeNull()
    const metrics = parsed!.inputs.find((i) => i.kind === 'metrics')!
    expect(metrics.sha256Normalized).toBeNull()
    expect(metrics.normalizationMethod).toBeNull()
    expect(metrics.normalizationError).toBeNull()
  })

  it('surfaces normalization_error verbatim on the parsed row', () => {
    const parsed = parseTrustScoreProvenanceReport({
      ...FULL_BODY_WITH_CANONICAL,
      inputs: [
        {
          kind: 'generator',
          path: 'generator/GS-A-candidate.py',
          present: true,
          sha256: 'a'.repeat(64),
          sha256_normalized: null,
          normalization_method: null,
          normalization_error: 'SyntaxError: invalid syntax (<unknown>, line 1)',
        },
      ],
    })
    expect(parsed!.inputs[0].normalizationError).toContain('SyntaxError')
    expect(parsed!.inputs[0].sha256Normalized).toBeNull()
  })
})

describe('Phase 10 E — ProvenancePanel renders normalized SHA cell', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('renders short canonical SHA on the generator row', async () => {
    stubFetch(FULL_BODY_WITH_CANONICAL)
    render(
      <ProvenancePanel
        apiBase="/api/v1"
        caseId="GS-A-candidate"
        snapshotLabel="2026-05-16T100000Z"
      />,
    )
    await waitFor(() => {
      const cell = screen.getByTestId('provenance-input-normalized-generator')
      expect(cell.textContent).toBe('c'.repeat(12))
    })
  })

  it('renders em-dash on non-generator rows (canonical fields null)', async () => {
    stubFetch(FULL_BODY_WITH_CANONICAL)
    render(
      <ProvenancePanel
        apiBase="/api/v1"
        caseId="GS-A-candidate"
        snapshotLabel="2026-05-16T100000Z"
      />,
    )
    await waitFor(() => {
      const cell = screen.getByTestId('provenance-input-normalized-metrics')
      expect(cell.textContent).toBe('—')
    })
  })

  it('renders literal "parse error" when normalizationError is non-null', async () => {
    stubFetch({
      ...FULL_BODY_WITH_CANONICAL,
      inputs: [
        {
          kind: 'generator',
          path: 'generator/GS-A-candidate.py',
          present: true,
          sha256: 'a'.repeat(64),
          sha256_normalized: null,
          normalization_method: null,
          normalization_error: 'SyntaxError: invalid syntax',
        },
      ],
    })
    render(
      <ProvenancePanel
        apiBase="/api/v1"
        caseId="GS-A-candidate"
        snapshotLabel="2026-05-16T100000Z"
      />,
    )
    await waitFor(() => {
      const cell = screen.getByTestId('provenance-input-normalized-generator')
      expect(cell.textContent).toBe('parse error')
    })
  })
})
