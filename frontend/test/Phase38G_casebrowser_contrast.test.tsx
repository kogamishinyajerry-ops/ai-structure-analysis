/**
 * FM-04a Phase 38 G — CaseBrowser WCAG 1.4.3 contrast, measured (act-on #5).
 *
 * Eval-fleet finding #5 (Phase 38 E) claimed the CaseBrowser runner_available
 * amber badge was ~3.3:1 (a 1.4.3 fail). The Phase 38 E eval ran via a
 * harsh-framed general-purpose proxy (not the calibrated fleet), and that
 * estimate is wrong: measured precisely against the badge's REAL background
 * (a dark, amber-tinted panel — NOT the amber border), the text is ~5.77:1,
 * which PASSES AA for small text. The 38 C audit had deferred these
 * CaseBrowser 1.4.3 cells as "not formally measured; Phase 38 audit" — this
 * test closes that task by pinning the measured values against the
 * spec-verified wcagContrast helper. No colors changed: nothing failed.
 *
 * Tier 1 / Tier 2 engineering candidate; not signed validation; not benchmark
 * agreement.
 */

import { describe, expect, it } from 'vitest'

import {
  compositeHexOver,
  computeContrastRatio,
  meetsWCAG_AA,
} from '../src/lib/wcagContrast'

// Theme tokens (frontend/src/index.css) + CaseBrowser.tsx style constants.
const BG_BASE = '#020617' // --bg-base (app root)
const BG_SURFACE = '#1e293b' // --bg-surface rgb, applied at 0.5 alpha
const TEXT_SECONDARY = '#94a3b8' // --text-secondary (badge + idle chip text)
const ACCENT = '#10b981' // --accent (active filter chip background)
const AMBER = '#ffb450' // runner badge fill rgb(255,180,80) at 0.10 alpha

// Effective backgrounds: composite the alpha layers down to the app root so
// the contrast is measured against what actually renders behind the text.
const PANEL = compositeHexOver(BG_SURFACE, 0.5, BG_BASE)
const RUNNER_BADGE_BG = compositeHexOver(AMBER, 0.1, PANEL)

const AA_SMALL = 4.5

describe('CaseBrowser WCAG 1.4.3 contrast (Phase 38 G — eval #5 disposition)', () => {
  it('runner_available amber badge passes AA — eval #5 (~3.3:1) was a false alarm', () => {
    const ratio = computeContrastRatio(TEXT_SECONDARY, RUNNER_BADGE_BG)
    expect(ratio).toBeGreaterThanOrEqual(AA_SMALL)
    expect(meetsWCAG_AA(ratio, false)).toBe(true)
    // Guard the disposition: the real ratio is materially above the eval claim.
    expect(ratio).toBeGreaterThan(5) // measured ~5.77:1, not ~3.3:1
  })

  it('active filter chip (#000 on --accent) passes AA', () => {
    const ratio = computeContrastRatio('#000000', ACCENT)
    expect(ratio).toBeGreaterThanOrEqual(AA_SMALL)
    expect(meetsWCAG_AA(ratio, false)).toBe(true)
  })

  it('idle filter chip (--text-secondary on panel) passes AA', () => {
    const ratio = computeContrastRatio(TEXT_SECONDARY, PANEL)
    expect(ratio).toBeGreaterThanOrEqual(AA_SMALL)
    expect(meetsWCAG_AA(ratio, false)).toBe(true)
  })
})

describe('TabButton WCAG 1.4.3 contrast (Phase 38 G — last 1.4.3 GAP → 10/10)', () => {
  // NOTE (Phase 42): TabButton now adopts the `.tab-pill` primitive, so the
  // live colors are active = #04130d on --accent, idle = --text-secondary on
  // panel (the calmer pair, both still AA — pinned in Phase42_aesthetic_motion).
  // The #000/#fff pair below is retained as a conservative AA *floor*: the old
  // high-contrast colors still pass, so the move to .tab-pill cannot regress AA.
  it('active tab (#000 on --accent) passes AA', () => {
    const ratio = computeContrastRatio('#000000', ACCENT)
    expect(ratio).toBeGreaterThanOrEqual(AA_SMALL)
    expect(meetsWCAG_AA(ratio, false)).toBe(true)
  })

  it('idle tab (#fff on panel) passes AA', () => {
    const ratio = computeContrastRatio('#ffffff', PANEL)
    expect(ratio).toBeGreaterThanOrEqual(AA_SMALL)
    expect(meetsWCAG_AA(ratio, false)).toBe(true)
  })
})
