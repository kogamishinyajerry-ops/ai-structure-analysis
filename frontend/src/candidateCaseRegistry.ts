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
  // FM-04a Phase 18 E (round 3) — optional human display label for
  // the picker dropdown + Cmd-K palette. When absent the picker
  // falls back to ``caseId``. Adopted incrementally so this stays
  // back-compat with payloads from the live route (which doesn't
  // emit this field yet).
  displayLabel?: string
  // FM-04a Phase 36 C — closes Phase 35 R3 friction point (f).
  // `true`  → the case has a live ccx runner + verdict YAML
  //           (cohort-12 cases as of Phase 34 C)
  // `false` → demo deck only (GS-* OpenRadioss decks + rod-wave
  //           cases without a cross-check runner yet)
  // undefined / absent → unknown / live-route payload not yet
  //           emitting this field; UI should not surface a badge.
  runnerAvailable?: boolean
  // FM-04a Phase 37 A — solver kind for CaseBrowser tree grouping.
  // Mirrors the backend verdict YAML `solver_kind:` enum
  // (Phase 35 B 6 values: linear_static / modal / buckling /
  // dynamic / heat_transfer_steady_state / contact_pair_static).
  // Optional so the live-route payload stays back-compat.
  solverKind?:
    | 'linear_static'
    | 'modal'
    | 'buckling'
    | 'dynamic'
    | 'heat_transfer_steady_state'
    | 'contact_pair_static'
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
// Phase 18 E (round 3) — gained human displayLabel + leak case entry.
export const FALLBACK_CANDIDATE_CASES: CandidateCaseRecord[] = [
  {
    caseId: 'GS-102-candidate',
    runnerAvailable: false,
    solverKind: 'dynamic',
    displayLabel: 'GS-102 · Single-hex demo (Tier 1)',
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
    runnerAvailable: false,
    solverKind: 'dynamic',
    displayLabel: 'GS-102 refined · 4×3×3 plate + 2×2×2 projectile (Tier 1)',
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
    runnerAvailable: false,
    solverKind: 'dynamic',
    displayLabel: 'GS-102 hi-fi · 7.62×51 AP vs Weldox 460E @ V0=600 m/s (Tier 1)',
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
  {
    // Phase 18 E (round 3) — leak case promoted into the fallback so
    // novice reviewers can find it without the live backend route.
    // UX agent round-2 finding: case was invisible in the fallback
    // path until now.
    caseId: 'rod-wave-impact-energy-leak-candidate',
    runnerAvailable: false,
    solverKind: 'dynamic',
    displayLabel: 'Rod-wave impact · ENERGY LEAK case (Tier 1)',
    claimTier: 'Tier 1 engineering candidate',
    starterDeckRelpath: null,
    engineDeckRelpath: null,
    generatorScriptRelpath: null,
    notesExcerpt:
      'rod-wave-impact-energy-leak-candidate · the canonical "what does ' +
      'a broken case look like?" fixture. Hidden energy leak appears in ' +
      'the .frd; the cohort drift surface flags it. Tier 1 only; not ' +
      'signed validation; not benchmark agreement.',
    claimBoundary:
      'tier1_engineering_candidate; not_signed_validation; not_benchmark_agreement',
  },
  {
    // Phase 19 B / Phase 20 — first tier_2_validated case (per the
    // verdict-file-driven overlay in
    // `backend/app/services/reporting/_claim_tier.py`). Surfaced in
    // the fallback so the Phase 20 D Sidebar candidate roster shows
    // it even when the live backend route is unreachable. Phase 20 E
    // round-1 UX finding: omission of these three new candidates was
    // a real defect; this commit closes it.
    caseId: 'cylinder-pv-candidate',
    runnerAvailable: true,
    solverKind: 'linear_static',
    displayLabel: 'Cylinder pressure vessel · Tier 2 validated',
    claimTier: 'Tier 2 validated (analytical hoop-stress cross-check)',
    starterDeckRelpath: null,
    engineDeckRelpath: null,
    generatorScriptRelpath: 'scripts/cross_check_cylinder_pv.py',
    notesExcerpt:
      'cylinder-pv-candidate · first tier_2_validated case in the harness. ' +
      'Lame thin-walled hoop stress σ=p·r/t cross-checked vs real ccx ' +
      'wall coupon at -0.0039% residual (PASS). Verdict file at ' +
      'golden_samples/cylinder-pv-candidate/cross_check_verdict.yaml.',
    claimBoundary:
      'tier2_real_solver_validated; not_signed_validation; ' +
      'cross_check_against_analytical',
  },
  {
    caseId: 'plate-with-hole-candidate',
    runnerAvailable: true,
    solverKind: 'linear_static',
    displayLabel: 'Plate with hole · 100×50×5 mm, meshed pipeline',
    claimTier: 'Tier 1 engineering candidate',
    starterDeckRelpath:
      'golden_samples/plate-with-hole-candidate/data/plate_with_hole.geo',
    engineDeckRelpath: null,
    generatorScriptRelpath: null,
    notesExcerpt:
      'plate-with-hole-candidate · Phase 20 C demonstration of the ' +
      'meshed Tier 2 pipeline. Real gmsh → C3D4 tet mesh → real ccx → ' +
      'non-zero u_x field under tensile load. Kirsch σ_max = 3·σ_∞ ' +
      'cross-check runner is Phase 21+ scope.',
    claimBoundary:
      'tier1_engineering_candidate; not_signed_validation; not_benchmark_agreement',
  },
  {
    caseId: 'cantilever-beam-candidate',
    runnerAvailable: true,
    solverKind: 'linear_static',
    displayLabel: 'Cantilever beam · Euler-Bernoulli δ=PL³/(3EI)',
    claimTier: 'Tier 1 engineering candidate',
    starterDeckRelpath: null,
    engineDeckRelpath: null,
    generatorScriptRelpath: null,
    notesExcerpt:
      'cantilever-beam-candidate · second analytical cross-check ' +
      'companion. Phase 20 B shipped the analytical formula + validity ' +
      'envelope; ccx-running runner is Phase 21+ scope (single-hex ' +
      'coupons cannot capture bending; multi-element Gmsh path lands ' +
      'this case at tier_2_validated).',
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
