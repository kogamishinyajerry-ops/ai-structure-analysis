// FM-04a Phase 34 A — analysis-type-aware vocab in CaseComparisonPanel.
//
// Pin the fix for Phase 33 C novice_simulator finding #1 (triple-
// flagged across P1+P2+P5 personas): ballistic axis labels (residual
// velocity / perforation marker / energy balance / energy audit) were
// being rendered with dash-filled values for non-ballistic cases like
// cantilever-beam-candidate or plate-with-hole-candidate. A junior
// engineer reading "residual velocity" on a static-structural
// cantilever comparison was confused ("is this case broken?").
//
// The Phase 34 A fix: when the backend returns all 4 ballistic-axis
// fields as null/empty (signalling non-ballistic comparison), the
// panel hides the ballistic rows and shows a clear notice instead.
// Convergence verdict + artifact diffs (analysis-type-neutral)
// continue to render.
//
// Anti-gaming guards:
//   J:-1 — CSV export schema NOT changed by Phase 34 A. The Phase
//          25 D 5-column export pins (not in this file) continue to
//          pass. Phase 34 A is presentation-layer only.
//   D:-1 — CaseComparison TypeScript schema unchanged; behavior is
//          driven by data presence at runtime, not schema rewrites.
//   C:-1 — ballistic comparison rendering preserved (case 4 below).

