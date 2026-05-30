// FM-04a Phase 43 — result-viewport color legend (ScaleBar) tests.
//
// The ScaleBar is the vertical color legend that floats over the dark 3D
// result viewport (sibling of ViewportNavGizmo). It maps the active
// field-value range to the SAME blue→green→orange ramp the mesh is painted
// with, annotated with numeric ticks (max at top … min at bottom).
//
// What is asserted (anti-gaming, codebase-grounded):
//   * The legend title reflects the field component via the SHARED
//     FIELD_COMPONENT_LABELS table (not a hard-coded string here).
//   * Tick labels reflect valueMax (top) and valueMin (bottom), formatted
//     with the SAME formatHeroValue the hero uses — the assertion compares
//     against formatHeroValue output so it tracks the component's formatter.
//   * The band carries a CSS linear-gradient (the shared ramp).
//   * A degenerate constant field (valueMax === valueMin) renders without
//     throwing and never surfaces 'NaN' / 'Infinity' text.
//   * The units suffix appears only when units are passed (no fabrication).
//
// Tier 1 / Tier 2 engineering candidate; not signed validation.

import { describe, expect, it } from 'vitest'
import { render, screen, within } from '@testing-library/react'
import { ScaleBar } from '../src/components/ScaleBar'
import { FIELD_COMPONENT_LABELS, formatHeroValue } from '../src/components/heroPeakFormat'

describe('ScaleBar — color legend', () => {
  it('renders the component label from the shared FIELD_COMPONENT_LABELS table', () => {
    render(<ScaleBar valueMin={0} valueMax={5e8} fieldComponent="mises" />)
    const title = screen.getByTestId('scale-bar-title')
    expect(title.textContent).toContain(FIELD_COMPONENT_LABELS.mises)
  })

  it('uses the component-specific label for a tensor component (sxx)', () => {
    render(<ScaleBar valueMin={0} valueMax={1e6} fieldComponent="sxx" />)
    const title = screen.getByTestId('scale-bar-title')
    expect(title.textContent).toContain(FIELD_COMPONENT_LABELS.sxx)
  })

  it('renders 5 ticks with top=valueMax and bottom=valueMin (formatHeroValue-consistent)', () => {
    const valueMin = 1.2e6
    const valueMax = 9.8e8
    render(<ScaleBar valueMin={valueMin} valueMax={valueMax} fieldComponent="mises" />)
    const ticks = screen.getAllByTestId('scale-bar-tick')
    expect(ticks).toHaveLength(5)
    // Top tick = valueMax, bottom tick = valueMin, formatted identically to the hero.
    expect(ticks[0].textContent).toBe(formatHeroValue(valueMax))
    expect(ticks[ticks.length - 1].textContent).toBe(formatHeroValue(valueMin))
  })

  it('the band carries a CSS linear-gradient (the shared ramp)', () => {
    render(<ScaleBar valueMin={0} valueMax={100} fieldComponent="mises" />)
    const band = screen.getByTestId('scale-bar-band')
    const bg = band.style.background || band.style.backgroundImage
    expect(bg).toContain('linear-gradient')
  })

  it('degenerate constant field (valueMax === valueMin) renders without NaN/Infinity', () => {
    expect(() =>
      render(<ScaleBar valueMin={42} valueMax={42} fieldComponent="mises" />),
    ).not.toThrow()
    const root = screen.getByTestId('result-scale-bar')
    expect(root.textContent ?? '').not.toContain('NaN')
    expect(root.textContent ?? '').not.toContain('Infinity')
    // A constant field shows a single value rather than a fabricated spread.
    const ticks = screen.getAllByTestId('scale-bar-tick')
    expect(ticks).toHaveLength(1)
    expect(ticks[0].textContent).toBe(formatHeroValue(42))
  })

  it('renders a SOLID band (NOT the full ramp) when the range collapses', () => {
    // colorForElement forces t=0 for a constant/invalid range, so the mesh is
    // a single color; the legend must match — no multicolor gradient that
    // would contradict the on-screen mesh (Codex Slice-3 R0).
    render(<ScaleBar valueMin={42} valueMax={42} fieldComponent="mises" />)
    const band = screen.getByTestId('scale-bar-band')
    const bg = band.style.background || band.style.backgroundImage
    expect(bg).not.toContain('linear-gradient')
    expect(bg).toMatch(/rgb\(/)
  })

  it('renders the units suffix when units are provided', () => {
    render(<ScaleBar valueMin={0} valueMax={5e8} fieldComponent="mises" units="Pa" />)
    const title = screen.getByTestId('scale-bar-title')
    expect(title.textContent).toContain('Pa')
  })

  it('OMITS the units suffix when units are absent (no fabrication)', () => {
    render(<ScaleBar valueMin={0} valueMax={5e8} fieldComponent="mises" />)
    const root = screen.getByTestId('result-scale-bar')
    // Only the shared label should be present — no invented units token.
    const title = within(root).getByTestId('scale-bar-title')
    expect(title.textContent).toBe(FIELD_COMPONENT_LABELS.mises)
  })
})
