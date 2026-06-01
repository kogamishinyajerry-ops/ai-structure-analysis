import { useCallback, useEffect, useMemo, useState, type CSSProperties } from 'react';
import { Box, Layers, Pause, Play, ShieldAlert } from 'lucide-react';

import {
  summarizeResultMeshPlayback,
  type ResultMeshElement,
  type ResultMeshFrame,
  type ResultMeshNode,
  type ResultMeshPayload,
} from '../resultMeshPlayback';
// FM-04a Phase 20 D — close the Phase 19 D scope-drift the UI agent
// flagged: the legend was added, but the bespoke loading / error /
// empty <div>s in this panel were never migrated to the SSOT
// primitives. Migrating them now closes that finding.
import { EmptyStateCard } from './EmptyStateCard';
import { ErrorCard } from './ErrorCard';
import { SkeletonCard } from './SkeletonCard';
// FM-04a Phase 21 C — three.js WebGL viewport. Reads the same
// `summary.selectedFrame` the SVG panel consumes; the SVG body stays
// as a fallback when WebGL is unavailable or the user toggles to it.
// FM-04a Phase 22 B — same import now carries nextFrame / playing /
// deformationScale / sectionCut props.
import {
  ResultMeshWebGLViewport,
  type PickedNodeInfo,
  type SectionCutState,
  type ValueFilterState,
} from './ResultMeshWebGLViewport';
// FM-04a Phase 30 B — companion viewport for 2-quadrant section-cut
// comparison. Independent section-cut state, shared field/component/
// threshold/playback state.
import { CompanionViewport } from './CompanionViewport';
// FM-04a Phase 30 C — Hyperworks-style floating coord-readout overlay.
import { CoordReadoutTooltip } from './CoordReadoutTooltip';
// FM-04a Phase 31 B — viewport-layout state + effect cascade
// centralized in a single hook. Eliminates 6 local useState + 5
// useEffect from this file (closes the 3-phase reducer-extraction
// debt called out by Phase 27 punchlist #3 + Phase 29 rec #2 +
// Phase 30 UX Dim 3 -1 debit).
import { useViewportLayout } from '../state/useViewportLayout';
import type { StressComponent } from '../stressDerivatives';
import {
  COLORMAP_IDS,
  COLORMAP_LABELS,
  DEFAULT_COLORMAP,
  colormapCssGradient,
  sampleColormap,
  type ColormapId,
} from './colormaps';
// FM-04a Phase 24 B — onboarding tour mounted into the result-mesh
// panel because that's where Phase 23 B/C/D added the new control
// surfaces. The tour persists dismissal in localStorage so it shows
// exactly once across sessions.
// FM-04a Phase 29 C — OnboardingTour + AdvancedModePromo mounts
// lifted to App.tsx (App-root). Imports removed from this panel.
// FM-04a Phase 24 D — multi-node probe list. Extends Phase 23 C
// single-pick to a comparison list (max 8). State owned here so the
// panel can render the table next to the viewport.
import { ProbeListPanel } from './ProbeListPanel';
// FM-04a Phase 43 — hero peak-result readout banner. Lifts the demo
// payoff number (summary.valueMax + fieldLabel + units) above the
// MetricGrid at a headline type size. Extracted to its own file so the
// readout is unit-testable in isolation.
import { HeroPeakReadout } from './HeroPeakReadout';
// FM-04a Phase 43 (Codex R0 P2) — pick the hero field that matches the
// currently-displayed component (von Mises vs an active σ-component).
import { selectActiveFieldPeak } from './heroPeakFormat';
// FM-04a Phase 27 D — probe-list save/restore across sessions
// (loadProbeList / loadProbeListWithDiagnostic / saveProbeList all
// moved to useViewportLayout in Phase 31 B; the panel only needs
// the immutable transforms below).
import {
  addProbeEntry,
  clearAllProbes,
  removeProbeEntry,
} from './probeList';
// FM-04a Phase 25 C — Basic/Advanced UI mode. Hides advanced
// control surfaces in basic mode without destroying their state
// (C:-1 anti-gaming guard: state preservation across toggle).
import {
  createUiModeStorage,
  shouldShowFeature,
  type UiMode,
} from '../uiMode';
import { UiModeToggle } from './UiModeToggle';
// FM-04a Phase 27 C — Apple-tier polish: gradient slider tracks +
// section-cut position hover readout.
import {
  installPolishStyles,
  POLISH_CLASS_GRADIENT_SLIDER,
  POLISH_CLASS_SECTION_CUT_READOUT,
  POLISH_CLASS_RESTORED_TOAST,
  POLISH_CLASS_WARNING_TOAST,
  POLISH_CLASS_VIEWPORT_FLEX_ROW,
} from './polishStyles';

interface ResultMeshPlaybackPanelProps {
  caseId: string | null;
  apiBase: string;
  enabled?: boolean;
  /** FM-04a Phase 22 D — unit suffix appended to the legend's min/max
   * field values. Defaults to "Pa" (stress fields are the canonical
   * Phase 22 output). Honest scope: a per-component switcher
   * (σ_xx / σ_yy / σ_zz / max-principal) was scoped in the blueprint
   * but requires σ-tensor payload not currently in result_mesh.json.
   * Documented gap in the Phase 22 D commit; deferred. */
  fieldUnits?: string;
  /** FM-04a Phase 29 C — when supplied, the parent (App-root) owns
   * the Basic/Advanced UI mode state. When undefined, the panel
   * falls back to its prior internal state (preserves backward
   * compatibility with tests that mount the panel directly). */
  uiMode?: UiMode;
  onUiModeChange?: (next: UiMode) => void;
}

interface ProjectedPolygon {
  key: string;
  points: string;
  fill: string;
  stroke: string;
  opacity: number;
  order: number;
}

const numberFormat = new Intl.NumberFormat('en-US', { maximumFractionDigits: 3 });

