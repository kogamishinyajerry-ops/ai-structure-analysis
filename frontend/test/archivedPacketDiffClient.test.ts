// FM-04a Phase 4 F — Archived packet diff client tests.
//
// Tier 1 engineering candidate; not signed validation; not benchmark agreement.

import { describe, it } from 'vitest'
import assert from 'node:assert/strict'

import {
  fetchArchivedPacketDiff,
  parseArchivedPacketDiff,
} from '../src/archivedPacketDiffClient.ts'

const SAMPLE_RAW = {
  generated_at_utc: '2026-05-16T03:00:00+00:00',
  claim_boundary: 'tier1_engineering_candidate; not_signed_validation; not_benchmark_agreement',
  archive_a: {
    relpath: 'reports/packet_a.json',
    sha256: 'a'.repeat(64),
    mtime_utc: '2026-05-15T03:00:00+00:00',
    case_id: 'GS-102-phase4d',
    generated_at_utc: '2026-05-15T03:00:00+00:00',
    claim_tier: 'Tier 1 engineering candidate',
    claim_boundary:
      'tier1_engineering_candidate; not_signed_validation; not_benchmark_agreement',
  },
  archive_b: {
    relpath: 'reports/packet_b.json',
    sha256: 'b'.repeat(64),
    mtime_utc: '2026-05-16T03:00:00+00:00',
    case_id: 'GS-102-phase4d',
    generated_at_utc: '2026-05-16T03:00:00+00:00',
    claim_tier: 'Tier 1 engineering candidate',
    claim_boundary:
      'tier1_engineering_candidate; not_signed_validation; not_benchmark_agreement',
  },
  residual_velocity_diff: { a: 75, b: 80, delta: 5, delta_pct: 6.666 },
  perforation_marker_diff: {
    a: 'perforated_candidate',
    b: 'perforated_candidate',
    same_marker: true,
  },
  energy_balance_error_diff: { a: 19, b: 17, delta_abs_pct: 2 },
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
  artifact_hash_diff: {
    a_only: [],
    b_only: [],
    shared: ['deck_engine'],
    hash_changed: [
      { kind: 'deck_starter', a_sha256: 'c'.repeat(64), b_sha256: 'd'.repeat(64) },
    ],
  },
  same_case: true,
  claim_impact:
    'Tier 1 candidate archived-acceptance-packet diff only; not signed validation; ' +
    'not benchmark agreement.',
}

describe('archived packet diff client', () => {
  it('parses a live payload from snake_case to camelCase', () => {
    const parsed = parseArchivedPacketDiff(SAMPLE_RAW)
    assert.ok(parsed)
    assert.equal(parsed!.archiveA.relpath, 'reports/packet_a.json')
    assert.equal(parsed!.archiveB.caseId, 'GS-102-phase4d')
    assert.equal(parsed!.sameCase, true)
    assert.equal(parsed!.residualVelocityDiff.delta, 5)
    assert.ok(
      parsed!.residualVelocityDiff.deltaPct !== null &&
        Math.abs(parsed!.residualVelocityDiff.deltaPct - 6.666) < 1e-6,
    )
    assert.equal(parsed!.energyBalanceErrorDiff.deltaAbsPct, 2)
    assert.equal(parsed!.artifactHashDiff.hashChanged.length, 1)
    assert.equal(parsed!.artifactHashDiff.hashChanged[0].kind, 'deck_starter')
  })

  it('returns null on malformed payload', () => {
    assert.equal(parseArchivedPacketDiff(null), null)
    assert.equal(parseArchivedPacketDiff(undefined), null)
    assert.equal(parseArchivedPacketDiff({} as never), null)
    assert.equal(parseArchivedPacketDiff({ archive_a: {} } as never), null) // missing archive_b
  })

  it('preserves Tier 1 boundary wording in the parsed payload', () => {
    const parsed = parseArchivedPacketDiff(SAMPLE_RAW)
    assert.ok(parsed)
    assert.match(parsed!.claimBoundary, /tier1_engineering_candidate/)
    assert.match(parsed!.claimBoundary, /not_signed_validation/)
    assert.match(parsed!.claimBoundary, /not_benchmark_agreement/)
    assert.match(parsed!.claimImpact, /not signed validation/)
    const stripped = parsed!.claimImpact
      .replace(/not signed validation/g, '')
      .replace(/not benchmark agreement/g, '')
    assert.equal(/validated against/.test(stripped), false)
    assert.equal(/perforation completed/.test(stripped), false)
  })

  it('fetchArchivedPacketDiff falls back when fetch throws', async () => {
    const originalFetch = globalThis.fetch
    // @ts-expect-error force-typed override
    globalThis.fetch = async () => {
      throw new Error('connection refused')
    }
    try {
      const result = await fetchArchivedPacketDiff(
        'http://example.invalid/api/v1',
        'reports/a.json',
        'reports/b.json',
      )
      assert.equal(result.source, 'fallback')
      assert.equal(result.diff, null)
      assert.ok(result.error)
    } finally {
      globalThis.fetch = originalFetch
    }
  })

  it('fetchArchivedPacketDiff parses a 200 OK response', async () => {
    const originalFetch = globalThis.fetch
    // @ts-expect-error force-typed override
    globalThis.fetch = async () => ({
      ok: true,
      status: 200,
      json: async () => SAMPLE_RAW,
    })
    try {
      const result = await fetchArchivedPacketDiff(
        'http://example.invalid/api/v1',
        'reports/a.json',
        'reports/b.json',
      )
      assert.equal(result.source, 'live')
      assert.ok(result.diff)
      assert.equal(result.diff!.archiveA.relpath, 'reports/packet_a.json')
    } finally {
      globalThis.fetch = originalFetch
    }
  })

  it('fetchArchivedPacketDiff falls back on non-2xx', async () => {
    const originalFetch = globalThis.fetch
    // @ts-expect-error force-typed override
    globalThis.fetch = async () => ({ ok: false, status: 400 })
    try {
      const result = await fetchArchivedPacketDiff(
        'http://example.invalid/api/v1',
        'reports/a.json',
        'reports/b.json',
      )
      assert.equal(result.source, 'fallback')
      assert.match(result.error ?? '', /400/)
    } finally {
      globalThis.fetch = originalFetch
    }
  })
})
