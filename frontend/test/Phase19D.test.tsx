// FM-04a Phase 19 D — UI primitive adoption + Sidebar extraction tests.
//
// Tier 1 / Tier 2 engineering candidate; not signed validation; not
// benchmark agreement.
//
// Pins the four Slice D changes:
//   1. Sidebar.tsx is a self-contained component with stable test-ids
//      (cmd-k-hint, case-gallery, case-item-*, frd-upload-input,
//      active-experiment-summary) and renders EmptyStateCard when the
//      case list is empty.
//   2. CohortDashboardPanel renders SkeletonCard / ErrorCard /
//      EmptyStateCard through its data-testid wrappers
//      (cohort-dashboard-loading / -error / -empty).
//   3. SignoffHistoryPanel renders the same primitives through
//      signoff-history-loading / -error / -empty wrappers.
//   4. ResultMeshPlaybackPanel surfaces a stress-contour-legend with
//      min/max field-value text and the linear-gradient swatch
//      (UX agent round-2 finding T5: contour scale was unlabeled).
//
// Anti-gaming guards:
//   * Each migration is asserted via the OUTER wrapper testid AND a
//     primitive-internal testid (e.g., empty-state-card, skeleton-card,
//     error-card) so swapping the primitive back to a bespoke div would
//     trip the suite.
//   * Sidebar receives `availableCases=[]` and the test asserts the
//     EmptyStateCard headline copy — pins the onboarding affordance.

import { describe, expect, it, vi, beforeEach } from 'vitest'
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { Sidebar } from '../src/components/Sidebar'
import { CohortDashboardPanel } from '../src/components/CohortDashboardPanel'
import { SignoffHistoryPanel } from '../src/components/SignoffHistoryPanel'
import { ResultMeshPlaybackPanel } from '../src/components/ResultMeshPlaybackPanel'

// ---------------------------------------------------------------------
// Shared fetch stub
// ---------------------------------------------------------------------

function stubFetch(body: unknown, ok = true, status = 200) {
  global.fetch = vi.fn().mockResolvedValue({
    ok,
    status,
    json: async () => body,
  } as Response)
}

function stubPendingFetch(): { resolveNow: () => void } {
  let resolve: (v: Response) => void = () => undefined
  global.fetch = vi.fn().mockImplementation(
    () =>
      new Promise<Response>((res) => {
        resolve = res
      }),
  )
  return {
    resolveNow: () =>
      resolve({
        ok: true,
        status: 200,
        json: async () => ({}),
      } as Response),
  }
}

// ---------------------------------------------------------------------
// 1. Sidebar.tsx
// ---------------------------------------------------------------------

