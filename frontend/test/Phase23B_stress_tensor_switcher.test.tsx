// FM-04a Phase 23 B — σ-tensor schema upgrade + Mises/component switcher tests.
//
// Tier 1 / Tier 2 engineering candidate; not signed validation; not
// benchmark agreement.
//
// Phase 22 D shipped a read-only field-component label on the WebGL
// legend; the per-component switcher was deferred because the
// schema carried only a scalar `value` per element. Phase 23 B
// extends the schema with optional `stressTensor` and implements
// the math + UI switcher.
//
// Anti-gaming guards:
//   * B:-1 — Von Mises pin uses analytical-known inputs: uniaxial
//     σ_xx=100 → σ_vm=100; hydrostatic (100,100,100) → σ_vm=0;
//     pure shear τ → σ_vm=√3·τ.
//   * B:-2 — when stressTensor is absent the switcher MUST stay
//     disabled (no silent zero-fill coercion).

import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import {
  computeVonMises,
  computePrincipalStresses,
  componentValue,
  type StressTensor,
} from '../src/stressDerivatives'
import { ResultMeshPlaybackPanel } from '../src/components/ResultMeshPlaybackPanel'

const ZERO_TENSOR: StressTensor = {
  sxx: 0,
  syy: 0,
  szz: 0,
  sxy: 0,
  syz: 0,
  sxz: 0,
}

describe('computeVonMises — analytical pins', () => {
  it('uniaxial σ_xx=100 → σ_vm = 100', () => {
    const t: StressTensor = { ...ZERO_TENSOR, sxx: 100 }
    expect(computeVonMises(t)).toBeCloseTo(100, 6)
  })

  it('hydrostatic (100,100,100) → σ_vm = 0', () => {
    const t: StressTensor = { ...ZERO_TENSOR, sxx: 100, syy: 100, szz: 100 }
    expect(computeVonMises(t)).toBeCloseTo(0, 6)
  })

  it('pure shear τ_xy=50 → σ_vm = √3 · 50', () => {
    const t: StressTensor = { ...ZERO_TENSOR, sxy: 50 }
    expect(computeVonMises(t)).toBeCloseTo(Math.sqrt(3) * 50, 4)
  })

  it('zero tensor → σ_vm = 0', () => {
    expect(computeVonMises(ZERO_TENSOR)).toBeCloseTo(0, 6)
  })
})

describe('computePrincipalStresses — closed-form eigenvalue pins', () => {
  it('diagonal tensor returns its components sorted descending', () => {
    const t: StressTensor = { ...ZERO_TENSOR, sxx: 50, syy: 100, szz: 25 }
    const [s1, s2, s3] = computePrincipalStresses(t)
    expect(s1).toBeCloseTo(100, 4)
    expect(s2).toBeCloseTo(50, 4)
    expect(s3).toBeCloseTo(25, 4)
  })

  it('uniaxial σ_xx=100 → [100, 0, 0]', () => {
    const t: StressTensor = { ...ZERO_TENSOR, sxx: 100 }
    const [s1, s2, s3] = computePrincipalStresses(t)
    expect(s1).toBeCloseTo(100, 4)
    expect(s2).toBeCloseTo(0, 4)
    expect(s3).toBeCloseTo(0, 4)
  })

  it('plane stress σ_xx=σ_yy=100, τ_xy=50 → [150, 50, 0]', () => {
    // For plane stress with σ_xx=σ_yy=σ, τ_xy=τ:
    //   In-plane principals σ ± √(0 + τ²) = 100 ± 50 → 150, 50.
    //   Out-of-plane σ_z = 0.
    // Sorted descending: [150, 50, 0].
    const t: StressTensor = { ...ZERO_TENSOR, sxx: 100, syy: 100, sxy: 50 }
    const [s1, s2, s3] = computePrincipalStresses(t)
    expect(s1).toBeCloseTo(150, 4)
    expect(s2).toBeCloseTo(50, 4)
    expect(s3).toBeCloseTo(0, 4)
  })
})

