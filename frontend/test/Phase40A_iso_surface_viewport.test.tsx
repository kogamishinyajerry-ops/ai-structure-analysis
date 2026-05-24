// FM-04a Phase 40 A (step 2) — iso-surface viewport wiring tests.
//
// Tier 1 / Tier 2 engineering candidate; not signed validation; not
// benchmark agreement.
//
// Step 1 (Phase40A_iso_surface.test.ts, node --test) covers the pure
// extraction kernel (cell→point averaging + marching-tets cases). THIS
// file covers the additive WIRING into the React viewport + panel:
//   - the iso-surface overlay is OPT-IN; by default the per-element
//     coloring is the only render (T:-1 honesty: truth view is default);
//   - when enabled, the viewport surfaces a HONESTY BADGE naming the
//     surface a smoothed Tier-0 viz approximation (never the solved
//     field), and reports the triangle count / "no crossing";
//   - the panel control (advanced mode) renders the toggle + threshold
//     slider + always-visible honesty caption, and is HIDDEN in basic
//     mode (no novice cognitive load).
//
// jsdom has no WebGL, so we stub getContext (same pattern as
// Phase21C_webgl.test.tsx) to let three.js's mount path complete; we
// assert DOM affordances, not pixels.

import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { ResultMeshWebGLViewport } from '../src/components/ResultMeshWebGLViewport'
import { ResultMeshPlaybackPanel } from '../src/components/ResultMeshPlaybackPanel'
import { CompanionViewport } from '../src/components/CompanionViewport'
import { extractIsoSurface } from '../src/components/isoSurface'

// Two adjacent C3D4 tets sharing face (2,3,4). After cell→point
// averaging the shared nodes get (1+3)/2 = 2.0, node 1 = 1.0, node 5 =
// 3.0. At threshold 1.5 (inside = value ≥ 1.5): tet A {1.0,2,2,2} has 3
// corners inside → 1 triangle; tet B {2,2,2,3} all inside → 0. So a
// real crossing yields exactly 1 iso triangle.
const crossingTetFrame = {
  frame: 0,
  timeMs: 0,
  fieldLabel: 'stress',
  nodes: [
    { label: 1, coordinates: [0, 0, 0] },
    { label: 2, coordinates: [1, 0, 0] },
    { label: 3, coordinates: [0, 1, 0] },
    { label: 4, coordinates: [0, 0, 1] },
    { label: 5, coordinates: [1, 1, 1] },
  ],
  elements: [
    { label: 1, type: 'C3D4', connectivity: [1, 2, 3, 4], partRole: 'plate', alive: true, value: 1.0 },
    { label: 2, type: 'C3D4', connectivity: [2, 3, 4, 5], partRole: 'plate', alive: true, value: 3.0 },
  ],
}

// A single constant tet: all 4 nodes average to the same value, so NO
// iso-surface exists at any threshold (the honest consequence pinned by
// the step-1 kernel tests — averaging a single element cannot fabricate
// a gradient).
const constantTetFrame = {
  frame: 0,
  timeMs: 0,
  fieldLabel: 'stress',
  nodes: [
    { label: 1, coordinates: [0, 0, 0] },
    { label: 2, coordinates: [1, 0, 0] },
    { label: 3, coordinates: [0, 1, 0] },
    { label: 4, coordinates: [0, 0, 1] },
  ],
  elements: [
    { label: 1, type: 'C3D4', connectivity: [1, 2, 3, 4], partRole: 'plate', alive: true, value: 2.0 },
  ],
}

// Stub getContext('webgl') so three.js's WebGLRenderer constructor does
// not throw on mount in jsdom. (Verbatim shape from Phase21C.)
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

