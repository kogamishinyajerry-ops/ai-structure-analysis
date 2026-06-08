// FM-04a Phase 9 E + Phase 10 E — Trust score provenance trace client.
//
// Tier 1 engineering candidate; not signed validation; not benchmark agreement.
//
// The frontend tuple SSOT must match the backend `PROVENANCE_INPUT_KINDS`
// tuple in `backend/app/services/reporting/trust_score_provenance.py`
// (Phase 8 C + Phase 9 B MINOR bump 1.0.0 -> 1.1.0 + Phase 10 E MINOR
// bump 1.1.0 -> 1.2.0). The Phase 9 B addition was `generator` as the
// fifth kind. Phase 10 E added three additive fields on every row:
// `sha256Normalized`, `normalizationMethod`, `normalizationError`.
//
// Defensive `parseInputKind` falls back to `'unknown'` for unknown
// values so a future MINOR bump that adds another kind does NOT crash
// the panel — it surfaces in a neutral state until the frontend tuple
// is updated to match (Phase 9 anti-gaming guard X: -2). The Phase 10 E
// fields are nullable on every row; the panel-side renderer falls back
// to a neutral dash when a row carries `null`.

export const PROVENANCE_INPUT_KINDS = [
  'metrics',
  'convergence',
  'completeness',
  'reproducibility',
  'generator',
] as const

export type ProvenanceInputKind = (typeof PROVENANCE_INPUT_KINDS)[number] | 'unknown'

export interface ProvenanceInput {
  kind: ProvenanceInputKind
  path: string
  present: boolean
  sha256: string | null
  // Phase 10 E — present on every row (`null` for non-generator kinds
  // and for generator rows with parse failure / absent file).
  sha256Normalized: string | null
  normalizationMethod: string | null
  normalizationError: string | null
}

export interface ProvenanceAxis {
  axis: string
  weighted: number
}

export interface TrustScoreProvenanceReport {
  schemaVersion: string
  formulaVersion: string
  caseId: string
  snapshotLabel: string
  generatedAtUtc: string
  trustScore: number | null
  axes: ProvenanceAxis[]
  inputs: ProvenanceInput[]
  claimTier: string
  claimBoundary: string
  claimImpact: string
}

interface RawInput {
  kind?: string
  path?: string
  present?: boolean
  sha256?: string | null
  sha256_normalized?: string | null
  normalization_method?: string | null
  normalization_error?: string | null
}

interface RawAxis {
  axis?: string
  weighted?: number
}

interface RawReport {
  schema_version?: string
  formula_version?: string
  case_id?: string
  snapshot_label?: string
  generated_at_utc?: string
  trust_score?: number | null
  axes?: RawAxis[]
  inputs?: RawInput[]
  claim_tier?: string
  claim_boundary?: string
  claim_impact?: string
}

function parseInputKind(raw: string | undefined): ProvenanceInputKind {
  // Defensive: a future MINOR bump that adds a kind not yet in the
  // frontend tuple surfaces here as `'unknown'`. The panel renders
  // such rows in a neutral state — it does NOT silently surface a
  // Tier 2 promotion verb (Phase 9 anti-gaming guard X: -2).
  if (raw === undefined) return 'unknown'
  if ((PROVENANCE_INPUT_KINDS as readonly string[]).includes(raw)) {
    return raw as ProvenanceInputKind
  }
  return 'unknown'
}

function parseInput(raw: RawInput | null | undefined): ProvenanceInput | null {
  if (!raw || typeof raw !== 'object') return null
  if (typeof raw.path !== 'string') return null
  return {
    kind: parseInputKind(raw.kind),
    path: raw.path,
    present: Boolean(raw.present),
    sha256: raw.sha256 ?? null,
    // Phase 10 E — all three nullable on every row; a 1.1.0-era
    // payload that omits the keys parses cleanly with `null`.
    sha256Normalized: raw.sha256_normalized ?? null,
    normalizationMethod: raw.normalization_method ?? null,
    normalizationError: raw.normalization_error ?? null,
  }
}

function parseAxis(raw: RawAxis | null | undefined): ProvenanceAxis | null {
  if (!raw || typeof raw !== 'object') return null
  if (typeof raw.axis !== 'string') return null
  return {
    axis: raw.axis,
    weighted: raw.weighted ?? 0,
  }
}

export function parseTrustScoreProvenanceReport(
  raw: RawReport | null | undefined,
): TrustScoreProvenanceReport | null {
  if (!raw || typeof raw !== 'object') return null
  if (typeof raw.case_id !== 'string') return null
  if (typeof raw.snapshot_label !== 'string') return null
  return {
    schemaVersion: raw.schema_version ?? '',
    formulaVersion: raw.formula_version ?? '',
    caseId: raw.case_id,
    snapshotLabel: raw.snapshot_label,
    generatedAtUtc: raw.generated_at_utc ?? '',
    trustScore: raw.trust_score ?? null,
    axes: (raw.axes ?? [])
      .map(parseAxis)
      .filter((a): a is ProvenanceAxis => a !== null),
    inputs: (raw.inputs ?? [])
      .map(parseInput)
      .filter((i): i is ProvenanceInput => i !== null),
    claimTier: raw.claim_tier ?? '',
    claimBoundary: raw.claim_boundary ?? '',
    claimImpact: raw.claim_impact ?? '',
  }
}

export interface ProvenanceFetchResult {
  report: TrustScoreProvenanceReport | null
  source: 'live' | 'fallback'
  error?: string
}

export async function fetchTrustScoreProvenance(
  apiBase: string,
  caseId: string,
  snapshotLabel: string,
  signal?: AbortSignal,
): Promise<ProvenanceFetchResult> {
  const url =
    `${apiBase.replace(/\/$/, '')}/trust-score-provenance/${encodeURIComponent(caseId)}` +
    `?snapshot=${encodeURIComponent(snapshotLabel)}`
  try {
    const res = await fetch(url, { signal })
    if (!res.ok) {
      throw new Error(`trust-score-provenance endpoint returned ${res.status}`)
    }
    const raw = (await res.json()) as RawReport
    const parsed = parseTrustScoreProvenanceReport(raw)
    if (!parsed) {
      throw new Error('trust-score-provenance payload is malformed')
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

/** Short SHA chip — first 12 chars of the full SHA-256, or '—' when null. */
export function shortSha(sha: string | null | undefined): string {
  if (!sha) return '—'
  return sha.slice(0, 12)
}
