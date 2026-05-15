// FM-04a Phase 4 E — Case completeness client tests.
//
// Tier 1 engineering candidate; not signed validation; not benchmark agreement.

import { describe, it } from 'node:test'
import assert from 'node:assert/strict'

import {
  fetchCaseCompleteness,
  parseCaseCompletenessScore,
} from '../src/caseCompletenessClient.ts'

const SAMPLE_RAW = {
  case_id: 'GS-102-phase4e',
  generated_at_utc: '2026-05-16T03:00:00+00:00',
  claim_tier: 'Tier 1 engineering candidate',
  claim_boundary: 'tier1_engineering_candidate; not_signed_validation; not_benchmark_agreement',
  score: 65,
  score_max: 100,
  breakdown: [
    {
      label: 'starter_deck',
      points_awarded: 15,
      points_max: 15,
      evidence_status: 'present',
    },
    {
      label: 'energy_audit',
      points_awarded: 10,
      points_max: 15,
      evidence_status: 'partial_candidate',
      notes: 'KE-only audit; per-term split blocked on /TH/PART cards.',
    },
    {
      label: 'convergence_study',
      points_awarded: 0,
      points_max: 15,
      evidence_status: 'absent',
    },
  ],
  missing_evidence: ['convergence_study', 'energy_audit_closed_aggregate'],
  tier2_blockers_remaining: [
    'ADR-024 (full) — locked benchmark case + tolerance + uncertainty interval',
    'sealed packet: SHA freeze + manifest of manifests (FM-04b P8)',
  ],
  claim_impact:
    'Tier 1 candidate evidence-presence score only; not signed validation; ' +
    'not benchmark agreement; not a measure of validation quality. Even a ' +
    '100/100 score does NOT authorize promotion to Tier 2.',
}

describe('case completeness client', () => {
  it('parses a live payload from snake_case to camelCase', () => {
    const parsed = parseCaseCompletenessScore(SAMPLE_RAW)
    assert.ok(parsed)
    assert.equal(parsed!.caseId, 'GS-102-phase4e')
    assert.equal(parsed!.score, 65)
    assert.equal(parsed!.scoreMax, 100)
    assert.equal(parsed!.breakdown.length, 3)
    assert.equal(parsed!.breakdown[0].label, 'starter_deck')
    assert.equal(parsed!.breakdown[1].notes, 'KE-only audit; per-term split blocked on /TH/PART cards.')
    assert.deepEqual(parsed!.missingEvidence, [
      'convergence_study',
      'energy_audit_closed_aggregate',
    ])
    assert.equal(parsed!.tier2BlockersRemaining.length, 2)
  })

  it('returns null on malformed payload', () => {
    assert.equal(parseCaseCompletenessScore(null), null)
    assert.equal(parseCaseCompletenessScore(undefined), null)
    assert.equal(parseCaseCompletenessScore({} as never), null)
    assert.equal(parseCaseCompletenessScore({ score: 100 } as never), null)
  })

  it('preserves Tier 1 boundary wording in the parsed payload', () => {
    const parsed = parseCaseCompletenessScore(SAMPLE_RAW)
    assert.ok(parsed)
    assert.match(parsed!.claimBoundary, /tier1_engineering_candidate/)
    assert.match(parsed!.claimBoundary, /not_signed_validation/)
    assert.match(parsed!.claimBoundary, /not_benchmark_agreement/)
    assert.match(parsed!.claimImpact, /even a 100\/100 score does not authorize promotion to tier 2/i)
    const stripped = parsed!.claimImpact
      .replace(/not signed validation/g, '')
      .replace(/not benchmark agreement/g, '')
    assert.equal(/validated against/.test(stripped), false)
    assert.equal(/perforation completed/.test(stripped), false)
  })

  it('fetchCaseCompleteness falls back when fetch throws', async () => {
    const originalFetch = globalThis.fetch
    // @ts-expect-error force-typed override
    globalThis.fetch = async () => {
      throw new Error('connection refused')
    }
    try {
      const result = await fetchCaseCompleteness(
        'http://example.invalid/api/v1',
        'GS-102-phase4e',
      )
      assert.equal(result.source, 'fallback')
      assert.equal(result.score, null)
      assert.ok(result.error)
    } finally {
      globalThis.fetch = originalFetch
    }
  })

  it('fetchCaseCompleteness parses a 200 OK response', async () => {
    const originalFetch = globalThis.fetch
    // @ts-expect-error force-typed override
    globalThis.fetch = async () => ({
      ok: true,
      status: 200,
      json: async () => SAMPLE_RAW,
    })
    try {
      const result = await fetchCaseCompleteness(
        'http://example.invalid/api/v1',
        'GS-102-phase4e',
      )
      assert.equal(result.source, 'live')
      assert.ok(result.score)
      assert.equal(result.score!.score, 65)
    } finally {
      globalThis.fetch = originalFetch
    }
  })

  it('fetchCaseCompleteness falls back on non-2xx', async () => {
    const originalFetch = globalThis.fetch
    // @ts-expect-error force-typed override
    globalThis.fetch = async () => ({ ok: false, status: 400 })
    try {
      const result = await fetchCaseCompleteness('http://example.invalid/api/v1', 'x')
      assert.equal(result.source, 'fallback')
      assert.match(result.error ?? '', /400/)
    } finally {
      globalThis.fetch = originalFetch
    }
  })
})
