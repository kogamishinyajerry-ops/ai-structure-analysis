// FM-04a M3 — Agentic FEA Workflow Runtime · in-app Monitor tab.
//
// Ports the self-contained M2 prototype (docs/demo/workflow_monitor.html) into
// a native React tab: a 13-stage node graph (left), an evolving
// bracket-with-hole specimen that gains layers per stage (center), and an
// agent-explanation log (right), with a run timeline + warnings/errors/artifacts
// strip below. POLL-only against the real backend (GET /workflow/runs/{id});
// no Trigger.dev realtime SDK — a clean seam for useRealtimeRun() remains in
// workflowClient (orchRunId/publicAccessToken) for when a real token is minted
// at the Node trigger layer.
//
// Tier 1 / Tier 2 engineering candidate; not signed validation; not
// benchmark agreement.

import { useCallback, useEffect, useRef, useState, type CSSProperties } from 'react'
import { Play, RotateCcw } from 'lucide-react'

import { EmptyStateCard } from './EmptyStateCard'
import { ErrorCard } from './ErrorCard'
import { SkeletonCard } from './SkeletonCard'
import {
  fetchWorkflowRun,
  fetchWorkflowStages,
  isTerminal,
  triggerWorkflow,
  type StageCatalogEntry,
  type StageState,
  type WorkflowRun,
  type WorkflowStatus,
} from '../workflowClient'
import {
  activeStageIndex,
  bcHatchRows,
  DEFORM_PATH,
  formatMetric,
  HOLE,
  LAYER_STAGE,
  loadArrowColumns,
  meshGridLines,
  PLATE_PATH,
  STATUS_LABEL,
  STATUS_TOKEN,
  stageReached,
  VIZ_H,
  VIZ_W,
} from '../workflowMonitorView'

const POLL_INTERVAL_MS = 800
// Stop polling + surface an error after this many consecutive failed polls, so a
// dropped backend cannot leave the Monitor spinning in `busy` forever (Codex M3 P2).
const MAX_POLL_FAILURES = 4

export interface WorkflowMonitorTabPanelProps {
  readonly apiBase: string
}

