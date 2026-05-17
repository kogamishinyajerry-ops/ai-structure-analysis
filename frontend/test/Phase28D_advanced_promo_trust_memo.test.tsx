// FM-04a Phase 28 D — Advanced-mode auto-promote prompt + trust-strip
// memoization tests.
//
// Two deliveries pinned in one test file:
//
// 1. Advanced-mode auto-promote prompt
//    - onboardingTour.ts gains ADVANCED_PROMPT_LS_KEY +
//      createAdvancedPromptStorage + shouldShowAdvancedPrompt
//      predicate (pure).
//    - AdvancedModePromo component renders ONLY when:
//        (a) tour persisted as dismissed, AND
//        (b) uiMode === 'basic', AND
//        (c) prompt-shown flag has NOT been set yet.
//    - Anti-gaming guard D:-1: prompt is one-shot — clicking either
//      button writes the flag, then the promo never re-renders for
//      the same browser even on full re-mount.
//
// 2. Trust-strip memoization (App.tsx)
//    - Each section builder call in App.tsx is wrapped in useMemo
//      with an explicit dep list. Pinned by structural source-scan
//      because the App-level integration test would require a
//      full-tree render plus mocked solver/manifest data.
//    - Purity (D:-3 no mutation) of buildOverviewSection +
//      buildRuntimeSection reaffirmed inline — same context returns
//      a deep-equal section across two calls.
//
// Tier 1 / Tier 2 engineering candidate; not signed validation;
// not benchmark agreement.

import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen } from '@testing-library/react'

import {
  ADVANCED_PROMPT_LS_KEY,
  ONBOARDING_LS_KEY,
  createAdvancedPromptStorage,
  shouldShowAdvancedPrompt,
} from '../src/onboardingTour'
import { AdvancedModePromo } from '../src/components/AdvancedModePromo'
import {
  buildOverviewSection,
  buildRuntimeSection,
  buildBlueprintTargetSection,
  buildGateSection,
} from '../src/state/trustCenterViewModel'

// ────────────────────────────────────────────────────────────────────
// 1. onboardingTour: storage helper + predicate
// ────────────────────────────────────────────────────────────────────

describe('Phase 28 D — ADVANCED_PROMPT_LS_KEY + storage round-trip', () => {
  beforeEach(() => window.localStorage.removeItem(ADVANCED_PROMPT_LS_KEY))
  afterEach(() => window.localStorage.removeItem(ADVANCED_PROMPT_LS_KEY))

  it('exports a versioned key (v1) distinct from the tour-dismissed key', () => {
    expect(ADVANCED_PROMPT_LS_KEY).toBe('fm04a.tour.advanced-prompt.v1.shown')
    expect(ADVANCED_PROMPT_LS_KEY).not.toBe(ONBOARDING_LS_KEY)
  })

  it('load returns false when key is absent', () => {
    const store = createAdvancedPromptStorage()
    expect(store.load()).toBe(false)
  })

  it('save(true) → load round-trip returns true', () => {
    const store = createAdvancedPromptStorage()
    store.save(true)
    expect(store.load()).toBe(true)
    expect(window.localStorage.getItem(ADVANCED_PROMPT_LS_KEY)).toBe('true')
  })

  it('save(false) writes the literal string "false" (no key delete)', () => {
    const store = createAdvancedPromptStorage()
    store.save(false)
    expect(window.localStorage.getItem(ADVANCED_PROMPT_LS_KEY)).toBe('false')
    expect(store.load()).toBe(false)
  })

  it('SSR fallback: no localStorage → load returns false; save is no-op', () => {
    const fakeGlobal = {} as typeof globalThis
    const store = createAdvancedPromptStorage(fakeGlobal)
    expect(store.load()).toBe(false)
    expect(() => store.save(true)).not.toThrow()
  })
})

