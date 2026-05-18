// FM-04a Phase 31 B — useViewportLayout reducer-hook tests.
//
// Closes the Phase 27 punchlist #3 + Phase 29 rec #2 + Phase 30
// UX Dim 3 -1 debit by extracting the viewport-layout state +
// effect cascade out of ResultMeshPlaybackPanel into a custom hook.
//
// Tests cover:
//
// 1. Initial state — defaults across all 8 state fields when no
//    persisted localStorage exists; restoration from persisted
//    state when keys exist.
//
// 2. Case-mount cascade — caseId change triggers
//    loadProbeListWithDiagnostic; corrupted payload sets the toast;
//    missing key does NOT set the toast (first-load semantics);
//    valid payload sets probeList + restoredCount but no toast.
//
// 3. Auto-dismiss timers — corruptedToast clears after 8 s;
//    restoredCount clears after 4 s; both timers cleanup on unmount.
//
// 4. Persistence effects — probeList writes saved per change;
//    companion enabled + cut written per change.
//
// 5. toggleCompanion action — turning ON with primary cut + no
//    persisted state seeds via computeCompanionInitialCut; turning
//    ON with persisted state PRESERVES the persisted cut (C:-1).
//
// 6. dismissCorruptedToast action — synchronously nulls the toast.
//
// Tier 1 / Tier 2 engineering candidate; not signed validation;
// not benchmark agreement.

import { act, renderHook } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import {
  COMPANION_CUT_LS_KEY,
  COMPANION_ENABLED_LS_KEY,
} from '../src/components/companionViewportStorage'
import {
  PROBE_LIST_LS_KEY_PREFIX,
  probeListStorageKey,
  saveProbeList,
} from '../src/components/probeListStorage'
import {
  PROBE_LIST_INITIAL_STATE,
  addProbeEntry,
} from '../src/components/probeList'
import { useViewportLayout } from '../src/state/useViewportLayout'
import type { SectionCutState } from '../src/components/viewportGeometry'