describe('Sidebar (Phase 19 D extraction)', () => {
  const baseProps = {
    availableCases: [],
    activeCaseId: null,
    onSelectCase: vi.fn(),
    activeExperiment: null,
    onFileUpload: vi.fn(),
    onOpenPalette: vi.fn(),
  }

  it('mounts the cmd-k discoverability chip', () => {
    render(<Sidebar {...baseProps} />)
    expect(screen.getByTestId('cmd-k-hint')).toBeInTheDocument()
    expect(screen.getByText(/command palette/i)).toBeInTheDocument()
    expect(screen.getByText('⌘K')).toBeInTheDocument()
  })

  it('clicking the cmd-k chip invokes onOpenPalette', () => {
    const onOpenPalette = vi.fn()
    render(<Sidebar {...baseProps} onOpenPalette={onOpenPalette} />)
    fireEvent.click(screen.getByTestId('cmd-k-hint'))
    expect(onOpenPalette).toHaveBeenCalledTimes(1)
  })

  it('renders EmptyStateCard inside case-gallery when availableCases is empty', () => {
    render(<Sidebar {...baseProps} availableCases={[]} />)
    const wrapper = screen.getByTestId('case-gallery-empty')
    expect(wrapper).toBeInTheDocument()
    // primitive identity pin — must be the SSOT EmptyStateCard, not a
    // bespoke replacement div.
    expect(wrapper.querySelector('[data-testid="empty-state-card"]')).toBeTruthy()
    expect(screen.getByText(/no cases yet/i)).toBeInTheDocument()
  })

  it('renders each case as a stable case-item-* test id', () => {
    const cases = [
      {
        id: 'cylinder-pv-candidate',
        name: 'Pressure vessel',
        description: '',
        type: 'static',
        structure: 'cylinder',
        frd_path: 'a.frd',
      },
      {
        id: 'rod-wave-impact-candidate',
        name: 'Rod wave',
        description: '',
        type: 'dynamic',
        structure: 'rod',
        frd_path: 'b.frd',
      },
    ]
    render(<Sidebar {...baseProps} availableCases={cases} />)
    expect(screen.getByTestId('case-item-cylinder-pv-candidate')).toBeInTheDocument()
    expect(screen.getByTestId('case-item-rod-wave-impact-candidate')).toBeInTheDocument()
    // empty-state must NOT mount when cases exist
    expect(screen.queryByTestId('case-gallery-empty')).toBeNull()
  })

  it('clicking a case-item fires onSelectCase with that case', () => {
    const onSelectCase = vi.fn()
    const cases = [
      {
        id: 'cylinder-pv-candidate',
        name: 'PV',
        description: '',
        type: 'static',
        structure: 'cylinder',
        frd_path: 'a.frd',
      },
    ]
    render(
      <Sidebar
        {...baseProps}
        availableCases={cases}
        onSelectCase={onSelectCase}
      />,
    )
    fireEvent.click(screen.getByTestId('case-item-cylinder-pv-candidate'))
    expect(onSelectCase).toHaveBeenCalledTimes(1)
    expect(onSelectCase.mock.calls[0][0].id).toBe('cylinder-pv-candidate')
  })

  it('marks the active case with the .active class', () => {
    const cases = [
      {
        id: 'cylinder-pv-candidate',
        name: 'PV',
        description: '',
        type: 'static',
        structure: 'cylinder',
        frd_path: 'a.frd',
      },
    ]
    render(
      <Sidebar
        {...baseProps}
        availableCases={cases}
        activeCaseId="cylinder-pv-candidate"
      />,
    )
    const item = screen.getByTestId('case-item-cylinder-pv-candidate')
    expect(item.className).toContain('active')
  })

  it('renders active-experiment-summary only when an experiment is active', () => {
    const { rerender } = render(<Sidebar {...baseProps} activeExperiment={null} />)
    expect(screen.queryByTestId('active-experiment-summary')).toBeNull()

    rerender(
      <Sidebar
        {...baseProps}
        activeExperiment={{
          parameter: 'mesh_density',
          runs: [
            { iteration: 1, value: 0.05, status: 'COMPLETED' },
            { iteration: 2, value: 0.025, status: 'RUNNING' },
          ],
        }}
      />,
    )
    expect(screen.getByTestId('active-experiment-summary')).toBeInTheDocument()
    expect(screen.getByText(/EXP: MESH_DENSITY/)).toBeInTheDocument()
  })

  it('FRD upload input is wired to onFileUpload', () => {
    const onFileUpload = vi.fn()
    render(<Sidebar {...baseProps} onFileUpload={onFileUpload} />)
    const input = screen.getByTestId('frd-upload-input') as HTMLInputElement
    expect(input.type).toBe('file')
    fireEvent.change(input, { target: { files: [] } })
    expect(onFileUpload).toHaveBeenCalledTimes(1)
  })
})

// ---------------------------------------------------------------------
// 2. CohortDashboardPanel — Phase 18 D primitive adoption
// ---------------------------------------------------------------------

