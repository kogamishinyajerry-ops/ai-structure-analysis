// FM-04a Phase 3 D — Convergence study client tests.
//
// Tier 1 engineering candidate; not signed validation; not benchmark agreement.

import { describe, it } from 'node:test'
import assert from 'node:assert/strict'

import {
  axisTone,
  combinedVerdictLabel,
  combinedVerdictTone,
  fetchConvergenceStudy,
  parseConvergenceStudy,
  rowDeviationTone,
} from '../src/convergenceStudyClient.ts'

const SAMPLE_RAW = {
  case_id: 'GS-102-phase3-d',
  study_metric: 'residual_velocity_m_per_s',
  tolerance_pct: 5.0,
  combined_verdict: 'candidate_observed_stable',
  row_count: 4,
  mesh_sweep: {
    axis: 'mesh_level',
    axis_label: 'mesh_level',
    held_dt_label: 'dt_default',
    held_dt_axis_value: 1e-6,
    run_count: 2,
    relative_change_pct: 0.05,
    candidate_stability: 'candidate_observed_stable',
    runs: [
      { label: 'coarse', mesh_axis_value: 1, metric_value: 75.0 },
      { label: 'fine', mesh_axis_value: 2, metric_value: 75.05 },
    ],
  },
  dt_sweep: {
    axis: 'time_step_dt_s',
    axis_label: 'time_step_dt_s',
    held_mesh_label: 'mesh_coarse',
    held_mesh_axis_value: 1,
    run_count: 2,
    relative_change_pct: 0.02,
    candidate_stability: 'candidate_observed_stable',
    runs: [
      { label: 'dt_default', dt_axis_value: 1e-6, metric_value: 75.0 },
      { label: 'dt_half', dt_axis_value: 5e-7, metric_value: 75.02 },
    ],
  },
  claim_boundary:
    'tier1_engineering_candidate; not_signed_validation; not_benchmark_agreement',
  claim_impact:
    'Tier 1 candidate mesh and time-step convergence study only; not signed ' +
    'validation; not benchmark agreement; tolerance 5% applied to ' +
    '`residual_velocity_m_per_s` across each 1-axis sweep',
  energy_balance_observation: {
    status: 'candidate_observed',
    rows_with_balance_error: 4,
    rows_total: 4,
    min_pct: 18.5,
    max_pct: 19.5,
    mean_pct: 19.0,
  },
}

