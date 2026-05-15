// FM-04a Phase 4 E — Cohort overview client tests.
//
// Tier 1 engineering candidate; not signed validation; not benchmark agreement.

import { describe, it } from 'node:test'
import assert from 'node:assert/strict'

import {
  fetchCohortOverview,
  parseCohortOverview,
  scoreTone,
  sortCohortEntries,
} from '../src/cohortOverviewClient.ts'

const SAMPLE_RAW = {
  generated_at_utc: '2026-05-16T03:00:00+00:00',
  claim_tier: 'Tier 1 engineering candidate',
  claim_boundary: 'tier1_engineering_candidate; not_signed_validation; not_benchmark_agreement',
  cohort_count: 3,
  mean_score: 65.0,
  completeness_distribution: { '0-49': 1, '50-79': 1, '80-99': 0, '100': 1 },
  entries: [
    {
      case_id: 'GS-A-candidate',
      completeness_score: 100,
      completeness_score_max: 100,
      perforation_marker: 'perforated_candidate',
      projectile_initial_velocity_m_per_s: 600,
      residual_velocity_candidate_m_per_s: 75,
      energy_balance_error_pct: 19,
      energy_audit_status: 'closed_aggregate',
      convergence_combined_verdict: 'candidate_observed_stable',
      last_modified_utc: '2026-05-16T03:00:00+00:00',
      missing_evidence_count: 0,
    },
    {
      case_id: 'GS-B-candidate',
      completeness_score: 30,
      completeness_score_max: 100,
      perforation_marker: null,
      projectile_initial_velocity_m_per_s: null,
      residual_velocity_candidate_m_per_s: null,
      energy_balance_error_pct: null,
      energy_audit_status: 'unavailable',
      convergence_combined_verdict: 'insufficient_data',
      last_modified_utc: '2026-05-15T03:00:00+00:00',
      missing_evidence_count: 5,
    },
    {
      case_id: 'GS-C-candidate',
      completeness_score: 65,
      completeness_score_max: 100,
      perforation_marker: 'perforated_candidate',
      projectile_initial_velocity_m_per_s: 600,
      residual_velocity_candidate_m_per_s: 75,
      energy_balance_error_pct: 19,
      energy_audit_status: 'closed_aggregate',
      convergence_combined_verdict: 'insufficient_data',
      last_modified_utc: '2026-05-14T03:00:00+00:00',
      missing_evidence_count: 2,
    },
  ],
  tier2_blockers_remaining: [
    'ADR-024 (full) — locked benchmark case + tolerance + uncertainty interval',
  ],
  claim_impact:
    'Tier 1 candidate cohort overview only; not signed validation; not ' +
    'benchmark agreement; not a cohort-level validation report.',
}

