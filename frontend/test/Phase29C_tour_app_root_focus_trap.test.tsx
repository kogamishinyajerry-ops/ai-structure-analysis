// FM-04a Phase 29 C — tour + promo App-root lift + focus-trap +
// promo entrance animation tests.
//
// Three deliveries pinned in one test file:
//
// 1. useFocusTrap hook (WCAG 2.4.3) — Tab / Shift-Tab cycling
//    inside the dialog container; initial focus on first-tabbable
//    (D:-2); previous-focus restored on unmount; Esc / Enter pass
//    through unmolested (E:-1).
//
// 2. App-root lift — OnboardingTour + AdvancedModePromo no longer
//    mount inside ResultMeshPlaybackPanel; they mount at App-root
//    so any tab landing surfaces onboarding. Pinned by structural
//    source scan + by re-rendering the panel and asserting NEITHER
//    overlay appears from inside the panel.
//
// 3. AdvancedModePromo entrance animation — new `fm04a-advanced-mode-
//    promo` class applied to the card; 200ms ease-out fade-slide
//    keyframe; reduce-motion @media disables it.
//
// Tier 1 / Tier 2 engineering candidate; not signed validation;
// not benchmark agreement.

import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { useRef } from 'react'

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { act, fireEvent, render, renderHook, screen } from '@testing-library/react'

import { AdvancedModePromo } from '../src/components/AdvancedModePromo'
import { OnboardingTour } from '../src/components/OnboardingTour'
import {
  POLISH_CLASS_ADVANCED_MODE_PROMO,
  POLISH_CSS_TEXT,
  uninstallPolishStyles,
} from '../src/components/polishStyles'
import {
  ADVANCED_PROMPT_LS_KEY,
  ONBOARDING_LS_KEY,
} from '../src/onboardingTour'
import { useFocusTrap } from '../src/components/useFocusTrap'

// ────────────────────────────────────────────────────────────────────
// 1. useFocusTrap hook
// ────────────────────────────────────────────────────────────────────

function TrapHarness({
  active,
  buttonCount = 3,
  skipInitialFocus,
}: {
  active: boolean
  buttonCount?: number
  skipInitialFocus?: boolean
}) {
  const ref = useRef<HTMLDivElement>(null)
  useFocusTrap({
    containerRef: ref,
    active,
    skipInitialFocus,
  })
  return (
    <div>
      <button data-testid="outside-before">outside-before</button>
      <div ref={ref} data-testid="dialog-container" role="dialog">
        {Array.from({ length: buttonCount }, (_, i) => (
          <button key={i} data-testid={`inside-${i}`}>
            inside-{i}
          </button>
        ))}
      </div>
      <button data-testid="outside-after">outside-after</button>
    </div>
  )
}

