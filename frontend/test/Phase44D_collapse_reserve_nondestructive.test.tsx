// FM-04a Phase 44 B — collapse + chat-reserve + non-destructive resize (additive).
//
// Tier 1 engineering candidate; not signed validation. Covers the two folded
// Codex R2 fixes (P2a chat reserve, P2b non-destructive resize) + the new
// collapse/expand. New filename (Phase44B_* is taken by the 44A splitter test).

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { renderHook, act, render, screen, fireEvent } from '@testing-library/react'

import {
  railBudget,
  clampLayoutToViewport,
  projectLayout,
  validateCollapseState,
  createCollapseStorage,
  useColumnLayout,
  COLLAPSED_STRIP_PX,
  COLLAPSE_LS_KEY,
  COLUMN_LAYOUT_LS_KEY,
  MIN_STAGE_PX,
  GRIP_PX,
  LEFT_MIN,
  LEFT_MAX,
  CASE_MIN,
  CASE_MAX,
} from '../src/state/useColumnLayout'
import { ColumnSplitter } from '../src/components/ColumnSplitter'

function setViewport(w: number): void {
  Object.defineProperty(window, 'innerWidth', { configurable: true, writable: true, value: w })
}

beforeEach(() => {
  setViewport(1920)
  try {
    window.localStorage.clear()
  } catch {
    /* SSR fallback */
  }
})
afterEach(() => {
  vi.restoreAllMocks()
})

// ── P2a — chat-aware stage reserve ──────────────────────────────────────────
describe('Phase 44 B — chat-aware stage reserve (R2 P2a)', () => {
  it('railBudget subtracts the chat reserve on desktop', () => {
    expect(railBudget(1440, 340)).toBe(1440 - MIN_STAGE_PX - 340 - 2 * GRIP_PX)
    expect(railBudget(1440, 0)).toBe(1440 - MIN_STAGE_PX - 2 * GRIP_PX)
  })
  it('railBudget below the breakpoint ignores the reserve (R1 P2 preserved)', () => {
    expect(railBudget(900, 340)).toBe(LEFT_MAX + CASE_MAX)
  })
  it('with chat open, maxed rails are clamped to leave the reserved stage', () => {
    const fitted = clampLayoutToViewport({ leftW: LEFT_MAX, caseW: CASE_MAX }, 1280, 340)
    expect(fitted.leftW + fitted.caseW).toBeLessThanOrEqual(railBudget(1280, 340))
  })
})

// ── P2b — non-destructive resize ────────────────────────────────────────────
describe('Phase 44 B — non-destructive resize (R2 P2b)', () => {
  it('resize never persists; widening restores the saved desktop layout', () => {
    setViewport(1920)
    const setItemSpy = vi.spyOn(Storage.prototype, 'setItem')
    const { result } = renderHook(() => useColumnLayout())

    act(() => result.current.splitterProps.case.onCommit('case', 480))
    expect(result.current.caseW).toBe(480) // displayed === saved at 1920

    act(() => {
      setViewport(1100)
      window.dispatchEvent(new Event('resize'))
    })
    expect(result.current.caseW).toBeLessThan(480) // displayed clamped, NOT persisted

    act(() => {
      setViewport(1920)
      window.dispatchEvent(new Event('resize'))
    })
    expect(result.current.caseW).toBe(480) // saved restored — the P2b proof

    // storage.save fired EXACTLY once (the commit), never on either resize:
    const widthSaves = setItemSpy.mock.calls.filter(([k]) => k === COLUMN_LAYOUT_LS_KEY)
    expect(widthSaves).toHaveLength(1)
  })
})

// ── Collapse model + persistence ────────────────────────────────────────────
describe('Phase 44 B — collapse model', () => {
  it('validateCollapseState defaults missing / wrong-typed fields to false', () => {
    expect(validateCollapseState(null)).toEqual({ left: false, case: false })
    expect(validateCollapseState({})).toEqual({ left: false, case: false })
    expect(validateCollapseState({ left: true })).toEqual({ left: true, case: false })
    expect(validateCollapseState({ left: 'x', case: 1 })).toEqual({ left: false, case: false })
  })
  it('createCollapseStorage round-trips; an absent key → both uncollapsed (44A upgrade)', () => {
    const s = createCollapseStorage(globalThis)
    expect(s.load()).toEqual({ left: false, case: false })
    s.save({ left: true, case: false })
    expect(window.localStorage.getItem(COLLAPSE_LS_KEY)).toContain('"left":true')
    expect(s.load()).toEqual({ left: true, case: false })
  })
  it('projectLayout: a collapsed rail becomes a strip and frees its budget', () => {
    const out = projectLayout({ leftW: 210, caseW: 300 }, { left: true, case: false }, 1440, 0)
    expect(out.leftW).toBe(COLLAPSED_STRIP_PX)
    expect(out.caseW).toBe(300) // case keeps its width (left no longer competes)
  })
  it('projectLayout: both collapsed → two strips', () => {
    expect(projectLayout({ leftW: 210, caseW: 300 }, { left: true, case: true }, 1440, 0)).toEqual({
      leftW: COLLAPSED_STRIP_PX,
      caseW: COLLAPSED_STRIP_PX,
    })
  })
  it('projectLayout: a collapsed strip counts against the budget — stage not starved (R0 P2)', () => {
    // mid-width desktop + chat open, left collapsed, case live near its max: the
    // 14px strip must be reserved so left+case never exceeds the rail budget.
    const out = projectLayout({ leftW: 210, caseW: 480 }, { left: true, case: false }, 1300, 340)
    expect(out.leftW).toBe(COLLAPSED_STRIP_PX)
    expect(out.leftW + out.caseW).toBeLessThanOrEqual(railBudget(1300, 340))
  })
})

