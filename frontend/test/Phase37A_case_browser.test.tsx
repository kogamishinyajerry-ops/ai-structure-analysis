// FM-04a Phase 37 A — CaseBrowser canonical-surface tests.
//
// Pins the new Hyperworks-style case browser: tree-style grouping
// by solver_kind + filter chip row + preview pane.
//
// Anti-gaming guards:
//   Q:-1 (NEW Phase 37) — CaseBrowser preserves the
//     CandidateCaseRecord data contract; consumes the same fallback
//     array the existing Sidebar / palette consume. The 12-cohort
//     case list is fully rendered when grouping is enabled with no
//     filters.
//   I:-1 (Phase 34 carry) — Phase 19 D Sidebar is NOT touched by
//     this slice; CaseBrowser coexists.
//   D:-1 — every filter / grouping / preview behaviour has an
//     explicit pin.

import { describe, expect, it } from 'vitest'
import { fireEvent, render, screen } from '@testing-library/react'
import {
  CaseBrowser,
  groupAndFilterCases,
  prettyKind,
  previewBlurbFor,
} from '../src/components/CaseBrowser'
import type { CandidateCaseRecord } from '../src/candidateCaseRegistry'

const FIXTURES: ReadonlyArray<CandidateCaseRecord> = [
  {
    caseId: 'cantilever-beam-candidate',
    runnerAvailable: true,
    solverKind: 'linear_static',
    displayLabel: 'Cantilever beam · Euler-Bernoulli δ=PL³/(3EI)',
    claimTier: 'Tier 1 engineering candidate',
    starterDeckRelpath: null,
    engineDeckRelpath: null,
    generatorScriptRelpath: null,
    notesExcerpt: null,
    claimBoundary:
      'tier1_engineering_candidate; not_signed_validation; not_benchmark_agreement',
  },
  {
    caseId: 'cylinder-pv-candidate',
    runnerAvailable: true,
    solverKind: 'linear_static',
    displayLabel: 'Cylinder pressure vessel · Tier 2 validated',
    claimTier: 'Tier 2 validated (analytical hoop-stress cross-check)',
    starterDeckRelpath: null,
    engineDeckRelpath: null,
    generatorScriptRelpath: null,
    notesExcerpt: null,
    claimBoundary:
      'tier2_real_solver_validated; not_signed_validation; cross_check_against_analytical',
  },
  {
    caseId: 'GS-102-candidate',
    runnerAvailable: false,
    solverKind: 'dynamic',
    displayLabel: 'GS-102 · Single-hex demo',
    claimTier: 'Tier 1 engineering candidate',
    starterDeckRelpath: null,
    engineDeckRelpath: null,
    generatorScriptRelpath: null,
    notesExcerpt: null,
    claimBoundary:
      'tier1_engineering_candidate; not_signed_validation; not_benchmark_agreement',
  },
  {
    caseId: 'GS-102-refined-candidate',
    runnerAvailable: false,
    solverKind: 'dynamic',
    displayLabel: 'GS-102 refined',
    claimTier: 'Tier 1 engineering candidate',
    starterDeckRelpath: null,
    engineDeckRelpath: null,
    generatorScriptRelpath: null,
    notesExcerpt: null,
    claimBoundary:
      'tier1_engineering_candidate; not_signed_validation; not_benchmark_agreement',
  },
  {
    caseId: 'something-uncategorized',
    displayLabel: 'Mystery case',
    claimTier: 'Tier 1 engineering candidate',
    starterDeckRelpath: null,
    engineDeckRelpath: null,
    generatorScriptRelpath: null,
    notesExcerpt: null,
    claimBoundary:
      'tier1_engineering_candidate; not_signed_validation; not_benchmark_agreement',
  },
] as const