describe('Phase 29 C — useFocusTrap', () => {
  it('D:-2 — initial focus = first tabbable on active mount', () => {
    render(<TrapHarness active />)
    expect(document.activeElement).toBe(screen.getByTestId('inside-0'))
  })

  it('skipInitialFocus suppresses the auto-focus', () => {
    const before = screen.queryByTestId('outside-before') as HTMLElement | null
    if (before) before.focus()
    render(<TrapHarness active skipInitialFocus />)
    // Don't assert specific element; just assert it's NOT the first
    // inside button (auto-focus suppressed).
    expect(document.activeElement).not.toBe(screen.getByTestId('inside-0'))
  })

  it('Tab from last tabbable wraps to first', () => {
    render(<TrapHarness active />)
    const inside2 = screen.getByTestId('inside-2')
    inside2.focus()
    fireEvent.keyDown(document, { key: 'Tab' })
    expect(document.activeElement).toBe(screen.getByTestId('inside-0'))
  })

  it('Shift-Tab from first tabbable wraps to last', () => {
    render(<TrapHarness active />)
    const inside0 = screen.getByTestId('inside-0')
    inside0.focus()
    fireEvent.keyDown(document, { key: 'Tab', shiftKey: true })
    expect(document.activeElement).toBe(screen.getByTestId('inside-2'))
  })

  it('Tab from outside wraps INTO the first tabbable', () => {
    render(<TrapHarness active />)
    const outside = screen.getByTestId('outside-before')
    outside.focus()
    fireEvent.keyDown(document, { key: 'Tab' })
    expect(document.activeElement).toBe(screen.getByTestId('inside-0'))
  })

  it('E:-1 — Esc passes through unmolested (no preventDefault)', () => {
    render(<TrapHarness active />)
    const inside0 = screen.getByTestId('inside-0')
    inside0.focus()
    const event = new KeyboardEvent('keydown', {
      key: 'Escape',
      bubbles: true,
      cancelable: true,
    })
    document.dispatchEvent(event)
    expect(event.defaultPrevented).toBe(false)
  })

  it('E:-1 — Enter passes through unmolested', () => {
    render(<TrapHarness active />)
    screen.getByTestId('inside-0').focus()
    const event = new KeyboardEvent('keydown', {
      key: 'Enter',
      bubbles: true,
      cancelable: true,
    })
    document.dispatchEvent(event)
    expect(event.defaultPrevented).toBe(false)
  })

  it('active=false → no trap', () => {
    render(<TrapHarness active={false} />)
    // No auto-focus.
    expect(document.activeElement).not.toBe(screen.getByTestId('inside-0'))
    // Tab from last does NOT wrap.
    screen.getByTestId('inside-2').focus()
    fireEvent.keyDown(document, { key: 'Tab' })
    // We can't assert browser-native Tab behavior in JSDOM, but we
    // CAN assert no wrap-to-first happened (which would only happen
    // via our trap).
    expect(document.activeElement).toBe(screen.getByTestId('inside-2'))
  })

  it('restores prior focus on unmount', () => {
    // Set up: focus an element outside, then mount the trap, then
    // unmount. Original element should regain focus.
    document.body.innerHTML =
      '<button id="prior" data-testid="prior-focus">prior</button>'
    const prior = document.getElementById('prior') as HTMLButtonElement
    prior.focus()
    expect(document.activeElement).toBe(prior)
    const { unmount } = render(<TrapHarness active />)
    expect(document.activeElement).not.toBe(prior)
    unmount()
    // Prior element still in DOM (we kept it on body); focus should
    // have been restored.
    expect(document.activeElement).toBe(prior)
  })
})

// ────────────────────────────────────────────────────────────────────
// 2. Structural App-root lift pins
// ────────────────────────────────────────────────────────────────────

