// FM-04a Phase 26 C — probe-list A-vs-baseline diff column tests.
//
// Closes Phase 25 retro punchlist item #2 (probe-list panel needed
// to graduate from "n parallel readouts" to "n COMPARED readouts").
// Adds a Δ column whose value = entry.fieldValue − baseline.fieldValue
// where baseline = first-pinned probe (entry index 0, per D:-2
// PIN ORDER guarantee).
//
// Anti-gaming guards:
//   * D:-2 — baseline is FIRST-PINNED, not "smallest", not "largest",
//     not "selected by user later". Renderer MUST NOT re-sort.
//   * E:-1 — null propagation. Any null fieldValue on either side
//     yields a null diff (no spurious zero), so "no anchor" doesn't
//     visually masquerade as "perfect agreement".
//   * E:-2 — diff column only renders when count ≥ 2. With a single
//     baseline there's nothing to compare to; rendering "—" for the
//     single entry would add visual noise without information.
//
// Tier 1 / Tier 2 engineering candidate; not signed validation; not
// benchmark agreement.

import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'

import {
  PROBE_LIST_INITIAL_STATE,
  addProbeEntry,
  buildDiffPairs,
  type ProbeListState,
} from '../src/components/probeList'
import { ProbeListPanel } from '../src/components/ProbeListPanel'
import type { PickedNodeInfo } from '../src/components/viewportRaycaster'

function makeProbe(
  label: number,
  fieldValue: number | null,
  x = 0,
  y = 0,
  z = 0,
): PickedNodeInfo {
  return { label, position: [x, y, z], fieldValue }
}

function makeState(...entries: PickedNodeInfo[]): ProbeListState {
  return entries.reduce(
    (acc, e) => addProbeEntry(acc, e),
    PROBE_LIST_INITIAL_STATE,
  )
}

describe('Phase 26 C — buildDiffPairs pure helper', () => {
  it('empty state returns an empty array', () => {
    expect(buildDiffPairs(PROBE_LIST_INITIAL_STATE)).toEqual([])
  })

  it('single entry: baseline only, diff=null, isBaseline=true', () => {
    const state = makeState(makeProbe(7, 1.5e8))
    const pairs = buildDiffPairs(state)
    expect(pairs).toHaveLength(1)
    expect(pairs[0].entry.label).toBe(7)
    expect(pairs[0].diff).toBeNull()
    expect(pairs[0].isBaseline).toBe(true)
  })

  it('two entries: baseline=null-diff; second=absolute Δ', () => {
    const state = makeState(
      makeProbe(7, 1.0e8), // baseline
      makeProbe(42, 3.5e8), // Δ = 2.5e8
    )
    const pairs = buildDiffPairs(state)
    expect(pairs[0].isBaseline).toBe(true)
    expect(pairs[0].diff).toBeNull()
    expect(pairs[1].isBaseline).toBe(false)
    expect(pairs[1].diff).toBeCloseTo(2.5e8, -3)
  })

  it('negative Δ is preserved (subtraction is signed)', () => {
    const state = makeState(
      makeProbe(7, 3.0e8), // baseline
      makeProbe(42, 1.0e8), // Δ = -2.0e8
    )
    const pairs = buildDiffPairs(state)
    expect(pairs[1].diff).toBeCloseTo(-2.0e8, -3)
  })

  it('null fieldValue on the entry → diff is null', () => {
    const state = makeState(
      makeProbe(7, 1.0e8),
      makeProbe(42, null),
    )
    const pairs = buildDiffPairs(state)
    expect(pairs[1].diff).toBeNull()
  })

  it('null fieldValue on the baseline → all non-baseline diffs are null', () => {
    const state = makeState(
      makeProbe(7, null), // baseline = no anchor
      makeProbe(42, 5.0e7),
      makeProbe(99, 8.0e7),
    )
    const pairs = buildDiffPairs(state)
    expect(pairs[0].isBaseline).toBe(true)
    expect(pairs[0].diff).toBeNull()
    expect(pairs[1].diff).toBeNull()
    expect(pairs[2].diff).toBeNull()
  })

  it('preserves PIN ORDER (D:-2 anti-gaming guard)', () => {
    // Pin in non-sorted order. The baseline is the FIRST-pinned probe
    // (label 99 here), NOT the smallest label.
    const state = makeState(
      makeProbe(99, 2.0e8),
      makeProbe(7, 5.0e8),
      makeProbe(42, 3.5e8),
    )
    const pairs = buildDiffPairs(state)
    expect(pairs.map((p) => p.entry.label)).toEqual([99, 7, 42])
    expect(pairs[0].isBaseline).toBe(true)
    expect(pairs[1].diff).toBeCloseTo(3.0e8, -3)
    expect(pairs[2].diff).toBeCloseTo(1.5e8, -3)
  })

  it('pure: input state is not mutated', () => {
    const state = makeState(makeProbe(7, 1e8), makeProbe(42, 2e8))
    const before = JSON.parse(JSON.stringify(state))
    buildDiffPairs(state)
    expect(state).toEqual(before)
  })
})

