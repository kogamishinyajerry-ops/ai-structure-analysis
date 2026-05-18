// FM-04a Phase 30 B — 2-quadrant viewport split + section-cut
// companion tests.
//
// Three deliveries pinned in one test file:
//
// 1. companionViewportStorage — enabled flag + section-cut state
//    persistence + corrupted-payload guard + computeCompanionInitialCut.
//
// 2. CompanionViewport component — renders with independent section-
//    cut controls; flip / axis-change / position-change fire callback;
//    shared field props pass through.
//
// 3. ResultMeshPlaybackPanel 2-quadrant integration — Compare-cuts
//    toggle is advanced-mode gated; toggling on renders the companion;
//    companion state independent of primary; state preserved across
//    toggle off/on (C:-1); SVG mode hides companion; uiMode='basic'
//    hides toggle (D:-1).
//
// Tier 1 / Tier 2 engineering candidate; not signed validation; not
// benchmark agreement.

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'

import { CompanionViewport } from '../src/components/CompanionViewport'
import {
  COMPANION_CUT_LS_KEY,
  COMPANION_ENABLED_LS_KEY,
  computeCompanionInitialCut,
  loadCompanionEnabled,
  loadCompanionSectionCut,
  saveCompanionEnabled,
  saveCompanionSectionCut,
} from '../src/components/companionViewportStorage'
import { ResultMeshPlaybackPanel } from '../src/components/ResultMeshPlaybackPanel'
import type { SectionCutState } from '../src/components/viewportGeometry'
import { ADVANCED_FEATURE_IDS, shouldShowFeature } from '../src/uiMode'

// ────────────────────────────────────────────────────────────────────
// 1. companionViewportStorage
// ────────────────────────────────────────────────────────────────────

function clearCompanionStorage() {
  try {
    window.localStorage.removeItem(COMPANION_ENABLED_LS_KEY)
    window.localStorage.removeItem(COMPANION_CUT_LS_KEY)
  } catch {
    /* SSR fallback */
  }
}

describe('Phase 30 B — companionViewportStorage enabled flag', () => {
  beforeEach(clearCompanionStorage)
  afterEach(clearCompanionStorage)

  it('default load returns false (D:-1 additive)', () => {
    expect(loadCompanionEnabled()).toBe(false)
  })

  it('save then load returns the saved value (true)', () => {
    saveCompanionEnabled(true)
    expect(loadCompanionEnabled()).toBe(true)
  })

  it('save then load returns the saved value (false)', () => {
    saveCompanionEnabled(true)
    saveCompanionEnabled(false)
    expect(loadCompanionEnabled()).toBe(false)
  })

  it('corrupted value (anything not "true") loads as false', () => {
    window.localStorage.setItem(COMPANION_ENABLED_LS_KEY, 'banana')
    expect(loadCompanionEnabled()).toBe(false)
  })

  it('persistence key is namespaced under fm04a.companion-viewport.*', () => {
    expect(COMPANION_ENABLED_LS_KEY).toMatch(/^fm04a\.companion-viewport\./)
    expect(COMPANION_CUT_LS_KEY).toMatch(/^fm04a\.companion-viewport\./)
  })
})

describe('Phase 30 B — companionViewportStorage section-cut state', () => {
  beforeEach(clearCompanionStorage)
  afterEach(clearCompanionStorage)

  it('default load returns null when key missing', () => {
    expect(loadCompanionSectionCut()).toBeNull()
  })

  it('save then load round-trips a full SectionCutState', () => {
    const cut: SectionCutState = { axis: 'y', positionM: 0.42, showLow: false }
    saveCompanionSectionCut(cut)
    expect(loadCompanionSectionCut()).toEqual(cut)
  })

  it('save null clears the key (load returns null after)', () => {
    saveCompanionSectionCut({ axis: 'x', positionM: 0, showLow: true })
    saveCompanionSectionCut(null)
    expect(loadCompanionSectionCut()).toBeNull()
  })

  it('corrupted JSON returns null (E:-1 guard, never throws)', () => {
    window.localStorage.setItem(COMPANION_CUT_LS_KEY, '{not json')
    expect(() => loadCompanionSectionCut()).not.toThrow()
    expect(loadCompanionSectionCut()).toBeNull()
  })

  it('payload with wrong shape (missing axis) returns null', () => {
    window.localStorage.setItem(
      COMPANION_CUT_LS_KEY,
      JSON.stringify({ positionM: 0, showLow: true }),
    )
    expect(loadCompanionSectionCut()).toBeNull()
  })

  it('payload with invalid axis value returns null', () => {
    window.localStorage.setItem(
      COMPANION_CUT_LS_KEY,
      JSON.stringify({ axis: 'w', positionM: 0, showLow: true }),
    )
    expect(loadCompanionSectionCut()).toBeNull()
  })

  it('payload with non-finite positionM returns null', () => {
    window.localStorage.setItem(
      COMPANION_CUT_LS_KEY,
      JSON.stringify({ axis: 'x', positionM: 'NaN', showLow: true }),
    )
    expect(loadCompanionSectionCut()).toBeNull()
  })
})