describe('Phase 28 D — shouldShowAdvancedPrompt predicate truth table', () => {
  it('false when tour NOT dismissed', () => {
    expect(shouldShowAdvancedPrompt('basic', false, false)).toBe(false)
  })

  it('false when uiMode is advanced (no need to promo)', () => {
    expect(shouldShowAdvancedPrompt('advanced', true, false)).toBe(false)
  })

  it('false when prompt already shown', () => {
    expect(shouldShowAdvancedPrompt('basic', true, true)).toBe(false)
  })

  it('true ONLY when tour dismissed + basic mode + prompt-not-shown', () => {
    expect(shouldShowAdvancedPrompt('basic', true, false)).toBe(true)
  })

  it('D:-1 — flipping prompt-shown to true short-circuits regardless of other inputs', () => {
    expect(shouldShowAdvancedPrompt('basic', true, true)).toBe(false)
    expect(shouldShowAdvancedPrompt('advanced', true, true)).toBe(false)
    expect(shouldShowAdvancedPrompt('basic', false, true)).toBe(false)
  })
})

// ────────────────────────────────────────────────────────────────────
// 2. AdvancedModePromo component
// ────────────────────────────────────────────────────────────────────

describe('Phase 28 D — AdvancedModePromo render gating', () => {
  beforeEach(() => {
    window.localStorage.removeItem(ADVANCED_PROMPT_LS_KEY)
    window.localStorage.removeItem(ONBOARDING_LS_KEY)
  })
  afterEach(() => {
    window.localStorage.removeItem(ADVANCED_PROMPT_LS_KEY)
    window.localStorage.removeItem(ONBOARDING_LS_KEY)
  })

  it('hidden by default (tour not dismissed)', () => {
    render(
      <AdvancedModePromo uiMode="basic" onSwitchToAdvanced={() => {}} />,
    )
    expect(screen.queryByTestId('advanced-mode-promo')).toBeNull()
  })

  it('visible when tour dismissed + basic mode + flag absent', () => {
    window.localStorage.setItem(ONBOARDING_LS_KEY, 'true')
    render(
      <AdvancedModePromo uiMode="basic" onSwitchToAdvanced={() => {}} />,
    )
    expect(screen.getByTestId('advanced-mode-promo')).toBeTruthy()
    expect(screen.getByTestId('advanced-mode-promo-switch')).toBeTruthy()
    expect(screen.getByTestId('advanced-mode-promo-stay')).toBeTruthy()
  })

  it('hidden when uiMode is already advanced', () => {
    window.localStorage.setItem(ONBOARDING_LS_KEY, 'true')
    render(
      <AdvancedModePromo uiMode="advanced" onSwitchToAdvanced={() => {}} />,
    )
    expect(screen.queryByTestId('advanced-mode-promo')).toBeNull()
  })

  it('hidden when prompt-shown flag is already true', () => {
    window.localStorage.setItem(ONBOARDING_LS_KEY, 'true')
    window.localStorage.setItem(ADVANCED_PROMPT_LS_KEY, 'true')
    render(
      <AdvancedModePromo uiMode="basic" onSwitchToAdvanced={() => {}} />,
    )
    expect(screen.queryByTestId('advanced-mode-promo')).toBeNull()
  })

  it('forceShow=true surfaces the promo even when LS keys say otherwise', () => {
    render(
      <AdvancedModePromo
        uiMode="basic"
        onSwitchToAdvanced={() => {}}
        forceShow
      />,
    )
    expect(screen.getByTestId('advanced-mode-promo')).toBeTruthy()
  })

  it('a11y: role=dialog + aria-live=polite + aria-label set', () => {
    window.localStorage.setItem(ONBOARDING_LS_KEY, 'true')
    render(
      <AdvancedModePromo uiMode="basic" onSwitchToAdvanced={() => {}} />,
    )
    const promo = screen.getByTestId('advanced-mode-promo')
    expect(promo.getAttribute('role')).toBe('dialog')
    expect(promo.getAttribute('aria-live')).toBe('polite')
    expect(promo.getAttribute('aria-label')).toBe('advanced mode promo')
  })
})

