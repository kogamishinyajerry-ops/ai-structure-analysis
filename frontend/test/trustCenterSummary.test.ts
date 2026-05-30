// FM-04a Phase 2 D — Trust Center summary helper tests.
//
// Tier 1 engineering candidate; not signed validation; not benchmark agreement.

import { describe, it } from 'vitest'
import assert from 'node:assert/strict'

import {
  candidateCaseSelectionLabel,
  candidateCaseSelectionTone,
  convergenceLabel,
  convergenceTone,
  energyBalanceLabel,
  energyBalanceTone,
  TIER1_BANNER,
} from '../src/trustCenterSummary.ts'

describe('energy balance tone', () => {
  it('accent when closed_aggregate and error ≤ 5%', () => {
    const tone = energyBalanceTone({
      status: 'closed_aggregate',
      initialKineticEnergyJ: 1000,
      residualKineticEnergyJ: 800,
      aggregateInternalEnergyJ: 200,
      externalWorkJ: 0,
      energyBalanceErrorPct: 0.5,
      claimImpact: 'Tier 1 closed aggregate energy audit',
    })
    assert.equal(tone, 'accent')
  })

  it('warning when closed_aggregate and 5% < error ≤ 15%', () => {
    const tone = energyBalanceTone({
      status: 'closed_aggregate',
      initialKineticEnergyJ: 1000,
      residualKineticEnergyJ: 850,
      aggregateInternalEnergyJ: 50,
      externalWorkJ: 0,
      energyBalanceErrorPct: 10.0,
      claimImpact: 'Tier 1 closed aggregate energy audit',
    })
    assert.equal(tone, 'warning')
  })

  it('danger when closed_aggregate and error > 15%', () => {
    const tone = energyBalanceTone({
      status: 'closed_aggregate',
      initialKineticEnergyJ: 1000,
      residualKineticEnergyJ: 500,
      aggregateInternalEnergyJ: 200,
      externalWorkJ: 0,
      energyBalanceErrorPct: 30.0,
      claimImpact: 'Tier 1 closed aggregate energy audit',
    })
    assert.equal(tone, 'danger')
  })

  it('warning when partial_candidate', () => {
    const tone = energyBalanceTone({
      status: 'partial_candidate',
      initialKineticEnergyJ: 1731,
      residualKineticEnergyJ: 125,
      aggregateInternalEnergyJ: null,
      externalWorkJ: null,
      energyBalanceErrorPct: null,
      claimImpact: 'Tier 1 partial energy audit',
    })
    assert.equal(tone, 'warning')
  })

  it('muted when status is unavailable', () => {
    const tone = energyBalanceTone({
      status: 'unavailable',
      initialKineticEnergyJ: null,
      residualKineticEnergyJ: null,
      aggregateInternalEnergyJ: null,
      externalWorkJ: null,
      energyBalanceErrorPct: null,
      claimImpact: 'unavailable',
    })
    assert.equal(tone, 'muted')
  })

  it('produces a human label that surfaces balance error percentage', () => {
    const label = energyBalanceLabel({
      status: 'closed_aggregate',
      initialKineticEnergyJ: 1000,
      residualKineticEnergyJ: 800,
      aggregateInternalEnergyJ: 200,
      externalWorkJ: 0,
      energyBalanceErrorPct: 1.234567,
      claimImpact: '',
    })
    assert.match(label, /closed aggregate/)
    assert.match(label, /1\.235%/)
  })
})

describe('convergence tone', () => {
  it('accent when combined verdict is stable', () => {
    const tone = convergenceTone({
      combinedVerdict: 'candidate_observed_stable',
      meshSweepStability: 'candidate_observed_stable',
      dtSweepStability: 'candidate_observed_stable',
      rowCount: 4,
      tolerancePct: 5,
    })
    assert.equal(tone, 'accent')
  })

  it('danger when combined verdict is unstable', () => {
    const tone = convergenceTone({
      combinedVerdict: 'candidate_observed_unstable',
      meshSweepStability: 'candidate_observed_unstable',
      dtSweepStability: 'candidate_observed_stable',
      rowCount: 3,
      tolerancePct: 5,
    })
    assert.equal(tone, 'danger')
  })

  it('warning when combined verdict is insufficient_data', () => {
    const tone = convergenceTone({
      combinedVerdict: 'insufficient_data',
      meshSweepStability: 'unknown',
      dtSweepStability: 'candidate_observed_stable',
      rowCount: 2,
      tolerancePct: 5,
    })
    assert.equal(tone, 'warning')
  })

  it('produces a label summarizing both per-axis verdicts', () => {
    const label = convergenceLabel({
      combinedVerdict: 'candidate_observed_unstable',
      meshSweepStability: 'candidate_observed_unstable',
      dtSweepStability: 'candidate_observed_stable',
      rowCount: 4,
      tolerancePct: 5,
    })
    assert.match(label, /candidate_observed_unstable/)
    assert.match(label, /mesh/)
    assert.match(label, /dt/)
    assert.match(label, /4 row\(s\) at ±5%/)
  })
})

describe('candidate case selection tone', () => {
  it('accent when a live-source case is fully described', () => {
    const tone = candidateCaseSelectionTone({
      caseId: 'GS-102-hifi-candidate',
      starterDeckRelpath: 'golden_samples/GS-102-hifi-candidate/data/model_00_0000.rad',
      engineDeckRelpath: 'golden_samples/GS-102-hifi-candidate/data/model_00_0001.rad',
      generatorScriptRelpath: 'scripts/gen_gs102_hifi_deck.py',
      source: 'live',
    })
    assert.equal(tone, 'accent')
  })

  it('warning when relying on the fallback list', () => {
    const tone = candidateCaseSelectionTone({
      caseId: 'GS-102-hifi-candidate',
      starterDeckRelpath: 'golden_samples/GS-102-hifi-candidate/data/model_00_0000.rad',
      engineDeckRelpath: 'golden_samples/GS-102-hifi-candidate/data/model_00_0001.rad',
      generatorScriptRelpath: 'scripts/gen_gs102_hifi_deck.py',
      source: 'fallback',
    })
    assert.equal(tone, 'warning')
  })

  it('warning when no case is selected', () => {
    const tone = candidateCaseSelectionTone({
      caseId: null,
      starterDeckRelpath: null,
      engineDeckRelpath: null,
      generatorScriptRelpath: null,
      source: 'fallback',
    })
    assert.equal(tone, 'warning')
  })

  it('label surfaces case id and source', () => {
    const label = candidateCaseSelectionLabel({
      caseId: 'GS-102-refined-candidate',
      starterDeckRelpath: 'a',
      engineDeckRelpath: 'b',
      generatorScriptRelpath: 'scripts/gen_gs102_refined_deck.py',
      source: 'live',
    })
    assert.match(label, /GS-102-refined-candidate/)
    assert.match(label, /source live/)
    assert.match(label, /scripts\/gen_gs102_refined_deck\.py/)
  })
})

describe('Tier 1 banner', () => {
  it('always carries the disclaimer trio for downstream cards', () => {
    assert.match(TIER1_BANNER, /Tier 1 engineering candidate/)
    assert.match(TIER1_BANNER, /not signed validation/)
    assert.match(TIER1_BANNER, /not benchmark agreement/)
  })
})
