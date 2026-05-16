// FM-04a Phase 4 E — Case completeness client.
//
// Tier 1 engineering candidate; not signed validation; not benchmark agreement.
//
// Typed fetch helper for `/api/v1/case-completeness/<case-id>` plus a
// snake-to-camel parser. The score is evidence-presence only; the
// rendered output preserves the FM-04b blockers list.

export interface CompletenessBreakdownEntry {
  label: string
  pointsAwarded: number
  pointsMax: number
  evidenceStatus: string
  notes: string | null
}

export interface CaseCompletenessScore {
  schemaVersion: string
  rubricVersion: string
  caseId: string
  generatedAtUtc: string
  claimTier: string
  claimBoundary: string
  score: number
  scoreMax: number
  breakdown: CompletenessBreakdownEntry[]
  missingEvidence: string[]
  tier2BlockersRemaining: string[]
  claimImpact: string
}

interface RawBreakdownEntry {
  label?: string
  points_awarded?: number
  points_max?: number
  evidence_status?: string
  notes?: string | null
}

interface RawCaseCompletenessScore {
  schema_version?: string
  rubric_version?: string
  case_id?: string
  generated_at_utc?: string
  claim_tier?: string
  claim_boundary?: string
  score?: number
  score_max?: number
  breakdown?: RawBreakdownEntry[]
  missing_evidence?: string[]
  tier2_blockers_remaining?: string[]
  claim_impact?: string
}

function parseBreakdownEntry(
  raw: RawBreakdownEntry | null | undefined,
): CompletenessBreakdownEntry | null {
  if (!raw || typeof raw !== 'object') return null
  if (typeof raw.label !== 'string') return null
  return {
    label: raw.label,
    pointsAwarded: raw.points_awarded ?? 0,
    pointsMax: raw.points_max ?? 0,
    evidenceStatus: raw.evidence_status ?? 'unknown',
    notes: raw.notes ?? null,
  }
}

export function parseCaseCompletenessScore(
  raw: RawCaseCompletenessScore | null | undefined,
): CaseCompletenessScore | null {
  if (!raw || typeof raw !== 'object') return null
  if (typeof raw.case_id !== 'string') return null
  return {
    schemaVersion: raw.schema_version ?? '',
    rubricVersion: raw.rubric_version ?? '',
    caseId: raw.case_id,
    generatedAtUtc: raw.generated_at_utc ?? '',
    claimTier: raw.claim_tier ?? '',
    claimBoundary: raw.claim_boundary ?? '',
    score: raw.score ?? 0,
    scoreMax: raw.score_max ?? 100,
    breakdown: (raw.breakdown ?? [])
      .map(parseBreakdownEntry)
      .filter((e): e is CompletenessBreakdownEntry => e !== null),
    missingEvidence: raw.missing_evidence ?? [],
    tier2BlockersRemaining: raw.tier2_blockers_remaining ?? [],
    claimImpact: raw.claim_impact ?? '',
  }
}

export interface CaseCompletenessFetchResult {
  score: CaseCompletenessScore | null
  source: 'live' | 'fallback'
  error?: string
}

export async function fetchCaseCompleteness(
  apiBase: string,
  caseId: string,
  signal?: AbortSignal,
): Promise<CaseCompletenessFetchResult> {
  const url = `${apiBase.replace(/\/$/, '')}/case-completeness/${encodeURIComponent(caseId)}`
  try {
    const res = await fetch(url, { signal })
    if (!res.ok) {
      throw new Error(`case-completeness endpoint returned ${res.status}`)
    }
    const raw = (await res.json()) as RawCaseCompletenessScore
    const parsed = parseCaseCompletenessScore(raw)
    if (!parsed) {
      throw new Error('case-completeness payload missing case_id')
    }
    return { score: parsed, source: 'live' }
  } catch (err) {
    return {
      score: null,
      source: 'fallback',
      error: err instanceof Error ? err.message : String(err),
    }
  }
}
