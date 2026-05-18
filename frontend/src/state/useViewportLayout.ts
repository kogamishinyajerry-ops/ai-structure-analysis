// FM-04a Phase 31 B — useViewportLayout custom hook.
//
// Closes the 3-phase reducer-extraction debt called out by:
//   - Phase 27 punchlist #3
//   - Phase 29 audit recommendation #2
//   - Phase 30 UX audit Dim 3 -1 debit
//
// Encapsulates the viewport-layout state and effect cascade that
// grew across Phases 27 D / 28 C / 30 B / 30 C into a single hook,
// mirroring the Phase 29 B `useTrustSections` extraction pattern.
//
// State surfaces owned by this hook:
//   - viewportMode ('webgl' | 'svg')
//   - showCompanionViewport + companionSectionCut (Phase 30 B)
//   - hoverCoords (Phase 30 C)
//   - probeList + exitingProbeLabel + restoredCount (Phase 27/28)
//   - corruptedToast (Phase 30 C)
//
// Effect cascades owned:
//   1. Case-mount diagnostic load (Phase 27 D + Phase 30 C):
//      loadProbeListWithDiagnostic → setProbeList + setRestoredCount
//      + (setCorruptedToast on corruption | clear).
//   2. Probe-list persistence on every change (Phase 27 D).
//   3. Auto-dismiss restored toast after 4 s (Phase 28 C).
//   4. Auto-dismiss corrupted toast after 8 s (Phase 30 C).
//   5. Companion enabled + cut-position persistence (Phase 30 B).
//
// Anti-gaming guards:
//   C:-1 — ALL existing Phase 27/28/30 B/30 C behavioral pins MUST
//          still pass. If a test needs to change to accommodate
//          the hook, that signals a semantic regression — revert
//          and re-plan.
//   D:-1 — hook is opt-in via explicit import; no context / global
//          state leakage. Returns its state surface verbatim.
//   E:-1 — effect cleanup respects unmount: timers cleared, no
//          stale-closure setState after unmount.
//
// Tier 1 / Tier 2 engineering candidate; not signed validation;
// not benchmark agreement.

import { useEffect, useState } from 'react';

import type { ProbeListState } from '../components/probeList';
import { PROBE_LIST_INITIAL_STATE } from '../components/probeList';
import {
  loadProbeListWithDiagnostic,
  saveProbeList,
} from '../components/probeListStorage';
import {
  computeCompanionInitialCut,
  loadCompanionEnabled,
  loadCompanionSectionCut,
  saveCompanionEnabled,
  saveCompanionSectionCut,
} from '../components/companionViewportStorage';
import type { SectionCutState } from '../components/viewportGeometry';

export type ViewportRenderMode = 'webgl' | 'svg';

export interface HoverCoordsInfo {
  worldX: number;
  worldY: number;
  worldZ: number;
  screenX: number;
  screenY: number;
}

export interface CorruptedToastInfo {
  caseId: string;
  reason: string;
}

export interface ViewportLayoutState {
  viewportMode: ViewportRenderMode;
  showCompanionViewport: boolean;
  companionSectionCut: SectionCutState;
  hoverCoords: HoverCoordsInfo | null;
  probeList: ProbeListState;
  exitingProbeLabel: number | null;
  restoredCount: number;
  corruptedToast: CorruptedToastInfo | null;
}

export interface ViewportLayoutActions {
  setViewportMode: (mode: ViewportRenderMode) => void;
  /** Toggle the Compare-cuts overlay. When turning ON for the
   * first time AND no persisted cut exists, seed the companion
   * cut by mirroring the primary's axis + flipping showLow so
   * the companion exposes the half the primary is hiding (Phase
   * 30 B heuristic). When turning OFF, the companion cut state
   * is PRESERVED (C:-1 anti-gaming) for reopen. */
  toggleCompanion: (primarySectionCut: SectionCutState | null) => void;
  setCompanionSectionCut: (next: SectionCutState) => void;
  setHoverCoords: (info: HoverCoordsInfo | null) => void;
  setProbeList: React.Dispatch<React.SetStateAction<ProbeListState>>;
  setExitingProbeLabel: (label: number | null) => void;
  setRestoredCount: (count: number) => void;
  dismissCorruptedToast: () => void;
}

export interface UseViewportLayoutInput {
  /** Case ID drives the case-mount cascade (probe-list load +
   * diagnostic + persistence). When `null`, the cascade clears
   * to initial state. */
  caseId: string | null;
}

export interface UseViewportLayoutResult {
  state: ViewportLayoutState;
  actions: ViewportLayoutActions;
}

/** Custom hook owning the viewport-layout state + effect cascade.
 *
 * Returns `{ state, actions }`. State is read-only; mutation goes
 * through actions. Effects auto-wire on mount and re-fire on
 * caseId change.
 */
