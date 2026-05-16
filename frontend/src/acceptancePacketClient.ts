// FM-04a Phase 3 C — Acceptance evidence packet client.
//
// Tier 1 engineering candidate; not signed validation; not benchmark agreement.
//
// Typed fetch helper for `/api/v1/acceptance-packet/<case-id>` plus a
// snake-to-camel parser for the JSON payload produced by the
// Phase 3 A builder. Mirrors the structure of `candidateCaseRegistry`:
// fetch returns either a live parsed payload or a structured fallback
// describing why the live payload is unavailable.

export interface AcceptanceArtifact {
  relpath: string
  sha256: string | null
  bytes: number | null
  kind: string
}

export interface BallisticMetricsSummary {
  perforationMarker: string | null
  projectileInitialVelocityMPerS: number | null
  residualVelocityCandidateMPerS: number | null
  frontFaceCrossed: boolean | null
  backFaceCrossed: boolean | null
  firstBackFaceCrossingTS: number | null
}

export interface EnergyAuditSummary {
  status: string
  initialKineticEnergyJ: number | null
  residualKineticEnergyJ: number | null
  aggregateInternalEnergyJ: number | null
  externalWorkJ: number | null
  energyBalanceErrorPct: number | null
  breakdownStatus: string
  missingTerms: string[]
}

export interface ConvergenceStudySummary {
  status: string
  combinedVerdict: string
  meshSweepStability: string
  dtSweepStability: string
  rowCount: number
  tolerancePct: number | null
}

export interface AcceptancePacket {
  schemaVersion: string
  caseId: string
  generatedAtUtc: string
  claimTier: string
  claimBoundary: string
  deckArtifacts: AcceptanceArtifact[]
  evidenceArtifacts: AcceptanceArtifact[]
  visualizationArtifacts: AcceptanceArtifact[]
  ballisticMetricsSummary: BallisticMetricsSummary
  energyAuditSummary: EnergyAuditSummary
  convergenceStudySummary: ConvergenceStudySummary
  assumptions: string[]
  limitations: string[]
  tier2BlockersRemaining: string[]
  claimImpact: string
}

interface RawArtifact {
  relpath?: string
  sha256?: string | null
  bytes?: number | null
  kind?: string
}

interface RawAcceptancePacket {
  schema_version?: string
  case_id?: string
  generated_at_utc?: string
  claim_tier?: string
  claim_boundary?: string
  deck_artifacts?: RawArtifact[]
  evidence_artifacts?: RawArtifact[]
  visualization_artifacts?: RawArtifact[]
  ballistic_metrics_summary?: {
    perforation_marker?: string | null
    projectile_initial_velocity_m_per_s?: number | null
    residual_velocity_candidate_m_per_s?: number | null
    front_face_crossed?: boolean | null
    back_face_crossed?: boolean | null
    first_back_face_crossing_t_s?: number | null
  }
  energy_audit_summary?: {
    status?: string
    initial_kinetic_energy_j?: number | null
    residual_kinetic_energy_j?: number | null
    aggregate_internal_energy_j?: number | null
    external_work_j?: number | null
    energy_balance_error_pct?: number | null
    breakdown_status?: string
    missing_terms?: string[]
  }
  convergence_study_summary?: {
    status?: string
    combined_verdict?: string
    mesh_sweep_stability?: string
    dt_sweep_stability?: string
    row_count?: number
    tolerance_pct?: number | null
  }
  assumptions?: string[]
  limitations?: string[]
  tier2_blockers_remaining?: string[]
  claim_impact?: string
}

function parseArtifact(raw: RawArtifact | null | undefined): AcceptanceArtifact | null {
  if (!raw || typeof raw !== 'object') return null
  if (typeof raw.relpath !== 'string' || typeof raw.kind !== 'string') return null
  return {
    relpath: raw.relpath,
    sha256: raw.sha256 ?? null,
    bytes: raw.bytes ?? null,
    kind: raw.kind,
  }
}

