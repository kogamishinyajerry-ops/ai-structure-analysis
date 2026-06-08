// FM-04a M3.5 — Trigger.dev realtime trigger client.
//
// The realtime path (vs the poll-only path in workflowClient.ts) triggers the
// pipeline through the thin Node trigger server (trigger/src/triggerServer.ts),
// which is the ONLY place the Trigger.dev SECRET key lives and the only thing
// that can mint a run-scoped public access token. The browser then feeds that
// token to useRealtimeRun() to stream the orchestrator run live. The Python
// backend can NOT mint this token (its REST trigger returns only a run id), so
// realtime always goes through this Node hop. Per-stage StageState detail still
// comes from the Python backend (workflowClient.fetchWorkflowRun) — the realtime
// stream is the live "tick" that says when to refresh it.
//
// Tier 1 / Tier 2 engineering candidate; not signed validation; not
// benchmark agreement.

import type { TriggerWorkflowOptions } from './workflowClient'

export interface RealtimeTrigger {
  /** The Python-side run id the Monitor polls for per-stage detail. */
  readonly feaRunId: string
  /** The Trigger.dev orchestrator run id useRealtimeRun subscribes to. */
  readonly orchRunId: string
  /** Run-scoped public access token (read-only) for the browser subscription. */
  readonly publicAccessToken: string
}

export interface RealtimeTriggerResult {
  readonly trigger: RealtimeTrigger | null
  readonly source: 'live' | 'fallback'
  readonly error?: string
}

const trimBase = (base: string): string => base.replace(/\/$/, '')

function asString(v: unknown): string | null {
  return typeof v === 'string' ? v : null
}

/**
 * POST the Node trigger server's /trigger-pipeline. Returns a defensive result:
 * a null trigger (with `error`) lets the caller gracefully fall back to the
 * poll-only path when the Node layer is not running.
 */
export async function triggerRealtimePipeline(
  triggerServerBase: string,
  opts: TriggerWorkflowOptions = {},
  signal?: AbortSignal,
): Promise<RealtimeTriggerResult> {
  try {
    const res = await fetch(`${trimBase(triggerServerBase)}/trigger-pipeline`, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ failAtStage: opts.failAtStage ?? null }),
      signal,
    })
    if (!res.ok) throw new Error(`trigger-pipeline returned ${res.status}`)
    const raw = (await res.json()) as Record<string, unknown>
    const feaRunId = asString(raw.feaRunId)
    const orchRunId = asString(raw.orchRunId)
    const publicAccessToken = asString(raw.publicAccessToken)
    if (feaRunId === null || orchRunId === null || publicAccessToken === null) {
      throw new Error('trigger-pipeline response missing feaRunId/orchRunId/publicAccessToken')
    }
    return { trigger: { feaRunId, orchRunId, publicAccessToken }, source: 'live' }
  } catch (err) {
    return { trigger: null, source: 'fallback', error: err instanceof Error ? err.message : String(err) }
  }
}

// Trigger.dev RunStatus values at which the orchestrator run is finished, so the
// realtime subscription should settle (clear busy, stop). Mirrors the SDK's
// terminal statuses; unknown future statuses are treated as non-terminal.
const ORCH_TERMINAL_STATUSES: ReadonlySet<string> = new Set([
  'COMPLETED',
  'FAILED',
  'CANCELED',
  'CRASHED',
  'TIMED_OUT',
  'EXPIRED',
  'INTERRUPTED',
  'SYSTEM_FAILURE',
])

export function isOrchTerminal(status: string | undefined): boolean {
  return status !== undefined && ORCH_TERMINAL_STATUSES.has(status)
}

function asMetaRecord(metadata: unknown): Record<string, unknown> {
  return typeof metadata === 'object' && metadata !== null ? (metadata as Record<string, unknown>) : {}
}

/** Defensive read of a numeric metadata field (e.g. completedStages). */
export function orchMetaNumber(metadata: unknown, key: string): number {
  const v = asMetaRecord(metadata)[key]
  return typeof v === 'number' ? v : 0
}

/** Defensive read of a string metadata field (e.g. currentStage, feaRunId). */
export function orchMetaString(metadata: unknown, key: string): string | null {
  const v = asMetaRecord(metadata)[key]
  return typeof v === 'string' ? v : null
}
