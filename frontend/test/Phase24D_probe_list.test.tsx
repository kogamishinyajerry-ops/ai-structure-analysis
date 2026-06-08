// FM-04a Phase 24 D — multi-node probe list tests.
//
// Tier 1 / Tier 2 engineering candidate; not signed validation; not
// benchmark agreement.
//
// Phase 24 D extends Phase 23 C single-node pick to multi-node probe
// list (max 8). The reducer in probeList.ts is pure; the
// ProbeListPanel component renders the table.
//
// Anti-gaming guards:
//   * D:-2 — entries stored in INSERTION (pin) ORDER. Test pins 5
//     nodes with labels [7, 42, 99, 11, 3]; asserts the rendered
//     table reads them in PIN order, not sorted by label, not by
//     array index.

import { describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen } from '@testing-library/react'

import {
  PROBE_LIST_INITIAL_STATE,
  PROBE_LIST_MAX,
  addProbeEntry,
  clearAllProbes,
  hasProbe,
  probeCount,
  removeProbeEntry,
  type ProbeListState,
} from '../src/components/probeList'
import { ProbeListPanel } from '../src/components/ProbeListPanel'
import type { PickedNodeInfo } from '../src/components/viewportRaycaster'

function mockPick(label: number, value: number | null = label * 1.5): PickedNodeInfo {
  return {
    label,
    position: [label * 0.1, label * 0.2, label * 0.3],
    fieldValue: value,
  }
}

describe('Phase 24 D — probeList reducer', () => {
  it('initial state has no entries', () => {
    expect(PROBE_LIST_INITIAL_STATE.entries).toEqual([])
    expect(probeCount(PROBE_LIST_INITIAL_STATE)).toBe(0)
  })

  it('addProbeEntry appends in pin order', () => {
    let state = PROBE_LIST_INITIAL_STATE
    state = addProbeEntry(state, mockPick(7))
    state = addProbeEntry(state, mockPick(42))
    state = addProbeEntry(state, mockPick(99))
    expect(state.entries.map((e) => e.label)).toEqual([7, 42, 99])
  })

  it('addProbeEntry is a no-op when label is already pinned (dedup)', () => {
    let state = PROBE_LIST_INITIAL_STATE
    state = addProbeEntry(state, mockPick(7))
    const before = state
    state = addProbeEntry(state, mockPick(7))
    expect(state).toBe(before)
  })

  it('addProbeEntry evicts the oldest entry when at PROBE_LIST_MAX', () => {
    let state = PROBE_LIST_INITIAL_STATE
    for (let i = 1; i <= PROBE_LIST_MAX; i++) {
      state = addProbeEntry(state, mockPick(i))
    }
    expect(state.entries.map((e) => e.label)).toEqual([1, 2, 3, 4, 5, 6, 7, 8])
    state = addProbeEntry(state, mockPick(99))
    // Oldest (1) evicted; 99 appended.
    expect(state.entries.map((e) => e.label)).toEqual([2, 3, 4, 5, 6, 7, 8, 99])
    expect(probeCount(state)).toBe(PROBE_LIST_MAX)
  })

  it('removeProbeEntry removes by label and preserves order of survivors', () => {
    let state = PROBE_LIST_INITIAL_STATE
    state = addProbeEntry(state, mockPick(7))
    state = addProbeEntry(state, mockPick(42))
    state = addProbeEntry(state, mockPick(99))
    state = removeProbeEntry(state, 42)
    expect(state.entries.map((e) => e.label)).toEqual([7, 99])
  })

  it('removeProbeEntry is a no-op for an absent label', () => {
    let state = PROBE_LIST_INITIAL_STATE
    state = addProbeEntry(state, mockPick(7))
    const before = state
    state = removeProbeEntry(state, 999)
    expect(state).toBe(before)
  })

  it('clearAllProbes resets to initial state', () => {
    let state = PROBE_LIST_INITIAL_STATE
    state = addProbeEntry(state, mockPick(7))
    state = addProbeEntry(state, mockPick(42))
    expect(probeCount(state)).toBe(2)
    state = clearAllProbes(state)
    expect(state).toEqual(PROBE_LIST_INITIAL_STATE)
  })

  it('hasProbe reports pinned membership correctly', () => {
    let state = PROBE_LIST_INITIAL_STATE
    state = addProbeEntry(state, mockPick(7))
    expect(hasProbe(state, 7)).toBe(true)
    expect(hasProbe(state, 99)).toBe(false)
  })

  it('D:-2 anti-gaming: 5 pins of labels [7, 42, 99, 11, 3] render in PIN order, not sorted', () => {
    let state = PROBE_LIST_INITIAL_STATE
    state = addProbeEntry(state, mockPick(7))
    state = addProbeEntry(state, mockPick(42))
    state = addProbeEntry(state, mockPick(99))
    state = addProbeEntry(state, mockPick(11))
    state = addProbeEntry(state, mockPick(3))

    // Sorted-by-label would be [3, 7, 11, 42, 99].
    // Sorted-by-array-index would happen to equal pin order here
    // (since we always push to end), so we ALSO check that a
    // reordering test (e.g. remove+re-add) preserves chronological.
    expect(state.entries.map((e) => e.label)).toEqual([7, 42, 99, 11, 3])

    // Now render and verify the rendered row order matches.
    // FM-04a Phase 26 C — the baseline row (index 0) now carries a
    // "base" tag inside the same <td>; use textContent contains to
    // tolerate the extra annotation.
    render(<ProbeListPanel state={state} />)
    for (let i = 0; i < state.entries.length; i++) {
      const labelEl = screen.getByTestId(`probe-row-${i}-label`)
      expect(labelEl.textContent).toContain(String(state.entries[i].label))
    }
  })

  it('D:-2 follow-up: after remove + re-add, order is [survivors..., reinserted]', () => {
    let state = PROBE_LIST_INITIAL_STATE
    state = addProbeEntry(state, mockPick(7))
    state = addProbeEntry(state, mockPick(42))
    state = addProbeEntry(state, mockPick(99))
    state = removeProbeEntry(state, 7)
    expect(state.entries.map((e) => e.label)).toEqual([42, 99])
    state = addProbeEntry(state, mockPick(7))
    expect(state.entries.map((e) => e.label)).toEqual([42, 99, 7])
  })
})

