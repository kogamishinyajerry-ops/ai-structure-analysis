// FM-04a Phase 22 B — WebGL viewport depth (animation + section + magnification).
//
// The Phase 21 C three.js viewport rendered single-frame static
// scenes. Phase 22 B adds:
//   * frame-to-frame interpolation (animTInterp 0 → 1)
//   * deformation magnification (scales (deformed - undeformed))
//   * section-cut clipping plane (hide one half along an axis)
//
// These tests pin the pure-function math (`buildNodeCoords`) and the
// parent-panel UI wiring (depth control toggles + section-cut state).
//
// Anti-gaming guards:
//   * Interpolation at t=0 lands on the SOURCE frame; at t=1 lands on
//     the NEXT frame; at t=0.5 lands on the midpoint. No rebuckling
//     of bounds.
//   * Deformation magnification ONLY scales the `deformed - undeformed`
//     delta — undeformed nodes stay put. Pinning this prevents drift
//     where the magnification accidentally multiplies the absolute
//     coordinate.
//   * Section-cut UI: toggling the checkbox creates a default cut
//     state; toggling off returns the state to null.
//
// Tier 1 / Tier 2 engineering candidate; not signed validation; not
// benchmark agreement.

import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { buildNodeCoords } from '../src/components/ResultMeshWebGLViewport'
import { ResultMeshPlaybackPanel } from '../src/components/ResultMeshPlaybackPanel'

const frameA = {
  frame: 0,
  timeMs: 0,
  fieldLabel: 'stress',
  nodes: [
    { label: 1, coordinates: [0, 0, 0], deformed: [0, 0, 0] },
    { label: 2, coordinates: [1, 0, 0], deformed: [1.01, 0, 0] },
    { label: 3, coordinates: [1, 1, 0], deformed: [1.01, 1.005, 0] },
    { label: 4, coordinates: [0, 1, 0], deformed: [0, 1.005, 0] },
  ],
  elements: [
    {
      label: 1,
      type: 'QUAD',
      connectivity: [1, 2, 3, 4],
      partRole: 'plate',
      alive: true,
      value: 1.5,
    },
  ],
}

// Frame B: a "next" frame where node 2 has translated to x=2.
const frameB = {
  frame: 1,
  timeMs: 1,
  fieldLabel: 'stress',
  nodes: [
    { label: 1, coordinates: [0, 0, 0], deformed: [0, 0, 0] },
    { label: 2, coordinates: [1, 0, 0], deformed: [2, 0, 0] },
    { label: 3, coordinates: [1, 1, 0], deformed: [2, 1, 0] },
    { label: 4, coordinates: [0, 1, 0], deformed: [0, 1, 0] },
  ],
  elements: [
    {
      label: 1,
      type: 'QUAD',
      connectivity: [1, 2, 3, 4],
      partRole: 'plate',
      alive: true,
      value: 1.5,
    },
  ],
}

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
      contextId === 'webgl' ||
      contextId === 'webgl2' ||
      contextId === 'experimental-webgl'
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

describe('buildNodeCoords — frame interpolation pin', () => {
  it('at tInterp=0 returns the source frame deformed coords', () => {
    const out = buildNodeCoords(frameA, frameB, 0, 1)
    expect(out.get(2)).toEqual([1.01, 0, 0])
  })

  it('at tInterp=1 returns the next frame deformed coords', () => {
    const out = buildNodeCoords(frameA, frameB, 1, 1)
    const node2 = out.get(2)!
    expect(node2[0]).toBeCloseTo(2, 4)
    expect(node2[1]).toBeCloseTo(0, 4)
  })

  it('at tInterp=0.5 returns the midpoint between source and next', () => {
    const out = buildNodeCoords(frameA, frameB, 0.5, 1)
    const node2 = out.get(2)!
    // Source x=1.01, next x=2 → midpoint = 1.505.
    expect(node2[0]).toBeCloseTo(1.505, 4)
  })

  it('with nextFrame=null, tInterp is ignored', () => {
    const out = buildNodeCoords(frameA, null, 0.5, 1)
    expect(out.get(2)).toEqual([1.01, 0, 0])
  })

  it('clamps tInterp > 1 to the next frame', () => {
    const out = buildNodeCoords(frameA, frameB, 2, 1)
    const node2 = out.get(2)!
    expect(node2[0]).toBeCloseTo(2, 4)
  })

  it('clamps tInterp < 0 to the source frame', () => {
    const out = buildNodeCoords(frameA, frameB, -1, 1)
    expect(out.get(2)).toEqual([1.01, 0, 0])
  })
})