describe('Phase 30 B — computeCompanionInitialCut', () => {
  it('returns x-axis, 0, showLow:false when primary cut is null', () => {
    expect(computeCompanionInitialCut(null)).toEqual({
      axis: 'x',
      positionM: 0,
      showLow: false,
    })
  })

  it('mirrors primary axis + position but flips showLow', () => {
    const primary: SectionCutState = {
      axis: 'y',
      positionM: 0.123,
      showLow: true,
    }
    expect(computeCompanionInitialCut(primary)).toEqual({
      axis: 'y',
      positionM: 0.123,
      showLow: false,
    })
  })

  it('flips showLow back when primary was already false', () => {
    const primary: SectionCutState = {
      axis: 'z',
      positionM: -0.5,
      showLow: false,
    }
    expect(computeCompanionInitialCut(primary)).toEqual({
      axis: 'z',
      positionM: -0.5,
      showLow: true,
    })
  })
})

// ────────────────────────────────────────────────────────────────────
// 2. CompanionViewport component
// ────────────────────────────────────────────────────────────────────

describe('Phase 30 B — CompanionViewport renders', () => {
  it('renders with the "Companion view" label', () => {
    const cut: SectionCutState = { axis: 'x', positionM: 0, showLow: true }
    render(
      <CompanionViewport
        frame={null}
        valueMin={0}
        valueMax={1}
        sectionCut={cut}
        onSectionCutChange={vi.fn()}
      />,
    )
    expect(screen.getByTestId('companion-viewport-label').textContent).toBe(
      'Companion view',
    )
  })

  it('renders axis select, position slider, and flip button', () => {
    const cut: SectionCutState = { axis: 'y', positionM: 0.3, showLow: false }
    render(
      <CompanionViewport
        frame={null}
        valueMin={0}
        valueMax={1}
        sectionCut={cut}
        onSectionCutChange={vi.fn()}
      />,
    )
    expect(screen.getByTestId('companion-section-cut-axis')).toBeTruthy()
    expect(screen.getByTestId('companion-section-cut-position')).toBeTruthy()
    expect(screen.getByTestId('companion-section-cut-flip')).toBeTruthy()
  })

  it('axis select reflects the current axis prop', () => {
    const cut: SectionCutState = { axis: 'z', positionM: 0, showLow: true }
    render(
      <CompanionViewport
        frame={null}
        valueMin={0}
        valueMax={1}
        sectionCut={cut}
        onSectionCutChange={vi.fn()}
      />,
    )
    const sel = screen.getByTestId('companion-section-cut-axis') as HTMLSelectElement
    expect(sel.value).toBe('z')
  })

  it('changing axis fires onSectionCutChange with new axis, preserves position+showLow', () => {
    const cut: SectionCutState = { axis: 'x', positionM: 0.7, showLow: false }
    const onChange = vi.fn()
    render(
      <CompanionViewport
        frame={null}
        valueMin={0}
        valueMax={1}
        sectionCut={cut}
        onSectionCutChange={onChange}
      />,
    )
    fireEvent.change(screen.getByTestId('companion-section-cut-axis'), {
      target: { value: 'y' },
    })
    expect(onChange).toHaveBeenCalledWith({
      axis: 'y',
      positionM: 0.7,
      showLow: false,
    })
  })

  it('moving position slider fires onSectionCutChange with new position', () => {
    const cut: SectionCutState = { axis: 'x', positionM: 0, showLow: true }
    const onChange = vi.fn()
    render(
      <CompanionViewport
        frame={null}
        valueMin={0}
        valueMax={1}
        sectionCut={cut}
        onSectionCutChange={onChange}
      />,
    )
    fireEvent.change(screen.getByTestId('companion-section-cut-position'), {
      target: { value: '0.5' },
    })
    expect(onChange).toHaveBeenCalledWith({
      axis: 'x',
      positionM: 0.5,
      showLow: true,
    })
  })

  it('clicking flip button toggles showLow', () => {
    const cut: SectionCutState = { axis: 'x', positionM: 0, showLow: true }
    const onChange = vi.fn()
    render(
      <CompanionViewport
        frame={null}
        valueMin={0}
        valueMax={1}
        sectionCut={cut}
        onSectionCutChange={onChange}
      />,
    )
    fireEvent.click(screen.getByTestId('companion-section-cut-flip'))
    expect(onChange).toHaveBeenCalledWith({
      axis: 'x',
      positionM: 0,
      showLow: false,
    })
  })

  it('flip button shows "−" when showLow=true, "+" when showLow=false', () => {
    const { rerender } = render(
      <CompanionViewport
        frame={null}
        valueMin={0}
        valueMax={1}
        sectionCut={{ axis: 'x', positionM: 0, showLow: true }}
        onSectionCutChange={vi.fn()}
      />,
    )
    expect(screen.getByTestId('companion-section-cut-flip').textContent).toBe('−')
    rerender(
      <CompanionViewport
        frame={null}
        valueMin={0}
        valueMax={1}
        sectionCut={{ axis: 'x', positionM: 0, showLow: false }}
        onSectionCutChange={vi.fn()}
      />,
    )
    expect(screen.getByTestId('companion-section-cut-flip').textContent).toBe('+')
  })

  it('section-cut readout appears only while position slider is being dragged', () => {
    const cut: SectionCutState = { axis: 'y', positionM: 0.25, showLow: true }
    render(
      <CompanionViewport
        frame={null}
        valueMin={0}
        valueMax={1}
        sectionCut={cut}
        onSectionCutChange={vi.fn()}
      />,
    )
    // Not visible at rest.
    expect(screen.queryByTestId('companion-section-cut-readout')).toBeNull()
    // Mousedown shows it.
    fireEvent.mouseDown(screen.getByTestId('companion-section-cut-position'))
    expect(screen.getByTestId('companion-section-cut-readout')).toBeTruthy()
    // Mouseup hides.
    fireEvent.mouseUp(screen.getByTestId('companion-section-cut-position'))
    expect(screen.queryByTestId('companion-section-cut-readout')).toBeNull()
  })
})

