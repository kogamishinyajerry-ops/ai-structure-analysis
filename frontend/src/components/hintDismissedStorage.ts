// FM-04a Phase 39 B — in-context-hint dismissal persistence.
//
// Mirrors sectionCollapseStorage (Phase 29 B): a per-hint dismissed boolean
// persisted to localStorage under a stable key:
//
//   fm04a.in-context-hint.<hintId>.dismissed.v1
//
// Anti-gaming guards:
//   C:-1: keys include the hintId verbatim — no cross-hint bleed.
//   D:-1: default is NOT dismissed (additive — dismissing is opt-in; a
//         first-time visitor sees every hint until they dismiss it).
//   E:-1: parse-fail / SecurityError → return null (caller shows the hint).
//         Never throws to the UI.
//
// Tier 1 / Tier 2 engineering candidate; not signed validation; not
// benchmark agreement.

export const HINT_DISMISSED_LS_KEY_PREFIX = 'fm04a.in-context-hint.';
export const HINT_DISMISSED_LS_KEY_SUFFIX = '.dismissed.v1';

/** Stable storage key. hintId is interpolated verbatim (C:-1 guard);
 * callers must use stable, URL-safe-ish strings. */
export function hintDismissedStorageKey(hintId: string): string {
  return `${HINT_DISMISSED_LS_KEY_PREFIX}${hintId}${HINT_DISMISSED_LS_KEY_SUFFIX}`;
}

/** Load the persisted dismissed state for a hint, or `null` if the key is
 * missing / parse fails. Caller treats `null` as "default" (shown, D:-1). */
export function loadHintDismissed(hintId: string): boolean | null {
  if (typeof window === 'undefined') return null;
  try {
    const raw = window.localStorage.getItem(hintDismissedStorageKey(hintId));
    if (raw === null) return null;
    if (raw === 'true') return true;
    if (raw === 'false') return false;
    return null; // corrupted value — treat as missing
  } catch {
    return null;
  }
}

/** Persist the dismissed state for a hint. Swallows quota / SecurityError
 * silently (E:-1: never throws to UI). */
export function saveHintDismissed(hintId: string, dismissed: boolean): void {
  if (typeof window === 'undefined') return;
  try {
    window.localStorage.setItem(
      hintDismissedStorageKey(hintId),
      dismissed ? 'true' : 'false',
    );
  } catch {
    /* swallow */
  }
}

/** Clear a hint's persisted state (test teardown helper; also used if the
 * user explicitly wants to re-surface dismissed hints). */
export function clearHintDismissed(hintId: string): void {
  if (typeof window === 'undefined') return;
  try {
    window.localStorage.removeItem(hintDismissedStorageKey(hintId));
  } catch {
    /* swallow */
  }
}