describe('Phase 24 D — ProbeListPanel component', () => {
  it('renders empty state with no pinned entries', () => {
    render(<ProbeListPanel state={PROBE_LIST_INITIAL_STATE} />)
    expect(screen.getByTestId('probe-list-empty')).toBeTruthy()
    expect(screen.getByTestId('probe-list-count').textContent).toContain('0 /')
  })

  it('renders a table with one row per pinned entry', () => {
    let state = PROBE_LIST_INITIAL_STATE
    state = addProbeEntry(state, mockPick(7, 1.23e5))
    state = addProbeEntry(state, mockPick(42, 9.87e6))
    render(<ProbeListPanel state={state} />)
    expect(screen.getByTestId('probe-list-table')).toBeTruthy()
    // FM-04a Phase 26 C — baseline row carries a "base" tag inside
    // the same <td>; assert contains, not strict equality.
    expect(screen.getByTestId('probe-row-0-label').textContent).toContain('7')
    expect(screen.getByTestId('probe-row-1-label').textContent).toContain('42')
  })

  it('fires onRemove(label) when a remove button is clicked', () => {
    let state = PROBE_LIST_INITIAL_STATE
    state = addProbeEntry(state, mockPick(7))
    state = addProbeEntry(state, mockPick(42))
    const onRemove = vi.fn()
    render(<ProbeListPanel state={state} onRemove={onRemove} />)
    fireEvent.click(screen.getByTestId('probe-remove-42'))
    expect(onRemove).toHaveBeenCalledWith(42)
  })

  it('fires onClearAll when "Clear all" is clicked', () => {
    let state = PROBE_LIST_INITIAL_STATE
    state = addProbeEntry(state, mockPick(7))
    const onClearAll = vi.fn()
    render(<ProbeListPanel state={state} onClearAll={onClearAll} />)
    fireEvent.click(screen.getByTestId('probe-clear-all'))
    expect(onClearAll).toHaveBeenCalled()
  })

  it('shows "+ Pin" button when activePick is supplied and not yet pinned', () => {
    const active = mockPick(7)
    const onPin = vi.fn()
    render(
      <ProbeListPanel
        state={PROBE_LIST_INITIAL_STATE}
        activePick={active}
        onPinActive={onPin}
      />,
    )
    const btn = screen.getByTestId('probe-pin-active')
    expect(btn.hasAttribute('disabled') || btn.getAttribute('aria-disabled') === 'true').toBe(false)
    fireEvent.click(btn)
    expect(onPin).toHaveBeenCalled()
  })

  it('disables "+ Pin" when activePick label is already in list', () => {
    let state = PROBE_LIST_INITIAL_STATE
    state = addProbeEntry(state, mockPick(7))
    const active = mockPick(7)
    render(<ProbeListPanel state={state} activePick={active} />)
    const btn = screen.getByTestId('probe-pin-active') as HTMLButtonElement
    expect(btn.disabled || btn.getAttribute('aria-disabled') === 'true').toBe(true)
  })

  it('disables "+ Pin" when list is at PROBE_LIST_MAX capacity', () => {
    let state = PROBE_LIST_INITIAL_STATE
    for (let i = 1; i <= PROBE_LIST_MAX; i++) {
      state = addProbeEntry(state, mockPick(i))
    }
    const active = mockPick(99)
    render(<ProbeListPanel state={state} activePick={active} />)
    const btn = screen.getByTestId('probe-pin-active') as HTMLButtonElement
    expect(btn.disabled || btn.getAttribute('aria-disabled') === 'true').toBe(true)
  })

  it('renders fieldValue as scientific notation; — for null', () => {
    let state = PROBE_LIST_INITIAL_STATE
    state = addProbeEntry(state, mockPick(7, 1.234e5))
    state = addProbeEntry(state, mockPick(42, null))
    const { container } = render(<ProbeListPanel state={state} />)
    const text = container.textContent ?? ''
    expect(text).toContain('1.23e+5')
    expect(text).toContain('—')
  })
})
