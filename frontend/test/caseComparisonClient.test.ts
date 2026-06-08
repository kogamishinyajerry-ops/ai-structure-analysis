// FM-04a Phase 3 C — Case comparison client tests.
//
// Tier 1 engineering candidate; not signed validation; not benchmark agreement.

import { describe, it } from 'vitest'
import assert from 'node:assert/strict'

import {
  absoluteDeltaTone,
  fetchCaseComparison,
  numericDeltaTone,
  parseCaseComparison,
} from '../src/caseComparisonClient.ts'

const SAMPLE_RAW = {
  case_a: 'GS-102-phase3-a',
  case_b: 'GS-102-phase3-b',
  generated_at_utc: '2026-05-16T03:00:00+00:00',
  claim_boundary:
    'tier1_engineering_candidate; not_signed_validation; not_benchmark_agreement',
  residual_velocity_diff: { a: 75, b: 85, delta: 10, delta_pct: 13.333 },
  perforation_marker_diff: {
    a: 'perforated_candidate',
    b: 'perforated_candidate',
    same_marker: true,
  },
  energy_balance_error_diff: { a: 19, b: 11, delta_abs_pct: 8 },
  energy_audit_status_diff: {
    a: 'closed_aggregate',
    b: 'closed_aggregate',
    both_closed: true,
    same_status: true,
  },
  convergence_verdict_diff: {
    a: 'candidate_observed_stable',
    b: 'candidate_observed_stable',
    same_verdict: true,
  },
  deck_artifact_diff: {
    a_only: [],
    b_only: [],
    shared: ['deck_starter', 'deck_engine'],
    hash_changed: [],
  },
  evidence_artifact_diff: {
    a_only: ['convergence_study'],
    b_only: [],
    shared: [],
    hash_changed: [
      {
        kind: 'ballistic_metrics',
        a_sha256: 'a'.repeat(64),
        b_sha256: 'b'.repeat(64),
      },
    ],
  },
  claim_impact:
    'Tier 1 candidate case-vs-case comparison only; not signed validation; ' +
    'not benchmark agreement; not a comparison against experimental data.',
}

describe('case comparison client', () => {
  it('parses a live payload from snake_case to camelCase', () => {
    const parsed = parseCaseComparison(SAMPLE_RAW)
    assert.ok(parsed)
    assert.equal(parsed!.caseA, 'GS-102-phase3-a')
    assert.equal(parsed!.caseB, 'GS-102-phase3-b')
    assert.equal(parsed!.residualVelocityDiff.delta, 10)
    assert.ok(
      parsed!.residualVelocityDiff.deltaPct !== null &&
        Math.abs(parsed!.residualVelocityDiff.deltaPct - 13.333) < 1e-6,
    )
    assert.equal(parsed!.energyBalanceErrorDiff.deltaAbsPct, 8)
    assert.equal(parsed!.perforationMarkerDiff.sameMarker, true)
    assert.equal(parsed!.energyAuditStatusDiff.bothClosed, true)
    assert.equal(parsed!.convergenceVerdictDiff.sameVerdict, true)
    assert.equal(parsed!.deckArtifactDiff.shared.length, 2)
    assert.equal(parsed!.evidenceArtifactDiff.aOnly[0], 'convergence_study')
    assert.equal(parsed!.evidenceArtifactDiff.hashChanged[0].kind, 'ballistic_metrics')
  })

  it('returns null on malformed payload', () => {
    assert.equal(parseCaseComparison(null), null)
    assert.equal(parseCaseComparison(undefined), null)
    assert.equal(parseCaseComparison({} as never), null)
    assert.equal(parseCaseComparison({ case_a: 'x' } as never), null)
  })

  it('preserves Tier 1 boundary wording in the parsed payload', () => {
    const parsed = parseCaseComparison(SAMPLE_RAW)
    assert.ok(parsed)
    assert.match(parsed!.claimImpact, /case-vs-case/)
    assert.match(parsed!.claimImpact, /not signed validation/)
    assert.match(parsed!.claimImpact, /not benchmark agreement/)
    // Forbidden positive claims absent.
    const stripped = parsed!.claimImpact
      .replace(/not signed validation/g, '')
      .replace(/not benchmark agreement/g, '')
    assert.equal(/validated against/.test(stripped), false)
    assert.equal(/perforation completed/.test(stripped), false)
  })

  it('fetchCaseComparison falls back when fetch throws', async () => {
    const originalFetch = globalThis.fetch
    // @ts-expect-error force-typed override for the test
    globalThis.fetch = async () => {
      throw new Error('connection refused')
    }
    try {
      const result = await fetchCaseComparison(
        'http://example.invalid/api/v1',
        'GS-102-phase3-a',
        'GS-102-phase3-b',
      )
      assert.equal(result.source, 'fallback')
      assert.equal(result.comparison, null)
      assert.ok(result.error)
    } finally {
      globalThis.fetch = originalFetch
    }
  })

  it('fetchCaseComparison parses a 200 OK response', async () => {
    const originalFetch = globalThis.fetch
    // @ts-expect-error force-typed override for the test
    globalThis.fetch = async () => ({
      ok: true,
      status: 200,
      json: async () => SAMPLE_RAW,
    })
    try {
      const result = await fetchCaseComparison(
        'http://example.invalid/api/v1',
        'GS-102-phase3-a',
        'GS-102-phase3-b',
      )
      assert.equal(result.source, 'live')
      assert.ok(result.comparison)
      assert.equal(result.comparison!.caseA, 'GS-102-phase3-a')
      assert.equal(result.comparison!.caseB, 'GS-102-phase3-b')
    } finally {
      globalThis.fetch = originalFetch
    }
  })

  it('fetchCaseComparison falls back on non-2xx status', async () => {
    const originalFetch = globalThis.fetch
    // @ts-expect-error force-typed override for the test
    globalThis.fetch = async () => ({ ok: false, status: 400 })
    try {
      const result = await fetchCaseComparison(
        'http://example.invalid/api/v1',
        'x',
        'y',
      )
      assert.equal(result.source, 'fallback')
      assert.match(result.error ?? '', /400/)
    } finally {
      globalThis.fetch = originalFetch
    }
  })

  it('numericDeltaTone selects accent / warning / danger by deltaPct band', () => {
    assert.equal(numericDeltaTone({ a: 100, b: 102, delta: 2, deltaPct: 2 }), 'accent')
    assert.equal(numericDeltaTone({ a: 100, b: 110, delta: 10, deltaPct: 10 }), 'warning')
    assert.equal(numericDeltaTone({ a: 100, b: 130, delta: 30, deltaPct: 30 }), 'danger')
    assert.equal(numericDeltaTone({ a: null, b: null, delta: null, deltaPct: null }), 'muted')
  })

  it('absoluteDeltaTone selects bands by deltaAbsPct', () => {
    assert.equal(absoluteDeltaTone({ a: 19, b: 18, deltaAbsPct: 1 }), 'accent')
    assert.equal(absoluteDeltaTone({ a: 19, b: 11, deltaAbsPct: 8 }), 'warning')
    assert.equal(absoluteDeltaTone({ a: 19, b: 0, deltaAbsPct: 19 }), 'danger')
    assert.equal(absoluteDeltaTone({ a: null, b: null, deltaAbsPct: null }), 'muted')
  })
})
