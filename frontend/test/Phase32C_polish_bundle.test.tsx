// FM-04a Phase 32 C — Tier-2 polish bundle pins.
//
// 4 polish affordances pinned:
//   C1. Coord-readout advanced-mode gating (Phase 30 FINAL gap #9,
//       Phase 31 UX honest gap #2): the 30Hz floating XYZ tooltip
//       now requires advanced mode. 'coord-readout' is added to
//       ADVANCED_FEATURE_IDS in uiMode.ts.
//   C2. Companion entrance opacity fade (Phase 31 UX honest gap #3):
//       POLISH_CLASS_COMPANION_MOUNT class applied to outermost
//       CompanionViewport div; @keyframes fm04a-companion-mount-
//       fade-in over 200ms ease-out; prefers-reduced-motion honored.
//   C3. Compare-cuts basic-mode unlock (Phase 30 FINAL gap #10,
//       Phase 31 UI honest gap #11): 'companion-viewport' REMOVED
//       from ADVANCED_FEATURE_IDS; companion now surfaces in basic
//       mode too (origin-stamping in Phase 31 D removed write-
//       conflict risk).
//   C4. Richardson p-anomaly clean r=2 spike (Phase 31 honest gap
//       #5): sibling convergence_study_r2.json in cantilever-beam-
//       modal-candidate/. Live ccx + gmsh at cl=12/6/3mm (clean
//       r=2). Honest finding: even with clean r the empirical p
//       stays around 1.33 — non-constant ratio was a noise source
//       but not the dominant one.
//
// Anti-gaming guards:
//   C:-1: all existing Phase 25 C / 30 B pins still pass (33
//         tests in Phase 30 B + 15 in Phase 25 C). 2 pins UPDATED
//         to track the registry swap (companion-viewport → coord-
//         readout) — additive scope, NOT behavioral regression.
//   D:-1: companion entrance fade is opacity-only (no transform),
//         and applies once per mount. NO continuous animation.
//   E:-1: prefers-reduced-motion: reduce suppresses both
//         transition AND keyframe animation (pinned).

import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'

import {
  ADVANCED_FEATURE_IDS,
  shouldShowFeature,
} from '../src/uiMode'
import {
  POLISH_CLASS_COMPANION_MOUNT,
  POLISH_CSS_TEXT,
} from '../src/components/polishStyles'
import { CompanionViewport } from '../src/components/CompanionViewport'

// ─── C1 — coord-readout in advanced registry ──────────────────────

describe('Phase 32 C C1 — coord-readout advanced-mode gating', () => {
  it("'coord-readout' is registered in ADVANCED_FEATURE_IDS", () => {
    expect(ADVANCED_FEATURE_IDS).toContain('coord-readout')
  })

  it("shouldShowFeature returns true for coord-readout in advanced", () => {
    expect(shouldShowFeature('advanced', 'coord-readout')).toBe(true)
  })

  it("shouldShowFeature returns false for coord-readout in basic", () => {
    expect(shouldShowFeature('basic', 'coord-readout')).toBe(false)
  })

  it('Phase 25 C registry count unchanged (5 features; swap-not-extend)', () => {
    // Net count is the same as Phase 30 B (companion-viewport → coord-
    // readout swap); the registry-size invariant from Phase 25 C
    // holds across the migration.
    expect(ADVANCED_FEATURE_IDS).toHaveLength(5)
  })
})

// ─── C2 — companion entrance opacity fade ─────────────────────────

