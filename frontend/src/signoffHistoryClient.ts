// FM-04a Phase 8 B — Signoff history client.
//
// Tier 1 engineering candidate; not signed validation; not benchmark agreement.
//
// Typed fetch helper for `/api/v1/signoff-history/<case-id>`. Preserves
// schemaVersion + verdict whitelist + Tier 1 disclaimer trio. The verdict
// whitelist is re-exported so any dropdown UI imports the source of truth
// instead of duplicating the list (Phase 8 anti-gaming guard X: -2).

// Keep in lock-step with backend SUPPORTED_SIGNOFF_VERDICTS. The 4-verdict
// whitelist deliberately excludes every Tier 2 promotion verb (Phase 8
// anti-gaming guard C: -10).
export const SUPPORTED_SIGNOFF_VERDICTS = [
  'watching',
  'needs_more_evidence',
  'needs_more_convergence',
  'blocked_pending_input',
] as const

export type SignoffVerdict = (typeof SUPPORTED_SIGNOFF_VERDICTS)[number]

export interface SignoffRecord {
  schemaVersion: string
  caseId: string
  reviewer: string
  verdict: SignoffVerdict
  signoffUtc: string
  notes: string
  claimTier: string
  claimBoundary: string
  claimImpact: string
}

export interface SignoffHistoryReport {
  schemaVersion: string
  caseId: string
  claimTier: string
  claimBoundary: string
  generatedAtUtc: string
  recordCount: number
  records: SignoffRecord[]
  claimImpact: string
}

interface RawSignoffRecord {
  schema_version?: string
  case_id?: string
  reviewer?: string
  verdict?: string
  signoff_utc?: string
  notes?: string
  claim_tier?: string
  claim_boundary?: string
  claim_impact?: string
}

interface RawSignoffHistoryReport {
  schema_version?: string
  case_id?: string
  claim_tier?: string
  claim_boundary?: string
  generated_at_utc?: string
  record_count?: number
  records?: RawSignoffRecord[]
  claim_impact?: string
}

function parseVerdict(raw: string | undefined): SignoffVerdict {
  if (
    raw === 'watching' ||
    raw === 'needs_more_evidence' ||
    raw === 'needs_more_convergence' ||
    raw === 'blocked_pending_input'
  ) {
    return raw
  }
  // Defensive: if the backend ever ships an unknown verdict, fall back to
  // the most conservative bucket (a UI should never silently surface an
  // unknown Tier 2 promotion verb).
  return 'blocked_pending_input'
}

function parseRecord(raw: RawSignoffRecord | null | undefined): SignoffRecord | null {
  if (!raw || typeof raw !== 'object') return null
  if (typeof raw.case_id !== 'string' || typeof raw.reviewer !== 'string') {
    return null
  }
  return {
    schemaVersion: raw.schema_version ?? '',
    caseId: raw.case_id,
    reviewer: raw.reviewer,
    verdict: parseVerdict(raw.verdict),
    signoffUtc: raw.signoff_utc ?? '',
    notes: raw.notes ?? '',
    claimTier: raw.claim_tier ?? '',
    claimBoundary: raw.claim_boundary ?? '',
    claimImpact: raw.claim_impact ?? '',
  }
}

export function parseSignoffHistoryReport(
  raw: RawSignoffHistoryReport | null | undefined,
): SignoffHistoryReport | null {
  if (!raw || typeof raw !== 'object') return null
  if (typeof raw.case_id !== 'string') return null
  return {
    schemaVersion: raw.schema_version ?? '',
    caseId: raw.case_id,
    claimTier: raw.claim_tier ?? '',
    claimBoundary: raw.claim_boundary ?? '',
    generatedAtUtc: raw.generated_at_utc ?? '',
    recordCount: raw.record_count ?? 0,
    records: (raw.records ?? [])
      .map(parseRecord)
      .filter((r): r is SignoffRecord => r !== null),
    claimImpact: raw.claim_impact ?? '',
  }
}

export interface SignoffHistoryFetchResult {
  report: SignoffHistoryReport | null
  source: 'live' | 'fallback'
  error?: string
}

export async function fetchSignoffHistory(
  apiBase: string,
  caseId: string,
  signal?: AbortSignal,
): Promise<SignoffHistoryFetchResult> {
  const url = `${apiBase.replace(/\/$/, '')}/signoff-history/${encodeURIComponent(caseId)}`
  try {
    const res = await fetch(url, { signal })
    if (!res.ok) {
      throw new Error(`signoff-history endpoint returned ${res.status}`)
    }
    const raw = (await res.json()) as RawSignoffHistoryReport
    const parsed = parseSignoffHistoryReport(raw)
    if (!parsed) {
      throw new Error('signoff-history payload is malformed')
    }
    return { report: parsed, source: 'live' }
  } catch (err) {
    return {
      report: null,
      source: 'fallback',
      error: err instanceof Error ? err.message : 'unknown error',
    }
  }
}

// Tone helper for verdict pills. Driven by verdict semantics, not inline
// hex codes (Phase 8 anti-gaming guard X: -2).
export type VerdictTone = 'info' | 'warn' | 'danger'

export function toneForVerdict(verdict: SignoffVerdict): VerdictTone {
  switch (verdict) {
    case 'watching':
      return 'info'
    case 'needs_more_evidence':
    case 'needs_more_convergence':
      return 'warn'
    case 'blocked_pending_input':
      return 'danger'
  }
}
