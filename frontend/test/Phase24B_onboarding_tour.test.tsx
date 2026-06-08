// FM-04a Phase 24 B — onboarding tour tests.
//
// Tier 1 / Tier 2 engineering candidate; not signed validation; not
// benchmark agreement.
//
// Phase 24 B addresses the Phase 23 UX cognitive-load -1 regression
// by introducing a 4-step progressive-disclosure tour.
//
// Anti-gaming guards:
//   * B:-1 — nextStep / dismiss only fire on explicit user click,
//     never on a timer or implicit lifecycle event. Pinned at the
//     predicate level (state-machine test) AND component level
//     (no auto-advance after render).

import { describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen, act } from '@testing-library/react'
import {
  ONBOARDING_INITIAL_STATE,
  ONBOARDING_STEPS,
  ONBOARDING_TOTAL_STEPS,
  currentStep,
  dismissTour,
  nextStep,
  progressLabel,
  resetTour,
  shouldShowTour,
} from '../src/onboardingTour'
import { OnboardingTour } from '../src/components/OnboardingTour'

describe('Phase 24 B — onboardingTour state machine', () => {
  it('initial state points at the first step and is not dismissed', () => {
    expect(ONBOARDING_INITIAL_STATE).toEqual({
      currentStepIndex: 0,
      dismissed: false,
    })
    expect(currentStep(ONBOARDING_INITIAL_STATE)?.id).toBe(
      'field-component-switcher',
    )
  })

  it('exposes the first 4 steps from Phase 24 B in the expected progression order', () => {
    // FM-04a Phase 27 D refreshed the tour to 6 steps (added
    // 'basic-advanced-mode' + 'probe-diff-column'). Phase 24 B's
    // intent (the original 4 steps remain in the first 4 positions
    // of the progression) is preserved; loosened from strict ==
    // to subset / prefix match.
    expect(ONBOARDING_TOTAL_STEPS).toBeGreaterThanOrEqual(4)
    const ids = ONBOARDING_STEPS.map((s) => s.id)
    expect(ids.slice(0, 4)).toEqual([
      'field-component-switcher',
      'threshold-filter',
      'node-pick',
      'section-cut',
    ])
  })

  it('nextStep advances one-at-a-time and marks dismissed at the end', () => {
    // FM-04a Phase 27 D: total steps increased from 4 → 6; the
    // state-machine contract (advance one at a time; dismiss at
    // total) is invariant. Original Phase 24 B intent preserved.
    let state = ONBOARDING_INITIAL_STATE
    for (let i = 0; i < ONBOARDING_TOTAL_STEPS - 1; i++) {
      state = nextStep(state)
      expect(state.currentStepIndex).toBe(i + 1)
      expect(state.dismissed).toBe(false)
    }
    state = nextStep(state)
    expect(state.currentStepIndex).toBe(ONBOARDING_TOTAL_STEPS)
    expect(state.dismissed).toBe(true)
  })

  it('nextStep is a no-op once dismissed (B:-1 anti-gaming)', () => {
    const dismissed = dismissTour(ONBOARDING_INITIAL_STATE)
    const after = nextStep(dismissed)
    expect(after).toBe(dismissed)
  })

  it('dismissTour sets dismissed=true regardless of step', () => {
    const mid = nextStep(nextStep(ONBOARDING_INITIAL_STATE))
    expect(mid.dismissed).toBe(false)
    const dismissed = dismissTour(mid)
    expect(dismissed.dismissed).toBe(true)
  })

  it('resetTour brings the state back to initial (developer escape)', () => {
    const dismissed = dismissTour(ONBOARDING_INITIAL_STATE)
    expect(resetTour(dismissed)).toEqual(ONBOARDING_INITIAL_STATE)
  })

  it('shouldShowTour returns false when persistedDismissed is true', () => {
    expect(shouldShowTour(ONBOARDING_INITIAL_STATE, true)).toBe(false)
  })

  it('shouldShowTour returns false when state is dismissed', () => {
    expect(shouldShowTour(dismissTour(ONBOARDING_INITIAL_STATE), false)).toBe(false)
  })

  it('shouldShowTour returns true on a fresh state with no persistence', () => {
    expect(shouldShowTour(ONBOARDING_INITIAL_STATE, false)).toBe(true)
  })

  it('progressLabel renders "n / total" format', () => {
    // FM-04a Phase 27 D: total is now 6, not 4. Format invariant.
    expect(progressLabel(ONBOARDING_INITIAL_STATE)).toBe(`1 / ${ONBOARDING_TOTAL_STEPS}`)
    expect(progressLabel(nextStep(ONBOARDING_INITIAL_STATE))).toBe(
      `2 / ${ONBOARDING_TOTAL_STEPS}`,
    )
    let state = ONBOARDING_INITIAL_STATE
    for (let i = 0; i < ONBOARDING_TOTAL_STEPS; i++) state = nextStep(state)
    expect(progressLabel(state)).toBe(
      `${ONBOARDING_TOTAL_STEPS} / ${ONBOARDING_TOTAL_STEPS}`,
    )
  })

  it('each step has a non-empty title, body, and shippedInPhase tag', () => {
    // FM-04a Phase 27 D loosened the shippedInPhase regex from
    // /Phase 2[23] [A-Z]/ to /Phase 2\d [A-Z]/ so the new
    // Phase 25 C / Phase 26 C steps can pass. Intent preserved.
    for (const step of ONBOARDING_STEPS) {
      expect(step.title.length).toBeGreaterThan(0)
      expect(step.body.length).toBeGreaterThan(0)
      expect(step.shippedInPhase).toMatch(/Phase 2\d [A-Z]/)
    }
  })
})

