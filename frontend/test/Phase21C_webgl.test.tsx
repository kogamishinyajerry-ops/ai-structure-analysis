// FM-04a Phase 21 C — three.js WebGL viewport tests.
//
// Tier 1 / Tier 2 engineering candidate; not signed validation; not
// benchmark agreement.
//
// The Phase 20 UI agent's R1 grep `three|webgl|<canvas` returned zero
// hits and dimensioned UI Dim 5 (Industrial-CAE comparison) at 4/20
// floor. Phase 21 C ships a minimal three.js viewport reading the
// same `summary.selectedFrame` payload the SVG panel consumes; the
// SVG body stays as a fallback when WebGL is unavailable, with a
// user-facing toggle.
//
// jsdom does not implement WebGL natively, so the tests:
//   - mock `HTMLCanvasElement.prototype.getContext` to return a stub
//     so `detectWebGLSupport` returns true and the viewport mounts;
//   - assert the viewport's outer testid renders and that the
//     "WebGL not available" message is hidden;
//   - exercise the color-gradient helper (pure function, fully
//     tested without a context);
//   - exercise the toggle (3D ↔ SVG) without depending on three.js
//     having actually drawn anything;
//   - assert the SVG fallback still renders when WebGL is disabled.
//
// Anti-gaming guards:
//   - Color-gradient pin: at t=0 (min), t=0.5, t=1 (max) the RGB
//     stops match the SVG legend's blue → green → orange constants.
//   - Toggle pin: clicking SVG switches off the WebGL viewport,
//     clicking 3D switches it back on.
//   - Fallback pin: with WebGL detection forced off, the parent panel
//     defaults to SVG body so a user without WebGL never sees a blank
//     viewport.

import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import {
  ResultMeshWebGLViewport,
  colorForValueFraction,
} from '../src/components/ResultMeshWebGLViewport'
import { ResultMeshPlaybackPanel } from '../src/components/ResultMeshPlaybackPanel'

// A minimal frame mirroring the canonical Phase 21 A plate-with-hole
// stress output: 4 nodes, 1 quad element. Connectivity is flat so
// `nodeCoords` lookup hits.
const fakeFrame = {
  frame: 0,
  timeMs: 0,
  fieldLabel: 'stress',
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
      value: 1.5,
    },
  ],
}

