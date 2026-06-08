// FM-04a Phase 43 — result-viewport color legend (ScaleBar).
//
// The vertical color legend every reference CAE tool (Abaqus / ANSYS /
// Hyperworks / Simcenter) shows over the 3D result viewport: a color ramp
// mapping the active field-value range to the same colors the mesh is
// painted with, annotated with numeric ticks.
//
// Honest scope / Tier discipline (Tier 1 engineering candidate):
// * Presentational only — NO state, NO effects, NO three.js. A dark-glass
//   overlay floating over the DARK WebGL canvas (sibling of ViewportNavGizmo).
// * The gradient is sampled from `colorForValueFraction` — the SAME ramp the
//   mesh-coloring path (viewportGeometry.colorForElement → gradientStop) uses,
//   so the legend can never lie about the on-screen colors.
// * The tick labels are derived ENTIRELY from the `valueMin` / `valueMax` this
//   component receives, which ARE the active mesh-coloring range — the legend
//   faithfully describes the range the viewport is currently coloring by. No
//   value is fabricated: a degenerate constant field (valueMax <= valueMin)
//   renders the band with a SINGLE value, not a fake gradient of distinct ticks.
// * Numeric labels are formatted with `formatHeroValue` so the legend's numbers
//   match the hardened hero peak-readout byte-for-byte.
//
// Not signed validation; not benchmark agreement.

import type { StressComponent } from '../stressDerivatives';
import { colorForValueFraction } from './viewportGeometry';
import { FIELD_COMPONENT_LABELS, formatHeroValue } from './heroPeakFormat';
import { DEFAULT_COLORMAP, type ColormapId } from './colormaps';

export interface ScaleBarProps {
  /** Lower bound of the active mesh-coloring range (maps to t=0, band bottom). */
  valueMin: number;
  /** Upper bound of the active mesh-coloring range (maps to t=1, band top). */
  valueMax: number;
  /** Field the viewport is coloring by; selects the legend title. Default 'mises'. */
  fieldComponent?: StressComponent;
  /** Engineering units suffix (e.g. 'Pa'); OMITTED when absent — never fabricated. */
  units?: string | null;
  /** Active colormap — MUST match the viewport's so the legend ramp equals the
   * mesh coloring. Defaults to 'spectral' (legacy ramp). */
  colormap?: ColormapId;
}

// Number of color stops sampled to build the CSS gradient. 11 stops resolve
// the blue→green→orange ramp smoothly without an oversized style string.
const GRADIENT_STOPS = 11;

// Number of numeric ticks alongside the band (max at top … min at bottom).
const TICK_COUNT = 5;

// Band geometry — a tall thin vertical bar, the CAE legend convention.
const BAND_HEIGHT = 180;
const BAND_WIDTH = 14;

// Build the CSS linear-gradient by sampling the SHARED ramp at GRADIENT_STOPS
// points. CSS gradients run top→bottom by default; we declare `to top` so the
// stop at offset 0% sits at the BOTTOM (t=0 = valueMin) and 100% at the TOP
// (t=1 = valueMax) — value increases upward, matching the CAE convention.
function buildGradient(colormap: ColormapId): string {
  const stops: string[] = [];
  for (let i = 0; i < GRADIENT_STOPS; i++) {
    const t = i / (GRADIENT_STOPS - 1);
    const [r, g, b] = colorForValueFraction(t, colormap);
    const rgb = `rgb(${Math.round(r * 255)}, ${Math.round(g * 255)}, ${Math.round(b * 255)})`;
    const pct = (t * 100).toFixed(1);
    stops.push(`${rgb} ${pct}%`);
  }
  return `linear-gradient(to top, ${stops.join(', ')})`;
}

// When the range collapses (valueMax <= valueMin / non-finite bound) the mesh
// paints EVERY element with the single t=0 ramp color (colorForElement forces
// t=0 in that case). The legend must match — a SOLID band of that same color,
// not the full ramp, or it would contradict the on-screen mesh (Codex R0).
function solidStopColor(colormap: ColormapId): string {
  const [r, g, b] = colorForValueFraction(0, colormap);
  return `rgb(${Math.round(r * 255)}, ${Math.round(g * 255)}, ${Math.round(b * 255)})`;
}

