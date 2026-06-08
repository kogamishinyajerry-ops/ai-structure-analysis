// FM-04a Phase 43 Slice 4b — colormap selector (panel UI) tests.
//
// Tier 1 engineering candidate; not signed validation. Additive suite.
// Verifies the in-panel colormap <select>: it offers every colormap, defaults
// to spectral, and — critically for honesty — switching it updates the legend
// gradient bar so the legend can never contradict the (re-colored) mesh.

import { describe, expect, it, beforeEach, afterEach, vi } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'

import { ResultMeshPlaybackPanel } from '../src/components/ResultMeshPlaybackPanel'
import { COLORMAP_IDS } from '../src/components/colormaps'

beforeEach(() => {
  // Render the full legend cluster (the field-component switcher shares it and
  // is advanced-gated; the colormap select is not, but advanced keeps parity
  // with the Phase23B harness).
  try {
    window.localStorage.setItem('fm04a.ui.mode.v1', 'advanced')
  } catch {
    /* SSR fallback */
  }
})
afterEach(() => {
  try {
    window.localStorage.removeItem('fm04a.ui.mode.v1')
  } catch {
    /* SSR fallback */
  }
  vi.restoreAllMocks()
})

const frame = {
  frame: 0,
  timeMs: 0,
  fieldLabel: 'Von Mises',
  nodes: [
    { label: 1, coordinates: [0, 0, 0] },
    { label: 2, coordinates: [1, 0, 0] },
    { label: 3, coordinates: [1, 1, 0] },
    { label: 4, coordinates: [0, 1, 0] },
  ],
  elements: [
    { label: 1, type: 'QUAD', connectivity: [1, 2, 3, 4], partRole: 'plate', alive: true, value: 100 },
  ],
}

function stubFetch(caseId: string) {
  vi.stubGlobal(
    'fetch',
    vi.fn(async () => ({
      ok: true,
      status: 200,
      json: async () => ({
        schemaVersion: 1,
        analysisType: 'dynamic',
        caseId,
        fieldRanges: { valueMin: 0, valueMax: 200 },
        modelTree: { id: 'root', label: 'root', children: [] },
        dynamicFrames: [frame],
      }),
    })),
  )
}

describe('ResultMeshPlaybackPanel — Phase 43 Slice 4b colormap selector', () => {
  it('renders the colormap select with every colormap, defaulting to spectral', async () => {
    stubFetch('p43-cmap-options')
    render(
      <ResultMeshPlaybackPanel caseId="p43-cmap-options" apiBase="http://localhost:8000/api/v1" />,
    )
    await waitFor(() =>
      expect(screen.getByTestId('legend-colormap-select')).toBeInTheDocument(),
    )
    const select = screen.getByTestId('legend-colormap-select') as HTMLSelectElement
    expect(select.value).toBe('spectral')
    const values = Array.from(select.options).map((o) => o.value)
    expect(values).toEqual([...COLORMAP_IDS])
  })

  it('switching the colormap updates the select AND the legend gradient bar', async () => {
    stubFetch('p43-cmap-switch')
    render(
      <ResultMeshPlaybackPanel caseId="p43-cmap-switch" apiBase="http://localhost:8000/api/v1" />,
    )
    await waitFor(() =>
      expect(screen.getByTestId('legend-colormap-select')).toBeInTheDocument(),
    )
    const select = screen.getByTestId('legend-colormap-select') as HTMLSelectElement
    const bar = screen.getByTestId('legend-gradient-bar')
    const before = bar.style.background

    fireEvent.change(select, { target: { value: 'grayscale' } })

    expect(select.value).toBe('grayscale')
    // Honesty: the legend bar must follow the active colormap — it can never
    // keep showing the spectral ramp while the mesh is re-colored.
    expect(bar.style.background).not.toBe(before)
    expect(bar.style.background).toContain('linear-gradient')
  })
})
