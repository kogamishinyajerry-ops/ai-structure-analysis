// FM-04a Phase 28 B — Ballistic candidate section extraction tests.
//
// Completes the Phase 26 D extraction arc: 6 of 7 sections were
// extracted by end of Phase 27 B; Ballistic was the final inline
// section. Phase 28 B extracts it.
//
// Honest LOC record:
//   - App.tsx pre-Phase-28-B:  1454 LOC
//   - App.tsx post-Phase-28-B: 1455 LOC (+1, essentially flat)
//
// Ballistic's context interface is WIDER than Blueprint's (12
// fields vs 2) — the call-site verbosity offsets the inline literal
// removal. Phase 27 B's lesson ("narrow context = real LOC win")
// holds; extracting Ballistic was always going to be ~flat on LOC.
// The value is in test isolation + humanizeStatus dedup, not in
// App.tsx shrinking.
//
// Anti-gaming guard D:-3 — purity (no ctx mutation). Re-pinned here.
//
// Tier 1 / Tier 2 engineering candidate; not signed validation;
// not benchmark agreement.

import { describe, expect, it } from 'vitest'

import {
  buildBallisticSection,
  humanizeStatus,
} from '../src/state/trustCenterViewModel'

function makeCtx(overrides?: Partial<Parameters<typeof buildBallisticSection>[0]>) {
  return {
    icon: 'ballistic-icon',
    candidateBallistic: {
      status: 'candidate_observed',
      claim_impact: 'Tier 1 candidate ballistic block',
      projectile_initial_velocity: { status: 'declared' },
      residual_velocity_candidate: { status: 'candidate_observed' },
      energy_balance_candidate: { claim_impact: 'energy balance is Tier 1' },
      animation_manifest: { status: 'available' },
    },
    ballisticInitialVelocitySummary: '850 m/s',
    ballisticResidualVelocitySummary: '120 m/s (candidate)',
    ballisticPerforationSummary: 'perforated_candidate',
    ballisticPerforationTone: 'warning' as const,
    ballisticEnergySummary: 'KE_residual / KE_initial = 0.020',
    ballisticEnergyTone: 'warning' as const,
    ballisticAnimationSummary: 'available · 12 frames',
    ballisticTimeStepStudySummary: 'Not surfaced',
    ballisticTimeStepStudyTone: 'muted' as const,
    ballisticTimeStepStudy: null,
    ballisticTier2BlockerSummary: '5 blockers',
    ...overrides,
  }
}

describe('Phase 28 B — humanizeStatus helper', () => {
  it('undefined → "Unknown"', () => {
    expect(humanizeStatus(undefined)).toBe('Unknown')
  })
  it('snake_case → Title Case', () => {
    expect(humanizeStatus('candidate_observed')).toBe('Candidate Observed')
    expect(humanizeStatus('perforated_candidate')).toBe('Perforated Candidate')
  })
  it('single word capitalizes', () => {
    expect(humanizeStatus('passed')).toBe('Passed')
  })
})

describe('Phase 28 B — buildBallisticSection', () => {
  it('emits 8 items with correct title and icon passthrough', () => {
    const section = buildBallisticSection(makeCtx())
    expect(section.title).toBe('Ballistic candidate')
    expect(section.icon).toBe('ballistic-icon')
    expect(section.items).toHaveLength(8)
    expect(section.items.map((i) => i.label)).toEqual([
      'Ballistic block',
      'Initial velocity',
      'Residual velocity',
      'Perforation marker',
      'Energy balance',
      'Animation manifest',
      'Time-step convergence',
      'Ballistic Tier 2 blockers',
    ])
  })

  it('Ballistic block humanizes the status', () => {
    const section = buildBallisticSection(makeCtx())
    const row = section.items.find((i) => i.label === 'Ballistic block')!
    expect(row.value).toBe('Candidate Observed')
    expect(row.tone).toBe('warning')
    expect(row.detail).toContain('Tier 1')
  })

  it('Ballistic block falls back when candidateBallistic is null', () => {
    const section = buildBallisticSection(
      makeCtx({ candidateBallistic: null }),
    )
    const row = section.items.find((i) => i.label === 'Ballistic block')!
    expect(row.value).toBe('Not surfaced')
    expect(row.tone).toBe('muted')
    expect(row.detail).toContain('not signed validation')
  })

  it('Initial velocity tone is accent when declared', () => {
    const section = buildBallisticSection(makeCtx())
    const row = section.items.find((i) => i.label === 'Initial velocity')!
    expect(row.value).toBe('850 m/s')
    expect(row.tone).toBe('accent')
  })

  it('Initial velocity tone is muted when candidateBallistic is null', () => {
    const section = buildBallisticSection(
      makeCtx({ candidateBallistic: null }),
    )
    const row = section.items.find((i) => i.label === 'Initial velocity')!
    expect(row.tone).toBe('muted')
  })

  it('Residual velocity carries the "not benchmark agreement" detail', () => {
    const section = buildBallisticSection(makeCtx())
    const row = section.items.find((i) => i.label === 'Residual velocity')!
    expect(row.detail).toContain('not benchmark agreement')
    expect(row.tone).toBe('warning')
  })

  it('Perforation marker passes through ballisticPerforationTone', () => {
    const section = buildBallisticSection(
      makeCtx({ ballisticPerforationTone: 'danger' }),
    )
    const row = section.items.find((i) => i.label === 'Perforation marker')!
    expect(row.tone).toBe('danger')
    expect(row.detail).toContain('perforated_candidate is NOT')
  })

  it('Energy balance passes through tone + uses claim_impact detail', () => {
    const section = buildBallisticSection(makeCtx())
    const row = section.items.find((i) => i.label === 'Energy balance')!
    expect(row.tone).toBe('warning')
    expect(row.detail).toBe('energy balance is Tier 1')
  })

  it('Energy balance falls back to default detail when candidateBallistic is null', () => {
    const section = buildBallisticSection(
      makeCtx({ candidateBallistic: null }),
    )
    const row = section.items.find((i) => i.label === 'Energy balance')!
    expect(row.detail).toContain('Tier 1 candidate health indicator')
  })

  it('Animation manifest tone is accent when available', () => {
    const section = buildBallisticSection(makeCtx())
    const row = section.items.find((i) => i.label === 'Animation manifest')!
    expect(row.tone).toBe('accent')
  })

  it('Time-step convergence falls back to FM-04b reserved detail', () => {
    const section = buildBallisticSection(makeCtx())
    const row = section.items.find((i) => i.label === 'Time-step convergence')!
    expect(row.detail).toContain('FM-04b')
  })

  it('Ballistic Tier 2 blockers row is always danger-toned', () => {
    const section = buildBallisticSection(makeCtx())
    const row = section.items.find((i) => i.label === 'Ballistic Tier 2 blockers')!
    expect(row.tone).toBe('danger')
    expect(row.value).toContain('5 blockers')
  })

  it('purity — same context returns deep-equal output across two calls', () => {
    const ctx = makeCtx()
    const a = buildBallisticSection(ctx)
    const b = buildBallisticSection(ctx)
    expect(a).toEqual(b)
  })

  it('D:-3 — ctx is not mutated', () => {
    const ctx = makeCtx()
    const before = JSON.parse(JSON.stringify(ctx))
    buildBallisticSection(ctx)
    expect(ctx).toEqual(before)
  })
})
