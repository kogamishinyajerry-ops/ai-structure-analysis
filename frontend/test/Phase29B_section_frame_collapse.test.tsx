// FM-04a Phase 29 B — SectionFrame primitive + collapsible accordion
// + useTrustSections hook tests.
//
// Three deliveries pinned in one test file:
//
// 1. SectionFrame primitive — header with chevron + collapsible body;
//    per-section localStorage persistence; aria-expanded / aria-controls;
//    chevron rotation tied to collapsed state.
// 2. sectionCollapseStorage helpers — load/save round-trip + corrupted-
//    key fallback + cross-section non-bleed (C:-1).
// 3. useTrustSections hook — 7-section build, granular per-section
//    memoization (same input → same reference); App.tsx LOC delta
//    (structural pin on file size).
//
// Anti-gaming guards:
//   B:-1 — prefers-reduced-motion: reduce disables chevron transition
//   C:-1 — per-section storage keys (no cross-section bleed)
//   D:-1 — default is EXPANDED (additive guard)
//   E:-1 — corrupted localStorage → default expanded (never throws)
//   D:-3 — useTrustSections preserves builder purity (no ctx mutation)
//
// Tier 1 / Tier 2 engineering candidate; not signed validation; not
// benchmark agreement.

import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, render, renderHook, screen } from '@testing-library/react'

import { SectionFrame } from '../src/components/SectionFrame'
import {
  sectionStorageKey,
} from '../src/components/OperatorStatusPanel'
import {
  SECTION_COLLAPSE_LS_KEY_PREFIX,
  SECTION_COLLAPSE_LS_KEY_SUFFIX,
  clearSectionCollapsed,
  loadSectionCollapsed,
  saveSectionCollapsed,
  sectionCollapseStorageKey,
} from '../src/components/sectionCollapseStorage'
import {
  POLISH_CSS_TEXT,
} from '../src/components/polishStyles'
import type { OperatorStatusSection } from '../src/types/AppTypes'
import {
  useTrustSections,
  type UseTrustSectionsContext,
} from '../src/state/useTrustSections'

// ────────────────────────────────────────────────────────────────────
// 1. sectionCollapseStorage helpers
// ────────────────────────────────────────────────────────────────────

describe('Phase 29 B — sectionCollapseStorageKey', () => {
  it('composes key with storageKey verbatim (C:-1)', () => {
    expect(sectionCollapseStorageKey('overview')).toBe(
      'fm04a.trust-section.overview.collapsed.v1',
    )
    expect(sectionCollapseStorageKey('blueprint-target')).toBe(
      'fm04a.trust-section.blueprint-target.collapsed.v1',
    )
    expect(sectionCollapseStorageKey('a')).not.toBe(
      sectionCollapseStorageKey('b'),
    )
  })

  it('prefix and suffix constants match the composed key', () => {
    const key = sectionCollapseStorageKey('xxx')
    expect(key.startsWith(SECTION_COLLAPSE_LS_KEY_PREFIX)).toBe(true)
    expect(key.endsWith(SECTION_COLLAPSE_LS_KEY_SUFFIX)).toBe(true)
  })
})

describe('Phase 29 B — load/save round-trip', () => {
  beforeEach(() => {
    clearSectionCollapsed('test-section')
    clearSectionCollapsed('other-section')
  })
  afterEach(() => {
    clearSectionCollapsed('test-section')
    clearSectionCollapsed('other-section')
  })

  it('load returns null when key absent (default → expanded)', () => {
    expect(loadSectionCollapsed('test-section')).toBeNull()
  })

  it('save(true) → load returns true', () => {
    saveSectionCollapsed('test-section', true)
    expect(loadSectionCollapsed('test-section')).toBe(true)
  })

  it('save(false) → load returns false (explicit expanded)', () => {
    saveSectionCollapsed('test-section', false)
    expect(loadSectionCollapsed('test-section')).toBe(false)
  })

  it('E:-1 — corrupted value returns null (caller defaults expanded)', () => {
    window.localStorage.setItem(
      sectionCollapseStorageKey('test-section'),
      'not-a-bool-value',
    )
    expect(loadSectionCollapsed('test-section')).toBeNull()
  })

  it('C:-1 — different storageKeys produce DIFFERENT persisted state', () => {
    saveSectionCollapsed('test-section', true)
    saveSectionCollapsed('other-section', false)
    expect(loadSectionCollapsed('test-section')).toBe(true)
    expect(loadSectionCollapsed('other-section')).toBe(false)
  })

  it('clearSectionCollapsed removes only that key', () => {
    saveSectionCollapsed('test-section', true)
    saveSectionCollapsed('other-section', true)
    clearSectionCollapsed('test-section')
    expect(loadSectionCollapsed('test-section')).toBeNull()
    expect(loadSectionCollapsed('other-section')).toBe(true)
  })
})