export function WorkflowMonitorTabPanel({ apiBase }: WorkflowMonitorTabPanelProps) {
  const [catalog, setCatalog] = useState<readonly StageCatalogEntry[]>([])
  const [loadingCatalog, setLoadingCatalog] = useState(true)
  const [catalogError, setCatalogError] = useState<string | null>(null)
  const [run, setRun] = useState<WorkflowRun | null>(null)
  const [selectedStage, setSelectedStage] = useState<string | null>(null)
  const [failAt, setFailAt] = useState('')
  const [busy, setBusy] = useState(false)
  const [runError, setRunError] = useState<string | null>(null)

  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const mountedRef = useRef(true)
  // Monotonic run "generation" — bumped on every run/reset so a poll from a
  // superseded run that resolves late cannot overwrite the current UI (P1).
  const runSeqRef = useRef(0)
  const pollFailRef = useRef(0)

  const stopPolling = (): void => {
    if (pollRef.current !== null) {
      clearInterval(pollRef.current)
      pollRef.current = null
    }
  }

  const reloadCatalog = useCallback(
    (signal?: AbortSignal): void => {
      void (async () => {
        const res = await fetchWorkflowStages(apiBase, signal)
        if (!mountedRef.current) return
        if (res.error !== undefined && res.stages.length === 0) setCatalogError(res.error)
        else {
          setCatalog(res.stages)
          setCatalogError(null)
        }
        setLoadingCatalog(false)
      })()
    },
    [apiBase],
  )

  useEffect(() => {
    mountedRef.current = true
    const ac = new AbortController()
    reloadCatalog(ac.signal)
    return () => {
      mountedRef.current = false
      ac.abort()
      if (pollRef.current !== null) {
        clearInterval(pollRef.current)
        pollRef.current = null
      }
    }
  }, [reloadCatalog])

  const pollOnce = async (runId: string, seq: number): Promise<void> => {
    const res = await fetchWorkflowRun(apiBase, runId)
    // Ignore a poll whose run was superseded (reset / newer run) or unmounted.
    if (!mountedRef.current || seq !== runSeqRef.current) return
    if (res.run !== null) {
      pollFailRef.current = 0
      setRun(res.run)
      if (isTerminal(res.run.status)) {
        stopPolling()
        setBusy(false)
      }
      return
    }
    // Tolerate transient blips, but stop + surface after a run of failures.
    pollFailRef.current += 1
    if (pollFailRef.current >= MAX_POLL_FAILURES) {
      stopPolling()
      setBusy(false)
      setRunError(res.error ?? 'lost connection to the workflow backend while polling')
    }
  }

  const runPipeline = async (): Promise<void> => {
    stopPolling()
    const seq = runSeqRef.current + 1
    runSeqRef.current = seq
    pollFailRef.current = 0
    setSelectedStage(null)
    setRunError(null)
    setBusy(true)
    const res = await triggerWorkflow(apiBase, { failAtStage: failAt === '' ? null : failAt })
    if (!mountedRef.current || seq !== runSeqRef.current) return
    if (res.run === null) {
      setRunError(res.error ?? 'failed to start the workflow run')
      setBusy(false)
      return
    }
    setRun(res.run)
    if (isTerminal(res.run.status)) {
      setBusy(false)
      return
    }
    const runId = res.run.runId
    void pollOnce(runId, seq)
    pollRef.current = setInterval(() => {
      void pollOnce(runId, seq)
    }, POLL_INTERVAL_MS)
  }

  const reset = (): void => {
    stopPolling()
    // Bump the generation so any in-flight poll/trigger from the prior run is
    // discarded when it resolves (P1 stale-state race).
    runSeqRef.current += 1
    pollFailRef.current = 0
    setRun(null)
    setSelectedStage(null)
    setRunError(null)
    setBusy(false)
  }

  if (loadingCatalog) {
    return (
      <div className="surface-card" style={shellStyle} data-testid="workflow-monitor">
        <SkeletonCard lines={5} label="Loading the FEA workflow stages…" />
      </div>
    )
  }

  if (catalogError !== null) {
    return (
      <div className="surface-card" style={shellStyle} data-testid="workflow-monitor">
        <ErrorCard
          title="Workflow backend not reachable"
          message={catalogError}
          remediation={[
            'Start the backend: uvicorn app.main:app --port 8000 (from backend/)',
            'Or run the standalone demo: python scripts/serve_workflow_demo.py (then set the API base to :8077)',
          ]}
          onRetry={() => {
            setLoadingCatalog(true)
            reloadCatalog()
          }}
          code="WORKFLOW-STAGES"
        />
      </div>
    )
  }

  const activeIdx = activeStageIndex(catalog, run, selectedStage)
  const focusStage = activeIdx >= 0 ? catalog[activeIdx] : undefined
  const focusState = focusStage !== undefined ? stageStateFor(run, focusStage.stage) : null

  return (
    <div className="surface-card" style={shellStyle} data-testid="workflow-monitor">
      <div style={headerRowStyle}>
        <div>
          <div style={titleStyle}>FEA Workflow Monitor</div>
          <div style={subtitleStyle}>
            Mock pipeline · synthetic solver data, real StageState events · 13 stages
          </div>
        </div>
        <RunBadge run={run} />
      </div>

      <div style={controlsRowStyle}>
        <button
          type="button"
          className="tab-pill"
          style={primaryButtonStyle}
          disabled={busy}
          onClick={() => {
            void runPipeline()
          }}
          data-testid="wf-run-button"
        >
          <Play size={14} /> {busy ? 'Running…' : 'Run pipeline'}
        </button>
        <label style={controlLabelStyle}>
          fail at
          <select
            value={failAt}
            onChange={(e) => setFailAt(e.target.value)}
            style={selectStyle}
            data-testid="wf-failat"
          >
            <option value="">— none —</option>
            {catalog.map((c) => (
              <option key={c.stage} value={c.stage}>
                {c.order + 1}. {c.description}
              </option>
            ))}
          </select>
        </label>
        <button
          type="button"
          className="tab-pill"
          style={ghostButtonStyle}
          onClick={reset}
          data-testid="wf-reset"
        >
          <RotateCcw size={14} /> Reset
        </button>
      </div>

      {runError !== null && (
        <div role="alert" style={runErrorStyle} data-testid="wf-run-error">
          Could not run the pipeline: {runError}
        </div>
      )}

      <div style={gridStyle}>
        <section style={columnStyle}>
          <h3 style={columnTitleStyle}>Pipeline · 13 stages</h3>
          <div>
            {catalog.map((c) => (
              <StageNode
                key={c.stage}
                entry={c}
                state={stageStateFor(run, c.stage)}
                selected={selectedStage === c.stage}
                onSelect={() => setSelectedStage(c.stage)}
              />
            ))}
          </div>
        </section>

        <section style={columnStyle}>
          <h3 style={columnTitleStyle}>
            Specimen preview{focusStage !== undefined ? ` · ${focusStage.description}` : ''}
          </h3>
          <WorkflowVizSvg
            catalog={catalog}
            activeIdx={activeIdx}
            qualityActive={selectedStage === LAYER_STAGE.quality || (run?.currentStage ?? null) === LAYER_STAGE.quality}
          />
          <MetricRows state={focusState} />
        </section>

        <section style={columnStyle}>
          <h3 style={columnTitleStyle}>Agent explanation log</h3>
          <AgentLog run={run} />
        </section>
      </div>

      <div style={bottomGridStyle}>
        <section style={columnStyle}>
          <h3 style={columnTitleStyle}>Run timeline</h3>
          <div style={timelineStyle} data-testid="wf-timeline">
            {catalog.map((c) => {
              const st = stageStateFor(run, c.stage)
              const status: WorkflowStatus = st?.status ?? 'pending'
              return (
                <span
                  key={c.stage}
                  title={c.description}
                  style={timelinePillStyle(status)}
                >
                  {c.order + 1} {c.stage.split('_')[0]}
                </span>
              )
            })}
          </div>
        </section>
        <section style={columnStyle}>
          <h3 style={columnTitleStyle}>Warnings · errors · artifacts</h3>
          <WeaList run={run} />
        </section>
      </div>
    </div>
  )
}

