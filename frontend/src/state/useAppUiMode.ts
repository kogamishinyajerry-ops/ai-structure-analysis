// FM-04a Phase 32 B — useAppUiMode App-root reducer hook.
//
// Mirrors the Phase 31 B useViewportLayout extraction pattern but
// scoped to the App-root uiMode + tour-dismissed cluster that
// Phase 29 C introduced. App-root needs to own uiMode (instead of
// scoping it inside ResultMeshPlaybackPanel) because the
// OnboardingTour + AdvancedModePromo mount above the panel — tabs
// other than Visual must receive onboarding too.
//
// **Honest scope note**: Phase 31 honest gap #7 said "App.tsx
// reducer debt half-closed" and projected Phase 32 B as
// "extract App-root state into useAppLayout". App.tsx has ~38
// useState/useEffect/useMemo surfaces; a full extraction is
// multi-phase work and would carry high regression risk in a
// single slice. Phase 32 B does the SMALLEST cohesive extraction
// that delivers real value: just the appUiMode cluster.
//
// The remaining App.tsx state (case selection, comparison cases,
// job tracking, materials, analysis flow) is deferred to Phase
// 33+ where each cluster can have a dedicated slice for safe
// extraction. This is the same scope-discipline pattern as Phase
// 31 A's contact→heat pivot and Phase 31 C's cylinder-pv→
// Richardson pivot: ship the LOWEST-RISK win, document the rest
// as honest deferral.
//
// State surfaces owned by this hook:
//   - appUiMode ('basic' | 'advanced') with localStorage adapter
//   - appTourDismissedInSession (boolean, session-only)
//
// Actions:
//   - handleAppUiModeChange(next) — updates state AND persists
//     to localStorage
//   - markTourDismissedInSession() — sets the in-session flag
//     (called once by OnboardingTour onDismissed)
//
// Anti-gaming guards:
//   C:-1 — ALL existing Phase 29 C App-root tour behavior pins
//          MUST still pass. If a test needs to change to
//          accommodate the hook, that signals a semantic
//          regression — revert and re-plan.
//   D:-1 — hook is opt-in via explicit import; no context /
//          global state leakage.
//   E:-1 — storage adapter respects SSR (createAppUiModeStorage
//          handles the typeof window === 'undefined' case).
//
// Tier 1 / Tier 2 engineering candidate; not signed validation;
// not benchmark agreement.

import { useMemo, useState } from 'react';

import {
  createUiModeStorage as createAppUiModeStorage,
  type UiMode as AppUiMode,
} from '../uiMode';

export interface UseAppUiModeState {
  appUiMode: AppUiMode;
  appTourDismissedInSession: boolean;
}

export interface UseAppUiModeActions {
  /** Update the App-root uiMode AND persist to localStorage in
   * one call. */
  handleAppUiModeChange: (next: AppUiMode) => void;
  /** Mark the tour as dismissed in the current browser session.
   * Wired to OnboardingTour's `onDismissed` prop. */
  markTourDismissedInSession: () => void;
}

export interface UseAppUiModeResult {
  state: UseAppUiModeState;
  actions: UseAppUiModeActions;
}

/** Custom hook owning the App-root uiMode + tour-dismissed
 * state.
 *
 * Returns `{ state, actions }`. State is read-only; mutation
 * goes through actions. Storage adapter is constructed once
 * via useMemo for stable identity across renders.
 */
export function useAppUiMode(): UseAppUiModeResult {
  const appUiModeStorage = useMemo(() => createAppUiModeStorage(), []);
  const [appUiMode, setAppUiMode] = useState<AppUiMode>(() =>
    appUiModeStorage.load(),
  );
  const [appTourDismissedInSession, setAppTourDismissedInSession] =
    useState<boolean>(false);

  const handleAppUiModeChange = (next: AppUiMode): void => {
    setAppUiMode(next);
    appUiModeStorage.save(next);
  };

  const markTourDismissedInSession = (): void => {
    setAppTourDismissedInSession(true);
  };

  const state: UseAppUiModeState = {
    appUiMode,
    appTourDismissedInSession,
  };

  const actions: UseAppUiModeActions = {
    handleAppUiModeChange,
    markTourDismissedInSession,
  };

  return { state, actions };
}
