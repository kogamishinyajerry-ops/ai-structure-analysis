// FM-04a Phase 28 D — Advanced-mode auto-promote prompt.
//
// Surfaces ONCE after the onboarding tour ends, when the user is
// still in Basic mode. Offers a single click to switch to Advanced
// (which exposes the threshold filter / section cut / field
// switcher / probe list panel the tour just covered).
//
// Visibility predicate (delegated to onboardingTour.shouldShowAdvancedPrompt):
//   * Tour persisted as dismissed in localStorage (ONBOARDING_LS_KEY = 'true'), AND
//   * Current uiMode === 'basic', AND
//   * ADVANCED_PROMPT_LS_KEY not yet 'true'.
//
// Either button (Switch / Stay) writes the prompt-shown flag and
// hides the promo. The promo is one-shot per browser; bumping the
// localStorage key bumps the version.
//
// Anti-gaming guard D:-1 — once the prompt-shown flag is written,
// the promo never re-surfaces for the same browser, even on full
// page reload + re-mount. Pinned by the storage round-trip test.
//
// Tier 1 / Tier 2 engineering candidate; not signed validation;
// not benchmark agreement.

import { useCallback, useEffect, useMemo, useState, type CSSProperties } from 'react';

import {
  ONBOARDING_LS_KEY,
  createAdvancedPromptStorage,
  createLocalStorageBackedStore,
  shouldShowAdvancedPrompt,
  type AdvancedPromptStorage,
  type OnboardingStorage,
} from '../onboardingTour';
import type { UiMode } from '../uiMode';

export interface AdvancedModePromoProps {
  /** Current UI mode. The promo only shows when this is 'basic'. */
  uiMode: UiMode;
  /** Called when the user clicks "Switch to Advanced". The parent is
   * responsible for actually flipping the mode (so this component
   * stays pure UI). */
  onSwitchToAdvanced: () => void;
  /** Optional injected storage for the prompt-shown flag. Defaults to
   * the localStorage adapter; tests pass a stub. */
  promptStorage?: AdvancedPromptStorage;
  /** Optional injected storage for the onboarding-dismissed flag.
   * Defaults to the localStorage adapter; tests pass a stub. */
  tourStorage?: OnboardingStorage;
  /** When true, surface the promo regardless of the persisted flag.
   * Useful for replaying via a settings affordance (not wired yet). */
  forceShow?: boolean;
  /** When provided, in-session signal that the tour just dismissed.
   * Triggers a re-read of the tour-dismissed flag so the promo
   * surfaces without a page reload. */
  tourDismissedInSession?: boolean;
}

export function AdvancedModePromo({
  uiMode,
  onSwitchToAdvanced,
  promptStorage,
  tourStorage,
  forceShow = false,
  tourDismissedInSession = false,
}: AdvancedModePromoProps) {
  const resolvedPromptStorage = useMemo<AdvancedPromptStorage>(
    () => promptStorage ?? createAdvancedPromptStorage(),
    [promptStorage],
  );
  const resolvedTourStorage = useMemo<OnboardingStorage>(
    () => tourStorage ?? createLocalStorageBackedStore(),
    [tourStorage],
  );

  // Persisted state, re-read on tour-dismiss signal.
  const [tourDismissed, setTourDismissed] = useState<boolean>(() =>
    forceShow ? true : resolvedTourStorage.load(),
  );
  const [promptShown, setPromptShown] = useState<boolean>(() =>
    forceShow ? false : resolvedPromptStorage.load(),
  );

  // FM-04a Phase 28 D — when the tour fires its in-session dismissed
  // signal, refresh both flags so the promo can surface in the same
  // session (no page reload required).
  useEffect(() => {
    if (!tourDismissedInSession) return;
    setTourDismissed(resolvedTourStorage.load());
    setPromptShown(resolvedPromptStorage.load());
  }, [tourDismissedInSession, resolvedTourStorage, resolvedPromptStorage]);

  const visible = shouldShowAdvancedPrompt(uiMode, tourDismissed, promptShown);

  const markShownAndHide = useCallback(() => {
    resolvedPromptStorage.save(true);
    setPromptShown(true);
  }, [resolvedPromptStorage]);

  const handleSwitch = useCallback(() => {
    markShownAndHide();
    onSwitchToAdvanced();
  }, [markShownAndHide, onSwitchToAdvanced]);

  const handleStay = useCallback(() => {
    markShownAndHide();
  }, [markShownAndHide]);

  if (!visible) return null;

  return (
    <div
      data-testid="advanced-mode-promo"
      role="dialog"
      aria-label="advanced mode promo"
      aria-live="polite"
      style={STYLES.backdrop}
    >
      <div style={STYLES.card}>
        <div style={STYLES.header}>
          <span style={STYLES.eyebrow}>Phase 25 C · Phase 28 D</span>
        </div>
        <h2 style={STYLES.title}>Want to see the advanced controls?</h2>
        <p style={STYLES.body}>
          You're currently in <strong>Basic</strong> mode. The tour
          covered the threshold filter, section cut, field-component
          switcher, and probe list — those live in{' '}
          <strong>Advanced</strong>. You can toggle back any time from
          the viewport header.
        </p>
        <div style={STYLES.actions}>
          <button
            type="button"
            data-testid="advanced-mode-promo-stay"
            onClick={handleStay}
            style={STYLES.stayButton}
          >
            Stay in Basic
          </button>
          <button
            type="button"
            data-testid="advanced-mode-promo-switch"
            onClick={handleSwitch}
            style={STYLES.switchButton}
          >
            Switch to Advanced
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
    background: 'rgba(15, 23, 42, 0.4)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    zIndex: 999, // one below the tour
  },
  card: {
    background: 'white',
    borderRadius: 12,
    padding: '22px 26px',
    maxWidth: 440,
    width: '90%',
    boxShadow: '0 18px 36px rgba(15, 23, 42, 0.16)',
    fontFamily: 'system-ui, -apple-system, sans-serif',
  },
  header: {
    marginBottom: 6,
  },
  eyebrow: {
    color: '#475569',
    fontSize: 11,
    letterSpacing: 0.5,
    textTransform: 'uppercase',
    fontWeight: 600,
  },
  title: {
    fontSize: 17,
    fontWeight: 700,
    color: '#0f172a',
    margin: '0 0 10px',
  },
  body: {
    fontSize: 13.5,
    lineHeight: 1.5,
    color: '#334155',
    margin: '0 0 16px',
  },
  actions: {
    display: 'flex',
    gap: 10,
    justifyContent: 'flex-end',
    alignItems: 'center',
  },
  stayButton: {
    background: 'transparent',
    border: '1px solid #cbd5e1',
    color: '#475569',
    borderRadius: 6,
    padding: '7px 14px',
    fontWeight: 500,
    fontSize: 13,
    cursor: 'pointer',
  },
  switchButton: {
    background: '#2563eb',
    color: 'white',
    border: 'none',
    borderRadius: 6,
    padding: '7px 16px',
    fontWeight: 600,
    fontSize: 13,
    cursor: 'pointer',
  },
};
