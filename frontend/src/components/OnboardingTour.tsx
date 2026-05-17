// FM-04a Phase 24 B — onboarding tour overlay component.
//
// Reads the pure-function state machine in onboardingTour.ts; persists
// dismissal to localStorage on first user interaction so the tour
// surfaces exactly once.

import { useCallback, useEffect, useMemo, useState, type CSSProperties } from 'react';

import {
  ONBOARDING_INITIAL_STATE,
  ONBOARDING_TOTAL_STEPS,
  createLocalStorageBackedStore,
  currentStep,
  dismissTour,
  nextStep,
  progressLabel,
  shouldShowTour,
  type OnboardingState,
  type OnboardingStorage,
} from '../onboardingTour';

export interface OnboardingTourProps {
  /** Optional injected storage; defaults to the localStorage adapter.
   * Test code passes a stub. */
  storage?: OnboardingStorage;
  /** Forces the overlay open regardless of localStorage; useful for
   * a future "Replay tour" affordance in settings. */
  forceShow?: boolean;
  /** Called every time the user advances or dismisses; useful for
   * higher-level telemetry. */
  onStateChange?: (next: OnboardingState) => void;
}

export function OnboardingTour({
  storage,
  forceShow = false,
  onStateChange,
}: OnboardingTourProps) {
  const resolvedStorage = useMemo<OnboardingStorage>(
    () => storage ?? createLocalStorageBackedStore(),
    [storage],
  );
  const [persistedDismissed, setPersistedDismissed] = useState<boolean>(() =>
    forceShow ? false : resolvedStorage.load(),
  );
  const [state, setState] = useState<OnboardingState>(ONBOARDING_INITIAL_STATE);

  useEffect(() => {
    onStateChange?.(state);
  }, [state, onStateChange]);

  const handleAdvance = useCallback(() => {
    setState((prev) => {
      const next = nextStep(prev);
      if (next.dismissed && !prev.dismissed) {
        resolvedStorage.save(true);
        setPersistedDismissed(true);
      }
      return next;
    });
  }, [resolvedStorage]);

  const handleSkip = useCallback(() => {
    setState((prev) => {
      const next = dismissTour(prev);
      resolvedStorage.save(true);
      setPersistedDismissed(true);
      return next;
    });
  }, [resolvedStorage]);

  if (!shouldShowTour(state, persistedDismissed)) {
    return null;
  }
  const step = currentStep(state);
  if (step === null) return null;

  return (
    <div data-testid="onboarding-tour" role="dialog" aria-label="onboarding tour" style={STYLES.backdrop}>
      <div style={STYLES.card}>
        <div style={STYLES.header}>
          <span style={STYLES.shipped}>{step.shippedInPhase}</span>
          <span data-testid="onboarding-progress" style={STYLES.progress}>
            {progressLabel(state)}
          </span>
        </div>
        <h2 style={STYLES.title}>{step.title}</h2>
        <p style={STYLES.body}>{step.body}</p>
        <div style={STYLES.dotRow}>
          {Array.from({ length: ONBOARDING_TOTAL_STEPS }, (_, i) => (
            <span
              key={i}
              data-testid={`onboarding-dot-${i}`}
              style={{
                ...STYLES.dot,
                background:
                  i === state.currentStepIndex
                    ? '#2563eb'
                    : i < state.currentStepIndex
                      ? '#94a3b8'
                      : '#e2e8f0',
              }}
            />
          ))}
        </div>
        <div style={STYLES.actions}>
          <button
            type="button"
            data-testid="onboarding-skip"
            onClick={handleSkip}
            style={STYLES.skipButton}
          >
            Skip tour
          </button>
          <button
            type="button"
            data-testid="onboarding-advance"
            onClick={handleAdvance}
            style={STYLES.advanceButton}
          >
            {state.currentStepIndex + 1 >= ONBOARDING_TOTAL_STEPS ? 'Done' : 'Got it'}
          </button>
        </div>
      </div>
    </div>
  );
}

const STYLES: Record<string, CSSProperties> = {
  backdrop: {
    position: 'fixed',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    background: 'rgba(15, 23, 42, 0.55)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    zIndex: 1000,
  },
  card: {
    background: 'white',
    borderRadius: 12,
    padding: '24px 28px',
    maxWidth: 480,
    width: '90%',
    boxShadow: '0 24px 48px rgba(15, 23, 42, 0.18)',
    fontFamily: 'system-ui, -apple-system, sans-serif',
  },
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 8,
  },
  shipped: {
    color: '#475569',
    fontSize: 11,
    letterSpacing: 0.5,
    textTransform: 'uppercase',
    fontWeight: 600,
  },
  progress: {
    color: '#94a3b8',
    fontSize: 12,
    fontWeight: 500,
  },
  title: {
    fontSize: 18,
    fontWeight: 700,
    color: '#0f172a',
    margin: '0 0 8px',
  },
  body: {
    fontSize: 14,
    lineHeight: 1.5,
    color: '#334155',
    margin: 0,
  },
  dotRow: {
    display: 'flex',
    gap: 6,
    margin: '20px 0',
    justifyContent: 'center',
  },
  dot: {
    width: 8,
    height: 8,
    borderRadius: '50%',
    display: 'inline-block',
  },
  actions: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginTop: 12,
  },
  skipButton: {
    background: 'transparent',
    border: 'none',
    color: '#64748b',
    cursor: 'pointer',
    fontSize: 13,
    textDecoration: 'underline',
    padding: '4px 8px',
  },
  advanceButton: {
    background: '#2563eb',
    color: 'white',
    border: 'none',
    borderRadius: 6,
    padding: '8px 18px',
    fontWeight: 600,
    fontSize: 14,
    cursor: 'pointer',
  },
};
