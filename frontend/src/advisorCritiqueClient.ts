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
  /**
   * Phase 13 A — structured suppression markers for advisor content
   * that contained a forbidden positive claim. Each entry has the
   * format `refused: <token>` (the verbatim forbidden token from
   * ADVISOR_FORBIDDEN_TOKENS). Back-compat: defaults to empty array
   * for pre-1.1.0 payloads or payloads that omit the field.
   */
  refusedClaims: string[]
}

/**
 * Phase 13 A SSOT: the marker prefix that distinguishes a refused-claim
 * marker from advisor content. Pinned by frontend vitest.
 */
export const REFUSED_CLAIM_MARKER_PREFIX = 'refused: '

/**
 * Phase 13 A render cap: the panel shows at most this many refused
 * markers before truncating with a "... N more" indicator. Independent
 * of MAX_ITEMS_PER_AXIS to keep the suppression history visible even
 * if backend caps grow.
 */
export const REFUSED_CLAIMS_MAX_ITEMS = 24

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
  // Phase 13 A — optional in pre-1.1.0 payloads; required in 1.1.0+.
  refused_claims?: unknown[]
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
    refusedClaims: _parseRefusedClaims(raw.refused_claims),
  }
}

/**
 * Phase 13 A — parse the refused_claims list defensively. Only strings
 * that match EXACTLY `refused: <token>` where `<token>` ∈
 * ADVISOR_FORBIDDEN_TOKENS are kept; everything else (numbers, objects,
 * non-marker strings, marker-prefix strings whose suffix is NOT a
 * close-set forbidden token) is discarded.
 *
 * This is the X:-2 anti-promotion guard for the suppression-history
 * surface. Tightened in Phase 13 B (slice-A TAA HIGH finding): a
 * tampered/MITM payload such as `"refused: production ready for
 * service deployment"` (a forbidden token followed by smuggled
 * positive-claim copy) used to slip through the prefix-only check and
 * render verbatim inside `_RefusedClaimsSection` (which does NOT apply
 * `isAdvisorEntrySafe` because the markers are reviewer-intended to
 * reveal *which* forbidden token tripped, not to relay advisor copy).
 * Close-set suffix validation closes that injection vector.
 *
 * Case folding mirrors the backend: tokens in ADVISOR_FORBIDDEN_TOKENS
 * are stored lower-case (`"asme compliant"` not `"ASME compliant"`),
 * and the backend marker emit path lower-cases the token before
 * embedding (`backend/app/services/reporting/advisor_critique.py`
 * `_audit_and_collect_refused`). The frontend folds the suffix for the
 * same reason.
 */
function _parseRefusedClaims(raw: unknown): string[] {
  if (!Array.isArray(raw)) return []
  const closedSet: ReadonlySet<string> = new Set(ADVISOR_FORBIDDEN_TOKENS)
  const out: string[] = []
  for (const item of raw) {
    if (typeof item !== 'string') continue
    if (!item.startsWith(REFUSED_CLAIM_MARKER_PREFIX)) continue
    const suffix = item.slice(REFUSED_CLAIM_MARKER_PREFIX.length).toLowerCase()
    if (!closedSet.has(suffix)) continue
    out.push(item)
  }
  return out
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
