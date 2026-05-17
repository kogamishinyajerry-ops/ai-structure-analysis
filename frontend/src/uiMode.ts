// FM-04a Phase 25 C — Basic / Advanced UI mode state machine.
//
// Phase 24 B shipped a one-shot onboarding tour for new reviewers;
// Phase 25 C addresses the cognitive-load axis for RETURNING reviewers
// by giving them a topbar toggle that hides the advanced-tier control
// surfaces (threshold filter, section cut, per-component switcher,
// probe-list panel).
//
// State preservation is a hard contract (see C:-1 anti-gaming guard):
// toggling Basic does NOT destroy any underlying state (threshold,
// section, probe list, etc.) — it only hides the UI. Toggling back
// to Advanced restores the same values.
//
// All functions are pure (no I/O outside the explicit localStorage
// adapter).
//
// Tier 1 / Tier 2 engineering candidate; not signed validation; not
// benchmark agreement.

/** Stable identifier for each advanced-tier feature. The UI gates
 * visibility on `shouldShowFeature(mode, id)`. */
export type AdvancedFeatureId =
  | 'threshold-filter'
  | 'section-cut'
  | 'field-component-switcher'
  | 'probe-list-panel';

export const ADVANCED_FEATURE_IDS: readonly AdvancedFeatureId[] = [
  'threshold-filter',
  'section-cut',
  'field-component-switcher',
  'probe-list-panel',
] as const;

/** Two-state UI mode. Default is 'basic' on first load. */
export type UiMode = 'basic' | 'advanced';

export const UI_MODE_INITIAL: UiMode = 'basic';

/** LocalStorage key for the persisted mode. */
export const UI_MODE_LS_KEY = 'fm04a.ui.mode.v1';

/**
 * Whether a given advanced-tier feature should be rendered in the
 * current mode. Returns true in 'advanced'; false in 'basic'.
 *
 * The contract is intentionally STRICT — in basic mode every advanced
 * feature MUST be hidden, with no per-feature overrides. The basic
 * mode is supposed to be predictable.
 */
export function shouldShowFeature(
  mode: UiMode,
  featureId: AdvancedFeatureId,
): boolean {
  // Suppress unused-parameter lint while preserving the typed shape.
  void featureId;
  return mode === 'advanced';
}

/** Pure reducer: toggle the mode. */
export function toggleMode(mode: UiMode): UiMode {
  return mode === 'basic' ? 'advanced' : 'basic';
}

/** Pure reducer: explicitly set the mode. */
export function setMode(_current: UiMode, next: UiMode): UiMode {
  return next;
}

export interface UiModeStorage {
  load: () => UiMode;
  save: (mode: UiMode) => void;
}

/** Default localStorage-backed storage. Returns the persisted mode
 * if present and valid; otherwise UI_MODE_INITIAL. */
export function createUiModeStorage(
  globalRef: typeof globalThis = globalThis,
): UiModeStorage {
  const ls = (globalRef as { localStorage?: Storage }).localStorage;
  if (!ls) {
    return {
      load: () => UI_MODE_INITIAL,
      save: () => {
        /* no-op */
      },
    };
  }
  return {
    load: () => {
      try {
        const raw = ls.getItem(UI_MODE_LS_KEY);
        if (raw === 'basic' || raw === 'advanced') return raw;
        return UI_MODE_INITIAL;
      } catch {
        return UI_MODE_INITIAL;
      }
    },
    save: (mode) => {
      try {
        ls.setItem(UI_MODE_LS_KEY, mode);
      } catch {
        /* swallow quota / SecurityError */
      }
    },
  };
}