// ────────────────────────────────────────────────────────────────────
// 3. ResultMeshPlaybackPanel integration — Compare-cuts toggle + layout
// ────────────────────────────────────────────────────────────────────

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

const basePayload = {
  schemaVersion: 1,
  analysisType: 'dynamic',
  caseId: 'phase30b-fixture',
  fieldRanges: { valueMin: 0, valueMax: 200 },
  modelTree: { id: 'root', label: 'root', children: [] },
  dynamicFrames: [baseFrame],
}

function stubFetchWithPayload(caseId: string) {
  vi.stubGlobal(
    'fetch',
    vi.fn(async () => ({
      ok: true,
      status: 200,
      json: async () => ({ ...basePayload, caseId }),
    })),
  )
}

let restoreGetContext: (() => void) | null = null

describe('Phase 30 B — ResultMeshPlaybackPanel Compare-cuts toggle gating', () => {
  beforeEach(() => {
    restoreGetContext = installWebGLStub()
    clearCompanionStorage()
  })
  afterEach(() => {
    restoreGetContext?.()
    restoreGetContext = null
    clearCompanionStorage()
    try {
      window.localStorage.removeItem('fm04a.ui.mode.v1')
    } catch {
      /* SSR fallback */
    }
    vi.unstubAllGlobals()
  })

  it('toggle button VISIBLE in basic mode (Phase 32 C un-gating)', async () => {
    // FM-04a Phase 32 C — Compare-cuts un-gated from advanced-mode-
    // only. Closes Phase 30 FINAL gap #10. Originally Phase 30 B
    // gated this to advanced because companion picks could
    // double-write to the shared probe list; Phase 31 D's origin-
    // stamping wrapper eliminates that risk, so basic-mode
    // reviewers now see the 2-quadrant lift.
    window.localStorage.setItem('fm04a.ui.mode.v1', 'basic')
    stubFetchWithPayload('phase30b-basic-visible')
    render(
      <ResultMeshPlaybackPanel
        caseId="phase30b-basic-visible"
        apiBase="http://localhost:8000/api/v1"
      />,
    )
    await waitFor(() =>
      expect(screen.getByTestId('viewport-mode-toggle')).toBeInTheDocument(),
    )
    expect(screen.getByTestId('compare-cuts-toggle')).toBeInTheDocument()
  })

  it('toggle button VISIBLE in advanced mode', async () => {
    window.localStorage.setItem('fm04a.ui.mode.v1', 'advanced')
    stubFetchWithPayload('phase30b-advanced-visible')
    render(
      <ResultMeshPlaybackPanel
        caseId="phase30b-advanced-visible"
        apiBase="http://localhost:8000/api/v1"
      />,
    )
    await waitFor(() =>
      expect(screen.getByTestId('compare-cuts-toggle')).toBeInTheDocument(),
    )
  })

  it('toggle button HIDDEN when viewportMode=svg even in advanced mode', async () => {
    window.localStorage.setItem('fm04a.ui.mode.v1', 'advanced')
    stubFetchWithPayload('phase30b-svg-mode')
    render(
      <ResultMeshPlaybackPanel
        caseId="phase30b-svg-mode"
        apiBase="http://localhost:8000/api/v1"
      />,
    )
    await waitFor(() =>
      expect(screen.getByTestId('viewport-toggle-svg')).toBeInTheDocument(),
    )
    fireEvent.click(screen.getByTestId('viewport-toggle-svg'))
    expect(screen.queryByTestId('compare-cuts-toggle')).toBeNull()
  })

  it('toggle ON renders the companion viewport', async () => {
    window.localStorage.setItem('fm04a.ui.mode.v1', 'advanced')
    stubFetchWithPayload('phase30b-toggle-on')
    render(
      <ResultMeshPlaybackPanel
        caseId="phase30b-toggle-on"
        apiBase="http://localhost:8000/api/v1"
      />,
    )
    await waitFor(() =>
      expect(screen.getByTestId('compare-cuts-toggle')).toBeInTheDocument(),
    )
    expect(screen.queryByTestId('companion-viewport')).toBeNull()
    fireEvent.click(screen.getByTestId('compare-cuts-toggle'))
    expect(screen.getByTestId('companion-viewport')).toBeTruthy()
  })

  it('toggle ON then OFF removes the companion viewport from the DOM', async () => {
    window.localStorage.setItem('fm04a.ui.mode.v1', 'advanced')
    stubFetchWithPayload('phase30b-toggle-off')
    render(
      <ResultMeshPlaybackPanel
        caseId="phase30b-toggle-off"
        apiBase="http://localhost:8000/api/v1"
      />,
    )
    await waitFor(() =>
      expect(screen.getByTestId('compare-cuts-toggle')).toBeInTheDocument(),
    )
    fireEvent.click(screen.getByTestId('compare-cuts-toggle'))
    expect(screen.getByTestId('companion-viewport')).toBeTruthy()
    fireEvent.click(screen.getByTestId('compare-cuts-toggle'))
    expect(screen.queryByTestId('companion-viewport')).toBeNull()
  })

  it('toggle state persists across remount (localStorage)', async () => {
    window.localStorage.setItem('fm04a.ui.mode.v1', 'advanced')
    saveCompanionEnabled(true)
    stubFetchWithPayload('phase30b-persist')
    render(
      <ResultMeshPlaybackPanel
        caseId="phase30b-persist"
        apiBase="http://localhost:8000/api/v1"
      />,
    )
    await waitFor(() =>
      expect(screen.getByTestId('companion-viewport')).toBeInTheDocument(),
    )
  })
})