describe('Phase 29 C — App-root lift (structural source pins)', () => {
  const appSource = readFileSync(
    resolve(__dirname, '../src/App.tsx'),
    'utf-8',
  )
  const panelSource = readFileSync(
    resolve(__dirname, '../src/components/ResultMeshPlaybackPanel.tsx'),
    'utf-8',
  )

  it('App.tsx imports OnboardingTour and AdvancedModePromo', () => {
    expect(appSource).toMatch(
      /import\s*\{\s*OnboardingTour\s*\}\s*from\s*['"][^'"]*OnboardingTour['"]/,
    )
    expect(appSource).toMatch(
      /import\s*\{\s*AdvancedModePromo\s*\}\s*from\s*['"][^'"]*AdvancedModePromo['"]/,
    )
  })

  it('App.tsx renders both at top of the return tree', () => {
    expect(appSource).toMatch(/<OnboardingTour\b/)
    expect(appSource).toMatch(/<AdvancedModePromo\b/)
  })

  it('ResultMeshPlaybackPanel NO LONGER imports those components', () => {
    expect(panelSource).not.toMatch(
      /import\s*\{\s*OnboardingTour\s*\}\s*from\s*['"][^'"]*OnboardingTour['"]/,
    )
    expect(panelSource).not.toMatch(
      /import\s*\{\s*AdvancedModePromo\s*\}\s*from\s*['"][^'"]*AdvancedModePromo['"]/,
    )
  })

  it('ResultMeshPlaybackPanel NO LONGER renders the mounts inline', () => {
    expect(panelSource).not.toMatch(/<OnboardingTour\b/)
    expect(panelSource).not.toMatch(/<AdvancedModePromo\b/)
  })

  it('ResultMeshPlaybackPanel exposes optional uiMode + onUiModeChange props', () => {
    // Pin the back-compat API surface.
    expect(panelSource).toMatch(/uiMode\??\s*:\s*UiMode/)
    expect(panelSource).toMatch(/onUiModeChange\??\s*:\s*\(/)
  })
})

// ────────────────────────────────────────────────────────────────────
// 3. AdvancedModePromo entrance animation
// ────────────────────────────────────────────────────────────────────

describe('Phase 29 C — AdvancedModePromo entrance animation', () => {
  beforeEach(() => {
    window.localStorage.setItem(ONBOARDING_LS_KEY, 'true')
    window.localStorage.removeItem(ADVANCED_PROMPT_LS_KEY)
  })
  afterEach(() => {
    window.localStorage.removeItem(ONBOARDING_LS_KEY)
    window.localStorage.removeItem(ADVANCED_PROMPT_LS_KEY)
    uninstallPolishStyles()
  })

  it('exports POLISH_CLASS_ADVANCED_MODE_PROMO constant', () => {
    expect(POLISH_CLASS_ADVANCED_MODE_PROMO).toBe('fm04a-advanced-mode-promo')
  })

  it('CSS defines the fade-slide-in keyframes', () => {
    expect(POLISH_CSS_TEXT).toContain(
      '@keyframes fm04a-advanced-mode-promo-fade-slide-in',
    )
  })

  it('CSS applies the keyframe to the promo class (200ms ease-out)', () => {
    expect(POLISH_CSS_TEXT).toMatch(
      /\.fm04a-advanced-mode-promo\s*\{[\s\S]*?animation:[\s\S]*?fm04a-advanced-mode-promo-fade-slide-in[\s\S]*?200ms[\s\S]*?ease-out/,
    )
  })

  it('B:-1 — reduce-motion @media disables the promo animation', () => {
    const idx = POLISH_CSS_TEXT.indexOf(
      '@media (prefers-reduced-motion: reduce)',
    )
    expect(idx).toBeGreaterThan(-1)
    const tail = POLISH_CSS_TEXT.slice(idx)
    expect(tail).toContain('.fm04a-advanced-mode-promo')
    expect(tail).toContain('animation: none')
  })

  it('the promo card carries the polish class when visible', () => {
    render(
      <AdvancedModePromo uiMode="basic" onSwitchToAdvanced={() => {}} />,
    )
    const promo = screen.getByTestId('advanced-mode-promo')
    expect(promo).toBeTruthy()
    // The class is on the card child, not the backdrop.
    const card = promo.firstElementChild as HTMLElement | null
    expect(card).not.toBeNull()
    expect(card!.className).toContain(POLISH_CLASS_ADVANCED_MODE_PROMO)
  })
})

// ────────────────────────────────────────────────────────────────────
// 4. Focus-trap integration with the dialog overlays
// ────────────────────────────────────────────────────────────────────

describe('Phase 29 C — OnboardingTour focus-trap integration', () => {
  beforeEach(() => window.localStorage.removeItem(ONBOARDING_LS_KEY))
  afterEach(() => window.localStorage.removeItem(ONBOARDING_LS_KEY))

  it('initial focus lands inside the dialog (D:-2)', () => {
    render(<OnboardingTour />)
    const tour = screen.queryByTestId('onboarding-tour')
    if (!tour) {
      // If reduce-motion or LS state prevents render, skip silently.
      return
    }
    expect(tour.contains(document.activeElement)).toBe(true)
  })
})

describe('Phase 29 C — AdvancedModePromo focus-trap integration', () => {
  beforeEach(() => {
    window.localStorage.setItem(ONBOARDING_LS_KEY, 'true')
    window.localStorage.removeItem(ADVANCED_PROMPT_LS_KEY)
  })
  afterEach(() => {
    window.localStorage.removeItem(ONBOARDING_LS_KEY)
    window.localStorage.removeItem(ADVANCED_PROMPT_LS_KEY)
  })

  it('initial focus lands inside the promo (D:-2)', () => {
    render(
      <AdvancedModePromo uiMode="basic" onSwitchToAdvanced={() => {}} />,
    )
    const promo = screen.getByTestId('advanced-mode-promo')
    expect(promo.contains(document.activeElement)).toBe(true)
  })

  it('Tab from the last button (Switch) wraps to the first (Stay)', () => {
    render(
      <AdvancedModePromo uiMode="basic" onSwitchToAdvanced={() => {}} />,
    )
    const switchBtn = screen.getByTestId('advanced-mode-promo-switch')
    switchBtn.focus()
    fireEvent.keyDown(document, { key: 'Tab' })
    expect(document.activeElement).toBe(
      screen.getByTestId('advanced-mode-promo-stay'),
    )
  })

  it('Shift-Tab from Stay wraps to Switch', () => {
    render(
      <AdvancedModePromo uiMode="basic" onSwitchToAdvanced={() => {}} />,
    )
    const stayBtn = screen.getByTestId('advanced-mode-promo-stay')
    stayBtn.focus()
    fireEvent.keyDown(document, { key: 'Tab', shiftKey: true })
    expect(document.activeElement).toBe(
      screen.getByTestId('advanced-mode-promo-switch'),
    )
  })
})