// ────────────────────────────────────────────────────────────────────
// 2. SectionFrame component
// ────────────────────────────────────────────────────────────────────

function makeSection(title = 'Test Section'): OperatorStatusSection {
  return {
    title,
    icon: <span data-testid="test-icon">[i]</span>,
    items: [
      { label: 'Row 1', value: 'value 1', tone: 'accent', detail: 'detail 1' },
      { label: 'Row 2', value: 'value 2', tone: 'warning' },
      { label: 'Row 3', value: 'value 3', tone: 'danger', detail: 'detail 3' },
    ],
  }
}

describe('Phase 29 B — SectionFrame default render', () => {
  beforeEach(() => clearSectionCollapsed('test-default'))
  afterEach(() => clearSectionCollapsed('test-default'))

  it('renders title and icon in the header', () => {
    render(<SectionFrame section={makeSection()} storageKey="test-default" />)
    expect(screen.getByText('Test Section')).toBeTruthy()
    expect(screen.getByTestId('test-icon')).toBeTruthy()
  })

  it('D:-1 — defaults to EXPANDED (no LS key, no defaultCollapsed)', () => {
    render(<SectionFrame section={makeSection()} storageKey="test-default" />)
    const body = screen.getByTestId('section-frame-test-default-body')
    expect(body.hasAttribute('hidden')).toBe(false)
    // All 3 rows visible
    expect(
      screen.getByTestId('section-frame-test-default-row-Row 1'),
    ).toBeTruthy()
    expect(
      screen.getByTestId('section-frame-test-default-row-Row 2'),
    ).toBeTruthy()
    expect(
      screen.getByTestId('section-frame-test-default-row-Row 3'),
    ).toBeTruthy()
  })

  it('toggle button has aria-expanded=true when expanded', () => {
    render(<SectionFrame section={makeSection()} storageKey="test-default" />)
    const toggle = screen.getByTestId('section-frame-test-default-toggle')
    expect(toggle.getAttribute('aria-expanded')).toBe('true')
    expect(toggle.getAttribute('aria-controls')).toBe(
      'section-frame-test-default-body',
    )
  })

  it('no item count shown when expanded', () => {
    render(<SectionFrame section={makeSection()} storageKey="test-default" />)
    expect(
      screen.queryByTestId('section-frame-test-default-count'),
    ).toBeNull()
  })
})

describe('Phase 29 B — SectionFrame collapse interaction', () => {
  beforeEach(() => clearSectionCollapsed('test-toggle'))
  afterEach(() => clearSectionCollapsed('test-toggle'))

  it('clicking toggle hides the body and writes LS', () => {
    render(<SectionFrame section={makeSection()} storageKey="test-toggle" />)
    fireEvent.click(screen.getByTestId('section-frame-test-toggle-toggle'))
    const body = screen.getByTestId('section-frame-test-toggle-body')
    expect(body.hasAttribute('hidden')).toBe(true)
    expect(loadSectionCollapsed('test-toggle')).toBe(true)
  })

  it('collapsed state shows item count in header', () => {
    render(<SectionFrame section={makeSection()} storageKey="test-toggle" />)
    fireEvent.click(screen.getByTestId('section-frame-test-toggle-toggle'))
    const count = screen.getByTestId('section-frame-test-toggle-count')
    expect(count.textContent).toContain('3 items')
  })

  it('item-count copy is SINGULAR for 1-item sections', () => {
    const oneItem: OperatorStatusSection = {
      title: 'Single',
      icon: null,
      items: [{ label: 'Only', value: 'v' }],
    }
    render(<SectionFrame section={oneItem} storageKey="test-toggle" />)
    fireEvent.click(screen.getByTestId('section-frame-test-toggle-toggle'))
    expect(
      screen.getByTestId('section-frame-test-toggle-count').textContent,
    ).toContain('1 item')
    expect(
      screen.getByTestId('section-frame-test-toggle-count').textContent,
    ).not.toContain('1 items')
  })

  it('aria-expanded flips to false after collapse', () => {
    render(<SectionFrame section={makeSection()} storageKey="test-toggle" />)
    const toggle = screen.getByTestId('section-frame-test-toggle-toggle')
    fireEvent.click(toggle)
    expect(toggle.getAttribute('aria-expanded')).toBe('false')
  })

  it('chevron rotates -90deg when collapsed', () => {
    render(<SectionFrame section={makeSection()} storageKey="test-toggle" />)
    fireEvent.click(screen.getByTestId('section-frame-test-toggle-toggle'))
    const chevron = screen.getByTestId(
      'section-frame-test-toggle-chevron',
    )
    expect(chevron.style.transform).toBe('rotate(-90deg)')
  })

  it('chevron rotates back to 0deg when re-expanded', () => {
    render(<SectionFrame section={makeSection()} storageKey="test-toggle" />)
    fireEvent.click(screen.getByTestId('section-frame-test-toggle-toggle'))
    fireEvent.click(screen.getByTestId('section-frame-test-toggle-toggle'))
    const chevron = screen.getByTestId(
      'section-frame-test-toggle-chevron',
    )
    expect(chevron.style.transform).toBe('rotate(0deg)')
  })

  it('fires onCollapsedChange callback with the new state', () => {
    const cb = vi.fn()
    render(
      <SectionFrame
        section={makeSection()}
        storageKey="test-toggle"
        onCollapsedChange={cb}
      />,
    )
    fireEvent.click(screen.getByTestId('section-frame-test-toggle-toggle'))
    expect(cb).toHaveBeenCalledWith(true)
    fireEvent.click(screen.getByTestId('section-frame-test-toggle-toggle'))
    expect(cb).toHaveBeenCalledWith(false)
  })
})

