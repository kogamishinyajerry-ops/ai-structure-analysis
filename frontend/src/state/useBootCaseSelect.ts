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
 */
export function useBootCaseSelect(
  availableCases: CaseMetadata[],
  activeCaseId: string | null,
  sessionActive: boolean,
  preferredCaseId: string | null,
  onSelect: (c: CaseMetadata) => void,
): void {
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
}