describe('ResultMeshWebGLViewport — iso-surface overlay (opt-in)', () => {
  it('does NOT render the iso badge by default (per-element truth view is default)', () => {
    render(
      <ResultMeshWebGLViewport
        frame={crossingTetFrame}
        valueMin={0}
        valueMax={4}
      />,
    )
    // Regression guard: with the overlay un-requested, the smoothed
    // surface must not appear and the badge must be absent.
    expect(
      screen.queryByTestId('webgl-iso-surface-badge'),
    ).not.toBeInTheDocument()
  })

  it('renders the honesty badge when enabled, naming the smoothed Tier-0 approximation', () => {
    render(
      <ResultMeshWebGLViewport
        frame={crossingTetFrame}
        valueMin={0}
        valueMax={4}
        isoSurfaceEnabled
        isoThreshold={1.5}
      />,
    )
    const badge = screen.getByTestId('webgl-iso-surface-badge')
    // T:-1 honesty framing must be verbatim-surfaced, not implied.
    expect(badge).toHaveTextContent(/SMOOTHED TIER-0 VIZ APPROXIMATION/i)
    expect(badge).toHaveTextContent(/per-element coloring is the truth view/i)
  })

  it('reports a real triangle count for a genuine crossing frame', () => {
    render(
      <ResultMeshWebGLViewport
        frame={crossingTetFrame}
        valueMin={0}
        valueMax={4}
        isoSurfaceEnabled
        isoThreshold={1.5}
      />,
    )
    const detail = screen.getByTestId('webgl-iso-surface-badge-detail')
    // Exactly one iso triangle results (see crossingTetFrame note).
    expect(detail).toHaveTextContent(/1 tris/i)
    expect(detail).not.toHaveTextContent(/no crossing/i)
  })

  it('honestly reports "no crossing" for a single constant tet (cannot fabricate a gradient)', () => {
    render(
      <ResultMeshWebGLViewport
        frame={constantTetFrame}
        valueMin={0}
        valueMax={4}
        isoSurfaceEnabled
        isoThreshold={1.5}
      />,
    )
    const detail = screen.getByTestId('webgl-iso-surface-badge-detail')
    expect(detail).toHaveTextContent(/no crossing at this threshold/i)
  })
})

describe('ResultMeshPlaybackPanel — iso-surface control wiring', () => {
  const payload = {
    schemaVersion: 1,
    analysisType: 'dynamic',
    caseId: 'phase40a-iso',
    fieldLabel: 'stress',
    fieldRanges: { valueMin: 0, valueMax: 4 },
    claimBoundary:
      'Tier 1 engineering candidate; not signed validation; not benchmark agreement',
    modelTree: { id: 'root', label: 'root', children: [] },
    dynamicFrames: [crossingTetFrame],
  }

  function stubFetch() {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => ({
        ok: true,
        status: 200,
        json: async () => payload,
      })),
    )
  }

  it('renders the iso-surface control + honesty caption in advanced mode', async () => {
    stubFetch()
    render(
      <ResultMeshPlaybackPanel
        caseId="phase40a-iso"
        apiBase="http://localhost:8000/api/v1"
        uiMode="advanced"
      />,
    )
    await waitFor(() =>
      expect(screen.getByTestId('iso-surface-control')).toBeInTheDocument(),
    )
    expect(screen.getByTestId('iso-surface-toggle')).toBeInTheDocument()
    // Honesty caption is visible BEFORE the overlay is even enabled.
    expect(
      screen.getByTestId('iso-surface-honesty-caption'),
    ).toHaveTextContent(/per-element coloring is the truth view/i)
    // Threshold slider only appears once the toggle is on.
    expect(
      screen.queryByTestId('iso-surface-threshold'),
    ).not.toBeInTheDocument()
  })

  it('toggling the control on reveals the threshold slider', async () => {
    stubFetch()
    render(
      <ResultMeshPlaybackPanel
        caseId="phase40a-iso"
        apiBase="http://localhost:8000/api/v1"
        uiMode="advanced"
      />,
    )
    await waitFor(() =>
      expect(screen.getByTestId('iso-surface-toggle')).toBeInTheDocument(),
    )
    fireEvent.click(screen.getByTestId('iso-surface-toggle'))
    await waitFor(() =>
      expect(
        screen.getByTestId('iso-surface-threshold'),
      ).toBeInTheDocument(),
    )
  })

  it('hides the iso-surface control in basic mode (no novice cognitive load)', async () => {
    stubFetch()
    render(
      <ResultMeshPlaybackPanel
        caseId="phase40a-iso"
        apiBase="http://localhost:8000/api/v1"
        uiMode="basic"
      />,
    )
    // Wait for the payload to load (the viewport toggle is mode-agnostic).
    await waitFor(() =>
      expect(screen.getByTestId('viewport-mode-toggle')).toBeInTheDocument(),
    )
    expect(
      screen.queryByTestId('iso-surface-control'),
    ).not.toBeInTheDocument()
  })
})