export function ScaleBar({
  valueMin,
  valueMax,
  fieldComponent = 'mises',
  units,
  colormap = DEFAULT_COLORMAP,
}: ScaleBarProps) {
  const title = FIELD_COMPONENT_LABELS[fieldComponent] ?? fieldComponent;
  const unitSuffix = units ? ` ${units}` : '';

  // A degenerate / constant field (valueMax <= valueMin, incl. equal bounds)
  // has no meaningful gradient of distinct ticks — honestly show a SINGLE value
  // rather than fabricate a spread. Also guards against NaN/Infinity bounds.
  const hasRange =
    Number.isFinite(valueMin) && Number.isFinite(valueMax) && valueMax > valueMin;

  // Ticks: top → bottom, evenly interpolated across [valueMin, valueMax].
  // Index 0 is the TOP tick (valueMax); the last is the BOTTOM tick (valueMin).
  const tickValues: number[] = hasRange
    ? Array.from({ length: TICK_COUNT }, (_, i) => {
        const frac = i / (TICK_COUNT - 1); // 0 at top … 1 at bottom
        return valueMax - frac * (valueMax - valueMin);
      })
    : // Degenerate: a single value (prefer the finite bound; fall back to 0).
      [Number.isFinite(valueMax) ? valueMax : Number.isFinite(valueMin) ? valueMin : 0];

  // Full ramp when there's a real range; a solid t=0 band when it collapses,
  // so the legend always matches what colorForElement paints on the mesh.
  const gradient = hasRange ? buildGradient(colormap) : solidStopColor(colormap);

  return (
    <div
      data-testid="result-scale-bar"
      style={{
        position: 'absolute',
        left: 16,
        top: '50%',
        transform: 'translateY(-50%)',
        zIndex: 5,
        pointerEvents: 'none',
        display: 'flex',
        flexDirection: 'column',
        gap: 'var(--sp-2)',
        background: 'rgba(30, 27, 22, 0.82)',
        border: '1px solid rgba(255, 255, 255, 0.10)',
        borderRadius: 'var(--r-sm)',
        padding: 'var(--sp-2) var(--sp-3)',
        backdropFilter: 'blur(6px)',
      }}
    >
      <div
        data-testid="scale-bar-title"
        style={{
          color: 'rgba(255, 255, 255, 0.92)',
          fontSize: 'var(--fs-xs)',
          fontWeight: 700,
          textTransform: 'uppercase',
          letterSpacing: '0.06em',
          whiteSpace: 'nowrap',
        }}
      >
        {title}
        {unitSuffix}
      </div>

      <div style={{ display: 'flex', alignItems: 'stretch', gap: 8 }}>
        {/* The gradient band — same ramp the mesh is painted with. */}
        <div
          data-testid="scale-bar-band"
          aria-hidden="true"
          style={{
            width: BAND_WIDTH,
            height: BAND_HEIGHT,
            background: gradient,
            borderRadius: 'var(--r-xs)',
            border: '1px solid rgba(255, 255, 255, 0.18)',
            flexShrink: 0,
          }}
        />

        {/* Tick labels: top-aligned to band top, bottom to band bottom. For a
            single degenerate value we just stack it (no spread to fabricate). */}
        <div
          style={{
            height: BAND_HEIGHT,
            display: 'flex',
            flexDirection: 'column',
            justifyContent: hasRange ? 'space-between' : 'center',
            color: 'rgba(255, 255, 255, 0.82)',
            fontFamily: 'var(--font-mono)',
            fontSize: '11px',
            lineHeight: 1,
            whiteSpace: 'nowrap',
          }}
        >
          {tickValues.map((v, i) => (
            <span data-testid="scale-bar-tick" key={i}>
              {formatHeroValue(v)}
            </span>
          ))}
        </div>
      </div>
    </div>
  );
}