describe('Phase 29 B — SectionFrame initial state from LS', () => {
  beforeEach(() => clearSectionCollapsed('test-restore'))
  afterEach(() => clearSectionCollapsed('test-restore'))

  it('mounts COLLAPSED when LS says true', () => {
    saveSectionCollapsed('test-restore', true)
    render(<SectionFrame section={makeSection()} storageKey="test-restore" />)
    const body = screen.getByTestId('section-frame-test-restore-body')
    expect(body.hasAttribute('hidden')).toBe(true)
  })

  it('mounts EXPANDED when LS says false (explicit)', () => {
    saveSectionCollapsed('test-restore', false)
    render(<SectionFrame section={makeSection()} storageKey="test-restore" />)
    const body = screen.getByTestId('section-frame-test-restore-body')
    expect(body.hasAttribute('hidden')).toBe(false)
  })

  it('respects defaultCollapsed=true when no LS value present', () => {
    render(
      <SectionFrame
        section={makeSection()}
        storageKey="test-restore"
        defaultCollapsed
      />,
    )
    const body = screen.getByTestId('section-frame-test-restore-body')
    expect(body.hasAttribute('hidden')).toBe(true)
  })

  it('LS value WINS over defaultCollapsed', () => {
    // LS says expanded; defaultCollapsed says collapsed. LS wins
    // because reviewer's choice always wins over fresh defaults.
    saveSectionCollapsed('test-restore', false)
    render(
      <SectionFrame
        section={makeSection()}
        storageKey="test-restore"
        defaultCollapsed
      />,
    )
    const body = screen.getByTestId('section-frame-test-restore-body')
    expect(body.hasAttribute('hidden')).toBe(false)
  })

  it('forceCollapsed overrides everything', () => {
    saveSectionCollapsed('test-restore', false)
    render(
      <SectionFrame
        section={makeSection()}
        storageKey="test-restore"
        forceCollapsed
      />,
    )
    const body = screen.getByTestId('section-frame-test-restore-body')
    expect(body.hasAttribute('hidden')).toBe(true)
  })
})

describe('Phase 29 B — SectionFrame motion polish', () => {
  it('B:-1 — prefers-reduced-motion @media block disables chevron transition', () => {
    // Pin via raw CSS text — the structural rule is what matters.
    const idx = POLISH_CSS_TEXT.indexOf('@media (prefers-reduced-motion: reduce)')
    expect(idx).toBeGreaterThan(-1)
    const tail = POLISH_CSS_TEXT.slice(idx)
    expect(tail).toContain('.fm04a-section-frame-chevron')
    expect(tail).toContain('transition: none')
  })

  it('default transition rule exists OUTSIDE the reduce-motion block', () => {
    const idx = POLISH_CSS_TEXT.indexOf('@media (prefers-reduced-motion: reduce)')
    const before = POLISH_CSS_TEXT.slice(0, idx)
    expect(before).toContain('.fm04a-section-frame-chevron')
    expect(before).toContain('transition: transform')
  })
})

