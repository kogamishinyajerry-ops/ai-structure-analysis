// FM-04a M3 — Agentic FEA Workflow Runtime client (read-only Monitor).
//
// Mirrors the house *Client.ts pattern (see convergenceStudyClient): camelCase
// typed interfaces, defensive parsers, fetch fns returning { ..., source,
// error? }. The backend wire format is already camelCase (pydantic
// model_dump(by_alias=True)), so parsing is a defensive pass-through. This is
// the M2 contract's read side — POLL-only, no Trigger.dev realtime SDK; the
// orchRunId/publicAccessToken fields are carried as a seam for a future
// useRealtimeRun() once a real token is minted at the Node trigger layer.
//
// Tier 1 / Tier 2 engineering candidate; not signed validation; not
// benchmark agreement.

export type WorkflowStatus = 'pending' | 'running' | 'success' | 'warning' | 'failed'

/** Statuses at which a run/stage is finished and polling can stop. */
export const TERMINAL_STATUSES: readonly WorkflowStatus[] = ['success', 'warning', 'failed']

export function isTerminal(status: WorkflowStatus): boolean {
  return TERMINAL_STATUSES.includes(status)
}

// ADR-028 D2 — machine-checkable provenance of a stage's agentExplanation /
// nextAction. The backend emits it as first-class wire data
// (schemas/workflow_state.py StageState.provenance); the UI MUST surface it and
// never infer it. Default `scripted_demo` = synthetic demo prose, NOT agent output.
export type StageProvenance = 'scripted_demo' | 'deterministic_agent' | 'llm_agent'

export const PROVENANCE_LABEL: Readonly<Record<StageProvenance, string>> = {
  scripted_demo: 'scripted demo',
  deterministic_agent: 'deterministic agent',
  llm_agent: 'LLM agent',
}

export interface StageError {
  readonly faultClass: string
  readonly message: string
  readonly detail?: string
}

export interface StageArtifacts {
  readonly geometryPreview?: string
  readonly meshPreview?: string
  readonly resultPreview?: string
  readonly logFile?: string
  readonly reportFile?: string
}

export interface StageState {
  readonly stage: string
  readonly status: WorkflowStatus
  readonly progress: number
  readonly currentObject: string | null
  readonly description: string
  readonly metrics: Readonly<Record<string, number | string>>
  readonly warnings: readonly string[]
  readonly errors: readonly StageError[]
  readonly artifacts: StageArtifacts
  readonly agentExplanation: string | null
  readonly nextAction: string | null
  readonly provenance: StageProvenance
}

export interface WorkflowRun {
  readonly runId: string
  readonly label: string | null
  readonly status: WorkflowStatus
  readonly startedAt: string | null
  readonly finishedAt: string | null
  readonly failAtStage: string | null
  readonly currentStage: string | null
  readonly stages: readonly StageState[]
  // M2 external-mode seam — null in the mock/M1 path; a real public token is
  // only ever minted by the Node trigger layer (never the Python backend).
  readonly orchRunId: string | null
  readonly publicAccessToken: string | null
}

export interface StageCatalogEntry {
  readonly order: number
  readonly stage: string
  readonly wsStage: string
  readonly currentObject: string | null
  readonly description: string
}

function asString(v: unknown): string | null {
  return typeof v === 'string' ? v : null
}

// The backend defaults agentExplanation/nextAction to '' (not null), so an empty
// string means "absent" — collapse it to null so the UI's null checks suppress
// blank paragraphs / empty arrow rows (Codex M3 P2).
function asNonEmptyString(v: unknown): string | null {
  return typeof v === 'string' && v !== '' ? v : null
}

function asRecord(v: unknown): Record<string, unknown> {
  return typeof v === 'object' && v !== null ? (v as Record<string, unknown>) : {}
}

function asStatus(v: unknown): WorkflowStatus {
  return v === 'running' || v === 'success' || v === 'warning' || v === 'failed' ? v : 'pending'
}

// Defensive: an unknown/missing provenance collapses to scripted_demo so an
// un-wired or malformed stage is never silently shown as agent-driven (ADR-028 D2).
function asProvenance(v: unknown): StageProvenance {
  return v === 'deterministic_agent' || v === 'llm_agent' ? v : 'scripted_demo'
}

function parseError(raw: unknown): StageError {
  const o = asRecord(raw)
  const detail = asString(o.detail)
  return {
    faultClass: asString(o.faultClass) ?? 'unknown',
    message: asString(o.message) ?? '',
    ...(detail !== null ? { detail } : {}),
  }
}

function parseArtifacts(raw: unknown): StageArtifacts {
  const o = asRecord(raw)
  const pick = (k: string): string | undefined => (typeof o[k] === 'string' ? (o[k] as string) : undefined)
  return {
    geometryPreview: pick('geometryPreview'),
    meshPreview: pick('meshPreview'),
    resultPreview: pick('resultPreview'),
    logFile: pick('logFile'),
    reportFile: pick('reportFile'),
  }
}