import { describe, expect, it, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { CaseComparisonPanel } from '../src/components/CaseComparisonPanel'
import type { CandidateCaseRecord } from '../src/candidateCaseRegistry'

const NULL_NUMERIC_DELTA = { a: null, b: null, delta: null, delta_pct: null }
const NULL_ABSOLUTE_DELTA = { a: null, b: null, delta_abs_pct: null }
const NULL_MARKER_DIFF = { a: null, b: null, same_marker: true }

const NEUTRAL_EXTRA_FIELDS = {
  energy_audit_status_diff: {
    a: 'n/a',
    b: 'n/a',
    both_closed: true,
    same_status: true,
  },
  convergence_verdict_diff: {
    a: 'PASS',
    b: 'PASS',
    same_verdict: true,
  },
  deck_artifact_diff: {
    a_only: [],
    b_only: [],
    shared: [],
    hash_changed: [],
  },
  evidence_artifact_diff: {
    a_only: [],
    b_only: [],
    shared: [],
    hash_changed: [],
  },
}

const NON_BALLISTIC_RESPONSE = {
  schema_version: '1.0.0',
  case_a: 'cantilever-beam-candidate',
  case_b: 'plate-with-hole-candidate',
  generated_at_utc: '2026-05-18T12:00:00Z',
  claim_boundary: 'tier1_engineering_candidate',
  residual_velocity_diff: NULL_NUMERIC_DELTA,
  perforation_marker_diff: NULL_MARKER_DIFF,
  energy_balance_error_diff: NULL_ABSOLUTE_DELTA,
  ...NEUTRAL_EXTRA_FIELDS,
  claim_impact: 'static-vs-static comparison; ballistic axes N/A',
}

const BALLISTIC_RESPONSE = {
  schema_version: '1.0.0',
  case_a: 'plate-ballistic-candidate-a',
  case_b: 'plate-ballistic-candidate-b',
  generated_at_utc: '2026-05-18T12:00:00Z',
  claim_boundary: 'tier1_engineering_candidate',
  residual_velocity_diff: { a: 320.5, b: 318.2, delta: -2.3, delta_pct: -0.72 },
  perforation_marker_diff: { a: 'partial', b: 'partial', same_marker: true },
  energy_balance_error_diff: { a: 0.04, b: 0.06, delta_abs_pct: 0.02 },
  ...NEUTRAL_EXTRA_FIELDS,
  energy_audit_status_diff: {
    a: 'closed',
    b: 'closed',
    both_closed: true,
    same_status: true,
  },
  claim_impact: 'ballistic-vs-ballistic comparison',
}

const CASES: CandidateCaseRecord[] = [
  { id: 'cantilever-beam-candidate', label: 'Cantilever Beam' } as CandidateCaseRecord,
  { id: 'plate-with-hole-candidate', label: 'Plate with Hole' } as CandidateCaseRecord,
  { id: 'plate-ballistic-candidate-a', label: 'Ballistic A' } as CandidateCaseRecord,
  { id: 'plate-ballistic-candidate-b', label: 'Ballistic B' } as CandidateCaseRecord,
]

function stubFetch(response: object): typeof globalThis.fetch {
  return vi.fn(async () => ({
    ok: true,
    status: 200,
    json: async () => response,
  })) as unknown as typeof globalThis.fetch
}

describe('Phase 34 A — non-ballistic comparison renders contextual notice', () => {
  it('hides residual-velocity row when backend reports null/empty ballistic axes', async () => {
    const originalFetch = globalThis.fetch
    globalThis.fetch = stubFetch(NON_BALLISTIC_RESPONSE)
    try {
      render(
        <CaseComparisonPanel
          apiBase="/api/v1"
          cases={CASES}
          caseA="cantilever-beam-candidate"
          caseB="plate-with-hole-candidate"
          onSelectA={() => {}}
          onSelectB={() => {}}
        />,
      )
      await waitFor(() => {
        expect(
          screen.getByTestId('case-comparison-non-ballistic-notice'),
        ).toBeTruthy()
      })
      // The ballistic axis labels must NOT be present in the rendered
      // output for the non-ballistic comparison.
      expect(screen.queryByText('residual velocity')).toBeNull()
      expect(screen.queryByText('perforation marker')).toBeNull()
      expect(screen.queryByText('energy balance error')).toBeNull()
      expect(screen.queryByText('energy audit status')).toBeNull()
    } finally {
      globalThis.fetch = originalFetch
    }
  })

  it('contextual notice text explains the analysis-type semantics', async () => {
    const originalFetch = globalThis.fetch
    globalThis.fetch = stubFetch(NON_BALLISTIC_RESPONSE)
    try {
      render(
        <CaseComparisonPanel
          apiBase="/api/v1"
          cases={CASES}
          caseA="cantilever-beam-candidate"
          caseB="plate-with-hole-candidate"
          onSelectA={() => {}}
          onSelectB={() => {}}
        />,
      )
      await waitFor(() => {
        const notice = screen.getByTestId('case-comparison-non-ballistic-notice')
        expect(notice.textContent).toContain('ballistic-impact analyses')
        expect(notice.textContent).toContain('hidden')
        expect(notice.textContent).toContain('Convergence verdict')
      })
    } finally {
      globalThis.fetch = originalFetch
    }
  })

  it('convergence verdict row remains visible for non-ballistic comparison', async () => {
    const originalFetch = globalThis.fetch
    globalThis.fetch = stubFetch(NON_BALLISTIC_RESPONSE)
    try {
      render(
        <CaseComparisonPanel
          apiBase="/api/v1"
          cases={CASES}
          caseA="cantilever-beam-candidate"
          caseB="plate-with-hole-candidate"
          onSelectA={() => {}}
          onSelectB={() => {}}
        />,
      )
      await waitFor(() => {
        expect(screen.getByText('convergence verdict')).toBeTruthy()
      })
    } finally {
      globalThis.fetch = originalFetch
    }
  })
})

describe('Phase 34 A — ballistic comparison rendering preserved (C:-1 anti-gaming)', () => {
  it('shows residual-velocity row when backend reports real ballistic data', async () => {
    const originalFetch = globalThis.fetch
    globalThis.fetch = stubFetch(BALLISTIC_RESPONSE)
    try {
      render(
        <CaseComparisonPanel
          apiBase="/api/v1"
          cases={CASES}
          caseA="plate-ballistic-candidate-a"
          caseB="plate-ballistic-candidate-b"
          onSelectA={() => {}}
          onSelectB={() => {}}
        />,
      )
      await waitFor(() => {
        expect(screen.getByText('residual velocity')).toBeTruthy()
        expect(screen.getByText('perforation marker')).toBeTruthy()
        expect(screen.getByText('energy balance error')).toBeTruthy()
        expect(screen.getByText('energy audit status')).toBeTruthy()
      })
      // The non-ballistic notice MUST NOT appear for ballistic data.
      expect(
        screen.queryByTestId('case-comparison-non-ballistic-notice'),
      ).toBeNull()
    } finally {
      globalThis.fetch = originalFetch
    }
  })

  it('residual velocity value renders with m/s unit when present', async () => {
    const originalFetch = globalThis.fetch
    globalThis.fetch = stubFetch(BALLISTIC_RESPONSE)
    try {
      render(
        <CaseComparisonPanel
          apiBase="/api/v1"
          cases={CASES}
          caseA="plate-ballistic-candidate-a"
          caseB="plate-ballistic-candidate-b"
          onSelectA={() => {}}
          onSelectB={() => {}}
        />,
      )
      await waitFor(() => {
        expect(screen.getByText('320.5 m/s')).toBeTruthy()
        expect(screen.getByText('318.2 m/s')).toBeTruthy()
      })
    } finally {
      globalThis.fetch = originalFetch
    }
  })
})
