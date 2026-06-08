// FM-04a Phase 2 C — Candidate case registry tests.
//
// Tier 1 engineering candidate; not signed validation; not benchmark agreement.

import { describe, it } from 'vitest'
import assert from 'node:assert/strict'

import {
  FALLBACK_CANDIDATE_CASES,
  fetchCandidateCases,
  findCandidateCase,
  parseCandidateCasesPayload,
} from '../src/candidateCaseRegistry.ts'

describe('candidate case registry', () => {
  it('exposes every on-disk candidate dir as a fallback list, each honesty-guarded', () => {
    // FM-04a — the fallback cohort grew from the original 3 GS-102 demo
    // decks to the full on-disk `golden_samples/*-candidate/` set as the
    // harness added validated cases. `Phase38H_fallback_cohort_coverage`
    // is the disk-parity drift guard; this exact-set pin is the unit-level
    // mirror (re-run scripts/gen_fallback_candidate_registry.py on drift).
    const ids = FALLBACK_CANDIDATE_CASES.map((c) => c.caseId).sort()
    assert.deepEqual(ids, [
      'GS-102-candidate',
      'GS-102-hifi-candidate',
      'GS-102-refined-candidate',
      'cantilever-beam-candidate',
      'cantilever-beam-modal-candidate',
      'cantilever-beam-modal-l50-candidate',
      'cantilever-buckle-candidate',
      'cantilever-dynamic-candidate',
      'cylinder-pv-candidate',
      'cylinder-pv-collapsed-candidate',
      'cylinder-pv-extended-candidate',
      'euler-column-candidate',
      'heat-transfer-1d-candidate',
      'hertz-contact-candidate',
      'modal-cantilever-candidate',
      'modal-cantilever-stiff-candidate',
      'nafems-le10-thick-plate-candidate',
      'nafems-le11-solid-cyl-temperature-candidate',
      'nafems-le3-hemisphere-shell-candidate',
      'plate-simply-supported-candidate',
      'plate-ss-shell-candidate',
      'plate-with-hole-candidate',
      'rod-wave-impact-candidate',
      'rod-wave-impact-energy-leak-candidate',
      'rod-wave-impact-stiff-candidate',
      'rotating-disk-centrifugal-candidate',
      'wedge-c3d6-candidate',
    ])
    // Anti-overclaim guard. The fallback cohort is a Tier 1 + Tier 2 mix
    // (Tier 2 entries were promoted via a real-solver cross_check_verdict.yaml
    // overlay). EVERY entry — regardless of tier — must explicitly disclaim
    // signed validation and never imply a benchmark/signoff it lacks.
    for (const c of FALLBACK_CANDIDATE_CASES) {
      assert.match(c.claimBoundary, /not_signed_validation/)
      if (c.claimTier === 'Tier 1 engineering candidate') {
        assert.match(c.claimBoundary, /tier1_engineering_candidate/)
        assert.match(c.claimBoundary, /not_benchmark_agreement/)
      } else {
        assert.match(c.claimTier, /Tier 2/)
        assert.match(c.claimBoundary, /tier2_real_solver_validated/)
      }
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
