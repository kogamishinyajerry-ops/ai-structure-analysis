// FM-04a Phase 28 C — probe row EXIT animation + "Restored N probes"
// toast tests.
//
// Two deliveries pinned in one test file:
//
// 1. Probe row EXIT animation. ProbeListPanel exposes an
//    `exitingLabel` prop; while non-null, the matching <tr> swaps
//    its className from POLISH_CLASS_PROBE_ROW_MOUNT to
//    POLISH_CLASS_PROBE_ROW_UNMOUNT (150ms fade-out). The parent
//    panel (ResultMeshPlaybackPanel) orchestrates the timing: set
//    exitingLabel → 150ms later, actually remove + clear.
//    Anti-gaming guard E:-1: total settle time ≤ 200ms — pinned by
//    parsing the animation duration directly out of POLISH_CSS_TEXT.
//
// 2. "Restored N probes from your last session" toast. On case
//    mount, if loadProbeList returned ≥ 1 entries, the toast
//    appears top-right with a dismiss × button and auto-fades after
//    4 seconds. Closes Phase 27 D's silent-restoration miss.
//    Anti-gaming guard D:-1: the toast does NOT clear the
//    restored probes (additive UX cue only); the probes remain
//    pinned regardless of toast dismissal.
//
// prefers-reduced-motion: reduce honored — both new animation
// classes have animation: none under the @media rule.
//
// Tier 1 / Tier 2 engineering candidate; not signed validation;
// not benchmark agreement.

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { act, fireEvent, render, screen } from '@testing-library/react'

import {
  installPolishStyles,
  uninstallPolishStyles,
  POLISH_CLASS_PROBE_ROW_MOUNT,
  POLISH_CLASS_PROBE_ROW_UNMOUNT,
  POLISH_CLASS_RESTORED_TOAST,
  POLISH_CSS_TEXT,
} from '../src/components/polishStyles'
import { ProbeListPanel } from '../src/components/ProbeListPanel'
import { ResultMeshPlaybackPanel } from '../src/components/ResultMeshPlaybackPanel'
import {
  PROBE_LIST_INITIAL_STATE,
  addProbeEntry,
} from '../src/components/probeList'
import {
  saveProbeList,
  probeListStorageKey,
  PROBE_LIST_LS_KEY_PREFIX,
} from '../src/components/probeListStorage'
import type { PickedNodeInfo } from '../src/components/viewportRaycaster'

function mkProbe(label: number, fv: number | null = 1.0e8): PickedNodeInfo {
  return { label, position: [label * 0.1, 0, 0], fieldValue: fv }
}

function clearAllProbeStorage() {
  try {
    const keys: string[] = []
    for (let i = 0; i < window.localStorage.length; i++) {
      const k = window.localStorage.key(i)
      if (k && k.startsWith(PROBE_LIST_LS_KEY_PREFIX)) keys.push(k)
    }
    for (const k of keys) window.localStorage.removeItem(k)
  } catch {
    /* SSR */
  }
}

// ────────────────────────────────────────────────────────────────────
// 1. polishStyles CSS structural pins
// ────────────────────────────────────────────────────────────────────

describe('Phase 28 C — polishStyles unmount + toast CSS', () => {
  afterEach(() => uninstallPolishStyles())

  it('exports POLISH_CLASS_PROBE_ROW_UNMOUNT constant', () => {
    expect(POLISH_CLASS_PROBE_ROW_UNMOUNT).toBe('fm04a-probe-row-unmount')
  })

  it('exports POLISH_CLASS_RESTORED_TOAST constant', () => {
    expect(POLISH_CLASS_RESTORED_TOAST).toBe('fm04a-restored-toast')
  })

  it('CSS defines the fade-out keyframes for row unmount', () => {
    expect(POLISH_CSS_TEXT).toContain('@keyframes fm04a-probe-row-fade-out')
    expect(POLISH_CSS_TEXT).toContain(`.${POLISH_CLASS_PROBE_ROW_UNMOUNT}`)
  })

  it('CSS defines the restored-toast fade-in keyframes + rule', () => {
    expect(POLISH_CSS_TEXT).toContain('@keyframes fm04a-restored-toast-fade-in')
    expect(POLISH_CSS_TEXT).toContain(`.${POLISH_CLASS_RESTORED_TOAST}`)
  })

  it('E:-1 — row unmount animation duration ≤ 200ms (settle budget)', () => {
    // Extract the `animation:` declaration from the unmount class
    // rule (e.g. "animation: fm04a-probe-row-fade-out 150ms ease-in
    // forwards;") and assert the duration is ≤ 200ms. This pins the
    // user-perception budget: a removed row must finish its exit
    // animation before the parent's 200ms settle-time cutoff.
    const rule = POLISH_CSS_TEXT.match(
      /\.fm04a-probe-row-unmount\s*\{[^}]*animation:\s*[^;]*?(\d+)ms/,
    )
    expect(rule).not.toBeNull()
    const ms = Number(rule![1])
    expect(ms).toBeGreaterThan(0)
    expect(ms).toBeLessThanOrEqual(200)
  })

  it('B:-1 — prefers-reduced-motion disables both new animations', () => {
    const idx = POLISH_CSS_TEXT.indexOf(
      '@media (prefers-reduced-motion: reduce)',
    )
    expect(idx).toBeGreaterThan(-1)
    const tail = POLISH_CSS_TEXT.slice(idx)
    expect(tail).toContain(`.${POLISH_CLASS_PROBE_ROW_UNMOUNT}`)
    expect(tail).toContain(`.${POLISH_CLASS_RESTORED_TOAST}`)
    expect(tail).toContain('animation: none')
  })
})