describe('componentValue — switcher pin', () => {
  it('returns the named component when tensor present', () => {
    const t: StressTensor = { sxx: 10, syy: 20, szz: 30, sxy: 1, syz: 2, sxz: 3 }
    expect(componentValue(t, 'sxx', 999)).toBeCloseTo(10, 6)
    expect(componentValue(t, 'syy', 999)).toBeCloseTo(20, 6)
    expect(componentValue(t, 'szz', 999)).toBeCloseTo(30, 6)
    expect(componentValue(t, 'sxy', 999)).toBeCloseTo(1, 6)
    expect(componentValue(t, 'syz', 999)).toBeCloseTo(2, 6)
    expect(componentValue(t, 'sxz', 999)).toBeCloseTo(3, 6)
  })

  it('returns Mises when component=mises', () => {
    const t: StressTensor = { ...ZERO_TENSOR, sxx: 100 }
    expect(componentValue(t, 'mises', 999)).toBeCloseTo(100, 6)
  })

  it('returns max-principal when component=max_principal', () => {
    const t: StressTensor = { ...ZERO_TENSOR, sxx: 100, syy: 100, sxy: 50 }
    expect(componentValue(t, 'max_principal', 999)).toBeCloseTo(150, 4)
  })

  it('returns fallback when tensor is null (B:-2 anti-gaming guard)', () => {
    expect(componentValue(null, 'mises', 42)).toBe(42)
  })

  it('returns fallback when tensor is undefined', () => {
    expect(componentValue(undefined, 'sxx', 7)).toBe(7)
  })
})

// =====================================================================
// UI integration — the legend dropdown switcher
// =====================================================================

function installWebGLStub() {
  const originalGetContext = HTMLCanvasElement.prototype.getContext
  const stubGl = {
    getExtension: () => null,
    getParameter: () => 0,
    getShaderPrecisionFormat: () => ({ precision: 8, rangeMin: 0, rangeMax: 0 }),
    createBuffer: () => ({}),
    bindBuffer: () => undefined,
    bufferData: () => undefined,
    createShader: () => ({}),
    shaderSource: () => undefined,
    compileShader: () => undefined,
    getShaderParameter: () => true,
    createProgram: () => ({}),
    attachShader: () => undefined,
    linkProgram: () => undefined,
    getProgramParameter: () => true,
    useProgram: () => undefined,
    getUniformLocation: () => ({}),
    getAttribLocation: () => 0,
    enableVertexAttribArray: () => undefined,
    vertexAttribPointer: () => undefined,
    enable: () => undefined,
    disable: () => undefined,
    cullFace: () => undefined,
    frontFace: () => undefined,
    blendFunc: () => undefined,
    depthFunc: () => undefined,
    clearColor: () => undefined,
    clear: () => undefined,
    viewport: () => undefined,
    drawArrays: () => undefined,
    drawElements: () => undefined,
    activeTexture: () => undefined,
    bindTexture: () => undefined,
    pixelStorei: () => undefined,
    texParameteri: () => undefined,
    texImage2D: () => undefined,
    deleteTexture: () => undefined,
    deleteBuffer: () => undefined,
    deleteShader: () => undefined,
    deleteProgram: () => undefined,
    canvas: null as unknown,
  }
  HTMLCanvasElement.prototype.getContext = function (
    this: HTMLCanvasElement,
    contextId: string,
    ..._rest: unknown[]
  ): unknown {
    if (
      contextId === 'webgl'
      || contextId === 'webgl2'
      || contextId === 'experimental-webgl'
    ) {
      stubGl.canvas = this
      return stubGl
    }
    return originalGetContext.call(this, contextId)
  } as typeof HTMLCanvasElement.prototype.getContext
  return () => {
    HTMLCanvasElement.prototype.getContext = originalGetContext
  }
}

let restoreGetContext: (() => void) | null = null
beforeEach(() => {
  restoreGetContext = installWebGLStub()
})
afterEach(() => {
  restoreGetContext?.()
  restoreGetContext = null
})

const baseFrame = {
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
      value: 100,
    },
  ],
}

const tensorFrame = {
  ...baseFrame,
  elements: [
    {
      ...baseFrame.elements[0],
      stressTensor: { sxx: 100, syy: 50, szz: 25, sxy: 10, syz: 5, sxz: 2 },
    },
  ],
}