describe('Phase 30 B — companion state independence (C:-1 anti-gaming)', () => {
  beforeEach(() => {
    restoreGetContext = installWebGLStub()
    clearCompanionStorage()
    window.localStorage.setItem('fm04a.ui.mode.v1', 'advanced')
  })
  afterEach(() => {
    restoreGetContext?.()
    restoreGetContext = null
    clearCompanionStorage()
    try {
      window.localStorage.removeItem('fm04a.ui.mode.v1')
    } catch {
      /* SSR fallback */
    }
    vi.unstubAllGlobals()
  })

  it('companion section-cut state preserved across Compare toggle off/on (C:-1)', async () => {
    stubFetchWithPayload('phase30b-state-preserved')
    render(
      <ResultMeshPlaybackPanel
        caseId="phase30b-state-preserved"
        apiBase="http://localhost:8000/api/v1"
      />,
    )
    await waitFor(() =>
      expect(screen.getByTestId('compare-cuts-toggle')).toBeInTheDocument(),
    )
    // Toggle ON.
    fireEvent.click(screen.getByTestId('compare-cuts-toggle'))
    expect(screen.getByTestId('companion-viewport')).toBeTruthy()
    // Edit companion's axis to 'z'.
    fireEvent.change(screen.getByTestId('companion-section-cut-axis'), {
      target: { value: 'z' },
    })
    // Toggle OFF.
    fireEvent.click(screen.getByTestId('compare-cuts-toggle'))
    expect(screen.queryByTestId('companion-viewport')).toBeNull()
    // Toggle ON — axis state preserved.
    fireEvent.click(screen.getByTestId('compare-cuts-toggle'))
    const axisSelect = screen.getByTestId(
      'companion-section-cut-axis',
    ) as HTMLSelectElement
    expect(axisSelect.value).toBe('z')
  })

  it('primary section cut and companion cut are independent (separate test ids)', async () => {
    stubFetchWithPayload('phase30b-independent')
    render(
      <ResultMeshPlaybackPanel
        caseId="phase30b-independent"
        apiBase="http://localhost:8000/api/v1"
      />,
    )
    await waitFor(() =>
      expect(screen.getByTestId('compare-cuts-toggle')).toBeInTheDocument(),
    )
    fireEvent.click(screen.getByTestId('compare-cuts-toggle'))
    // Enable primary section cut.
    fireEvent.click(screen.getByTestId('section-cut-toggle'))
    // Edit primary axis to 'y'.
    fireEvent.change(screen.getByTestId('section-cut-axis'), {
      target: { value: 'y' },
    })
    // Edit companion axis to 'z'.
    fireEvent.change(screen.getByTestId('companion-section-cut-axis'), {
      target: { value: 'z' },
    })
    // Both retain their own axis — pinned by the dedicated test-ids.
    const primaryAxis = screen.getByTestId('section-cut-axis') as HTMLSelectElement
    const companionAxis = screen.getByTestId(
      'companion-section-cut-axis',
    ) as HTMLSelectElement
    expect(primaryAxis.value).toBe('y')
    expect(companionAxis.value).toBe('z')
  })

  it('companion position persists in localStorage on slider change', async () => {
    stubFetchWithPayload('phase30b-persist-cut')
    render(
      <ResultMeshPlaybackPanel
        caseId="phase30b-persist-cut"
        apiBase="http://localhost:8000/api/v1"
      />,
    )
    await waitFor(() =>
      expect(screen.getByTestId('compare-cuts-toggle')).toBeInTheDocument(),
    )
    fireEvent.click(screen.getByTestId('compare-cuts-toggle'))
    fireEvent.change(screen.getByTestId('companion-section-cut-position'), {
      target: { value: '0.42' },
    })
    const persisted = loadCompanionSectionCut()
    expect(persisted).not.toBeNull()
    expect(persisted!.positionM).toBeCloseTo(0.42, 4)
  })

  it('probe-list row is now a sibling of viewport-flex-row, not nested inside primary-viewport-slot', async () => {
    stubFetchWithPayload('phase30b-probe-lifted')
    render(
      <ResultMeshPlaybackPanel
        caseId="phase30b-probe-lifted"
        apiBase="http://localhost:8000/api/v1"
      />,
    )
    await waitFor(() =>
      expect(screen.getByTestId('viewport-row')).toBeInTheDocument(),
    )
    const probeRow = screen.queryByTestId('probe-list-row')
    if (probeRow) {
      // If probe panel rendered (advanced mode), its parent should be
      // the viewport-row, NOT the primary-viewport-slot.
      const primarySlot = screen.getByTestId('primary-viewport-slot')
      expect(primarySlot.contains(probeRow)).toBe(false)
      expect(screen.getByTestId('viewport-row').contains(probeRow)).toBe(true)
    }
  })
})

