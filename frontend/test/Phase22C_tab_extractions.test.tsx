// FM-04a Phase 22 C — Narrative + Exploration tab extractions tests.
//
// Tier 1 / Tier 2 engineering candidate; not signed validation; not
// benchmark agreement.
//
// Anti-gaming guards:
//   * The two new panels render with their expected testids when
//     given canonical props.
//   * The Narrative panel calls `onDownloadPDF` exactly once per
//     click (no double-dispatch regression).
//   * The Exploration panel surfaces SensitivityForm + the comparison
//     overlay only when the experiment is COMPLETED.
//   * App.tsx LOC count is pinned (≤ 1500) inside the commit; this
//     test file does not duplicate that pin (a Bash check fits the
//     evidence shape better).

import { describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen } from '@testing-library/react'
import { NarrativeTabPanel } from '../src/components/NarrativeTabPanel'
import { ExplorationTabPanel } from '../src/components/ExplorationTabPanel'
import { OperatorStatusPanel } from '../src/components/OperatorStatusPanel'
import { TabButton } from '../src/components/TabButton'
import type {
  ExperimentStatus,
  GoldenSampleQueueItem,
  OperatorStatusItem,
  OperatorStatusSection,
  ReportData,
} from '../src/types/AppTypes'

const minimalReport: ReportData = {
  summary: 'Phase 22 C narrative test report',
  metrics: {
    max_displacement: 0.001,
    max_von_mises: 1e8,
    safety_factor: 2.0,
    status: 'PASS',
  },
  validation: { status: 'verified', error_percentage: 0 },
  markdown:
    '**Bold heading**\nA second line with `code`.\nA third line for layout.',
}

const completedExperiment: ExperimentStatus = {
  id: 'exp-001',
  parameter: 'thickness_m',
  status: 'COMPLETED',
  runs: [
    {
      iteration: 1,
      value: 0.005,
      job_id: 'job-1',
      status: 'COMPLETED',
      inp_path: '/tmp/run1.inp',
    },
    {
      iteration: 2,
      value: 0.01,
      job_id: 'job-2',
      status: 'COMPLETED',
      inp_path: '/tmp/run2.inp',
    },
  ],
}

describe('NarrativeTabPanel', () => {
  it('renders the markdown body and the Export PDF button', () => {
    render(
      <NarrativeTabPanel report={minimalReport} onDownloadPDF={() => undefined} />,
    )
    expect(screen.getByTestId('narrative-tab-panel')).toBeInTheDocument()
    const body = screen.getByTestId('narrative-markdown-body')
    expect(body.innerHTML).toContain('Bold heading')
    // newlines are translated to <br/> tags before render
    expect(body.innerHTML).toContain('<br>')
    expect(screen.getByTestId('narrative-export-pdf')).toBeInTheDocument()
  })

  it('invokes onDownloadPDF exactly once when the export button is clicked', () => {
    const onDownloadPDF = vi.fn()
    render(
      <NarrativeTabPanel report={minimalReport} onDownloadPDF={onDownloadPDF} />,
    )
    fireEvent.click(screen.getByTestId('narrative-export-pdf'))
    expect(onDownloadPDF).toHaveBeenCalledTimes(1)
  })
})

