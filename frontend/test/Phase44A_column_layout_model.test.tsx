// FM-04a Phase 44 A — column-layout model + hook tests (additive).
//
// Tier 1 engineering candidate; not signed validation. Pure model/storage unit
// tests + a renderHook smoke for the resize hook, plus the Codex R0 P2
// viewport-budget clamp. No App render (the shell wiring is covered by Phase44C
// via a faithful harness).

import { describe, it, expect, beforeEach, afterEach } from 'vitest'
import { renderHook, act } from '@testing-library/react'

import {
  clampW,
  validateColumnLayout,
  createColumnLayoutStorage,
  useColumnLayout,
  railBudget,
  clampLayoutToViewport,
  DEFAULT_COLUMN_LAYOUT,
  COLUMN_LAYOUT_LS_KEY,
  MIN_STAGE_PX,
  GRIP_PX,
  LEFT_MIN,
  LEFT_MAX,
  CASE_MIN,
  CASE_MAX,
} from '../src/state/useColumnLayout'

function setViewport(w: number): void {
  Object.defineProperty(window, 'innerWidth', {
    configurable: true,
    writable: true,
    value: w,
  })
}

describe('clampW', () => {
  it('clamps the left track to [LEFT_MIN, LEFT_MAX]', () => {
    expect(clampW('left', 10)).toBe(LEFT_MIN)
    expect(clampW('left', 9999)).toBe(LEFT_MAX)
    expect(clampW('left', 250)).toBe(250)
  })
  it('clamps the case track to [CASE_MIN, CASE_MAX]', () => {
    expect(clampW('case', 10)).toBe(CASE_MIN)
    expect(clampW('case', 9999)).toBe(CASE_MAX)
    expect(clampW('case', 320)).toBe(320)
  })
  it('non-finite falls back to the track default width', () => {
    expect(clampW('left', Number.NaN)).toBe(DEFAULT_COLUMN_LAYOUT.leftW)
    expect(clampW('case', Number.POSITIVE_INFINITY)).toBe(DEFAULT_COLUMN_LAYOUT.caseW)
  })
})

describe('validateColumnLayout', () => {
  it('returns the default for non-objects / null', () => {
    expect(validateColumnLayout(null)).toEqual(DEFAULT_COLUMN_LAYOUT)
    expect(validateColumnLayout('x')).toEqual(DEFAULT_COLUMN_LAYOUT)
    expect(validateColumnLayout(42)).toEqual(DEFAULT_COLUMN_LAYOUT)
  })
  it('fills missing / wrong-typed fields from the default', () => {
    expect(validateColumnLayout({})).toEqual(DEFAULT_COLUMN_LAYOUT)
    expect(validateColumnLayout({ leftW: 'no', caseW: false })).toEqual(DEFAULT_COLUMN_LAYOUT)
  })
  it('clamps in-range overrides', () => {
    expect(validateColumnLayout({ leftW: 9999, caseW: 5 })).toEqual({
      leftW: LEFT_MAX,
      caseW: CASE_MIN,
    })
    expect(validateColumnLayout({ leftW: 250, caseW: 320 })).toEqual({
      leftW: 250,
      caseW: 320,
    })
  })
})

describe('railBudget + clampLayoutToViewport (Codex R0 P2)', () => {
  it('railBudget reserves stage space on desktop, no clamp below the breakpoint', () => {
    expect(railBudget(1440)).toBe(1440 - MIN_STAGE_PX - 2 * GRIP_PX)
    // at/below the responsive breakpoint the rails are CSS-controlled → no clamp
    // so stored desktop widths are preserved (Codex R1 P2)
    expect(railBudget(900)).toBe(LEFT_MAX + CASE_MAX)
  })
  it('a layout maxed on a large monitor is shrunk to fit a 1280 laptop, case-first', () => {
    const fitted = clampLayoutToViewport({ leftW: LEFT_MAX, caseW: CASE_MAX }, 1280)
    expect(fitted.leftW + fitted.caseW).toBeLessThanOrEqual(railBudget(1280))
    expect(fitted.leftW).toBe(LEFT_MAX) // left preserved; case shrinks first
    expect(fitted.caseW).toBeLessThan(CASE_MAX)
    expect(fitted.caseW).toBeGreaterThanOrEqual(CASE_MIN)
  })
  it('a layout that already fits is unchanged', () => {
    expect(clampLayoutToViewport({ leftW: 210, caseW: 300 }, 1920)).toEqual({
      leftW: 210,
      caseW: 300,
    })
  })
})

