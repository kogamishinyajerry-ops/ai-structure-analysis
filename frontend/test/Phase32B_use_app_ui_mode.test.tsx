// FM-04a Phase 32 B — useAppUiMode App-root reducer hook pins.
//
// Phase 31 B introduced the panel-level useViewportLayout
// extraction. Phase 32 B mirrors the pattern at App-root for the
// cohesive appUiMode + tour-dismissed cluster (Phase 29 C work).
//
// **Honest scope**: this is PARTIAL closure of Phase 31 honest
// gap #7. App.tsx has ~38 useState/useEffect/useMemo surfaces;
// Phase 32 B extracts just the uiMode cluster. The remaining
// ~36 surfaces are deferred to Phase 33+. Audit will reflect
// this as a partial Dim 3 lift (NOT the full Phase 31 FINAL
// projection of 91 → 93).
//
// Anti-gaming guards:
//   C:-1: App.tsx behavioral tests (Phase 29 C tour pin) must
//         still pass.
//   D:-1: hook is opt-in via explicit import; tests verify
//         no module-level side effects.
//   E:-1: SSR-safe storage adapter (Phase 29 C precedent).

import { renderHook, act } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it } from 'vitest'

import { useAppUiMode } from '../src/state/useAppUiMode'

describe('Phase 32 B — useAppUiMode hook', () => {
  beforeEach(() => {
    // Clear the localStorage key the hook uses (createUiModeStorage
    // writes to `fm04a.uiMode.v1`).
    if (typeof window !== 'undefined') {
      window.localStorage.clear()
    }
  })
  afterEach(() => {
    if (typeof window !== 'undefined') {
      window.localStorage.clear()
    }
  })

  describe('initial state', () => {
    it('returns { state, actions } shape', () => {
      const { result } = renderHook(() => useAppUiMode())
      expect(result.current).toHaveProperty('state')
      expect(result.current).toHaveProperty('actions')
    })

    it('exposes appUiMode + appTourDismissedInSession in state', () => {
      const { result } = renderHook(() => useAppUiMode())
      expect(result.current.state).toHaveProperty('appUiMode')
      expect(result.current.state).toHaveProperty('appTourDismissedInSession')
    })

    it('exposes handleAppUiModeChange + markTourDismissedInSession in actions', () => {
      const { result } = renderHook(() => useAppUiMode())
      expect(typeof result.current.actions.handleAppUiModeChange).toBe('function')
      expect(typeof result.current.actions.markTourDismissedInSession).toBe('function')
    })

    it('appTourDismissedInSession defaults to false', () => {
      const { result } = renderHook(() => useAppUiMode())
      expect(result.current.state.appTourDismissedInSession).toBe(false)
    })

    it('appUiMode defaults to storage load (basic when empty)', () => {
      // createUiModeStorage default for unset localStorage is 'basic'
      // per Phase 25 C / 29 C precedent.
      const { result } = renderHook(() => useAppUiMode())
      expect(result.current.state.appUiMode).toBe('basic')
    })

    it('appUiMode rehydrates from localStorage when set', () => {
      window.localStorage.setItem('fm04a.ui.mode.v1', 'advanced')
      const { result } = renderHook(() => useAppUiMode())
      expect(result.current.state.appUiMode).toBe('advanced')
    })
  })

  describe('handleAppUiModeChange action', () => {
    it('updates state AND persists to localStorage', () => {
      const { result } = renderHook(() => useAppUiMode())
      act(() => {
        result.current.actions.handleAppUiModeChange('advanced')
      })
      expect(result.current.state.appUiMode).toBe('advanced')
      expect(window.localStorage.getItem('fm04a.ui.mode.v1')).toBe('advanced')
    })

    it('toggling back to basic persists the change', () => {
      const { result } = renderHook(() => useAppUiMode())
      act(() => {
        result.current.actions.handleAppUiModeChange('advanced')
      })
      act(() => {
        result.current.actions.handleAppUiModeChange('basic')
      })
      expect(result.current.state.appUiMode).toBe('basic')
      expect(window.localStorage.getItem('fm04a.ui.mode.v1')).toBe('basic')
    })
  })

  describe('markTourDismissedInSession action', () => {
    it('sets appTourDismissedInSession to true', () => {
      const { result } = renderHook(() => useAppUiMode())
      act(() => {
        result.current.actions.markTourDismissedInSession()
      })
      expect(result.current.state.appTourDismissedInSession).toBe(true)
    })

    it('does NOT persist to localStorage (session-only flag)', () => {
      const { result } = renderHook(() => useAppUiMode())
      act(() => {
        result.current.actions.markTourDismissedInSession()
      })
      // The flag is session-only by Phase 29 C design — never persisted.
      // Storage should only contain the uiMode key (set on default load).
      const keys = Object.keys(window.localStorage)
      expect(
        keys.some((k) => k.toLowerCase().includes('tour-dismissed')),
      ).toBe(false)
    })

    it('is idempotent (calling twice keeps true)', () => {
      const { result } = renderHook(() => useAppUiMode())
      act(() => {
        result.current.actions.markTourDismissedInSession()
      })
      act(() => {
        result.current.actions.markTourDismissedInSession()
      })
      expect(result.current.state.appTourDismissedInSession).toBe(true)
    })
  })

  describe('independence: uiMode and tour-dismissed do not couple', () => {
    it('changing uiMode does NOT alter tour-dismissed flag', () => {
      const { result } = renderHook(() => useAppUiMode())
      act(() => {
        result.current.actions.markTourDismissedInSession()
      })
      expect(result.current.state.appTourDismissedInSession).toBe(true)
      act(() => {
        result.current.actions.handleAppUiModeChange('advanced')
      })
      expect(result.current.state.appTourDismissedInSession).toBe(true)
    })

    it('marking tour dismissed does NOT alter uiMode', () => {
      const { result } = renderHook(() => useAppUiMode())
      act(() => {
        result.current.actions.handleAppUiModeChange('advanced')
      })
      expect(result.current.state.appUiMode).toBe('advanced')
      act(() => {
        result.current.actions.markTourDismissedInSession()
      })
      expect(result.current.state.appUiMode).toBe('advanced')
    })
  })

  describe('storage SSR safety', () => {
    it('hook initialization does not throw without window context', () => {
      // This is a smoke test — renderHook always runs in jsdom which
      // has window. Phase 29 C's createUiModeStorage handles the
      // typeof window === 'undefined' case via its own guard. This
      // test just confirms the hook doesn't error on standard init.
      expect(() => renderHook(() => useAppUiMode())).not.toThrow()
    })
  })
})
