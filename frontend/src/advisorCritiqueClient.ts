// FM-04a Phase 11 E — AdvisorCritique typed client.
//
// Tier 1 engineering candidate; not signed validation; not benchmark agreement.
//
// The frontend SSOTs below MUST match the backend tuples in
// `backend/app/services/reporting/advisor_critique.py`:
//   * `ADVISOR_STATUS_TUPLE` — closed enum of `advisor_status` values.
//   * `FOUR_QUESTION_GATE_KEYS` — the four-question gate keys every
//     payload answers; rendered as a 4-tick checklist in the panel.
//   * `ADVISOR_FORBIDDEN_TOKENS` — extended Tier 1 forbidden list;
//     used by the client-side preview audit to refuse rendering any
//     entry that contains a positive-claim verb outside `not <claim>`
//     form (defense in depth on top of the backend audit).
//
// Defensive `parseAdvisorStatus` falls back to `'unknown'` for any
// value the backend introduces in a future MINOR bump but the
// frontend has not yet been updated to match (Phase 11 anti-gaming
// guard X:-2). The panel renders unknown-status rows in a neutral
// state — it does NOT silently surface an "online" badge.

export const ADVISOR_STATUS_TUPLE = ['online', 'offline', 'stub'] as const
export type AdvisorStatus = (typeof ADVISOR_STATUS_TUPLE)[number] | 'unknown'

export const FOUR_QUESTION_GATE_KEYS = [
  'llm_offline_ok',
  'artifacts_user_owned',
  'trustgate_explains',
  'advisor_only',
] as const
export type FourQuestionGateKey = (typeof FOUR_QUESTION_GATE_KEYS)[number]

export const ADVISOR_FORBIDDEN_TOKENS = [
  // Base Tier 1 list.
  'validated against',
  'perforation completed',
  'bullet-through-steel complete',
  'validated physics',
  // Phase 11 B extension — advisor-specific positive verbs.
  'production ready',
  'certified',
  'approved for service',
  'asme compliant', // case-folded
  'signed off',
] as const

export interface AdvisorCritique {
  schemaVersion: string
  caseId: string
  snapshotLabel: string
  advisorStatus: AdvisorStatus
  advisorBackend: string
  generatedAtUtc: string
  fourQuestionGate: Partial<Record<FourQuestionGateKey, boolean>>
  meshQualityConcerns: string[]
  boundaryConditionQuestions: string[]
  failureModesToConsider: string[]
  unhandledLoadCases: string[]
  degradeReason: string | null
  claimTier: string
  claimBoundary: string
  claimImpact: string
}

interface RawCritique {
  schema_version?: string
  case_id?: string
  snapshot_label?: string
  advisor_status?: string
  advisor_backend?: string
  generated_at_utc?: string
  four_question_gate?: Record<string, unknown>
  mesh_quality_concerns?: unknown[]
  boundary_condition_questions?: unknown[]
  failure_modes_to_consider?: unknown[]
  unhandled_load_cases?: unknown[]
  degrade_reason?: string | null
  claim_tier?: string
  claim_boundary?: string
  claim_impact?: string
}

export function parseAdvisorStatus(raw: string | undefined): AdvisorStatus {
  if (raw === undefined) return 'unknown'
  if ((ADVISOR_STATUS_TUPLE as readonly string[]).includes(raw)) {
    return raw as AdvisorStatus
  }
  return 'unknown'
}

function _parseStringList(raw: unknown): string[] {
  if (!Array.isArray(raw)) return []
  return raw.filter((item): item is string => typeof item === 'string')
}

function _parseGate(
  raw: Record<string, unknown> | undefined,
): Partial<Record<FourQuestionGateKey, boolean>> {
  const out: Partial<Record<FourQuestionGateKey, boolean>> = {}
  if (!raw || typeof raw !== 'object') return out
  for (const key of FOUR_QUESTION_GATE_KEYS) {
    const value = raw[key]
    if (typeof value === 'boolean') {
      out[key] = value
    }
  }
  return out
}

export function parseAdvisorCritique(
  raw: RawCritique | null | undefined,
): AdvisorCritique | null {
  if (!raw || typeof raw !== 'object') return null
  if (typeof raw.case_id !== 'string') return null
  if (typeof raw.snapshot_label !== 'string') return null
  return {
    schemaVersion: raw.schema_version ?? '',
    caseId: raw.case_id,
    snapshotLabel: raw.snapshot_label,
    advisorStatus: parseAdvisorStatus(raw.advisor_status),
    advisorBackend: raw.advisor_backend ?? '',
    generatedAtUtc: raw.generated_at_utc ?? '',
    fourQuestionGate: _parseGate(raw.four_question_gate),
    meshQualityConcerns: _parseStringList(raw.mesh_quality_concerns),
    boundaryConditionQuestions: _parseStringList(raw.boundary_condition_questions),
    failureModesToConsider: _parseStringList(raw.failure_modes_to_consider),
    unhandledLoadCases: _parseStringList(raw.unhandled_load_cases),
    degradeReason: raw.degrade_reason ?? null,
    claimTier: raw.claim_tier ?? '',
    claimBoundary: raw.claim_boundary ?? '',
    claimImpact: raw.claim_impact ?? '',
  }
}

/**
 * Client-side preview audit. Refuses to render any string that contains
 * an ADVISOR_FORBIDDEN_TOKENS entry outside the `not <claim>` disclaimer
 * form. Defense in depth: the backend audit already refused such
 * envelopes, but if the response was tampered with (man-in-the-middle,
 * a proxy injecting copy, etc.) the panel still refuses to display the
 * tainted entry. Returns `true` when SAFE to render.
 */
export function isAdvisorEntrySafe(entry: string): boolean {
  const haystack = entry.toLowerCase()
  for (const token of ADVISOR_FORBIDDEN_TOKENS) {
    let start = 0
    while (true) {
      const idx = haystack.indexOf(token, start)
      if (idx === -1) break
      const prefix = haystack.slice(Math.max(0, idx - 4), idx)
      if (!prefix.endsWith('not ')) {
        return false
      }
      start = idx + token.length
    }
  }
  return true
}

export interface AdvisorFetchResult {
  critique: AdvisorCritique | null
  source: 'live' | 'fallback'
  error?: string
}

export async function fetchAdvisorCritique(
  apiBase: string,
  caseId: string,
  snapshotLabel: string,
  signal?: AbortSignal,
): Promise<AdvisorFetchResult> {
  const url =
    `${apiBase.replace(/\/$/, '')}/advisor-critique/${encodeURIComponent(caseId)}` +
    `?snapshot=${encodeURIComponent(snapshotLabel)}`
  try {
    const res = await fetch(url, { signal })
    if (!res.ok) {
      throw new Error(`advisor-critique endpoint returned ${res.status}`)
    }
    const raw = (await res.json()) as RawCritique
    const parsed = parseAdvisorCritique(raw)
    if (!parsed) {
      throw new Error('advisor-critique payload is malformed')
    }
    return { critique: parsed, source: 'live' }
  } catch (err) {
    return {
      critique: null,
      source: 'fallback',
      error: err instanceof Error ? err.message : 'unknown error',
    }
  }
}
