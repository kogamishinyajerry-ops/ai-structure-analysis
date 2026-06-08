// FM-04a Phase 27 C — Apple-tier polish breadth pass tests.
//
// Three deliverables:
//   1. Probe-list row entrance fade-in (.fm04a-probe-row-mount class
//      with 200ms ease-out keyframes + 6px lift)
//   2. Threshold-filter + section-cut slider gradient track
//      (.fm04a-gradient-slider class with -webkit- + -moz- pseudo-
//      element gradients matching the legend)
//   3. Section-cut position hover readout (only rendered while
//      isDraggingCutPosition is true; CSS-positioned readout above
//      the slider)
//
// Anti-gaming guard B:-1 — prefers-reduced-motion: reduce honored.
// Pinned via the CSS textContent (no JSdom mediaQuery mock needed —
// the rule is in the stylesheet itself).
//
// Tier 1 / Tier 2 engineering candidate; not signed validation; not
// benchmark agreement.

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen } from '@testing-library/react'

import {
  installPolishStyles,
  uninstallPolishStyles,
  isPolishInstalled,
  POLISH_CLASS_PROBE_ROW_MOUNT,
  POLISH_CLASS_GRADIENT_SLIDER,
  POLISH_CLASS_SECTION_CUT_READOUT,
  POLISH_CSS_TEXT,
} from '../src/components/polishStyles'
import { ProbeListPanel } from '../src/components/ProbeListPanel'
import { ViewportDepthControls } from '../src/components/ResultMeshPlaybackPanel'
import {
  PROBE_LIST_INITIAL_STATE,
  addProbeEntry,
} from '../src/components/probeList'

describe('Phase 27 C — installPolishStyles helper', () => {
  afterEach(() => {
    uninstallPolishStyles()
  })

  it('injects exactly one <style> tag on first install', () => {
    expect(isPolishInstalled()).toBe(false)
    installPolishStyles()
    expect(isPolishInstalled()).toBe(true)
  })

  it('repeat installs are idempotent (no duplicate <style> tags)', () => {
    installPolishStyles()
    installPolishStyles()
    installPolishStyles()
    const matches = document.querySelectorAll(
      `#fm04a-phase27c-polish-styles`,
    )
    expect(matches.length).toBe(1)
  })

  it('uninstall removes the style tag', () => {
    installPolishStyles()
    expect(isPolishInstalled()).toBe(true)
    uninstallPolishStyles()
    expect(isPolishInstalled()).toBe(false)
  })

  it('B:-1 — CSS includes prefers-reduced-motion rule disabling row animation', () => {
    expect(POLISH_CSS_TEXT).toContain('@media (prefers-reduced-motion: reduce)')
    expect(POLISH_CSS_TEXT).toContain(`.${POLISH_CLASS_PROBE_ROW_MOUNT}`)
    // The reduce-motion block must SET animation: none on the
    // row-mount class. Approximate this with a string search of the
    // CSS for "animation: none" appearing AFTER the media query.
    const idx = POLISH_CSS_TEXT.indexOf('@media (prefers-reduced-motion: reduce)')
    expect(idx).toBeGreaterThan(-1)
    expect(POLISH_CSS_TEXT.slice(idx)).toContain('animation: none')
  })

  it('CSS gradient matches the legend stops (blue → green → orange)', () => {
    expect(POLISH_CSS_TEXT).toContain('#2563eb')
    expect(POLISH_CSS_TEXT).toContain('#10b981')
    expect(POLISH_CSS_TEXT).toContain('#f97316')
  })
})

describe('Phase 27 C — ProbeListPanel row entrance class', () => {
  afterEach(() => {
    uninstallPolishStyles()
  })

  it('each pinned row carries the row-mount animation class', () => {
    const state = addProbeEntry(
      addProbeEntry(PROBE_LIST_INITIAL_STATE, {
        label: 7,
        position: [0, 0, 0],
        fieldValue: 1.0e8,
      }),
      { label: 42, position: [0.5, 0, 0], fieldValue: 2.5e8 },
    )
    render(<ProbeListPanel state={state} />)
    const row0 = screen.getByTestId('probe-row-0')
    const row1 = screen.getByTestId('probe-row-1')
    expect(row0.className).toContain(POLISH_CLASS_PROBE_ROW_MOUNT)
    expect(row1.className).toContain(POLISH_CLASS_PROBE_ROW_MOUNT)
  })

  it('mounting the panel installs the polish stylesheet', () => {
    expect(isPolishInstalled()).toBe(false)
    render(<ProbeListPanel state={PROBE_LIST_INITIAL_STATE} />)
    expect(isPolishInstalled()).toBe(true)
  })
})

