// FM-04a Phase 21 D — material_reference surfacing tests.
//
// Tier 1 / Tier 2 engineering candidate; not signed validation; not
// benchmark agreement.
//
// Phase 20 A wired `JobResponse.material_reference` end-to-end at the
// backend route, but NO frontend consumer existed (Phase 20 retro
// noted this as carry-forward). Phase 21 D surfaces the citation in
// two places:
//
//   1. Topbar: inline pill ("MATL · <reference>") right next to the
//      breadcrumb, so reviewers see WHICH material the solver actually
//      used immediately after pressing Run Solver.
//   2. OperatorStatusPanel "Runtime" section: a "Material reference"
//      row carrying the full citation (long-form, with detail tooltip).
//
// These tests pin the Topbar surface in isolation (the
// OperatorStatusPanel row would require firing up the whole App with
// a mocked /solver/run response — that path is exercised by the dev-
// server smoke, not unit-tested here).
//
// Anti-gaming guards:
//   - `materialReference={null}` MUST NOT render the chip (so the
//     surface doesn't lie about a citation when there isn't one).
//   - The chip carries the citation in both the visible text AND the
//     `title` attribute (full citation accessible via hover/aria).

import { describe, expect, it, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { Topbar } from '../src/components/Topbar'
import { VisualTabPanel } from '../src/components/VisualTabPanel'
import { FALLBACK_MATERIALS } from '../src/materialsClient'

describe('Topbar material_reference surfacing (Phase 21 D)', () => {
  const baseProps = {
    breadcrumbLabel: 'cylinder-pv-candidate',
    showRunControls: true,
    analysisType: 'static' as const,
    onChangeAnalysisType: vi.fn(),
    solving: false,
    onRunSolver: vi.fn(),
    onStopSolver: vi.fn(),
    showChat: false,
    onToggleChat: vi.fn(),
  }

  it('renders the MATL chip when materialReference is non-empty', () => {
    render(
      <Topbar
        {...baseProps}
        materialReference="EN 10025-2:2019 §7.3 (S355 grade, room temperature)"
      />,
    )
    const chip = screen.getByTestId('topbar-material-reference')
    expect(chip).toBeInTheDocument()
    expect(chip.textContent ?? '').toContain('MATL')
    expect(chip.textContent ?? '').toContain('EN 10025-2:2019')
  })

  it('carries the full citation in title attribute (hover affordance)', () => {
    const ref =
      'EN 10025-2:2019 §7.3 (S355 grade, room temperature); plastic_hardening_curve per EN 1993-1-5 Annex C §C.6 bilinear approximation (yield 355 MPa, ultimate 510 MPa at 20% plastic strain)'
    render(<Topbar {...baseProps} materialReference={ref} />)
    const chip = screen.getByTestId('topbar-material-reference')
    expect(chip).toHaveAttribute('title', ref)
  })

  it('does NOT render the MATL chip when materialReference is null', () => {
    render(<Topbar {...baseProps} materialReference={null} />)
    expect(
      screen.queryByTestId('topbar-material-reference'),
    ).not.toBeInTheDocument()
  })

  it('does NOT render the MATL chip when materialReference prop is omitted', () => {
    render(<Topbar {...baseProps} />)
    expect(
      screen.queryByTestId('topbar-material-reference'),
    ).not.toBeInTheDocument()
  })

  it('does NOT render the MATL chip when materialReference is empty string', () => {
    render(<Topbar {...baseProps} materialReference="" />)
    expect(
      screen.queryByTestId('topbar-material-reference'),
    ).not.toBeInTheDocument()
  })

  it('the MATL chip coexists with the badge slot', () => {
    render(
      <Topbar
        {...baseProps}
        badge={<span data-testid="custom-badge">BADGE</span>}
        materialReference="EN 10025-2:2019 §7.3"
      />,
    )
    expect(screen.getByTestId('custom-badge')).toBeInTheDocument()
    expect(screen.getByTestId('topbar-material-reference')).toBeInTheDocument()
  })
})

describe('VisualTabPanel extraction (Phase 21 D)', () => {
  beforeEach(() => {
    // Each child panel of the Visual tab makes its own fetch calls
    // against apiBase. Stub them all out with a 404 so the panels
    // mount cleanly to their fallback states without going for the
    // real network.
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => ({
        ok: false,
        status: 404,
        json: async () => ({}),
        text: async () => '',
      })),
    )
  })

  const baseProps = {
    apiBase: 'http://localhost:8000/api/v1',
    selectedCandidateCaseId: null,
    onSelectCandidateCaseId: vi.fn(),
    comparisonCaseA: null,
    comparisonCaseB: null,
    onSelectComparisonA: vi.fn(),
    onSelectComparisonB: vi.fn(),
    snapshotLabelA: null,
    snapshotLabelB: null,
    onSelectSnapshotLabelA: vi.fn(),
    onSelectSnapshotLabelB: vi.fn(),
    selectedMaterial: FALLBACK_MATERIALS[0],
    onMaterialChange: vi.fn(),
    latestSignoff: null,
    onLatestSignoff: vi.fn(),
  }

  it('mounts the extracted panel container', () => {
    render(<VisualTabPanel {...baseProps} />)
    expect(screen.getByTestId('visual-tab-panel')).toBeInTheDocument()
  })

  it('does NOT mount the ProvenancePanel when snapshotLabelA is null', () => {
    // ProvenancePanel and AdvisorPanel both gate mount on the (case_id
    // AND snapshotLabelA) pair to avoid empty-param fetches. With both
    // null we expect them absent.
    render(<VisualTabPanel {...baseProps} />)
    expect(screen.queryByTestId('provenance-panel')).not.toBeInTheDocument()
    expect(screen.queryByTestId('advisor-panel')).not.toBeInTheDocument()
  })
})