describe('CohortDashboardPanel (Phase 19 D primitive adoption)', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('renders SkeletonCard while loading via cohort-dashboard-loading wrapper', () => {
    stubPendingFetch()
    render(
      <CohortDashboardPanel
        apiBase="/api/v1"
        selectedCaseId={null}
        onSelectCase={vi.fn()}
      />,
    )
    const wrapper = screen.getByTestId('cohort-dashboard-loading')
    expect(wrapper).toBeInTheDocument()
    // Primitive identity pin
    expect(wrapper.querySelector('[data-testid="skeleton-card"]')).toBeTruthy()
  })

  it('renders ErrorCard with remediation when fetch fails', async () => {
    stubFetch({}, false, 500)
    render(
      <CohortDashboardPanel
        apiBase="/api/v1"
        selectedCaseId={null}
        onSelectCase={vi.fn()}
      />,
    )
    await waitFor(() => {
      expect(screen.getByTestId('cohort-dashboard-error')).toBeInTheDocument()
    })
    const wrapper = screen.getByTestId('cohort-dashboard-error')
    expect(wrapper.querySelector('[data-testid="error-card"]')).toBeTruthy()
    expect(wrapper.querySelector('[data-testid="error-code"]')?.textContent).toBe(
      'COHORT-LOAD',
    )
    expect(wrapper.querySelector('[data-testid="error-remediation"]')).toBeTruthy()
  })

  it('renders EmptyStateCard with onboarding copy when cohort is empty', async () => {
    stubFetch({
      schema_version: '1.0',
      generated_at_utc: '2026-05-17T00:00:00+00:00',
      claim_tier: 'Tier 1 engineering candidate',
      claim_boundary: 'tier1',
      cohort_count: 0,
      mean_score: null,
      completeness_distribution: {},
      entries: [],
      tier2_blockers_remaining: [],
      claim_impact: 'no candidates yet',
    })
    render(
      <CohortDashboardPanel
        apiBase="/api/v1"
        selectedCaseId={null}
        onSelectCase={vi.fn()}
      />,
    )
    await waitFor(() => {
      expect(screen.getByTestId('cohort-dashboard-empty')).toBeInTheDocument()
    })
    const wrapper = screen.getByTestId('cohort-dashboard-empty')
    expect(wrapper.querySelector('[data-testid="empty-state-card"]')).toBeTruthy()
    expect(screen.getByText(/no tier 1 candidate cases yet/i)).toBeInTheDocument()
  })
})

// ---------------------------------------------------------------------
// 3. SignoffHistoryPanel — Phase 18 D primitive adoption
// ---------------------------------------------------------------------

describe('SignoffHistoryPanel (Phase 19 D primitive adoption)', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('renders SkeletonCard wrapper while loading', () => {
    stubPendingFetch()
    render(
      <SignoffHistoryPanel apiBase="/api/v1" caseId="cylinder-pv-candidate" />,
    )
    const wrapper = screen.getByTestId('signoff-history-loading')
    expect(wrapper).toBeInTheDocument()
    expect(wrapper.querySelector('[data-testid="skeleton-card"]')).toBeTruthy()
  })

  it('renders ErrorCard with SIGNOFF-LOAD code on fetch failure', async () => {
    stubFetch({}, false, 500)
    render(
      <SignoffHistoryPanel apiBase="/api/v1" caseId="cylinder-pv-candidate" />,
    )
    await waitFor(() => {
      expect(screen.getByTestId('signoff-history-error')).toBeInTheDocument()
    })
    const wrapper = screen.getByTestId('signoff-history-error')
    expect(wrapper.querySelector('[data-testid="error-card"]')).toBeTruthy()
    expect(wrapper.querySelector('[data-testid="error-code"]')?.textContent).toBe(
      'SIGNOFF-LOAD',
    )
  })

  it('renders EmptyStateCard with "No signoffs yet" copy when record_count is 0', async () => {
    stubFetch({
      schema_version: '1.0.0',
      case_id: 'cylinder-pv-candidate',
      claim_tier: 'Tier 1 engineering candidate',
      claim_boundary: 'tier1',
      generated_at_utc: '2026-05-17T00:00:00+00:00',
      record_count: 0,
      records: [],
      claim_impact: '',
    })
    render(
      <SignoffHistoryPanel apiBase="/api/v1" caseId="cylinder-pv-candidate" />,
    )
    await waitFor(() => {
      expect(screen.getByTestId('signoff-history-empty')).toBeInTheDocument()
    })
    const wrapper = screen.getByTestId('signoff-history-empty')
    expect(wrapper.querySelector('[data-testid="empty-state-card"]')).toBeTruthy()
    expect(screen.getByText(/no signoffs yet/i)).toBeInTheDocument()
  })
})

// ---------------------------------------------------------------------
// 4. ResultMeshPlaybackPanel — stress contour legend
// ---------------------------------------------------------------------

