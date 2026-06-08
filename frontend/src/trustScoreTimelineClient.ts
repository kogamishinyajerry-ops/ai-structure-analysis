// FM-04a Phase 6 D — Trust score timeline client.
//
// Tier 1 engineering candidate; not signed validation; not benchmark agreement.
//
// Typed fetch helper for `/api/v1/trust-score-timeline/<case-id>`.
// Surfaces schemaVersion + formulaVersion + per-point per-axis
// weighted breakdown so the UI sparkline can render an exact trend.

export interface TimelinePoint {
  snapshotLabel: string
  capturedAtUtc: string | null
  trustScore: number
  completenessWeighted: number
  convergenceWeighted: number
  energyAuditWeighted: number
  reproducibilityWeighted: number
}

export interface TrustScoreTimeline {
  schemaVersion: string
  formulaVersion: string
  caseId: string
  claimTier: string
  claimBoundary: string
  generatedAtUtc: string
  pointCount: number
  points: TimelinePoint[]
  claimImpact: string
}

interface RawPoint {
  snapshot_label?: string
  captured_at_utc?: string | null
  trust_score?: number
  completeness_weighted?: number
  convergence_weighted?: number
  energy_audit_weighted?: number
  reproducibility_weighted?: number
}

interface RawTimeline {
  schema_version?: string
  formula_version?: string
  case_id?: string
  claim_tier?: string
  claim_boundary?: string
  generated_at_utc?: string
  point_count?: number
  points?: RawPoint[]
  claim_impact?: string
}

function parsePoint(raw: RawPoint | null | undefined): TimelinePoint | null {
  if (!raw || typeof raw !== 'object') return null
  if (typeof raw.snapshot_label !== 'string') return null
  return {
    snapshotLabel: raw.snapshot_label,
    capturedAtUtc: raw.captured_at_utc ?? null,
    trustScore: raw.trust_score ?? 0,
    completenessWeighted: raw.completeness_weighted ?? 0,
    convergenceWeighted: raw.convergence_weighted ?? 0,
    energyAuditWeighted: raw.energy_audit_weighted ?? 0,
    reproducibilityWeighted: raw.reproducibility_weighted ?? 0,
  }
}

export function parseTrustScoreTimeline(
  raw: RawTimeline | null | undefined,
): TrustScoreTimeline | null {
  if (!raw || typeof raw !== 'object') return null
  if (typeof raw.case_id !== 'string') return null
  return {
    schemaVersion: raw.schema_version ?? '',
    formulaVersion: raw.formula_version ?? '',
    caseId: raw.case_id,
    claimTier: raw.claim_tier ?? '',
    claimBoundary: raw.claim_boundary ?? '',
    generatedAtUtc: raw.generated_at_utc ?? '',
    pointCount: raw.point_count ?? 0,
    points: (raw.points ?? [])
      .map(parsePoint)
      .filter((p): p is TimelinePoint => p !== null),
    claimImpact: raw.claim_impact ?? '',
  }
}

export interface TrustScoreTimelineFetchResult {
  timeline: TrustScoreTimeline | null
  source: 'live' | 'fallback'
  error?: string
}

export async function fetchTrustScoreTimeline(
  apiBase: string,
  caseId: string,
  signal?: AbortSignal,
): Promise<TrustScoreTimelineFetchResult> {
  const url = `${apiBase.replace(/\/$/, '')}/trust-score-timeline/${encodeURIComponent(caseId)}`
  try {
    const res = await fetch(url, { signal })
    if (!res.ok) {
      throw new Error(`trust-score-timeline endpoint returned ${res.status}`)
    }
    const raw = (await res.json()) as RawTimeline
    const parsed = parseTrustScoreTimeline(raw)
    if (!parsed) {
      throw new Error('trust-score-timeline payload is malformed')
    }
    return { timeline: parsed, source: 'live' }
  } catch (err) {
    return {
      timeline: null,
      source: 'fallback',
      error: err instanceof Error ? err.message : 'unknown error',
    }
  }
}

// Sparkline path builder. Returns an SVG path "d" string that draws
// the timeline scores into a [0..width, 0..height] viewport. Top of
// the viewport is trust_score = 100; bottom is 0.
export function buildSparklinePath(
  points: TimelinePoint[],
  width: number,
  height: number,
): string {
  if (points.length === 0) return ''
  if (points.length === 1) {
    const y = height - (points[0].trustScore / 100) * height
    return `M 0 ${y} L ${width} ${y}`
  }
  const step = width / (points.length - 1)
  const segments = points.map((p, i) => {
    const x = i * step
    const y = height - (p.trustScore / 100) * height
    return `${i === 0 ? 'M' : 'L'} ${x.toFixed(2)} ${y.toFixed(2)}`
  })
  return segments.join(' ')
}