export function parseStageState(raw: unknown): StageState {
  const o = asRecord(raw)
  const rawMetrics = asRecord(o.metrics)
  const metrics: Record<string, number | string> = {}
  for (const k of Object.keys(rawMetrics)) {
    const val = rawMetrics[k]
    if (typeof val === 'number' || typeof val === 'string') metrics[k] = val
  }
  return {
    stage: asString(o.stage) ?? '',
    status: asStatus(o.status),
    progress: typeof o.progress === 'number' ? o.progress : 0,
    currentObject: asString(o.currentObject),
    description: asString(o.description) ?? '',
    metrics,
    warnings: Array.isArray(o.warnings) ? o.warnings.filter((w): w is string => typeof w === 'string') : [],
    errors: Array.isArray(o.errors) ? o.errors.map(parseError) : [],
    artifacts: parseArtifacts(o.artifacts),
    agentExplanation: asNonEmptyString(o.agentExplanation),
    nextAction: asNonEmptyString(o.nextAction),
    provenance: asProvenance(o.provenance),
  }
}

export interface ProvenanceCoverage {
  readonly deterministic: number
  readonly llm: number
  readonly scripted: number
  readonly total: number
  /** stages whose explanation came from a live agent node (deterministic + llm). */
  readonly agentDriven: number
}

// ADR-028 D2 run-level coverage qualifier: count each stage by provenance so the
// Monitor can honestly disclose "N of total agent-driven" and never imply more.
// Deterministic and LLM are kept DISTINCT (the enum distinction is the point of D2);
// they are summed only into `agentDriven`, never blurred in the per-class counts.
export function provenanceCoverage(stages: readonly StageState[]): ProvenanceCoverage {
  let deterministic = 0
  let llm = 0
  for (const s of stages) {
    if (s.provenance === 'deterministic_agent') deterministic += 1
    else if (s.provenance === 'llm_agent') llm += 1
  }
  const total = stages.length
  return {
    deterministic,
    llm,
    scripted: total - deterministic - llm,
    total,
    agentDriven: deterministic + llm,
  }
}

export function parseWorkflowRun(raw: unknown): WorkflowRun | null {
  const o = asRecord(raw)
  const runId = asString(o.runId)
  if (runId === null) return null
  return {
    runId,
    label: asString(o.label),
    status: asStatus(o.status),
    startedAt: asString(o.startedAt),
    finishedAt: asString(o.finishedAt),
    failAtStage: asString(o.failAtStage),
    currentStage: asString(o.currentStage),
    stages: Array.isArray(o.stages) ? o.stages.map(parseStageState) : [],
    orchRunId: asString(o.orchRunId),
    publicAccessToken: asString(o.publicAccessToken),
  }
}

function parseCatalogEntry(raw: unknown): StageCatalogEntry {
  const o = asRecord(raw)
  return {
    order: typeof o.order === 'number' ? o.order : 0,
    stage: asString(o.stage) ?? '',
    wsStage: asString(o.wsStage) ?? '',
    currentObject: asString(o.currentObject),
    description: asString(o.description) ?? '',
  }
}

export interface StageCatalogResult {
  readonly stages: readonly StageCatalogEntry[]
  readonly source: 'live' | 'fallback'
  readonly error?: string
}

export interface WorkflowRunResult {
  readonly run: WorkflowRun | null
  readonly source: 'live' | 'fallback'
  readonly error?: string
}

const trimBase = (apiBase: string): string => apiBase.replace(/\/$/, '')

export async function fetchWorkflowStages(apiBase: string, signal?: AbortSignal): Promise<StageCatalogResult> {
  try {
    const res = await fetch(`${trimBase(apiBase)}/workflow/stages`, { signal })
    if (!res.ok) throw new Error(`workflow/stages returned ${res.status}`)
    const raw = asRecord(await res.json())
    const stages = Array.isArray(raw.stages) ? raw.stages.map(parseCatalogEntry) : []
    return { stages, source: 'live' }
  } catch (err) {
    return { stages: [], source: 'fallback', error: err instanceof Error ? err.message : String(err) }
  }
}

export async function fetchWorkflowRun(
  apiBase: string,
  runId: string,
  signal?: AbortSignal,
): Promise<WorkflowRunResult> {
  try {
    const res = await fetch(`${trimBase(apiBase)}/workflow/runs/${encodeURIComponent(runId)}`, { signal })
    if (!res.ok) throw new Error(`workflow/runs returned ${res.status}`)
    const run = parseWorkflowRun(await res.json())
    if (run === null) throw new Error('workflow run payload missing runId')
    return { run, source: 'live' }
  } catch (err) {
    return { run: null, source: 'fallback', error: err instanceof Error ? err.message : String(err) }
  }
}

export interface TriggerWorkflowOptions {
  readonly label?: string
  // ADR-028 P1 — the genuine NL analysis intent (distinct from the display label).
  // Only a real request drives the project_intake agent node; absent it the stage
  // stays scripted_demo. Sent as camelCase `userRequest` (backend populate_by_name).
  readonly userRequest?: string | null
  readonly failAtStage?: string | null
}

export async function triggerWorkflow(
  apiBase: string,
  opts: TriggerWorkflowOptions = {},
  signal?: AbortSignal,
): Promise<WorkflowRunResult> {
  try {
    const res = await fetch(`${trimBase(apiBase)}/workflow/trigger`, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({
        label: opts.label ?? 'monitor',
        userRequest: opts.userRequest ?? null,
        failAtStage: opts.failAtStage ?? null,
      }),
      signal,
    })
    if (!res.ok) throw new Error(`workflow/trigger returned ${res.status}`)
    const run = parseWorkflowRun(await res.json())
    if (run === null) throw new Error('workflow trigger payload missing runId')
    return { run, source: 'live' }
  } catch (err) {
    return { run: null, source: 'fallback', error: err instanceof Error ? err.message : String(err) }
  }
}
