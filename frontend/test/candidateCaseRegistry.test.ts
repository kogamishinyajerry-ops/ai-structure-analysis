// FM-04a Phase 2 C — Candidate case registry tests.
//
// Tier 1 engineering candidate; not signed validation; not benchmark agreement.

import { describe, it } from 'node:test'
import assert from 'node:assert/strict'

import {
  FALLBACK_CANDIDATE_CASES,
  fetchCandidateCases,
  findCandidateCase,
  parseCandidateCasesPayload,
} from '../src/candidateCaseRegistry.ts'

describe('candidate case registry', () => {
  it('exposes the three on-disk candidate dirs as a fallback list', () => {
    const ids = FALLBACK_CANDIDATE_CASES.map((c) => c.caseId).sort()
    assert.deepEqual(ids, [
      'GS-102-candidate',
      'GS-102-hifi-candidate',
      'GS-102-refined-candidate',
    ])
    // Every fallback case must carry the Tier 1 boundary; never an unguarded
    // claim of signed validation.
    for (const c of FALLBACK_CANDIDATE_CASES) {
      assert.match(c.claimBoundary, /tier1_engineering_candidate/)
      assert.match(c.claimBoundary, /not_signed_validation/)
      assert.match(c.claimBoundary, /not_benchmark_agreement/)
      assert.equal(c.claimTier, 'Tier 1 engineering candidate')
    }
  })

  it('parses a live payload from snake_case to camelCase', () => {
    const parsed = parseCandidateCasesPayload({
      claim_tier: 'Tier 1 engineering candidate',
      claim_boundary: 'tier1_engineering_candidate; not_signed_validation; not_benchmark_agreement',
      claim_impact: 'Tier 1 candidate-case picker listing only',
      count: 1,
      cases: [
        {
          case_id: 'GS-102-some-candidate',
          claim_tier: 'Tier 1 engineering candidate',
          starter_deck_relpath: 'golden_samples/GS-102-some-candidate/data/model_00_0000.rad',
          engine_deck_relpath: 'golden_samples/GS-102-some-candidate/data/model_00_0001.rad',
          generator_script_relpath: null,
          notes_excerpt: 'fixture notes',
          claim_boundary: 'tier1_engineering_candidate; not_signed_validation; not_benchmark_agreement',
        },
      ],
    })
    assert.ok(parsed)
    assert.equal(parsed!.count, 1)
    assert.equal(parsed!.cases[0].caseId, 'GS-102-some-candidate')
    assert.equal(
      parsed!.cases[0].starterDeckRelpath,
      'golden_samples/GS-102-some-candidate/data/model_00_0000.rad',
    )
  })

  it('returns null when given a malformed payload', () => {
    assert.equal(parseCandidateCasesPayload(null), null)
    assert.equal(parseCandidateCasesPayload(undefined), null)
    assert.equal(parseCandidateCasesPayload({} as never), null)
    assert.equal(parseCandidateCasesPayload({ cases: 'wrong type' } as never), null)
  })

  it('findCandidateCase returns null on missing or unknown id', () => {
    assert.equal(findCandidateCase(FALLBACK_CANDIDATE_CASES, null), null)
    assert.equal(findCandidateCase(FALLBACK_CANDIDATE_CASES, ''), null)
    assert.equal(findCandidateCase(FALLBACK_CANDIDATE_CASES, 'GS-999-candidate'), null)
    const hit = findCandidateCase(FALLBACK_CANDIDATE_CASES, 'GS-102-hifi-candidate')
    assert.ok(hit)
    assert.equal(hit!.generatorScriptRelpath, 'scripts/gen_gs102_hifi_deck.py')
  })

  it('fetchCandidateCases falls back to the static list when fetch fails', async () => {
    const originalFetch = globalThis.fetch
    // @ts-expect-error force-typed override for the test
    globalThis.fetch = async () => {
      throw new Error('connection refused')
    }
    try {
      const result = await fetchCandidateCases('http://example.invalid/api/v1')
      assert.equal(result.source, 'fallback')
      assert.equal(result.cases.length, FALLBACK_CANDIDATE_CASES.length)
      assert.match(result.claimImpact, /Tier 1/)
      assert.match(result.claimImpact, /not signed validation/)
    } finally {
      globalThis.fetch = originalFetch
    }
  })

  it('fetchCandidateCases parses a 200 OK response into the live source', async () => {
    const originalFetch = globalThis.fetch
    // @ts-expect-error force-typed override for the test
    globalThis.fetch = async () => ({
      ok: true,
      status: 200,
      json: async () => ({
        claim_tier: 'Tier 1 engineering candidate',
        claim_boundary: 'tier1_engineering_candidate; not_signed_validation; not_benchmark_agreement',
        claim_impact: 'Tier 1 candidate-case picker listing only',
        count: 2,
        cases: [
          {
            case_id: 'GS-102-candidate',
            claim_tier: 'Tier 1 engineering candidate',
            starter_deck_relpath: 'golden_samples/GS-102-candidate/data/model_00_0000.rad',
            engine_deck_relpath: 'golden_samples/GS-102-candidate/data/model_00_0001.rad',
            generator_script_relpath: null,
            notes_excerpt: 'live notes',
            claim_boundary: 'tier1_engineering_candidate; not_signed_validation; not_benchmark_agreement',
          },
          {
            case_id: 'GS-102-refined-candidate',
            claim_tier: 'Tier 1 engineering candidate',
            starter_deck_relpath: 'golden_samples/GS-102-refined-candidate/data/model_00_0000.rad',
            engine_deck_relpath: 'golden_samples/GS-102-refined-candidate/data/model_00_0001.rad',
            generator_script_relpath: 'scripts/gen_gs102_refined_deck.py',
            notes_excerpt: 'live notes refined',
            claim_boundary: 'tier1_engineering_candidate; not_signed_validation; not_benchmark_agreement',
          },
        ],
      }),
    })
    try {
      const result = await fetchCandidateCases('http://example.invalid/api/v1')
      assert.equal(result.source, 'live')
      assert.equal(result.cases.length, 2)
      assert.equal(result.cases[0].caseId, 'GS-102-candidate')
      assert.equal(result.cases[1].caseId, 'GS-102-refined-candidate')
    } finally {
      globalThis.fetch = originalFetch
    }
  })

  it('fetchCandidateCases falls back when the server returns a non-2xx status', async () => {
    const originalFetch = globalThis.fetch
    // @ts-expect-error force-typed override for the test
    globalThis.fetch = async () => ({ ok: false, status: 500 })
    try {
      const result = await fetchCandidateCases('http://example.invalid/api/v1')
      assert.equal(result.source, 'fallback')
      assert.ok(result.error)
    } finally {
      globalThis.fetch = originalFetch
    }
  })
})
