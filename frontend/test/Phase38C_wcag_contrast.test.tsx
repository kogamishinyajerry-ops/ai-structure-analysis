/**
 * FM-04a Phase 38 C — WCAG 1.4.3 contrast sweep pins.
 *
 * Phase 37 C's wcag_audit.md flagged 10/10 surfaces with an UNMEASURED
 * 1.4.3 (contrast) GAP. Phase 38 C measures the actual text/bg hex pairs
 * with a real WCAG 2.x helper and adjusts the one failing token
 * (--text-muted). These tests:
 *   - V:-1 guard: pin the helper against 3 PUBLISHED WCAG canonical
 *     examples so the math is verifiably the spec algorithm, not a vibe.
 *   - measure each documented surface pair and assert AA (4.5:1 normal).
 *
 * Tier 1 engineering candidate; not signed validation; not benchmark
 * agreement.
 */

import { describe, expect, it } from 'vitest'

import {
  compositeHexOver,
  computeContrastRatio,
  computeRelativeLuminance,
  hexToRgb,
  meetsWCAG_AA,
} from '../src/lib/wcagContrast'

// --- Palette SSOT (mirrors frontend/src/index.css :root + component styles).
// If index.css changes a token, update here in the SAME commit (the pin is
// the contract). --text-muted is RAISED from #64748b (3.74:1, FAIL) to
// #828fa6 in Phase 38 C.
const PALETTE = {
  bgBase: '#020617',
  bgSurfaceOpaque: '#1e293b', // rgba(30,41,59, .5) before alpha
  bgSurfaceAlpha: 0.5,
  textPrimary: '#f8fafc',
  textSecondary: '#94a3b8',
  textMuted: '#828fa6', // Phase 38 C: raised from #64748b to pass 4.5:1
  accent: '#10b981',
  amber: '#f59e0b',
} as const

// Effective opaque background behind glass-panel text.
const GLASS = compositeHexOver(
  PALETTE.bgSurfaceOpaque,
  PALETTE.bgSurfaceAlpha,
  PALETTE.bgBase,
)

describe('V:-1 — helper matches published WCAG canonical examples', () => {
  it('black on white = 21:1 (exact)', () => {
    expect(computeContrastRatio('#000000', '#ffffff')).toBeCloseTo(21.0, 2)
  })

  it('white relative luminance = 1.0, black = 0.0', () => {
    expect(computeRelativeLuminance('#ffffff')).toBeCloseTo(1.0, 5)
    expect(computeRelativeLuminance('#000000')).toBeCloseTo(0.0, 5)
  })

  it('#767676 on white ≈ 4.54:1 (WebAIM AA-boundary gray)', () => {
    expect(computeContrastRatio('#767676', '#ffffff')).toBeCloseTo(4.54, 1)
  })

  it('#595959 on white ≈ 7.0:1 (WebAIM AAA-boundary gray)', () => {
    expect(computeContrastRatio('#595959', '#ffffff')).toBeCloseTo(7.0, 1)
  })

  it('contrast ratio is symmetric in argument order', () => {
    expect(computeContrastRatio('#94a3b8', GLASS)).toBeCloseTo(
      computeContrastRatio(GLASS, '#94a3b8'),
      6,
    )
  })
})

describe('helper unit behaviour', () => {
  it('parses #rgb and #rrggbb', () => {
    expect(hexToRgb('#fff')).toEqual([255, 255, 255])
    expect(hexToRgb('#10b981')).toEqual([16, 185, 129])
  })

  it('rejects malformed hex', () => {
    expect(() => hexToRgb('#xyz123')).toThrow()
  })

  it('composites 50% surface over base into the expected opaque color', () => {
    // 0.5*(30,41,59) + 0.5*(2,6,23) = (16, 23.5->24, 41) = #101829
    expect(GLASS).toBe('#101829')
  })

  it('meetsWCAG_AA honours the normal vs large-text threshold', () => {
    expect(meetsWCAG_AA(4.5)).toBe(true)
    expect(meetsWCAG_AA(4.49)).toBe(false)
    expect(meetsWCAG_AA(3.0, true)).toBe(true)
    expect(meetsWCAG_AA(2.99, true)).toBe(false)
  })
})

describe('glass-surface text pairs meet WCAG AA (4.5:1)', () => {
  it('text-primary on glass', () => {
    expect(meetsWCAG_AA(computeContrastRatio(PALETTE.textPrimary, GLASS))).toBe(
      true,
    )
  })

  it('text-secondary on glass', () => {
    expect(
      meetsWCAG_AA(computeContrastRatio(PALETTE.textSecondary, GLASS)),
    ).toBe(true)
  })

  it('text-muted on glass — the Phase 38 C fix (was 3.74:1 at #64748b)', () => {
    const ratio = computeContrastRatio(PALETTE.textMuted, GLASS)
    expect(ratio).toBeGreaterThanOrEqual(4.5)
    // sanity: the OLD muted token would have failed
    expect(computeContrastRatio('#64748b', GLASS)).toBeLessThan(4.5)
  })

  it('accent (emerald) on glass', () => {
    expect(meetsWCAG_AA(computeContrastRatio(PALETTE.accent, GLASS))).toBe(true)
  })

  it('amber (runner_available badge text) on glass', () => {
    expect(meetsWCAG_AA(computeContrastRatio(PALETTE.amber, GLASS))).toBe(true)
  })
})

describe('ErrorCard dark-red palette meets WCAG AA (Phase 36 B + 38 C verify)', () => {
  it('error title text #ffcdcd on #2a1414', () => {
    expect(meetsWCAG_AA(computeContrastRatio('#ffcdcd', '#2a1414'))).toBe(true)
  })

  it('error message text #ffe3e3 on #3a1818', () => {
    expect(meetsWCAG_AA(computeContrastRatio('#ffe3e3', '#3a1818'))).toBe(true)
  })

  it('Retry button text #ffffff on #5c1e1e', () => {
    expect(meetsWCAG_AA(computeContrastRatio('#ffffff', '#5c1e1e'))).toBe(true)
  })
})
