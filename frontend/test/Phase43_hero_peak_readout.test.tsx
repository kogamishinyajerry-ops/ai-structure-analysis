// FM-04a Phase 43 — hero peak-result readout banner.
//
// Tier 1 engineering candidate; not signed validation; not benchmark
// agreement. This suite verifies the extracted HeroPeakReadout
// subcomponent (frontend/src/components/HeroPeakReadout.tsx), which the
// ResultMeshPlaybackPanel mounts above the MetricGrid.
//
// What it pins (per the Phase 43 spec):
//   (a) the formatted peak value (summary.valueMax) + the field label
//       are displayed;
//   (b) the readout uses a LARGER font-size token than the MetricGrid
//       cells — asserted via the exported token string, and confirmed
//       that token (--fs-xl) is not the MetricGrid cell size (0.9rem);
//   (c) it renders gracefully (no throw, neutral/empty output) when
//       there is no summary data (null label + null value).
//
// Honesty (Tier discipline): units are shown ONLY when supplied; the
// component never fabricates a unit. A no-units case is asserted.

import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import { HeroPeakReadout } from '../src/components/HeroPeakReadout'
import {
  HERO_VALUE_FONT_SIZE_TOKEN,
  formatHeroValue,
  selectActiveFieldPeak,
  FIELD_COMPONENT_LABELS,
} from '../src/components/heroPeakFormat'
import type { ResultMeshElement } from '../src/resultMeshPlayback'
import type { ValueFilterState } from '../src/components/viewportRaycaster'

describe('HeroPeakReadout — Phase 43 hero peak banner', () => {
  it('displays the formatted peak value (valueMax) + field label + units', () => {
    render(
      <HeroPeakReadout fieldLabel="Peak von Mises" valueMax={123456789} units="Pa" />,
    )

    // Field label (a)
    expect(screen.getByText('Peak von Mises')).toBeTruthy()

    // Formatted peak value (a) — matches the panel's formatNumber output.
    const value = screen.getByTestId('hero-peak-value')
    expect(value.textContent).toBe(formatHeroValue(123456789))
    expect(value.textContent).toBe('123,456,789')

    // Units shown only because they were supplied.
    expect(screen.getByText('Pa')).toBeTruthy()
  })

  it('renders the peak value at a larger font-size token than the MetricGrid cells', () => {
    // MetricGrid cells render their value at the literal 0.9rem
    // (ResultMeshPlaybackPanel.tsx MetricGrid). The hero uses --fs-xl
    // (1.6rem), which is unambiguously larger.
    expect(HERO_VALUE_FONT_SIZE_TOKEN).toBe('var(--fs-xl)')
    expect(HERO_VALUE_FONT_SIZE_TOKEN).not.toBe('0.9rem')

    render(<HeroPeakReadout fieldLabel="Peak displacement" valueMax={42} units="mm" />)
    const value = screen.getByTestId('hero-peak-value')
    // The element carries the hero token as its inline font-size.
    expect((value as HTMLElement).style.fontSize).toBe('var(--fs-xl)')
  })

  it('does not fabricate units when none are supplied (honesty)', () => {
    render(<HeroPeakReadout fieldLabel="Result field" valueMax={7.5} />)

    expect(screen.getByText('Result field')).toBeTruthy()
    expect(screen.getByTestId('hero-peak-value').textContent).toBe('7.5')
    // No Pa/MPa/mm fabricated — only label + value present.
    expect(screen.queryByText('Pa')).toBeNull()
    expect(screen.queryByText('MPa')).toBeNull()
    expect(screen.queryByText('mm')).toBeNull()
  })

  it('uses exponential formatting for very small magnitudes (matches MetricGrid)', () => {
    render(<HeroPeakReadout fieldLabel="Peak strain" valueMax={0.0001} units="" />)
    expect(screen.getByTestId('hero-peak-value').textContent).toBe('1.00e-4')
  })

  it('renders gracefully (no throw, neutral output) when summary is absent', () => {
    // Simulates a null summary: no label, no value.
    const { container } = render(
      <HeroPeakReadout fieldLabel={null} valueMax={null} />,
    )
    // Renders nothing rather than crashing or printing a bogus "0".
    expect(container.querySelector('[data-testid="hero-peak-readout"]')).toBeNull()
    expect(container.textContent).toBe('')
  })

  it('still renders a neutral headline when only a value is present (no label)', () => {
    render(<HeroPeakReadout fieldLabel={undefined} valueMax={500} units="Pa" />)
    // Neutral placeholder label, real value — does not crash.
    expect(screen.getByText('Peak result')).toBeTruthy()
    expect(screen.getByTestId('hero-peak-value').textContent).toBe('500')
  })
})

