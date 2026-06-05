// FM-04a M3 — headless smoke for the in-app Workflow Monitor tab.
//
// Drives the M2 read contract (GET /workflow/stages, POST /workflow/trigger,
// GET /workflow/runs/{id}) with a routed fetch stub, mirroring the house panel
// test pattern (CohortAnomaliesPanel.test.tsx).

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor, fireEvent, act } from '@testing-library/react'
import { WorkflowMonitorTabPanel } from '../src/components/WorkflowMonitorTabPanel.tsx'
import { activeStageIndex, formatMetric } from '../src/workflowMonitorView.ts'
import { parseWorkflowRun } from '../src/workflowClient.ts'

// Mock the Trigger.dev realtime hook so the realtime path is exercised without a
// live cloud subscription. The holder lets each test choose what the orchestrator
// run looks like (terminal COMPLETED / stream error / absent).
const { realtimeHolder } = vi.hoisted(() => {
  const current: { run: unknown; error: Error | undefined; stop: () => void } = {
    run: undefined,
    error: undefined,
    stop: () => {},
  }
  return { realtimeHolder: { current } }
})
vi.mock('@trigger.dev/react-hooks', () => ({
  useRealtimeRun: () => realtimeHolder.current,
}))

const TRIGGER_BASE = 'http://localhost:3033'
const NODE_TRIGGER_BODY = { feaRunId: 'mock_1', orchRunId: 'run_x', publicAccessToken: 'tok_x' }

const CATALOG = {
  stages: [
    { order: 0, stage: 'project_intake', wsStage: 'intake', currentObject: 'project', description: '项目接收' },
    { order: 1, stage: 'solver_run', wsStage: 'solver', currentObject: 'ccx', description: '求解器运行' },
    { order: 2, stage: 'report_generation', wsStage: 'report', currentObject: 'report', description: '报告生成' },
  ],
}

function stageState(stage: string, status: string, extra: Record<string, unknown> = {}): Record<string, unknown> {
  return {
    schemaVersion: '1.0.0',
    runId: 'mock_1',
    stage,
    status,
    progress: 1.0,
    currentObject: stage,
    description: stage,
    metrics: {},
    warnings: [],
    errors: [],
    artifacts: {},
    agentExplanation: null,
    nextAction: null,
    ...extra,
  }
}

const PENDING_RUN = {
  runId: 'mock_1',
  label: 'monitor',
  status: 'pending',
  startedAt: null,
  finishedAt: null,
  failAtStage: null,
  currentStage: null,
  stages: CATALOG.stages.map((s) => stageState(s.stage, 'pending')),
}

const SUCCESS_RUN = {
  ...PENDING_RUN,
  status: 'success',
  finishedAt: '2026-06-03T00:00:00Z',
  currentStage: null,
  stages: [
    stageState('project_intake', 'success', { agentExplanation: '已接收项目几何与材料。' }),
    stageState('solver_run', 'success', { agentExplanation: 'CalculiX 收敛。' }),
    stageState('report_generation', 'success'),
  ],
}

const FAILED_RUN = {
  ...PENDING_RUN,
  status: 'failed',
  finishedAt: '2026-06-03T00:00:00Z',
  stages: [
    stageState('project_intake', 'success'),
    stageState('solver_run', 'failed', { errors: [{ faultClass: 'solver_convergence', message: 'diverged' }] }),
    stageState('report_generation', 'pending'),
  ],
}

// ADR-028 P1.5: a run whose intake stage is genuinely agent-driven (deterministic
// rule-based node), the other stages still scripted_demo — drives the D2 coverage
// qualifier (1 deterministic · 0 LLM · 2 scripted of 3) + per-stage badges.
const AGENTIC_RUN = {
  ...PENDING_RUN,
  status: 'success',
  finishedAt: '2026-06-03T00:00:00Z',
  stages: [
    stageState('project_intake', 'success', {
      provenance: 'deterministic_agent',
      agentExplanation: '判定物理类型 = 模态分析。',
    }),
    stageState('solver_run', 'success'),
    stageState('report_generation', 'success'),
  ],
}

interface RouteResp {
  ok?: boolean
  status?: number
  body: unknown
}

function routeFetch(routes: Record<string, RouteResp>): void {
  global.fetch = vi.fn(async (input: RequestInfo | URL) => {
    const u = String(input)
    const key = Object.keys(routes).find((k) => u.includes(k))
    const r: RouteResp = key !== undefined ? routes[key] : { ok: false, status: 404, body: {} }
    return { ok: r.ok ?? true, status: r.status ?? 200, json: async () => r.body } as Response
  }) as unknown as typeof fetch
}

