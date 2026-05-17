// FM-04a Phase 30 C — corrupted-key toast + coord-readout tooltip
// tests.
//
// Three deliveries pinned in one test file:
//
// 1. probeListStorage `loadProbeListWithDiagnostic` — returns
//    {state, corrupted, reason}. corrupted=true ONLY when stored
//    key existed AND parse/shape failed; missing-key is corrupted=false.
//
// 2. ResultMeshPlaybackPanel corrupted-key toast — appears when
//    diagnostic load reports corruption; role=alert; dismiss button
//    + auto-fade after 8s; reuses the POLISH_CLASS_RESTORED_TOAST
//    styling (already covered by Phase 28 C reduce-motion guard).
//
// 3. CoordReadoutTooltip — renders xyz at screenX/screenY when info
//    is non-null + finite; renders nothing when null or non-finite.
//    `makeCoordThrottle` honors the 30Hz minIntervalMs.
//
// Tier 1 / Tier 2 engineering candidate; not signed validation; not
// benchmark agreement.

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'

import { CoordReadoutTooltip, makeCoordThrottle } from '../src/components/CoordReadoutTooltip'
import {
  PROBE_LIST_LS_KEY_PREFIX,
  loadProbeListWithDiagnostic,
  probeListStorageKey,
  saveProbeList,
} from '../src/components/probeListStorage'
import { addProbeEntry, PROBE_LIST_INITIAL_STATE } from '../src/components/probeList'
import { ResultMeshPlaybackPanel } from '../src/components/ResultMeshPlaybackPanel'

function clearAllProbeStorage() {
  try {
    for (let i = window.localStorage.length - 1; i >= 0; i--) {
      const key = window.localStorage.key(i)
      if (key && key.startsWith(PROBE_LIST_LS_KEY_PREFIX)) {
        window.localStorage.removeItem(key)
      }
    }
  } catch {
    /* SSR fallback */
  }
}

function mkProbe(label: number) {
  return {
    label,
    position: [0, 0, 0] as [number, number, number],
    fieldValue: 100,
  }
}

// ────────────────────────────────────────────────────────────────────
// 1. loadProbeListWithDiagnostic
// ────────────────────────────────────────────────────────────────────

describe('Phase 30 C — loadProbeListWithDiagnostic', () => {
  beforeEach(clearAllProbeStorage)
  afterEach(clearAllProbeStorage)

  it('missing key → corrupted=false (first-load is NOT corruption)', () => {
    const result = loadProbeListWithDiagnostic('phase30c-missing')
    expect(result.corrupted).toBe(false)
    expect(result.state.entries).toEqual([])
    expect(result.reason).toBeUndefined()
  })

  it('valid stored payload → corrupted=false, state round-trips', () => {
    const state = addProbeEntry(PROBE_LIST_INITIAL_STATE, mkProbe(7))
    saveProbeList('phase30c-valid', state)
    const result = loadProbeListWithDiagnostic('phase30c-valid')
    expect(result.corrupted).toBe(false)
    expect(result.state.entries).toHaveLength(1)
    expect(result.state.entries[0].label).toBe(7)
  })

  it('malformed JSON → corrupted=true with reason mentioning JSON', () => {
    window.localStorage.setItem(probeListStorageKey('phase30c-bad-json'), '{not json')
    const result = loadProbeListWithDiagnostic('phase30c-bad-json')
    expect(result.corrupted).toBe(true)
    expect(result.state.entries).toEqual([])
    expect(result.reason).toMatch(/JSON/i)
  })

  it('wrong-shape payload → corrupted=true with reason mentioning shape', () => {
    window.localStorage.setItem(
      probeListStorageKey('phase30c-bad-shape'),
      JSON.stringify({ entries: 'not-an-array' }),
    )
    const result = loadProbeListWithDiagnostic('phase30c-bad-shape')
    expect(result.corrupted).toBe(true)
    expect(result.state.entries).toEqual([])
    expect(result.reason).toMatch(/shape/i)
  })

  it('entries with missing fields → corrupted=true (full shape validation)', () => {
    window.localStorage.setItem(
      probeListStorageKey('phase30c-bad-entry'),
      JSON.stringify({ entries: [{ label: 7 /* missing position + fieldValue */ }] }),
    )
    const result = loadProbeListWithDiagnostic('phase30c-bad-entry')
    expect(result.corrupted).toBe(true)
    expect(result.state.entries).toEqual([])
  })
})

// ────────────────────────────────────────────────────────────────────
// 2. ResultMeshPlaybackPanel — corrupted-key toast
// ────────────────────────────────────────────────────────────────────

