// FM-04a Phase 24 B — onboarding tour state machine.
//
// Phase 23 R1 closed at UX 80.8/100 with a -1 cognitive-load
// regression because three new control surfaces (component switcher,
// threshold filter, node-pick HUD) shipped without onboarding. This
// module ships a 4-step progressive-disclosure tour and the persistence
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
  | 'section-cut';

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

/** Stable localStorage key. */
export const ONBOARDING_LS_KEY = 'fm04a.onboarding.v1.dismissed';

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