describe('convergence study client', () => {
  it('parses an orchestrator payload from snake_case to camelCase', () => {
    const parsed = parseConvergenceStudy(SAMPLE_RAW)
    assert.ok(parsed)
    assert.equal(parsed!.caseId, 'GS-102-phase3-d')
    assert.equal(parsed!.studyMetric, 'residual_velocity_m_per_s')
    assert.equal(parsed!.combinedVerdict, 'candidate_observed_stable')
    assert.equal(parsed!.tolerancePct, 5)
    assert.equal(parsed!.meshSweep.runs.length, 2)
    assert.equal(parsed!.meshSweep.runs[0].label, 'coarse')
    assert.equal(parsed!.meshSweep.runs[0].axisValue, 1)
    assert.equal(parsed!.meshSweep.runs[0].metricValue, 75.0)
    assert.equal(parsed!.dtSweep.runs[1].axisValue, 5e-7)
    assert.equal(parsed!.energyBalanceObservation.status, 'candidate_observed')
    assert.equal(parsed!.energyBalanceObservation.meanPct, 19.0)
  })

  it('returns null on malformed payload', () => {
    assert.equal(parseConvergenceStudy(null), null)
    assert.equal(parseConvergenceStudy(undefined), null)
    assert.equal(parseConvergenceStudy({} as never), null)
    assert.equal(parseConvergenceStudy({ combined_verdict: 'x' } as never), null)
  })

  it('preserves Tier 1 boundary wording in claim_impact', () => {
    const parsed = parseConvergenceStudy(SAMPLE_RAW)
    assert.ok(parsed)
    assert.match(parsed!.claimImpact, /not signed validation/)
    assert.match(parsed!.claimImpact, /not benchmark agreement/)
    // Forbidden positive claims absent (after stripping disclaimers).
    const stripped = parsed!.claimImpact
      .replace(/not signed validation/g, '')
      .replace(/not benchmark agreement/g, '')
    assert.equal(/validated against/.test(stripped), false)
    assert.equal(/benchmark agreement/.test(stripped), false)
    assert.equal(/signed validation/.test(stripped), false)
    assert.equal(/perforation completed/.test(stripped), false)
  })

  it('fetchConvergenceStudy falls back when fetch throws', async () => {
    const originalFetch = globalThis.fetch
    // @ts-expect-error force-typed override
    globalThis.fetch = async () => {
      throw new Error('connection refused')
    }
    try {
      const result = await fetchConvergenceStudy(
        'http://example.invalid/api/v1',
        'GS-102-phase3-d',
      )
      assert.equal(result.source, 'fallback')
      assert.equal(result.study, null)
      assert.ok(result.error)
    } finally {
      globalThis.fetch = originalFetch
    }
  })

  it('fetchConvergenceStudy parses a 200 OK response', async () => {
    const originalFetch = globalThis.fetch
    // @ts-expect-error force-typed override
    globalThis.fetch = async () => ({
      ok: true,
      status: 200,
      json: async () => SAMPLE_RAW,
    })
    try {
      const result = await fetchConvergenceStudy(
        'http://example.invalid/api/v1',
        'GS-102-phase3-d',
      )
      assert.equal(result.source, 'live')
      assert.ok(result.study)
      assert.equal(result.study!.caseId, 'GS-102-phase3-d')
    } finally {
      globalThis.fetch = originalFetch
    }
  })

  it('fetchConvergenceStudy falls back on non-2xx status', async () => {
    const originalFetch = globalThis.fetch
    // @ts-expect-error force-typed override
    globalThis.fetch = async () => ({ ok: false, status: 404 })
    try {
      const result = await fetchConvergenceStudy(
        'http://example.invalid/api/v1',
        'missing',
      )
      assert.equal(result.source, 'fallback')
      assert.match(result.error ?? '', /404/)
    } finally {
      globalThis.fetch = originalFetch
    }
  })

  it('axisTone routes stability through trustCenterSummary.convergenceTone', () => {
    assert.equal(axisTone('candidate_observed_stable'), 'accent')
    assert.equal(axisTone('candidate_observed_unstable'), 'danger')
    assert.equal(axisTone('insufficient_data'), 'warning')
    assert.equal(axisTone('unknown'), 'warning')
  })

  it('combinedVerdictTone reflects the combined verdict', () => {
    const parsed = parseConvergenceStudy(SAMPLE_RAW)
    assert.ok(parsed)
    assert.equal(combinedVerdictTone(parsed!), 'accent')
  })

  it('combinedVerdictLabel formats the verdict + axes + row count', () => {
    const parsed = parseConvergenceStudy(SAMPLE_RAW)
    assert.ok(parsed)
    const label = combinedVerdictLabel(parsed!)
    assert.match(label, /candidate_observed_stable/)
    assert.match(label, /mesh candidate_observed_stable/)
    assert.match(label, /dt candidate_observed_stable/)
    assert.match(label, /4 row\(s\) at ±5%/)
  })

  it('rowDeviationTone selects accent / warning / danger by deviation band', () => {
    // 75.0 reference, run = 75.0001 → 0.000133% deviation → accent (≤ 0.01%)
    assert.equal(rowDeviationTone(75.0, 75.0001, 5), 'accent')
    // 75.0 reference, run = 80 → 6.67% deviation → warning (≤ 15%)
    assert.equal(rowDeviationTone(75.0, 80.0, 5), 'warning')
    // 75.0 reference, run = 100 → 33% deviation → danger
    assert.equal(rowDeviationTone(75.0, 100.0, 5), 'danger')
    // zero reference → muted
    assert.equal(rowDeviationTone(0, 1, 5), 'muted')
  })
})
