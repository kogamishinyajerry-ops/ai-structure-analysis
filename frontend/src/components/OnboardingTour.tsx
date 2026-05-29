// FM-04a Phase 24 B — onboarding tour overlay component.
//
// Reads the pure-function state machine in onboardingTour.ts; persists
// dismissal to localStorage on first user interaction so the tour
// surfaces exactly once.

import { useCallback, useEffect, useMemo, useRef, useState, type CSSProperties } from 'react';

import { useFocusTrap } from './useFocusTrap';

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
  /** FM-04a Phase 41.4 — gates the *auto*-show. The demo boots straight
   * into the GS-102-candidate 3D hero; auto-popping the first-visit tour
   * over that centerpiece muddied the first paint. App passes
   * `autoShow={casesLoaded && !activeCaseId}` so the tour only auto-surfaces
   * on the genuine no-case landing, never over a boot/opened case.
   * `forceShow` (replay) still overrides this. Defaults to true so the
   * component's own tests + any unparented mount keep prior behavior. */
  autoShow?: boolean;
  /** Called every time the user advances or dismisses; useful for
   * higher-level telemetry. */
  onStateChange?: (next: OnboardingState) => void;
  /** FM-04a Phase 28 D — fired exactly once when the tour
   * transitions to dismissed (either Skip click or Done on the last
   * step). The parent uses this to surface the Advanced-mode
   * auto-promote prompt in the same session without a page reload. */
  onDismissed?: () => void;
}

export function OnboardingTour({
  storage,
  forceShow = false,
  autoShow = true,
  onStateChange,
  onDismissed,
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
        // FM-04a Phase 28 D — fire the one-shot dismissed signal so
        // the Advanced-mode promo can surface this session.
        onDismissed?.();
      }
      return next;
    });
  }, [resolvedStorage, onDismissed]);

  const handleSkip = useCallback(() => {
    setState((prev) => {
      if (prev.dismissed) return prev;
      const next = dismissTour(prev);
      resolvedStorage.save(true);
      setPersistedDismissed(true);
      // FM-04a Phase 28 D — same one-shot signal on the Skip path.
      onDismissed?.();
      return next;
    });
  }, [resolvedStorage, onDismissed]);

  const containerRef = useRef<HTMLDivElement>(null);
  // FM-04a Phase 41.4 — `autoShow` gates the first-visit auto-pop so it
  // never covers the boot 3D hero; `forceShow` (replay) still overrides.
  const visible = (autoShow || forceShow) && shouldShowTour(state, persistedDismissed);
  // FM-04a Phase 29 C — focus-trap (WCAG 2.4.3). Active only while
  // the overlay is visible.
  useFocusTrap({ containerRef, active: visible });

  if (!visible) {
    return null;
  }
  const step = currentStep(state);
  if (step === null) return null;

  // FM-04a Phase 25 D — fade + slide-in animation on first render.
  // Respects prefers-reduced-motion via CSS media query in the
  // injected <style> tag.
  return (
    <div ref={containerRef} data-testid="onboarding-tour" role="dialog" aria-label="onboarding tour" style={STYLES.backdrop}>
      <style>{ONBOARDING_TOUR_KEYFRAMES}</style>
      <div style={STYLES.card} className="onboarding-tour-card">
        <div style={STYLES.header}>
          {/* FM-04a Phase 41.2 — dev-phase provenance badge
              (step.shippedInPhase, e.g. "Phase 23 B") removed from the
              user-facing tour: it leaked the internal build cadence into
              the demo. The 1/N progress label carries the only
              user-meaningful position info. Closes Phase 39 audit #2. */}
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

/** FM-04a Phase 25 D — fade + slide-in keyframes. Respects
 * prefers-reduced-motion so motion-sensitive users see an instant
 * appearance instead. */
const ONBOARDING_TOUR_KEYFRAMES = `
@keyframes fm04a-onboarding-fade-slide-in {
  from { opacity: 0; transform: translateY(-12px); }
  to   { opacity: 1; transform: translateY(0); }
}
.onboarding-tour-card {
  animation: fm04a-onboarding-fade-slide-in 200ms ease-out;
}
@media (prefers-reduced-motion: reduce) {
  .onboarding-tour-card {
    animation: none;
  }
}
`;

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
    color: 'var(--text-muted)', /* Phase 38 C: was #64748b (3.74:1 FAIL); token now 4.5:1+ */
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