describe('Phase 32 C C2 — companion entrance fade', () => {
  it('POLISH_CLASS_COMPANION_MOUNT is exported and stable', () => {
    expect(POLISH_CLASS_COMPANION_MOUNT).toBe('fm04a-companion-mount')
  })

  it('@keyframes fm04a-companion-mount-fade-in is defined', () => {
    expect(POLISH_CSS_TEXT).toMatch(
      /@keyframes\s+fm04a-companion-mount-fade-in/,
    )
  })

  it('keyframe transitions opacity 0 → 1', () => {
    // The keyframe body contains nested {} blocks, so a single non-
    // greedy match against [^}]+ truncates at the first inner brace.
    // Inspect a longer slice instead.
    const idx = POLISH_CSS_TEXT.indexOf('fm04a-companion-mount-fade-in')
    expect(idx).toBeGreaterThan(-1)
    // The keyframe definition has two inner blocks; capture enough
    // of the string after the keyframe name.
    const slice = POLISH_CSS_TEXT.slice(idx, idx + 200)
    expect(slice).toMatch(/from\s*{\s*opacity:\s*0/)
    expect(slice).toMatch(/to\s*{\s*opacity:\s*1/)
  })

  it('class applies 200ms ease-out animation matching FM-04a vocabulary', () => {
    expect(POLISH_CSS_TEXT).toMatch(
      /\.fm04a-companion-mount\s*{\s*animation:\s*fm04a-companion-mount-fade-in\s+200ms\s+ease-out/,
    )
  })

  it('prefers-reduced-motion: reduce disables the animation', () => {
    // The reduced-motion block at the bottom of POLISH_CSS_TEXT lists
    // POLISH_CLASS_COMPANION_MOUNT among the classes whose animation
    // becomes 'none'.
    const reduceIdx = POLISH_CSS_TEXT.indexOf('prefers-reduced-motion: reduce')
    expect(reduceIdx).toBeGreaterThan(-1)
    const afterReduce = POLISH_CSS_TEXT.slice(reduceIdx)
    expect(afterReduce).toMatch(/fm04a-companion-mount/)
    expect(afterReduce).toMatch(/animation:\s*none/)
  })

  it('CompanionViewport applies the mount class to its outermost div', () => {
    render(
      <CompanionViewport
        frame={null}
        valueMin={0}
        valueMax={1}
        sectionCut={{ axis: 'x', positionM: 0, showLow: true }}
        onSectionCutChange={() => {}}
      />,
    )
    const root = screen.getByTestId('companion-viewport')
    expect(root.className).toMatch(/fm04a-companion-mount/)
  })
})

// ─── C3 — Compare-cuts basic-mode unlock ─────────────────────────

describe('Phase 32 C C3 — Compare-cuts basic-mode unlock', () => {
  it("'companion-viewport' is REMOVED from ADVANCED_FEATURE_IDS", () => {
    // TS would refuse companion-viewport as an AdvancedFeatureId
    // member now. The runtime check uses string cast for parity with
    // historic test prose.
    expect(ADVANCED_FEATURE_IDS as readonly string[]).not.toContain(
      'companion-viewport',
    )
  })

  it('total advanced feature count unchanged at 5 (swap)', () => {
    expect(ADVANCED_FEATURE_IDS).toHaveLength(5)
  })

  it('coord-readout took companion-viewport place in the registry', () => {
    expect([...ADVANCED_FEATURE_IDS].sort()).toEqual([
      'coord-readout',
      'field-component-switcher',
      'probe-list-panel',
      'section-cut',
      'threshold-filter',
    ])
  })
})

// ─── C4 — Richardson p-anomaly clean r=2 spike artifact ──────────

import { readFileSync } from 'fs'
import { resolve } from 'path'

describe('Phase 32 C C4 — cantilever-modal clean r=2 sibling artifact', () => {
  const REPO_ROOT = resolve(__dirname, '..', '..')
  const PATH = resolve(
    REPO_ROOT,
    'golden_samples',
    'cantilever-beam-modal-candidate',
    'convergence_study_r2.json',
  )

  // Read once + reuse across cases. If the spike artifact is missing
  // (e.g., live ccx not available in CI), every test below trips
  // with a clear message rather than silently passing.
  let payload: ReturnType<typeof JSON.parse>
  try {
    payload = JSON.parse(readFileSync(PATH, 'utf-8'))
  } catch (err) {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    payload = { __load_error__: String((err as any).message ?? err) }
  }

  it('sibling artifact exists', () => {
    expect(payload.__load_error__).toBeUndefined()
  })

  it('schema 1.1.0', () => {
    expect(payload.schema_version).toBe('1.1.0')
  })

  it('case_id matches the canonical artifact', () => {
    expect(payload.case_id).toBe('cantilever-beam-modal-candidate')
  })

  it('refinement values are clean r=2 (cl=12/6/3 mm)', () => {
    const values = payload.points.map((p: { refinement_param: number }) =>
      p.refinement_param,
    )
    expect(values).toEqual([0.012, 0.006, 0.003])
  })

  it('refinement_ratio_constant is TRUE (clean r=2 ratio)', () => {
    expect(payload.richardson.refinement_ratio_constant).toBe(true)
    expect(payload.richardson.refinement_ratio_r).toBe(2)
  })

  it('observed p stabilized between Phase 31 0.69 and theoretical 2', () => {
    // Honest finding: clean r=2 lifted p from 0.69 (non-constant
    // ratio noise) to ~1.33, but did NOT reach theoretical p=2.
    // Pinned at ~1.33 ± 0.05. If a future change pushes p past 1.5
    // OR drops it below 1.0, the test trips for re-verification.
    expect(payload.richardson.observed_order_p).toBeGreaterThan(1.0)
    expect(payload.richardson.observed_order_p).toBeLessThan(1.5)
  })

  it('extrapolated residual reveals 0.05% asymptotic agreement', () => {
    // f_∞ ≈ 66.879 Hz vs analytical 66.841 Hz → residual ≈ +0.056%.
    // Well below the original Phase 30 D finest-mesh +0.084%
    // residual — Richardson extracted ~30% additional convergence.
    expect(payload.richardson.extrapolated_residual_pct).toBeLessThan(0.10)
    expect(payload.richardson.extrapolated_residual_pct).toBeGreaterThan(0.0)
  })

  it('canonical convergence_study.json is PRESERVED', () => {
    // The r=2 spike does NOT overwrite the Phase 30 D canonical
    // artifact (cl=12/8/5 mm with non-constant ratio). Both
    // coexist as sibling files. This is the same "preserve the
    // historical record" honest-scope pattern as Phase 28 A's
    // C3D8 NotImplementedError.
    const canonicalPath = resolve(
      REPO_ROOT,
      'golden_samples',
      'cantilever-beam-modal-candidate',
      'convergence_study.json',
    )
    const canonical = JSON.parse(readFileSync(canonicalPath, 'utf-8'))
    // The canonical still has the cl=12/8/5 values.
    const canonicalCls = canonical.points.map(
      (p: { refinement_param: number }) => p.refinement_param,
    )
    expect(canonicalCls).toEqual([0.012, 0.008, 0.005])
  })
})
