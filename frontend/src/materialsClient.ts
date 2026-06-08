// FM-04a Phase 18 E (round 2) — typed client for /api/v1/materials/.
//
// Tier 1 / Tier 2 engineering candidate; not signed validation; not
// benchmark agreement.
//
// Mirrors the backend route shape (per
// `backend/app/api/routes/materials.py`). The static fallback list
// is a byte-equivalent copy of `library.json` so the picker still
// renders the 3 baseline materials when the backend is unreachable.

export interface MaterialRecord {
  readonly id: string
  readonly name: string
  readonly youngsModulusPa: number
  readonly poissonRatio: number
  readonly densityKgM3: number
  readonly yieldStressPa: number | null
  readonly ultimateStressPa: number | null
  readonly reference: string
  readonly claimTier: string
  readonly claimBoundary: string
}

export interface MaterialsPayload {
  readonly claimTier: string
  readonly claimBoundary: string
  readonly count: number
  readonly materials: MaterialRecord[]
}

// Server payload key → camelCase mapping.
interface RawMaterialRecord {
  id: string
  name: string
  youngs_modulus_pa: number
  poisson_ratio: number
  density_kg_m3: number
  yield_stress_pa: number | null
  ultimate_stress_pa: number | null
  reference: string
  claim_tier: string
  claim_boundary: string
}

interface RawMaterialsPayload {
  claim_tier: string
  claim_boundary: string
  count: number
  materials: RawMaterialRecord[]
}

const TIER_1_BANNER = 'Tier 1 engineering candidate'
const TIER_1_BOUNDARY =
  'tier1_engineering_candidate; not_signed_validation; not_benchmark_agreement'

// Static fallback — byte-equivalent to library.json.
export const FALLBACK_MATERIALS: MaterialRecord[] = [
  {
    id: 'steel-s355',
    name: 'Structural Steel S355',
    youngsModulusPa: 210e9,
    poissonRatio: 0.3,
    densityKgM3: 7850.0,
    yieldStressPa: 355e6,
    ultimateStressPa: 510e6,
    reference: 'EN 10025-2:2019 §7.3 (S355 grade, room temperature)',
    claimTier: TIER_1_BANNER,
    claimBoundary: TIER_1_BOUNDARY,
  },
  {
    id: 'aluminium-6061-t6',
    name: 'Aluminium 6061-T6',
    youngsModulusPa: 68.9e9,
    poissonRatio: 0.33,
    densityKgM3: 2700.0,
    yieldStressPa: 276e6,
    ultimateStressPa: 310e6,
    reference:
      'MMPDS-2023 §3.6.1.0 (6061-T6 wrought, sheet, longitudinal, room temperature)',
    claimTier: TIER_1_BANNER,
    claimBoundary: TIER_1_BOUNDARY,
  },
  {
    id: 'titanium-ti-6al-4v',
    name: 'Titanium Ti-6Al-4V',
    youngsModulusPa: 113.8e9,
    poissonRatio: 0.342,
    densityKgM3: 4430.0,
    yieldStressPa: 880e6,
    ultimateStressPa: 950e6,
    reference: 'MMPDS-2023 §5.4.1.0 (Ti-6Al-4V annealed bar, room temperature)',
    claimTier: TIER_1_BANNER,
    claimBoundary: TIER_1_BOUNDARY,
  },
]

function toCamel(raw: RawMaterialRecord): MaterialRecord {
  return {
    id: raw.id,
    name: raw.name,
    youngsModulusPa: raw.youngs_modulus_pa,
    poissonRatio: raw.poisson_ratio,
    densityKgM3: raw.density_kg_m3,
    yieldStressPa: raw.yield_stress_pa,
    ultimateStressPa: raw.ultimate_stress_pa,
    reference: raw.reference,
    claimTier: raw.claim_tier,
    claimBoundary: raw.claim_boundary,
  }
}

export function parseMaterialsPayload(
  raw: RawMaterialsPayload | null | undefined,
): MaterialsPayload | null {
  if (!raw || typeof raw !== 'object' || !Array.isArray(raw.materials)) {
    return null
  }
  return {
    claimTier: raw.claim_tier,
    claimBoundary: raw.claim_boundary,
    count: raw.count ?? raw.materials.length,
    materials: raw.materials.map(toCamel),
  }
}

export interface MaterialsFetchResult {
  readonly materials: MaterialRecord[]
  readonly source: 'live' | 'fallback'
  readonly claimTier: string
  readonly claimBoundary: string
  readonly error?: string
}

export async function fetchMaterials(
  apiBase: string,
  signal?: AbortSignal,
): Promise<MaterialsFetchResult> {
  const url = `${apiBase.replace(/\/$/, '')}/materials/`
  try {
    const res = await fetch(url, { signal })
    if (!res.ok) {
      throw new Error(`materials endpoint returned ${res.status}`)
    }
    const raw = (await res.json()) as RawMaterialsPayload
    const parsed = parseMaterialsPayload(raw)
    if (!parsed) {
      throw new Error('materials payload missing materials array')
    }
    return {
      materials: parsed.materials,
      source: 'live',
      claimTier: parsed.claimTier,
      claimBoundary: parsed.claimBoundary,
    }
  } catch (err) {
    return {
      materials: FALLBACK_MATERIALS,
      source: 'fallback',
      claimTier: TIER_1_BANNER,
      claimBoundary: TIER_1_BOUNDARY,
      error: err instanceof Error ? err.message : String(err),
    }
  }
}

// Formatting helpers for the picker UI — kept here so they share
// behaviour with the typed payload and tests can pin them.
export function formatPascalsAsGPa(pa: number): string {
  const gpa = pa / 1e9
  // ≥ 100 GPa renders as integer (e.g. "210 GPa"); below 100 keeps
  // one decimal to discriminate alloys like 68.9 vs 73.1 GPa.
  return `${gpa.toFixed(gpa >= 100 ? 0 : 1)} GPa`
}

export function formatPascalsAsMPa(pa: number): string {
  return `${Math.round(pa / 1e6)} MPa`
}

export function formatDensity(kgM3: number): string {
  return `${kgM3.toFixed(0)} kg/m³`
}