// ────────────────────────────────────────────────────────────────────
// 2. ProbeListPanel exitingLabel prop
// ────────────────────────────────────────────────────────────────────

describe('Phase 28 C — ProbeListPanel exitingLabel swaps row class', () => {
  afterEach(() => uninstallPolishStyles())

  function twoRowState() {
    return addProbeEntry(
      addProbeEntry(PROBE_LIST_INITIAL_STATE, mkProbe(7, 1.0e8)),
      mkProbe(42, 2.5e8),
    )
  }

  it('default (no exitingLabel) — both rows carry the MOUNT class', () => {
    render(<ProbeListPanel state={twoRowState()} />)
    expect(screen.getByTestId('probe-row-0').className).toContain(
      POLISH_CLASS_PROBE_ROW_MOUNT,
    )
    expect(screen.getByTestId('probe-row-1').className).toContain(
      POLISH_CLASS_PROBE_ROW_MOUNT,
    )
  })

  it('exitingLabel=42 — row with label 42 carries UNMOUNT, row 7 still MOUNT', () => {
    render(<ProbeListPanel state={twoRowState()} exitingLabel={42} />)
    const row0 = screen.getByTestId('probe-row-0') // label 7
    const row1 = screen.getByTestId('probe-row-1') // label 42
    expect(row0.className).toContain(POLISH_CLASS_PROBE_ROW_MOUNT)
    expect(row0.className).not.toContain(POLISH_CLASS_PROBE_ROW_UNMOUNT)
    expect(row1.className).toContain(POLISH_CLASS_PROBE_ROW_UNMOUNT)
    expect(row1.className).not.toContain(POLISH_CLASS_PROBE_ROW_MOUNT)
  })

  it('exitingLabel=null is treated identically to default (no row UNMOUNT)', () => {
    render(<ProbeListPanel state={twoRowState()} exitingLabel={null} />)
    expect(screen.getByTestId('probe-row-0').className).not.toContain(
      POLISH_CLASS_PROBE_ROW_UNMOUNT,
    )
    expect(screen.getByTestId('probe-row-1').className).not.toContain(
      POLISH_CLASS_PROBE_ROW_UNMOUNT,
    )
  })

  it('exitingLabel pointing at no existing row — no crash, no UNMOUNT class', () => {
    render(<ProbeListPanel state={twoRowState()} exitingLabel={9999} />)
    expect(screen.getByTestId('probe-row-0').className).not.toContain(
      POLISH_CLASS_PROBE_ROW_UNMOUNT,
    )
    expect(screen.getByTestId('probe-row-1').className).not.toContain(
      POLISH_CLASS_PROBE_ROW_UNMOUNT,
    )
  })
})

// ────────────────────────────────────────────────────────────────────
// 3. ResultMeshPlaybackPanel "Restored N probes" toast
// ────────────────────────────────────────────────────────────────────