describe('Phase 28 D — AdvancedModePromo click handlers', () => {
  beforeEach(() => {
    window.localStorage.setItem(ONBOARDING_LS_KEY, 'true')
    window.localStorage.removeItem(ADVANCED_PROMPT_LS_KEY)
  })
  afterEach(() => {
    window.localStorage.removeItem(ADVANCED_PROMPT_LS_KEY)
    window.localStorage.removeItem(ONBOARDING_LS_KEY)
  })

  it('Switch button calls onSwitchToAdvanced and writes the flag', () => {
    const onSwitch = vi.fn()
    render(<AdvancedModePromo uiMode="basic" onSwitchToAdvanced={onSwitch} />)
    fireEvent.click(screen.getByTestId('advanced-mode-promo-switch'))
    expect(onSwitch).toHaveBeenCalledTimes(1)
    expect(window.localStorage.getItem(ADVANCED_PROMPT_LS_KEY)).toBe('true')
    // Promo hides after the click.
    expect(screen.queryByTestId('advanced-mode-promo')).toBeNull()
  })

  it('Stay button writes the flag but does NOT call onSwitchToAdvanced', () => {
    const onSwitch = vi.fn()
    render(<AdvancedModePromo uiMode="basic" onSwitchToAdvanced={onSwitch} />)
    fireEvent.click(screen.getByTestId('advanced-mode-promo-stay'))
    expect(onSwitch).not.toHaveBeenCalled()
    expect(window.localStorage.getItem(ADVANCED_PROMPT_LS_KEY)).toBe('true')
    expect(screen.queryByTestId('advanced-mode-promo')).toBeNull()
  })

  it('D:-1 — after Stay click, re-mounting does NOT re-surface the promo', () => {
    const onSwitch = vi.fn()
    const { unmount } = render(
      <AdvancedModePromo uiMode="basic" onSwitchToAdvanced={onSwitch} />,
    )
    fireEvent.click(screen.getByTestId('advanced-mode-promo-stay'))
    unmount()
    // Fresh mount — should read the flag from storage and stay hidden.
    render(<AdvancedModePromo uiMode="basic" onSwitchToAdvanced={onSwitch} />)
    expect(screen.queryByTestId('advanced-mode-promo')).toBeNull()
  })

  it('D:-1 — after Switch click, re-mounting does NOT re-surface the promo', () => {
    const onSwitch = vi.fn()
    const { unmount } = render(
      <AdvancedModePromo uiMode="basic" onSwitchToAdvanced={onSwitch} />,
    )
    fireEvent.click(screen.getByTestId('advanced-mode-promo-switch'))
    unmount()
    render(<AdvancedModePromo uiMode="basic" onSwitchToAdvanced={onSwitch} />)
    expect(screen.queryByTestId('advanced-mode-promo')).toBeNull()
  })

  it('in-session: setting tourDismissedInSession after mount surfaces the promo', () => {
    // Pre-condition: tour NOT yet persisted as dismissed; promo
    // initially hidden.
    window.localStorage.removeItem(ONBOARDING_LS_KEY)
    const { rerender } = render(
      <AdvancedModePromo
        uiMode="basic"
        onSwitchToAdvanced={() => {}}
        tourDismissedInSession={false}
      />,
    )
    expect(screen.queryByTestId('advanced-mode-promo')).toBeNull()
    // Now: simulate the tour writing its dismissed flag + firing the
    // in-session signal. The promo should re-read storage and show.
    window.localStorage.setItem(ONBOARDING_LS_KEY, 'true')
    rerender(
      <AdvancedModePromo
        uiMode="basic"
        onSwitchToAdvanced={() => {}}
        tourDismissedInSession
      />,
    )
    expect(screen.getByTestId('advanced-mode-promo')).toBeTruthy()
  })
})

// ────────────────────────────────────────────────────────────────────
// 3. Trust-strip memoization (structural App.tsx scan)
// ────────────────────────────────────────────────────────────────────

// FM-04a Phase 29 B — these structural App.tsx pins were valid for
// Phase 28 D's inline useMemo block. Phase 29 B moved the entire
// build into `useTrustSections` (frontend/src/state/useTrustSections.ts),
// so the pins now target THAT file instead. Memoization semantics
// are unchanged (granular per-section); only the home is different.

