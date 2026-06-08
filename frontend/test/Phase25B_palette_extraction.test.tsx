// FM-04a Phase 25 B — palette + topbar config extraction tests.
//
// Tier 1 / Tier 2 engineering candidate; not signed validation; not
// benchmark agreement.
//
// Phase 25 B extracts the Cmd-K palette command builder + topbar
// material option mapper from App.tsx into
// frontend/src/state/paletteCommands.ts for LOC discipline.
//
// HONEST SCOPE: Phase 25 B reduces App.tsx by ~52 LOC (1498 → 1446);
// blueprint target of <1300 NOT met. Full reducer / view-model
// extraction is a multi-slice refactor recorded as a Phase 26 honest
// gap. This test pins the extraction that DID happen.
//
// Anti-gaming guard B:-1 — App.tsx LOC measurement is verified in
// audit, not in this test (Vitest doesn't read its own source size).

import { describe, expect, it, vi } from 'vitest'

import {
  buildPaletteCommands,
  buildTopbarMaterialOptions,
  type PaletteActions,
} from '../src/state/paletteCommands'
import type { MaterialRecord } from '../src/materialsClient'

const stubMaterials: readonly MaterialRecord[] = [
  { id: 'steel-s355', name: 'Steel S355', reference: 'EN 10025-2:2019', source: 'library' },
  { id: 'aluminium-6061-t6', name: 'Aluminium 6061-T6', reference: 'MMPDS', source: 'library' },
  { id: 'ti-6al-4v', name: 'Titanium Ti-6Al-4V', reference: 'AMS 4928', source: 'library' },
]

function makeStubActions(overrides: Partial<PaletteActions> = {}): PaletteActions {
  return {
    setActiveTab: vi.fn(),
    runSolverFromPalette: vi.fn(),
    pickMaterialByIndex: vi.fn(),
    openMaterialPickerPanel: vi.fn(),
    closePalette: vi.fn(),
    activeCaseId: null,
    materials: stubMaterials,
    ...overrides,
  }
}

describe('Phase 25 B — buildPaletteCommands', () => {
  it('returns navigation + solver + per-material + picker-open + close commands', () => {
    const actions = makeStubActions()
    const commands = buildPaletteCommands(actions)
    const ids = commands.map((c) => c.id)
    expect(ids).toEqual([
      'cmd-switch-tab-visual',
      'cmd-switch-tab-narrative',
      'cmd-switch-tab-exploration',
      'cmd-run-solver',
      'cmd-pick-material-steel-s355',
      'cmd-pick-material-aluminium-6061-t6',
      'cmd-pick-material-ti-6al-4v',
      'cmd-material-picker-open',
      'cmd-close-palette',
    ])
  })

  it('wires setActiveTab handler for each tab command', () => {
    const setActiveTab = vi.fn()
    const commands = buildPaletteCommands(makeStubActions({ setActiveTab }))
    commands.find((c) => c.id === 'cmd-switch-tab-visual')?.handler()
    commands.find((c) => c.id === 'cmd-switch-tab-narrative')?.handler()
    commands.find((c) => c.id === 'cmd-switch-tab-exploration')?.handler()
    expect(setActiveTab).toHaveBeenNthCalledWith(1, 'visual')
    expect(setActiveTab).toHaveBeenNthCalledWith(2, 'report')
    expect(setActiveTab).toHaveBeenNthCalledWith(3, 'explore')
  })

  it('cmd-run-solver description shows activeCaseId when present', () => {
    const commands = buildPaletteCommands(
      makeStubActions({ activeCaseId: 'GS-101-demo-unsigned' }),
    )
    const run = commands.find((c) => c.id === 'cmd-run-solver')
    expect(run?.description).toContain('GS-101-demo-unsigned')
  })

  it('cmd-run-solver description shows "no case" hint when activeCaseId is null', () => {
    const commands = buildPaletteCommands(makeStubActions({ activeCaseId: null }))
    const run = commands.find((c) => c.id === 'cmd-run-solver')
    expect(run?.description).toContain('No case selected')
  })

  it('cmd-pick-material-<id> handler calls pickMaterialByIndex with the right index', () => {
    const pickMaterialByIndex = vi.fn()
    const commands = buildPaletteCommands(makeStubActions({ pickMaterialByIndex }))
    commands.find((c) => c.id === 'cmd-pick-material-aluminium-6061-t6')?.handler()
    expect(pickMaterialByIndex).toHaveBeenCalledWith(1)
  })

  it('cmd-close-palette handler calls closePalette', () => {
    const closePalette = vi.fn()
    const commands = buildPaletteCommands(makeStubActions({ closePalette }))
    commands.find((c) => c.id === 'cmd-close-palette')?.handler()
    expect(closePalette).toHaveBeenCalled()
  })

  it('builder is pure (same input → same output structure)', () => {
    const a = buildPaletteCommands(makeStubActions())
    const b = buildPaletteCommands(makeStubActions())
    expect(a.map((c) => c.id)).toEqual(b.map((c) => c.id))
  })

  it('extending the materials list adds one command per new entry', () => {
    const extended: MaterialRecord[] = [
      ...stubMaterials,
      { id: 'inconel-718', name: 'Inconel 718', reference: 'AMS 5662', source: 'library' },
    ]
    const commands = buildPaletteCommands(makeStubActions({ materials: extended }))
    expect(commands.map((c) => c.id)).toContain('cmd-pick-material-inconel-718')
  })
})

describe('Phase 25 B — buildTopbarMaterialOptions', () => {
  it('maps MaterialRecord[] → {id, label}[]', () => {
    expect(buildTopbarMaterialOptions(stubMaterials)).toEqual([
      { id: 'steel-s355', label: 'Steel S355' },
      { id: 'aluminium-6061-t6', label: 'Aluminium 6061-T6' },
      { id: 'ti-6al-4v', label: 'Titanium Ti-6Al-4V' },
    ])
  })

  it('returns empty array for empty input', () => {
    expect(buildTopbarMaterialOptions([])).toEqual([])
  })
})
