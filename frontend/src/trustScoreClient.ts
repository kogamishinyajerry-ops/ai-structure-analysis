// FM-04a Phase 6 B — Trust score client.
//
// Tier 1 engineering candidate; not signed validation; not benchmark agreement.
//
// Typed fetch helper for `/api/v1/trust-score/<case-id>`. Surfaces both
// schemaVersion AND formulaVersion on the parsed payload. The formula
// version is separate from the schema version because a reviewer
// comparing two trust scores needs to know whether the delta came
// from a formula rebalance or a real evidence change.

export interface TrustScoreBreakdownEntry {
  axis: string
  weight: number
  rawScore: number
  weighted: number
  rationale: string
}

export interface TrustScore {
  schemaVersion: string
  formulaVersion: string
  caseId: string
  generatedAtUtc: string
  claimTier: string
  claimBoundary: string
  trustScore: number
  trustScoreMax: number
  breakdown: TrustScoreBreakdownEntry[]
  tier2BlockersRemaining: string[]
  claimImpact: string
}

interface RawBreakdownEntry {
  axis?: string
  weight?: number
  raw_score?: number
  weighted?: number
  rationale?: string
}

interface RawTrustScore {
  schema_version?: string
  formula_version?: string
  case_id?: string
  generated_at_utc?: string
  claim_tier?: string
  claim_boundary?: string
  trust_score?: number
  trust_score_max?: number
  breakdown?: RawBreakdownEntry[]
  tier2_blockers_remaining?: string[]
  claim_impact?: string
}

function parseBreakdownEntry(
  raw: RawBreakdownEntry | null | undefined,
): TrustScoreBreakdownEntry | null {
  if (!raw || typeof raw !== 'object') return null
  if (typeof raw.axis !== 'string') return null
  return {
    axis: raw.axis,
    weight: raw.weight ?? 0,
    rawScore: raw.raw_score ?? 0,
    weighted: raw.weighted ?? 0,
    rationale: raw.rationale ?? '',
  }
}

export function parseTrustScore(
  raw: RawTrustScore | null | undefined,
): TrustScore | null {
  if (!raw || typeof raw !== 'object') return null
  if (typeof raw.case_id !== 'string') return null
  return {
    schemaVersion: raw.schema_version ?? '',
    formulaVersion: raw.formula_version ?? '',
    caseId: raw.case_id,
    generatedAtUtc: raw.generated_at_utc ?? '',
    claimTier: raw.claim_tier ?? '',
    claimBoundary: raw.claim_boundary ?? '',
    trustScore: raw.trust_score ?? 0,
    trustScoreMax: raw.trust_score_max ?? 100,
    breakdown: (raw.breakdown ?? [])
      .map(parseBreakdownEntry)
      .filter((e): e is TrustScoreBreakdownEntry => e !== null),
    tier2BlockersRemaining: raw.tier2_blockers_remaining ?? [],
    claimImpact: raw.claim_impact ?? '',
  }
}

export interface TrustScoreFetchResult {
  trustScore: TrustScore | null
  source: 'live' | 'fallback'
  error?: string
}

export async function fetchTrustScore(
  apiBase: string,
  caseId: string,
  signal?: AbortSignal,
): Promise<TrustScoreFetchResult> {
  const url = `${apiBase.replace(/\/$/, '')}/trust-score/${encodeURIComponent(caseId)}`
  try {
    const res = await fetch(url, { signal })
    if (!res.ok) {
      throw new Error(`trust-score endpoint returned ${res.status}`)
    }
    const raw = (await res.json()) as RawTrustScore
    const parsed = parseTrustScore(raw)
    if (!parsed) {
      throw new Error('trust-score payload is malformed')
    }
    return { trustScore: parsed, source: 'live' }
  } catch (err) {
    return {
      trustScore: null,
      source: 'fallback',
      error: err instanceof Error ? err.message : 'unknown error',
    }
  }
}

// Tone breakpoints exposed as named constants (anti-magic-number guard
// for Phase 6 D: -3 if any weight/threshold is inline-magic-numbered).
export const TRUST_TONE_ACCENT_THRESHOLD = 80
export const TRUST_TONE_WARNING_THRESHOLD = 50

export type TrustTone = 'accent' | 'warning' | 'danger' | 'muted'

export function trustTone(score: number | null): TrustTone {
  if (score === null) return 'muted'
  if (score >= TRUST_TONE_ACCENT_THRESHOLD) return 'accent'
  if (score >= TRUST_TONE_WARNING_THRESHOLD) return 'warning'
  return 'danger'
}