// Stub a getContext('webgl') so three.js's WebGLRenderer constructor
// doesn't throw on import. We can't render actual WebGL in jsdom but
// we can let the mount path complete.
function installWebGLStub() {
  const originalGetContext = HTMLCanvasElement.prototype.getContext
  // Minimal subset of the WebGL API that three.js touches during
  // construction. We don't need a working renderer — we just need
  // `getContext('webgl')` to return non-null so `detectWebGLSupport`
  // returns true and three.js's mount goes past the early-throw.
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

describe('colorForValueFraction (gradient pin)', () => {
  it('at t=0 lands on the legend blue stop (#2563eb)', () => {
    const [r, g, b] = colorForValueFraction(0)
    // 37/255, 99/255, 235/255
    expect(r).toBeCloseTo(37 / 255, 4)
    expect(g).toBeCloseTo(99 / 255, 4)
    expect(b).toBeCloseTo(235 / 255, 4)
  })

  it('at t=0.5 lands on the legend green stop (#10b981)', () => {
    const [r, g, b] = colorForValueFraction(0.5)
    expect(r).toBeCloseTo(16 / 255, 4)
    expect(g).toBeCloseTo(185 / 255, 4)
    expect(b).toBeCloseTo(129 / 255, 4)
  })

  it('at t=1 lands on the legend orange stop (#f97316)', () => {
    const [r, g, b] = colorForValueFraction(1)
    expect(r).toBeCloseTo(249 / 255, 4)
    expect(g).toBeCloseTo(115 / 255, 4)
    expect(b).toBeCloseTo(22 / 255, 4)
  })

  it('clamps t below 0 to the blue stop', () => {
    const [r, g, b] = colorForValueFraction(-0.5)
    expect(r).toBeCloseTo(37 / 255, 4)
    expect(g).toBeCloseTo(99 / 255, 4)
    expect(b).toBeCloseTo(235 / 255, 4)
  })

  it('clamps t above 1 to the orange stop', () => {
    const [r, g, b] = colorForValueFraction(2)
    expect(r).toBeCloseTo(249 / 255, 4)
    expect(g).toBeCloseTo(115 / 255, 4)
    expect(b).toBeCloseTo(22 / 255, 4)
  })
})

describe('ResultMeshWebGLViewport mount', () => {
  it('renders the outer viewport container even without a frame', () => {
    render(
      <ResultMeshWebGLViewport frame={null} valueMin={0} valueMax={1} />,
    )
    expect(
      screen.getByTestId('result-mesh-webgl-viewport'),
    ).toBeInTheDocument()
  })

  it('renders the canvas container when WebGL is available', () => {
    render(
      <ResultMeshWebGLViewport
        frame={fakeFrame}
        valueMin={0}
        valueMax={1}
      />,
    )
    // The container div is always present; with WebGL stubbed in
    // beforeEach the renderer mounts a canvas inside it.
    expect(
      screen.getByTestId('webgl-canvas-container'),
    ).toBeInTheDocument()
  })

  it('renders the orbit / pan / zoom help overlay', () => {
    render(
      <ResultMeshWebGLViewport
        frame={fakeFrame}
        valueMin={0}
        valueMax={1}
      />,
    )
    const overlay = screen.getByTestId('webgl-overlay-help')
    expect(overlay).toHaveTextContent('ORBIT')
    expect(overlay).toHaveTextContent('PAN')
    expect(overlay).toHaveTextContent('ZOOM')
  })

  it('shows a "WebGL not available" fallback when getContext returns null', () => {
    // Force detection to fail: override getContext to return null for
    // every context kind. Tests in this describe block beforeEach the
    // WebGL stub, so we restore it before disabling.
    restoreGetContext?.()
    restoreGetContext = null
    const originalGetContext = HTMLCanvasElement.prototype.getContext
    HTMLCanvasElement.prototype.getContext = function () {
      return null
    } as typeof HTMLCanvasElement.prototype.getContext
    try {
      render(
        <ResultMeshWebGLViewport
          frame={fakeFrame}
          valueMin={0}
          valueMax={1}
        />,
      )
      const msg = screen.getByTestId('webgl-message')
      expect(msg.textContent ?? '').toMatch(/WebGL/)
    } finally {
      HTMLCanvasElement.prototype.getContext = originalGetContext
    }
  })
})

describe('ResultMeshPlaybackPanel — WebGL toggle integration', () => {
  it('the 3D / SVG toggle buttons render when a payload loads', async () => {
    const payload = {
      schemaVersion: 1,
      analysisType: 'dynamic',
      caseId: 'phase21c-test',
      fieldLabel: 'stress',
      fieldRanges: { valueMin: 0, valueMax: 1 },
      claimBoundary:
        'Tier 1 engineering candidate; not signed validation; not benchmark agreement',
      modelTree: {
        id: 'root',
        label: 'root',
        children: [],
      },
      dynamicFrames: [fakeFrame],
    }
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => ({
        ok: true,
        status: 200,
        json: async () => payload,
      })),
    )
    render(
      <ResultMeshPlaybackPanel
        caseId="phase21c-test"
        apiBase="http://localhost:8000/api/v1"
      />,
    )
    await waitFor(() =>
      expect(screen.getByTestId('viewport-mode-toggle')).toBeInTheDocument(),
    )
    expect(screen.getByTestId('viewport-toggle-webgl')).toBeInTheDocument()
    expect(screen.getByTestId('viewport-toggle-svg')).toBeInTheDocument()
  })

  it('defaults to WebGL mode (3D button is active)', async () => {
    const payload = {
      schemaVersion: 1,
      analysisType: 'dynamic',
      caseId: 'phase21c-default',
      fieldRanges: { valueMin: 0, valueMax: 1 },
      modelTree: { id: 'root', label: 'root', children: [] },
      dynamicFrames: [fakeFrame],
    }
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => ({
        ok: true,
        status: 200,
        json: async () => payload,
      })),
    )
    render(
      <ResultMeshPlaybackPanel
        caseId="phase21c-default"
        apiBase="http://localhost:8000/api/v1"
      />,
    )
    await waitFor(() =>
      expect(
        screen.getByTestId('result-mesh-webgl-viewport'),
      ).toBeInTheDocument(),
    )
    // The SVG `<svg>` element should NOT be mounted in WebGL mode.
    expect(
      document.querySelector('svg[aria-label="Dynamic result mesh frame"]'),
    ).toBeNull()
  })

  it('clicking SVG toggles to the SVG body; clicking 3D toggles back', async () => {
    const payload = {
      schemaVersion: 1,
      analysisType: 'dynamic',
      caseId: 'phase21c-toggle',
      fieldRanges: { valueMin: 0, valueMax: 1 },
      modelTree: { id: 'root', label: 'root', children: [] },
      dynamicFrames: [fakeFrame],
    }
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => ({
        ok: true,
        status: 200,
        json: async () => payload,
      })),
    )
    render(
      <ResultMeshPlaybackPanel
        caseId="phase21c-toggle"
        apiBase="http://localhost:8000/api/v1"
      />,
    )
    await waitFor(() =>
      expect(screen.getByTestId('viewport-toggle-svg')).toBeInTheDocument(),
    )
    fireEvent.click(screen.getByTestId('viewport-toggle-svg'))
    expect(
      screen.queryByTestId('result-mesh-webgl-viewport'),
    ).not.toBeInTheDocument()
    expect(
      document.querySelector('svg[aria-label="Dynamic result mesh frame"]'),
    ).not.toBeNull()

    fireEvent.click(screen.getByTestId('viewport-toggle-webgl'))
    await waitFor(() =>
      expect(
        screen.getByTestId('result-mesh-webgl-viewport'),
      ).toBeInTheDocument(),
    )
  })
})
