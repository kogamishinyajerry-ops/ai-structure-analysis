// FM-04a Phase 4 F — Archived packet diff client.
//
// Tier 1 engineering candidate; not signed validation; not benchmark agreement.
//
// Typed fetch helper for `/api/v1/archived-packet-diff?a=...&b=...`
// plus a snake-to-camel parser. The diff is archive-vs-archive only —
// it never re-runs any live builder.

export interface ArchiveProvenance {
  relpath: string
  sha256: string
  mtimeUtc: string
  caseId: string
  generatedAtUtc: string
  claimTier: string
  claimBoundary: string
}

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

export interface ArchivedPacketDiff {
  generatedAtUtc: string
  claimBoundary: string
  archiveA: ArchiveProvenance
  archiveB: ArchiveProvenance
  residualVelocityDiff: NumericDelta
  perforationMarkerDiff: MarkerDiff
  energyBalanceErrorDiff: AbsoluteDelta
  energyAuditStatusDiff: EnergyAuditStatusDiff
  convergenceVerdictDiff: ConvergenceVerdictDiff
  artifactHashDiff: ArtifactDiff
  sameCase: boolean
  claimImpact: string
}

interface RawProvenance {
  relpath?: string
  sha256?: string
  mtime_utc?: string
  case_id?: string
  generated_at_utc?: string
  claim_tier?: string
  claim_boundary?: string
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

interface RawArchivedPacketDiff {
  generated_at_utc?: string
  claim_boundary?: string
  archive_a?: RawProvenance
  archive_b?: RawProvenance
  residual_velocity_diff?: RawNumericDelta
  perforation_marker_diff?: RawMarkerDiff
  energy_balance_error_diff?: RawAbsoluteDelta
  energy_audit_status_diff?: RawEnergyAuditStatusDiff
  convergence_verdict_diff?: RawConvergenceVerdictDiff
  artifact_hash_diff?: RawArtifactDiff
  same_case?: boolean
  claim_impact?: string
}

function parseProvenance(raw: RawProvenance | undefined): ArchiveProvenance {
  return {
    relpath: raw?.relpath ?? '',
    sha256: raw?.sha256 ?? '',
    mtimeUtc: raw?.mtime_utc ?? '',
    caseId: raw?.case_id ?? '',
    generatedAtUtc: raw?.generated_at_utc ?? '',
    claimTier: raw?.claim_tier ?? '',
    claimBoundary: raw?.claim_boundary ?? '',
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

export function parseArchivedPacketDiff(
  raw: RawArchivedPacketDiff | null | undefined,
): ArchivedPacketDiff | null {
  if (!raw || typeof raw !== 'object') return null
  if (!raw.archive_a || !raw.archive_b) return null
  return {
    generatedAtUtc: raw.generated_at_utc ?? '',
    claimBoundary: raw.claim_boundary ?? '',
    archiveA: parseProvenance(raw.archive_a),
    archiveB: parseProvenance(raw.archive_b),
    residualVelocityDiff: {
      a: raw.residual_velocity_diff?.a ?? null,
      b: raw.residual_velocity_diff?.b ?? null,
      delta: raw.residual_velocity_diff?.delta ?? null,
      deltaPct: raw.residual_velocity_diff?.delta_pct ?? null,
    },
    perforationMarkerDiff: {
      a: raw.perforation_marker_diff?.a ?? null,
      b: raw.perforation_marker_diff?.b ?? null,
      sameMarker: raw.perforation_marker_diff?.same_marker ?? false,
    },
    energyBalanceErrorDiff: {
      a: raw.energy_balance_error_diff?.a ?? null,
      b: raw.energy_balance_error_diff?.b ?? null,
      deltaAbsPct: raw.energy_balance_error_diff?.delta_abs_pct ?? null,
    },
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
    artifactHashDiff: parseArtifactDiff(raw.artifact_hash_diff),
    sameCase: raw.same_case ?? false,
    claimImpact: raw.claim_impact ?? '',
  }
}

export interface ArchivedPacketDiffFetchResult {
  diff: ArchivedPacketDiff | null
  source: 'live' | 'fallback'
  error?: string
}

export async function fetchArchivedPacketDiff(
  apiBase: string,
  a: string,
  b: string,
  signal?: AbortSignal,
): Promise<ArchivedPacketDiffFetchResult> {
  const url =
    `${apiBase.replace(/\/$/, '')}/archived-packet-diff` +
    `?a=${encodeURIComponent(a)}&b=${encodeURIComponent(b)}`
  try {
    const res = await fetch(url, { signal })
    if (!res.ok) {
      throw new Error(`archived-packet-diff endpoint returned ${res.status}`)
    }
    const raw = (await res.json()) as RawArchivedPacketDiff
    const parsed = parseArchivedPacketDiff(raw)
    if (!parsed) {
      throw new Error('archived-packet-diff payload missing archives')
    }
    return { diff: parsed, source: 'live' }
  } catch (err) {
    return {
      diff: null,
      source: 'fallback',
      error: err instanceof Error ? err.message : String(err),
    }
  }
}
