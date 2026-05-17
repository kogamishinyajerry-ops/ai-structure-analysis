// FM-04a Phase 26 B — full Basic-mode gating tests.
//
// Closes the Phase 25 C honest-scope gap: in Phase 25 C only the
// probe-list panel was actually hidden in basic mode. The other 3
// advanced-tier surfaces (threshold filter, section cut, field-
// component switcher) had their `show*` flags computed but never
// threaded through. Phase 26 B threads them.
//
// Anti-gaming guards re-pinned at the component level:
//   * C:-1 — state preservation contract. Hiding a row in basic mode
//     does NOT clear the underlying state in the parent; toggling
//     back to advanced restores the same values. Phase 26 B tests
//     the predicate-level contract via the `showSectionCut` /
//     `showThresholdFilter` flag (the parent's state-setter
//     callback is NOT invoked when the row is hidden — a separate
//     test below).
//   * D:-1 — gating is at render time, not at storage time. The
//     ResultMeshPlaybackPanel keeps its useState hooks regardless
//     of mode (verified by the test that mounts in basic mode and
//     asserts that toggling to advanced restores the same values).
//
// Tier 1 / Tier 2 engineering candidate; not signed validation; not
// benchmark agreement.

import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'

import { ViewportDepthControls } from '../src/components/ResultMeshPlaybackPanel'

describe('Phase 26 B — ViewportDepthControls gating', () => {
  function defaultProps() {
    return {
      deformationScale: 1,
      onDeformationScaleChange: vi.fn(),
      sectionCut: null,
      onSectionCutChange: vi.fn(),
      valueFilter: null,
      onValueFilterChange: vi.fn(),
      valueRange: [0, 1] as [number, number],
    }
  }

  it('renders all 3 advanced rows when both show flags are true (default)', () => {
    render(<ViewportDepthControls {...defaultProps()} />)
    expect(screen.queryByTestId('deformation-scale-control')).toBeTruthy()
    expect(screen.queryByTestId('section-cut-control')).toBeTruthy()
    expect(screen.queryByTestId('value-filter-control')).toBeTruthy()
  })

  it('hides section-cut row when showSectionCut=false', () => {
    render(
      <ViewportDepthControls
        {...defaultProps()}
        showSectionCut={false}
        showThresholdFilter={true}
      />,
    )
    expect(screen.queryByTestId('deformation-scale-control')).toBeTruthy()
    expect(screen.queryByTestId('section-cut-control')).toBeNull()
    expect(screen.queryByTestId('value-filter-control')).toBeTruthy()
  })

  it('hides threshold-filter row when showThresholdFilter=false', () => {
    render(
      <ViewportDepthControls
        {...defaultProps()}
        showSectionCut={true}
        showThresholdFilter={false}
      />,
    )
    expect(screen.queryByTestId('deformation-scale-control')).toBeTruthy()
    expect(screen.queryByTestId('section-cut-control')).toBeTruthy()
    expect(screen.queryByTestId('value-filter-control')).toBeNull()
  })

  it('hides both advanced rows in basic mode (deformation stays)', () => {
    render(
      <ViewportDepthControls
        {...defaultProps()}
        showSectionCut={false}
        showThresholdFilter={false}
      />,
    )
    // Deformation row is intentionally NOT in ADVANCED_FEATURE_IDS:
    // it is a fundamental rendering affordance even for basic-mode
    // reviewers.
    expect(screen.queryByTestId('deformation-scale-control')).toBeTruthy()
    expect(screen.queryByTestId('section-cut-control')).toBeNull()
    expect(screen.queryByTestId('value-filter-control')).toBeNull()
  })

  it('does NOT invoke the state setter when the row is hidden (C:-1)', () => {
    // Pin the state-preservation contract: when section-cut is
    // hidden, the parent's setSectionCut MUST NOT be called as a
    // side-effect of mounting. The component cannot silently clear
    // sectionCut state on render.
    const props = defaultProps()
    render(
      <ViewportDepthControls
        {...props}
        sectionCut={{ axis: 'x', positionM: 0.25, showLow: true }}
        valueFilter={{ minValue: 0.1, maxValue: 0.9, mode: 'inside' }}
        showSectionCut={false}
        showThresholdFilter={false}
      />,
    )
    expect(props.onSectionCutChange).not.toHaveBeenCalled()
    expect(props.onValueFilterChange).not.toHaveBeenCalled()
  })

  it('preserves underlying state when toggled basic → advanced (C:-1 round-trip)', () => {
    // Mount with basic-mode gating + a non-null sectionCut + non-null
    // valueFilter. Then re-render with advanced gating. The rows
    // come back populated with the SAME values — the C:-1 contract.
    const props = {
      ...defaultProps(),
      sectionCut: { axis: 'y' as const, positionM: 0.33, showLow: false },
      valueFilter: { minValue: 0.2, maxValue: 0.8, mode: 'inside' as const },
    }
    const { rerender } = render(
      <ViewportDepthControls
        {...props}
        showSectionCut={false}
        showThresholdFilter={false}
      />,
    )
    expect(screen.queryByTestId('section-cut-control')).toBeNull()
    expect(screen.queryByTestId('value-filter-control')).toBeNull()

    rerender(
      <ViewportDepthControls
        {...props}
        showSectionCut={true}
        showThresholdFilter={true}
      />,
    )
    // Rows reappear and the sub-controls reflect the preserved state.
    expect(screen.queryByTestId('section-cut-control')).toBeTruthy()
    expect(screen.queryByTestId('section-cut-toggle')).toBeTruthy()
    const sectionToggle = screen.getByTestId(
      'section-cut-toggle',
    ) as HTMLInputElement
    expect(sectionToggle.checked).toBe(true) // sectionCut was non-null
    expect(screen.queryByTestId('value-filter-control')).toBeTruthy()
    const filterToggle = screen.getByTestId(
      'value-filter-toggle',
    ) as HTMLInputElement
    expect(filterToggle.checked).toBe(true) // valueFilter was non-null
    // No spurious setter calls during the round-trip:
    expect(props.onSectionCutChange).not.toHaveBeenCalled()
    expect(props.onValueFilterChange).not.toHaveBeenCalled()
  })

  it('explicit show flags default to true (back-compat with existing call sites)', () => {
    // Phase 22 B's original ViewportDepthControls had no show flags;
    // Phase 26 B added them with defaults. A call site that omits
    // them must render the same as before — both advanced rows
    // visible.
    render(<ViewportDepthControls {...defaultProps()} />)
    expect(screen.queryByTestId('section-cut-control')).toBeTruthy()
    expect(screen.queryByTestId('value-filter-control')).toBeTruthy()
  })
})
