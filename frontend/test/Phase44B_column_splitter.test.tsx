// FM-04a Phase 44 A — ColumnSplitter component tests (additive).
//
// Tier 1 engineering candidate; not signed validation. ARIA contract + keyboard
// nudges + pointer-drag callback wiring. The component wraps setPointerCapture
// in try/catch, so jsdom's missing pointer-capture needs no stub.

import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'

import { ColumnSplitter } from '../src/components/ColumnSplitter'
import { LEFT_MIN, LEFT_MAX } from '../src/state/useColumnLayout'

function setup(overrides: Record<string, unknown> = {}) {
  const onPreview = vi.fn()
  const onCommit = vi.fn()
  const model = {
    track: 'left' as const,
    valueNow: 210,
    valueMin: LEFT_MIN,
    valueMax: LEFT_MAX,
    label: 'Resize project rail',
    onPreview,
    onCommit,
    ...overrides,
  }
  render(<ColumnSplitter {...model} />)
  const el = screen.getByTestId('col-splitter-left')
  return { el, onPreview, onCommit }
}

describe('ColumnSplitter — ARIA', () => {
  it('renders a vertical separator with valuemin/max/now + label + tabindex', () => {
    const { el } = setup()
    expect(el).toHaveAttribute('role', 'separator')
    expect(el).toHaveAttribute('aria-orientation', 'vertical')
    expect(el).toHaveAttribute('aria-valuemin', String(LEFT_MIN))
    expect(el).toHaveAttribute('aria-valuemax', String(LEFT_MAX))
    expect(el).toHaveAttribute('aria-valuenow', '210')
    expect(el).toHaveAttribute('aria-label', 'Resize project rail')
    expect(el).toHaveAttribute('tabindex', '0')
  })
})

describe('ColumnSplitter — keyboard (W3C window-splitter)', () => {
  it('Arrow keys commit ±8 (±32 with Shift); Home/End commit min/max', () => {
    const { el, onCommit } = setup()
    fireEvent.keyDown(el, { key: 'ArrowRight' })
    expect(onCommit).toHaveBeenLastCalledWith('left', 218)
    fireEvent.keyDown(el, { key: 'ArrowLeft' })
    expect(onCommit).toHaveBeenLastCalledWith('left', 202)
    fireEvent.keyDown(el, { key: 'ArrowRight', shiftKey: true })
    expect(onCommit).toHaveBeenLastCalledWith('left', 242)
    fireEvent.keyDown(el, { key: 'Home' })
    expect(onCommit).toHaveBeenLastCalledWith('left', LEFT_MIN)
    fireEvent.keyDown(el, { key: 'End' })
    expect(onCommit).toHaveBeenLastCalledWith('left', LEFT_MAX)
  })
})

describe('ColumnSplitter — pointer drag', () => {
  it('previews during move, marks data-dragging, commits the last width on up', () => {
    const { el, onPreview, onCommit } = setup()
    fireEvent.pointerDown(el, { clientX: 100, pointerId: 1 })
    expect(el).toHaveAttribute('data-dragging', 'true')
    fireEvent.pointerMove(el, { clientX: 140, pointerId: 1 })
    expect(onPreview).toHaveBeenLastCalledWith('left', 250) // 210 + (140 - 100)
    fireEvent.pointerUp(el, { clientX: 140, pointerId: 1 })
    expect(onCommit).toHaveBeenLastCalledWith('left', 250)
    expect(el).not.toHaveAttribute('data-dragging')
  })
  it('does not preview without a preceding pointerdown', () => {
    const { el, onPreview } = setup()
    fireEvent.pointerMove(el, { clientX: 140 })
    expect(onPreview).not.toHaveBeenCalled()
  })
  it('tracks the pointer off the grip and commits on release outside (Codex R1 P3)', () => {
    const { el, onPreview, onCommit } = setup()
    fireEvent.pointerDown(el, { clientX: 100, pointerId: 1 })
    // move + release happen OUTSIDE the 8px grip — the window-level listeners
    // must still drive the drag and commit on release.
    fireEvent.pointerMove(document.body, { clientX: 160 })
    expect(onPreview).toHaveBeenLastCalledWith('left', 270) // 210 + (160 - 100)
    fireEvent.pointerUp(document.body, { clientX: 160 })
    expect(onCommit).toHaveBeenLastCalledWith('left', 270)
    expect(el).not.toHaveAttribute('data-dragging')
  })
})
