// FM-04a Phase 23 D — element-value threshold filter tests.
//
// Tier 1 / Tier 2 engineering candidate; not signed validation; not
// benchmark agreement.
//
// Phase 23 D ships an alternative to iso-surfaces: reviewers hide
// elements below/above a threshold to focus on hot spots. The
// legend's full range stays anchored — only the rendered set
// changes.
//
// Anti-gaming guards:
//   * D:-1 — elements without a derivable value (no value, no
//     tensor, OR partRole=projectile, OR alive=false) are RETAINED
//     regardless of filter. Pinned by the predicate test.

import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { applyValueFilter } from '../src/components/ResultMeshWebGLViewport'
import { ResultMeshPlaybackPanel } from '../src/components/ResultMeshPlaybackPanel'
import type { ResultMeshElement } from '../src/resultMeshPlayback'

const baseElement: ResultMeshElement = {
  label: 1,
  type: 'QUAD',
  connectivity: [1, 2, 3, 4],
  partRole: 'plate',
  alive: true,
  value: 50,
}

describe('applyValueFilter — Phase 23 D pure-function pin', () => {
  it('returns true (retain) when no filter is set', () => {
    expect(applyValueFilter(baseElement, null)).toBe(true)
    expect(applyValueFilter(baseElement, undefined)).toBe(true)
  })

  it('mode=inside retains elements within [min, max]', () => {
    expect(
      applyValueFilter(baseElement, {
        minValue: 0,
        maxValue: 100,
        mode: 'inside',
      }),
    ).toBe(true)
    expect(
      applyValueFilter(baseElement, {
        minValue: 0,
        maxValue: 25,
        mode: 'inside',
      }),
    ).toBe(false)
    expect(
      applyValueFilter(baseElement, {
        minValue: 100,
        maxValue: 200,
        mode: 'inside',
      }),
    ).toBe(false)
  })

  it('mode=outside hides elements within [min, max], retains outside', () => {
    expect(
      applyValueFilter(baseElement, {
        minValue: 0,
        maxValue: 100,
        mode: 'outside',
      }),
    ).toBe(false)
    expect(
      applyValueFilter(baseElement, {
        minValue: 0,
        maxValue: 25,
        mode: 'outside',
      }),
    ).toBe(true)
  })

  it('null bounds mean ±∞ (open-ended filter)', () => {
    expect(
      applyValueFilter(baseElement, {
        minValue: null,
        maxValue: 60,
        mode: 'inside',
      }),
    ).toBe(true)
    expect(
      applyValueFilter(baseElement, {
        minValue: 60,
        maxValue: null,
        mode: 'inside',
      }),
    ).toBe(false)
  })

  it('uses Mises by default when tensor is present', () => {
    const tensorElem: ResultMeshElement = {
      ...baseElement,
      // Uniaxial σ_xx=100 → Mises=100.
      stressTensor: { sxx: 100, syy: 0, szz: 0, sxy: 0, syz: 0, sxz: 0 },
      value: 999, // distinct from tensor's derived Mises
    }
    expect(
      applyValueFilter(
        tensorElem,
        { minValue: 0, maxValue: 200, mode: 'inside' },
        'mises',
      ),
    ).toBe(true)
    expect(
      applyValueFilter(
        tensorElem,
        { minValue: 500, maxValue: 1500, mode: 'inside' },
        'mises',
      ),
    ).toBe(false)
  })

  it('honors the fieldComponent argument', () => {
    const tensorElem: ResultMeshElement = {
      ...baseElement,
      stressTensor: { sxx: 100, syy: -100, szz: 0, sxy: 0, syz: 0, sxz: 0 },
    }
    // σ_xx = 100 — inside [50, 150]
    expect(
      applyValueFilter(
        tensorElem,
        { minValue: 50, maxValue: 150, mode: 'inside' },
        'sxx',
      ),
    ).toBe(true)
    // σ_yy = -100 — outside [50, 150]
    expect(
      applyValueFilter(
        tensorElem,
        { minValue: 50, maxValue: 150, mode: 'inside' },
        'syy',
      ),
    ).toBe(false)
  })

  it('D:-1 anti-gaming guard: alive=false elements ALWAYS render', () => {
    const dead: ResultMeshElement = { ...baseElement, alive: false }
    // Filter that would exclude any value-based element.
    expect(
      applyValueFilter(dead, {
        minValue: 1e9,
        maxValue: 2e9,
        mode: 'inside',
      }),
    ).toBe(true)
  })

  it('D:-1 anti-gaming guard: projectile parts ALWAYS render', () => {
    const projectile: ResultMeshElement = { ...baseElement, partRole: 'projectile' }
    expect(
      applyValueFilter(projectile, {
        minValue: 1e9,
        maxValue: 2e9,
        mode: 'inside',
      }),
    ).toBe(true)
  })

  it('D:-1 anti-gaming guard: element with no value AND no tensor retained', () => {
    const valueless: ResultMeshElement = {
      label: 5,
      type: 'QUAD',
      connectivity: [1, 2, 3, 4],
      partRole: 'plate',
      alive: true,
      // No value, no stressTensor.
    }
    expect(
      applyValueFilter(valueless, {
        minValue: 1e9,
        maxValue: 2e9,
        mode: 'inside',
      }),
    ).toBe(true)
  })
})