export function ResultMeshPlaybackPanel({
  caseId,
  apiBase,
  enabled = true,
  // Stress fields render in MPa: the result-mesh reader emits stress under the
  // design-institute default unit system SI_mm (mm/MPa/t/N/s — see backend
  // core/types/enums.py UnitSystem.SI_MM), and the viz payload carries no unit
  // metadata, so this default IS the displayed unit. It only ever labels stress
  // (von Mises + σ-components); displacement is shown separately in mm. (Was
  // 'Pa' — off by 1e6 for real cases, e.g. GS-102 von Mises peak 731.493.)
  fieldUnits = 'MPa',
  uiMode: uiModeProp,
  onUiModeChange,
}: ResultMeshPlaybackPanelProps) {
  const [result, setResult] = useState<{
    caseId: string;
    payload: ResultMeshPayload | null;
    error: string | null;
  } | null>(null);
  const [frameIndex, setFrameIndex] = useState(0);
  const [playing, setPlaying] = useState(false);
  // FM-04a Phase 22 B — viewport depth controls. Deformation
  // magnification scales (deformed - undeformed) so small-strain
  // results are visible; default 1× (true coords). Section cut hides
  // half the mesh along one axis; default null (no cut).
  const [deformationScale, setDeformationScale] = useState<number>(1);
  const [sectionCut, setSectionCut] = useState<SectionCutState | null>(null);
  // FM-04a Phase 23 B — stress-tensor component switcher. Defaults to
  // Mises; when the frame's elements carry a stressTensor the viewport
  // recolors by the selected derivative.
  const [fieldComponent, setFieldComponent] = useState<StressComponent>('mises');
  // FM-04a Phase 43 Slice 4b — active colormap for the WebGL coloring + every
  // legend surface. Default 'spectral' (legacy ramp) → no visual change unless
  // the reviewer switches it.
  const [colormap, setColormap] = useState<ColormapId>(DEFAULT_COLORMAP);
  // FM-04a Phase 23 D — element-value threshold filter.
  const [valueFilter, setValueFilter] = useState<ValueFilterState | null>(null);
  // FM-04a Phase 40 A — iso-surface overlay (opt-in, default OFF). The
  // per-element coloring stays the truth view; the iso-surface is a
  // smoothed Tier-0 viz approximation. `isoThreshold` null = use the
  // midpoint of [valueMin, valueMax] (computed at the call site).
  const [isoSurfaceEnabled, setIsoSurfaceEnabled] = useState<boolean>(false);
  const [isoThreshold, setIsoThreshold] = useState<number | null>(null);
  // FM-04a Phase 24 D — active pick (single, live; pinned list owned
  // by the layout hook below).
  const [activePick, setActivePick] = useState<PickedNodeInfo | null>(null);
  // FM-04a Phase 31 D — WebGL context-loss toast state. Surfaces a
  // user-visible warning when the GPU context drops (memory pressure
  // / GPU reset / tab background reclaim). `reason` is the browser's
  // statusMessage if supplied (most browsers do not). Auto-dismisses
  // after 10s; manually dismissable via the toast's × button.
  const [contextLostToast, setContextLostToast] = useState<
    { reason: string } | null
  >(null);

  // FM-04a Phase 31 B — viewport-layout state + effect cascade
  // extracted to a custom hook. Closes the 3-phase reducer-extraction
  // debt (Phase 27 punchlist #3 + Phase 29 rec #2 + Phase 30 Dim 3
  // -1 debit). Hook owns: viewportMode, showCompanionViewport,
  // companionSectionCut, hoverCoords, probeList, exitingProbeLabel,
  // restoredCount, corruptedToast — and the 5 effects coupling them
  // (case-mount diagnostic load + 2 auto-dismiss timers + 2
  // companion persistence).
  const { state: layout, actions: layoutActions } = useViewportLayout({
    caseId,
  });
  const {
    viewportMode,
    showCompanionViewport,
    companionSectionCut,
    hoverCoords,
    probeList,
    exitingProbeLabel,
    restoredCount,
    corruptedToast,
  } = layout;
  const {
    setViewportMode,
    toggleCompanion,
    setCompanionSectionCut,
    setHoverCoords,
    setProbeList,
    setExitingProbeLabel,
    setRestoredCount,
    dismissCorruptedToast,
  } = layoutActions;
  // FM-04a Phase 25 C — Basic/Advanced UI mode. State preservation
  // contract: toggling basic does NOT clear the threshold filter /
  // section cut / probe list / field component — only the UI is
  // hidden. Pinned by Phase 25 C tests.
  // FM-04a Phase 29 C — uiMode ownership: if parent supplies it
  // (App-root path), use the prop verbatim and forward changes
  // through onUiModeChange. Otherwise fall back to internal state
  // + storage adapter (preserves Phase 25 C contract for direct-
  // mount tests).
  const uiModeStorage = useMemo(() => createUiModeStorage(), []);
  const [internalUiMode, setInternalUiMode] = useState<UiMode>(() =>
    uiModeProp ?? uiModeStorage.load(),
  );
  const uiMode = uiModeProp ?? internalUiMode;
  const setUiMode = (next: UiMode) => {
    if (uiModeProp === undefined) setInternalUiMode(next);
    onUiModeChange?.(next);
  };
  // FM-04a Phase 27 C — install Apple-tier polish stylesheet on
  // first mount. Used by gradient slider tracks (value-filter min/max)
  // and the section-cut readout. ProbeListPanel installs the same
  // sheet for its row-mount animation, but ResultMeshPlaybackPanel
  // installs unconditionally because the sliders render even in
  // basic mode (showProbeListPanel can be false).
  useEffect(() => {
    installPolishStyles();
  }, []);
  // FM-04a Phase 31 D — context-lost toast auto-dismiss after 10s.
  // Longer than the 4s restored-toast (Phase 28 C) and 8s corrupted-
  // toast (Phase 30 C) because GL context loss is rarer and the
  // reviewer needs more time to register the change to SVG mode.
  // E:-1 unmount safety: timer cleared on rerender and on unmount.
  useEffect(() => {
    if (!contextLostToast) return;
    const timer = setTimeout(() => setContextLostToast(null), 10000);
    return () => clearTimeout(timer);
  }, [contextLostToast]);
  // FM-04a Phase 31 D — context-loss handler. Falls back to SVG so
  // the reviewer keeps working, and surfaces the toast above the
  // viewport. Wired into the primary ResultMeshWebGLViewport below
  // via `onContextLost`. (Companion does NOT wire this; if the
  // companion's context drops the parent layout already fell back
  // for the primary.)
  const handleContextLost = useCallback((reason: string) => {
    setViewportMode('svg');
    setContextLostToast({ reason });
  }, [setViewportMode]);
  // FM-04a Phase 31 B — case-mount cascade + auto-dismiss timers +
  // probe-list & companion-state persistence ALL moved to
  // `useViewportLayout` above. The 5 useEffect blocks deleted from
  // this panel are now centralized in the hook with the same
  // behavioral semantics (pinned by Phase 27 D / 28 C / 30 B /
  // 30 C tests + new Phase 31 B tests).
  const handleUiModeChange = (next: UiMode) => {
    setUiMode(next);
    // Only the internal-state path needs to persist — the App-root
    // path persists in its own hook.
    if (uiModeProp === undefined) uiModeStorage.save(next);
  };
  const showThresholdFilter = shouldShowFeature(uiMode, 'threshold-filter');
  const showSectionCut = shouldShowFeature(uiMode, 'section-cut');
  const showFieldComponentSwitcher = shouldShowFeature(uiMode, 'field-component-switcher');
  const showProbeListPanel = shouldShowFeature(uiMode, 'probe-list-panel');
  // FM-04a Phase 30 B introduced the Compare-cuts toggle. Phase 32 C
  // UNGATES it from advanced-mode (Phase 30 FINAL gap #10 closure):
  // since Phase 31 D wired companion node-pick with origin marker
  // (no write-conflict risk), the 2-quadrant layout is safe to
  // surface in basic mode. The toggle is OPT-IN (button click), so
  // cognitive load on first paint is zero. State preservation
  // contract preserved: toggling has no effect on underlying
  // showCompanionViewport / companionSectionCut state.
  const showCompanionViewportToggle = true;
  // Effective render flag: companion only renders when (a) the user
  // has enabled it AND (b) the primary viewport is in WebGL mode
  // (SVG fallback has no shared contract with the companion).
  const companionViewportActive =
    showCompanionViewport && showCompanionViewportToggle;

  const currentResult = result?.caseId === caseId ? result : null;
  const payload = currentResult?.payload ?? null;
  const error = currentResult?.error ?? null;
  const loading = Boolean(enabled && caseId && !currentResult);

  useEffect(() => {
    if (!enabled || !caseId) return;
    const controller = new AbortController();

    fetch(`${apiBase}/visualize/result-mesh/${encodeURIComponent(caseId)}`, {
      signal: controller.signal,
    })
      .then(async (response) => {
        if (!response.ok) {
          throw new Error(
            response.status === 404
              ? 'result_mesh.json unavailable'
              : `result_mesh.json request failed (${response.status})`,
          );
        }
        return response.json() as Promise<ResultMeshPayload>;
      })
      .then((data) => {
        setResult({ caseId, payload: data, error: null });
        setFrameIndex(0);
        setPlaying(false);
      })
      .catch((err: unknown) => {
        if (err instanceof DOMException && err.name === 'AbortError') return;
        setResult({
          caseId,
          payload: null,
          error: err instanceof Error ? err.message : 'result_mesh.json request failed',
        });
      });

    return () => controller.abort();
  }, [apiBase, caseId, enabled]);

  const summary = useMemo(
    () => (payload ? summarizeResultMeshPlayback(payload, frameIndex) : null),
    [payload, frameIndex],
  );
  const frameCount = summary?.frameCount ?? 0;

  // FM-04a Phase 22 B — next frame for WebGL interpolation. When the
  // current frame is the last one, nextFrame is null and the viewport
  // falls back to single-frame render. Loop wrap-around is handled by
  // the parent's setInterval; the WebGL viewport interpolates only
  // forward to the linearly-adjacent frame.
  const nextFrame = useMemo(() => {
    if (!payload || !summary) return null;
    if (summary.selectedFrameIndex + 1 >= summary.frameCount) return null;
    return summarizeResultMeshPlayback(payload, summary.selectedFrameIndex + 1)
      .selectedFrame;
  }, [payload, summary]);

  useEffect(() => {
    if (!playing || frameCount <= 1) return;
    const timer = window.setInterval(() => {
      setFrameIndex((current) => (current + 1 >= frameCount ? 0 : current + 1));
    }, 240);
    return () => window.clearInterval(timer);
  }, [frameCount, playing]);

  const projection = useMemo(
    () => buildProjection(summary?.selectedFrame ?? null, summary?.valueMin ?? 0, summary?.valueMax ?? 0, colormap),
    [summary, colormap],
  );

  // FM-04a Phase 43 (Codex R0 P2) — the hero headline must track the field
  // the viewport is actually coloring by, so it can't claim the von Mises
  // peak while a σ-component is selected. Recomputes the component peak only
  // when a non-Mises component is active.
  const heroField = useMemo(
    () =>
      summary
        ? selectActiveFieldPeak(
            {
              fieldLabel: summary.fieldLabel,
              valueMax: summary.valueMax,
              elements: summary.selectedFrame?.elements ?? [],
            },
            fieldComponent,
            viewportMode,
            valueFilter,
          )
        : null,
    [summary, fieldComponent, viewportMode, valueFilter],
  );

  const vtuState = readVtuState(payload);

  return (
    <section
      aria-label="OpenRadioss dynamic playback"
      style={{
        height: '100%',
        minHeight: '360px',
        border: '1px solid var(--border)',
        borderRadius: '8px',
        background: 'var(--bg-surface)',
        overflow: 'hidden',
        display: 'grid',
        gridTemplateRows: 'auto 1fr',
      }}
    >
      {/* FM-04a Phase 29 C — OnboardingTour + AdvancedModePromo
          lifted to App-root so reviewers landing on tabs OTHER than
          Visual still see onboarding. When the panel is mounted
          standalone (tests / future direct-mount paths), the tour
          will simply not surface — App-root is the canonical owner. */}
      {/* FM-04a Phase 28 C — "Restored N probes" toast on case
          mount. Closes Phase 27 D's silent restoration miss. Click
          dismisses; auto-fades after 4 seconds. */}
      {restoredCount > 0 && (
        <div
          data-testid="probe-restored-toast"
          className={POLISH_CLASS_RESTORED_TOAST}
          role="status"
          aria-live="polite"
        >
          <span>
            Restored {restoredCount} pinned probe
            {restoredCount === 1 ? '' : 's'} from your last session
          </span>
          <button
            type="button"
            data-testid="probe-restored-toast-dismiss"
            onClick={() => setRestoredCount(0)}
            aria-label="Dismiss restored probes notification"
          >
            ×
          </button>
        </div>
      )}
      {/* FM-04a Phase 30 C — corrupted-key toast. Surfaces when the
          probe-list load discarded a corrupted/malformed payload on
          case mount (NOT on missing-key first-load). 8s auto-fade
          + dismiss button. Role=alert so screen readers announce it
          immediately — corruption is higher-stakes than a routine
          restore. Reuses POLISH_CLASS_RESTORED_TOAST styling but
          uses warning-tinted text via inline color override. */}
      {corruptedToast && (
        <div
          data-testid="probe-corrupted-toast"
          className={`${POLISH_CLASS_RESTORED_TOAST} ${POLISH_CLASS_WARNING_TOAST}`}
          role="alert"
          aria-live="assertive"
          style={{ top: '50px' }}
        >
          <span>
            Discarded corrupted probe list for case '{corruptedToast.caseId}' —
            starting fresh
          </span>
          <button
            type="button"
            data-testid="probe-corrupted-toast-dismiss"
            onClick={() => dismissCorruptedToast()}
            aria-label="Dismiss corrupted probe list notification"
          >
            ×
          </button>
        </div>
      )}
      {/* FM-04a Phase 31 D — WebGL context-loss toast. Surfaces when
          the ResultMeshWebGLViewport's `webglcontextlost` listener
          fires (parent setViewportMode to 'svg' so the reviewer
          keeps working). Same rose tint as corrupted-toast via the
          shared warning-toast class. 10s auto-fade. */}
      {contextLostToast && (
        <div
          data-testid="webgl-context-lost-toast"
          className={`${POLISH_CLASS_RESTORED_TOAST} ${POLISH_CLASS_WARNING_TOAST}`}
          role="alert"
          aria-live="assertive"
          style={{ top: '90px' }}
        >
          <span>
            WebGL context lost — fell back to SVG rendering
            {contextLostToast.reason ? ` (${contextLostToast.reason})` : ''}
          </span>
          <button
            type="button"
            data-testid="webgl-context-lost-toast-dismiss"
            onClick={() => setContextLostToast(null)}
            aria-label="Dismiss WebGL context-lost notification"
          >
            ×
          </button>
        </div>
      )}
      <div
        style={{
          padding: '14px 16px',
          borderBottom: '1px solid var(--border)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: '12px',
          flexWrap: 'wrap',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <Box size={18} color="var(--accent)" />
          <div>
            <div className="eyebrow">OpenRadioss dynamic</div>
            <h3 className="heading-tight" style={{ margin: 0, fontSize: 'var(--fs-lg)' }}>Result mesh playback</h3>
          </div>
          <UiModeToggle mode={uiMode} onChange={handleUiModeChange} />
        </div>
        <div
          style={{
            color: 'var(--danger-400)',
            border: '1px solid rgba(197, 69, 59, 0.30)',
            background: 'rgba(197, 69, 59, 0.10)',
            borderRadius: '999px',
            padding: '5px 10px',
            fontSize: '0.72rem',
            fontWeight: 800,
          }}
        >
          not signed validation
        </div>
      </div>

      {loading ? (
        <div data-testid="result-mesh-loading" style={{ padding: '14px' }}>
          <SkeletonCard lines={4} label="Loading dynamic payload" />
        </div>
      ) : error ? (
        <div data-testid="result-mesh-error" style={{ padding: '14px' }}>
          <ErrorCard
            title="Could not load dynamic payload"
            message={error}
            code="RESULT-MESH-LOAD"
            remediation={
              // FM-04a Phase 41.4: a signed-registry case (^GS-\d{3}$) is
              // refused (422) by design — running the solver can NEVER make it
              // serve a result_mesh.json. Steer the user to a candidate instead
              // of the misleading "Run the solver" copy.
              /^GS-\d{3}$/.test(caseId ?? '')
                ? [
                    'This is a sealed signed-registry case — its 3D result is not served here.',
                    'Switch to a candidate case (e.g. GS-102-candidate) to view a 3D result.',
                  ]
                : [
                    'Run the solver for this case via Topbar → Run Solver to produce a result_mesh.json.',
                    'Confirm the backend /visualize/result-mesh route responds for this case_id.',
                  ]
            }
          />
        </div>
      ) : summary ? (
        <div
          style={{
            padding: '14px',
            display: 'grid',
            gridTemplateColumns: 'minmax(360px, 1fr) minmax(260px, 340px)',
            gap: '14px',
            minHeight: 0,
          }}
        >
          <div
            style={{
              minHeight: 0,
              display: 'grid',
              gridTemplateRows: 'auto auto 1fr auto',
              gap: '12px',
            }}
          >
            <div
              data-testid="viewport-mode-toggle"
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'flex-end',
                gap: 6,
                fontSize: '0.7rem',
              }}
            >
              {showCompanionViewportToggle && viewportMode === 'webgl' && (
                <button
                  type="button"
                  data-testid="compare-cuts-toggle"
                  aria-pressed={companionViewportActive}
                  onClick={() => toggleCompanion(sectionCut)}
                  className="vp-toggle"
                >
                  Compare cuts
                </button>
              )}
              <button
                type="button"
                data-testid="viewport-toggle-webgl"
                onClick={() => setViewportMode('webgl')}
                className="vp-toggle"
                aria-pressed={viewportMode === 'webgl'}
              >
                3D
              </button>
              <button
                type="button"
                data-testid="viewport-toggle-svg"
                onClick={() => setViewportMode('svg')}
                className="vp-toggle"
                aria-pressed={viewportMode === 'svg'}
              >
                SVG
              </button>
            </div>
            <div data-testid="viewport-depth-controls-slot">
              {viewportMode === 'webgl' && (
                <ViewportDepthControls
                  deformationScale={deformationScale}
                  onDeformationScaleChange={setDeformationScale}
                  sectionCut={sectionCut}
                  onSectionCutChange={setSectionCut}
                  valueFilter={valueFilter}
                  onValueFilterChange={setValueFilter}
                  valueRange={[summary.valueMin, summary.valueMax]}
                  showSectionCut={showSectionCut}
                  showThresholdFilter={showThresholdFilter}
                  isoSurfaceEnabled={isoSurfaceEnabled}
                  onIsoSurfaceToggle={setIsoSurfaceEnabled}
                  isoThreshold={isoThreshold}
                  onIsoThresholdChange={setIsoThreshold}
                  showIsoSurface={showThresholdFilter}
                />
              )}
            </div>
            {/* FM-04a Phase 30 B — viewport row. When the Compare-cuts
                toggle is on AND the primary is in WebGL mode, the row
                renders as a 2-quadrant flex layout with the companion
                beside the primary. When off, the primary fills the
                entire row (D:-1: zero behavior change for default-off
                state). */}
            <div
              data-testid="viewport-row"
              style={{
                minHeight: '210px',
                display: 'flex',
                flexDirection: 'column',
                gap: 10,
              }}
            >
            <div
              data-testid="viewport-flex-row"
              className={POLISH_CLASS_VIEWPORT_FLEX_ROW}
              style={{
                display: 'flex',
                gap: 12,
                flex: 1,
                minHeight: '210px',
              }}
            >
            <div
              data-testid="primary-viewport-slot"
              style={{
                flex: 1,
                minWidth: 0,
                border: '1px solid var(--border-strong)',
                borderRadius: 'var(--r-lg)',
                background: '#020617',
                boxShadow: 'var(--elev-2)',
                overflow: 'hidden',
                position: 'relative',
              }}
            >
              {viewportMode === 'webgl' ? (
                <ResultMeshWebGLViewport
                  frame={summary.selectedFrame}
                  valueMin={summary.valueMin}
                  valueMax={summary.valueMax}
                  nextFrame={nextFrame}
                  playing={playing}
                  deformationScale={deformationScale}
                  sectionCut={sectionCut}
                  fieldComponent={fieldComponent}
                  fieldUnits={fieldUnits}
                  colormap={colormap}
                  valueFilter={valueFilter}
                  onNodePicked={setActivePick}
                  onHoverCoords={setHoverCoords}
                  onContextLost={handleContextLost}
                  isoSurfaceEnabled={isoSurfaceEnabled}
                  isoThreshold={
                    isoThreshold ?? (summary.valueMin + summary.valueMax) / 2
                  }
                />
              ) : (
              <>
              <svg width="100%" height="100%" viewBox="0 0 1000 440" role="img" aria-label="Dynamic result mesh frame">
                <rect x="0" y="0" width="1000" height="440" fill="#020617" />
                {projection.map((polygon) => (
                  <polygon
                    key={polygon.key}
                    points={polygon.points}
                    fill={polygon.fill}
                    stroke={polygon.stroke}
                    strokeWidth="1.4"
                    opacity={polygon.opacity}
                  />
                ))}
              </svg>
              {projection.length === 0 && (
                <div
                  style={{
                    position: 'absolute',
                    inset: 0,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    color: 'var(--text-muted)',
                    fontSize: '0.84rem',
                  }}
                >
                  No renderable mesh frame
                </div>
              )}
              </>
              )}
              {/* FM-04a Phase 19 D — stress-contour color legend
                  (Phase 21 C: now shared by WebGL + SVG viewports).
                  The legend renders OUTSIDE the WebGL/SVG conditional
                  so the gradient annotation stays visible in both
                  modes. Phase 21 C's three.js viewport uses the same
                  blue→green→orange gradient as the SVG projection. */}
              {summary && (
                <div
                  data-testid="stress-contour-legend"
                  style={{
                    position: 'absolute',
                    right: 16,
                    bottom: 16,
                    background: 'rgba(255, 255, 255, 0.92)',
                    border: '1px solid var(--border-strong)',
                    boxShadow: 'var(--elev-2)',
                    borderRadius: 'var(--r-md)',
                    padding: '8px 12px',
                    color: 'var(--text-secondary)',
                    fontSize: '0.7rem',
                    fontFamily:
                      'ui-monospace, SFMono-Regular, "SF Mono", Menlo, monospace',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: 4,
                    minWidth: 140,
                  }}
                  aria-label="Field-value color legend"
                >
                  <div className="eyebrow">Field value</div>
                  <div
                    data-testid="legend-gradient-bar"
                    style={{
                      height: 8,
                      borderRadius: 4,
                      // FM-04a Phase 43 Slice 4b — driven by the active colormap
                      // so this legend bar always matches the mesh + ScaleBar.
                      background: colormapCssGradient(colormap, 'to right'),
                    }}
                  />
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span data-testid="legend-min">
                      min {formatNumber(summary.valueMin)} {fieldUnits}
                    </span>
                    <span data-testid="legend-max">
                      max {formatNumber(summary.valueMax)} {fieldUnits}
                    </span>
                  </div>
                  {/* FM-04a Phase 23 B — field-component switcher.
                      When any element in the current frame carries a
                      stressTensor, the dropdown is enabled and
                      switches the WebGL viewport's per-vertex coloring
                      via the tensor-derivative helpers. When the
                      frame's elements have no tensor, the dropdown
                      stays disabled with a tooltip naming the gap.
                      FM-04a Phase 26 B — gated by
                      `showFieldComponentSwitcher`; basic mode hides
                      the dropdown while preserving `fieldComponent`
                      state in the parent (C:-1). */}
                  {showFieldComponentSwitcher && (() => {
                    const tensorPresent = (summary.selectedFrame?.elements ?? []).some(
                      (el) => Boolean(el.stressTensor),
                    );
                    return (
                      <div
                        data-testid="legend-field-component"
                        style={{ marginTop: 2 }}
                      >
                        <select
                          data-testid="legend-field-component-select"
                          aria-label="Field component"
                          disabled={!tensorPresent}
                          value={fieldComponent}
                          onChange={(event) =>
                            setFieldComponent(event.target.value as StressComponent)
                          }
                          title={
                            tensorPresent
                              ? 'Switch field component (σ_xx / σ_yy / σ_zz / shear / Mises / principal)'
                              : 'Stress tensor not present in result_mesh.json; only scalar value path active.'
                          }
                          style={{
                            background: 'transparent',
                            color: tensorPresent
                              ? 'var(--text-primary)'
                              : 'var(--text-muted)',
                            border: '1px solid var(--border)',
                            borderRadius: 3,
                            padding: '2px 6px',
                            fontSize: '0.66rem',
                            fontFamily:
                              'ui-monospace, SFMono-Regular, "SF Mono", Menlo, monospace',
                            letterSpacing: '0.04em',
                            textTransform: 'uppercase',
                            cursor: tensorPresent ? 'pointer' : 'not-allowed',
                            width: '100%',
                          }}
                        >
                          <option value="mises">Von Mises</option>
                          <option value="sxx">σ xx</option>
                          <option value="syy">σ yy</option>
                          <option value="szz">σ zz</option>
                          <option value="sxy">τ xy</option>
                          <option value="syz">τ yz</option>
                          <option value="sxz">τ xz</option>
                          <option value="max_principal">σ 1 (max principal)</option>
                          <option value="min_principal">σ 3 (min principal)</option>
                        </select>
                      </div>
                    );
                  })()}
                  {/* FM-04a Phase 43 Slice 4b — colormap selector. Switches the
                      WebGL coloring + every legend ramp. Always available (a
                      low-cognitive color preference, not gated on advanced). */}
                  <div data-testid="legend-colormap" style={{ marginTop: 2 }}>
                    <select
                      data-testid="legend-colormap-select"
                      aria-label="Colormap"
                      value={colormap}
                      onChange={(event) =>
                        setColormap(event.target.value as ColormapId)
                      }
                      title="Switch the result colormap (Spectral / Viridis / Turbo / Grayscale)"
                      style={{
                        background: 'transparent',
                        color: 'var(--text-primary)',
                        border: '1px solid var(--border)',
                        borderRadius: 3,
                        padding: '2px 6px',
                        fontSize: '0.66rem',
                        fontFamily:
                          'ui-monospace, SFMono-Regular, "SF Mono", Menlo, monospace',
                        letterSpacing: '0.04em',
                        textTransform: 'uppercase',
                        cursor: 'pointer',
                        width: '100%',
                      }}
                    >
                      {COLORMAP_IDS.map((id) => (
                        <option key={id} value={id}>
                          {COLORMAP_LABELS[id]}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>
              )}
              {/* FM-04a Phase 30 C — floating coord-readout tooltip.
                  Anchored to the primary-viewport-slot (position:
                  relative) so the screenX/screenY hover coords from
                  the WebGL viewport map correctly. Only renders when
                  the WebGL viewport is active AND the raycaster
                  reports a hit; null hoverCoords renders nothing. */}
              {/* FM-04a Phase 32 C — gated on advanced-mode. Phase
                  30 C introduced the 30Hz floating XYZ tooltip but
                  it rendered unconditionally on every webgl-mode
                  view, adding continuous cognitive load on novice
                  reviewers. Phase 32 C closes Phase 30 FINAL gap #9
                  by hiding the tooltip in basic mode. Power users
                  in advanced mode keep the Hyperworks-style readout. */}
              {viewportMode === 'webgl'
                && shouldShowFeature(uiMode, 'coord-readout') && (
                <CoordReadoutTooltip info={hoverCoords} />
              )}
            </div>{/* close primary-viewport-slot */}
            {/* FM-04a Phase 30 B — companion viewport (2-quadrant
                split). Only renders when (a) showCompanionViewport
                is true AND (b) advanced UI mode is current (the
                Compare-cuts toggle is the only way to flip it on,
                and that toggle itself is advanced-mode gated) AND
                (c) primary is in WebGL mode (SVG fallback has no
                section-cut contract). All shared props are passed
                BY VALUE — companion's sectionCut is independent. */}
            {companionViewportActive && viewportMode === 'webgl' && (
              <CompanionViewport
                frame={summary.selectedFrame}
                valueMin={summary.valueMin}
                valueMax={summary.valueMax}
                nextFrame={nextFrame}
                playing={playing}
                deformationScale={deformationScale}
                fieldComponent={fieldComponent}
                colormap={colormap}
                valueFilter={valueFilter}
                isoSurfaceEnabled={isoSurfaceEnabled}
                isoThreshold={
                  isoThreshold ?? (summary.valueMin + summary.valueMax) / 2
                }
                sectionCut={companionSectionCut}
                onSectionCutChange={setCompanionSectionCut}
                onNodePicked={setActivePick}
              />
            )}
            </div>{/* close viewport-flex-row */}
            {/* FM-04a Phase 24 D — multi-node probe list (max 8).
                FM-04a Phase 25 C gated by uiMode advanced.
                FM-04a Phase 30 B — lifted out of primary-viewport-slot
                so the 2-quadrant layout does not push it under one
                column. Renders below both viewports as a row of its
                own inside the viewport-row column flex. */}
            {showProbeListPanel && (
              <div data-testid="probe-list-row">
                <ProbeListPanel
                  state={probeList}
                  activePick={activePick}
                  fieldUnits={fieldUnits}
                  exitingLabel={exitingProbeLabel}
                  onPinActive={() => {
                    if (activePick) {
                      setProbeList((s) => addProbeEntry(s, activePick));
                    }
                  }}
                  onRemove={(label) => {
                    // FM-04a Phase 28 C — exit-animation timing:
                    // mark the row as exiting (parent re-renders
                    // with the unmount class), then after the
                    // 150ms animation duration actually call
                    // removeProbeEntry and clear the exiting flag.
                    // E:-1 guard: total settle time ≤ 200ms so the
                    // user never perceives a stuck removal.
                    setExitingProbeLabel(label);
                    setTimeout(() => {
                      setProbeList((s) => removeProbeEntry(s, label));
                      setExitingProbeLabel((current) =>
                        current === label ? null : current,
                      );
                    }, 150);
                  }}
                  onClearAll={() => setProbeList((s) => clearAllProbes(s))}
                />
              </div>
            )}
            </div>{/* close viewport-row */}

            <div
              style={{
                display: 'grid',
                gridTemplateColumns: '40px 1fr minmax(140px, auto)',
                alignItems: 'center',
                gap: '12px',
              }}
            >
              <button
                type="button"
                aria-label={playing ? 'Pause' : 'Play'}
                title={playing ? 'Pause' : 'Play'}
                onClick={() => setPlaying((current) => !current)}
                disabled={frameCount <= 1}
                style={{
                  width: '40px',
                  height: '40px',
                  borderRadius: '8px',
                  border: '1px solid var(--border)',
                  background: frameCount > 1 ? 'var(--accent)' : 'var(--bg-surface)',
                  color: frameCount > 1 ? '#fff' : 'var(--text-muted)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  cursor: frameCount > 1 ? 'pointer' : 'not-allowed',
                }}
              >
                {playing ? <Pause size={18} fill="currentColor" /> : <Play size={18} fill="currentColor" />}
              </button>
              <input
                aria-label="Dynamic frame"
                type="range"
                min={0}
                max={Math.max(frameCount - 1, 0)}
                value={summary.selectedFrameIndex}
                onChange={(event) => setFrameIndex(Number(event.target.value))}
                disabled={frameCount <= 1}
                style={{ width: '100%' }}
              />
              <div style={{ textAlign: 'right', fontSize: '0.8rem', color: 'var(--text-secondary)', lineHeight: 1.35 }}>
                <div style={{ color: 'var(--text-primary)', fontWeight: 800 }}>
                  Frame {summary.selectedFrameIndex + 1}/{Math.max(frameCount, 1)}
                </div>
                <div>{formatNumber(summary.timeMs)} ms</div>
              </div>
            </div>
          </div>

          <div style={{ minHeight: 0, overflowY: 'auto', display: 'grid', gap: '10px', alignContent: 'start' }}>
            <HeroPeakReadout
              fieldLabel={heroField?.label}
              valueMax={heroField?.value}
              units={fieldUnits}
            />
            <MetricGrid summary={summary} />

            <div style={panelBoxStyle}>
              <div style={panelTitleStyle}>
                <Layers size={15} color="var(--accent)" />
                Model tree
              </div>
              <div style={{ display: 'grid', gap: '8px' }}>
                {summary.modelTree.map((node) => (
                  <div
                    key={node.id ?? `${node.partRole}-${node.partId}`}
                    style={{
                      display: 'grid',
                      gridTemplateColumns: '1fr auto',
                      gap: '8px',
                      borderTop: '1px solid var(--border)',
                      paddingTop: '8px',
                    }}
                  >
                    <div>
                      <div style={{ fontSize: '0.82rem', color: 'var(--text-primary)', fontWeight: 800 }}>
                        {node.label ?? node.partRole ?? 'Part'}
                      </div>
                      <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
                        {node.partRole ?? 'unknown'}
                      </div>
                    </div>
                    <div style={{ textAlign: 'right', fontSize: '0.76rem', color: 'var(--text-secondary)' }}>
                      <div>{node.elementCount ?? 0} elems</div>
                      <div>{node.aliveElementCount ?? node.elementCount ?? 0} alive</div>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div style={panelBoxStyle}>
              <div style={panelTitleStyle}>
                <ShieldAlert size={15} color="var(--danger-400)" />
                Evidence boundary
              </div>
              <div style={{ color: 'var(--text-secondary)', fontSize: '0.76rem', lineHeight: 1.45, overflowWrap: 'anywhere' }}>
                {summary.claimBoundary}
              </div>
              <div style={{ color: 'var(--text-muted)', fontSize: '0.72rem', lineHeight: 1.45, marginTop: '8px', overflowWrap: 'anywhere' }}>
                VTU: {vtuState}
              </div>
            </div>
          </div>
        </div>
      ) : (
        <div data-testid="result-mesh-empty" style={{ padding: '14px' }}>
          <EmptyStateCard
            headline="No active dynamic payload"
            body="Run an explicit-dynamics solver for this case to populate frames of stress + displacement evolution. Static-only cases will not surface a playback timeline."
            glyph="∅"
          />
        </div>
      )}
    </section>
  );
}

function MetricGrid({ summary }: { summary: NonNullable<ReturnType<typeof summarizeResultMeshPlayback>> }) {
  const rows = [
    ['Nodes', formatInteger(summary.nodeCount)],
    ['Faces', formatInteger(summary.elementCount)],
    ['Projectile', formatInteger(summary.projectileElements)],
    ['Plate', formatInteger(summary.plateElements)],
    ['Deleted', formatInteger(summary.deletedElements)],
    ['Max disp', formatNumber(summary.maxDisplacement)],
    ['Min field', formatNumber(summary.valueMin)],
    ['Max field', formatNumber(summary.valueMax)],
  ];

  return (
    <div style={{ ...panelBoxStyle, padding: '10px' }}>
      <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', fontWeight: 800, marginBottom: '8px' }}>
        {summary.fieldLabel}
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, minmax(0, 1fr))', gap: '8px' }}>
        {rows.map(([label, value]) => (
          <div key={label} style={{ border: '1px solid var(--border)', borderRadius: '8px', padding: '8px', minHeight: '50px' }}>
            <div style={{ color: 'var(--text-muted)', fontSize: '0.66rem', fontWeight: 800, textTransform: 'uppercase' }}>
              {label}
            </div>
            <div style={{ color: 'var(--text-primary)', fontSize: '0.9rem', fontWeight: 800, marginTop: '3px' }}>
              {value}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function buildProjection(frame: ResultMeshFrame | null, valueMin: number, valueMax: number, colormap: ColormapId): ProjectedPolygon[] {
  if (!frame) return [];
  const nodeMap = new Map<number, number[]>();
  frame.nodes.forEach((node) => {
    const point = readPoint(node);
    if (point) nodeMap.set(node.label, point);
  });

  const points = Array.from(nodeMap.values());
  const axes = selectProjectionAxes(points);
  const bounds = computeBounds(points, axes);
  if (!bounds) return [];

  const projected = frame.elements
    .filter((element) => (element.connectivity?.length ?? 0) >= 3)
    .map((element, index) => projectElement(element, index, nodeMap, axes, bounds, valueMin, valueMax, colormap))
    .filter((polygon): polygon is ProjectedPolygon => Boolean(polygon))
    .sort((a, b) => a.order - b.order);
  return projected;
}

function readPoint(node: ResultMeshNode): number[] | null {
  const point = node.deformed ?? node.coordinates;
  return point && point.length >= 3 ? point : null;
}

function selectProjectionAxes(points: number[][]): [number, number] {
  if (points.length === 0) return [0, 1];
  const ranges = [0, 1, 2].map((axis) => {
    const values = points.map((point) => point[axis]);
    return { axis, range: Math.max(...values) - Math.min(...values) };
  });
  const sorted = ranges.sort((a, b) => b.range - a.range);
  return [sorted[0]?.axis ?? 0, sorted[1]?.axis ?? 1];
}

function computeBounds(points: number[][], axes: [number, number]) {
  if (points.length === 0) return null;
  const xs = points.map((point) => point[axes[0]]);
  const ys = points.map((point) => point[axes[1]]);
  const minX = Math.min(...xs);
  const maxX = Math.max(...xs);
  const minY = Math.min(...ys);
  const maxY = Math.max(...ys);
  return {
    minX,
    minY,
    scale: Math.min(880 / Math.max(maxX - minX, 1e-9), 340 / Math.max(maxY - minY, 1e-9)),
    offsetX: 500 - ((minX + maxX) / 2) * Math.min(880 / Math.max(maxX - minX, 1e-9), 340 / Math.max(maxY - minY, 1e-9)),
    offsetY: 220 + ((minY + maxY) / 2) * Math.min(880 / Math.max(maxX - minX, 1e-9), 340 / Math.max(maxY - minY, 1e-9)),
  };
}

function projectElement(
  element: ResultMeshElement,
  index: number,
  nodeMap: Map<number, number[]>,
  axes: [number, number],
  bounds: NonNullable<ReturnType<typeof computeBounds>>,
  valueMin: number,
  valueMax: number,
  colormap: ColormapId,
): ProjectedPolygon | null {
  const projectedPoints = (element.connectivity ?? [])
    .map((nodeLabel) => nodeMap.get(nodeLabel))
    .filter((point): point is number[] => Boolean(point))
    .map((point) => {
      const x = point[axes[0]] * bounds.scale + bounds.offsetX;
      const y = bounds.offsetY - point[axes[1]] * bounds.scale;
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    });

  if (projectedPoints.length < 3) return null;
  const alive = element.alive !== false;
  const isProjectile = element.partRole === 'projectile';
  return {
    key: `${element.sourceElement ?? element.label ?? index}-${index}`,
    points: projectedPoints.join(' '),
    fill: alive ? colorForElement(element, valueMin, valueMax, colormap) : 'rgba(239, 68, 68, 0.28)',
    stroke: isProjectile ? '#f8fafc' : alive ? 'rgba(148, 163, 184, 0.5)' : 'rgba(239, 68, 68, 0.75)',
    opacity: isProjectile ? 0.92 : alive ? 0.86 : 0.5,
    order: isProjectile ? 3 : alive ? 1 : 2,
  };
}

// FM-04a Phase 43 Slice 4b (Codex R0 P2) — the SVG-fallback mesh coloring now
// samples the SHARED colormap SSOT, so changing the colormap selector recolors
// the SVG polygons too (previously hard-coded spectral, leaving the legend and
// mesh inconsistent in viewportMode==='svg' / context-loss fallback). At the
// default 'spectral' the rgb() output is byte-identical to the prior ramp.
function colorForElement(
  element: ResultMeshElement,
  valueMin: number,
  valueMax: number,
  colormap: ColormapId,
) {
  if (element.partRole === 'projectile') return '#e5e7eb';
  const value = element.value ?? valueMin;
  const t = valueMax > valueMin ? Math.min(Math.max((value - valueMin) / (valueMax - valueMin), 0), 1) : 0;
  const [r, g, b] = sampleColormap(colormap, t);
  return `rgb(${Math.round(r * 255)}, ${Math.round(g * 255)}, ${Math.round(b * 255)})`;
}

function readVtuState(payload: ResultMeshPayload | null) {
  const manifest = payload?.artifacts?.vtuManifest;
  if (!manifest || typeof manifest !== 'object' || Array.isArray(manifest)) return 'not surfaced';
  const record = manifest as Record<string, unknown>;
  const status = typeof record.status === 'string' ? record.status : 'unknown';
  const path = typeof record.path === 'string' ? record.path : 'vtu_manifest.json';
  return `${status} / ${path}`;
}

function formatNumber(value: number) {
  if (!Number.isFinite(value)) return '0';
  const magnitude = Math.abs(value);
  if (magnitude > 0 && magnitude < 0.001) return value.toExponential(2);
  return numberFormat.format(value);
}

function formatInteger(value: number) {
  return Number.isFinite(value) ? String(Math.trunc(value)) : '0';
}

const panelBoxStyle = {
  border: '1px solid var(--border)',
  borderRadius: '8px',
  background: 'var(--c-100)',
  padding: '12px',
} satisfies CSSProperties;

const panelTitleStyle = {
  display: 'flex',
  alignItems: 'center',
  gap: '8px',
  color: 'var(--text-primary)',
  fontSize: '0.84rem',
  fontWeight: 800,
  marginBottom: '8px',
} satisfies CSSProperties;

// FM-04a Phase 22 B — depth controls for the WebGL viewport:
// deformation magnification slider (1×..100×) + section-cut row
// (axis radio + position slider + low/high half toggle).
// Phase 23 D — extended with element-value threshold filter row.
// Phase 26 B — section-cut and threshold-filter rows are gated by
// `showSectionCut` / `showThresholdFilter`. Defaults default to true
// for back-compat with any call site that does not opt in. The
// deformation row stays unconditional — it is not in
// ADVANCED_FEATURE_IDS and is a fundamental rendering affordance.
// State preservation (C:-1 anti-gaming guard): hiding a row does
// NOT clear `sectionCut` / `valueFilter` in the parent — toggling
// back to advanced restores the same values.
export function ViewportDepthControls({
  deformationScale,
  onDeformationScaleChange,
  sectionCut,
  onSectionCutChange,
  valueFilter,
  onValueFilterChange,
  valueRange,
  showSectionCut = true,
  showThresholdFilter = true,
  isoSurfaceEnabled = false,
  onIsoSurfaceToggle,
  isoThreshold = null,
  onIsoThresholdChange,
  showIsoSurface = true,
}: {
  deformationScale: number;
  onDeformationScaleChange: (value: number) => void;
  sectionCut: SectionCutState | null;
  onSectionCutChange: (next: SectionCutState | null) => void;
  valueFilter: ValueFilterState | null;
  onValueFilterChange: (next: ValueFilterState | null) => void;
  valueRange: [number, number];
  showSectionCut?: boolean;
  showThresholdFilter?: boolean;
  // FM-04a Phase 40 A — iso-surface overlay controls (opt-in).
  isoSurfaceEnabled?: boolean;
  onIsoSurfaceToggle?: (enabled: boolean) => void;
  isoThreshold?: number | null;
  onIsoThresholdChange?: (value: number) => void;
  showIsoSurface?: boolean;
}) {
  const cutEnabled = sectionCut !== null;
  const axis = sectionCut?.axis ?? 'x';
  const positionM = sectionCut?.positionM ?? 0;
  const showLow = sectionCut?.showLow ?? true;
  const filterEnabled = valueFilter !== null;
  const [vMin, vMax] = valueRange;
  const filterMin = valueFilter?.minValue ?? vMin;
  const filterMax = valueFilter?.maxValue ?? vMax;
  const filterMode = valueFilter?.mode ?? 'inside';
  // FM-04a Phase 40 A — iso-surface threshold default = midpoint of the
  // field range (matches the viewport's own fallback).
  // KNOWN LIMITATION (Codex R2 P2, deferred to retro queue per round-cap-3):
  // [vMin, vMax] is the `value` / payload fieldRanges domain. When the
  // reviewer switches to a tensor-derived component (σ_xx / σ_3 / …) the
  // slider is still clamped to this domain and the midpoint default can
  // fall outside the component's true range, so the badge may read
  // "no crossing" when one exists. The existing value-filter slider
  // shares the identical limitation (same valueRange source), so iso is
  // consistent with the established pattern; a per-component range
  // derivation is a separate follow-up (see codex_round3_overflow_phase40A).
  const isoThresholdEffective = isoThreshold ?? (vMin + vMax) / 2;
  // FM-04a Phase 27 C — section-cut hover preview state. true
  // while the user is actively dragging the position slider; the
  // floating readout above the slider shows the cut position in
  // meters. False on release; the readout disappears.
  const [isDraggingCutPosition, setIsDraggingCutPosition] =
    useState<boolean>(false);

  return (
    <div
      data-testid="viewport-depth-controls"
      style={{
        display: 'grid',
        gridTemplateColumns: '1fr 1fr',
        gap: 10,
        padding: '8px 10px',
        border: '1px solid var(--border)',
        borderRadius: 6,
        background: 'var(--c-100)',
        fontSize: '0.72rem',
        color: 'var(--text-secondary)',
      }}
    >
      <label
        data-testid="deformation-scale-control"
        style={{ display: 'grid', gap: 4 }}
      >
        <span style={{ fontWeight: 700, color: 'var(--text-primary)' }}>
          Deformation ×{deformationScale.toFixed(0)}
        </span>
        <input
          aria-label="Deformation magnification"
          type="range"
          min={1}
          max={100}
          step={1}
          value={deformationScale}
          onChange={(event) =>
            onDeformationScaleChange(Number(event.target.value))
          }
          data-testid="deformation-scale-input"
        />
      </label>
      {showSectionCut && (
      <div
        data-testid="section-cut-control"
        style={{ display: 'grid', gap: 4 }}
      >
        <label
          style={{
            display: 'flex',
            gap: 6,
            alignItems: 'center',
            fontWeight: 700,
            color: 'var(--text-primary)',
          }}
        >
          <input
            type="checkbox"
            data-testid="section-cut-toggle"
            checked={cutEnabled}
            onChange={(event) =>
              onSectionCutChange(
                event.target.checked
                  ? { axis: 'x', positionM: 0, showLow: true }
                  : null,
              )
            }
          />
          Section cut
        </label>
        {cutEnabled && (
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'auto 1fr auto',
              gap: 6,
              alignItems: 'center',
            }}
          >
            <select
              aria-label="Section-cut axis"
              data-testid="section-cut-axis"
              value={axis}
              onChange={(event) =>
                onSectionCutChange({
                  axis: event.target.value as 'x' | 'y' | 'z',
                  positionM,
                  showLow,
                })
              }
              style={{
                background: 'transparent',
                color: 'var(--text-primary)',
                border: '1px solid var(--border)',
                borderRadius: 3,
                padding: '2px 4px',
              }}
            >
              <option value="x">X</option>
              <option value="y">Y</option>
              <option value="z">Z</option>
            </select>
            <div style={{ position: 'relative', display: 'flex', alignItems: 'center' }}>
              <input
                aria-label="Section-cut position"
                type="range"
                min={-1}
                max={1}
                step={0.01}
                value={positionM}
                data-testid="section-cut-position"
                className={POLISH_CLASS_GRADIENT_SLIDER}
                style={{ flex: 1 }}
                onChange={(event) =>
                  onSectionCutChange({
                    axis,
                    positionM: Number(event.target.value),
                    showLow,
                  })
                }
                onMouseDown={() => setIsDraggingCutPosition(true)}
                onMouseUp={() => setIsDraggingCutPosition(false)}
                onMouseLeave={() => setIsDraggingCutPosition(false)}
                onTouchStart={() => setIsDraggingCutPosition(true)}
                onTouchEnd={() => setIsDraggingCutPosition(false)}
              />
              {/* FM-04a Phase 27 C — section-cut position hover
                  readout. Only rendered while actively dragging; CSS
                  positions it 120% above the slider thumb (rough
                  approximation via translate-50% on the wrapping
                  div's center; exact thumb-tracking would need a
                  ref+resize-observer which is out of scope). */}
              {isDraggingCutPosition && (
                <div
                  data-testid="section-cut-position-readout"
                  className={POLISH_CLASS_SECTION_CUT_READOUT}
                  style={{
                    left: `${((positionM - -1) / 2) * 100}%`,
                    top: 0,
                  }}
                >
                  {axis} = {positionM.toFixed(2)} m
                </div>
              )}
            </div>
            <button
              type="button"
              data-testid="section-cut-flip"
              onClick={() =>
                onSectionCutChange({ axis, positionM, showLow: !showLow })
              }
              style={{
                background: 'transparent',
                color: 'var(--text-primary)',
                border: '1px solid var(--border)',
                borderRadius: 3,
                padding: '2px 6px',
                fontFamily:
                  'ui-monospace, SFMono-Regular, "SF Mono", Menlo, monospace',
                cursor: 'pointer',
              }}
            >
              {showLow ? '−' : '+'}
            </button>
          </div>
        )}
      </div>
      )}
      {/* Phase 23 D — element-value threshold filter row.
          Phase 26 B — gated by showThresholdFilter (basic mode hides
          the row while preserving valueFilter state in the parent). */}
      {showThresholdFilter && (
      <div
        data-testid="value-filter-control"
        style={{ display: 'grid', gap: 4, gridColumn: '1 / -1' }}
      >
        <label
          style={{
            display: 'flex',
            gap: 6,
            alignItems: 'center',
            fontWeight: 700,
            color: 'var(--text-primary)',
          }}
        >
          <input
            type="checkbox"
            data-testid="value-filter-toggle"
            checked={filterEnabled}
            onChange={(event) =>
              onValueFilterChange(
                event.target.checked
                  ? { minValue: vMin, maxValue: vMax, mode: 'inside' }
                  : null,
              )
            }
          />
          Element threshold filter
        </label>
        {filterEnabled && (
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: '1fr 1fr auto',
              gap: 8,
              alignItems: 'center',
            }}
          >
            <label style={{ display: 'grid', gap: 2 }}>
              <span style={{ fontSize: '0.66rem' }}>
                min ≥ {filterMin.toExponential(2)}
              </span>
              <input
                aria-label="Value filter minimum"
                type="range"
                min={vMin}
                max={vMax}
                step={(vMax - vMin) / 200 || 1}
                value={filterMin}
                data-testid="value-filter-min"
                className={POLISH_CLASS_GRADIENT_SLIDER}
                onChange={(event) =>
                  onValueFilterChange({
                    minValue: Number(event.target.value),
                    maxValue: filterMax,
                    mode: filterMode,
                  })
                }
              />
            </label>
            <label style={{ display: 'grid', gap: 2 }}>
              <span style={{ fontSize: '0.66rem' }}>
                max ≤ {filterMax.toExponential(2)}
              </span>
              <input
                aria-label="Value filter maximum"
                type="range"
                min={vMin}
                max={vMax}
                step={(vMax - vMin) / 200 || 1}
                value={filterMax}
                data-testid="value-filter-max"
                className={POLISH_CLASS_GRADIENT_SLIDER}
                onChange={(event) =>
                  onValueFilterChange({
                    minValue: filterMin,
                    maxValue: Number(event.target.value),
                    mode: filterMode,
                  })
                }
              />
            </label>
            <button
              type="button"
              data-testid="value-filter-mode"
              onClick={() =>
                onValueFilterChange({
                  minValue: filterMin,
                  maxValue: filterMax,
                  mode: filterMode === 'inside' ? 'outside' : 'inside',
                })
              }
              style={{
                background: 'transparent',
                color: 'var(--text-primary)',
                border: '1px solid var(--border)',
                borderRadius: 3,
                padding: '2px 6px',
                fontFamily:
                  'ui-monospace, SFMono-Regular, "SF Mono", Menlo, monospace',
                fontSize: '0.62rem',
                cursor: 'pointer',
              }}
            >
              {filterMode === 'inside' ? 'IN' : 'OUT'}
            </button>
          </div>
        )}
      </div>
      )}
      {/* FM-04a Phase 40 A — iso-surface overlay row. Opt-in; gated by
          showIsoSurface (advanced). The honesty caption (T:-1 guard) is
          always visible when the toggle row renders, naming the surface
          a smoothed Tier-0 viz approximation so it is never read as the
          solved per-element field. State preserved on hide (C:-1). */}
      {showIsoSurface && (
      <div
        data-testid="iso-surface-control"
        style={{ display: 'grid', gap: 4, gridColumn: '1 / -1' }}
      >
        <label
          style={{
            display: 'flex',
            gap: 6,
            alignItems: 'center',
            fontWeight: 700,
            color: 'var(--text-primary)',
          }}
        >
          <input
            type="checkbox"
            data-testid="iso-surface-toggle"
            checked={isoSurfaceEnabled}
            onChange={(event) => onIsoSurfaceToggle?.(event.target.checked)}
          />
          Iso-surface (smoothed viz)
        </label>
        <div
          data-testid="iso-surface-honesty-caption"
          style={{
            fontSize: '0.62rem',
            color: 'var(--text-muted)',
            lineHeight: 1.4,
          }}
        >
          Tier-0 smoothed approximation (cell→point averaged, tet-only) —
          per-element coloring is the truth view.
        </div>
        {isoSurfaceEnabled && (
          <label style={{ display: 'grid', gap: 2 }}>
            <span style={{ fontSize: '0.66rem' }}>
              threshold = {isoThresholdEffective.toExponential(2)}
            </span>
            <input
              aria-label="Iso-surface threshold"
              type="range"
              min={vMin}
              max={vMax}
              step={(vMax - vMin) / 200 || 1}
              value={isoThresholdEffective}
              data-testid="iso-surface-threshold"
              className={POLISH_CLASS_GRADIENT_SLIDER}
              onChange={(event) =>
                onIsoThresholdChange?.(Number(event.target.value))
              }
            />
          </label>
        )}
      </div>
      )}
    </div>
  );
}
