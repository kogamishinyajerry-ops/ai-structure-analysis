// FM-04a Phase 3 C — Case comparison client.
//
// Tier 1 engineering candidate; not signed validation; not benchmark agreement.
//
// Typed fetch helper for `/api/v1/case-comparison?a=<id>&b=<id>` plus a
// snake-to-camel parser. The comparison is case-vs-case across two Tier 1
// candidate acceptance packets — NOT a comparison against experimental
// benchmark data.

export interface NumericDelta {
  a: number | null
  b: number | null
  delta: number | null
  deltaPct: number | null
}

export interface AbsoluteDelta {
  a: number | null
  b: number | null
  deltaAbsPct: number | null
}

export interface MarkerDiff {
  a: string | null
  b: string | null
  sameMarker: boolean
}

export interface EnergyAuditStatusDiff {
  a: string
  b: string
  bothClosed: boolean
  sameStatus: boolean
}

export interface ConvergenceVerdictDiff {
  a: string
  b: string
  sameVerdict: boolean
}

export interface HashChangedEntry {
  kind: string
  aSha256: string | null
  bSha256: string | null
}

export interface ArtifactDiff {
  aOnly: string[]
  bOnly: string[]
  shared: string[]
  hashChanged: HashChangedEntry[]
}

export interface CaseComparison {
  caseA: string
  caseB: string
  generatedAtUtc: string
  claimBoundary: string
  residualVelocityDiff: NumericDelta
  perforationMarkerDiff: MarkerDiff
  energyBalanceErrorDiff: AbsoluteDelta
  energyAuditStatusDiff: EnergyAuditStatusDiff
  convergenceVerdictDiff: ConvergenceVerdictDiff
  deckArtifactDiff: ArtifactDiff
  evidenceArtifactDiff: ArtifactDiff
  claimImpact: string
}

interface RawNumericDelta {
  a?: number | null
  b?: number | null
  delta?: number | null
  delta_pct?: number | null
}

interface RawAbsoluteDelta {
  a?: number | null
  b?: number | null
  delta_abs_pct?: number | null
}

interface RawMarkerDiff {
  a?: string | null
  b?: string | null
  same_marker?: boolean
}

interface RawEnergyAuditStatusDiff {
  a?: string
  b?: string
  both_closed?: boolean
  same_status?: boolean
}

interface RawConvergenceVerdictDiff {
  a?: string
  b?: string
  same_verdict?: boolean
}

interface RawHashChangedEntry {
  kind?: string
  a_sha256?: string | null
  b_sha256?: string | null
}

interface RawArtifactDiff {
  a_only?: string[]
  b_only?: string[]
  shared?: string[]
  hash_changed?: RawHashChangedEntry[]
}

interface RawCaseComparison {
  case_a?: string
  case_b?: string
  generated_at_utc?: string
  claim_boundary?: string
  residual_velocity_diff?: RawNumericDelta
  perforation_marker_diff?: RawMarkerDiff
  energy_balance_error_diff?: RawAbsoluteDelta
  energy_audit_status_diff?: RawEnergyAuditStatusDiff
  convergence_verdict_diff?: RawConvergenceVerdictDiff
  deck_artifact_diff?: RawArtifactDiff
  evidence_artifact_diff?: RawArtifactDiff
  claim_impact?: string
}

function parseNumericDelta(raw: RawNumericDelta | undefined): NumericDelta {
  return {
    a: raw?.a ?? null,
    b: raw?.b ?? null,
    delta: raw?.delta ?? null,
    deltaPct: raw?.delta_pct ?? null,
  }
}

function parseAbsoluteDelta(raw: RawAbsoluteDelta | undefined): AbsoluteDelta {
  return {
    a: raw?.a ?? null,
    b: raw?.b ?? null,
    deltaAbsPct: raw?.delta_abs_pct ?? null,
  }
}