function stageStateFor(run: WorkflowRun | null, stage: string): StageState | null {
  if (run === null) return null
  return run.stages.find((s) => s.stage === stage) ?? null
}

function RunBadge({ run }: { run: WorkflowRun | null }) {
  if (run === null) {
    return (
      <span style={badgeStyle('var(--text-muted)')} data-testid="wf-run-badge">
        no run
      </span>
    )
  }
  return (
    <span style={badgeStyle(STATUS_TOKEN[run.status])} data-testid="wf-run-badge">
      {run.runId} · {STATUS_LABEL[run.status]}
    </span>
  )
}

function StageNode({
  entry,
  state,
  selected,
  onSelect,
}: {
  entry: StageCatalogEntry
  state: StageState | null
  selected: boolean
  onSelect: () => void
}) {
  const status: WorkflowStatus = state?.status ?? 'pending'
  const color = STATUS_TOKEN[status]
  const progressPct = status === 'pending' ? 0 : Math.round((state?.progress ?? 0) * 100)
  const object = state?.currentObject ?? entry.currentObject ?? ''
  return (
    <button
      type="button"
      onClick={onSelect}
      style={nodeStyle(selected)}
      data-testid={`wf-node-${entry.stage}`}
      data-status={status}
    >
      <span aria-hidden="true" style={nodeDotStyle(color, status === 'running')} />
      <span style={nodeBodyStyle}>
        <span style={nodeNameStyle(status, color)}>
          {entry.order + 1}. {entry.description}
        </span>
        <span style={nodeMetaStyle}>
          {object}
          {state !== null && status !== 'pending' ? ` · ${status}` : ''}
        </span>
        <span style={nodeBarTrackStyle}>
          <span style={nodeBarFillStyle(progressPct, color)} />
        </span>
      </span>
    </button>
  )
}

