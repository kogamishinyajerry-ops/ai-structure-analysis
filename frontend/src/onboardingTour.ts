// FM-04a Phase 24 B — onboarding tour state machine.
// FM-04a Phase 27 D — tour copy refreshed to v2 (6 steps including
// Basic-mode toggle from Phase 25 C and Δ column from Phase 26 C).
// Storage key bumped from v1 → v2 so previously-dismissed-v1 users
// see the new tour once. Honest annoyance trade: existing users get
// surfaced ONE more tour; that's the cost of refreshing onboarding
// for features they've never been introduced to.
//
// Phase 23 R1 closed at UX 80.8/100 with a -1 cognitive-load
// regression because three new control surfaces (component switcher,
// threshold filter, node-pick HUD) shipped without onboarding. This
// module ships a progressive-disclosure tour and the persistence
// gate so it shows once.
//
// All functions are pure (no I/O outside the explicit localStorage
// adapter); the React component imports them and supplies its own
// dispatcher.
//
// Tier 1 / Tier 2 engineering candidate; not signed validation; not
// benchmark agreement.

/**
 * Stable identifier for each onboarding step. The order is also the
 * progression order; the UI uses the index to render the "n / 4" dots.
 */
export type OnboardingStepId =
  | 'field-component-switcher'
  | 'threshold-filter'
  | 'node-pick'
  | 'section-cut'
  | 'basic-advanced-mode'  // Phase 27 D · introduces Phase 25 C
  | 'probe-diff-column';   // Phase 27 D · introduces Phase 26 C

export interface OnboardingStep {
  id: OnboardingStepId;
  title: string;
  body: string;
  /** Phase from which this affordance shipped. Helps reviewers track
   * what each step is referring back to. */
  shippedInPhase: string;
}

export const ONBOARDING_STEPS: readonly OnboardingStep[] = [
  {
    id: 'field-component-switcher',
    title: 'Pick the stress component you want to see',
    body: 'The legend dropdown switches between Mises, individual normal stresses (σ_xx / σ_yy / σ_zz), shears (σ_xy / σ_yz / σ_xz), and principal stresses. The viewport contour and the threshold filter both honor the selected component.',
    shippedInPhase: 'Phase 23 B',
  },
  {
    id: 'threshold-filter',
    title: 'Hide elements outside a value range',
    body: 'Use the threshold filter row to focus on a stress band: set min / max and toggle IN-range vs OUT-of-range. Elements with no value (e.g. dead or projectile) remain visible regardless of the filter.',
    shippedInPhase: 'Phase 23 D',
  },
  {
    id: 'node-pick',
    title: 'Click any node to probe its value',
    body: 'Click anywhere on a mesh node to open the field-probe HUD. The HUD shows the node label, coordinates in scientific notation, and the field value. Press Escape to clear the pick.',
    shippedInPhase: 'Phase 23 C',
  },
  {
    id: 'section-cut',
    title: 'Slice into the model with a section cut',
    body: 'Use the section-cut depth slider to clip the model along a plane. Combine with magnification to study interior stress distribution. The cut is purely visual; the solver mesh is unchanged.',
    shippedInPhase: 'Phase 22 B',
  },
  // FM-04a Phase 27 D — Basic / Advanced mode toggle (Phase 25 C).
  // Refresh introduces returning reviewers to the cognitive-load
  // escape they may not have noticed in the top-right corner.
  {
    id: 'basic-advanced-mode',
    title: 'Switch between Basic and Advanced reviewer modes',
    body: 'The Basic / Advanced toggle in the viewport header hides advanced control surfaces (threshold filter, section cut, field-component switcher, probe list) when set to Basic. Your selections are preserved across the toggle — Basic just hides the UI, not the state.',
    shippedInPhase: 'Phase 25 C',
  },
  // FM-04a Phase 27 D — Probe-list Δ column (Phase 26 C). The Δ
  // column was added in Phase 26 C but the tour never introduced
  // it. This step refreshes that gap.
  {
    id: 'probe-diff-column',
    title: 'Compare probes with the Δ vs #1 column',
    body: 'When you pin two or more nodes, the probe list adds a Δ column showing the difference vs the first-pinned probe (your baseline). Positive values lead with +, negative with − (Unicode minus). The column hides when only one probe is pinned.',
    shippedInPhase: 'Phase 26 C',
  },
] as const;

