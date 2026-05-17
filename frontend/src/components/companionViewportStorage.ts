// FM-04a Phase 30 B — companion-viewport persistence helpers.
//
// Two independent localStorage keys:
//   fm04a.companion-viewport.enabled.v1      — boolean "true" | "false"
//   fm04a.companion-viewport.cut-position.v1 — JSON SectionCutState
//
// Anti-gaming guards:
//   C:-1: companion state SCOPED separately from primary section-cut.
//         Toggling Compare off does NOT clear the companion cut
//         position; switching Compare on later restores the same
//         position the user last set. Pinned by Phase 30 B tests.
//   D:-1: default disabled. Existing reviewers see no behavior change;
//         the compare layout is purely additive.
//   E:-1: parse-fail / corrupted JSON / SecurityError → return null
//         and let the caller compute a sensible default. Never throws.
//
// Tier 1 / Tier 2 engineering candidate; not signed validation; not
// benchmark agreement.

import type { SectionCutState } from './viewportGeometry';

export const COMPANION_ENABLED_LS_KEY =
  'fm04a.companion-viewport.enabled.v1';
export const COMPANION_CUT_LS_KEY =
  'fm04a.companion-viewport.cut-position.v1';

/** Load whether the companion viewport is enabled. Defaults to
 * `false` (D:-1: additive — Compare is opt-in). */
export function loadCompanionEnabled(): boolean {
  if (typeof window === 'undefined') return false;
  try {
    return window.localStorage.getItem(COMPANION_ENABLED_LS_KEY) === 'true';
  } catch {
    return false;
  }
}

/** Persist the enabled flag. Swallows SecurityError / quota issues
 * silently — E:-1: never throws to UI. */
export function saveCompanionEnabled(enabled: boolean): void {
  if (typeof window === 'undefined') return;
  try {
    window.localStorage.setItem(
      COMPANION_ENABLED_LS_KEY,
      enabled ? 'true' : 'false',
    );
  } catch {
    /* swallow */
  }
}

/** Load the persisted companion section-cut state, or `null` if no
 * key exists / parse fails / payload shape is invalid. Caller treats
 * `null` as "compute fresh default" via `computeCompanionInitialCut`. */
export function loadCompanionSectionCut(): SectionCutState | null {
  if (typeof window === 'undefined') return null;
  try {
    const raw = window.localStorage.getItem(COMPANION_CUT_LS_KEY);
    if (raw === null) return null;
    const parsed = JSON.parse(raw) as unknown;
    if (typeof parsed !== 'object' || parsed === null) return null;
    const obj = parsed as Record<string, unknown>;
    if (obj.axis !== 'x' && obj.axis !== 'y' && obj.axis !== 'z') {
      return null;
    }
    if (typeof obj.positionM !== 'number' || !Number.isFinite(obj.positionM)) {
      return null;
    }
    if (typeof obj.showLow !== 'boolean') return null;
    return {
      axis: obj.axis,
      positionM: obj.positionM,
      showLow: obj.showLow,
    };
  } catch {
    return null;
  }
}

/** Persist (or clear) the companion section-cut state. Pass `null`
 * to remove the key entirely (e.g., test teardown). */
export function saveCompanionSectionCut(
  cut: SectionCutState | null,
): void {
  if (typeof window === 'undefined') return;
  try {
    if (cut === null) {
      window.localStorage.removeItem(COMPANION_CUT_LS_KEY);
    } else {
      window.localStorage.setItem(COMPANION_CUT_LS_KEY, JSON.stringify(cut));
    }
  } catch {
    /* swallow */
  }
}

/** Compute a sensible initial cut for the companion when no persisted
 * value exists. If the primary already has a cut, mirror the axis but
 * flip `showLow` so the companion shows the half the primary is
 * hiding (the most useful default for a comparison view). Otherwise
 * default to x-axis at origin with `showLow: false`. */
export function computeCompanionInitialCut(
  primaryCut: SectionCutState | null,
): SectionCutState {
  if (primaryCut) {
    return {
      axis: primaryCut.axis,
      positionM: primaryCut.positionM,
      showLow: !primaryCut.showLow,
    };
  }
  return { axis: 'x', positionM: 0, showLow: false };
}
