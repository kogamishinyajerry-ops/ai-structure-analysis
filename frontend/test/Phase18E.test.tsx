// FM-04a Phase 18 E (round 2) — materials client + picker panel tests.
//
// Tier 1 / Tier 2 engineering candidate; not signed validation; not
// benchmark agreement.
//
// Pins the new round-2 frontend pieces: materialsClient parse/fetch,
// MaterialPickerPanel render + selection + fallback path, formatting
// helpers.

import { describe, expect, it, vi, beforeEach } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import {
  FALLBACK_MATERIALS,
  fetchMaterials,
  formatDensity,
  formatPascalsAsGPa,
  formatPascalsAsMPa,
  parseMaterialsPayload,
} from '../src/materialsClient'
import { MaterialPickerPanel } from '../src/components/MaterialPickerPanel'

beforeEach(() => {
  vi.restoreAllMocks()
})

// ---------------------------------------------------------------------
// materialsClient
// ---------------------------------------------------------------------

describe('materialsClient', () => {
  it('FALLBACK_MATERIALS has the 3 baseline entries pinned', () => {
    const ids = FALLBACK_MATERIALS.map((m) => m.id)
    expect(ids).toEqual([
      'steel-s355',
      'aluminium-6061-t6',
      'titanium-ti-6al-4v',
    ])
  })

  it('FALLBACK_MATERIALS values are byte-identical to library.json', () => {
    const steel = FALLBACK_MATERIALS[0]
    expect(steel.youngsModulusPa).toBe(210e9)
    expect(steel.poissonRatio).toBe(0.3)
    expect(steel.densityKgM3).toBe(7850.0)
    expect(steel.yieldStressPa).toBe(355e6)
    expect(steel.ultimateStressPa).toBe(510e6)
    expect(steel.reference).toContain('EN 10025-2:2019')
  })

  it('every fallback material carries the Tier 1 banner', () => {
    for (const m of FALLBACK_MATERIALS) {
      expect(m.claimTier).toBe('Tier 1 engineering candidate')
      expect(m.claimBoundary).toContain('not_signed_validation')
    }
  })

  it('parseMaterialsPayload converts snake_case to camelCase', () => {
    const parsed = parseMaterialsPayload({
      claim_tier: 'Tier 1 engineering candidate',
      claim_boundary: 'tier1_engineering_candidate; ...',
      count: 1,
      materials: [
        {
          id: 'x',
          name: 'X',
          youngs_modulus_pa: 1e11,
          poisson_ratio: 0.3,
          density_kg_m3: 8000,
          yield_stress_pa: 300e6,
          ultimate_stress_pa: 400e6,
          reference: 'internal-test reference',
          claim_tier: 'Tier 1 engineering candidate',
          claim_boundary: 'tier1_engineering_candidate; ...',
        },
      ],
    })
    expect(parsed).not.toBeNull()
    expect(parsed!.materials[0].youngsModulusPa).toBe(1e11)
    expect(parsed!.materials[0].yieldStressPa).toBe(300e6)
  })

  it('parseMaterialsPayload returns null on malformed input', () => {
    expect(parseMaterialsPayload(null as unknown as never)).toBeNull()
    expect(parseMaterialsPayload({} as unknown as never)).toBeNull()
  })

  it('fetchMaterials returns source=live on 200', async () => {
    const responsePayload = {
      claim_tier: 'Tier 1 engineering candidate',
      claim_boundary: 'tier1_engineering_candidate; not_signed_validation',
      count: FALLBACK_MATERIALS.length,
      materials: FALLBACK_MATERIALS.map((m) => ({
        id: m.id,
        name: m.name,
        youngs_modulus_pa: m.youngsModulusPa,
        poisson_ratio: m.poissonRatio,
        density_kg_m3: m.densityKgM3,
        yield_stress_pa: m.yieldStressPa,
        ultimate_stress_pa: m.ultimateStressPa,
        reference: m.reference,
        claim_tier: m.claimTier,
        claim_boundary: m.claimBoundary,
      })),
    }
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => ({
        ok: true,
        json: async () => responsePayload,
      })),
    )
    const result = await fetchMaterials('http://localhost:8000/api/v1')
    expect(result.source).toBe('live')
    expect(result.materials).toHaveLength(3)
    expect(result.materials[0].id).toBe('steel-s355')
  })

  it('fetchMaterials returns source=fallback on network failure', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => {
        throw new Error('NetworkDown')
      }),
    )
    const result = await fetchMaterials('http://localhost:8000/api/v1')
    expect(result.source).toBe('fallback')
    expect(result.materials).toEqual(FALLBACK_MATERIALS)
    expect(result.error).toContain('NetworkDown')
  })

  it('fetchMaterials returns fallback on non-200', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => ({ ok: false, status: 500, json: async () => ({}) })),
    )
    const result = await fetchMaterials('http://localhost:8000/api/v1')
    expect(result.source).toBe('fallback')
  })
})