export function parseAcceptancePacket(
  raw: RawAcceptancePacket | null | undefined,
): AcceptancePacket | null {
  if (!raw || typeof raw !== 'object') return null
  if (typeof raw.case_id !== 'string') return null
  const ballistic = raw.ballistic_metrics_summary ?? {}
  const energy = raw.energy_audit_summary ?? {}
  const convergence = raw.convergence_study_summary ?? {}
  return {
    schemaVersion: raw.schema_version ?? '',
    caseId: raw.case_id,
    generatedAtUtc: raw.generated_at_utc ?? '',
    claimTier: raw.claim_tier ?? '',
    claimBoundary: raw.claim_boundary ?? '',
    deckArtifacts: (raw.deck_artifacts ?? [])
      .map(parseArtifact)
      .filter((a): a is AcceptanceArtifact => a !== null),
    evidenceArtifacts: (raw.evidence_artifacts ?? [])
      .map(parseArtifact)
      .filter((a): a is AcceptanceArtifact => a !== null),
    visualizationArtifacts: (raw.visualization_artifacts ?? [])
      .map(parseArtifact)
      .filter((a): a is AcceptanceArtifact => a !== null),
    ballisticMetricsSummary: {
      perforationMarker: ballistic.perforation_marker ?? null,
      projectileInitialVelocityMPerS: ballistic.projectile_initial_velocity_m_per_s ?? null,
      residualVelocityCandidateMPerS: ballistic.residual_velocity_candidate_m_per_s ?? null,
      frontFaceCrossed: ballistic.front_face_crossed ?? null,
      backFaceCrossed: ballistic.back_face_crossed ?? null,
      firstBackFaceCrossingTS: ballistic.first_back_face_crossing_t_s ?? null,
    },
    energyAuditSummary: {
      status: energy.status ?? 'unavailable',
      initialKineticEnergyJ: energy.initial_kinetic_energy_j ?? null,
      residualKineticEnergyJ: energy.residual_kinetic_energy_j ?? null,
      aggregateInternalEnergyJ: energy.aggregate_internal_energy_j ?? null,
      externalWorkJ: energy.external_work_j ?? null,
      energyBalanceErrorPct: energy.energy_balance_error_pct ?? null,
      breakdownStatus: energy.breakdown_status ?? 'unavailable',
      missingTerms: energy.missing_terms ?? [],
    },
    convergenceStudySummary: {
      status: convergence.status ?? 'unavailable',
      combinedVerdict: convergence.combined_verdict ?? 'insufficient_data',
      meshSweepStability: convergence.mesh_sweep_stability ?? 'unknown',
      dtSweepStability: convergence.dt_sweep_stability ?? 'unknown',
      rowCount: convergence.row_count ?? 0,
      tolerancePct: convergence.tolerance_pct ?? null,
    },
    assumptions: raw.assumptions ?? [],
    limitations: raw.limitations ?? [],
    tier2BlockersRemaining: raw.tier2_blockers_remaining ?? [],
    claimImpact: raw.claim_impact ?? '',
  }
}

export interface AcceptancePacketFetchResult {
  packet: AcceptancePacket | null
  source: 'live' | 'fallback'
  rawJson: string | null
  error?: string
}

export async function fetchAcceptancePacket(
  apiBase: string,
  caseId: string,
  signal?: AbortSignal,
): Promise<AcceptancePacketFetchResult> {
  const url = `${apiBase.replace(/\/$/, '')}/acceptance-packet/${encodeURIComponent(caseId)}`
  try {
    const res = await fetch(url, { signal })
    if (!res.ok) {
      throw new Error(`acceptance-packet endpoint returned ${res.status}`)
    }
    const text = await res.text()
    const parsed = parseAcceptancePacket(JSON.parse(text) as RawAcceptancePacket)
    if (!parsed) {
      throw new Error('acceptance-packet payload missing case_id')
    }
    return { packet: parsed, source: 'live', rawJson: text }
  } catch (err) {
    return {
      packet: null,
      source: 'fallback',
      rawJson: null,
      error: err instanceof Error ? err.message : String(err),
    }
  }
}

export function acceptancePacketDownloadUrl(apiBase: string, caseId: string): string {
  return `${apiBase.replace(/\/$/, '')}/acceptance-packet/${encodeURIComponent(caseId)}`
}