describe('createColumnLayoutStorage', () => {
  beforeEach(() => {
    try {
      window.localStorage.clear()
    } catch {
      /* SSR fallback */
    }
  })
  it('round-trips save → load on the LS key', () => {
    const s = createColumnLayoutStorage(globalThis)
    s.save({ leftW: 240, caseW: 360 })
    expect(window.localStorage.getItem(COLUMN_LAYOUT_LS_KEY)).toContain('240')
    expect(s.load()).toEqual({ leftW: 240, caseW: 360 })
  })
  it('load returns the default when absent or corrupted', () => {
    const s = createColumnLayoutStorage(globalThis)
    expect(s.load()).toEqual(DEFAULT_COLUMN_LAYOUT)
    window.localStorage.setItem(COLUMN_LAYOUT_LS_KEY, '{not json')
    expect(s.load()).toEqual(DEFAULT_COLUMN_LAYOUT)
  })
  it('SSR-absent storage → default load + no-op save', () => {
    const s = createColumnLayoutStorage({} as typeof globalThis)
    expect(s.load()).toEqual(DEFAULT_COLUMN_LAYOUT)
    expect(() => s.save({ leftW: 200, caseW: 300 })).not.toThrow()
  })
  it('swallows a throwing setItem (quota / SecurityError)', () => {
    const throwingLs = {
      getItem: () => null,
      setItem: () => {
        throw new Error('quota')
      },
    } as unknown as Storage
    const s = createColumnLayoutStorage({ localStorage: throwingLs } as unknown as typeof globalThis)
    expect(() => s.save({ leftW: 200, caseW: 300 })).not.toThrow()
  })
})

describe('useColumnLayout', () => {
  beforeEach(() => {
    setViewport(1440) // generous desktop so the budget clamp doesn't bite
    try {
      window.localStorage.clear()
    } catch {
      /* SSR fallback */
    }
  })
  afterEach(() => {
    try {
      window.localStorage.clear()
    } catch {
      /* SSR fallback */
    }
  })
  it('exposes default widths + railVars on first mount', () => {
    const { result } = renderHook(() => useColumnLayout())
    expect(result.current.leftW).toBe(DEFAULT_COLUMN_LAYOUT.leftW)
    expect(result.current.caseW).toBe(DEFAULT_COLUMN_LAYOUT.caseW)
    const vars = result.current.railVars as Record<string, string>
    expect(vars['--rail-w']).toBe('210px')
    expect(vars['--caserail-w']).toBe('300px')
    expect(vars['--grip']).toBe('8px')
  })
  it('commit clamps to the track max, updates state, and persists', () => {
    const { result } = renderHook(() => useColumnLayout())
    act(() => {
      result.current.splitterProps.left.onCommit('left', 9999)
    })
    expect(result.current.leftW).toBe(LEFT_MAX)
    expect(createColumnLayoutStorage(globalThis).load().leftW).toBe(LEFT_MAX)
  })
  it('clamps a layout persisted on a larger monitor against the viewport on load (R0 P2)', () => {
    setViewport(1100)
    createColumnLayoutStorage(globalThis).save({ leftW: LEFT_MAX, caseW: CASE_MAX })
    const { result } = renderHook(() => useColumnLayout())
    expect(result.current.leftW + result.current.caseW).toBeLessThanOrEqual(railBudget(1100))
    expect(result.current.caseW).toBeLessThan(CASE_MAX)
  })
  it('preserves saved desktop widths when first loaded below the breakpoint (R1 P2)', () => {
    setViewport(800) // tablet — index.css overrides the rail vars here
    createColumnLayoutStorage(globalThis).save({ leftW: LEFT_MAX, caseW: CASE_MAX })
    const { result } = renderHook(() => useColumnLayout())
    // the stored desktop layout must NOT be shrunk / rewritten
    expect(result.current.leftW).toBe(LEFT_MAX)
    expect(result.current.caseW).toBe(CASE_MAX)
  })
})
