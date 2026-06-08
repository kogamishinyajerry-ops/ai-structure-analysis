// FM-04a Phase 30 C — Hyperworks-style floating coord readout.
//
// Pure presentational component. Receives world-space (x, y, z) and
// screen-space (px) hit info from the viewport's raycaster and
// renders a small fixed-positioned overlay near the cursor.
//
// Honest scope:
// * NO raycasting here — that lives in the WebGL viewport (which
//   already has scene/mesh access). This component is just the UI.
// * NO throttling here — throttling is applied at the source (the
//   viewport's mousemove handler) so this component never sees
//   high-frequency updates.
// * Coordinates rendered with 3 decimal places (mm precision for a
//   1-m scale mesh).
// * `pointerEvents: none` so the tooltip never intercepts mouse
//   events that should hit the viewport canvas.
//
// Anti-gaming guards:
// * D:-1: when info is null, component returns null (renders nothing).
//         The tooltip never persists after the mouse leaves.
// * E:-1: when info has non-finite values, component returns null
//         (don't render NaN to the user).
//
// Tier 1 / Tier 2 engineering candidate; not signed validation; not
// benchmark agreement.

interface CoordReadoutTooltipProps {
  /** World-space coordinates of the cursor's mesh hit, plus screen-
   * space anchor (px relative to the viewport-slot's bounding box).
   * When `null`, the tooltip renders nothing. */
  info: {
    worldX: number;
    worldY: number;
    worldZ: number;
    screenX: number;
    screenY: number;
  } | null;
}

export function CoordReadoutTooltip({ info }: CoordReadoutTooltipProps) {
  if (info === null) return null;
  if (
    !Number.isFinite(info.worldX)
    || !Number.isFinite(info.worldY)
    || !Number.isFinite(info.worldZ)
  ) {
    return null;
  }
  return (
    <div
      data-testid="coord-readout-tooltip"
      role="status"
      aria-live="off"
      style={{
        position: 'absolute',
        left: info.screenX + 12,
        top: info.screenY + 12,
        zIndex: 15,
        padding: '4px 8px',
        background: 'rgba(2, 6, 23, 0.92)',
        border: '1px solid rgba(148, 163, 184, 0.4)',
        borderRadius: 4,
        color: '#e2e8f0',
        fontSize: '0.66rem',
        fontFamily:
          'ui-monospace, SFMono-Regular, "SF Mono", Menlo, monospace',
        pointerEvents: 'none',
        whiteSpace: 'nowrap',
        lineHeight: 1.35,
        display: 'grid',
        gridTemplateColumns: 'auto auto',
        columnGap: 6,
      }}
    >
      <span style={{ color: '#94a3b8' }}>x</span>
      <span data-testid="coord-readout-x">{info.worldX.toFixed(3)}</span>
      <span style={{ color: '#94a3b8' }}>y</span>
      <span data-testid="coord-readout-y">{info.worldY.toFixed(3)}</span>
      <span style={{ color: '#94a3b8' }}>z</span>
      <span data-testid="coord-readout-z">{info.worldZ.toFixed(3)}</span>
    </div>
  );
}

/** Pure helper: 30Hz throttle. Returns a wrapper function that, given
 * a stream of calls, invokes the underlying callback at most once
 * every ~33ms. Useful as the source-side throttle on the viewport's
 * mousemove handler so the raycaster + setState don't fire at the
 * browser's native event rate. */
export function makeCoordThrottle<T>(
  callback: (arg: T) => void,
  minIntervalMs = 33,
  now: () => number = () => Date.now(),
): (arg: T) => void {
  let lastFiredAt = -Infinity;
  return (arg: T) => {
    const t = now();
    if (t - lastFiredAt < minIntervalMs) return;
    lastFiredAt = t;
    callback(arg);
  };
}