export const ONBOARDING_TOTAL_STEPS = ONBOARDING_STEPS.length;

export interface OnboardingState {
  /** 0..ONBOARDING_TOTAL_STEPS-1. ONBOARDING_TOTAL_STEPS = past-end / dismissed. */
  currentStepIndex: number;
  /** True once the user has explicitly dismissed the tour OR completed
   * every step. Persisted to localStorage. */
  dismissed: boolean;
}

export const ONBOARDING_INITIAL_STATE: OnboardingState = {
  currentStepIndex: 0,
  dismissed: false,
};

/** Pure-function reducer: advance one step or mark dismissed at end. */
export function nextStep(state: OnboardingState): OnboardingState {
  if (state.dismissed) return state;
  const newIndex = state.currentStepIndex + 1;
  if (newIndex >= ONBOARDING_TOTAL_STEPS) {
    return { currentStepIndex: ONBOARDING_TOTAL_STEPS, dismissed: true };
  }
  return { ...state, currentStepIndex: newIndex };
}

/** Pure-function reducer: explicit user dismiss (Skip tour link). */
export function dismissTour(state: OnboardingState): OnboardingState {
  return { ...state, dismissed: true };
}

/** Pure-function reducer: developer escape hatch to replay the tour. */
export function resetTour(_state: OnboardingState): OnboardingState {
  return { currentStepIndex: 0, dismissed: false };
}

/**
 * Whether the overlay should be visible. Returns false when:
 * - dismissed in this session, OR
 * - localStorage flag indicates a previous dismissal (caller supplies
 *   the resolved flag so this stays pure).
 */
export function shouldShowTour(
  state: OnboardingState,
  persistedDismissed: boolean,
): boolean {
  if (persistedDismissed) return false;
  if (state.dismissed) return false;
  return state.currentStepIndex < ONBOARDING_TOTAL_STEPS;
}

/** Stable localStorage key.
 *
 * FM-04a Phase 27 D — bumped v1 → v2 because the tour copy was
 * refreshed with 2 new cards (Basic/Advanced mode + Δ column).
 * Existing users who dismissed v1 will see v2 once. v1 dismissals
 * are NOT cleared; if a user wants to revert they keep their
 * `fm04a.onboarding.v1.dismissed=true` separately.
 */
export const ONBOARDING_LS_KEY = 'fm04a.onboarding.v2.dismissed';

export interface OnboardingStorage {
  load: () => boolean;
  save: (dismissed: boolean) => void;
}

/** Default localStorage-backed storage; falls back to no-op when
 * localStorage is unavailable (e.g. SSR or test environments without
 * jsdom). Caller can inject a stub for testing. */
export function createLocalStorageBackedStore(
  globalRef: typeof globalThis = globalThis,
): OnboardingStorage {
  const ls = (globalRef as { localStorage?: Storage }).localStorage;
  if (!ls) {
    return {
      load: () => false,
      save: () => {
        /* no-op */
      },
    };
  }
  return {
    load: () => {
      try {
        return ls.getItem(ONBOARDING_LS_KEY) === 'true';
      } catch {
        return false;
      }
    },
    save: (dismissed) => {
      try {
        ls.setItem(ONBOARDING_LS_KEY, dismissed ? 'true' : 'false');
      } catch {
        /* swallow quota / SecurityError */
      }
    },
  };
}