function parseArtifactDiff(raw: RawArtifactDiff | undefined): ArtifactDiff {
  return {
    aOnly: raw?.a_only ?? [],
    bOnly: raw?.b_only ?? [],
    shared: raw?.shared ?? [],
    hashChanged: (raw?.hash_changed ?? []).map((entry) => ({
      kind: entry.kind ?? '',
      aSha256: entry.a_sha256 ?? null,
      bSha256: entry.b_sha256 ?? null,
    })),
  }
}

export function parseCaseComparison(
  raw: RawCaseComparison | null | undefined,
): CaseComparison | null {
  if (!raw || typeof raw !== 'object') return null
  if (typeof raw.case_a !== 'string' || typeof raw.case_b !== 'string') return null
  return {
    caseA: raw.case_a,
    caseB: raw.case_b,
    generatedAtUtc: raw.generated_at_utc ?? '',
    claimBoundary: raw.claim_boundary ?? '',
    residualVelocityDiff: parseNumericDelta(raw.residual_velocity_diff),
    perforationMarkerDiff: {
      a: raw.perforation_marker_diff?.a ?? null,
      b: raw.perforation_marker_diff?.b ?? null,
      sameMarker: raw.perforation_marker_diff?.same_marker ?? false,
    },
    energyBalanceErrorDiff: parseAbsoluteDelta(raw.energy_balance_error_diff),
    energyAuditStatusDiff: {
      a: raw.energy_audit_status_diff?.a ?? 'unavailable',
      b: raw.energy_audit_status_diff?.b ?? 'unavailable',
      bothClosed: raw.energy_audit_status_diff?.both_closed ?? false,
      sameStatus: raw.energy_audit_status_diff?.same_status ?? false,
    },
    convergenceVerdictDiff: {
      a: raw.convergence_verdict_diff?.a ?? 'insufficient_data',
      b: raw.convergence_verdict_diff?.b ?? 'insufficient_data',
      sameVerdict: raw.convergence_verdict_diff?.same_verdict ?? false,
    },
    deckArtifactDiff: parseArtifactDiff(raw.deck_artifact_diff),
    evidenceArtifactDiff: parseArtifactDiff(raw.evidence_artifact_diff),
    claimImpact: raw.claim_impact ?? '',
  }
}

export interface CaseComparisonFetchResult {
  comparison: CaseComparison | null
  source: 'live' | 'fallback'
  error?: string
}

export async function fetchCaseComparison(
  apiBase: string,
  caseA: string,
  caseB: string,
  signal?: AbortSignal,
): Promise<CaseComparisonFetchResult> {
  const url =
    `${apiBase.replace(/\/$/, '')}/case-comparison` +
    `?a=${encodeURIComponent(caseA)}&b=${encodeURIComponent(caseB)}`
  try {
    const res = await fetch(url, { signal })
    if (!res.ok) {
      throw new Error(`case-comparison endpoint returned ${res.status}`)
    }
    const raw = (await res.json()) as RawCaseComparison
    const parsed = parseCaseComparison(raw)
    if (!parsed) {
      throw new Error('case-comparison payload missing case ids')
    }
    return { comparison: parsed, source: 'live' }
  } catch (err) {
    return {
      comparison: null,
      source: 'fallback',
      error: err instanceof Error ? err.message : String(err),
    }
  }
}

// Tone-coded thresholds for residual-velocity / energy-balance delta cells.
// 'accent' = ≤ 5% delta, 'warning' = ≤ 15% delta, 'danger' = > 15%.
export type DeltaTone = 'accent' | 'warning' | 'danger' | 'muted'

export function numericDeltaTone(delta: NumericDelta): DeltaTone {
  if (delta.deltaPct === null || delta.deltaPct === undefined) return 'muted'
  const abs = Math.abs(delta.deltaPct)
  if (abs <= 5) return 'accent'
  if (abs <= 15) return 'warning'
  return 'danger'
}

export function absoluteDeltaTone(delta: AbsoluteDelta): DeltaTone {
  if (delta.deltaAbsPct === null || delta.deltaAbsPct === undefined) return 'muted'
  const abs = Math.abs(delta.deltaAbsPct)
  if (abs <= 5) return 'accent'
  if (abs <= 15) return 'warning'
  return 'danger'
}
