// FM-04a Phase 20 D — Topbar + RightRail + ResultMesh primitive
// migration + Sidebar candidate-case roster tests.
//
// Tier 1 / Tier 2 engineering candidate; not signed validation; not
// benchmark agreement.
//
// Closes three Phase 19 E findings:
//   1. App.tsx god-component → Topbar.tsx + RightRail.tsx extracted.
//   2. ResultMeshPlaybackPanel scope drift → bespoke loading / error /
//      empty divs migrated to SkeletonCard / ErrorCard / EmptyStateCard.
//   3. cylinder-pv-candidate invisible in left rail → Sidebar exposes
//      a `candidateCases` roster section parallel to `availableCases`.
//
// Anti-gaming guards mirror Phase 19 D: every migration is asserted
// via the OUTER wrapper test id AND a primitive-internal test id
// (`empty-state-card` / `skeleton-card` / `error-card`).

import { describe, expect, it, vi, beforeEach } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { Topbar } from '../src/components/Topbar'
import { RightRail } from '../src/components/RightRail'
import { Sidebar } from '../src/components/Sidebar'
import { ResultMeshPlaybackPanel } from '../src/components/ResultMeshPlaybackPanel'

// ---------------------------------------------------------------------
// Topbar
// ---------------------------------------------------------------------

describe('Topbar (Phase 20 D extraction)', () => {
  const baseProps = {
    breadcrumbLabel: 'Session',
    showRunControls: false,
    analysisType: 'static' as const,
    onChangeAnalysisType: vi.fn(),
    solving: false,
    onRunSolver: vi.fn(),
    onStopSolver: vi.fn(),
    showChat: false,
    onToggleChat: vi.fn(),
  }

  it('renders breadcrumb label', () => {
    render(<Topbar {...baseProps} breadcrumbLabel="cylinder-pv-candidate" />)
    expect(screen.getByTestId('topbar-breadcrumb')).toHaveTextContent(
      'cylinder-pv-candidate',
    )
  })

  it('Copilot toggle button fires onToggleChat', () => {
    const onToggleChat = vi.fn()
    render(<Topbar {...baseProps} onToggleChat={onToggleChat} />)
    fireEvent.click(screen.getByTestId('topbar-copilot-toggle'))
    expect(onToggleChat).toHaveBeenCalledTimes(1)
  })

  it('does NOT render run controls when showRunControls=false', () => {
    render(<Topbar {...baseProps} showRunControls={false} />)
    expect(screen.queryByTestId('topbar-run-controls')).toBeNull()
    expect(screen.queryByTestId('topbar-run-solver')).toBeNull()
  })

  it('renders run controls when showRunControls=true', () => {
    render(<Topbar {...baseProps} showRunControls={true} />)
    expect(screen.getByTestId('topbar-run-controls')).toBeInTheDocument()
    expect(screen.getByTestId('topbar-analysis-type')).toBeInTheDocument()
    expect(screen.getByTestId('topbar-run-solver')).toBeInTheDocument()
  })

  it('analysis-type select fires onChangeAnalysisType', () => {
    const onChangeAnalysisType = vi.fn()
    render(
      <Topbar
        {...baseProps}
        showRunControls={true}
        onChangeAnalysisType={onChangeAnalysisType}
      />,
    )
    fireEvent.change(screen.getByTestId('topbar-analysis-type'), {
      target: { value: 'modal' },
    })
    expect(onChangeAnalysisType).toHaveBeenCalledWith('modal')
  })

  it('Run Solver button fires onRunSolver and is disabled while solving', () => {
    const onRunSolver = vi.fn()
    const { rerender } = render(
      <Topbar
        {...baseProps}
        showRunControls={true}
        onRunSolver={onRunSolver}
      />,
    )
    fireEvent.click(screen.getByTestId('topbar-run-solver'))
    expect(onRunSolver).toHaveBeenCalledTimes(1)
    rerender(
      <Topbar
        {...baseProps}
        showRunControls={true}
        solving={true}
        onRunSolver={onRunSolver}
      />,
    )
    expect(screen.getByTestId('topbar-run-solver')).toBeDisabled()
  })

  it('shows Stop button only while solving', () => {
    const { rerender } = render(
      <Topbar {...baseProps} showRunControls={true} solving={false} />,
    )
    expect(screen.queryByTestId('topbar-stop-solver')).toBeNull()
    rerender(<Topbar {...baseProps} showRunControls={true} solving={true} />)
    expect(screen.getByTestId('topbar-stop-solver')).toBeInTheDocument()
  })
})

// ---------------------------------------------------------------------
// RightRail
// ---------------------------------------------------------------------

describe('RightRail (Phase 20 D extraction)', () => {
  const baseProps = {
    showChat: false,
    caseId: null,
    onExecuteAction: vi.fn().mockResolvedValue({}),
    reviewCards: [],
  }

  it('renders nothing when showChat=false', () => {
    render(<RightRail {...baseProps} showChat={false} />)
    expect(screen.queryByTestId('workbench-right-rail')).toBeNull()
  })

  it('renders aside + ChatPanel when showChat=true', () => {
    // ChatPanel internally calls Element.scrollIntoView which jsdom
    // doesn't implement; stub it so the mount completes.
    Element.prototype.scrollIntoView = vi.fn() as unknown as (
      arg?: boolean | ScrollIntoViewOptions,
    ) => void
    render(<RightRail {...baseProps} showChat={true} />)
    expect(screen.getByTestId('workbench-right-rail')).toBeInTheDocument()
  })
})