describe('Phase 37 A — CaseBrowser mount + structure', () => {
  it('renders the case-browser region with accessible name', () => {
    render(
      <CaseBrowser cases={FIXTURES} onSelectCase={() => undefined} />,
    )
    const region = screen.getByRole('region', {
      name: /Case browser — grouped by solver kind/i,
    })
    expect(region).toBeTruthy()
  })

  it('renders the count "5 of 5" with no filters applied', () => {
    render(<CaseBrowser cases={FIXTURES} onSelectCase={() => undefined} />)
    const count = screen.getByTestId('case-browser-count')
    expect(count.textContent).toBe('5 of 5')
  })

  it('groups cases by solver_kind with sorted group headers', () => {
    render(<CaseBrowser cases={FIXTURES} onSelectCase={() => undefined} />)
    // 3 groups: dynamic / linear_static / uncategorized
    expect(screen.getByTestId('case-browser-group-dynamic')).toBeTruthy()
    expect(screen.getByTestId('case-browser-group-linear_static')).toBeTruthy()
    expect(screen.getByTestId('case-browser-group-uncategorized')).toBeTruthy()
  })

  it('renders every fixture case row in some group (Q:-1 data contract)', () => {
    render(<CaseBrowser cases={FIXTURES} onSelectCase={() => undefined} />)
    for (const c of FIXTURES) {
      expect(screen.getByTestId(`case-browser-row-${c.caseId}`)).toBeTruthy()
    }
  })
})

describe('Phase 37 A — filter chips', () => {
  it('renders a filter chip for each distinct solver kind', () => {
    render(<CaseBrowser cases={FIXTURES} onSelectCase={() => undefined} />)
    expect(screen.getByTestId('case-browser-kind-chip-linear_static')).toBeTruthy()
    expect(screen.getByTestId('case-browser-kind-chip-dynamic')).toBeTruthy()
    // uncategorized fixtures have no solverKind → no chip
    expect(screen.queryByTestId('case-browser-kind-chip-uncategorized')).toBeNull()
  })

  it('toggles a kind chip → narrows the list to that kind', () => {
    render(<CaseBrowser cases={FIXTURES} onSelectCase={() => undefined} />)
    const chip = screen.getByTestId('case-browser-kind-chip-linear_static')
    fireEvent.click(chip)
    expect(chip.getAttribute('aria-pressed')).toBe('true')
    // The dynamic + uncategorized rows should no longer render
    expect(screen.queryByTestId('case-browser-row-GS-102-candidate')).toBeNull()
    expect(screen.queryByTestId('case-browser-row-something-uncategorized')).toBeNull()
    // linear_static rows remain
    expect(screen.getByTestId('case-browser-row-cantilever-beam-candidate')).toBeTruthy()
    expect(screen.getByTestId('case-browser-row-cylinder-pv-candidate')).toBeTruthy()
  })

  it('Tier 2 chip filters to Tier 2 validated cases only', () => {
    render(<CaseBrowser cases={FIXTURES} onSelectCase={() => undefined} />)
    fireEvent.click(screen.getByTestId('case-browser-tier2-chip'))
    expect(screen.getByTestId('case-browser-row-cylinder-pv-candidate')).toBeTruthy()
    expect(screen.queryByTestId('case-browser-row-cantilever-beam-candidate')).toBeNull()
  })

  it('search input filters case-insensitively by displayLabel or caseId', () => {
    render(<CaseBrowser cases={FIXTURES} onSelectCase={() => undefined} />)
    const input = screen.getByTestId('case-browser-search-input') as HTMLInputElement
    fireEvent.change(input, { target: { value: 'cylinder' } })
    expect(screen.getByTestId('case-browser-row-cylinder-pv-candidate')).toBeTruthy()
    expect(screen.queryByTestId('case-browser-row-cantilever-beam-candidate')).toBeNull()
  })

  it('renders the empty-state copy when no case matches the filter', () => {
    render(<CaseBrowser cases={FIXTURES} onSelectCase={() => undefined} />)
    const input = screen.getByTestId('case-browser-search-input') as HTMLInputElement
    fireEvent.change(input, { target: { value: 'nonexistent-xyzzy' } })
    expect(screen.getByTestId('case-browser-empty')).toBeTruthy()
  })
})