describe('ResultMeshPlaybackPanel — Phase 23 B switcher', () => {
  it('dropdown is DISABLED when frame elements have no tensor (B:-2 guard)', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => ({
        ok: true,
        status: 200,
        json: async () => ({
          schemaVersion: 1,
          analysisType: 'dynamic',
          caseId: 'phase23b-no-tensor',
          fieldRanges: { valueMin: 0, valueMax: 200 },
          modelTree: { id: 'root', label: 'root', children: [] },
          dynamicFrames: [baseFrame],
        }),
      })),
    )
    render(
      <ResultMeshPlaybackPanel
        caseId="phase23b-no-tensor"
        apiBase="http://localhost:8000/api/v1"
      />,
    )
    await waitFor(() =>
      expect(
        screen.getByTestId('legend-field-component-select'),
      ).toBeInTheDocument(),
    )
    const select = screen.getByTestId(
      'legend-field-component-select',
    ) as HTMLSelectElement
    expect(select.disabled).toBe(true)
  })

  it('dropdown is ENABLED when at least one element has a tensor', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => ({
        ok: true,
        status: 200,
        json: async () => ({
          schemaVersion: 1,
          analysisType: 'dynamic',
          caseId: 'phase23b-tensor',
          fieldRanges: { valueMin: 0, valueMax: 200 },
          modelTree: { id: 'root', label: 'root', children: [] },
          dynamicFrames: [tensorFrame],
        }),
      })),
    )
    render(
      <ResultMeshPlaybackPanel
        caseId="phase23b-tensor"
        apiBase="http://localhost:8000/api/v1"
      />,
    )
    await waitFor(() =>
      expect(
        screen.getByTestId('legend-field-component-select'),
      ).toBeInTheDocument(),
    )
    const select = screen.getByTestId(
      'legend-field-component-select',
    ) as HTMLSelectElement
    expect(select.disabled).toBe(false)
    expect(select.value).toBe('mises')
  })

  it('switching the dropdown changes the value', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => ({
        ok: true,
        status: 200,
        json: async () => ({
          schemaVersion: 1,
          analysisType: 'dynamic',
          caseId: 'phase23b-switch',
          fieldRanges: { valueMin: 0, valueMax: 200 },
          modelTree: { id: 'root', label: 'root', children: [] },
          dynamicFrames: [tensorFrame],
        }),
      })),
    )
    render(
      <ResultMeshPlaybackPanel
        caseId="phase23b-switch"
        apiBase="http://localhost:8000/api/v1"
      />,
    )
    await waitFor(() =>
      expect(
        screen.getByTestId('legend-field-component-select'),
      ).toBeInTheDocument(),
    )
    const select = screen.getByTestId(
      'legend-field-component-select',
    ) as HTMLSelectElement
    fireEvent.change(select, { target: { value: 'sxx' } })
    expect(select.value).toBe('sxx')
    fireEvent.change(select, { target: { value: 'max_principal' } })
    expect(select.value).toBe('max_principal')
  })

  it('all expected component options are present in the dropdown', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => ({
        ok: true,
        status: 200,
        json: async () => ({
          schemaVersion: 1,
          analysisType: 'dynamic',
          caseId: 'phase23b-options',
          fieldRanges: { valueMin: 0, valueMax: 200 },
          modelTree: { id: 'root', label: 'root', children: [] },
          dynamicFrames: [tensorFrame],
        }),
      })),
    )
    render(
      <ResultMeshPlaybackPanel
        caseId="phase23b-options"
        apiBase="http://localhost:8000/api/v1"
      />,
    )
    await waitFor(() =>
      expect(
        screen.getByTestId('legend-field-component-select'),
      ).toBeInTheDocument(),
    )
    const select = screen.getByTestId(
      'legend-field-component-select',
    ) as HTMLSelectElement
    const values = Array.from(select.options).map((o) => o.value)
    expect(values).toEqual([
      'mises',
      'sxx',
      'syy',
      'szz',
      'sxy',
      'syz',
      'sxz',
      'max_principal',
      'min_principal',
    ])
  })
})