// ────────────────────────────────────────────────────────────────────
// FM-04a Phase 28 D — Advanced-mode auto-promote prompt.
//
// Closes a gap in the Phase 27 D refresh: the tour now includes a
// 'basic-advanced-mode' step that introduces the Basic/Advanced
// toggle, but new users default to Basic mode and the tour ends
// without surfacing Advanced. The tour-completion → Basic-mode
// reviewer never sees the threshold filter / section cut / probe
// list / field-component switcher that the tour just covered.
//
// Phase 28 D: when the tour transitions to dismissed AND the user is
// still in Basic mode AND the one-shot localStorage flag has not
// been set, surface a single follow-up prompt offering "Switch to
// Advanced". Click either button sets the flag so the prompt
// never re-surfaces.
//
// Anti-gaming guard D:-1 (additive promotion):
//   * Flag is independent of the tour's dismissed key — the prompt is
//     additive UX, not part of the tour state machine.
//   * Flag is single-version (v1) — future revisions bump the key.
//
// All helpers below are pure (no I/O outside the explicit storage
// adapter); the React component imports them and supplies its own
// dispatcher.
// ────────────────────────────────────────────────────────────────────

/** Stable localStorage key for the "have we already nudged this user
 * to Advanced mode" flag. v1 — bumped only when the prompt copy/UX
 * changes materially. */
export const ADVANCED_PROMPT_LS_KEY = 'fm04a.tour.advanced-prompt.v1.shown';

export interface AdvancedPromptStorage {
  load: () => boolean;
  save: (shown: boolean) => void;
}

/** Default localStorage-backed storage for the advanced-mode prompt
 * one-shot flag. Falls back to no-op when localStorage is unavailable
 * (SSR / test envs without jsdom). Caller can inject a stub. */
export function createAdvancedPromptStorage(
  globalRef: typeof globalThis = globalThis,
): AdvancedPromptStorage {
  const ls = (globalRef as { localStorage?: Storage }).localStorage;
  if (!ls) {
    return {
      load: () => false,
      save: () => {
        /* no-op */
      },
    };
  }
  return {
    load: () => {
      try {
        return ls.getItem(ADVANCED_PROMPT_LS_KEY) === 'true';
      } catch {
        return false;
      }
    },
    save: (shown) => {
      try {
        ls.setItem(ADVANCED_PROMPT_LS_KEY, shown ? 'true' : 'false');
      } catch {
        /* swallow quota / SecurityError */
      }
    },
  };
}

/**
 * Pure predicate: should the Advanced-mode promo be visible?
 *
 *   - True iff ALL of:
 *       (a) tour has been dismissed (persisted in storage), AND
 *       (b) the user is in Basic mode, AND
 *       (c) the one-shot prompt-shown flag has NOT been set yet.
 *
 * D:-1 — independent of in-session state; only the three persisted
 * inputs matter. The caller is responsible for resolving them.
 */
export function shouldShowAdvancedPrompt(
  uiMode: 'basic' | 'advanced',
  tourDismissedInStorage: boolean,
  promptAlreadyShown: boolean,
): boolean {
  if (!tourDismissedInStorage) return false;
  if (uiMode !== 'basic') return false;
  if (promptAlreadyShown) return false;
  return true;
}

/** Resolve the currently-active step (or null when dismissed / past-end). */
export function currentStep(state: OnboardingState): OnboardingStep | null {
  if (state.dismissed) return null;
  if (state.currentStepIndex < 0) return null;
  if (state.currentStepIndex >= ONBOARDING_TOTAL_STEPS) return null;
  return ONBOARDING_STEPS[state.currentStepIndex];
}

/** Progress label like "2 / 4" for the dot row. */
export function progressLabel(state: OnboardingState): string {
  const displayed =
    state.currentStepIndex >= ONBOARDING_TOTAL_STEPS
      ? ONBOARDING_TOTAL_STEPS
      : state.currentStepIndex + 1;
  return `${displayed} / ${ONBOARDING_TOTAL_STEPS}`;
}