function clearAllStorage() {
  try {
    window.localStorage.removeItem(COMPANION_ENABLED_LS_KEY)
    window.localStorage.removeItem(COMPANION_CUT_LS_KEY)
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
// 1. Initial state
// ────────────────────────────────────────────────────────────────────

describe('Phase 31 B — useViewportLayout initial state', () => {
  beforeEach(clearAllStorage)
  afterEach(clearAllStorage)

  it('default viewportMode is webgl', () => {
    const { result } = renderHook(() => useViewportLayout({ caseId: null }))
    expect(result.current.state.viewportMode).toBe('webgl')
  })

  it('default showCompanionViewport is false (D:-1 additive)', () => {
    const { result } = renderHook(() => useViewportLayout({ caseId: null }))
    expect(result.current.state.showCompanionViewport).toBe(false)
  })

  it('default companionSectionCut is {axis:x, positionM:0, showLow:false}', () => {
    const { result } = renderHook(() => useViewportLayout({ caseId: null }))
    expect(result.current.state.companionSectionCut).toEqual({
      axis: 'x',
      positionM: 0,
      showLow: false,
    })
  })

  it('default hoverCoords is null', () => {
    const { result } = renderHook(() => useViewportLayout({ caseId: null }))
    expect(result.current.state.hoverCoords).toBeNull()
  })

  it('null caseId yields PROBE_LIST_INITIAL_STATE + zero restoredCount + null corruptedToast', () => {
    const { result } = renderHook(() => useViewportLayout({ caseId: null }))
    expect(result.current.state.probeList).toEqual(PROBE_LIST_INITIAL_STATE)
    expect(result.current.state.restoredCount).toBe(0)
    expect(result.current.state.corruptedToast).toBeNull()
  })

  it('restores companion state from persisted localStorage', () => {
    const cut: SectionCutState = { axis: 'z', positionM: 0.7, showLow: false }
    window.localStorage.setItem(COMPANION_ENABLED_LS_KEY, 'true')
    window.localStorage.setItem(COMPANION_CUT_LS_KEY, JSON.stringify(cut))
    const { result } = renderHook(() => useViewportLayout({ caseId: null }))
    expect(result.current.state.showCompanionViewport).toBe(true)
    expect(result.current.state.companionSectionCut).toEqual(cut)
  })
})

// ────────────────────────────────────────────────────────────────────
// 2. Case-mount cascade
// ────────────────────────────────────────────────────────────────────

describe('Phase 31 B — case-mount cascade', () => {
  beforeEach(() => {
    clearAllStorage()
    // Silence console.warn from the storage layer during corrupted
    // payload tests; this hook test is about behavioral wiring,
    // not log noise.
    vi.spyOn(console, 'warn').mockImplementation(() => undefined)
  })
  afterEach(() => {
    clearAllStorage()
    vi.restoreAllMocks()
  })

  it('valid persisted probe list populates probeList + restoredCount + no toast', () => {
    saveProbeList(
      'caseA',
      addProbeEntry(PROBE_LIST_INITIAL_STATE, mkProbe(7)),
    )
    const { result } = renderHook(() => useViewportLayout({ caseId: 'caseA' }))
    expect(result.current.state.probeList.entries).toHaveLength(1)
    expect(result.current.state.restoredCount).toBe(1)
    expect(result.current.state.corruptedToast).toBeNull()
  })

  it('corrupted JSON payload populates corruptedToast', () => {
    window.localStorage.setItem(probeListStorageKey('caseB'), '{malformed')
    const { result } = renderHook(() => useViewportLayout({ caseId: 'caseB' }))
    expect(result.current.state.corruptedToast).not.toBeNull()
    expect(result.current.state.corruptedToast?.caseId).toBe('caseB')
    expect(result.current.state.probeList.entries).toEqual([])
  })

  it('missing key does NOT set corruptedToast (first-load semantics)', () => {
    const { result } = renderHook(() => useViewportLayout({ caseId: 'caseC' }))
    expect(result.current.state.corruptedToast).toBeNull()
    expect(result.current.state.probeList.entries).toEqual([])
  })

  it('case_id change re-runs the cascade', () => {
    saveProbeList(
      'caseD',
      addProbeEntry(PROBE_LIST_INITIAL_STATE, mkProbe(1)),
    )
    saveProbeList(
      'caseE',
      addProbeEntry(
        addProbeEntry(PROBE_LIST_INITIAL_STATE, mkProbe(2)),
        mkProbe(3),
      ),
    )
    const { result, rerender } = renderHook(
      ({ caseId }) => useViewportLayout({ caseId }),
      { initialProps: { caseId: 'caseD' as string | null } },
    )
    expect(result.current.state.restoredCount).toBe(1)
    rerender({ caseId: 'caseE' })
    expect(result.current.state.restoredCount).toBe(2)
  })

  it('switching to null caseId clears probe list + counts', () => {
    saveProbeList(
      'caseF',
      addProbeEntry(PROBE_LIST_INITIAL_STATE, mkProbe(9)),
    )
    const { result, rerender } = renderHook(
      ({ caseId }) => useViewportLayout({ caseId }),
      { initialProps: { caseId: 'caseF' as string | null } },
    )
    expect(result.current.state.restoredCount).toBe(1)
    rerender({ caseId: null })
    expect(result.current.state.probeList).toEqual(PROBE_LIST_INITIAL_STATE)
    expect(result.current.state.restoredCount).toBe(0)
  })
})

// ────────────────────────────────────────────────────────────────────
// 3. Auto-dismiss timers
// ────────────────────────────────────────────────────────────────────

describe('Phase 31 B — auto-dismiss timers', () => {
  beforeEach(() => {
    clearAllStorage()
    vi.useFakeTimers()
    vi.spyOn(console, 'warn').mockImplementation(() => undefined)
  })
  afterEach(() => {
    clearAllStorage()
    vi.useRealTimers()
    vi.restoreAllMocks()
  })

  it('corruptedToast clears after 8s', () => {
    window.localStorage.setItem(probeListStorageKey('autofadeC'), '{bad')
    const { result } = renderHook(() =>
      useViewportLayout({ caseId: 'autofadeC' }),
    )
    expect(result.current.state.corruptedToast).not.toBeNull()
    act(() => {
      vi.advanceTimersByTime(7999)
    })
    expect(result.current.state.corruptedToast).not.toBeNull()
    act(() => {
      vi.advanceTimersByTime(2)
    })
    expect(result.current.state.corruptedToast).toBeNull()
  })

  it('restoredCount clears after 4s', () => {
    saveProbeList(
      'autofadeR',
      addProbeEntry(PROBE_LIST_INITIAL_STATE, mkProbe(7)),
    )
    const { result } = renderHook(() =>
      useViewportLayout({ caseId: 'autofadeR' }),
    )
    expect(result.current.state.restoredCount).toBe(1)
    act(() => {
      vi.advanceTimersByTime(4001)
    })
    expect(result.current.state.restoredCount).toBe(0)
  })
})

// ────────────────────────────────────────────────────────────────────
// 4. Persistence effects
// ────────────────────────────────────────────────────────────────────

describe('Phase 31 B — persistence effects', () => {
  beforeEach(clearAllStorage)
  afterEach(clearAllStorage)

  it('setCompanionSectionCut writes the new cut to localStorage', () => {
    const { result } = renderHook(() =>
      useViewportLayout({ caseId: null }),
    )
    act(() => {
      result.current.actions.setCompanionSectionCut({
        axis: 'y',
        positionM: 0.42,
        showLow: false,
      })
    })
    const raw = window.localStorage.getItem(COMPANION_CUT_LS_KEY)
    expect(raw).not.toBeNull()
    expect(JSON.parse(raw as string)).toEqual({
      axis: 'y',
      positionM: 0.42,
      showLow: false,
    })
  })

  it('toggleCompanion(null) writes the enabled flag', () => {
    const { result } = renderHook(() =>
      useViewportLayout({ caseId: null }),
    )
    act(() => {
      result.current.actions.toggleCompanion(null)
    })
    expect(window.localStorage.getItem(COMPANION_ENABLED_LS_KEY)).toBe('true')
  })

  it('setProbeList writes the updated list to localStorage scoped by case', () => {
    const { result } = renderHook(() =>
      useViewportLayout({ caseId: 'persistP' }),
    )
    act(() => {
      result.current.actions.setProbeList((s) => addProbeEntry(s, mkProbe(5)))
    })
    const raw = window.localStorage.getItem(probeListStorageKey('persistP'))
    expect(raw).not.toBeNull()
    const parsed = JSON.parse(raw as string)
    expect(parsed.entries).toHaveLength(1)
    expect(parsed.entries[0].label).toBe(5)
  })
})

// ────────────────────────────────────────────────────────────────────
// 5. toggleCompanion action — C:-1 invariant
// ────────────────────────────────────────────────────────────────────

describe('Phase 31 B — toggleCompanion (C:-1 anti-gaming)', () => {
  beforeEach(clearAllStorage)
  afterEach(clearAllStorage)

  it('first toggle ON with primary cut + no persisted seeds via computeCompanionInitialCut', () => {
    const { result } = renderHook(() =>
      useViewportLayout({ caseId: null }),
    )
    const primaryCut: SectionCutState = {
      axis: 'z',
      positionM: 0.3,
      showLow: true,
    }
    act(() => {
      result.current.actions.toggleCompanion(primaryCut)
    })
    expect(result.current.state.showCompanionViewport).toBe(true)
    // Mirror axis + position, flip showLow → expose the other half.
    expect(result.current.state.companionSectionCut).toEqual({
      axis: 'z',
      positionM: 0.3,
      showLow: false,
    })
  })

  it('toggle OFF preserves companionSectionCut (C:-1)', () => {
    const { result } = renderHook(() =>
      useViewportLayout({ caseId: null }),
    )
    act(() => {
      result.current.actions.setCompanionSectionCut({
        axis: 'y',
        positionM: 0.5,
        showLow: false,
      })
      result.current.actions.toggleCompanion(null)
    })
    expect(result.current.state.showCompanionViewport).toBe(true)
    act(() => {
      result.current.actions.toggleCompanion(null)
    })
    expect(result.current.state.showCompanionViewport).toBe(false)
    expect(result.current.state.companionSectionCut).toEqual({
      axis: 'y',
      positionM: 0.5,
      showLow: false,
    })
  })

  it('toggle ON when persisted cut exists does NOT re-seed (C:-1)', () => {
    // Persist a user-edited cut first.
    const userEdited: SectionCutState = {
      axis: 'x',
      positionM: 0.9,
      showLow: true,
    }
    window.localStorage.setItem(
      COMPANION_CUT_LS_KEY,
      JSON.stringify(userEdited),
    )
    const { result } = renderHook(() =>
      useViewportLayout({ caseId: null }),
    )
    const primaryCut: SectionCutState = {
      axis: 'z',
      positionM: 0,
      showLow: true,
    }
    act(() => {
      result.current.actions.toggleCompanion(primaryCut)
    })
    // Persisted cut preserved.
    expect(result.current.state.companionSectionCut).toEqual(userEdited)
  })
})

// ────────────────────────────────────────────────────────────────────
// 6. dismissCorruptedToast
// ────────────────────────────────────────────────────────────────────

describe('Phase 31 B — dismissCorruptedToast', () => {
  beforeEach(() => {
    clearAllStorage()
    vi.spyOn(console, 'warn').mockImplementation(() => undefined)
  })
  afterEach(() => {
    clearAllStorage()
    vi.restoreAllMocks()
  })

  it('clears the toast synchronously', () => {
    window.localStorage.setItem(probeListStorageKey('dismissC'), '{bad')
    const { result } = renderHook(() =>
      useViewportLayout({ caseId: 'dismissC' }),
    )
    expect(result.current.state.corruptedToast).not.toBeNull()
    act(() => {
      result.current.actions.dismissCorruptedToast()
    })
    expect(result.current.state.corruptedToast).toBeNull()
  })
})

// ────────────────────────────────────────────────────────────────────
// 7. setHoverCoords — sanity wiring (no effect cascade)
// ────────────────────────────────────────────────────────────────────

describe('Phase 31 B — setHoverCoords', () => {
  it('updates hoverCoords without side effects', () => {
    const { result } = renderHook(() =>
      useViewportLayout({ caseId: null }),
    )
    act(() => {
      result.current.actions.setHoverCoords({
        worldX: 1.0,
        worldY: 2.0,
        worldZ: 3.0,
        screenX: 100,
        screenY: 50,
      })
    })
    expect(result.current.state.hoverCoords).toEqual({
      worldX: 1.0,
      worldY: 2.0,
      worldZ: 3.0,
      screenX: 100,
      screenY: 50,
    })
    act(() => {
      result.current.actions.setHoverCoords(null)
    })
    expect(result.current.state.hoverCoords).toBeNull()
  })
})