describe('Phase 28 C — restored toast on case mount', () => {
  beforeEach(() => {
    clearAllProbeStorage()
    // Stub fetch so the result-mesh GET never hits the network.
    vi.spyOn(globalThis, 'fetch').mockImplementation(
      async () =>
        new Response('null', {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        }) as Response,
    )
  })
  afterEach(() => {
    clearAllProbeStorage()
    uninstallPolishStyles()
    vi.useRealTimers()
  })

  it('no toast when localStorage has 0 entries for the case', () => {
    render(
      <ResultMeshPlaybackPanel
        caseId="phase28c-toast-empty"
        apiBase="http://localhost:8000/api/v1"
      />,
    )
    expect(screen.queryByTestId('probe-restored-toast')).toBeNull()
  })

  it('toast appears with PLURAL copy when ≥2 entries restored', () => {
    const state = addProbeEntry(
      addProbeEntry(PROBE_LIST_INITIAL_STATE, mkProbe(7)),
      mkProbe(42),
    )
    saveProbeList('phase28c-toast-2', state)
    // Sanity: storage was written under the expected key.
    expect(
      window.localStorage.getItem(probeListStorageKey('phase28c-toast-2')),
    ).not.toBeNull()
    render(
      <ResultMeshPlaybackPanel
        caseId="phase28c-toast-2"
        apiBase="http://localhost:8000/api/v1"
      />,
    )
    const toast = screen.getByTestId('probe-restored-toast')
    expect(toast).toBeTruthy()
    expect(toast.textContent).toContain('Restored 2 pinned probes')
    expect(toast.textContent).toContain('last session')
  })

  it('toast uses SINGULAR copy ("probe", no s) when exactly 1 restored', () => {
    saveProbeList(
      'phase28c-toast-1',
      addProbeEntry(PROBE_LIST_INITIAL_STATE, mkProbe(7)),
    )
    render(
      <ResultMeshPlaybackPanel
        caseId="phase28c-toast-1"
        apiBase="http://localhost:8000/api/v1"
      />,
    )
    const toast = screen.getByTestId('probe-restored-toast')
    expect(toast.textContent).toContain('Restored 1 pinned probe')
    // Pin singular: 'probe ' (with trailing space) appears; 'probes'
    // (with the s) does NOT.
    expect(toast.textContent).not.toContain('pinned probes')
  })

  it('toast has role="status" + aria-live="polite" for screen readers', () => {
    saveProbeList(
      'phase28c-toast-a11y',
      addProbeEntry(PROBE_LIST_INITIAL_STATE, mkProbe(7)),
    )
    render(
      <ResultMeshPlaybackPanel
        caseId="phase28c-toast-a11y"
        apiBase="http://localhost:8000/api/v1"
      />,
    )
    const toast = screen.getByTestId('probe-restored-toast')
    expect(toast.getAttribute('role')).toBe('status')
    expect(toast.getAttribute('aria-live')).toBe('polite')
  })

  it('clicking × dismisses the toast immediately', () => {
    saveProbeList(
      'phase28c-toast-dismiss',
      addProbeEntry(PROBE_LIST_INITIAL_STATE, mkProbe(7)),
    )
    render(
      <ResultMeshPlaybackPanel
        caseId="phase28c-toast-dismiss"
        apiBase="http://localhost:8000/api/v1"
      />,
    )
    expect(screen.getByTestId('probe-restored-toast')).toBeTruthy()
    fireEvent.click(screen.getByTestId('probe-restored-toast-dismiss'))
    expect(screen.queryByTestId('probe-restored-toast')).toBeNull()
  })

  it('toast auto-dismisses after 4 seconds', () => {
    vi.useFakeTimers()
    saveProbeList(
      'phase28c-toast-auto',
      addProbeEntry(PROBE_LIST_INITIAL_STATE, mkProbe(7)),
    )
    render(
      <ResultMeshPlaybackPanel
        caseId="phase28c-toast-auto"
        apiBase="http://localhost:8000/api/v1"
      />,
    )
    expect(screen.getByTestId('probe-restored-toast')).toBeTruthy()
    // Just before 4s: still visible.
    act(() => {
      vi.advanceTimersByTime(3999)
    })
    expect(screen.queryByTestId('probe-restored-toast')).toBeTruthy()
    // At 4s: gone.
    act(() => {
      vi.advanceTimersByTime(2)
    })
    expect(screen.queryByTestId('probe-restored-toast')).toBeNull()
  })

  it('D:-1 — dismissing the toast does NOT clear the restored probes', () => {
    // The probes themselves must remain pinned; the toast is a
    // notification, not a confirmation of the restoration.
    saveProbeList(
      'phase28c-toast-additive',
      addProbeEntry(
        addProbeEntry(PROBE_LIST_INITIAL_STATE, mkProbe(7)),
        mkProbe(42),
      ),
    )
    render(
      <ResultMeshPlaybackPanel
        caseId="phase28c-toast-additive"
        apiBase="http://localhost:8000/api/v1"
      />,
    )
    expect(screen.getByTestId('probe-restored-toast')).toBeTruthy()
    fireEvent.click(screen.getByTestId('probe-restored-toast-dismiss'))
    // Storage is untouched — the next case mount would still restore.
    const stored = window.localStorage.getItem(
      probeListStorageKey('phase28c-toast-additive'),
    )
    expect(stored).not.toBeNull()
    const parsed = JSON.parse(stored!)
    expect(parsed.entries).toHaveLength(2)
  })
})