// ────────────────────────────────────────────────────────────────────
// Codex R0 fix regression guards (Phase 40 A step 2)
// ────────────────────────────────────────────────────────────────────

describe('Codex R0 P1 — iso-surface marches over deformed coordinates', () => {
  it('places iso vertices at the supplied (deformed) coords, not the raw frame coords', () => {
    const scalarFor = (el: { value?: number }) => el.value
    // Baseline: extract from the frame's own (undeformed) coordinates.
    const base = extractIsoSurface(crossingTetFrame, 1.5, scalarFor)
    expect(base.triangles.length).toBeGreaterThan(0)

    // Override: every node shifted +100 in x (simulating a deformed /
    // magnified coordinate map from buildNodeCoords). The iso-surface
    // must follow — every vertex x shifts by exactly +100.
    const shifted = new Map<number, [number, number, number]>()
    for (const n of crossingTetFrame.nodes) {
      const [x, y, z] = n.coordinates
      shifted.set(n.label, [x + 100, y, z])
    }
    const deformed = extractIsoSurface(crossingTetFrame, 1.5, scalarFor, shifted)
    expect(deformed.triangles.length).toBe(base.triangles.length)

    const sumX = (r: typeof base) =>
      r.triangles.reduce((acc, t) => acc + t.a[0] + t.b[0] + t.c[0], 0)
    const vertexCount = base.triangles.length * 3
    // Mean vertex x must differ by exactly the +100 offset.
    expect(sumX(deformed) / vertexCount - sumX(base) / vertexCount).toBeCloseTo(
      100,
      6,
    )
  })
})

describe('Codex R0 P2 — iso-surface honors the active value filter', () => {
  it('reports "no crossing" when the value filter excludes every element', () => {
    render(
      <ResultMeshWebGLViewport
        frame={crossingTetFrame}
        valueMin={0}
        valueMax={4}
        isoSurfaceEnabled
        isoThreshold={1.5}
        // Both element values (1.0, 3.0) fall OUTSIDE [100, 200], so the
        // filter excludes them — the overlay must not fabricate crossings
        // from filtered-out elements (matching the truth mesh).
        valueFilter={{ minValue: 100, maxValue: 200, mode: 'inside' }}
      />,
    )
    const detail = screen.getByTestId('webgl-iso-surface-badge-detail')
    expect(detail).toHaveTextContent(/no crossing at this threshold/i)
  })
})

describe('Codex R0 P2 — iso-surface props reach the companion viewport', () => {
  it('renders the iso honesty badge inside the companion pane', () => {
    render(
      <CompanionViewport
        frame={crossingTetFrame}
        valueMin={0}
        valueMax={4}
        sectionCut={{ axis: 'x', positionM: 0, showLow: true }}
        onSectionCutChange={() => {}}
        isoSurfaceEnabled
        isoThreshold={1.5}
      />,
    )
    // The companion forwards iso props to its inner viewport, so the
    // smoothed-Tier-0 badge appears in the compare-cuts pane too.
    expect(screen.getByTestId('webgl-iso-surface-badge')).toBeInTheDocument()
  })
})
