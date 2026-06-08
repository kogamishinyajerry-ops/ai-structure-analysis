/**
 * FM-04a Phase 38 D — BCSetupPillList + BC-setup friction fixes.
 *
 * Phase 37 D FINAL friction points 1-3:
 *   #1 advisor row column → row (App.tsx; visual, not unit-tested here)
 *   #2 BCSetupAdvisorCard hides once BCs assigned → shouldShowBCSetupAdvisor
 *   #3 bc_setup_panel gains a concrete read-only affordance → BCSetupPillList
 *
 * Tier 1 engineering candidate; not signed validation; not benchmark
 * agreement.
 */

import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import {
  assignedBCsForCaseKind,
  BCSetupPillList,
  shouldShowBCSetupAdvisor,
} from '../src/components/BCSetupPillList'
import type { CandidateCaseRecord } from '../src/candidateCaseRegistry'

function mockRecord(
  overrides: Partial<CandidateCaseRecord> = {},
): CandidateCaseRecord {
  return {
    caseId: 'cylinder-pv-candidate' as CandidateCaseRecord['caseId'],
    claimTier: 'Tier 1 engineering candidate',
    starterDeckRelpath: null,
    engineDeckRelpath: null,
    generatorScriptRelpath: null,
    notesExcerpt: null,
    claimBoundary: 'tier1_engineering_candidate',
    ...overrides,
  }
}

describe('assignedBCsForCaseKind', () => {
  it('cylinder-pv → internal pressure', () => {
    expect(assignedBCsForCaseKind('cylinder-pv-candidate')).toContain(
      'Internal pressure',
    )
  })

  it('cantilever (static) → fixed end + tip load', () => {
    const bcs = assignedBCsForCaseKind('cantilever-beam-candidate')
    expect(bcs).toContain('Fixed end (encastre)')
    expect(bcs).toContain('Tip load')
  })

  it('cantilever (modal) → free vibration, NOT a tip load', () => {
    const bcs = assignedBCsForCaseKind('cantilever-beam-modal-candidate')
    expect(bcs.some((b) => b.includes('Free vibration'))).toBe(true)
    expect(bcs).not.toContain('Tip load')
  })

  it('wedge-c3d6 → base z-clamp + prescribed displacement', () => {
    const bcs = assignedBCsForCaseKind('wedge-c3d6-candidate')
    expect(bcs).toContain('Base z-clamp')
    expect(bcs).toContain('Top prescribed displacement')
  })

  it('unknown case → generic fallback (never empty)', () => {
    expect(assignedBCsForCaseKind('mystery-candidate')).toEqual([
      'Boundary conditions per case setup',
    ])
  })
})

describe('shouldShowBCSetupAdvisor (Phase 38 D friction #2)', () => {
  it('shows when bcAssigned is absent (cohort default)', () => {
    expect(shouldShowBCSetupAdvisor(mockRecord())).toBe(true)
  })

  it('shows when bcAssigned is false', () => {
    expect(shouldShowBCSetupAdvisor(mockRecord({ bcAssigned: false }))).toBe(
      true,
    )
  })

  it('HIDES when bcAssigned is true', () => {
    expect(shouldShowBCSetupAdvisor(mockRecord({ bcAssigned: true }))).toBe(
      false,
    )
  })
})

describe('BCSetupPillList render (Phase 38 D friction #3)', () => {
  it('renders Case-defined-BC pills + label when not assigned', () => {
    render(<BCSetupPillList caseRecord={mockRecord()} />)
    expect(screen.getByText('Case-defined BCs')).toBeTruthy()
    expect(screen.getByText('Internal pressure')).toBeTruthy()
    expect(screen.getAllByTestId('bc-pill').length).toBeGreaterThanOrEqual(1)
    expect(
      screen
        .getByTestId('bc-setup-pill-list')
        .getAttribute('data-bc-assigned'),
    ).toBe('false')
  })

  it('renders Assigned label + flag when bcAssigned true', () => {
    render(
      <BCSetupPillList
        caseRecord={mockRecord({
          caseId: 'cantilever-beam-candidate' as CandidateCaseRecord['caseId'],
          bcAssigned: true,
        })}
      />,
    )
    expect(screen.getByText('Assigned BCs')).toBeTruthy()
    expect(
      screen
        .getByTestId('bc-setup-pill-list')
        .getAttribute('data-bc-assigned'),
    ).toBe('true')
  })
})
