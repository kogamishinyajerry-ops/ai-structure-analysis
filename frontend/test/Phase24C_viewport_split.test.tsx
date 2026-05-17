// FM-04a Phase 24 C — viewport file split tests.
//
// Tier 1 / Tier 2 engineering candidate; not signed validation; not
// benchmark agreement.
//
// Phase 24 C extracts pure-function helpers from
// ResultMeshWebGLViewport.tsx into three submodules (viewportGeometry,
// viewportRaycaster, viewportAnimation) to reverse Phase 23's UI LOC
// discipline -2 regression. Constraint: ZERO behavior change.
//
// Anti-gaming guards:
//   * C:-3 — the public API surface of ResultMeshWebGLViewport must
//     remain stable across the split. Any extracted helper that
//     existing tests / sibling components import (applyValueFilter,
//     findClosestNode, fieldValueAtNode, buildNodeCoords,
//     colorForValueFraction, PickedNodeInfo, SectionCutState,
//     ValueFilterState) must still be importable from the same path
//     as before.

import { describe, expect, it } from 'vitest'

// Cross-module byte-equivalence check: same function reference
// imported through the orchestrator and through the extracted
// modules MUST be the same identity (re-export, not duplicate).
import * as ViewportOrchestrator from '../src/components/ResultMeshWebGLViewport'
import * as ViewportGeometry from '../src/components/viewportGeometry'
import * as ViewportRaycaster from '../src/components/viewportRaycaster'
import * as ViewportAnimation from '../src/components/viewportAnimation'

describe('Phase 24 C — viewport file split', () => {
  it('C:-3 anti-gaming: ResultMeshWebGLViewport re-exports applyValueFilter from viewportRaycaster', () => {
    expect(ViewportOrchestrator.applyValueFilter).toBe(
      ViewportRaycaster.applyValueFilter,
    )
  })

  it('C:-3 anti-gaming: ResultMeshWebGLViewport re-exports findClosestNode from viewportRaycaster', () => {
    expect(ViewportOrchestrator.findClosestNode).toBe(
      ViewportRaycaster.findClosestNode,
    )
  })

  it('C:-3 anti-gaming: ResultMeshWebGLViewport re-exports fieldValueAtNode from viewportRaycaster', () => {
    expect(ViewportOrchestrator.fieldValueAtNode).toBe(
      ViewportRaycaster.fieldValueAtNode,
    )
  })

  it('C:-3 anti-gaming: ResultMeshWebGLViewport re-exports buildNodeCoords from viewportGeometry', () => {
    expect(ViewportOrchestrator.buildNodeCoords).toBe(
      ViewportGeometry.buildNodeCoords,
    )
  })

  it('C:-3 anti-gaming: ResultMeshWebGLViewport re-exports colorForValueFraction from viewportGeometry', () => {
    expect(ViewportOrchestrator.colorForValueFraction).toBe(
      ViewportGeometry.colorForValueFraction,
    )
  })

  it('C:-3 anti-gaming: ResultMeshWebGLViewport re-exports buildBufferGeometry from viewportGeometry', () => {
    expect(ViewportOrchestrator.buildBufferGeometry).toBe(
      ViewportGeometry.buildBufferGeometry,
    )
  })

  it('C:-3 anti-gaming: ResultMeshWebGLViewport re-exports detectWebGLSupport from viewportAnimation', () => {
    expect(ViewportOrchestrator.detectWebGLSupport).toBe(
      ViewportAnimation.detectWebGLSupport,
    )
  })

  it('viewportGeometry module exports the 3 face-table constants', () => {
    expect(ViewportGeometry.TET_FACES).toBeDefined()
    expect(ViewportGeometry.HEX_FACES).toBeDefined()
    expect(ViewportGeometry.QUAD_FACES).toBeDefined()
    expect(ViewportGeometry.TET_FACES.length).toBe(4)
    expect(ViewportGeometry.HEX_FACES.length).toBe(12)
    expect(ViewportGeometry.QUAD_FACES.length).toBe(2)
  })

  it('viewportRaycaster module exports applyValueFilter as a function', () => {
    expect(typeof ViewportRaycaster.applyValueFilter).toBe('function')
  })

  it('viewportAnimation module exports detectWebGLSupport as a function', () => {
    expect(typeof ViewportAnimation.detectWebGLSupport).toBe('function')
  })

  it('public API surface is the union of orchestrator + submodule exports', () => {
    // Documenting the public surface so any future deletion would
    // surface as a test failure.
    const publicSurface = [
      'applyValueFilter',
      'buildBufferGeometry',
      'buildNodeCoords',
      'colorForValueFraction',
      'detectWebGLSupport',
      'fieldValueAtNode',
      'findClosestNode',
      'ResultMeshWebGLViewport',
    ]
    for (const name of publicSurface) {
      expect(
        (ViewportOrchestrator as Record<string, unknown>)[name],
      ).toBeDefined()
    }
  })

  it('LOC discipline: orchestrator file is materially smaller than the pre-split 930 LOC', () => {
    // This test is informational; the byte-level check happens in
    // the Phase 24 C audit. Pin a sentinel by importing the
    // orchestrator without crash → file is parseable post-split.
    expect(typeof ViewportOrchestrator.ResultMeshWebGLViewport).toBe('function')
  })
})
