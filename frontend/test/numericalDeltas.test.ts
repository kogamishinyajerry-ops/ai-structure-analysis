// FM-04a Phase 6 A — Numerical delta parsing test.
//
// Tier 1 engineering candidate; not signed validation; not benchmark agreement.
//
// The diff parser must surface the new `numerical_deltas` field added
// in schema v1.1.0. Forward-compat: when the field is absent (parsing
// a 1.0.0 payload from an older snapshot diff), the parsed object's
// `numericalDeltas` must be an empty array, not undefined.

import { strict as assert } from 'node:assert'
import { describe, it } from 'vitest'
import { parseCohortSnapshotDiff } from '../src/cohortSnapshotClient.ts'

describe('parseCohortSnapshotDiff — numerical_deltas (Phase 6 A)', () => {
  it('parses residual_velocity + energy_balance pairs into camelCase', () => {
    const parsed = parseCohortSnapshotDiff({
      schema_version: '1.1.0',
      snapshot_a_label: '2026-05-16T100000Z',
      snapshot_b_label: '2026-05-16T200000Z',
      numerical_deltas: [
        {
          case_id: 'GS-A-candidate',
          residual_velocity_m_per_s: { a: 75.0, b: 80.0, delta: 5.0, delta_pct: 6.666667 },
          energy_balance_error_pct: { a: 12.0, b: 8.5, delta: -3.5, delta_abs_pct: 3.5 },
          convergence_combined_verdict: {
            a: 'candidate_observed_stable',
            b: 'candidate_observed_stable',
            same_verdict: true,
          },
          perforation_marker: {
            a: 'candidate_perforation',
            b: 'candidate_perforation',
            same_marker: true,
          },
        },
      ],
    })
    assert.ok(parsed)
    assert.equal(parsed!.numericalDeltas.length, 1)
    const delta = parsed!.numericalDeltas[0]
    assert.equal(delta.caseId, 'GS-A-candidate')
    assert.equal(delta.residualVelocityMPerS.delta, 5.0)
    assert.equal(delta.residualVelocityMPerS.deltaPct, 6.666667)
    assert.equal(delta.energyBalanceErrorPct.deltaAbsPct, 3.5)
    assert.equal(delta.convergenceCombinedVerdict.sameVerdict, true)
    assert.equal(delta.perforationMarker.sameMarker, true)
  })

  it('returns empty numericalDeltas when field is absent (1.0.0 fallback)', () => {
    const parsed = parseCohortSnapshotDiff({
      schema_version: '1.0.0',
      snapshot_a_label: '2026-05-16T100000Z',
      snapshot_b_label: '2026-05-16T200000Z',
    })
    assert.ok(parsed)
    assert.deepEqual(parsed!.numericalDeltas, [])
  })

  it('drops malformed numerical_delta entries (no case_id)', () => {
    const parsed = parseCohortSnapshotDiff({
      schema_version: '1.1.0',
      snapshot_a_label: '2026-05-16T100000Z',
      snapshot_b_label: '2026-05-16T200000Z',
      numerical_deltas: [
        { case_id: 'GS-A-candidate' },
        { residual_velocity_m_per_s: { a: 1, b: 2 } } as never,
      ],
    })
    assert.ok(parsed)
    assert.equal(parsed!.numericalDeltas.length, 1)
  })

  it('surfaces None / null values without crashing', () => {
    const parsed = parseCohortSnapshotDiff({
      schema_version: '1.1.0',
      snapshot_a_label: '2026-05-16T100000Z',
      snapshot_b_label: '2026-05-16T200000Z',
      numerical_deltas: [
        {
          case_id: 'GS-A-candidate',
          residual_velocity_m_per_s: { a: null, b: 80.0, delta: null, delta_pct: null },
        },
      ],
    })
    assert.ok(parsed)
    const delta = parsed!.numericalDeltas[0]
    assert.equal(delta.residualVelocityMPerS.a, null)
    assert.equal(delta.residualVelocityMPerS.b, 80.0)
    assert.equal(delta.residualVelocityMPerS.delta, null)
  })
})
