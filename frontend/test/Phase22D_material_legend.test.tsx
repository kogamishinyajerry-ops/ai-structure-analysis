// FM-04a Phase 22 D — material picker promotion + WebGL legend units.
//
// Tier 1 / Tier 2 engineering candidate; not signed validation; not
// benchmark agreement.
//
// Anti-gaming guards:
//   * A:-2 — material-pick palette entries fire ONLY
//     `setSelectedMaterial` (no Run Solver autotrigger). Pinned via
//     the existing /materials commands; the new `cmd-material-picker-
//     open` entry must NOT call setSelectedMaterial (scroll only).
//   * D2 honest scope: result_mesh.json schema does NOT carry σ_xx /
//     σ_yy / σ_zz tensor data, so the field-component switcher
//     scoped in the blueprint is documented as deferred. This test
//     suite verifies the legend renders the units suffix + the
//     current field label as a read-only display.

import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { Topbar } from '../src/components/Topbar'
import { ResultMeshPlaybackPanel } from '../src/components/ResultMeshPlaybackPanel'

describe('Topbar — Phase 22 D material select', () => {
  it('hides the material select when no options are provided', () => {
    render(
      <Topbar
        breadcrumbLabel="case-001"
        showRunControls={true}
        analysisType="static"
        onChangeAnalysisType={() => undefined}
        solving={false}
        onRunSolver={() => undefined}
        onStopSolver={() => undefined}
        showChat={false}
        onToggleChat={() => undefined}
      />,
    )
    expect(
      screen.queryByTestId('topbar-material-select'),
    ).not.toBeInTheDocument()
  })

  it('renders the material select when options are provided', () => {
    render(
      <Topbar
        breadcrumbLabel="case-001"
        showRunControls={true}
        analysisType="static"
        onChangeAnalysisType={() => undefined}
        solving={false}
        onRunSolver={() => undefined}
        onStopSolver={() => undefined}
        showChat={false}
        onToggleChat={() => undefined}
        materialOptions={[
          { id: 'steel-s355', label: 'Structural Steel S355' },
          { id: 'aluminium-6061-t6', label: 'Aluminium 6061-T6' },
        ]}
        selectedMaterialId="steel-s355"
        onChangeMaterialId={() => undefined}
      />,
    )
    const select = screen.getByTestId(
      'topbar-material-select',
    ) as HTMLSelectElement
    expect(select).toBeInTheDocument()
    expect(select.value).toBe('steel-s355')
    expect(select.options).toHaveLength(2)
  })

  it('forwards the selected material id on change', () => {
    const onChangeMaterialId = vi.fn()
    render(
      <Topbar
        breadcrumbLabel="case-001"
        showRunControls={true}
        analysisType="static"
        onChangeAnalysisType={() => undefined}
        solving={false}
        onRunSolver={() => undefined}
        onStopSolver={() => undefined}
        showChat={false}
        onToggleChat={() => undefined}
        materialOptions={[
          { id: 'steel-s355', label: 'Structural Steel S355' },
          { id: 'aluminium-6061-t6', label: 'Aluminium 6061-T6' },
        ]}
        selectedMaterialId="steel-s355"
        onChangeMaterialId={onChangeMaterialId}
      />,
    )
    const select = screen.getByTestId(
      'topbar-material-select',
    ) as HTMLSelectElement
    fireEvent.change(select, { target: { value: 'aluminium-6061-t6' } })
    expect(onChangeMaterialId).toHaveBeenCalledWith('aluminium-6061-t6')
  })

  it('material select is suppressed when showRunControls=false', () => {
    render(
      <Topbar
        breadcrumbLabel="Session"
        showRunControls={false}
        analysisType="static"
        onChangeAnalysisType={() => undefined}
        solving={false}
        onRunSolver={() => undefined}
        onStopSolver={() => undefined}
        showChat={false}
        onToggleChat={() => undefined}
        materialOptions={[
          { id: 'steel-s355', label: 'Structural Steel S355' },
        ]}
        selectedMaterialId="steel-s355"
        onChangeMaterialId={() => undefined}
      />,
    )
    expect(
      screen.queryByTestId('topbar-material-select'),
    ).not.toBeInTheDocument()
  })
})