describe('Phase 27 C — ViewportDepthControls slider polish', () => {
  afterEach(() => {
    uninstallPolishStyles()
  })

  function defaultProps() {
    return {
      deformationScale: 1,
      onDeformationScaleChange: vi.fn(),
      sectionCut: { axis: 'x' as const, positionM: 0, showLow: true },
      onSectionCutChange: vi.fn(),
      valueFilter: { minValue: 0.1, maxValue: 0.9, mode: 'inside' as const },
      onValueFilterChange: vi.fn(),
      valueRange: [0, 1] as [number, number],
    }
  }

  it('value-filter min slider carries the gradient class', () => {
    render(<ViewportDepthControls {...defaultProps()} />)
    const slider = screen.getByTestId('value-filter-min')
    expect(slider.className).toContain(POLISH_CLASS_GRADIENT_SLIDER)
  })

  it('value-filter max slider carries the gradient class', () => {
    render(<ViewportDepthControls {...defaultProps()} />)
    const slider = screen.getByTestId('value-filter-max')
    expect(slider.className).toContain(POLISH_CLASS_GRADIENT_SLIDER)
  })

  it('section-cut position slider carries the gradient class', () => {
    render(<ViewportDepthControls {...defaultProps()} />)
    const slider = screen.getByTestId('section-cut-position')
    expect(slider.className).toContain(POLISH_CLASS_GRADIENT_SLIDER)
  })
})

describe('Phase 27 C — section-cut position hover readout', () => {
  afterEach(() => {
    uninstallPolishStyles()
  })

  function defaultProps() {
    return {
      deformationScale: 1,
      onDeformationScaleChange: vi.fn(),
      sectionCut: { axis: 'x' as const, positionM: 0.25, showLow: true },
      onSectionCutChange: vi.fn(),
      valueFilter: null,
      onValueFilterChange: vi.fn(),
      valueRange: [0, 1] as [number, number],
    }
  }

  it('readout is NOT rendered initially (not dragging)', () => {
    render(<ViewportDepthControls {...defaultProps()} />)
    expect(screen.queryByTestId('section-cut-position-readout')).toBeNull()
  })

  it('readout appears on mouseDown of the slider', () => {
    render(<ViewportDepthControls {...defaultProps()} />)
    const slider = screen.getByTestId('section-cut-position')
    fireEvent.mouseDown(slider)
    const readout = screen.getByTestId('section-cut-position-readout')
    expect(readout).toBeTruthy()
    expect(readout.textContent).toContain('x = 0.25 m')
  })

  it('readout disappears on mouseUp', () => {
    render(<ViewportDepthControls {...defaultProps()} />)
    const slider = screen.getByTestId('section-cut-position')
    fireEvent.mouseDown(slider)
    expect(screen.queryByTestId('section-cut-position-readout')).toBeTruthy()
    fireEvent.mouseUp(slider)
    expect(screen.queryByTestId('section-cut-position-readout')).toBeNull()
  })

  it('readout disappears on mouseLeave', () => {
    render(<ViewportDepthControls {...defaultProps()} />)
    const slider = screen.getByTestId('section-cut-position')
    fireEvent.mouseDown(slider)
    expect(screen.queryByTestId('section-cut-position-readout')).toBeTruthy()
    fireEvent.mouseLeave(slider)
    expect(screen.queryByTestId('section-cut-position-readout')).toBeNull()
  })

  it('readout text reflects axis + position from props', () => {
    const props = defaultProps()
    props.sectionCut = { axis: 'z' as const, positionM: -0.5, showLow: true }
    render(<ViewportDepthControls {...props} />)
    const slider = screen.getByTestId('section-cut-position')
    fireEvent.mouseDown(slider)
    expect(screen.getByTestId('section-cut-position-readout').textContent).toBe(
      'z = -0.50 m',
    )
  })

  it('readout supports touch (touchStart/touchEnd)', () => {
    render(<ViewportDepthControls {...defaultProps()} />)
    const slider = screen.getByTestId('section-cut-position')
    fireEvent.touchStart(slider)
    expect(screen.queryByTestId('section-cut-position-readout')).toBeTruthy()
    fireEvent.touchEnd(slider)
    expect(screen.queryByTestId('section-cut-position-readout')).toBeNull()
  })
})
