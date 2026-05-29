import { useEffect, useRef } from 'react';
import type { CaseMetadata } from '../types/AppTypes';

/**
 * FM-04a Phase 41.4 — demo "centerpiece on load".
 *
 * Once the case list has loaded and the user has NOT already opened a case,
 * auto-open a preferred renderable candidate so the 3D result leads the first
 * paint (golden path 案例→求解→结果可视化). Guarantees:
 *
 * - fires at most ONCE per mount (a ref guard — no auto-select loop even though
 *   `onSelect` is recreated each render);
 * - never overrides a user/prior selection (`activeCaseId` already set → stand down);
 * - stands down if a session is already underway (`sessionActive` — e.g. an
 *   upload-driven flow that keeps `activeCaseId` null but has a report/file;
 *   Codex R0 P1: otherwise a slow `/cases` load would steal the upload session);
 * - silently no-ops if the preferred case is absent from `availableCases`
 *   (honest fallback — the case-browser landing renders instead, no fabrication).
 *
 * Extracted from `App.tsx` to honor the App.tsx <1500 LOC pin (the Phase 35 C /
 * 38 I hook-extraction precedent).
 *
 * RETURNS the tour/promo `autoShow` decisions (Codex R0+R1 P2s): the boot
 * landing policy already lives here, so the gates that keep onboarding off the
 * boot 3D hero are co-located rather than re-derived in App.
 */
export interface BootAutoShow {
  /** First-visit tour: surfaces ONLY on the genuine no-case landing. */
  tourAutoShow: boolean;
  /** Advanced-mode promo: suppressed only during the boot first-paint flash
   * window; stays reachable once the boot case settles (or on the no-case
   * landing) for returning basic-mode users (Codex R1 P2 #1 — never permanently
   * unreachable). */
  promoAutoShow: boolean;
}

export function useBootCaseSelect(
  availableCases: CaseMetadata[],
  activeCaseId: string | null,
  sessionActive: boolean,
  preferredCaseId: string | null,
  onSelect: (c: CaseMetadata) => void,
  casesLoaded = false,
): BootAutoShow {
  const done = useRef(false);

  useEffect(() => {
    if (done.current) return;
    if (activeCaseId || sessionActive) {
      // a case is open OR an upload/report session has started — stand down for
      // the rest of this mount (never reclaim it later either).
      done.current = true;
      return;
    }
    if (!preferredCaseId || availableCases.length === 0) return;
    const match = availableCases.find((c) => c.id === preferredCaseId);
    if (!match) return; // preferred case not in the list → leave the browser landing
    done.current = true;
    onSelect(match);
  }, [availableCases, activeCaseId, sessionActive, preferredCaseId, onSelect]);

  // FM-04a Phase 41.4 — onboarding/promo auto-show decisions.
  //   - !casesLoaded → /cases not yet resolved (or reloading): stay hidden, no
  //     pre-load flash (Codex R1 P2 #2: App resets casesLoaded per request);
  //   - sessionActive → an upload/report flow clears activeCaseId but is a live
  //     session — never re-arm onboarding over it (Codex R0 P2 #1);
  //   - bootPending → a boot auto-select WILL fire this mount: suppress from the
  //     first paint, before the effect runs (Codex R0 P2 #2: no flash over the
  //     boot 3D hero).
  const preferredAvailable =
    !!preferredCaseId && availableCases.some((c) => c.id === preferredCaseId);
  const bootPending = preferredAvailable && !activeCaseId;
  const ready = casesLoaded && !sessionActive;
  return {
    // Tour: genuine no-case landing only (never over a boot/opened case).
    tourAutoShow: ready && !activeCaseId && !preferredAvailable,
    // Promo: only the boot first-paint flash is suppressed; once the case has
    // settled the one-time advanced nudge stays reachable.
    promoAutoShow: ready && !bootPending,
  };
}