describe('Phase 28 D — trust builder memoization (post Phase 29 B → hook)', () => {
  const hookSource = readFileSync(
    resolve(__dirname, '../src/state/useTrustSections.ts'),
    'utf-8',
  )
  const appSource = readFileSync(
    resolve(__dirname, '../src/App.tsx'),
    'utf-8',
  )

  it('useTrustSections hook imports useMemo from react', () => {
    expect(hookSource).toMatch(
      /import\s*\{[^}]*\buseMemo\b[^}]*\}\s*from\s*['"]react['"]/,
    )
  })

  it.each([
    'buildTrustStrip',
    'buildOverviewSection',
    'buildRuntimeSection',
    'buildEvidenceSection',
    'buildValidationSection',
    'buildBlueprintTargetSection',
    'buildBallisticSection',
    'buildGateSection',
  ])('%s call site is wrapped in useMemo inside the hook', (builder) => {
    const pattern = new RegExp(
      `useMemo\\s*\\(\\s*\\(\\s*\\)\\s*=>[\\s\\S]{0,200}?${builder}\\s*\\(`,
    )
    expect(hookSource).toMatch(pattern)
  })

  it('sections array is itself memoized inside the hook', () => {
    expect(hookSource).toMatch(
      /const\s+sections\s*=\s*useMemo\s*\(/,
    )
  })

  it('App.tsx consumes the hook (single useTrustSections call)', () => {
    expect(appSource).toMatch(
      /\buseTrustSections\s*\(\s*\{/,
    )
  })
})

describe('Phase 28 D — section builders remain pure (D:-3 reaffirmation)', () => {
  it('buildOverviewSection: same ctx → deep-equal output across two calls', () => {
    const ctx = {
      icon: 'icon-x',
      candidateSpine: null,
      activeCaseId: 'case-x',
      file: null,
      caseLabel: 'X',
      nextAction: 'do thing',
    }
    const a = buildOverviewSection(ctx)
    const b = buildOverviewSection(ctx)
    expect(a).toEqual(b)
    // And the ctx itself is untouched.
    expect(ctx.candidateSpine).toBeNull()
    expect(ctx.activeCaseId).toBe('case-x')
  })

  it('buildBlueprintTargetSection: same ctx → deep-equal output', () => {
    const ctx = {
      icon: 'icon-bp',
      blueprintSummary: {
        label: 'BP-x',
        claimTier: 'tier1_candidate',
        imagePath: '/i.png',
        evidenceCaseId: 'evc',
        coveredAnchorCount: 4,
        anchorCount: 4,
        availableEvidenceCount: 1,
        evidenceCount: 1,
        allowedClaim: 'tier1_candidate',
      } as Parameters<typeof buildBlueprintTargetSection>[0]['blueprintSummary'],
    }
    const a = buildBlueprintTargetSection(ctx)
    const b = buildBlueprintTargetSection(ctx)
    expect(a).toEqual(b)
  })

  it('buildGateSection: same ctx → deep-equal output, ctx unmutated', () => {
    const ctx = {
      icon: 'icon-g',
      reviewerSummary: '0 reviewers',
      candidateReviewer: null,
      allowedClaim: 'tier1_candidate',
      candidateLimitations: ['documented limitation 1', 'documented limitation 2'],
      tier2BlockerSummary: '5 blockers',
    }
    const before = JSON.parse(JSON.stringify({ ...ctx, icon: 'icon-g' }))
    const a = buildGateSection(ctx)
    const b = buildGateSection(ctx)
    expect(a).toEqual(b)
    expect({ ...ctx, icon: 'icon-g' }).toEqual(before)
  })

  it('buildRuntimeSection: same ctx → deep-equal output (memo-readiness)', () => {
    const ctx = {
      icon: 'icon-r',
      solverTruthSource: 'foam-agent' as const,
      candidateSpine: null,
      currentJobId: null,
      executionMode: 'tier1' as const,
      report: null,
      analysisModeLabel: 'Mode X',
      currentJobLabel: 'job-x',
      lastSolverMaterialReference: null,
      runState: 'idle',
      runStateTone: 'muted' as const,
      latestEvent: null,
      solverLogSummary: 'no log',
      solverLogState: null,
      convergenceSummary: 'no conv',
      candidateConvergenceEvidence: null,
      convergenceClaimImpact: null,
    } as Parameters<typeof buildRuntimeSection>[0]
    const a = buildRuntimeSection(ctx)
    const b = buildRuntimeSection(ctx)
    expect(a).toEqual(b)
  })
})