export function useViewportLayout(
  input: UseViewportLayoutInput,
): UseViewportLayoutResult {
  const { caseId } = input;

  // ── State ────────────────────────────────────────────────────
  const [viewportMode, setViewportMode] =
    useState<ViewportRenderMode>('webgl');

  const [showCompanionViewport, setShowCompanionViewport] = useState<boolean>(
    () => loadCompanionEnabled(),
  );
  const [companionSectionCut, setCompanionSectionCut] = useState<SectionCutState>(
    () => loadCompanionSectionCut() ?? computeCompanionInitialCut(null),
  );

  const [hoverCoords, setHoverCoords] = useState<HoverCoordsInfo | null>(
    null,
  );

  const [probeList, setProbeList] = useState<ProbeListState>(() =>
    caseId
      ? loadProbeListWithDiagnostic(caseId).state
      : PROBE_LIST_INITIAL_STATE,
  );

  const [exitingProbeLabel, setExitingProbeLabel] = useState<number | null>(
    null,
  );

  const [restoredCount, setRestoredCount] = useState<number>(() => {
    if (!caseId) return 0;
    return loadProbeListWithDiagnostic(caseId).state.entries.length;
  });

  const [corruptedToast, setCorruptedToast] = useState<CorruptedToastInfo | null>(
    null,
  );

  // ── Effects ──────────────────────────────────────────────────

  // 1. Case-mount diagnostic load (Phase 27 D + Phase 30 C).
  useEffect(() => {
    if (caseId) {
      const { state: loaded, corrupted, reason } =
        loadProbeListWithDiagnostic(caseId);
      setProbeList(loaded);
      setRestoredCount(loaded.entries.length);
      if (corrupted) {
        setCorruptedToast({
          caseId,
          reason: reason ?? 'corrupted payload',
        });
      } else {
        setCorruptedToast(null);
      }
    } else {
      setProbeList(PROBE_LIST_INITIAL_STATE);
      setRestoredCount(0);
      setCorruptedToast(null);
    }
  }, [caseId]);

  // 2. Auto-dismiss corrupted toast after 8 s (Phase 30 C).
  useEffect(() => {
    if (!corruptedToast) return;
    const timer = setTimeout(() => setCorruptedToast(null), 8000);
    return () => clearTimeout(timer);
  }, [corruptedToast]);

  // 3. Auto-dismiss restored toast after 4 s (Phase 28 C).
  useEffect(() => {
    if (restoredCount === 0) return;
    const timer = setTimeout(() => setRestoredCount(0), 4000);
    return () => clearTimeout(timer);
  }, [restoredCount]);

  // 4. Probe-list persistence on every change (Phase 27 D).
  useEffect(() => {
    if (caseId) saveProbeList(caseId, probeList);
  }, [caseId, probeList]);

  // 5a. Companion enabled persistence (Phase 30 B).
  useEffect(() => {
    saveCompanionEnabled(showCompanionViewport);
  }, [showCompanionViewport]);

  // 5b. Companion cut-position persistence (Phase 30 B).
  useEffect(() => {
    saveCompanionSectionCut(companionSectionCut);
  }, [companionSectionCut]);

  // ── Actions ──────────────────────────────────────────────────

  const toggleCompanion = (primarySectionCut: SectionCutState | null) => {
    setShowCompanionViewport((current) => {
      const next = !current;
      if (next && primarySectionCut !== null) {
        // Seed via computeCompanionInitialCut(primary) IFF the
        // companion cut has not yet been customized. We compare
        // against the default cut shape `computeCompanionInitialCut
        // (null)` — checking the live state, NOT localStorage,
        // because the first-render persistence effect always writes
        // SOMETHING to localStorage before the user can act, so a
        // raw `loadCompanionSectionCut() === null` check would never
        // be true after first render (race condition).
        // C:-1: a user-edited cut diverges from the default and
        // will be preserved verbatim.
        setCompanionSectionCut((existing) => {
          const defaultCut = computeCompanionInitialCut(null);
          if (
            existing.axis === defaultCut.axis
            && existing.positionM === defaultCut.positionM
            && existing.showLow === defaultCut.showLow
          ) {
            return computeCompanionInitialCut(primarySectionCut);
          }
          return existing;
        });
      }
      return next;
    });
  };

  const dismissCorruptedToast = () => setCorruptedToast(null);

  const state: ViewportLayoutState = {
    viewportMode,
    showCompanionViewport,
    companionSectionCut,
    hoverCoords,
    probeList,
    exitingProbeLabel,
    restoredCount,
    corruptedToast,
  };

  const actions: ViewportLayoutActions = {
    setViewportMode,
    toggleCompanion,
    setCompanionSectionCut,
    setHoverCoords,
    setProbeList,
    setExitingProbeLabel,
    setRestoredCount,
    dismissCorruptedToast,
  };

  return { state, actions };
}