function MetricRows({ state }: { state: StageState | null }) {
  if (state === null) {
    return (
      <p style={vizHintStyle}>Click a stage on the left, or run the pipeline, to see stage detail.</p>
    )
  }
  const keys = Object.keys(state.metrics)
  return (
    <div style={{ marginTop: 'var(--sp-3, 12px)' }}>
      <div style={kvRowStyle}>
        <span style={kvKeyStyle}>stage</span>
        <span style={kvValueStyle}>
          {state.stage}{' '}
          <span style={chipStyle(STATUS_TOKEN[state.status])}>{state.status}</span>
        </span>
      </div>
      <div style={kvRowStyle}>
        <span style={kvKeyStyle}>currentObject</span>
        <span style={kvValueStyle}>{state.currentObject ?? '—'}</span>
      </div>
      {keys.map((k) => (
        <div key={k} style={kvRowStyle}>
          <span style={kvKeyStyle}>{k}</span>
          <span style={kvValueStyle}>{formatMetric(state.metrics[k] ?? '')}</span>
        </div>
      ))}
    </div>
  )
}

function AgentLog({ run }: { run: WorkflowRun | null }) {
  const entries = run === null ? [] : run.stages.filter((s) => s.status !== 'pending')
  if (entries.length === 0) {
    return (
      <EmptyStateCard
        headline="Nothing has run yet"
        body="Run the pipeline to watch each stage explain what it is doing, why, and the recommended next action."
        glyph="◷"
      />
    )
  }
  return (
    <div style={logListStyle} data-testid="wf-agent-log">
      {entries.map((st) => (
        <div key={st.stage} style={logEntryStyle(STATUS_TOKEN[st.status])}>
          <div style={logTopStyle}>
            <span aria-hidden="true" style={logDotStyle(STATUS_TOKEN[st.status])} />
            {st.description} · {st.status}
          </div>
          {st.agentExplanation !== null && <p style={logWhyStyle}>{st.agentExplanation}</p>}
          {st.warnings.map((w) => (
            <div key={w} style={logNoteStyle('var(--warn-400)')}>
              ⚠ {w}
            </div>
          ))}
          {st.errors.map((e) => (
            <div key={`${e.faultClass}:${e.message}`} style={logNoteStyle('var(--danger-400)')}>
              ✗ {e.faultClass}: {e.message}
            </div>
          ))}
          {st.nextAction !== null && <div style={logNextStyle}>→ {st.nextAction}</div>}
        </div>
      ))}
    </div>
  )
}

function WeaList({ run }: { run: WorkflowRun | null }) {
  if (run === null) {
    return <p style={vizHintStyle}>No warnings, errors, or artifacts yet.</p>
  }
  const items: { key: string; tone: string; text: string }[] = []
  for (const st of run.stages) {
    for (const w of st.warnings) items.push({ key: `w-${st.stage}-${w}`, tone: 'var(--warn-400)', text: `⚠ ${st.stage} · ${w}` })
    for (const e of st.errors)
      items.push({ key: `e-${st.stage}-${e.faultClass}`, tone: 'var(--danger-400)', text: `✗ ${st.stage} · ${e.faultClass}: ${e.message}` })
    const rf = st.artifacts.reportFile
    if (rf !== undefined) items.push({ key: `a-${st.stage}`, tone: 'var(--border-strong)', text: `📄 ${st.stage} · ${rf}` })
  }
  if (items.length === 0) {
    return <p style={vizHintStyle}>No warnings, errors, or artifacts.</p>
  }
  return (
    <div data-testid="wf-wea">
      {items.map((it) => (
        <div key={it.key} style={listItemStyle(it.tone)}>
          {it.text}
        </div>
      ))}
    </div>
  )
}

