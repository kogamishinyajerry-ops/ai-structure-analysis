// FM-04a Phase 2 C — Workbench candidate-case picker registry.
//
// Tier 1 engineering candidate; not signed validation; not benchmark agreement.
//
// Typed contract for the `/api/v1/candidate-cases` endpoint plus a
// static fallback list that matches the on-disk
// `golden_samples/*-candidate/` directories. The static list is used
// when the backend is unreachable so the Workbench still surfaces the
// picker as a Tier 1 boundary-preserving stub.

export type CandidateCaseId =
  | 'GS-102-candidate'
  | 'GS-102-refined-candidate'
  | 'GS-102-hifi-candidate'
  | string

export interface CandidateCaseRecord {
  caseId: CandidateCaseId
  claimTier: string
  starterDeckRelpath: string | null
  engineDeckRelpath: string | null
  generatorScriptRelpath: string | null
  notesExcerpt: string | null
  claimBoundary: string
}

export interface CandidateCaseRegistryPayload {
  claimTier: string
  claimBoundary: string
  claimImpact: string
  count: number
  cases: CandidateCaseRecord[]
}

// Static fallback list — read at build time so the Workbench can
// render the picker even when /api/v1/candidate-cases is unreachable.
// Mirrors the on-disk directory contents committed in
// `golden_samples/*-candidate/` and the matching `scripts/gen_*` files.
export const FALLBACK_CANDIDATE_CASES: CandidateCaseRecord[] = [
  {
    caseId: 'GS-102-candidate',
    claimTier: 'Tier 1 engineering candidate',
    starterDeckRelpath: 'golden_samples/GS-102-candidate/data/model_00_0000.rad',
    engineDeckRelpath: 'golden_samples/GS-102-candidate/data/model_00_0001.rad',
    generatorScriptRelpath: null,
    notesExcerpt:
      'GS-102-candidate · 1-hex starter+engine demo deck for FM-04a P3 ' +
      'registration. Tier 1 engineering candidate; not signed validation; ' +
      'not benchmark agreement.',
    claimBoundary:
      'tier1_engineering_candidate; not_signed_validation; not_benchmark_agreement',
  },
  {
    caseId: 'GS-102-refined-candidate',
    claimTier: 'Tier 1 engineering candidate',
    starterDeckRelpath:
      'golden_samples/GS-102-refined-candidate/data/model_00_0000.rad',
    engineDeckRelpath:
      'golden_samples/GS-102-refined-candidate/data/model_00_0001.rad',
    generatorScriptRelpath: 'scripts/gen_gs102_refined_deck.py',
    notesExcerpt:
      'GS-102-refined-candidate · 4x3x3 plate hex + 2x2x2 projectile hex ' +
      'refinement of GS-102-candidate. Tier 1 only; not signed validation; ' +
      'not benchmark agreement.',
    claimBoundary:
      'tier1_engineering_candidate; not_signed_validation; not_benchmark_agreement',
  },
  {
    caseId: 'GS-102-hifi-candidate',
    claimTier: 'Tier 1 engineering candidate',
    starterDeckRelpath: 'golden_samples/GS-102-hifi-candidate/data/model_00_0000.rad',
    engineDeckRelpath: 'golden_samples/GS-102-hifi-candidate/data/model_00_0001.rad',
    generatorScriptRelpath: 'scripts/gen_gs102_hifi_deck.py',
    notesExcerpt:
      'GS-102-hifi-candidate · 7.62x51 AP-class projectile vs 100x100x8 mm ' +
      'Weldox 460E plate at V0 = 600 m/s. Tier 1 only; not signed validation; ' +
      'not benchmark agreement.',
    claimBoundary:
      'tier1_engineering_candidate; not_signed_validation; not_benchmark_agreement',
  },
]

// Server payload key → camelCase mapping for the React layer.
interface RawCandidateCaseRecord {
  case_id: string
  claim_tier: string
  starter_deck_relpath: string | null
  engine_deck_relpath: string | null
  generator_script_relpath: string | null
  notes_excerpt: string | null
  claim_boundary: string
}

interface RawCandidateCasePayload {
  claim_tier: string
  claim_boundary: string
  claim_impact: string
  count: number
  cases: RawCandidateCaseRecord[]
}

export function parseCandidateCasesPayload(
  raw: RawCandidateCasePayload | null | undefined,
): CandidateCaseRegistryPayload | null {
  if (!raw || typeof raw !== 'object' || !Array.isArray(raw.cases)) {
    return null
  }
  return {
    claimTier: raw.claim_tier,
    claimBoundary: raw.claim_boundary,
    claimImpact: raw.claim_impact,
    count: raw.count ?? raw.cases.length,
    cases: raw.cases.map((r) => ({
      caseId: r.case_id,
      claimTier: r.claim_tier,
      starterDeckRelpath: r.starter_deck_relpath,
      engineDeckRelpath: r.engine_deck_relpath,
      generatorScriptRelpath: r.generator_script_relpath,
      notesExcerpt: r.notes_excerpt,
      claimBoundary: r.claim_boundary,
    })),
  }
}

export interface CandidateCaseFetchResult {
  cases: CandidateCaseRecord[]
  source: 'live' | 'fallback'
  claimImpact: string
  error?: string
}

export async function fetchCandidateCases(
  apiBase: string,
  signal?: AbortSignal,
): Promise<CandidateCaseFetchResult> {
  const url = `${apiBase.replace(/\/$/, '')}/candidate-cases`
  try {
    const res = await fetch(url, { signal })
    if (!res.ok) {
      throw new Error(`candidate-cases endpoint returned ${res.status}`)
    }
    const raw = (await res.json()) as RawCandidateCasePayload
    const parsed = parseCandidateCasesPayload(raw)
    if (!parsed) {
      throw new Error('candidate-cases payload missing cases array')
    }
    return {
      cases: parsed.cases,
      source: 'live',
      claimImpact: parsed.claimImpact,
    }
  } catch (err) {
    return {
      cases: FALLBACK_CANDIDATE_CASES,
      source: 'fallback',
      claimImpact:
        'Tier 1 candidate-case picker fallback (backend unreachable); not ' +
        'signed validation; not benchmark agreement',
      error: err instanceof Error ? err.message : String(err),
    }
  }
}

export function findCandidateCase(
  cases: CandidateCaseRecord[],
  caseId: string | null | undefined,
): CandidateCaseRecord | null {
  if (!caseId) return null
  return cases.find((c) => c.caseId === caseId) ?? null
}
