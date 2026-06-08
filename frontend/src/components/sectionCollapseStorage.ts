// FM-04a Phase 29 B — section-collapse persistence.
//
// Each trust-section has an independent collapsed/expanded state
// persisted to localStorage under a stable per-section key:
//
//   fm04a.trust-section.<storageKey>.collapsed.v1
//
// Anti-gaming guards:
//   C:-1: keys include the storageKey verbatim — no cross-section
//         bleed; switching sections never mis-applies state.
//   D:-1: default is EXPANDED (additive — collapsing is opt-in;
//         existing reviewers see no behavior change).
//   E:-1: parse-fail / SecurityError → return null (caller defaults
//         to expanded). Never throws.
//
// Tier 1 / Tier 2 engineering candidate; not signed validation;
// not benchmark agreement.

export const SECTION_COLLAPSE_LS_KEY_PREFIX = 'fm04a.trust-section.';
export const SECTION_COLLAPSE_LS_KEY_SUFFIX = '.collapsed.v1';

/** Stable storage key. The storageKey identifier is interpolated
 * verbatim (C:-1 guard); callers must use stable, URL-safe-ish
 * strings. */
export function sectionCollapseStorageKey(storageKey: string): string {
  return `${SECTION_COLLAPSE_LS_KEY_PREFIX}${storageKey}${SECTION_COLLAPSE_LS_KEY_SUFFIX}`;
}

/** Load the persisted collapsed state for a section, or `null` if
 * the key is missing / parse fails. Caller treats `null` as
 * "default" (expanded, D:-1). */
export function loadSectionCollapsed(storageKey: string): boolean | null {
  if (typeof window === 'undefined') return null;
  try {
    const raw = window.localStorage.getItem(
      sectionCollapseStorageKey(storageKey),
    );
    if (raw === null) return null;
    if (raw === 'true') return true;
    if (raw === 'false') return false;
    return null; // corrupted value — treat as missing
  } catch {
    return null;
  }
}

/** Persist the collapsed state for a section. Swallows quota /
 * SecurityError silently (E:-1: never throws to UI). */
export function saveSectionCollapsed(
  storageKey: string,
  collapsed: boolean,
): void {
  if (typeof window === 'undefined') return;
  try {
    window.localStorage.setItem(
      sectionCollapseStorageKey(storageKey),
      collapsed ? 'true' : 'false',
    );
  } catch {
    /* swallow */
  }
}

/** Clear a section's persisted state (test teardown helper; also
 * used if the user explicitly wants to reset). */
export function clearSectionCollapsed(storageKey: string): void {
  if (typeof window === 'undefined') return;
  try {
    window.localStorage.removeItem(sectionCollapseStorageKey(storageKey));
  } catch {
    /* swallow */
  }
}
