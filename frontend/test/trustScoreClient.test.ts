// FM-04a Phase 6 B — Trust score client tests.
//
// Tier 1 engineering candidate; not signed validation; not benchmark agreement.

import { strict as assert } from 'node:assert'
import { describe, it } from 'vitest'
import {
  TRUST_TONE_ACCENT_THRESHOLD,
  TRUST_TONE_WARNING_THRESHOLD,
  parseTrustScore,
  trustTone,
} from '../src/trustScoreClient.ts'

describe('parseTrustScore', () => {
  it('preserves schemaVersion AND formulaVersion', () => {
    const parsed = parseTrustScore({
      schema_version: '1.0.0',
      formula_version: '1.0.0',
      case_id: 'GS-A-candidate',
      generated_at_utc: '2026-05-16T00:00:00+00:00',
      claim_tier: 'Tier 1 engineering candidate',
      claim_boundary: 'tier1_engineering_candidate; not_signed_validation',
      trust_score: 87,
      trust_score_max: 100,
      breakdown: [
        {
          axis: 'completeness',
          weight: 50,
          raw_score: 90,
          weighted: 45,
          rationale: 'completeness 90/100 normalized; evidence-presence only',
        },
        {
          axis: 'convergence_stability',
          weight: 20,
          raw_score: 100,
          weighted: 20,
          rationale: 'both axes stable',
        },
      ],
      tier2_blockers_remaining: ['FM-04b P8'],
      claim_impact: 'Tier 1 candidate; not benchmark agreement',
    })
    assert.ok(parsed)
    assert.equal(parsed!.schemaVersion, '1.0.0')
    assert.equal(parsed!.formulaVersion, '1.0.0')
    assert.equal(parsed!.trustScore, 87)
    assert.equal(parsed!.trustScoreMax, 100)
    assert.equal(parsed!.breakdown.length, 2)
    assert.equal(parsed!.breakdown[0].axis, 'completeness')
    assert.equal(parsed!.breakdown[0].weighted, 45)
  })

  it('returns null when case_id is missing', () => {
    assert.equal(parseTrustScore({ schema_version: '1.0.0' }), null)
  })

  it('returns null on non-object payloads', () => {
    assert.equal(parseTrustScore(null), null)
    assert.equal(parseTrustScore(undefined), null)
  })

  it('tolerates missing optional fields', () => {
    const parsed = parseTrustScore({ case_id: 'GS-pre-phase6' })
    assert.ok(parsed)
    assert.equal(parsed!.schemaVersion, '')
    assert.equal(parsed!.formulaVersion, '')
    assert.equal(parsed!.trustScore, 0)
    assert.deepEqual(parsed!.breakdown, [])
  })

  it('drops malformed breakdown entries (missing axis name)', () => {
    const parsed = parseTrustScore({
      case_id: 'GS-A',
      breakdown: [
        { axis: 'completeness', weight: 50, raw_score: 90, weighted: 45 },
        { weight: 20 } as never,
      ],
    })
    assert.ok(parsed)
    assert.equal(parsed!.breakdown.length, 1)
  })
})

describe('trustTone', () => {
  it('returns "muted" for null score', () => {
    assert.equal(trustTone(null), 'muted')
  })

  it('returns "accent" at or above the accent threshold (80)', () => {
    assert.equal(TRUST_TONE_ACCENT_THRESHOLD, 80)
    assert.equal(trustTone(80), 'accent')
    assert.equal(trustTone(100), 'accent')
  })

  it('returns "warning" between the two thresholds [50, 80)', () => {
    assert.equal(TRUST_TONE_WARNING_THRESHOLD, 50)
    assert.equal(trustTone(50), 'warning')
    assert.equal(trustTone(79), 'warning')
  })

  it('returns "danger" below the warning threshold', () => {
    assert.equal(trustTone(49), 'danger')
    assert.equal(trustTone(0), 'danger')
  })
})