function WorkflowVizSvg({
  catalog,
  activeIdx,
  qualityActive,
}: {
  catalog: readonly StageCatalogEntry[]
  activeIdx: number
  qualityActive: boolean
}) {
  const has = (stage: string): boolean => stageReached(catalog, activeIdx, stage)
  const grid = meshGridLines()
  return (
    <div style={vizFrameStyle} data-testid="wf-viz">
      <svg viewBox={`0 0 ${VIZ_W} ${VIZ_H}`} style={{ width: '100%', display: 'block' }} role="img" aria-label="FEA specimen preview">
        {has(LAYER_STAGE.stress) ? (
          <>
            <defs>
              <radialGradient id="wf-stress" cx={`${HOLE.cx / VIZ_W}`} cy={`${HOLE.cy / VIZ_H}`} r="0.6">
                <stop offset="0" stopColor="#ff6b6b" />
                <stop offset="0.4" stopColor="#ffb454" />
                <stop offset="0.75" stopColor="#3ad29f" />
                <stop offset="1" stopColor="#2b6cb0" />
              </radialGradient>
            </defs>
            <path d={PLATE_PATH} fill="url(#wf-stress)" opacity="0.85" />
          </>
        ) : (
          <path d={PLATE_PATH} fill="#13212f" stroke="#2c4156" />
        )}

        {has(LAYER_STAGE.mesh) && (
          <g>
            {grid.vertical.map((x) => (
              <line key={`v${x}`} x1={x} y1="60" x2={x} y2="240" stroke="#2c4156" strokeWidth="0.5" opacity="0.5" />
            ))}
            {grid.horizontal.map((y) => (
              <line key={`h${y}`} x1="10" y1={y} x2="470" y2={y} stroke="#2c4156" strokeWidth="0.5" opacity="0.5" />
            ))}
          </g>
        )}

        <circle cx={HOLE.cx} cy={HOLE.cy} r={HOLE.r} fill="#0a0f15" stroke="#3a4d60" />

        {has(LAYER_STAGE.quality) && (
          <>
            <circle
              cx={HOLE.cx}
              cy={HOLE.cy}
              r={HOLE.r + 9}
              fill="none"
              stroke="#ffb454"
              strokeWidth="2.5"
              strokeDasharray="5 4"
              opacity={qualityActive ? 1 : 0.5}
            />
            <text x={HOLE.cx} y={HOLE.cy - HOLE.r - 16} textAnchor="middle" style={svgLabelStyle} fill="#ffb454">
              bracket_hole_region
            </text>
          </>
        )}

        {has(LAYER_STAGE.bc) && (
          <>
            <g>
              {bcHatchRows().map((y) => (
                <line key={`bc${y}`} x1="10" y1={y} x2="22" y2={y + 8} stroke="#5d9bff" strokeWidth="1.4" />
              ))}
            </g>
            <text x="8" y="54" style={svgLabelStyle} fill="#5d9bff">
              fixed
            </text>
          </>
        )}

        {has(LAYER_STAGE.load) && (
          <>
            <defs>
              <marker id="wf-ah" markerWidth="7" markerHeight="7" refX="3" refY="6" orient="auto">
                <path d="M0 0 L3 6 L6 0" fill="#3ad29f" />
              </marker>
            </defs>
            <g>
              {loadArrowColumns().map((x) => (
                <line key={`ld${x}`} x1={x} y1="30" x2={x} y2="56" stroke="#3ad29f" strokeWidth="1.6" markerEnd="url(#wf-ah)" />
              ))}
            </g>
            <text x="60" y="26" style={svgLabelStyle} fill="#3ad29f">
              5 kN
            </text>
          </>
        )}

        {has(LAYER_STAGE.deform) && (
          <path d={DEFORM_PATH} fill="none" stroke="#fff" strokeWidth="0.8" strokeDasharray="3 3" opacity="0.5" />
        )}

        {has(LAYER_STAGE.stress) && (
          <text x="40" y="280" style={svgLabelStyle} fill="#8b9bb0">
            von Mises (peak at hole edge)
          </text>
        )}
      </svg>
    </div>
  )
}