describe('selectActiveFieldPeak — Phase 43 Codex R0 P2 (hero tracks active component)', () => {
  const tensor = (sxx: number, syy: number): ResultMeshElement => ({
    value: sxx, // scalar value path (von Mises in the real payload)
    stressTensor: { sxx, syy, szz: 0, sxy: 0, syz: 0, sxz: 0 },
  })
  const input = {
    fieldLabel: 'Von Mises stress',
    valueMax: 9_000,
    elements: [tensor(100, 700), tensor(500, 200), tensor(300, 400)],
  }

  it('returns the scalar summary peak + label for the Mises default', () => {
    // The default path is authoritative — it must NOT recompute from elements.
    expect(selectActiveFieldPeak(input, 'mises')).toEqual({
      label: 'Von Mises stress',
      value: 9_000,
    })
  })

  it('recomputes the peak + component label for an active σ-component', () => {
    // σxx peak over the elements is 500 (not the scalar 9000) — proving the
    // headline tracks the displayed component, not the von Mises summary.
    expect(selectActiveFieldPeak(input, 'sxx')).toEqual({
      label: FIELD_COMPONENT_LABELS.sxx,
      value: 500,
    })
    // A different component resolves to its own peak (σyy → 700).
    expect(selectActiveFieldPeak(input, 'syy')).toEqual({
      label: FIELD_COMPONENT_LABELS.syy,
      value: 700,
    })
  })

  it('falls back to the scalar summary when no tensor data is reachable', () => {
    // Defensive: the switcher is gated on tensor presence, but if a component
    // is requested with tensor-less elements we must not report -Infinity.
    const noTensor = { fieldLabel: 'Displacement', valueMax: 42, elements: [{ value: 5 }] }
    expect(selectActiveFieldPeak(noTensor, 'sxx')).toEqual({
      label: 'Displacement',
      value: 42,
    })
  })

  it('includes scalar-only elements on MIXED frames (Codex R1 P2)', () => {
    // A frame where some elements carry a stressTensor and others rely on the
    // scalar `value` fallback. The viewport colors the scalar-only elements via
    // that same fallback, so the hero peak MUST consider them — here the
    // scalar-only element (900) is the true maximum, NOT the tensor σxx (300).
    const mixed = {
      fieldLabel: 'Von Mises stress',
      valueMax: 9_000,
      elements: [
        { value: 300, stressTensor: { sxx: 300, syy: 10, szz: 0, sxy: 0, syz: 0, sxz: 0 } },
        { value: 900 }, // scalar-only — displayed via its value for ANY component
      ] as ResultMeshElement[],
    }
    expect(selectActiveFieldPeak(mixed, 'sxx')).toEqual({
      label: FIELD_COMPONENT_LABELS.sxx,
      value: 900,
    })
  })

  it('falls back to the scalar field in SVG mode (Codex R1 P2)', () => {
    // SVG colors by the scalar `value` path (colorForElement) and ignores
    // tensor-component switching — so the headline must NOT advertise σxx there.
    expect(selectActiveFieldPeak(input, 'sxx', 'svg')).toEqual({
      label: 'Von Mises stress',
      value: 9_000,
    })
  })

  it('excludes hidden elements — deleted cells + projectile parts (Codex R1 P2)', () => {
    // The renderer does not field-color deleted cells (alive===false) or
    // projectile parts (drawn fixed gray), so they must not headline the peak.
    const withHidden = {
      fieldLabel: 'Von Mises stress',
      valueMax: 9_000,
      elements: [
        { value: 200, stressTensor: { sxx: 200, syy: 0, szz: 0, sxy: 0, syz: 0, sxz: 0 } },
        { value: 8000, alive: false, stressTensor: { sxx: 8000, syy: 0, szz: 0, sxy: 0, syz: 0, sxz: 0 } },
        { value: 7000, partRole: 'projectile', stressTensor: { sxx: 7000, syy: 0, szz: 0, sxy: 0, syz: 0, sxz: 0 } },
      ] as ResultMeshElement[],
    }
    // Only the first (visible) element counts → σxx peak 200, not 8000 / 7000.
    expect(selectActiveFieldPeak(withHidden, 'sxx', 'webgl')).toEqual({
      label: FIELD_COMPONENT_LABELS.sxx,
      value: 200,
    })
  })

  it('honors an active value-filter when computing the component peak (Codex R1 P2)', () => {
    // A value-filtered-out element is not in the visible contour, so it cannot
    // be the headline — mirror the renderer's applyValueFilter selection.
    const filter: ValueFilterState = { minValue: null, maxValue: 250, mode: 'inside' }
    const filtered = {
      fieldLabel: 'Von Mises stress',
      valueMax: 9_000,
      elements: [
        { value: 200, stressTensor: { sxx: 200, syy: 0, szz: 0, sxy: 0, syz: 0, sxz: 0 } },
        { value: 600, stressTensor: { sxx: 600, syy: 0, szz: 0, sxy: 0, syz: 0, sxz: 0 } },
      ] as ResultMeshElement[],
    }
    // σxx=600 is filtered out (>250); the visible peak is 200.
    expect(selectActiveFieldPeak(filtered, 'sxx', 'webgl', filter)).toEqual({
      label: FIELD_COMPONENT_LABELS.sxx,
      value: 200,
    })
  })
})
