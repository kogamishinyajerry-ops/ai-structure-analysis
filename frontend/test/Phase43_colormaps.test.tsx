/**
 * FM-04a Phase 43 Slice 4 — colormap engine tests (additive).
 *
 * Tier 1 engineering candidate; not signed validation. Pins the colormap SSOT
 * (src/components/colormaps.ts) + its threading through viewportGeometry:
 *
 *   - REGRESSION GUARD: 'spectral' reproduces the legacy gradientStop ramp
 *     byte-for-byte, so introducing colormaps changes NO existing visual when
 *     the default is in effect (complements the Phase21C gradient-pin test);
 *   - sampleColormap clamps t to [0,1] and degrades non-finite t to 0;
 *   - every ramp returns linear RGB in [0,1];
 *   - the non-spectral ramps are DISTINCT from spectral (the dispatch really
 *     switches ramps, not a no-op);
 *   - colorForValueFraction threads the colormap arg (default = spectral).
 */

import { describe, it, expect } from 'vitest'

import {
  sampleColormap,
  COLORMAP_IDS,
  DEFAULT_COLORMAP,
  COLORMAP_LABELS,
} from '../src/components/colormaps'
import { colorForValueFraction, gradientStop } from '../src/components/viewportGeometry'

// Independent re-statement of the pre-Slice-4 ramp arithmetic — the oracle the
// 'spectral' colormap must match exactly.
function legacyGradientStop(t: number): [number, number, number] {
  const tc = Math.max(0, Math.min(1, t))
  if (tc < 0.5) {
    const k = tc * 2
    return [
      (37 + (16 - 37) * k) / 255,
      (99 + (185 - 99) * k) / 255,
      (235 + (129 - 235) * k) / 255,
    ]
  }
  const k = (tc - 0.5) * 2
  return [
    (16 + (249 - 16) * k) / 255,
    (185 + (115 - 185) * k) / 255,
    (129 + (22 - 129) * k) / 255,
  ]
}

describe('colormaps — spectral reproduces the legacy ramp (regression guard)', () => {
  for (const t of [0, 0.1, 0.25, 0.5, 0.75, 0.9, 1]) {
    it(`spectral(${t}) === legacy gradientStop(${t})`, () => {
      const got = sampleColormap('spectral', t)
      const want = legacyGradientStop(t)
      for (let i = 0; i < 3; i++) expect(got[i]).toBeCloseTo(want[i], 12)
    })
  }

  it('gradientStop alias + colorForValueFraction default both equal spectral', () => {
    for (const t of [0, 0.3, 0.5, 0.8, 1]) {
      expect(gradientStop(t)).toEqual(sampleColormap('spectral', t))
      expect(colorForValueFraction(t)).toEqual(sampleColormap('spectral', t))
    }
  })
})

describe('colormaps — sampling contract', () => {
  it('clamps t to [0,1] and degrades non-finite t to 0', () => {
    for (const id of COLORMAP_IDS) {
      expect(sampleColormap(id, -1)).toEqual(sampleColormap(id, 0))
      expect(sampleColormap(id, 2)).toEqual(sampleColormap(id, 1))
      expect(sampleColormap(id, Number.NaN)).toEqual(sampleColormap(id, 0))
    }
  })

  it('returns linear RGB in [0,1] for every colormap across t', () => {
    for (const id of COLORMAP_IDS) {
      for (const t of [0, 0.33, 0.66, 1]) {
        const [r, g, b] = sampleColormap(id, t)
        for (const c of [r, g, b]) {
          expect(c).toBeGreaterThanOrEqual(0)
          expect(c).toBeLessThanOrEqual(1)
        }
      }
    }
  })

  it('non-spectral ramps differ from spectral (dispatch actually switches)', () => {
    for (const id of COLORMAP_IDS) {
      if (id === 'spectral') continue
      const differs = [0.25, 0.5, 0.75].some((t) => {
        const a = sampleColormap(id, t)
        const b = sampleColormap('spectral', t)
        return a[0] !== b[0] || a[1] !== b[1] || a[2] !== b[2]
      })
      expect(differs).toBe(true)
    }
  })

  it('colorForValueFraction threads the colormap arg', () => {
    expect(colorForValueFraction(0.5, 'grayscale')).toEqual(sampleColormap('grayscale', 0.5))
    expect(colorForValueFraction(0.5, 'turbo')).toEqual(sampleColormap('turbo', 0.5))
  })

  it('metadata: DEFAULT is spectral and every id has a label', () => {
    expect(DEFAULT_COLORMAP).toBe('spectral')
    for (const id of COLORMAP_IDS) expect(typeof COLORMAP_LABELS[id]).toBe('string')
  })
})
