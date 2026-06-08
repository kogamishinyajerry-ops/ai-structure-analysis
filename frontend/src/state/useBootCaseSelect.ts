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
  bootResultReady = false,
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

  // FM-04a Phase 41.4 — onboarding/promo auto-show decisions (Codex R0→R2 + this round).
  //   TOUR (first-visit onboarding): genuine no-case landing ONLY. `ready`
  //   (casesLoaded && !sessionActive) suppresses it during any upload/report
  //   session; !activeCaseId && !preferredAvailable keeps it off a boot/opened case
  //   and off the first-paint flash before the auto-select effect runs.
  //   PROMO (one-time advanced-controls nudge): gate on `bootResultReady` ALONE
  //   (App passes Boolean(report) && !loading) — i.e. a result has actually PAINTED
  //   and nothing is loading. It must NOT reuse `ready`: sessionActive is
  //   Boolean(file || report), so the instant a result exists `ready` is false —
  //   reusing it made the promo permanently UNREACHABLE in the real app (this-round
  //   Codex P2). The painted-result edge keeps the promo off the boot shimmer / the
  //   upload-in-flight window (loading true / report null) yet reachable once the
  //   result is up — which is also exactly when the advanced viewport controls it
  //   nudges toward are relevant.
  const preferredAvailable =
    !!preferredCaseId && availableCases.some((c) => c.id === preferredCaseId);
  const ready = casesLoaded && !sessionActive;
  const tourAutoShow = ready && !activeCaseId && !preferredAvailable;
  return {
    tourAutoShow,
    // Disjunction of two non-overlapping arming paths: (1) the no-case landing
    // where the tour ends — the promo must surface there per shouldShowAdvancedPrompt
    // even before any report exists (Codex R1 this-round F6); (2) once a result has
    // PAINTED. Every suppression window (pre-cases / boot-pending / shimmer /
    // upload-in-flight) leaves BOTH disjuncts false.
    promoAutoShow: tourAutoShow || (casesLoaded && bootResultReady),
  };
}