describe('Phase 26 C — ProbeListPanel diff column rendering', () => {
  it('does NOT render the Δ header or cells when count = 0', () => {
    render(<ProbeListPanel state={PROBE_LIST_INITIAL_STATE} />)
    expect(screen.queryByTestId('probe-diff-header')).toBeNull()
  })

  it('does NOT render the Δ header when count = 1 (E:-2 guard)', () => {
    const state = makeState(makeProbe(7, 1.0e8))
    render(<ProbeListPanel state={state} />)
    expect(screen.queryByTestId('probe-diff-header')).toBeNull()
    // The baseline tag is also suppressed when there is nothing to
    // compare against — saves visual real-estate.
    expect(screen.queryByTestId('probe-row-0-baseline-tag')).toBeNull()
  })

  it('renders the Δ header and a "base" tag when count ≥ 2', () => {
    const state = makeState(
      makeProbe(7, 1.0e8),
      makeProbe(42, 3.5e8),
    )
    render(<ProbeListPanel state={state} />)
    expect(screen.queryByTestId('probe-diff-header')).toBeTruthy()
    expect(screen.queryByTestId('probe-row-0-baseline-tag')).toBeTruthy()
    // Second row has no baseline tag.
    expect(screen.queryByTestId('probe-row-1-baseline-tag')).toBeNull()
  })

  it('baseline row Δ cell shows "—" (no spurious 0)', () => {
    const state = makeState(
      makeProbe(7, 1.0e8),
      makeProbe(42, 3.5e8),
    )
    render(<ProbeListPanel state={state} />)
    expect(screen.getByTestId('probe-row-0-diff').textContent).toBe('—')
  })

  it('positive Δ renders with leading "+" sign', () => {
    const state = makeState(
      makeProbe(7, 1.0e8),
      makeProbe(42, 3.5e8), // +2.5e+8
    )
    render(<ProbeListPanel state={state} />)
    const diffCell = screen.getByTestId('probe-row-1-diff')
    expect(diffCell.textContent).toMatch(/^\+/)
    expect(diffCell.textContent).toContain('2.50e+8')
  })

  it('negative Δ renders with leading Unicode "−" minus', () => {
    const state = makeState(
      makeProbe(7, 3.0e8),
      makeProbe(42, 1.0e8), // -2.0e+8
    )
    render(<ProbeListPanel state={state} />)
    const diffCell = screen.getByTestId('probe-row-1-diff')
    // Unicode minus (U+2212), not hyphen-minus.
    expect(diffCell.textContent?.startsWith('−')).toBe(true)
    expect(diffCell.textContent).toContain('2.00e+8')
  })

  it('null fieldValue on the entry → Δ cell shows "—"', () => {
    const state = makeState(
      makeProbe(7, 1.0e8),
      makeProbe(42, null),
    )
    render(<ProbeListPanel state={state} />)
    expect(screen.getByTestId('probe-row-1-diff').textContent).toBe('—')
  })

  it('null fieldValue on the baseline → all rows show "—"', () => {
    const state = makeState(
      makeProbe(7, null),
      makeProbe(42, 5.0e7),
    )
    render(<ProbeListPanel state={state} />)
    expect(screen.getByTestId('probe-row-0-diff').textContent).toBe('—')
    expect(screen.getByTestId('probe-row-1-diff').textContent).toBe('—')
  })

  it('does not affect the existing Phase 24 D pin-order contract', () => {
    // Smoke check: rendering the table with diff column does not
    // reorder rows. Pinned order [99, 7, 42] must read 99 / 7 / 42
    // top-to-bottom.
    const state = makeState(
      makeProbe(99, 2.0e8),
      makeProbe(7, 5.0e8),
      makeProbe(42, 3.5e8),
    )
    render(<ProbeListPanel state={state} />)
    expect(screen.getByTestId('probe-row-0-label').textContent).toContain('99')
    expect(screen.getByTestId('probe-row-1-label').textContent).toContain('7')
    expect(screen.getByTestId('probe-row-2-label').textContent).toContain('42')
  })

  it('CSV export still produces the Phase 25 D schema (no diff column in CSV)', () => {
    // FM-04a Phase 26 C honesty contract: the diff column is a
    // RENDER affordance; CSV stays at the Phase 25 D schema
    // (node_label, x, y, z, field_value). Users importing the CSV
    // compute diffs in their spreadsheet of choice.
    const state = makeState(
      makeProbe(7, 1.0e8),
      makeProbe(42, 3.5e8),
    )
    const capture = vi.fn()
    render(<ProbeListPanel state={state} onExportCsv={capture} />)
    const button = screen.getByTestId('probe-export-csv')
    button.click()
    expect(capture).toHaveBeenCalledTimes(1)
    const csv = capture.mock.calls[0][0] as string
    expect(csv.split('\n')[0]).toBe(
      'node_label,x_m,y_m,z_m,field_value',
    )
    expect(csv).not.toContain('diff')
  })
})
