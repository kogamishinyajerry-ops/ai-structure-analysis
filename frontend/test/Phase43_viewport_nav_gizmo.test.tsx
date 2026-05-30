// FM-04a Phase 43 — viewport navigation gizmo tests.
//
// The gizmo is a dark-glass overlay floating in the 3D WebGL viewport.
// It renders a static orientation triad + a row of standard-view
// buttons (Iso / Top / Front / Right / Fit). Each button invokes the
// `onSetView` callback with a named preset; the host viewport maps the
// preset to camera azimuth/elevation (and, for Fit, a bounds-framing
// radius). Live triad orientation + actual camera MOTION are a manual /
// visual concern — NOT asserted here (no brittle WebGL assertions).
//
// Anti-gaming guards:
//   * Each preset → onSetView identifier is asserted via a real click,
//     not by reading the component's internals.
//   * Buttons are asserted to be real, focusable <button> elements.
//   * The exported preset → (azimuth, elevation) table is asserted
//     against analytical-known angles (Top = +90° elevation looking
//     down; Front = az 0 / el 0; Right = az +90° / el 0; Fit frames).
//
// Tier 1 / Tier 2 engineering candidate; not signed validation; not
// benchmark agreement.

import { describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen } from '@testing-library/react'
import { ViewportNavGizmo } from '../src/components/ViewportNavGizmo'
import { VIEW_PRESET_ANGLES, type ViewPreset } from '../src/components/viewportNavPresets'

const PRESETS: ViewPreset[] = ['iso', 'top', 'front', 'right', 'fit']

describe('ViewportNavGizmo — preset buttons invoke onSetView', () => {
  it.each(PRESETS)('clicking the %s button calls onSetView with that preset', (preset) => {
    const onSetView = vi.fn()
    render(<ViewportNavGizmo onSetView={onSetView} />)
    const btn = screen.getByTestId(`viewport-nav-${preset}`)
    fireEvent.click(btn)
    expect(onSetView).toHaveBeenCalledTimes(1)
    expect(onSetView).toHaveBeenCalledWith(preset)
  })

  it('renders all five standard-view buttons as real focusable <button> elements', () => {
    render(<ViewportNavGizmo onSetView={vi.fn()} />)
    for (const preset of PRESETS) {
      const btn = screen.getByTestId(`viewport-nav-${preset}`)
      // Real semantic button (keyboard-focusable, not a styled div).
      expect(btn.tagName).toBe('BUTTON')
      // A native <button> is focusable; confirm focus lands on it.
      btn.focus()
      expect(document.activeElement).toBe(btn)
    }
  })

  it('renders a static orientation triad with X / Y / Z labels', () => {
    render(<ViewportNavGizmo onSetView={vi.fn()} />)
    const triad = screen.getByTestId('viewport-nav-triad')
    expect(triad.textContent).toBe('XYZ')
  })

  it('does not fire onSetView before any interaction', () => {
    const onSetView = vi.fn()
    render(<ViewportNavGizmo onSetView={onSetView} />)
    expect(onSetView).not.toHaveBeenCalled()
  })
})

describe('VIEW_PRESET_ANGLES — pure preset → camera-angle table', () => {
  it('Top looks straight down (elevation ≈ +90°)', () => {
    // Just shy of the pole (the viewport clamps elevation off ±90° to
    // avoid the lookAt gimbal degeneracy).
    expect(VIEW_PRESET_ANGLES.top.elevation).toBeGreaterThan(Math.PI / 2 - 0.05)
    expect(VIEW_PRESET_ANGLES.top.elevation).toBeLessThanOrEqual(Math.PI / 2)
    expect(VIEW_PRESET_ANGLES.top.azimuth).toBe(0)
    expect(VIEW_PRESET_ANGLES.top.frame).toBe(false)
  })

  it('Front = azimuth 0, elevation 0', () => {
    expect(VIEW_PRESET_ANGLES.front.azimuth).toBe(0)
    expect(VIEW_PRESET_ANGLES.front.elevation).toBe(0)
  })

  it('Right = azimuth +90°, elevation 0', () => {
    expect(VIEW_PRESET_ANGLES.right.azimuth).toBeCloseTo(Math.PI / 2, 10)
    expect(VIEW_PRESET_ANGLES.right.elevation).toBe(0)
  })

  it('Iso = azimuth +45°, elevation +30°, no reframing', () => {
    expect(VIEW_PRESET_ANGLES.iso.azimuth).toBeCloseTo(Math.PI / 4, 10)
    expect(VIEW_PRESET_ANGLES.iso.elevation).toBeCloseTo(Math.PI / 6, 10)
    expect(VIEW_PRESET_ANGLES.iso.frame).toBe(false)
  })

  it('Fit = iso angle + bounds-framing flag (the only preset that reframes radius)', () => {
    expect(VIEW_PRESET_ANGLES.fit.frame).toBe(true)
    expect(VIEW_PRESET_ANGLES.fit.azimuth).toBeCloseTo(VIEW_PRESET_ANGLES.iso.azimuth, 10)
    expect(VIEW_PRESET_ANGLES.fit.elevation).toBeCloseTo(VIEW_PRESET_ANGLES.iso.elevation, 10)
    // Fit is the sole framing preset.
    const framing = PRESETS.filter((p) => VIEW_PRESET_ANGLES[p].frame)
    expect(framing).toEqual(['fit'])
  })
})
