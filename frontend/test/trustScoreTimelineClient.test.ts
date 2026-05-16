// FM-04a Phase 6 D — Trust score timeline client tests.
//
// Tier 1 engineering candidate; not signed validation; not benchmark agreement.

import { strict as assert } from 'node:assert'
import { describe, it } from 'node:test'
import {
  buildSparklinePath,
  parseTrustScoreTimeline,
} from '../src/trustScoreTimelineClient.ts'

describe('parseTrustScoreTimeline', () => {
  it('preserves schemaVersion + formulaVersion + per-axis weighted', () => {
    const parsed = parseTrustScoreTimeline({
      schema_version: '1.0.0',
      formula_version: '1.0.0',
      case_id: 'GS-A-candidate',
      claim_tier: 'Tier 1 engineering candidate',
      claim_boundary: 'tier1_engineering_candidate; not_signed_validation',
      generated_at_utc: '2026-05-16T00:00:00+00:00',
      point_count: 2,
      points: [
        {
          snapshot_label: '2026-05-16T100000Z',
          captured_at_utc: '2026-05-16T10:00:00+00:00',
          trust_score: 70,
          completeness_weighted: 40,
          convergence_weighted: 20,
          energy_audit_weighted: 10,
          reproducibility_weighted: 0,
        },
        {
          snapshot_label: '2026-05-16T200000Z',
          captured_at_utc: '2026-05-16T20:00:00+00:00',
          trust_score: 87,
          completeness_weighted: 45,
          convergence_weighted: 20,
          energy_audit_weighted: 15,
          reproducibility_weighted: 7,
        },
      ],
      claim_impact: 'Tier 1 candidate; not benchmark agreement',
    })
    assert.ok(parsed)
    assert.equal(parsed!.schemaVersion, '1.0.0')
    assert.equal(parsed!.formulaVersion, '1.0.0')
    assert.equal(parsed!.points.length, 2)
    assert.equal(parsed!.points[0].trustScore, 70)
    assert.equal(parsed!.points[1].completenessWeighted, 45)
  })

  it('returns null when case_id is missing', () => {
    assert.equal(parseTrustScoreTimeline({ schema_version: '1.0.0' }), null)
  })

  it('drops points missing snapshot_label', () => {
    const parsed = parseTrustScoreTimeline({
      case_id: 'GS-A',
      points: [
        { snapshot_label: '2026-05-16T100000Z', trust_score: 80 },
        { trust_score: 70 } as never,
      ],
    })
    assert.ok(parsed)
    assert.equal(parsed!.points.length, 1)
  })

  it('handles empty timeline gracefully', () => {
    const parsed = parseTrustScoreTimeline({
      case_id: 'GS-A',
      point_count: 0,
      points: [],
    })
    assert.ok(parsed)
    assert.deepEqual(parsed!.points, [])
  })
})

describe('buildSparklinePath', () => {
  it('returns empty string when there are no points', () => {
    assert.equal(buildSparklinePath([], 100, 50), '')
  })

  it('returns a flat line when there is one point', () => {
    const path = buildSparklinePath(
      [
        {
          snapshotLabel: '2026-05-16T100000Z',
          capturedAtUtc: null,
          trustScore: 80,
          completenessWeighted: 40,
          convergenceWeighted: 20,
          energyAuditWeighted: 15,
          reproducibilityWeighted: 5,
        },
      ],
      100,
      50,
    )
    assert.match(path, /^M 0 \d+\.?\d* L 100 \d+\.?\d*$/)
  })

  it('places trust_score = 100 at top of viewport (y=0)', () => {
    const path = buildSparklinePath(
      [
        {
          snapshotLabel: 'a',
          capturedAtUtc: null,
          trustScore: 100,
          completenessWeighted: 50,
          convergenceWeighted: 20,
          energyAuditWeighted: 15,
          reproducibilityWeighted: 15,
        },
        {
          snapshotLabel: 'b',
          capturedAtUtc: null,
          trustScore: 0,
          completenessWeighted: 0,
          convergenceWeighted: 0,
          energyAuditWeighted: 0,
          reproducibilityWeighted: 0,
        },
      ],
      100,
      50,
    )
    // First point trust=100 -> y = 50 - 50 = 0; second trust=0 -> y = 50
    assert.match(path, /M 0\.00 0\.00 L 100\.00 50\.00/)
  })

  it('returns canonical M+L sequence for >= 2 points', () => {
    const path = buildSparklinePath(
      [
        {
          snapshotLabel: 'a',
          capturedAtUtc: null,
          trustScore: 50,
          completenessWeighted: 25,
          convergenceWeighted: 10,
          energyAuditWeighted: 10,
          reproducibilityWeighted: 5,
        },
        {
          snapshotLabel: 'b',
          capturedAtUtc: null,
          trustScore: 75,
          completenessWeighted: 38,
          convergenceWeighted: 15,
          energyAuditWeighted: 15,
          reproducibilityWeighted: 7,
        },
        {
          snapshotLabel: 'c',
          capturedAtUtc: null,
          trustScore: 90,
          completenessWeighted: 45,
          convergenceWeighted: 20,
          energyAuditWeighted: 15,
          reproducibilityWeighted: 10,
        },
      ],
      100,
      50,
    )
    // M for the first segment, then L for each subsequent
    assert.match(path, /^M /)
    const moveCount = (path.match(/M /g) ?? []).length
    const lineCount = (path.match(/L /g) ?? []).length
    assert.equal(moveCount, 1)
    assert.equal(lineCount, 2)
  })
})
