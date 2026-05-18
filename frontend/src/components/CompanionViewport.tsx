// FM-04a Phase 30 B — 2-quadrant viewport split companion.
//
// Renders a SECOND ResultMeshWebGLViewport next to the primary one,
// sharing field/component/threshold/playback state but with an
// INDEPENDENT section-cut position. Together they form Hyperworks/
// Abaqus-CAE-style "compare-cuts" 2-quadrant layout.
//
// Honest scope:
// * Only the section-cut state is independent. Camera (orbit/pan/zoom)
//   is also independent because each viewport owns its own three.js
//   scene; we do NOT attempt camera-sync.
// * Two WebGL contexts on screen at once. Browsers cap at ~16 live
//   contexts; two is well under, but flagged for performance
//   monitoring in the Phase 30 B retro.
// * FM-04a Phase 31 D — node-pick callback IS now wired through.
//   Picks from the companion viewport flow into the SAME parent
//   activePick state as the primary; the wrapper here injects
//   `origin: 'companion'` into the PickedNodeInfo so the probe-list
//   renderer can prefix the label cell with "companion:" without
//   re-routing the pick stream. CSV serialization (`serializeProbe
//   ListAsCsv`) IGNORES the origin field to keep the export schema
//   stable (C:-1 — existing CSV tests do not change).
// * De-dup by label (Phase 24 D addProbeEntry) means the same node
//   pinned from primary then companion does NOT create two rows;
//   the FIRST pin wins. This is intentional — the prefix exists to
//   help the reviewer see WHICH viewport surfaced the node first,
//   not to allow double-pinning the same id.
//
// Anti-gaming guards:
// * C:-1: companion section-cut state passed down via props; the
//   companion does NOT mutate the primary's state (or vice versa).
// * E:-1: shared field/component/threshold props are reference-
//   identical to what the primary receives — pinned by test.
//
// Tier 1 / Tier 2 engineering candidate; not signed validation; not
// benchmark agreement.

import { useCallback, useState } from 'react';
import type { ResultMeshFrame } from '../resultMeshPlayback';
import type { StressComponent } from '../stressDerivatives';
import { ResultMeshWebGLViewport } from './ResultMeshWebGLViewport';
import type {
  SectionCutState,
  ValueFilterState,
} from './viewportGeometry';
import type { PickedNodeInfo } from './viewportRaycaster';
import {
  POLISH_CLASS_GRADIENT_SLIDER,
  POLISH_CLASS_SECTION_CUT_READOUT,
} from './polishStyles';

interface CompanionViewportProps {
  /** Shared with primary (E:-1 invariant — both viewports see the
   * same frame). */
  frame: ResultMeshFrame | null;
  /** Shared value range — must match primary's legend min/max. */
  valueMin: number;
  valueMax: number;
  /** Shared playback animation. */
  nextFrame?: ResultMeshFrame | null;
  playing?: boolean;
  /** Shared deformation magnification. */
  deformationScale?: number;
  /** Shared field component switcher. */
  fieldComponent?: StressComponent;
  /** Shared threshold filter. */
  valueFilter?: ValueFilterState | null;
  /** INDEPENDENT — the whole point of the companion. */
  sectionCut: SectionCutState;
  onSectionCutChange: (next: SectionCutState) => void;
  /** FM-04a Phase 31 D — node-pick forwarder. When supplied, picks
   * made inside the companion canvas flow to this callback with
   * `origin: 'companion'` injected; absent → companion picks are
   * dropped (Phase 30 B behavior). */
  onNodePicked?: (info: PickedNodeInfo | null) => void;
}

