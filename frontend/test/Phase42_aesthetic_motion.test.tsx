/**
 * FM-04a Phase 42 — connect-the-foundation aesthetic/motion polish.
 *
 * Additive pins (no prior-phase test edited) for the slice that wires the
 * already-shipped calm primitives into their consumers and kills one dead
 * animation:
 *   1. SkeletonCard adopts `.skeleton-block` / `.skeleton-line` AND the
 *      `skeleton-shimmer` keyframe it references is actually DEFINED in
 *      index.css — the exact regression class (a referenced-but-undefined
 *      keyframe → frozen animation) that this slice fixes.
 *   2. TabButton adopts the `.tab-pill` primitive (calm idle + hover + active),
 *      keeping the Phase22C `style.background` contract on the active branch.
 *   3. The new tab colors (active #04130d on --accent, idle --text-secondary on
 *      the panel surface) still meet WCAG AA 4.5:1 — no a11y regression vs the
 *      Phase 38 G floor.
 *
 * Tier 1 engineering candidate; not signed validation; not benchmark agreement.
 */

import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'

import { TabButton } from '../src/components/TabButton'
import { SkeletonCard } from '../src/components/SkeletonCard'
import { computeContrastRatio, meetsWCAG_AA } from '../src/lib/wcagContrast'

// vitest root is frontend/, so the foundation stylesheet resolves off cwd.
const INDEX_CSS = readFileSync(resolve(process.cwd(), 'src/index.css'), 'utf-8')

describe('Phase 42 — SkeletonCard dead-animation bug fix', () => {
  it('adopts the tokenized .skeleton-block / .skeleton-line classes', () => {
    render(<SkeletonCard lines={3} />)
    const card = screen.getByTestId('skeleton-card')
    expect(card.className).toContain('skeleton-block')
    const lines = screen.getAllByTestId('skeleton-line')
    expect(lines).toHaveLength(3)
    lines.forEach((l) => expect(l.className).toContain('skeleton-line'))
  })

  it('no longer hard-codes the inline shimmer animation on the line element', () => {
    render(<SkeletonCard lines={1} />)
    // The animation now lives in the .skeleton-line CSS class, not inline —
    // so the element MUST NOT carry an inline `animation` value.
    expect(screen.getAllByTestId('skeleton-line')[0].style.animation).toBe('')
  })

  it('the @keyframes the .skeleton-line class references IS defined in index.css', () => {
    // Regression guard for the dead-animation bug class (a referenced keyframe
    // that was never defined — same family as the 41.3 `animate-spin` fix).
    expect(INDEX_CSS).toContain('@keyframes skeleton-shimmer')
    expect(INDEX_CSS).toContain('animation: skeleton-shimmer')
    // and it is suppressed under reduced motion.
    expect(INDEX_CSS).toMatch(/prefers-reduced-motion[\s\S]*\.skeleton-line\s*\{\s*animation:\s*none/)
  })
})

describe('Phase 42 — TabButton adopts the .tab-pill primitive', () => {
  it('idle tab carries .tab-pill (no active modifier, no inline background)', () => {
    render(<TabButton active={false} onClick={() => undefined} label="Idle" icon={<span>★</span>} />)
    const btn = screen.getByText('Idle').closest('button') as HTMLButtonElement
    expect(btn.className).toContain('tab-pill')
    expect(btn.className).not.toContain('active')
    // No inline background → the `.tab-pill:hover` rule is free to paint hover.
    expect(btn.style.background).toBe('')
  })

  it('active tab carries .tab-pill.active and keeps the Phase22C inline background', () => {
    render(<TabButton active onClick={() => undefined} label="Active" icon={<span>★</span>} />)
    const btn = screen.getByText('Active').closest('button') as HTMLButtonElement
    expect(btn.className).toContain('tab-pill')
    expect(btn.className).toContain('active')
    expect(btn.style.background).toBe('var(--accent)')
  })
})

describe('Phase 42 — warm-light tab-pill colors meet WCAG AA', () => {
  // Warm-light Claude theme: the tab-pill-bar surface is --bg-surface (white).
  const PANEL = '#ffffff' // --bg-surface
  const ACCENT = '#b3552f' // --accent-500 (clay/coral)
  const TEXT_SECONDARY = '#5a544b' // --text-secondary
  const ACTIVE_TEXT = '#ffffff' // .tab-pill.active color (white on coral)

  it('active tab text (#fff on the clay --accent) passes AA', () => {
    expect(meetsWCAG_AA(computeContrastRatio(ACTIVE_TEXT, ACCENT))).toBe(true)
  })

  it('idle tab text (--text-secondary on the white panel) passes AA', () => {
    expect(meetsWCAG_AA(computeContrastRatio(TEXT_SECONDARY, PANEL))).toBe(true)
  })
})

describe('Phase 42 — status TEXT tokens meet WCAG AA on white cards (Codex R0 P2)', () => {
  // warn/success/danger/info are routed as normal-size text through these
  // tokens in badges + cards (CaseCompletenessCard, CohortDashboardPanel,
  // ComplianceBadge, …). On the warm-light theme card surface (--bg-surface =
  // white) they MUST clear 4.5:1. Pins the Codex R0 finding that --warn-400
  // (#b3791a = 3.7) and --success-500 (#4a8a5e = 4.1) regressed below AA.
  const WHITE = '#ffffff' // --bg-surface
  const STATUS_TEXT: Record<string, string> = {
    'warn-400': '#8f6200',
    'success-500': '#3f7a52',
    'danger-400': '#c5453b',
    'info-400': '#2f6fdb',
  }
  for (const [name, hex] of Object.entries(STATUS_TEXT)) {
    it(`--${name} (${hex}) as text on a white card passes AA`, () => {
      expect(meetsWCAG_AA(computeContrastRatio(hex, WHITE))).toBe(true)
    })
  }
})