describe('Phase 37 A — preview pane', () => {
  it('renders a preview empty-state when no case is focused', () => {
    render(<CaseBrowser cases={FIXTURES} onSelectCase={() => undefined} />)
    const pane = screen.getByTestId('case-browser-preview-pane')
    expect(pane.textContent).toMatch(/Hover or focus a case/i)
  })

  it('renders the preview from the focusedCaseId prop', () => {
    render(
      <CaseBrowser
        cases={FIXTURES}
        focusedCaseId="cylinder-pv-candidate"
        onSelectCase={() => undefined}
      />,
    )
    const pane = screen.getByTestId('case-browser-preview-pane')
    expect(pane.textContent).toContain('Cylinder pressure vessel')
    expect(pane.textContent).toContain('Tier 2 validated')
    expect(pane.textContent).toMatch(/Pressure-vessel case/i)
  })

  it('renders the runner badge in the preview when runnerAvailable=false', () => {
    render(
      <CaseBrowser
        cases={FIXTURES}
        focusedCaseId="GS-102-candidate"
        onSelectCase={() => undefined}
      />,
    )
    expect(screen.getByTestId('case-browser-runner-badge')).toBeTruthy()
  })
})

describe('Phase 37 A — selection callback', () => {
  it('fires onSelectCase with the row caseId on click', () => {
    const onSelect = vi.fn()
    render(<CaseBrowser cases={FIXTURES} onSelectCase={onSelect} />)
    fireEvent.click(
      screen.getByTestId('case-browser-row-cantilever-beam-candidate'),
    )
    expect(onSelect).toHaveBeenCalledTimes(1)
    expect(onSelect.mock.calls[0][0]).toBe('cantilever-beam-candidate')
  })
})

describe('Phase 37 A — pure helpers', () => {
  it('groupAndFilterCases groups by solverKind and sorts group keys', () => {
    const groups = groupAndFilterCases(FIXTURES, {
      searchQuery: '',
      activeKindFilters: new Set(),
      tier2Only: false,
    })
    const keys = groups.map((g) => g.kind)
    expect(keys).toEqual(['dynamic', 'linear_static', 'uncategorized'])
  })

  it('prettyKind humanises the 6 enum values + uncategorized', () => {
    expect(prettyKind('linear_static')).toBe('Linear static')
    expect(prettyKind('modal')).toBe('Modal')
    expect(prettyKind('buckling')).toBe('Buckling')
    expect(prettyKind('dynamic')).toBe('Dynamic')
    expect(prettyKind('heat_transfer_steady_state')).toBe(
      'Heat transfer (steady state)',
    )
    expect(prettyKind('contact_pair_static')).toBe('Contact pair (static)')
    expect(prettyKind('uncategorized')).toBe('Uncategorized')
  })

  it('previewBlurbFor returns Phase-35-A-consistent copy', () => {
    expect(previewBlurbFor('hertz-contact-candidate')).toMatch(/Contact/i)
    expect(previewBlurbFor('cylinder-pv-candidate')).toMatch(/Pressure/i)
    expect(previewBlurbFor('cantilever-beam-candidate')).toMatch(/Cantilever beam/i)
    expect(previewBlurbFor('plate-with-hole-candidate')).toMatch(/Stress/i)
    expect(previewBlurbFor('heat-transfer-1d-candidate')).toMatch(/Heat-transfer/i)
    expect(previewBlurbFor('rod-wave-impact-energy-leak-candidate')).toMatch(
      /known-bad/i,
    )
    expect(previewBlurbFor('GS-102-candidate')).toMatch(/Ballistic/i)
  })
})

// vi is needed for the spy
import { vi } from 'vitest'