export function CompanionViewport({
  frame,
  valueMin,
  valueMax,
  nextFrame,
  playing,
  deformationScale,
  fieldComponent,
  valueFilter,
  sectionCut,
  onSectionCutChange,
  onNodePicked,
}: CompanionViewportProps) {
  const [isDragging, setIsDragging] = useState<boolean>(false);

  // FM-04a Phase 31 D — origin-stamping wrapper. Tags every pick
  // with `origin: 'companion'` before forwarding so the probe-list
  // renderer can prefix the label cell with "companion:". Pure-
  // function injection, no state of its own.
  const handlePicked = useCallback(
    (info: PickedNodeInfo | null) => {
      if (!onNodePicked) return;
      if (info === null) {
        onNodePicked(null);
        return;
      }
      onNodePicked({ ...info, origin: 'companion' });
    },
    [onNodePicked],
  );

  return (
    <div
      data-testid="companion-viewport"
      style={{
        flex: 1,
        minWidth: 0,
        display: 'flex',
        flexDirection: 'column',
        gap: 6,
      }}
    >
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: 8,
          padding: '4px 8px',
          background: 'rgba(15, 23, 42, 0.55)',
          borderRadius: 4,
          fontSize: '0.7rem',
          color: 'var(--text-secondary)',
          letterSpacing: '0.04em',
          textTransform: 'uppercase',
        }}
      >
        <span
          data-testid="companion-viewport-label"
          style={{ fontWeight: 700, color: 'var(--text-primary)' }}
        >
          Companion view
        </span>
        <div
          data-testid="companion-section-cut-control"
          style={{
            display: 'grid',
            gridTemplateColumns: 'auto 120px auto',
            gap: 6,
            alignItems: 'center',
          }}
        >
          <select
            aria-label="Companion section-cut axis"
            data-testid="companion-section-cut-axis"
            value={sectionCut.axis}
            onChange={(event) =>
              onSectionCutChange({
                axis: event.target.value as 'x' | 'y' | 'z',
                positionM: sectionCut.positionM,
                showLow: sectionCut.showLow,
              })
            }
            style={{
              background: 'transparent',
              color: 'var(--text-primary)',
              border: '1px solid var(--border)',
              borderRadius: 3,
              padding: '2px 4px',
              textTransform: 'uppercase',
            }}
          >
            <option value="x">X</option>
            <option value="y">Y</option>
            <option value="z">Z</option>
          </select>
          <div style={{ position: 'relative', display: 'flex', alignItems: 'center' }}>
            <input
              aria-label="Companion section-cut position"
              type="range"
              min={-1}
              max={1}
              step={0.01}
              value={sectionCut.positionM}
              data-testid="companion-section-cut-position"
              className={POLISH_CLASS_GRADIENT_SLIDER}
              style={{ flex: 1 }}
              onChange={(event) =>
                onSectionCutChange({
                  axis: sectionCut.axis,
                  positionM: Number(event.target.value),
                  showLow: sectionCut.showLow,
                })
              }
              onMouseDown={() => setIsDragging(true)}
              onMouseUp={() => setIsDragging(false)}
              onMouseLeave={() => setIsDragging(false)}
              onTouchStart={() => setIsDragging(true)}
              onTouchEnd={() => setIsDragging(false)}
            />
            {isDragging && (
              <div
                data-testid="companion-section-cut-readout"
                className={POLISH_CLASS_SECTION_CUT_READOUT}
                style={{
                  left: `${((sectionCut.positionM - -1) / 2) * 100}%`,
                  top: 0,
                }}
              >
                {sectionCut.axis} = {sectionCut.positionM.toFixed(2)} m
              </div>
            )}
          </div>
          <button
            type="button"
            data-testid="companion-section-cut-flip"
            onClick={() =>
              onSectionCutChange({
                axis: sectionCut.axis,
                positionM: sectionCut.positionM,
                showLow: !sectionCut.showLow,
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
              cursor: 'pointer',
            }}
            aria-label="Flip companion section-cut half"
          >
            {sectionCut.showLow ? '−' : '+'}
          </button>
        </div>
      </div>
      <div
        style={{
          flex: 1,
          minHeight: '210px',
          border: '1px solid var(--border)',
          borderRadius: '8px',
          background: '#020617',
          overflow: 'hidden',
          position: 'relative',
        }}
      >
        <ResultMeshWebGLViewport
          frame={frame}
          valueMin={valueMin}
          valueMax={valueMax}
          nextFrame={nextFrame}
          playing={playing}
          deformationScale={deformationScale}
          sectionCut={sectionCut}
          fieldComponent={fieldComponent}
          valueFilter={valueFilter}
          onNodePicked={onNodePicked ? handlePicked : undefined}
        />
      </div>
    </div>
  );
}
