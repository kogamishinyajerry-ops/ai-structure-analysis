// FM-04a Phase 39 B — in-context hints (Dim 2 novice 80-anchor sub-bullet).
//
// Tier 1 / Tier 2 engineering candidate; not signed validation; not
// benchmark agreement.
//
// Closes the RUBRIC_v2.md Dim 2 80-anchor sub-bullet "in-context bubbles
// attached to ≥5 UI surfaces". Pins: (1) the per-hint dismissal storage,
// (2) the InContextHint component behaviour (render / dismiss-persists /
// hidden-when-dismissed), and (3) a non-brittle source-presence proof that
// 5 DISTINCT surface components each mount an InContextHint with a distinct
// hintId (full-rendering the heavier panels — which fetch / need many props —
// would be brittle; the source check guards the anchor from silent removal).

import { describe, expect, it, beforeEach } from 'vitest'
import { readFileSync } from 'node:fs'
import { render, screen, fireEvent } from '@testing-library/react'
import { InContextHint } from '../src/components/InContextHint'
import {
  hintDismissedStorageKey,
  loadHintDismissed,
  saveHintDismissed,
  clearHintDismissed,
} from '../src/components/hintDismissedStorage'

describe('Phase 39 B — hintDismissedStorage', () => {
  beforeEach(() => clearHintDismissed('t1'))

  it('builds a stable, verbatim per-hint key (C:-1)', () => {
    expect(hintDismissedStorageKey('t1')).toBe(
      'fm04a.in-context-hint.t1.dismissed.v1',
    )
  })

  it('defaults to null (shown) and round-trips dismissed=true (D:-1)', () => {
    expect(loadHintDismissed('t1')).toBeNull()
    saveHintDismissed('t1', true)
    expect(loadHintDismissed('t1')).toBe(true)
  })

  it('treats a corrupted stored value as missing/null (E:-1)', () => {
    window.localStorage.setItem(hintDismissedStorageKey('t1'), 'garbage')
    expect(loadHintDismissed('t1')).toBeNull()
  })
})

describe('Phase 39 B — InContextHint component', () => {
  beforeEach(() => clearHintDismissed('demo'))

  it('renders the label + first-timer text', () => {
    render(<InContextHint hintId="demo" label="Demo" text="hello first-timer" />)
    const hint = screen.getByTestId('in-context-hint-demo')
    expect(hint.textContent).toContain('Demo')
    expect(hint.textContent).toContain('hello first-timer')
  })

  it('has role="note" with an accessible label', () => {
    render(<InContextHint hintId="demo" label="Demo" text="x" />)
    expect(screen.getByRole('note', { name: /Hint: Demo/i })).toBeTruthy()
  })

  it('dismiss hides it AND persists so it stays gone across re-mount (D:-1)', () => {
    const { unmount } = render(
      <InContextHint hintId="demo" label="Demo" text="x" />,
    )
    fireEvent.click(screen.getByTestId('in-context-hint-dismiss-demo'))
    expect(screen.queryByTestId('in-context-hint-demo')).toBeNull()
    expect(loadHintDismissed('demo')).toBe(true)
    unmount()
    render(<InContextHint hintId="demo" label="Demo" text="x" />)
    expect(screen.queryByTestId('in-context-hint-demo')).toBeNull()
  })

  it('renders nothing when already dismissed in storage', () => {
    saveHintDismissed('demo', true)
    render(<InContextHint hintId="demo" label="Demo" text="x" />)
    expect(screen.queryByTestId('in-context-hint-demo')).toBeNull()
  })
})

describe('Phase 39 B — in-context hints attached to ≥5 distinct surfaces', () => {
  const SURFACES: ReadonlyArray<{ readonly file: string; readonly hintId: string }> = [
    { file: 'CaseBrowser.tsx', hintId: 'case-browser' },
    { file: 'BCSetupPillList.tsx', hintId: 'bc-setup' },
    { file: 'AdvisorPanel.tsx', hintId: 'advisor-panel' },
    { file: 'OperatorStatusPanel.tsx', hintId: 'operator-status' },
    { file: 'ProbeListPanel.tsx', hintId: 'probe-list' },
  ]

  it('covers exactly 5 distinct surfaces with distinct hintIds', () => {
    expect(SURFACES.length).toBe(5)
    expect(new Set(SURFACES.map((s) => s.hintId)).size).toBe(5)
  })

  for (const { file, hintId } of SURFACES) {
    it(`${file} imports + mounts InContextHint hintId="${hintId}"`, () => {
      // vitest runs from the frontend/ project root (vitest.config lives
      // there), so resolve the surface source relative to process.cwd().
      const src = readFileSync(`${process.cwd()}/src/components/${file}`, 'utf8')
      expect(src).toContain("InContextHint")
      expect(src).toContain(`hintId="${hintId}"`)
    })
  }
})
