// FM-04a Phase 43 — viewport navigation gizmo.
//
// A dark-glass HUD overlay floating in a corner of the 3D WebGL
// viewport. Renders (a) a small static orientation triad (X/Y/Z axis
// labels) and (b) a compact row of standard-view buttons — Iso / Top /
// Front / Right / Fit. Each button invokes the `onSetView` callback
// with a named preset; the host viewport translates that into a camera
// azimuth/elevation (and, for Fit, a bounds-framing radius recompute).
//
// Honest scope:
// * Presentational only — NO three.js / camera math here. The preset →
//   (azimuth, elevation) mapping is exported as a pure table so the
//   viewport seam and the test consume the SAME source of truth.
// * The triad is a tasteful STATIC indicator (it does not live-track
//   the camera rotation in this slice). Live-tracking is a manual /
//   visual concern deferred out of this presentational component.
// * Dark-glass styling (semi-opaque dark bg + light text + var(--accent)
//   for the active/hover state) — it floats over the intentionally DARK
//   WebGL canvas, matching CoordReadoutTooltip / the viewport HUD, NOT a
//   white warm-light card.
//
// Tier 1 / Tier 2 engineering candidate; not signed validation; not
// benchmark agreement.

import { useState } from 'react';
import { Box, ArrowDownToLine, ArrowRightToLine, Maximize2 } from 'lucide-react';
// FM-04a Phase 43 — the preset → camera-angle table lives in a pure module
// (shared with the viewport's setView seam + the test) so this component file
// only exports a component (Vite Fast-Refresh hygiene).
import type { ViewPreset } from './viewportNavPresets';

interface ViewButtonSpec {
  preset: ViewPreset;
  label: string;
  Icon: typeof Box;
  title: string;
}

const VIEW_BUTTONS: ReadonlyArray<ViewButtonSpec> = [
  { preset: 'iso', label: 'Iso', Icon: Box, title: 'Isometric view' },
  { preset: 'top', label: 'Top', Icon: ArrowDownToLine, title: 'Top view (looking down)' },
  { preset: 'front', label: 'Front', Icon: ArrowRightToLine, title: 'Front view' },
  { preset: 'right', label: 'Right', Icon: ArrowRightToLine, title: 'Right view' },
  { preset: 'fit', label: 'Fit', Icon: Maximize2, title: 'Fit / Home — frame the whole model' },
];

interface ViewportNavGizmoProps {
  /** Fires with the named preset when a standard-view button is clicked.
   * The host viewport maps the preset to camera azimuth/elevation (and,
   * for `fit`, a bounds-framing radius) and repaints. */
  onSetView: (preset: ViewPreset) => void;
}

export function ViewportNavGizmo({ onSetView }: ViewportNavGizmoProps) {
  const [hovered, setHovered] = useState<ViewPreset | null>(null);
  const [focused, setFocused] = useState<ViewPreset | null>(null);

  return (
    <div
      data-testid="viewport-nav-gizmo"
      style={{
        position: 'absolute',
        left: 12,
        bottom: 12,
        zIndex: 15,
        display: 'flex',
        alignItems: 'flex-end',
        gap: 8,
        background: 'rgba(2, 6, 23, 0.82)',
        border: '1px solid rgba(148, 163, 184, 0.28)',
        borderRadius: 'var(--r-sm)',
        padding: '7px 9px',
        boxShadow: '0 6px 18px -8px rgba(0, 0, 0, 0.6)',
        backdropFilter: 'blur(6px)',
      }}
    >
      {/* (a) Static orientation triad — X (red) / Y (green) / Z (blue),
          the conventional CAD axis colors, on a dark chip so they read
          over the dark canvas. */}
      <div
        data-testid="viewport-nav-triad"
        aria-hidden="true"
        title="Orientation: X / Y / Z"
        style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          gap: 2,
          padding: '4px 7px',
          marginRight: 2,
          borderRight: '1px solid rgba(148, 163, 184, 0.18)',
          fontFamily: 'var(--font-mono)',
          fontSize: '0.6rem',
          fontWeight: 700,
          letterSpacing: '0.04em',
          lineHeight: 1.25,
        }}
      >
        <span style={{ color: '#fb7185' }}>X</span>
        <span style={{ color: '#4ade80' }}>Y</span>
        <span style={{ color: '#60a5fa' }}>Z</span>
      </div>

      {/* (b) Standard-view buttons. Real <button> elements → keyboard
          focusable; visible hover/focus uses var(--accent). */}
      <div style={{ display: 'flex', gap: 5 }}>
        {VIEW_BUTTONS.map(({ preset, label, Icon, title }) => {
          const active = hovered === preset || focused === preset;
          return (
            <button
              key={preset}
              type="button"
              data-testid={`viewport-nav-${preset}`}
              title={title}
              aria-label={title}
              onClick={() => onSetView(preset)}
              onMouseEnter={() => setHovered(preset)}
              onMouseLeave={() => setHovered((p) => (p === preset ? null : p))}
              onFocus={() => setFocused(preset)}
              onBlur={() => setFocused((p) => (p === preset ? null : p))}
              style={{
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                gap: 2,
                minWidth: 38,
                padding: '5px 6px',
                cursor: 'pointer',
                color: active ? '#fff' : '#cbd5e1',
                background: active ? 'var(--accent)' : 'rgba(148, 163, 184, 0.10)',
                border: active
                  ? '1px solid var(--accent)'
                  : '1px solid rgba(148, 163, 184, 0.22)',
                borderRadius: 'var(--r-xs)',
                fontFamily: 'var(--font-mono)',
                fontSize: '0.6rem',
                fontWeight: 600,
                letterSpacing: '0.05em',
                outline: active ? '2px solid var(--accent-400)' : 'none',
                outlineOffset: 1,
                transition: 'background 130ms ease, color 130ms ease, border-color 130ms ease',
              }}
            >
              <Icon size={14} strokeWidth={2} aria-hidden="true" />
              <span>{label}</span>
            </button>
          );
        })}
      </div>
    </div>
  );
}