describe('ExplorationTabPanel', () => {
  it('renders SensitivityForm but hides the comparison overlay when no completed experiment', () => {
    render(
      <ExplorationTabPanel
        activeCaseId="case-001"
        loading={false}
        activeExperiment={null}
        comparedIndices={null}
        onCompareIndex={() => undefined}
        onRunStudy={() => undefined}
      />,
    )
    expect(screen.getByTestId('exploration-tab-panel')).toBeInTheDocument()
    expect(
      screen.queryByTestId('exploration-result-comparison'),
    ).not.toBeInTheDocument()
  })

  it('shows the comparison overlay when an experiment is COMPLETED', () => {
    render(
      <ExplorationTabPanel
        activeCaseId="case-001"
        loading={false}
        activeExperiment={completedExperiment}
        comparedIndices={null}
        onCompareIndex={() => undefined}
        onRunStudy={() => undefined}
      />,
    )
    expect(
      screen.getByTestId('exploration-result-comparison'),
    ).toBeInTheDocument()
    expect(
      screen.getByTestId('exploration-compare-button-0'),
    ).toBeInTheDocument()
    expect(
      screen.getByTestId('exploration-compare-button-1'),
    ).toBeInTheDocument()
  })

  it('compare button click forwards the iteration index', () => {
    const onCompareIndex = vi.fn()
    render(
      <ExplorationTabPanel
        activeCaseId="case-001"
        loading={false}
        activeExperiment={completedExperiment}
        comparedIndices={null}
        onCompareIndex={onCompareIndex}
        onRunStudy={() => undefined}
      />,
    )
    fireEvent.click(screen.getByTestId('exploration-compare-button-1'))
    expect(onCompareIndex).toHaveBeenCalledWith(1)
  })

  it('hides the comparison overlay when status is not COMPLETED', () => {
    const runningExperiment: ExperimentStatus = {
      ...completedExperiment,
      status: 'RUNNING',
    }
    render(
      <ExplorationTabPanel
        activeCaseId="case-001"
        loading={false}
        activeExperiment={runningExperiment}
        comparedIndices={null}
        onCompareIndex={() => undefined}
        onRunStudy={() => undefined}
      />,
    )
    expect(
      screen.queryByTestId('exploration-result-comparison'),
    ).not.toBeInTheDocument()
  })
})

describe('OperatorStatusPanel + TabButton extractions', () => {
  it('OperatorStatusPanel renders strip items, sections, and golden samples', () => {
    const strip: OperatorStatusItem[] = [
      { label: 'Pipeline', value: 'green', tone: 'accent' },
    ]
    const sections: OperatorStatusSection[] = [
      {
        title: 'Test section',
        icon: <span data-testid="section-icon">⚙</span>,
        items: [{ label: 'Item-A', value: 'value-A' }],
      },
    ]
    const goldenSamples: GoldenSampleQueueItem[] = [
      {
        caseId: 'gs-001',
        name: 'sample-1',
        status: 'pending',
        reason: 'awaiting review',
        failurePatternRef: 'fp-1',
        tone: 'muted',
      },
    ]
    render(
      <OperatorStatusPanel
        strip={strip}
        sections={sections}
        goldenSamples={goldenSamples}
      />,
    )
    expect(screen.getByText('Pipeline')).toBeInTheDocument()
    expect(screen.getByText('Test section')).toBeInTheDocument()
    expect(screen.getByText('gs-001')).toBeInTheDocument()
  })

  it('TabButton renders label + invokes onClick on click', () => {
    const onClick = vi.fn()
    render(
      <TabButton
        active={false}
        onClick={onClick}
        label="Test Tab"
        icon={<span>★</span>}
      />,
    )
    fireEvent.click(screen.getByText('Test Tab'))
    expect(onClick).toHaveBeenCalledTimes(1)
  })

  it('TabButton active styling switches with active prop', () => {
    const { rerender } = render(
      <TabButton
        active={false}
        onClick={() => undefined}
        label="Test Tab"
        icon={<span>★</span>}
      />,
    )
    const inactiveBtn = screen
      .getByText('Test Tab')
      .closest('button') as HTMLButtonElement
    expect(inactiveBtn.style.background).not.toBe('var(--accent)')
    rerender(
      <TabButton
        active={true}
        onClick={() => undefined}
        label="Test Tab"
        icon={<span>★</span>}
      />,
    )
    const activeBtn = screen
      .getByText('Test Tab')
      .closest('button') as HTMLButtonElement
    expect(activeBtn.style.background).toBe('var(--accent)')
  })
})