describe('cohort overview client', () => {
  it('parses a live payload from snake_case to camelCase', () => {
    const parsed = parseCohortOverview(SAMPLE_RAW)
    assert.ok(parsed)
    assert.equal(parsed!.cohortCount, 3)
    assert.equal(parsed!.meanScore, 65)
    assert.equal(parsed!.entries.length, 3)
    assert.equal(parsed!.entries[0].caseId, 'GS-A-candidate')
    assert.equal(parsed!.entries[0].completenessScore, 100)
    assert.equal(parsed!.completenessDistribution['100'], 1)
  })

  it('returns null on malformed payload', () => {
    assert.equal(parseCohortOverview(null), null)
    assert.equal(parseCohortOverview(undefined), null)
    assert.equal(parseCohortOverview({ entries: 'wrong type' } as never), null)
  })

  it('parses an empty cohort', () => {
    const parsed = parseCohortOverview({
      cohort_count: 0,
      mean_score: null,
      entries: [],
      completeness_distribution: { '0-49': 0, '50-79': 0, '80-99': 0, '100': 0 },
    })
    assert.ok(parsed)
    assert.equal(parsed!.cohortCount, 0)
    assert.equal(parsed!.meanScore, null)
    assert.equal(parsed!.entries.length, 0)
  })

  it('preserves Tier 1 boundary wording in the parsed payload', () => {
    const parsed = parseCohortOverview(SAMPLE_RAW)
    assert.ok(parsed)
    assert.match(parsed!.claimBoundary, /tier1_engineering_candidate/)
    assert.match(parsed!.claimBoundary, /not_signed_validation/)
    assert.match(parsed!.claimBoundary, /not_benchmark_agreement/)
    assert.match(parsed!.claimImpact, /not signed validation/)
    assert.match(parsed!.claimImpact, /not benchmark agreement/)
    // Forbidden positive-claim audit on the rendered payload.
    const stripped = parsed!.claimImpact
      .replace(/not signed validation/g, '')
      .replace(/not benchmark agreement/g, '')
    assert.equal(/validated against/.test(stripped), false)
    assert.equal(/perforation completed/.test(stripped), false)
  })

  it('fetchCohortOverview falls back when fetch throws', async () => {
    const originalFetch = globalThis.fetch
    // @ts-expect-error force-typed override
    globalThis.fetch = async () => {
      throw new Error('connection refused')
    }
    try {
      const result = await fetchCohortOverview('http://example.invalid/api/v1')
      assert.equal(result.source, 'fallback')
      assert.equal(result.overview, null)
      assert.ok(result.error)
    } finally {
      globalThis.fetch = originalFetch
    }
  })

  it('fetchCohortOverview parses a 200 OK response', async () => {
    const originalFetch = globalThis.fetch
    // @ts-expect-error force-typed override
    globalThis.fetch = async () => ({
      ok: true,
      status: 200,
      json: async () => SAMPLE_RAW,
    })
    try {
      const result = await fetchCohortOverview('http://example.invalid/api/v1')
      assert.equal(result.source, 'live')
      assert.ok(result.overview)
      assert.equal(result.overview!.cohortCount, 3)
    } finally {
      globalThis.fetch = originalFetch
    }
  })

  it('fetchCohortOverview falls back on non-2xx', async () => {
    const originalFetch = globalThis.fetch
    // @ts-expect-error force-typed override
    globalThis.fetch = async () => ({ ok: false, status: 503 })
    try {
      const result = await fetchCohortOverview('http://example.invalid/api/v1')
      assert.equal(result.source, 'fallback')
      assert.match(result.error ?? '', /503/)
    } finally {
      globalThis.fetch = originalFetch
    }
  })

  it('scoreTone selects bands correctly', () => {
    assert.equal(scoreTone(0), 'muted')
    assert.equal(scoreTone(49), 'danger')
    assert.equal(scoreTone(50), 'warning')
    assert.equal(scoreTone(79), 'warning')
    assert.equal(scoreTone(80), 'accent')
    assert.equal(scoreTone(100), 'accent')
  })

  it('sortCohortEntries orders by score_desc', () => {
    const parsed = parseCohortOverview(SAMPLE_RAW)
    assert.ok(parsed)
    const sorted = sortCohortEntries(parsed!.entries, 'score_desc')
    assert.deepEqual(
      sorted.map((e) => e.caseId),
      ['GS-A-candidate', 'GS-C-candidate', 'GS-B-candidate'],
    )
  })

  it('sortCohortEntries orders by score_asc', () => {
    const parsed = parseCohortOverview(SAMPLE_RAW)
    assert.ok(parsed)
    const sorted = sortCohortEntries(parsed!.entries, 'score_asc')
    assert.deepEqual(
      sorted.map((e) => e.caseId),
      ['GS-B-candidate', 'GS-C-candidate', 'GS-A-candidate'],
    )
  })

  it('sortCohortEntries orders by case_id_asc (default-ish)', () => {
    const parsed = parseCohortOverview(SAMPLE_RAW)
    assert.ok(parsed)
    const sorted = sortCohortEntries(parsed!.entries, 'case_id_asc')
    assert.deepEqual(
      sorted.map((e) => e.caseId),
      ['GS-A-candidate', 'GS-B-candidate', 'GS-C-candidate'],
    )
  })

  it('sortCohortEntries orders by recency_desc (most-recent first)', () => {
    const parsed = parseCohortOverview(SAMPLE_RAW)
    assert.ok(parsed)
    const sorted = sortCohortEntries(parsed!.entries, 'recency_desc')
    // 2026-05-16 > 2026-05-15 > 2026-05-14
    assert.deepEqual(
      sorted.map((e) => e.caseId),
      ['GS-A-candidate', 'GS-B-candidate', 'GS-C-candidate'],
    )
  })
})