describe('buildNodeCoords — deformation magnification pin', () => {
  it('at scale=1 returns the true deformed coordinates', () => {
    const out = buildNodeCoords(frameA, null, 0, 1)
    expect(out.get(2)).toEqual([1.01, 0, 0])
  })

  it('at scale=100 amplifies displacement, not absolute position', () => {
    // Node 2: undeformed=(1,0,0), deformed=(1.01,0,0), delta=(0.01,0,0).
    // At scale=100, deformed-magnified = (1 + 100*0.01, 0, 0) = (2, 0, 0).
    const out = buildNodeCoords(frameA, null, 0, 100)
    const node2 = out.get(2)!
    expect(node2[0]).toBeCloseTo(2, 4)
    expect(node2[1]).toBeCloseTo(0, 4)
  })

  it('a node with zero displacement is unchanged at any scale', () => {
    // Node 1 has deformed === undeformed → delta is zero.
    const out = buildNodeCoords(frameA, null, 0, 100)
    expect(out.get(1)).toEqual([0, 0, 0])
  })
})

describe('ResultMeshPlaybackPanel — Phase 22 B depth controls UI', () => {
  const buildPayload = (frames: unknown[]) => ({
    schemaVersion: 1,
    analysisType: 'dynamic',
    caseId: 'phase22b-test',
    fieldRanges: { valueMin: 0, valueMax: 2 },
    modelTree: { id: 'root', label: 'root', children: [] },
    dynamicFrames: frames,
  })

  it('renders depth controls in WebGL mode', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => ({
        ok: true,
        status: 200,
        json: async () => buildPayload([frameA, frameB]),
      })),
    )
    render(
      <ResultMeshPlaybackPanel
        caseId="phase22b-test"
        apiBase="http://localhost:8000/api/v1"
      />,
    )
    await waitFor(() =>
      expect(
        screen.getByTestId('viewport-depth-controls'),
      ).toBeInTheDocument(),
    )
    expect(
      screen.getByTestId('deformation-scale-input'),
    ).toBeInTheDocument()
    expect(screen.getByTestId('section-cut-toggle')).toBeInTheDocument()
  })

  it('hides depth controls in SVG mode', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => ({
        ok: true,
        status: 200,
        json: async () => buildPayload([frameA, frameB]),
      })),
    )
    render(
      <ResultMeshPlaybackPanel
        caseId="phase22b-toggle"
        apiBase="http://localhost:8000/api/v1"
      />,
    )
    await waitFor(() =>
      expect(
        screen.getByTestId('viewport-depth-controls'),
      ).toBeInTheDocument(),
    )
    fireEvent.click(screen.getByTestId('viewport-toggle-svg'))
    // The slot remains; the controls themselves should be absent.
    expect(
      screen.queryByTestId('viewport-depth-controls'),
    ).not.toBeInTheDocument()
  })

  it('section-cut checkbox creates state on toggle', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => ({
        ok: true,
        status: 200,
        json: async () => buildPayload([frameA]),
      })),
    )
    render(
      <ResultMeshPlaybackPanel
        caseId="phase22b-section"
        apiBase="http://localhost:8000/api/v1"
      />,
    )
    await waitFor(() =>
      expect(screen.getByTestId('section-cut-toggle')).toBeInTheDocument(),
    )
    // No axis select before toggle.
    expect(screen.queryByTestId('section-cut-axis')).not.toBeInTheDocument()
    fireEvent.click(screen.getByTestId('section-cut-toggle'))
    expect(screen.getByTestId('section-cut-axis')).toBeInTheDocument()
    expect(screen.getByTestId('section-cut-position')).toBeInTheDocument()
    expect(screen.getByTestId('section-cut-flip')).toBeInTheDocument()
  })

  it('deformation scale slider value flows through to the input', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => ({
        ok: true,
        status: 200,
        json: async () => buildPayload([frameA]),
      })),
    )
    render(
      <ResultMeshPlaybackPanel
        caseId="phase22b-mag"
        apiBase="http://localhost:8000/api/v1"
      />,
    )
    await waitFor(() =>
      expect(
        screen.getByTestId('deformation-scale-input'),
      ).toBeInTheDocument(),
    )
    const input = screen.getByTestId(
      'deformation-scale-input',
    ) as HTMLInputElement
    fireEvent.change(input, { target: { value: '25' } })
    expect(input.value).toBe('25')
  })

  it('section-cut flip button toggles the showLow indicator', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => ({
        ok: true,
        status: 200,
        json: async () => buildPayload([frameA]),
      })),
    )
    render(
      <ResultMeshPlaybackPanel
        caseId="phase22b-flip"
        apiBase="http://localhost:8000/api/v1"
      />,
    )
    await waitFor(() =>
      expect(screen.getByTestId('section-cut-toggle')).toBeInTheDocument(),
    )
    fireEvent.click(screen.getByTestId('section-cut-toggle'))
    const flip = screen.getByTestId('section-cut-flip') as HTMLButtonElement
    // Default showLow=true → button label is "−".
    expect(flip.textContent).toBe('−')
    fireEvent.click(flip)
    expect(flip.textContent).toBe('+')
  })
})
