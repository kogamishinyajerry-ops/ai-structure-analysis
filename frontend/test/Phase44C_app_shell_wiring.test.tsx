// FM-04a Phase 44 A — shell-wiring integration + App.tsx LOC pin (additive).
//
// Tier 1 engineering candidate; not signed validation. No test renders <App/>
// (fetch/effect-heavy), so this pins the EXACT shell composition App.tsx uses
// (shellRef + railVars on .app-container, two splitters between the rails) via
// a faithful harness, then re-asserts the App.tsx LOC pin (mirrors Phase29B).
// Includes the Codex R0 P1 regression: a drag must survive an unrelated
// re-render.

import { describe, it, expect, beforeEach } from 'vitest'
import { useState } from 'react'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { render, screen, fireEvent } from '@testing-library/react'

import {
  useColumnLayout,
  createColumnLayoutStorage,
} from '../src/state/useColumnLayout'
import { ColumnSplitter } from '../src/components/ColumnSplitter'

function setViewport(w: number): void {
  Object.defineProperty(window, 'innerWidth', {
    configurable: true,
    writable: true,
    value: w,
  })
}

beforeEach(() => {
  setViewport(1440) // generous desktop so the budget clamp doesn't bite
  try {
    window.localStorage.clear()
  } catch {
    /* SSR fallback */
  }
})

// Faithful replica of App.tsx's shell composition: the .app-container carries
// the shell ref + railVars, with the two splitters mounted between the rails in
// DOM order rail | grip | caserail | grip | stage. The ext-rerender button
// (outside the grid) mimics a solver-log / job-poll state update.
function ShellHarness() {
  const [, setTick] = useState(0)
  const { shellRef, railVars, splitterProps, leftW, caseW } = useColumnLayout()
  return (
    <>
      <button data-testid="ext-rerender" onClick={() => setTick((t) => t + 1)}>
        bump
      </button>
      <div className="app-container" ref={shellRef} style={{ display: 'grid', ...railVars }}>
        <div data-testid="rail-left">left {leftW}</div>
        <ColumnSplitter {...splitterProps.left} />
        <div data-testid="rail-case">case {caseW}</div>
        <ColumnSplitter {...splitterProps.case} />
        <div data-testid="stage">stage</div>
      </div>
    </>
  )
}

describe('Phase 44 A — shell wiring', () => {
  it('mounts the shell vars + exactly two separators in rail|grip order', () => {
    const { container } = render(<ShellHarness />)
    const shell = container.querySelector('.app-container') as HTMLElement
    expect(shell.style.getPropertyValue('--rail-w')).toBe('210px')
    expect(shell.style.getPropertyValue('--caserail-w')).toBe('300px')
    expect(shell.style.getPropertyValue('--grip')).toBe('8px')
    const seps = screen.getAllByRole('separator')
    expect(seps).toHaveLength(2)
    expect(seps[0]).toHaveAttribute('data-testid', 'col-splitter-left')
    expect(seps[1]).toHaveAttribute('data-testid', 'col-splitter-case')
  })

  it('a drag on the left splitter updates the shell --rail-w and persists on release', () => {
    const { container } = render(<ShellHarness />)
    const shell = container.querySelector('.app-container') as HTMLElement
    const left = screen.getByTestId('col-splitter-left')
    fireEvent.pointerDown(left, { clientX: 0, pointerId: 1 })
    fireEvent.pointerMove(left, { clientX: 40, pointerId: 1 })
    // imperative preview wrote the custom property on the shell node:
    expect(shell.style.getPropertyValue('--rail-w')).toBe('250px') // 210 + 40
    fireEvent.pointerUp(left, { clientX: 40, pointerId: 1 })
    expect(createColumnLayoutStorage(globalThis).load().leftW).toBe(250)
  })

  it('keeps the previewed width across an unrelated re-render (Codex R0 P1)', () => {
    const { container } = render(<ShellHarness />)
    const shell = container.querySelector('.app-container') as HTMLElement
    const left = screen.getByTestId('col-splitter-left')
    fireEvent.pointerDown(left, { clientX: 0, pointerId: 1 })
    fireEvent.pointerMove(left, { clientX: 40, pointerId: 1 })
    expect(shell.style.getPropertyValue('--rail-w')).toBe('250px')
    // a solver-log / job-poll style re-render must NOT clobber the in-flight drag:
    fireEvent.click(screen.getByTestId('ext-rerender'))
    expect(shell.style.getPropertyValue('--rail-w')).toBe('250px')
    fireEvent.pointerUp(left, { clientX: 40, pointerId: 1 })
    expect(createColumnLayoutStorage(globalThis).load().leftW).toBe(250)
  })
})

describe('Phase 44 A — App.tsx LOC pin', () => {
  it('App.tsx stays below the 1500 LOC pin after the shell wiring', () => {
    const appSource = readFileSync(resolve(__dirname, '../src/App.tsx'), 'utf-8')
    expect(appSource.split('\n').length).toBeLessThan(1500)
  })
})