// ────────────────────────────────────────────────────────────────────
// 3. sectionStorageKey kebab derivation
// ────────────────────────────────────────────────────────────────────

describe('Phase 29 B — sectionStorageKey (kebab derivation)', () => {
  it('lowercases and replaces non-alphanumeric with hyphens', () => {
    expect(sectionStorageKey('Overview')).toBe('overview')
    expect(sectionStorageKey('Ballistic candidate')).toBe(
      'ballistic-candidate',
    )
    expect(sectionStorageKey('Validation & Reference')).toBe(
      'validation-reference',
    )
    expect(sectionStorageKey('Blueprint Target')).toBe('blueprint-target')
  })

  it('strips leading and trailing hyphens', () => {
    expect(sectionStorageKey('  spaced  ')).toBe('spaced')
    expect(sectionStorageKey('!!!Gate!!!')).toBe('gate')
  })
})

// ────────────────────────────────────────────────────────────────────
// 4. useTrustSections hook
// ────────────────────────────────────────────────────────────────────

function makeMinimalCtx(): UseTrustSectionsContext {
  // Minimal valid context where every input is non-throwing for the
  // 7 builders. The actual values don't matter for memo identity
  // tests, only that the shape is correct.
  const blueprintSummary = {
    label: 'BP-x',
    claimTier: 'tier1_candidate',
    imagePath: '/i.png',
    evidenceCaseId: 'evc',
    coveredAnchorCount: 4,
    anchorCount: 4,
    availableEvidenceCount: 1,
    evidenceCount: 1,
    allowedClaim: 'tier1_candidate',
  } as UseTrustSectionsContext['blueprintSummary']
  return {
    claimTier: 'tier1_candidate' as UseTrustSectionsContext['claimTier'],
    allowedClaim: 'tier1_candidate',
    solverTruthSource: 'foam-agent' as UseTrustSectionsContext['solverTruthSource'],
    candidateSpine: null,
    currentJobId: null,
    executionMode: 'tier1' as UseTrustSectionsContext['executionMode'],
    report: null,
    reportValidationStatus: null as UseTrustSectionsContext['reportValidationStatus'],
    referenceStatusRaw: null as UseTrustSectionsContext['referenceStatusRaw'],
    goldenSampleSummary: '0 samples',
    goldenSampleReviewCount: 0,
    blueprintSummary,
    overviewIcon: null,
    runtimeIcon: null,
    evidenceIcon: null,
    validationIcon: null,
    blueprintIcon: null,
    ballisticIcon: null,
    gateIcon: null,
    activeCaseId: null,
    file: null,
    caseLabel: '',
    nextAction: '',
    analysisModeLabel: '',
    currentJobLabel: '',
    lastSolverMaterialReference: null,
    runState: 'idle',
    runStateTone: 'muted' as UseTrustSectionsContext['runStateTone'],
    latestEvent: null,
    solverLogSummary: '',
    solverLogState: null,
    convergenceSummary: '',
    candidateConvergenceEvidence: null,
    convergenceClaimImpact: null,
    evidenceState: null as UseTrustSectionsContext['evidenceState'],
    manifestState: null as UseTrustSectionsContext['manifestState'],
    candidateManifest: null,
    backendProvenance: null,
    meshArtifactSource: null,
    candidateMeshEvidence: null,
    convergenceArtifactList: [],
    meshConvergenceStudySource: null,
    meshConvergenceStudy: null,
    meshConvergenceClaimImpact: null,
    referenceStatus: '',
    referenceReason: '',
    referenceDeviation: null,
    unitSummary: '',
    candidateAssumptions: null,
    materialSummary: '',
    boundarySummary: '',
    meshTopologySummary: '',
    meshDeckElementTypes: [],
    meshQualitySummary: '',
    meshClaimImpact: null,
    meshConvergenceStudySummary: '',
    convergenceMissingSummary: '',
    failurePatternRef: '',
    candidateBallistic: null,
    ballisticInitialVelocitySummary: '',
    ballisticResidualVelocitySummary: '',
    ballisticPerforationSummary: '',
    ballisticPerforationTone: 'muted' as UseTrustSectionsContext['ballisticPerforationTone'],
    ballisticEnergySummary: '',
    ballisticEnergyTone: 'muted' as UseTrustSectionsContext['ballisticEnergyTone'],
    ballisticAnimationSummary: '',
    ballisticTimeStepStudySummary: '',
    ballisticTimeStepStudyTone: 'muted' as UseTrustSectionsContext['ballisticTimeStepStudyTone'],
    ballisticTimeStepStudy: null,
    ballisticTier2BlockerSummary: '0 blockers',
    reviewerSummary: '0 reviewers',
    candidateReviewer: null,
    candidateLimitations: [],
    tier2BlockerSummary: '0 blockers',
  }
}