// ---------------------------------------------------------------------
// Sidebar — candidate-case roster
// ---------------------------------------------------------------------

describe('Sidebar candidate-case roster (Phase 20 D)', () => {
  const baseProps = {
    availableCases: [],
    activeCaseId: null,
    onSelectCase: vi.fn(),
    activeExperiment: null,
    onFileUpload: vi.fn(),
    onOpenPalette: vi.fn(),
  }

  it('does NOT render the candidate roster when prop is absent', () => {
    render(<Sidebar {...baseProps} />)
    expect(screen.queryByTestId('candidate-case-roster')).toBeNull()
  })

  it('renders each candidate as a stable test id', () => {
    render(
      <Sidebar
        {...baseProps}
        candidateCases={[
          { caseId: 'cylinder-pv-candidate', displayLabel: 'Pressure Vessel' },
          {
            caseId: 'plate-with-hole-candidate',
            displayLabel: 'Plate with Hole',
          },
        ]}
      />,
    )
    expect(screen.getByTestId('candidate-case-roster')).toBeInTheDocument()
    expect(
      screen.getByTestId('candidate-case-cylinder-pv-candidate'),
    ).toBeInTheDocument()
    expect(
      screen.getByTestId('candidate-case-plate-with-hole-candidate'),
    ).toBeInTheDocument()
    expect(screen.getByText('Pressure Vessel')).toBeInTheDocument()
  })

  it('clicking a candidate fires onSelectCandidateCase with caseId', () => {
    const onSelectCandidateCase = vi.fn()
    render(
      <Sidebar
        {...baseProps}
        candidateCases={[
          { caseId: 'cylinder-pv-candidate', displayLabel: 'PV' },
        ]}
        onSelectCandidateCase={onSelectCandidateCase}
      />,
    )
    fireEvent.click(
      screen.getByTestId('candidate-case-cylinder-pv-candidate'),
    )
    expect(onSelectCandidateCase).toHaveBeenCalledWith(
      'cylinder-pv-candidate',
    )
  })

  it('marks the selected candidate with the .active class', () => {
    render(
      <Sidebar
        {...baseProps}
        candidateCases={[
          { caseId: 'cylinder-pv-candidate', displayLabel: 'PV' },
          { caseId: 'plate-with-hole-candidate', displayLabel: 'Plate' },
        ]}
        selectedCandidateCaseId="plate-with-hole-candidate"
      />,
    )
    expect(
      screen.getByTestId('candidate-case-cylinder-pv-candidate').className,
    ).not.toContain('active')
    expect(
      screen.getByTestId('candidate-case-plate-with-hole-candidate').className,
    ).toContain('active')
  })
})

// ---------------------------------------------------------------------
// ResultMeshPlaybackPanel — primitive migration (closes Phase 19 D
// commit-message scope drift the UI agent flagged)
// ---------------------------------------------------------------------

function stubFetch(body: unknown, ok = true, status = 200) {
  global.fetch = vi.fn().mockResolvedValue({
    ok,
    status,
    json: async () => body,
  } as Response)
}

function stubPendingFetch() {
  global.fetch = vi
    .fn()
    .mockImplementation(() => new Promise<Response>(() => undefined))
}

describe('ResultMeshPlaybackPanel primitive migration (Phase 20 D)', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('mounts SkeletonCard inside result-mesh-loading while pending', () => {
    stubPendingFetch()
    render(<ResultMeshPlaybackPanel apiBase="/api/v1" caseId="x" />)
    const wrapper = screen.getByTestId('result-mesh-loading')
    expect(wrapper).toBeInTheDocument()
    expect(wrapper.querySelector('[data-testid="skeleton-card"]')).toBeTruthy()
  })

  it('mounts ErrorCard with RESULT-MESH-LOAD code on fetch failure', async () => {
    stubFetch({}, false, 500)
    render(<ResultMeshPlaybackPanel apiBase="/api/v1" caseId="x" />)
    await waitFor(() => {
      expect(screen.getByTestId('result-mesh-error')).toBeInTheDocument()
    })
    const wrapper = screen.getByTestId('result-mesh-error')
    expect(wrapper.querySelector('[data-testid="error-card"]')).toBeTruthy()
    expect(
      wrapper.querySelector('[data-testid="error-code"]')?.textContent,
    ).toBe('RESULT-MESH-LOAD')
  })

  it('mounts EmptyStateCard when the payload is null (no result yet)', async () => {
    // The empty branch fires when payload itself is null (e.g. a
    // backend that responded with a literal `null` body — some
    // backends signal "no data" that way). Use a fetch stub that
    // returns null as the parsed JSON so currentResult.payload === null
    // while error stays null.
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => null,
    } as Response)
    render(
      <ResultMeshPlaybackPanel apiBase="/api/v1" caseId="static-only" />,
    )
    await waitFor(() => {
      expect(screen.getByTestId('result-mesh-empty')).toBeInTheDocument()
    })
    const wrapper = screen.getByTestId('result-mesh-empty')
    expect(wrapper.querySelector('[data-testid="empty-state-card"]')).toBeTruthy()
    expect(
      screen.getByText(/No active dynamic payload/i),
    ).toBeInTheDocument()
  })
})
