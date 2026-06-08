// FM-04a Phase 43 — viewport navigation presets (pure data).
//
// The named camera presets + their azimuth/elevation table live here (a
// pure, component-free module) so the gizmo (ViewportNavGizmo.tsx), the
// viewport camera seam (ResultMeshWebGLViewport.setView), and the test all
// consume ONE source of truth — and so the .tsx component files only export
// components (Vite Fast-Refresh / react-refresh hygiene).

/** The named camera presets the gizmo can request. `fit` = iso angle +
 * a bounds-framing fit (the viewport recomputes radius for it too). */
export type ViewPreset = 'iso' | 'top' | 'front' | 'right' | 'fit';

/** Pure preset → camera-angle table (RADIANS, matching the viewport's
 * hand-rolled spherical convention: azimuth around +Y, elevation off the
 * horizon). `fit` carries the iso angle AND a `frame` flag so the host
 * knows to recompute the bounds-framing radius.
 *
 * Convention sanity (matches renderScene in ResultMeshWebGLViewport):
 *   pos = target + radius * (cosE*cosA, sinE, cosE*sinA)
 *   - Top:   elevation = +90° → camera straight above, looking down.
 *   - Front: azimuth 0, elevation 0 → looks along -X toward target.
 *   - Right: azimuth +90°, elevation 0 → looks along -Z toward target.
 *   - Iso:   azimuth +45°, elevation +30°.
 */
export const VIEW_PRESET_ANGLES: Record<
  ViewPreset,
  { azimuth: number; elevation: number; frame: boolean }
> = {
  iso: { azimuth: Math.PI / 4, elevation: Math.PI / 6, frame: false },
  top: { azimuth: 0, elevation: Math.PI / 2 - 0.01, frame: false },
  front: { azimuth: 0, elevation: 0, frame: false },
  right: { azimuth: Math.PI / 2, elevation: 0, frame: false },
  // Fit = iso framing + a radius recompute from the geometry bounds.
  fit: { azimuth: Math.PI / 4, elevation: Math.PI / 6, frame: true },
};