describe('Phase 44 B — collapse hook behaviour', () => {
  it('toggle collapses to the strip, persists, and restores on a second toggle', () => {
    const { result } = renderHook(() => useColumnLayout())
    const vars = () => result.current.railVars as Record<string, string>
    expect(vars()['--rail-w']).toBe('210px')

    act(() => result.current.splitterProps.left.onToggleCollapse?.('left'))
    expect(vars()['--rail-w']).toBe(`${COLLAPSED_STRIP_PX}px`)
    expect(result.current.splitterProps.left.collapsed).toBe(true)
    expect(createCollapseStorage(globalThis).load().left).toBe(true)

    act(() => result.current.splitterProps.left.onToggleCollapse?.('left'))
    expect(vars()['--rail-w']).toBe('210px') // saved width restored
    expect(result.current.splitterProps.left.collapsed).toBe(false)
  })
})

// ── ColumnSplitter collapse UX ──────────────────────────────────────────────
describe('Phase 44 B — ColumnSplitter collapse UX', () => {
  function setup(overrides: Record<string, unknown> = {}) {
    const onToggleCollapse = vi.fn()
    const model = {
      track: 'left' as const,
      valueNow: 210,
      valueMin: LEFT_MIN,
      valueMax: LEFT_MAX,
      label: 'Resize project rail',
      collapsed: false,
      onPreview: vi.fn(),
      onCommit: vi.fn(),
      onToggleCollapse,
      ...overrides,
    }
    render(<ColumnSplitter {...model} />)
    return { el: screen.getByTestId('col-splitter-left'), onToggleCollapse }
  }

  it('collapsed → aria-valuenow 0 + an expand chevron that toggles', () => {
    const { el, onToggleCollapse } = setup({ collapsed: true })
    expect(el).toHaveAttribute('aria-valuenow', '0')
    expect(el).toHaveAttribute('data-collapsed', '')
    const chevron = screen.getByTestId('col-splitter-expand-left')
    fireEvent.click(chevron)
    expect(onToggleCollapse).toHaveBeenCalledWith('left')
  })

  it('double-click, Enter, and Space all toggle collapse', () => {
    const { el, onToggleCollapse } = setup()
    fireEvent.doubleClick(el)
    fireEvent.keyDown(el, { key: 'Enter' })
    fireEvent.keyDown(el, { key: ' ' })
    expect(onToggleCollapse).toHaveBeenCalledTimes(3)
    expect(onToggleCollapse).toHaveBeenLastCalledWith('left')
  })

  it('while collapsed, resize keys are inert-but-consumed; Enter still expands (R0 P2 / R1 P3)', () => {
    const onCommit = vi.fn()
    const onToggleCollapse = vi.fn()
    const { el } = setup({ collapsed: true, valueNow: 0, onCommit, onToggleCollapse })
    // Arrow/Home/End must NOT commit — committing valueNow(=0)±step would clobber
    // the hidden rail's saved width, breaking non-destructive restore (R0 P2).
    // They must STILL be consumed (preventDefault) so a focused collapsed splitter
    // doesn't scroll the overflow:auto pane (R1 P3). fireEvent returns false when
    // the dispatched cancelable event had preventDefault() called.
    for (const key of ['ArrowLeft', 'ArrowRight', 'Home', 'End']) {
      const notCancelled = fireEvent.keyDown(el, { key })
      expect(notCancelled).toBe(false) // preventDefault was called → key consumed
    }
    expect(onCommit).not.toHaveBeenCalled()
    // An unhandled key (e.g. Tab) is NOT consumed — focus traversal still works.
    expect(fireEvent.keyDown(el, { key: 'Tab' })).toBe(true)
    // Enter/Space still reach the toggle so a collapsed rail is keyboard-recoverable.
    fireEvent.keyDown(el, { key: 'Enter' })
    expect(onToggleCollapse).toHaveBeenCalledWith('left')
  })

  it('a legacy model without onToggleCollapse does not throw on toggle gestures', () => {
    const onPreview = vi.fn()
    const onCommit = vi.fn()
    render(
      <ColumnSplitter
        track="case"
        valueNow={300}
        valueMin={CASE_MIN}
        valueMax={CASE_MAX}
        label="Resize case rail"
        onPreview={onPreview}
        onCommit={onCommit}
      />,
    )
    const el = screen.getByTestId('col-splitter-case')
    expect(() => {
      fireEvent.doubleClick(el)
      fireEvent.keyDown(el, { key: 'Enter' })
    }).not.toThrow()
  })
})