// ────────────────────────────────────────────────────────────────────
// 4. uiMode registry guard
// ────────────────────────────────────────────────────────────────────

describe('Phase 30 B → Phase 32 C — uiMode registry transition', () => {
  // FM-04a Phase 32 C — companion-viewport REMOVED from
  // ADVANCED_FEATURE_IDS. The 2-quadrant Compare-cuts feature is now
  // available in basic mode (Phase 30 FINAL gap #10 closure). The
  // safety rationale: Phase 31 D wired companion node-pick with
  // origin: 'companion' marker, eliminating the write-conflict risk
  // that originally motivated the advanced-only gate.
  it("'companion-viewport' is NO LONGER in ADVANCED_FEATURE_IDS", () => {
    expect(ADVANCED_FEATURE_IDS as readonly string[]).not.toContain(
      'companion-viewport',
    )
  })

  // The shouldShowFeature contract is preserved: any non-registered
  // id returns false (Phase 25 C strict-typing contract). But
  // because 'companion-viewport' is no longer in the AdvancedFeatureId
  // union, calling shouldShowFeature with it is now a TS type error
  // — caught at compile time, not runtime. The legacy runtime
  // checks below are intentionally REMOVED rather than kept as
  // negative pins (they'd require a string cast that defeats the
  // type system).
})
