// FM-04a Phase 43 Slice 4 — result-viewport colormaps (pure, leaf module).
//
// The single source of truth for the value→color ramps the 3D result viewport
// paints with. Extracted as a leaf module (no imports from viewportGeometry,
// so no import cycle) and unit-testable in isolation.
//
// Honesty / regression safety: the DEFAULT colormap 'spectral' reproduces the
// pre-Slice-4 viewport ramp (viewportGeometry.gradientStop's blue→green→orange)
// BYTE-FOR-BYTE — same piecewise-linear arithmetic — so existing visuals and
// the Phase21C gradient-pin test are unchanged. Switching colormaps only swaps
// the t→RGB ramp; the value→t mapping (and therefore which element is "hot")
// is untouched. These are perceptual VISUALISATION ramps (Tier-0 aesthetics),
// not data — the underlying field values are never altered.

export type ColormapId = 'spectral' | 'viridis' | 'turbo' | 'grayscale';

/** The ramp used everywhere unless a colormap is explicitly chosen. */
export const DEFAULT_COLORMAP: ColormapId = 'spectral';

/** Selectable colormaps, in display order. */
export const COLORMAP_IDS: readonly ColormapId[] = [
  'spectral',
  'viridis',
  'turbo',
  'grayscale',
];

/** Human labels for the colormap selector. */
export const COLORMAP_LABELS: Record<ColormapId, string> = {
  spectral: 'Spectral',
  viridis: 'Viridis',
  turbo: 'Turbo',
  grayscale: 'Grayscale',
};

// Each colormap is a list of uniformly-spaced RGB control points in 0..255.
// `sampleColormap` linearly interpolates between adjacent stops. 'spectral'
// MUST stay [blue #2563eb, green #10b981, orange #f97316] at offsets {0,.5,1}
// so it equals the legacy gradientStop ramp exactly.
const STOPS: Record<ColormapId, ReadonlyArray<readonly [number, number, number]>> = {
  spectral: [
    [37, 99, 235], // blue  #2563eb
    [16, 185, 129], // green #10b981
    [249, 115, 22], // orange #f97316
  ],
  // Matplotlib viridis anchors (perceptually uniform, colour-blind safe).
  viridis: [
    [68, 1, 84],
    [59, 82, 139],
    [33, 145, 140],
    [94, 201, 98],
    [253, 231, 37],
  ],
  // Google turbo anchors (high-contrast rainbow without the artefacts of jet).
  turbo: [
    [48, 18, 59],
    [33, 144, 241],
    [27, 229, 181],
    [165, 254, 76],
    [251, 169, 52],
    [217, 35, 8],
  ],
  // Simple dark→light ramp for a neutral, print-friendly view.
  grayscale: [
    [30, 30, 30],
    [235, 235, 235],
  ],
};

/**
 * Sample a colormap at fraction `t`. `t` is clamped to [0,1]; the result is
 * linear RGB with each channel in [0,1] (the form three.js vertex colors and
 * the ScaleBar gradient both consume). Linear interpolation between uniformly
 * spaced control points — identical arithmetic to the legacy gradientStop for
 * 'spectral'.
 */
export function sampleColormap(id: ColormapId, t: number): [number, number, number] {
  const stops = STOPS[id] ?? STOPS.spectral;
  const tc = Math.max(0, Math.min(1, Number.isFinite(t) ? t : 0));
  const n = stops.length;
  if (n === 1) {
    const [r, g, b] = stops[0];
    return [r / 255, g / 255, b / 255];
  }
  // Position within the (n-1) uniform segments; clamp the top so t=1 lands at
  // the end of the last segment (k=1) rather than indexing past the array.
  const scaled = tc * (n - 1);
  let i = Math.floor(scaled);
  if (i >= n - 1) i = n - 2;
  const k = scaled - i;
  const a = stops[i];
  const b = stops[i + 1];
  return [
    (a[0] + (b[0] - a[0]) * k) / 255,
    (a[1] + (b[1] - a[1]) * k) / 255,
    (a[2] + (b[2] - a[2]) * k) / 255,
  ];
}
