// FM-04a Phase 27 B — Blueprint target section extraction tests.
//
// Phase 26 D extracted 5 of 7 trust sections; Blueprint target +
// Ballistic candidate stayed inline. Phase 27 B extracts Blueprint
// target with a narrow single-object context interface.
//
// Honest LOC measurement (this is the load-bearing audit):
//   - App.tsx pre-Phase-27-B:  1464 LOC
//   - App.tsx post-Phase-27-B: 1454 LOC (-10, genuine reduction)
//
// Phase 26 D taught the lesson: a wide context interface (10+
// fields, multi-line construction at the call site) can GROW
// App.tsx even after extraction. Phase 27 B picked Blueprint
// target precisely because its context is a SINGLE already-typed
// bundle (blueprintSummary) + icon — 2-line construction at the
// call site vs 15-line inline literal = real LOC savings.
//
// Anti-gaming guard D:-3 — purity (no ctx mutation). Same as
// Phase 26 D. Re-pinned here.
//
// Tier 1 / Tier 2 engineering candidate; not signed validation;
// not benchmark agreement.

import { describe, expect, it } from 'vitest'

import { buildBlueprintTargetSection } from '../src/state/trustCenterViewModel'

function makeCtx(overrides?: {
  blueprintSummary?: Partial<{
    label: string
    imagePath: string
    evidenceCaseId: string
    claimTier: string
    allowedClaim: string
    anchorCount: number
    coveredAnchorCount: number
    availableEvidenceCount: number
    evidenceCount: number
    startedSlices: number
    nextSlice: string
    blockerCount: number
  }>
}) {
  return {
    icon: 'blueprint-icon',
    blueprintSummary: {
      label: 'Workbench parity scope',
      imagePath: '/Users/Zhuanz/Downloads/cfd_harness_workbench_ui_concept.svg',
      evidenceCaseId: 'cylinder-pv-candidate',
      claimTier: 'Tier 1 engineering candidate',
      allowedClaim: 'not_signed_validation; not_benchmark_agreement',
      anchorCount: 5,
      coveredAnchorCount: 2,
      availableEvidenceCount: 1,
      evidenceCount: 6,
      startedSlices: 3,
      nextSlice: 'M2 mesh-import baseline',
      blockerCount: 4,
      ...overrides?.blueprintSummary,
    },
  }
}

describe('Phase 27 B — buildBlueprintTargetSection', () => {
  it('emits 9 items with the correct title and icon passthrough', () => {
    const section = buildBlueprintTargetSection(makeCtx())
    expect(section.title).toBe('Blueprint target')
    expect(section.icon).toBe('blueprint-icon')
    expect(section.items).toHaveLength(9)
    expect(section.items.map((i) => i.label)).toEqual([
      'Blueprint memory',
      'Evidence case',
      'Claim tier',
      'Visual anchors',
      'Available evidence',
      'Covered anchors',
      'Started slices',
      'Next deferred slice',
      'Tier 2 blockers',
    ])
  })

  it('Claim tier carries warning tone + allowedClaim as detail', () => {
    const section = buildBlueprintTargetSection(makeCtx())
    const claimTierRow = section.items.find((i) => i.label === 'Claim tier')!
    expect(claimTierRow.tone).toBe('warning')
    expect(claimTierRow.detail).toContain('not_signed_validation')
  })

  it('Available evidence tone flips warning when count is 0', () => {
    const section = buildBlueprintTargetSection(
      makeCtx({ blueprintSummary: { availableEvidenceCount: 0 } }),
    )
    const evidenceRow = section.items.find((i) => i.label === 'Available evidence')!
    expect(evidenceRow.tone).toBe('warning')
    expect(evidenceRow.value).toBe('0/6 indexed evidence ref(s)')
  })

  it('Available evidence tone is accent when count > 0', () => {
    const section = buildBlueprintTargetSection(
      makeCtx({ blueprintSummary: { availableEvidenceCount: 3, evidenceCount: 6 } }),
    )
    const evidenceRow = section.items.find((i) => i.label === 'Available evidence')!
    expect(evidenceRow.tone).toBe('accent')
    expect(evidenceRow.value).toBe('3/6 indexed evidence ref(s)')
  })

  it('Covered anchors tone is accent when fully covered', () => {
    const section = buildBlueprintTargetSection(
      makeCtx({ blueprintSummary: { anchorCount: 5, coveredAnchorCount: 5 } }),
    )
    const coveredRow = section.items.find((i) => i.label === 'Covered anchors')!
    expect(coveredRow.tone).toBe('accent')
    expect(coveredRow.value).toBe('5/5')
  })

  it('Covered anchors tone is warning when partial', () => {
    const section = buildBlueprintTargetSection(
      makeCtx({ blueprintSummary: { anchorCount: 5, coveredAnchorCount: 2 } }),
    )
    const coveredRow = section.items.find((i) => i.label === 'Covered anchors')!
    expect(coveredRow.tone).toBe('warning')
    expect(coveredRow.value).toBe('2/5')
  })

  it('Tier 2 blockers row is always danger-toned', () => {
    const section = buildBlueprintTargetSection(makeCtx())
    const blockerRow = section.items.find((i) => i.label === 'Tier 2 blockers')!
    expect(blockerRow.tone).toBe('danger')
    expect(blockerRow.value).toContain('blocker(s) still active')
  })

  it('purity — same context returns deep-equal output across two calls', () => {
    const ctx = makeCtx()
    const a = buildBlueprintTargetSection(ctx)
    const b = buildBlueprintTargetSection(ctx)
    expect(a).toEqual(b)
  })

  it('D:-3 — ctx is not mutated', () => {
    const ctx = makeCtx()
    const before = JSON.parse(JSON.stringify(ctx))
    buildBlueprintTargetSection(ctx)
    expect(ctx).toEqual(before)
  })
})