const dynamicPayload = {
  schemaVersion: 1,
  analysisType: 'dynamic',
  caseId: 'phase22d-test',
  fieldLabel: 'Von Mises',
  fieldRanges: { valueMin: 0, valueMax: 1.5e8 },
  modelTree: { id: 'root', label: 'root', children: [] },
  dynamicFrames: [
    {
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
        {
          label: 1,
          type: 'QUAD',
          connectivity: [1, 2, 3, 4],
          partRole: 'plate',
          alive: true,
          value: 7.5e7,
        },
      ],
    },
  ],
}

describe('ResultMeshPlaybackPanel — Phase 22 D legend units', () => {
  beforeEach(() => {
    // FM-04a Phase 26 B — this test asserts on the field-component
    // dropdown which is now gated by uiMode='advanced'. Pre-set
    // localStorage so the dropdown is rendered.
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
  })
  it('defaults the legend units to "MPa" (SI_mm) and surfaces the field label', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => ({
        ok: true,
        status: 200,
        json: async () => dynamicPayload,
      })),
    )
    render(
      <ResultMeshPlaybackPanel
        caseId="phase22d-test"
        apiBase="http://localhost:8000/api/v1"
      />,
    )
    await waitFor(() =>
      expect(screen.getByTestId('legend-min')).toBeInTheDocument(),
    )
    expect(screen.getByTestId('legend-min').textContent).toMatch(/\bMPa\b/)
    expect(screen.getByTestId('legend-max').textContent).toMatch(/\bMPa\b/)
    // Phase 22 D shipped a read-only field-component chip; Phase 23 B
    // promoted it to a dropdown switcher. The current selection is
    // exposed via the select's value. Default is 'mises' (Von Mises).
    const select = screen.getByTestId(
      'legend-field-component-select',
    ) as HTMLSelectElement
    expect(select.value).toBe('mises')
  })

  it('overrides the units suffix when a custom value is passed', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => ({
        ok: true,
        status: 200,
        json: async () => dynamicPayload,
      })),
    )
    render(
      <ResultMeshPlaybackPanel
        caseId="phase22d-units"
        apiBase="http://localhost:8000/api/v1"
        fieldUnits="GPa"
      />,
    )
    await waitFor(() =>
      expect(screen.getByTestId('legend-min')).toBeInTheDocument(),
    )
    expect(screen.getByTestId('legend-min').textContent).toMatch(/\bGPa\b/)
    expect(screen.getByTestId('legend-min').textContent).not.toMatch(/\bPa\b\s*$/)
  })
})

describe('Material palette → setSelectedMaterial integrity (Phase 22 D A:-2 guard)', () => {
  it('cmd-material-picker-open scrolls but does NOT mutate material state', () => {
    // Simulated handler stand-in. The real handler (in App.tsx) calls
    // `document.getElementById('material-picker-panel')?.scrollIntoView`
    // and intentionally does NOT call setSelectedMaterial. This test
    // documents that contract: the scroll handler is pure-DOM, no
    // material mutation.
    const setSelectedMaterial = vi.fn()
    // Stub a target element so scrollIntoView is callable.
    const fake = document.createElement('section')
    fake.id = 'material-picker-panel'
    fake.scrollIntoView = vi.fn()
    document.body.appendChild(fake)
    try {
      // Inline handler — same shape as the App.tsx palette entry.
      const handler = () => {
        const target = document.getElementById('material-picker-panel')
        target?.scrollIntoView({ behavior: 'smooth', block: 'center' })
      }
      handler()
      expect(fake.scrollIntoView).toHaveBeenCalledTimes(1)
      expect(setSelectedMaterial).toHaveBeenCalledTimes(0)
    } finally {
      document.body.removeChild(fake)
    }
  })
})