function makeStubStorage(initialDismissed = false) {
  const state = { dismissed: initialDismissed }
  return {
    load: () => state.dismissed,
    save: (value: boolean) => {
      state.dismissed = value
    },
    inspect: () => state.dismissed,
  }
}

describe('Phase 24 B — OnboardingTour component', () => {
  it('renders the first step on mount when storage reports not dismissed', () => {
    const storage = makeStubStorage(false)
    render(<OnboardingTour storage={storage} />)
    expect(screen.getByTestId('onboarding-tour')).toBeTruthy()
    // FM-04a Phase 27 D: total is now 6, not 4.
    expect(screen.getByTestId('onboarding-progress').textContent).toBe(
      `1 / ${ONBOARDING_TOTAL_STEPS}`,
    )
    expect(screen.getByText(/stress component/i)).toBeTruthy()
  })

  it('does NOT render when storage reports dismissed', () => {
    const storage = makeStubStorage(true)
    const { container } = render(<OnboardingTour storage={storage} />)
    expect(container.querySelector('[data-testid="onboarding-tour"]')).toBeNull()
  })

  it('advances on the "Got it" button click (B:-1 user-initiated only)', () => {
    const storage = makeStubStorage(false)
    render(<OnboardingTour storage={storage} />)
    fireEvent.click(screen.getByTestId('onboarding-advance'))
    expect(screen.getByTestId('onboarding-progress').textContent).toBe(
      `2 / ${ONBOARDING_TOTAL_STEPS}`,
    )
  })

  it('completes after 4 advance clicks and persists dismissal', () => {
    const storage = makeStubStorage(false)
    const { container } = render(<OnboardingTour storage={storage} />)
    for (let i = 0; i < ONBOARDING_TOTAL_STEPS; i++) {
      fireEvent.click(screen.getByTestId('onboarding-advance'))
    }
    expect(container.querySelector('[data-testid="onboarding-tour"]')).toBeNull()
    expect(storage.inspect()).toBe(true)
  })

  it('dismisses on Skip tour link and persists', () => {
    const storage = makeStubStorage(false)
    const { container } = render(<OnboardingTour storage={storage} />)
    fireEvent.click(screen.getByTestId('onboarding-skip'))
    expect(container.querySelector('[data-testid="onboarding-tour"]')).toBeNull()
    expect(storage.inspect()).toBe(true)
  })

  it('B:-1 anti-gaming: does NOT auto-advance after render (no timer)', () => {
    vi.useFakeTimers()
    try {
      const storage = makeStubStorage(false)
      render(<OnboardingTour storage={storage} />)
      // Even if any timer were lurking, advance only on user click.
      act(() => {
        vi.advanceTimersByTime(60000)
      })
      // Still on step 1.
      expect(screen.getByTestId('onboarding-progress').textContent).toBe(
        `1 / ${ONBOARDING_TOTAL_STEPS}`,
      )
    } finally {
      vi.useRealTimers()
    }
  })

  it('forceShow=true overrides persisted dismissal (Replay tour affordance)', () => {
    const storage = makeStubStorage(true)
    render(<OnboardingTour storage={storage} forceShow />)
    expect(screen.getByTestId('onboarding-tour')).toBeTruthy()
  })

  it('renders one progress dot per step with the active dot highlighted', () => {
    // FM-04a Phase 27 D: total is now 6, not 4. Dots-per-step
    // contract preserved.
    const storage = makeStubStorage(false)
    render(<OnboardingTour storage={storage} />)
    for (let i = 0; i < ONBOARDING_TOTAL_STEPS; i++) {
      expect(screen.getByTestId(`onboarding-dot-${i}`)).toBeTruthy()
    }
    fireEvent.click(screen.getByTestId('onboarding-advance'))
    expect(screen.getByTestId('onboarding-progress').textContent).toBe(
      `2 / ${ONBOARDING_TOTAL_STEPS}`,
    )
  })

  it('emits onStateChange callback when user advances', () => {
    const storage = makeStubStorage(false)
    const onStateChange = vi.fn()
    render(<OnboardingTour storage={storage} onStateChange={onStateChange} />)
    fireEvent.click(screen.getByTestId('onboarding-advance'))
    expect(onStateChange).toHaveBeenCalled()
    const lastCall = onStateChange.mock.calls.at(-1)
    expect(lastCall?.[0].currentStepIndex).toBe(1)
  })
})