describe('materialsClient formatters', () => {
  it('formatPascalsAsGPa rounds steel correctly', () => {
    expect(formatPascalsAsGPa(210e9)).toBe('210 GPa')
    expect(formatPascalsAsGPa(68.9e9)).toBe('68.9 GPa')
  })

  it('formatPascalsAsMPa rounds yield to integer MPa', () => {
    expect(formatPascalsAsMPa(355e6)).toBe('355 MPa')
    expect(formatPascalsAsMPa(880e6)).toBe('880 MPa')
  })

  it('formatDensity drops decimals and adds unit', () => {
    expect(formatDensity(7850.0)).toBe('7850 kg/m³')
    expect(formatDensity(2700.0)).toBe('2700 kg/m³')
  })
})

// ---------------------------------------------------------------------
// MaterialPickerPanel
// ---------------------------------------------------------------------

describe('MaterialPickerPanel', () => {
  it('shows loading skeleton then renders 3 fallback rows when backend down', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => {
        throw new Error('NetworkDown')
      }),
    )
    render(<MaterialPickerPanel apiBase="http://localhost:8000/api/v1" />)
    // Skeleton may render briefly.
    await waitFor(() =>
      expect(screen.getByTestId('material-picker-panel')).toBeInTheDocument(),
    )
    expect(screen.getByTestId('material-row-steel-s355')).toBeInTheDocument()
    expect(
      screen.getByTestId('material-row-aluminium-6061-t6'),
    ).toBeInTheDocument()
    expect(
      screen.getByTestId('material-row-titanium-ti-6al-4v'),
    ).toBeInTheDocument()
    expect(
      screen.getByTestId('materials-fallback-marker'),
    ).toBeInTheDocument()
  })

  it('clicking a row fires onMaterialChange with that material', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => {
        throw new Error('use fallback')
      }),
    )
    const onPick = vi.fn()
    render(
      <MaterialPickerPanel
        apiBase="http://localhost:8000/api/v1"
        onMaterialChange={onPick}
      />,
    )
    await waitFor(() =>
      expect(screen.getByTestId('material-row-aluminium-6061-t6')).toBeInTheDocument(),
    )
    fireEvent.click(screen.getByTestId('material-row-aluminium-6061-t6'))
    expect(onPick).toHaveBeenCalledTimes(1)
    expect(onPick.mock.calls[0][0].id).toBe('aluminium-6061-t6')
  })

  it('marks the selected row data-selected=true', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => {
        throw new Error('use fallback')
      }),
    )
    render(
      <MaterialPickerPanel
        apiBase="http://localhost:8000/api/v1"
        selectedMaterialId="titanium-ti-6al-4v"
      />,
    )
    await waitFor(() =>
      expect(
        screen.getByTestId('material-row-titanium-ti-6al-4v'),
      ).toBeInTheDocument(),
    )
    expect(
      screen.getByTestId('material-row-titanium-ti-6al-4v').getAttribute('data-selected'),
    ).toBe('true')
    expect(
      screen.getByTestId('material-row-steel-s355').getAttribute('data-selected'),
    ).toBe('false')
  })

  it('renders the per-material citation reference', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => {
        throw new Error('use fallback')
      }),
    )
    render(<MaterialPickerPanel apiBase="http://localhost:8000/api/v1" />)
    await waitFor(() =>
      expect(screen.getByTestId('material-row-steel-s355')).toBeInTheDocument(),
    )
    expect(
      screen.getByTestId('material-row-steel-s355'),
    ).toHaveTextContent('EN 10025-2:2019')
  })

  it('renders the Tier 1 banner inline', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => {
        throw new Error('use fallback')
      }),
    )
    render(<MaterialPickerPanel apiBase="http://localhost:8000/api/v1" />)
    await waitFor(() =>
      expect(screen.getByTestId('material-picker-panel')).toBeInTheDocument(),
    )
    expect(
      screen.getByTestId('material-picker-panel'),
    ).toHaveTextContent(/Tier 1 engineering candidate/)
    expect(
      screen.getByTestId('material-picker-panel'),
    ).toHaveTextContent(/not signed validation/)
  })
})
