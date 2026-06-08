// FM-04a Phase 3 C — Acceptance packet client tests.
//
// Tier 1 engineering candidate; not signed validation; not benchmark agreement.

import { describe, it } from 'vitest'
import assert from 'node:assert/strict'

import {
  acceptancePacketDownloadUrl,
  fetchAcceptancePacket,
  parseAcceptancePacket,
} from '../src/acceptancePacketClient.ts'

const SAMPLE_RAW = {
  case_id: 'GS-102-phase3-a',
  generated_at_utc: '2026-05-16T03:00:00+00:00',
  claim_tier: 'Tier 1 engineering candidate',
  claim_boundary:
    'tier1_engineering_candidate; not_signed_validation; not_benchmark_agreement',
  deck_artifacts: [
    {
      relpath: 'project_state/runs/x/data/model_00_0000.rad',
      sha256: 'a'.repeat(64),
      bytes: 123,
      kind: 'deck_starter',
    },
    {
      relpath: 'project_state/runs/x/data/model_00_0001.rad',
      sha256: 'b'.repeat(64),
      bytes: 456,
      kind: 'deck_engine',
    },
  ],
  evidence_artifacts: [
    {
      relpath: 'project_state/graph_executor/x/ballistic/ballistic_metrics.json',
      sha256: 'c'.repeat(64),
      bytes: 789,
      kind: 'ballistic_metrics',
    },
  ],
  visualization_artifacts: [],
  ballistic_metrics_summary: {
    perforation_marker: 'perforated_candidate',
    projectile_initial_velocity_m_per_s: 600.0,
    residual_velocity_candidate_m_per_s: 75.0,
    front_face_crossed: true,
    back_face_crossed: true,
    first_back_face_crossing_t_s: 5e-5,
  },
  energy_audit_summary: {
    status: 'closed_aggregate',
    initial_kinetic_energy_j: 1731.0,
    residual_kinetic_energy_j: 575.5,
    aggregate_internal_energy_j: 826.6,
    external_work_j: 0.0,
    energy_balance_error_pct: 19.0,
    breakdown_status: 'aggregated_into_internal_energy',
    missing_terms: ['plastic_dissipation_j'],
  },
  convergence_study_summary: {
    status: 'available',
    combined_verdict: 'candidate_observed_stable',
    mesh_sweep_stability: 'candidate_observed_stable',
    dt_sweep_stability: 'candidate_observed_stable',
    row_count: 4,
    tolerance_pct: 5.0,
  },
  assumptions: ['demo assumption'],
  limitations: [
    'Not signed validation. Not benchmark agreement. Not perforation completion.',
  ],
  tier2_blockers_remaining: [
    'ADR-024 (full) — locked benchmark case + tolerance + uncertainty interval',
    'sealed packet: SHA freeze + manifest of manifests (FM-04b P8)',
  ],
  claim_impact:
    'Tier 1 candidate acceptance evidence packet only; not signed validation; ' +
    'not benchmark agreement; not a sealed Tier 2 bundle.',
}

describe('acceptance packet client', () => {
  it('parses a live payload from snake_case to camelCase', () => {
    const parsed = parseAcceptancePacket(SAMPLE_RAW)
    assert.ok(parsed)
    assert.equal(parsed!.caseId, 'GS-102-phase3-a')
    assert.equal(parsed!.claimTier, 'Tier 1 engineering candidate')
    assert.match(parsed!.claimBoundary, /not_signed_validation/)
    assert.match(parsed!.claimBoundary, /not_benchmark_agreement/)
    assert.equal(parsed!.deckArtifacts.length, 2)
    assert.equal(parsed!.deckArtifacts[0].kind, 'deck_starter')
    assert.equal(parsed!.ballisticMetricsSummary.residualVelocityCandidateMPerS, 75)
    assert.equal(parsed!.energyAuditSummary.status, 'closed_aggregate')
    assert.equal(parsed!.energyAuditSummary.energyBalanceErrorPct, 19)
    assert.equal(parsed!.convergenceStudySummary.combinedVerdict, 'candidate_observed_stable')
    assert.equal(parsed!.tier2BlockersRemaining.length, 2)
  })

  it('returns null on malformed payload', () => {
    assert.equal(parseAcceptancePacket(null), null)
    assert.equal(parseAcceptancePacket(undefined), null)
    assert.equal(parseAcceptancePacket({} as never), null)
    assert.equal(parseAcceptancePacket({ generated_at_utc: 'x' } as never), null)
  })

  it('preserves Tier 1 boundary wording in the parsed payload', () => {
    const parsed = parseAcceptancePacket(SAMPLE_RAW)
    assert.ok(parsed)
    assert.match(parsed!.claimImpact, /not signed validation/)
    assert.match(parsed!.claimImpact, /not benchmark agreement/)
    assert.match(parsed!.claimImpact, /not a sealed Tier 2 bundle/)
    // Forbidden positive claims must not be present.
    const banned = [
      /validated against/,
      /benchmark agreement(?! is)/i,
      /signed validation(?! is)/i,
      /perforation completed/,
    ]
    for (const re of banned) {
      const matchTarget = parsed!.claimImpact.replace(
        /not signed validation/g,
        '',
      ).replace(/not benchmark agreement/g, '')
      assert.equal(re.test(matchTarget), false, `forbidden wording ${re} leaked: ${parsed!.claimImpact}`)
    }
  })

  it('fetchAcceptancePacket falls back when fetch throws', async () => {
    const originalFetch = globalThis.fetch
    // @ts-expect-error force-typed override for the test
    globalThis.fetch = async () => {
      throw new Error('connection refused')
    }
    try {
      const result = await fetchAcceptancePacket('http://example.invalid/api/v1', 'GS-102-phase3-a')
      assert.equal(result.source, 'fallback')
      assert.equal(result.packet, null)
      assert.ok(result.error)
    } finally {
      globalThis.fetch = originalFetch
    }
  })

  it('fetchAcceptancePacket parses a 200 OK response', async () => {
    const originalFetch = globalThis.fetch
    // @ts-expect-error force-typed override for the test
    globalThis.fetch = async () => ({
      ok: true,
      status: 200,
      text: async () => JSON.stringify(SAMPLE_RAW),
    })
    try {
      const result = await fetchAcceptancePacket('http://example.invalid/api/v1', 'GS-102-phase3-a')
      assert.equal(result.source, 'live')
      assert.ok(result.packet)
      assert.equal(result.packet!.caseId, 'GS-102-phase3-a')
      assert.ok(result.rawJson)
    } finally {
      globalThis.fetch = originalFetch
    }
  })

  it('fetchAcceptancePacket falls back on non-2xx status', async () => {
    const originalFetch = globalThis.fetch
    // @ts-expect-error force-typed override for the test
    globalThis.fetch = async () => ({ ok: false, status: 404 })
    try {
      const result = await fetchAcceptancePacket('http://example.invalid/api/v1', 'missing')
      assert.equal(result.source, 'fallback')
      assert.match(result.error ?? '', /404/)
    } finally {
      globalThis.fetch = originalFetch
    }
  })

  it('acceptancePacketDownloadUrl returns the canonical endpoint URL', () => {
    const url = acceptancePacketDownloadUrl('http://example/api/v1', 'GS-102-phase3-a')
    assert.equal(url, 'http://example/api/v1/acceptance-packet/GS-102-phase3-a')
    // Trailing slash on the base must not produce a double slash.
    const url2 = acceptancePacketDownloadUrl('http://example/api/v1/', 'GS-102-phase3-a')
    assert.equal(url2, 'http://example/api/v1/acceptance-packet/GS-102-phase3-a')
  })
})