// --- styles (inline CSSProperties on warm-light tokens; house pattern) -------

const shellStyle: CSSProperties = { padding: 'var(--sp-4, 16px)' }
const headerRowStyle: CSSProperties = {
  display: 'flex',
  alignItems: 'flex-start',
  justifyContent: 'space-between',
  gap: 12,
  flexWrap: 'wrap',
}
const titleStyle: CSSProperties = { fontSize: 16, fontWeight: 700, color: 'var(--text-primary)' }
const subtitleStyle: CSSProperties = { fontSize: 12, color: 'var(--text-muted)', marginTop: 2 }
const controlsRowStyle: CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  gap: 10,
  flexWrap: 'wrap',
  margin: '14px 0',
}
const primaryButtonStyle: CSSProperties = {
  display: 'inline-flex',
  alignItems: 'center',
  gap: 6,
  background: 'var(--accent)',
  color: '#fff',
}
const ghostButtonStyle: CSSProperties = { display: 'inline-flex', alignItems: 'center', gap: 6 }
const controlLabelStyle: CSSProperties = {
  display: 'inline-flex',
  alignItems: 'center',
  gap: 6,
  fontSize: 12,
  color: 'var(--text-muted)',
}
const selectStyle: CSSProperties = {
  fontSize: 12.5,
  color: 'var(--text-primary)',
  background: 'var(--bg-surface)',
  border: '1px solid var(--border)',
  borderRadius: 7,
  padding: '5px 8px',
  maxWidth: 280,
}
const runErrorStyle: CSSProperties = {
  fontSize: 13,
  color: 'var(--danger-400)',
  background: 'rgba(197, 69, 59, 0.10)',
  border: '1px solid var(--danger-300)',
  borderRadius: 8,
  padding: '8px 12px',
  marginBottom: 12,
}
const gridStyle: CSSProperties = {
  display: 'grid',
  gridTemplateColumns: 'minmax(220px, 300px) 1fr minmax(240px, 320px)',
  gap: 13,
}
const bottomGridStyle: CSSProperties = {
  display: 'grid',
  gridTemplateColumns: '1.4fr 1fr',
  gap: 13,
  marginTop: 13,
}
const columnStyle: CSSProperties = {
  background: 'var(--bg-surface)',
  border: '1px solid var(--border)',
  borderRadius: 12,
  padding: 12,
  minWidth: 0,
}
const columnTitleStyle: CSSProperties = {
  margin: '0 0 10px',
  fontSize: 11,
  letterSpacing: '0.5px',
  textTransform: 'uppercase',
  color: 'var(--text-muted)',
  fontWeight: 600,
}

function badgeStyle(color: string): CSSProperties {
  return {
    fontFamily: 'var(--mono, ui-monospace, monospace)',
    fontSize: 11,
    padding: '3px 9px',
    borderRadius: 999,
    border: '1px solid var(--border)',
    color,
  }
}

function nodeStyle(selected: boolean): CSSProperties {
  return {
    display: 'flex',
    gap: 9,
    alignItems: 'flex-start',
    padding: '7px 8px',
    width: '100%',
    textAlign: 'left',
    borderRadius: 9,
    cursor: 'pointer',
    border: `1px solid ${selected ? 'var(--border-strong)' : 'transparent'}`,
    background: selected ? 'var(--bg-app, rgba(0,0,0,0.03))' : 'transparent',
  }
}
function nodeDotStyle(color: string, running: boolean): CSSProperties {
  return {
    width: 13,
    height: 13,
    borderRadius: '50%',
    border: `2px solid ${color}`,
    background: running ? color : 'transparent',
    flex: '0 0 auto',
    marginTop: 2,
  }
}
const nodeBodyStyle: CSSProperties = { flex: 1, minWidth: 0, display: 'flex', flexDirection: 'column' }
function nodeNameStyle(status: WorkflowStatus, color: string): CSSProperties {
  return { fontSize: 12.5, fontWeight: 600, color: status === 'pending' ? 'var(--text-primary)' : color }
}
const nodeMetaStyle: CSSProperties = {
  fontSize: 10.5,
  color: 'var(--text-muted)',
  fontFamily: 'var(--mono, ui-monospace, monospace)',
  overflow: 'hidden',
  textOverflow: 'ellipsis',
  whiteSpace: 'nowrap',
}
const nodeBarTrackStyle: CSSProperties = {
  height: 3,
  background: 'var(--border)',
  borderRadius: 2,
  marginTop: 4,
  overflow: 'hidden',
}
function nodeBarFillStyle(pct: number, color: string): CSSProperties {
  return { display: 'block', height: '100%', width: `${pct}%`, background: color, transition: 'width 0.3s' }
}