// =====================================================================
// UI integration
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
  // FM-04a Phase 26 B — these tests exercise the threshold-filter UI
  // which is now gated by uiMode='advanced'. Pre-set localStorage so
  // the filter row is rendered.
  try {
    window.localStorage.setItem('fm04a.ui.mode.v1', 'advanced')
  } catch {
    /* SSR fallback */
  }
})
afterEach(() => {
  restoreGetContext?.()
  restoreGetContext = null
  try {
    window.localStorage.removeItem('fm04a.ui.mode.v1')
  } catch {
    /* SSR fallback */
  }
})

const payloadWithFrame = {
  schemaVersion: 1,
  analysisType: 'dynamic',
  caseId: 'phase23d-test',
  modelTree: { id: 'root', label: 'root', children: [] },
  dynamicFrames: [
    {
      frame: 0,
      timeMs: 0,
      fieldLabel: 'stress',
      // Frame-level fieldRanges win in the summary's lookup order.
      fieldRanges: { valueMin: 0, valueMax: 200 },
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
    },
  ],
}

describe('ResultMeshPlaybackPanel — Phase 23 D filter UI', () => {
  it('value-filter checkbox toggles state', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => ({
        ok: true,
        status: 200,
        json: async () => payloadWithFrame,
      })),
    )
    render(
      <ResultMeshPlaybackPanel
        caseId="phase23d-toggle"
        apiBase="http://localhost:8000/api/v1"
      />,
    )
    await waitFor(() =>
      expect(screen.getByTestId('value-filter-toggle')).toBeInTheDocument(),
    )
    // Default: filter is off, no sliders.
    expect(screen.queryByTestId('value-filter-min')).not.toBeInTheDocument()
    fireEvent.click(screen.getByTestId('value-filter-toggle'))
    expect(screen.getByTestId('value-filter-min')).toBeInTheDocument()
    expect(screen.getByTestId('value-filter-max')).toBeInTheDocument()
    expect(screen.getByTestId('value-filter-mode')).toBeInTheDocument()
  })

  it('mode button toggles inside ↔ outside', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => ({
        ok: true,
        status: 200,
        json: async () => payloadWithFrame,
      })),
    )
    render(
      <ResultMeshPlaybackPanel
        caseId="phase23d-mode"
        apiBase="http://localhost:8000/api/v1"
      />,
    )
    await waitFor(() =>
      expect(screen.getByTestId('value-filter-toggle')).toBeInTheDocument(),
    )
    fireEvent.click(screen.getByTestId('value-filter-toggle'))
    const modeBtn = screen.getByTestId('value-filter-mode') as HTMLButtonElement
    expect(modeBtn.textContent).toBe('IN')
    fireEvent.click(modeBtn)
    expect(modeBtn.textContent).toBe('OUT')
    fireEvent.click(modeBtn)
    expect(modeBtn.textContent).toBe('IN')
  })

  it('min slider value reflects state changes (re-query after fire)', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => ({
        ok: true,
        status: 200,
        json: async () => payloadWithFrame,
      })),
    )
    render(
      <ResultMeshPlaybackPanel
        caseId="phase23d-slider"
        apiBase="http://localhost:8000/api/v1"
      />,
    )
    await waitFor(() =>
      expect(screen.getByTestId('value-filter-toggle')).toBeInTheDocument(),
    )
    fireEvent.click(screen.getByTestId('value-filter-toggle'))
    fireEvent.change(screen.getByTestId('value-filter-min'), {
      target: { value: '50' },
    })
    // The label text reflects the controlled state.
    expect(
      screen.getByTestId('value-filter-control').textContent,
    ).toMatch(/min ≥ 5\.00e\+1/)
  })
})
