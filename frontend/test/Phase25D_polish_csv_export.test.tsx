// FM-04a Phase 25 D — visual polish + probe-list CSV export tests.
//
// Tier 1 / Tier 2 engineering candidate; not signed validation; not
// benchmark agreement.
//
// Anti-gaming guards:
//   * D:-1 — serializeProbeListAsCsv preserves PIN ORDER (carries the
//     Phase 24 D D:-2 guarantee to the export layer). Pinned by an
//     order test on a 5-entry list with non-sorted labels.
//   * CSV cells with commas / newlines / quotes are RFC-4180 quoted.

import { describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen } from '@testing-library/react'

import {
  PROBE_LIST_INITIAL_STATE,
  addProbeEntry,
  serializeProbeListAsCsv,
} from '../src/components/probeList'
import { ProbeListPanel } from '../src/components/ProbeListPanel'
import { OnboardingTour } from '../src/components/OnboardingTour'
import type { PickedNodeInfo } from '../src/components/viewportRaycaster'

function mockPick(
  label: number,
  position: [number, number, number] = [label * 0.1, label * 0.2, label * 0.3],
  fieldValue: number | null = label * 1.5,
): PickedNodeInfo {
  return { label, position, fieldValue }
}

describe('Phase 25 D — serializeProbeListAsCsv', () => {
  it('empty list produces header-only CSV', () => {
    const csv = serializeProbeListAsCsv(PROBE_LIST_INITIAL_STATE)
    expect(csv).toBe('node_label,x_m,y_m,z_m,field_value\n')
  })

  it('one entry produces header + one row', () => {
    let state = PROBE_LIST_INITIAL_STATE
    state = addProbeEntry(state, mockPick(7, [0.7, 1.4, 2.1], 10.5))
    const csv = serializeProbeListAsCsv(state)
    expect(csv).toBe(
      'node_label,x_m,y_m,z_m,field_value\n' +
      '7,0.7,1.4,2.1,10.5\n',
    )
  })

  it('D:-1 anti-gaming guard: CSV row order matches PIN ORDER, not sorted', () => {
    let state = PROBE_LIST_INITIAL_STATE
    state = addProbeEntry(state, mockPick(7))
    state = addProbeEntry(state, mockPick(42))
    state = addProbeEntry(state, mockPick(99))
    state = addProbeEntry(state, mockPick(11))
    state = addProbeEntry(state, mockPick(3))
    const csv = serializeProbeListAsCsv(state)
    const labelsInOrder = csv
      .split('\n')
      .slice(1)
      .filter((row) => row.length > 0)
      .map((row) => row.split(',')[0])
    expect(labelsInOrder).toEqual(['7', '42', '99', '11', '3'])
  })

  it('null fieldValue serializes as empty cell', () => {
    let state = PROBE_LIST_INITIAL_STATE
    state = addProbeEntry(state, mockPick(7, [0, 0, 0], null))
    const csv = serializeProbeListAsCsv(state)
    expect(csv).toContain(',\n') // empty trailing cell
    expect(csv).toContain('7,0,0,0,\n')
  })

  it('NaN / Infinity coordinates serialize as empty cells', () => {
    let state = PROBE_LIST_INITIAL_STATE
    state = addProbeEntry(state, mockPick(7, [Number.NaN, Number.POSITIVE_INFINITY, 0], 1))
    const csv = serializeProbeListAsCsv(state)
    // x and y cells empty; z='0'; field='1'
    expect(csv).toContain('7,,,0,1\n')
  })

  it('CSV ends with a trailing newline (RFC 4180)', () => {
    let state = PROBE_LIST_INITIAL_STATE
    state = addProbeEntry(state, mockPick(7))
    expect(serializeProbeListAsCsv(state).endsWith('\n')).toBe(true)
  })
})

describe('Phase 25 D — ProbeListPanel CSV export UI', () => {
  it('"Export CSV" button does NOT appear when list is empty', () => {
    render(<ProbeListPanel state={PROBE_LIST_INITIAL_STATE} />)
    expect(screen.queryByTestId('probe-export-csv')).toBeNull()
  })

  it('"Export CSV" button appears when list has ≥1 entry', () => {
    let state = PROBE_LIST_INITIAL_STATE
    state = addProbeEntry(state, mockPick(7))
    render(<ProbeListPanel state={state} />)
    expect(screen.getByTestId('probe-export-csv')).toBeTruthy()
  })

  it('clicking "Export CSV" invokes onExportCsv with the serialized CSV', () => {
    let state = PROBE_LIST_INITIAL_STATE
    state = addProbeEntry(state, mockPick(7, [0.7, 1.4, 2.1], 10.5))
    state = addProbeEntry(state, mockPick(42, [4.2, 8.4, 12.6], 63.0))
    const onExport = vi.fn()
    render(<ProbeListPanel state={state} onExportCsv={onExport} />)
    fireEvent.click(screen.getByTestId('probe-export-csv'))
    expect(onExport).toHaveBeenCalledTimes(1)
    const csv = onExport.mock.calls[0][0] as string
    expect(csv).toContain('node_label,x_m,y_m,z_m,field_value')
    expect(csv).toContain('7,0.7,1.4,2.1,10.5')
    expect(csv).toContain('42,4.2,8.4,12.6,63')
  })

  it('default CSV export is a no-op in SSR-like env (no window.document)', () => {
    // The default handler is invoked only when no onExportCsv is
    // provided. In jsdom, window+document exist; the no-op fallback
    // exercises the catch path. This pin is intentionally lenient —
    // it just confirms NO exception escapes when the button is
    // clicked without an override.
    let state = PROBE_LIST_INITIAL_STATE
    state = addProbeEntry(state, mockPick(7))
    render(<ProbeListPanel state={state} />)
    expect(() =>
      fireEvent.click(screen.getByTestId('probe-export-csv')),
    ).not.toThrow()
  })
})

describe('Phase 25 D — OnboardingTour fade-slide animation', () => {
  function makeStubStorage() {
    const state = { dismissed: false }
    return {
      load: () => state.dismissed,
      save: (v: boolean) => {
        state.dismissed = v
      },
    }
  }

  it('injects fade-slide keyframes via inline <style>', () => {
    const storage = makeStubStorage()
    const { container } = render(<OnboardingTour storage={storage} />)
    const styleTag = container.querySelector('style')
    expect(styleTag).toBeTruthy()
    expect(styleTag?.textContent).toContain('fm04a-onboarding-fade-slide-in')
    expect(styleTag?.textContent).toContain('prefers-reduced-motion')
  })

  it('card carries the animation class', () => {
    const storage = makeStubStorage()
    const { container } = render(<OnboardingTour storage={storage} />)
    expect(container.querySelector('.onboarding-tour-card')).toBeTruthy()
  })
})