describe('Phase 29 B — useTrustSections', () => {
  it('returns 7 sections in canonical order', () => {
    const { result } = renderHook(() => useTrustSections(makeMinimalCtx()))
    expect(result.current.sections).toHaveLength(7)
    expect(result.current.sections.map((s) => s.title)).toEqual([
      'Overview',
      'Runtime',
      'Evidence',
      'Validation',
      'Blueprint target',
      'Ballistic candidate',
      'Gate',
    ])
  })

  it('trustStrip is a non-empty array of OperatorStatusItem', () => {
    const { result } = renderHook(() => useTrustSections(makeMinimalCtx()))
    expect(Array.isArray(result.current.trustStrip)).toBe(true)
    expect(result.current.trustStrip.length).toBeGreaterThan(0)
    for (const item of result.current.trustStrip) {
      expect(typeof item.label).toBe('string')
      // value MAY be a ReactNode (e.g. JSX badge) — the TS type is
      // historically `string` but the builders also produce JSX in
      // some cells. Just assert defined for purity.
      expect(item.value).toBeDefined()
    }
  })

  it('granular memoization: re-render with same ctx → SAME section refs', () => {
    const ctx = makeMinimalCtx()
    const { result, rerender } = renderHook(
      ({ c }: { c: UseTrustSectionsContext }) => useTrustSections(c),
      { initialProps: { c: ctx } },
    )
    const firstSections = result.current.sections
    const firstStrip = result.current.trustStrip
    rerender({ c: ctx })
    expect(result.current.sections).toBe(firstSections)
    expect(result.current.trustStrip).toBe(firstStrip)
  })

  it('changing one field busts ONLY the section that depends on it', () => {
    // Mutate `nextAction` (Overview-only input). Overview section
    // should be a fresh reference; Runtime / Evidence / Gate / etc
    // should still be ===.
    const ctx1 = makeMinimalCtx()
    const { result, rerender } = renderHook(
      ({ c }: { c: UseTrustSectionsContext }) => useTrustSections(c),
      { initialProps: { c: ctx1 } },
    )
    const firstSections = result.current.sections
    const overviewBefore = firstSections[0]
    const runtimeBefore = firstSections[1]
    const gateBefore = firstSections[6]

    const ctx2 = { ...ctx1, nextAction: 'do something new' }
    rerender({ c: ctx2 })
    const afterSections = result.current.sections

    expect(afterSections[0]).not.toBe(overviewBefore) // Overview busted
    expect(afterSections[1]).toBe(runtimeBefore) // Runtime preserved
    expect(afterSections[6]).toBe(gateBefore) // Gate preserved
  })
})

// ────────────────────────────────────────────────────────────────────
// 5. App.tsx structural LOC pin
// ────────────────────────────────────────────────────────────────────

describe('Phase 29 B — App.tsx LOC reversal', () => {
  const appSource = readFileSync(
    resolve(__dirname, '../src/App.tsx'),
    'utf-8',
  )
  const appLOC = appSource.split('\n').length

  it('App.tsx LOC is below 1500 after the Phase 29 B refactor', () => {
    // Phase 28 D left App.tsx at 1596 LOC. Phase 29 B target ≤1500.
    expect(appLOC).toBeLessThan(1500)
  })

  it('App.tsx no longer carries the inline Phase 28 D useMemo block', () => {
    // The Phase 28 D inline pattern: `const trustStrip: OperatorStatusItem[] = useMemo(`
    // should NO LONGER appear in App.tsx because the hook now owns it.
    expect(appSource).not.toMatch(
      /const\s+trustStrip\s*:\s*OperatorStatusItem\[\]\s*=\s*useMemo\s*\(/,
    )
    expect(appSource).not.toMatch(
      /const\s+trustSections\s*:\s*OperatorStatusSection\[\]\s*=\s*useMemo\s*\(/,
    )
  })

  it('App.tsx imports useTrustSections', () => {
    expect(appSource).toMatch(
      /import\s*\{\s*useTrustSections\s*\}\s*from\s*['"][^'"]*useTrustSections['"]/,
    )
  })
})