describe('WorkflowMonitorTabPanel', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    realtimeHolder.current = { run: undefined, error: undefined, stop: () => {} }
  })

  it('renders the stage catalog as nodes once loaded', async () => {
    routeFetch({ '/workflow/stages': { body: CATALOG } })
    render(<WorkflowMonitorTabPanel apiBase="/api/v1" />)
    await waitFor(() => expect(screen.getByTestId('wf-node-project_intake')).toBeInTheDocument())
    expect(screen.getByTestId('wf-node-solver_run')).toHaveTextContent('求解器运行')
    expect(screen.getByTestId('wf-run-badge')).toHaveTextContent('no run')
  })

  it('shows an ErrorCard when the workflow backend is unreachable', async () => {
    routeFetch({ '/workflow/stages': { ok: false, status: 500, body: {} } })
    render(<WorkflowMonitorTabPanel apiBase="/api/v1" />)
    await waitFor(() => expect(screen.getByText(/not reachable/i)).toBeInTheDocument())
  })

  it('runs the pipeline and renders a terminal success run + agent log', async () => {
    routeFetch({
      '/workflow/stages': { body: CATALOG },
      '/workflow/trigger': { body: PENDING_RUN },
      '/workflow/runs/': { body: SUCCESS_RUN },
    })
    render(<WorkflowMonitorTabPanel apiBase="/api/v1" />)
    await waitFor(() => expect(screen.getByTestId('wf-run-button')).toBeInTheDocument())
    fireEvent.click(screen.getByTestId('wf-run-button'))
    await waitFor(() => expect(screen.getByTestId('wf-run-badge')).toHaveTextContent('SUCCESS'))
    expect(screen.getByTestId('wf-agent-log')).toHaveTextContent('CalculiX 收敛')
  })

  it('surfaces the ADR-028 D2 provenance coverage qualifier + per-stage badges', async () => {
    routeFetch({
      '/workflow/stages': { body: CATALOG },
      '/workflow/trigger': { body: PENDING_RUN },
      '/workflow/runs/': { body: AGENTIC_RUN },
    })
    render(<WorkflowMonitorTabPanel apiBase="/api/v1" />)
    await waitFor(() => expect(screen.getByTestId('wf-run-button')).toBeInTheDocument())
    fireEvent.click(screen.getByTestId('wf-run-button'))
    await waitFor(() => expect(screen.getByTestId('wf-run-badge')).toHaveTextContent('SUCCESS'))
    // Run-level coverage qualifier — deterministic and LLM kept DISTINCT, scripted honest.
    expect(screen.getByTestId('wf-coverage')).toHaveTextContent(
      'Agent-driven: deterministic 1 · LLM 0 · scripted 2 (of 3 stages)',
    )
    // Per-stage badges: the wired intake reads deterministic agent; the rest scripted demo.
    expect(screen.getAllByTestId('wf-prov-deterministic_agent').length).toBeGreaterThan(0)
    expect(screen.getAllByTestId('wf-prov-scripted_demo').length).toBeGreaterThan(0)
  })

  it('discloses 0 agent-driven for a default run with no genuine request (no over-claim)', async () => {
    routeFetch({
      '/workflow/stages': { body: CATALOG },
      '/workflow/trigger': { body: PENDING_RUN },
      '/workflow/runs/': { body: SUCCESS_RUN },
    })
    render(<WorkflowMonitorTabPanel apiBase="/api/v1" />)
    await waitFor(() => expect(screen.getByTestId('wf-run-button')).toBeInTheDocument())
    fireEvent.click(screen.getByTestId('wf-run-button'))
    await waitFor(() => expect(screen.getByTestId('wf-run-badge')).toHaveTextContent('SUCCESS'))
    // SUCCESS_RUN carries no provenance → all scripted_demo → honest 0 agent-driven.
    expect(screen.getByTestId('wf-coverage')).toHaveTextContent(
      'Agent-driven: deterministic 0 · LLM 0 · scripted 3 (of 3 stages)',
    )
  })

  it('surfaces a fault class when a stage fails', async () => {
    routeFetch({
      '/workflow/stages': { body: CATALOG },
      '/workflow/trigger': { body: PENDING_RUN },
      '/workflow/runs/': { body: FAILED_RUN },
    })
    render(<WorkflowMonitorTabPanel apiBase="/api/v1" />)
    await waitFor(() => expect(screen.getByTestId('wf-run-button')).toBeInTheDocument())
    fireEvent.click(screen.getByTestId('wf-run-button'))
    await waitFor(() => expect(screen.getByTestId('wf-run-badge')).toHaveTextContent('FAILED'))
    expect(screen.getByTestId('wf-wea')).toHaveTextContent('solver_convergence')
  })

  it('view helpers parse the run and locate the active stage', () => {
    const run = parseWorkflowRun(SUCCESS_RUN)
    expect(run).not.toBeNull()
    if (run === null) return
    expect(run.stages.length).toBe(3)
    expect(activeStageIndex(CATALOG.stages, run, null)).toBe(2)
    expect(formatMetric(2_500_000)).toBe('2.500e+6')
    expect(formatMetric('warn')).toBe('warn')
  })

  it('resets back to the no-run state', async () => {
    routeFetch({
      '/workflow/stages': { body: CATALOG },
      '/workflow/trigger': { body: PENDING_RUN },
      '/workflow/runs/': { body: SUCCESS_RUN },
    })
    render(<WorkflowMonitorTabPanel apiBase="/api/v1" />)
    await waitFor(() => expect(screen.getByTestId('wf-run-button')).toBeInTheDocument())
    fireEvent.click(screen.getByTestId('wf-run-button'))
    await waitFor(() => expect(screen.getByTestId('wf-run-badge')).toHaveTextContent('SUCCESS'))
    fireEvent.click(screen.getByTestId('wf-reset'))
    await waitFor(() => expect(screen.getByTestId('wf-run-badge')).toHaveTextContent('no run'))
    expect(screen.queryByTestId('wf-agent-log')).not.toBeInTheDocument()
  })

  it('surfaces an error and clears busy when the run cannot be started', async () => {
    routeFetch({
      '/workflow/stages': { body: CATALOG },
      '/workflow/trigger': { ok: false, status: 500, body: {} },
    })
    render(<WorkflowMonitorTabPanel apiBase="/api/v1" />)
    await waitFor(() => expect(screen.getByTestId('wf-run-button')).toBeInTheDocument())
    fireEvent.click(screen.getByTestId('wf-run-button'))
    await waitFor(() => expect(screen.getByTestId('wf-run-error')).toBeInTheDocument())
    expect(screen.getByTestId('wf-run-button')).not.toBeDisabled()
  })

  it('treats an empty agentExplanation / nextAction as absent (P2 parser)', () => {
    const run = parseWorkflowRun({
      ...SUCCESS_RUN,
      stages: [stageState('project_intake', 'success', { agentExplanation: '', nextAction: '' })],
    })
    expect(run).not.toBeNull()
    if (run === null) return
    expect(run.stages[0].agentExplanation).toBeNull()
    expect(run.stages[0].nextAction).toBeNull()
  })

  it('ignores a late poll that resolves after reset (stale-poll guard)', async () => {
    // Hold the first /runs/ poll open until we choose to resolve it, so we can
    // reset() while it is in flight and prove the superseded poll is discarded.
    let resolveRun: ((v: unknown) => void) | null = null
    const runPromise = new Promise<unknown>((res) => {
      resolveRun = res
    })
    global.fetch = vi.fn(async (input: RequestInfo | URL) => {
      const u = String(input)
      if (u.includes('/workflow/stages')) return { ok: true, status: 200, json: async () => CATALOG } as Response
      if (u.includes('/workflow/trigger')) return { ok: true, status: 200, json: async () => PENDING_RUN } as Response
      if (u.includes('/workflow/runs/')) {
        const body = await runPromise // hangs until the test resolves it
        return { ok: true, status: 200, json: async () => body } as Response
      }
      return { ok: false, status: 404, json: async () => ({}) } as Response
    }) as unknown as typeof fetch

    render(<WorkflowMonitorTabPanel apiBase="/api/v1" />)
    await waitFor(() => expect(screen.getByTestId('wf-run-button')).toBeInTheDocument())
    fireEvent.click(screen.getByTestId('wf-run-button'))
    await waitFor(() => expect(screen.getByTestId('wf-run-badge')).toHaveTextContent('mock_1'))
    // Reset while the poll is still in flight -> bumps the generation.
    fireEvent.click(screen.getByTestId('wf-reset'))
    await waitFor(() => expect(screen.getByTestId('wf-run-badge')).toHaveTextContent('no run'))
    // Now let the stale poll resolve with a terminal run and fully drain the
    // async chain (fetch -> parse -> pollOnce continuation). Without the guard,
    // setRun(SUCCESS_RUN) would land here; with it, the poll is discarded.
    await act(async () => {
      resolveRun?.(SUCCESS_RUN)
      await new Promise((r) => setTimeout(r, 20))
    })
    expect(screen.getByTestId('wf-run-badge')).toHaveTextContent('no run')
    expect(screen.queryByTestId('wf-agent-log')).not.toBeInTheDocument()
  })

  it('stops polling and surfaces an error after repeated poll failures', async () => {
    // Catalog + trigger succeed (non-terminal -> polling starts), but every poll
    // of the run fails; after MAX_POLL_FAILURES the Monitor stops + surfaces it.
    routeFetch({
      '/workflow/stages': { body: CATALOG },
      '/workflow/trigger': { body: PENDING_RUN },
      '/workflow/runs/': { ok: false, status: 500, body: {} },
    })
    render(<WorkflowMonitorTabPanel apiBase="/api/v1" />)
    await waitFor(() => expect(screen.getByTestId('wf-run-button')).toBeInTheDocument())
    fireEvent.click(screen.getByTestId('wf-run-button'))
    await waitFor(() => expect(screen.getByTestId('wf-run-error')).toBeInTheDocument(), { timeout: 5000 })
    expect(screen.getByTestId('wf-run-button')).not.toBeDisabled()
  })

  // --- realtime path (triggerServerBase set) -------------------------------

  it('realtime mode: triggers via the Node server and streams the orchestrator run', async () => {
    // The mocked orchestrator run is terminal (COMPLETED, 13/13) -> the live tick
    // refreshes the per-stage detail from FastAPI.
    realtimeHolder.current = {
      run: { status: 'COMPLETED', metadata: { feaRunId: 'mock_1', completedStages: 13, totalStages: 13 } },
      error: undefined,
      stop: () => {},
    }
    routeFetch({
      '/workflow/stages': { body: CATALOG },
      '/trigger-pipeline': { body: NODE_TRIGGER_BODY },
      '/workflow/runs/': { body: SUCCESS_RUN },
    })
    render(<WorkflowMonitorTabPanel apiBase="/api/v1" triggerServerBase={TRIGGER_BASE} />)
    await waitFor(() => expect(screen.getByTestId('wf-run-button')).toBeInTheDocument())
    fireEvent.click(screen.getByTestId('wf-run-button'))
    await waitFor(() => expect(screen.getByTestId('wf-run-badge')).toHaveTextContent('SUCCESS'))
    // The live-mode chip proves the realtime path engaged (not polling).
    expect(screen.getByTestId('wf-live-mode')).toHaveTextContent('realtime')
    expect(screen.getByTestId('wf-agent-log')).toHaveTextContent('CalculiX 收敛')
  })

  it('realtime mode falls back to polling when the Node trigger server is unreachable', async () => {
    // /trigger-pipeline fails -> the run still happens via the poll-only path,
    // and the chip honestly reports "polling".
    routeFetch({
      '/workflow/stages': { body: CATALOG },
      '/trigger-pipeline': { ok: false, status: 502, body: {} },
      '/workflow/trigger': { body: PENDING_RUN },
      '/workflow/runs/': { body: SUCCESS_RUN },
    })
    render(<WorkflowMonitorTabPanel apiBase="/api/v1" triggerServerBase={TRIGGER_BASE} />)
    await waitFor(() => expect(screen.getByTestId('wf-run-button')).toBeInTheDocument())
    fireEvent.click(screen.getByTestId('wf-run-button'))
    await waitFor(() => expect(screen.getByTestId('wf-run-badge')).toHaveTextContent('SUCCESS'))
    expect(screen.getByTestId('wf-live-mode')).toHaveTextContent('polling')
  })

  it('realtime mode surfaces a stream error from useRealtimeRun', async () => {
    realtimeHolder.current = { run: undefined, error: new Error('token expired'), stop: () => {} }
    routeFetch({
      '/workflow/stages': { body: CATALOG },
      '/trigger-pipeline': { body: NODE_TRIGGER_BODY },
      '/workflow/runs/': { body: SUCCESS_RUN },
    })
    render(<WorkflowMonitorTabPanel apiBase="/api/v1" triggerServerBase={TRIGGER_BASE} />)
    await waitFor(() => expect(screen.getByTestId('wf-run-button')).toBeInTheDocument())
    fireEvent.click(screen.getByTestId('wf-run-button'))
    await waitFor(() => expect(screen.getByTestId('wf-run-error')).toHaveTextContent(/realtime stream error/i))
  })
})