const vizFrameStyle: CSSProperties = {
  background: '#0a0f15',
  border: '1px solid var(--border)',
  borderRadius: 10,
  overflow: 'hidden',
}
const svgLabelStyle: CSSProperties = { fontSize: 10, fontFamily: 'var(--mono, ui-monospace, monospace)' }
const vizHintStyle: CSSProperties = {
  color: 'var(--text-muted)',
  fontSize: 12,
  fontStyle: 'italic',
  margin: '8px 0 0',
}

const kvRowStyle: CSSProperties = {
  display: 'flex',
  justifyContent: 'space-between',
  gap: 10,
  padding: '4px 0',
  borderBottom: '1px dashed var(--border)',
  fontSize: 12.5,
}
const kvKeyStyle: CSSProperties = { color: 'var(--text-muted)' }
const kvValueStyle: CSSProperties = { fontFamily: 'var(--mono, ui-monospace, monospace)' }
function chipStyle(color: string): CSSProperties {
  return {
    fontFamily: 'var(--mono, ui-monospace, monospace)',
    fontSize: 10,
    padding: '1px 6px',
    borderRadius: 5,
    border: `1px solid ${color}`,
    color,
  }
}

const logListStyle: CSSProperties = { display: 'flex', flexDirection: 'column', gap: 9, maxHeight: 560, overflow: 'auto' }
function logEntryStyle(color: string): CSSProperties {
  return { border: `1px solid ${color}`, borderRadius: 9, padding: '8px 10px', background: 'var(--bg-surface)' }
}
const logTopStyle: CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  gap: 7,
  fontSize: 11,
  color: 'var(--text-secondary)',
  fontFamily: 'var(--mono, ui-monospace, monospace)',
}
function logDotStyle(color: string): CSSProperties {
  return { width: 8, height: 8, borderRadius: '50%', background: color, display: 'inline-block' }
}
const logWhyStyle: CSSProperties = { margin: '5px 0 0', fontSize: 12.5, color: 'var(--text-primary)' }
function logNoteStyle(color: string): CSSProperties {
  return { marginTop: 6, fontSize: 11.5, color, borderLeft: `2px solid ${color}`, paddingLeft: 8 }
}
const logNextStyle: CSSProperties = {
  marginTop: 6,
  fontSize: 11.5,
  color: 'var(--text-muted)',
  borderLeft: '2px solid var(--border)',
  paddingLeft: 8,
}

const timelineStyle: CSSProperties = { display: 'flex', gap: 4, flexWrap: 'wrap' }
function timelinePillStyle(status: WorkflowStatus): CSSProperties {
  const color = status === 'pending' ? 'var(--text-muted)' : STATUS_TOKEN[status]
  return {
    fontFamily: 'var(--mono, ui-monospace, monospace)',
    fontSize: 9.5,
    padding: '3px 5px',
    borderRadius: 5,
    border: `1px solid ${status === 'pending' ? 'var(--border)' : color}`,
    color,
  }
}
function listItemStyle(tone: string): CSSProperties {
  return {
    fontSize: 12,
    padding: '5px 8px',
    borderRadius: 7,
    background: 'var(--bg-surface)',
    marginBottom: 5,
    borderLeft: `2px solid ${tone}`,
  }
}