describe('Phase 30 C — corrupted-key toast', () => {
  beforeEach(() => {
    clearAllProbeStorage()
    vi.spyOn(globalThis, 'fetch').mockImplementation(
      async () =>
        new Response('null', {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        }) as Response,
    )
    // Silence console.warn from the storage layer; the test is
    // about user-visible UI, not log noise.
    vi.spyOn(console, 'warn').mockImplementation(() => undefined)
  })
  afterEach(() => {
    clearAllProbeStorage()
    vi.restoreAllMocks()
    vi.useRealTimers()
  })

  it('NO toast when storage is empty (missing key is not corruption)', async () => {
    render(
      <ResultMeshPlaybackPanel
        caseId="phase30c-no-toast"
        apiBase="http://localhost:8000/api/v1"
      />,
    )
    // Give effects a tick.
    await waitFor(() => {
      expect(screen.queryByTestId('probe-corrupted-toast')).toBeNull()
    })
  })

  it('NO toast when storage has a VALID entry (just restored toast)', async () => {
    saveProbeList(
      'phase30c-valid-mount',
      addProbeEntry(PROBE_LIST_INITIAL_STATE, mkProbe(7)),
    )
    render(
      <ResultMeshPlaybackPanel
        caseId="phase30c-valid-mount"
        apiBase="http://localhost:8000/api/v1"
      />,
    )
    await waitFor(() => {
      expect(screen.queryByTestId('probe-corrupted-toast')).toBeNull()
    })
  })

  it('toast appears when storage payload is malformed JSON', async () => {
    window.localStorage.setItem(
      probeListStorageKey('phase30c-corrupt-1'),
      '{not json',
    )
    render(
      <ResultMeshPlaybackPanel
        caseId="phase30c-corrupt-1"
        apiBase="http://localhost:8000/api/v1"
      />,
    )
    await waitFor(() => {
      expect(screen.getByTestId('probe-corrupted-toast')).toBeInTheDocument()
    })
    const toast = screen.getByTestId('probe-corrupted-toast')
    expect(toast.textContent).toContain('Discarded corrupted')
    expect(toast.textContent).toContain('phase30c-corrupt-1')
  })

  it('toast appears when storage payload has wrong shape', async () => {
    window.localStorage.setItem(
      probeListStorageKey('phase30c-corrupt-2'),
      JSON.stringify({ entries: 'wrong' }),
    )
    render(
      <ResultMeshPlaybackPanel
        caseId="phase30c-corrupt-2"
        apiBase="http://localhost:8000/api/v1"
      />,
    )
    await waitFor(() => {
      expect(screen.getByTestId('probe-corrupted-toast')).toBeInTheDocument()
    })
  })

  it('toast has role="alert" + aria-live="assertive" (higher stakes than restored)', async () => {
    window.localStorage.setItem(
      probeListStorageKey('phase30c-a11y'),
      '{malformed',
    )
    render(
      <ResultMeshPlaybackPanel
        caseId="phase30c-a11y"
        apiBase="http://localhost:8000/api/v1"
      />,
    )
    const toast = await screen.findByTestId('probe-corrupted-toast')
    expect(toast.getAttribute('role')).toBe('alert')
    expect(toast.getAttribute('aria-live')).toBe('assertive')
  })

  it('dismiss button removes the toast immediately', async () => {
    window.localStorage.setItem(
      probeListStorageKey('phase30c-dismiss'),
      '{malformed',
    )
    render(
      <ResultMeshPlaybackPanel
        caseId="phase30c-dismiss"
        apiBase="http://localhost:8000/api/v1"
      />,
    )
    const toast = await screen.findByTestId('probe-corrupted-toast')
    expect(toast).toBeInTheDocument()
    fireEvent.click(screen.getByTestId('probe-corrupted-toast-dismiss'))
    expect(screen.queryByTestId('probe-corrupted-toast')).toBeNull()
  })

  it('toast carries warning-tinted color (visual distinction from restored toast)', async () => {
    window.localStorage.setItem(
      probeListStorageKey('phase30c-color'),
      '{malformed',
    )
    render(
      <ResultMeshPlaybackPanel
        caseId="phase30c-color"
        apiBase="http://localhost:8000/api/v1"
      />,
    )
    const toast = await screen.findByTestId('probe-corrupted-toast')
    // Pinned via inline style override on top of the shared
    // POLISH_CLASS_RESTORED_TOAST styling. Color is warning-rose
    // (Tailwind rose-300 == #fda4af) to visually separate it from
    // the blue informational restored toast.
    expect(toast.style.color).toMatch(/^(rgb|#)/)
    // Just verify color is set on the element directly, not the
    // default text-secondary inherited from chrome.
    expect(toast.style.color).not.toBe('')
  })
})

// ────────────────────────────────────────────────────────────────────
// 3. CoordReadoutTooltip + makeCoordThrottle
// ────────────────────────────────────────────────────────────────────

describe('Phase 30 C — CoordReadoutTooltip', () => {
  it('renders nothing when info is null', () => {
    const { container } = render(<CoordReadoutTooltip info={null} />)
    expect(container.firstChild).toBeNull()
    expect(screen.queryByTestId('coord-readout-tooltip')).toBeNull()
  })

  it('renders xyz with 3-decimal precision when info is finite', () => {
    render(
      <CoordReadoutTooltip
        info={{
          worldX: 1.234567,
          worldY: -0.5,
          worldZ: 0.001,
          screenX: 100,
          screenY: 80,
        }}
      />,
    )
    expect(screen.getByTestId('coord-readout-tooltip')).toBeTruthy()
    expect(screen.getByTestId('coord-readout-x').textContent).toBe('1.235')
    expect(screen.getByTestId('coord-readout-y').textContent).toBe('-0.500')
    expect(screen.getByTestId('coord-readout-z').textContent).toBe('0.001')
  })

  it('renders nothing when any coord is non-finite (NaN guard)', () => {
    render(
      <CoordReadoutTooltip
        info={{
          worldX: Number.NaN,
          worldY: 0,
          worldZ: 0,
          screenX: 0,
          screenY: 0,
        }}
      />,
    )
    expect(screen.queryByTestId('coord-readout-tooltip')).toBeNull()
  })

  it('renders nothing when any coord is +Infinity', () => {
    render(
      <CoordReadoutTooltip
        info={{
          worldX: 0,
          worldY: Number.POSITIVE_INFINITY,
          worldZ: 0,
          screenX: 0,
          screenY: 0,
        }}
      />,
    )
    expect(screen.queryByTestId('coord-readout-tooltip')).toBeNull()
  })

  it('positions tooltip offset from cursor (left = screenX + 12)', () => {
    render(
      <CoordReadoutTooltip
        info={{
          worldX: 0,
          worldY: 0,
          worldZ: 0,
          screenX: 100,
          screenY: 80,
        }}
      />,
    )
    const tooltip = screen.getByTestId('coord-readout-tooltip')
    expect(tooltip.style.left).toBe('112px')
    expect(tooltip.style.top).toBe('92px')
  })

  it('has pointerEvents: none so it never blocks mouse hits on the canvas', () => {
    render(
      <CoordReadoutTooltip
        info={{ worldX: 0, worldY: 0, worldZ: 0, screenX: 0, screenY: 0 }}
      />,
    )
    const tooltip = screen.getByTestId('coord-readout-tooltip')
    expect(tooltip.style.pointerEvents).toBe('none')
  })

  it('has aria-live="off" (high-frequency updates would spam screen readers)', () => {
    render(
      <CoordReadoutTooltip
        info={{ worldX: 0, worldY: 0, worldZ: 0, screenX: 0, screenY: 0 }}
      />,
    )
    expect(screen.getByTestId('coord-readout-tooltip').getAttribute('aria-live')).toBe(
      'off',
    )
  })
})

describe('Phase 30 C — makeCoordThrottle (30Hz)', () => {
  it('fires immediately on first call', () => {
    const spy = vi.fn()
    let nowVal = 0
    const throttled = makeCoordThrottle(spy, 33, () => nowVal)
    throttled('a')
    expect(spy).toHaveBeenCalledTimes(1)
    expect(spy).toHaveBeenLastCalledWith('a')
  })

  it('suppresses second call within minIntervalMs window', () => {
    const spy = vi.fn()
    let nowVal = 0
    const throttled = makeCoordThrottle(spy, 33, () => nowVal)
    throttled('a')
    nowVal = 20
    throttled('b')
    expect(spy).toHaveBeenCalledTimes(1)
  })

  it('fires again once minIntervalMs has elapsed', () => {
    const spy = vi.fn()
    let nowVal = 0
    const throttled = makeCoordThrottle(spy, 33, () => nowVal)
    throttled('a')
    nowVal = 40
    throttled('b')
    expect(spy).toHaveBeenCalledTimes(2)
    expect(spy).toHaveBeenLastCalledWith('b')
  })

  it('default 33ms interval reflects ~30Hz target', () => {
    const spy = vi.fn()
    let nowVal = 0
    const throttled = makeCoordThrottle(spy, undefined, () => nowVal)
    throttled('a')
    nowVal = 32 // just under 33ms
    throttled('b')
    expect(spy).toHaveBeenCalledTimes(1)
    nowVal = 34 // just over
    throttled('c')
    expect(spy).toHaveBeenCalledTimes(2)
  })
})