describe('ResultMeshPlaybackPanel stress-contour-legend (Phase 19 D)', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('does NOT render the legend when there is no payload', () => {
    stubPendingFetch()
    render(<ResultMeshPlaybackPanel apiBase="/api/v1" caseId="x" />)
    expect(screen.queryByTestId('stress-contour-legend')).toBeNull()
  })

  it('renders the legend with min/max field-value labels once a frame projects', async () => {
    // Minimal payload: 4 coplanar nodes + 1 quad element so
    // buildProjection produces a non-empty polygon set and the
    // legend mounts. fieldRanges drives the min/max display.
    const payload = {
      schemaVersion: 1,
      analysisType: 'dynamic',
      fieldLabel: 'von Mises stress',
      claimBoundary: 'Tier 1 engineering candidate',
      modelTree: {
        children: [{ partRole: 'plate', elementCount: 1 }],
      },
      dynamicFrames: [
        {
          frame: 0,
          timeMs: 0,
          // readFrame() always materialises an empty fieldRanges object
          // when omitted, which then shadows any root-level ranges.
          // Put the ranges directly on the frame so the SSOT min/max
          // surfaces in the legend.
          fieldRanges: { valueMin: 0, valueMax: 320, maxDisplacement: 12.5 },
          nodes: [
            { label: 1, coordinates: [0, 0, 0] },
            { label: 2, coordinates: [1, 0, 0] },
            { label: 3, coordinates: [1, 1, 0] },
            { label: 4, coordinates: [0, 1, 0] },
          ],
          elements: [
            {
              label: 10,
              partRole: 'plate',
              alive: true,
              connectivity: [1, 2, 3, 4],
              value: 160,
            },
          ],
        },
      ],
    }
    stubFetch(payload)
    render(<ResultMeshPlaybackPanel apiBase="/api/v1" caseId="cylinder-pv-candidate" />)
    await waitFor(() => {
      expect(screen.getByTestId('stress-contour-legend')).toBeInTheDocument()
    })
    const legend = screen.getByTestId('stress-contour-legend')
    expect(legend.textContent).toMatch(/min/i)
    expect(legend.textContent).toMatch(/max/i)
    // The fieldRange values drive the labels.
    expect(legend.textContent).toMatch(/0/)
    expect(legend.textContent).toMatch(/320/)
  })

  it('legend exposes a linear-gradient swatch (color-scale legibility)', async () => {
    const payload = {
      schemaVersion: 1,
      analysisType: 'dynamic',
      fieldLabel: 'von Mises stress',
      claimBoundary: 'Tier 1',
      modelTree: { children: [{ partRole: 'plate', elementCount: 1 }] },
      dynamicFrames: [
        {
          frame: 0,
          timeMs: 0,
          fieldRanges: { valueMin: 0, valueMax: 100, maxDisplacement: 0 },
          nodes: [
            { label: 1, coordinates: [0, 0, 0] },
            { label: 2, coordinates: [1, 0, 0] },
            { label: 3, coordinates: [0, 1, 0] },
          ],
          elements: [
            {
              label: 1,
              partRole: 'plate',
              alive: true,
              connectivity: [1, 2, 3],
              value: 50,
            },
          ],
        },
      ],
    }
    stubFetch(payload)
    render(<ResultMeshPlaybackPanel apiBase="/api/v1" caseId="rod-wave-impact-candidate" />)
    await waitFor(() => {
      expect(screen.getByTestId('stress-contour-legend')).toBeInTheDocument()
    })
    const legend = screen.getByTestId('stress-contour-legend')
    // Defense in depth: confirm the swatch div carries the
    // linear-gradient SSOT colour stops so a future refactor can't
    // silently drop the gradient.
    const swatch = legend.querySelector(
      'div[style*="linear-gradient"]',
    ) as HTMLElement | null
    expect(swatch).toBeTruthy()
    // jsdom rewrites hex colour stops to rgb() form, so pin both forms
    // (#hex 0x2563eb == rgb(37,99,235); 0x10b981 == rgb(16,185,129);
    // 0xf97316 == rgb(249,115,22)). Either representation is acceptable.
    const style = swatch!.getAttribute('style') ?? ''
    expect(style).toMatch(/#2563eb|rgb\(\s*37,\s*99,\s*235\s*\)/i)
    expect(style).toMatch(/#10b981|rgb\(\s*16,\s*185,\s*129\s*\)/i)
    expect(style).toMatch(/#f97316|rgb\(\s*249,\s*115,\s*22\s*\)/i)
  })
})
