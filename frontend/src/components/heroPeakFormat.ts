// FM-04a Phase 43 — hero peak-readout formatting (pure helpers).
//
// Extracted from HeroPeakReadout.tsx so the .tsx file only exports a
// component (Vite Fast-Refresh hygiene) and the formatting logic is
// unit-testable in isolation, shared with the component.

import { componentValue, type StressComponent } from '../stressDerivatives';
import type { ResultMeshElement } from '../resultMeshPlayback';

// Largest sensible heading token for the value. The MetricGrid cells
// render their value at 0.9rem; --fs-xl (1.6rem) is unambiguously larger
// so the peak reads as the headline.
export const HERO_VALUE_FONT_SIZE_TOKEN = 'var(--fs-xl)';

const numberFormat = new Intl.NumberFormat('en-US', { maximumFractionDigits: 3 });

// Mirrors ResultMeshPlaybackPanel.formatNumber so the hero value matches
// the MetricGrid formatting (small magnitudes => exponential).
export function formatHeroValue(value: number | null | undefined): string {
  if (value === null || value === undefined || !Number.isFinite(value)) return '0';
  const magnitude = Math.abs(value);
  if (magnitude > 0 && magnitude < 0.001) return value.toExponential(2);
  return numberFormat.format(value);
}

// Human labels for the stress-tensor field components (mirrors the legend
// dropdown options) so the hero headline NAMES the field the viewport is
// actually coloring by — not always "von Mises".
export const FIELD_COMPONENT_LABELS: Record<StressComponent, string> = {
  mises: 'Von Mises stress',
  sxx: 'σxx · normal X',
  syy: 'σyy · normal Y',
  szz: 'σzz · normal Z',
  sxy: 'τxy · shear',
  syz: 'τyz · shear',
  sxz: 'τxz · shear',
  max_principal: 'σ1 · max principal',
  min_principal: 'σ3 · min principal',
};

export interface HeroFieldInput {
  fieldLabel: string;
  valueMax: number;
  elements: readonly ResultMeshElement[];
}

export interface HeroFieldSelection {
  label: string;
  value: number;
}

/**
 * FM-04a Phase 43 (Codex R0 P2) — pick the hero-readout field that MATCHES
 * what the viewport is currently coloring by. For the scalar/Mises default the
 * summary's pre-computed valueMax is authoritative; for an explicitly selected
 * tensor component we recompute the peak over the frame's tensor-bearing
 * elements with the SAME `componentValue` path the viewport / pick-HUD /
 * geometry builder use (viewportGeometry.ts), so the headline can never report
 * von Mises while the plot shows σxx. Falls back to the scalar summary when no
 * tensor data is reachable (defensive — the switcher is gated on tensor
 * presence).
 */
export function selectActiveFieldPeak(
  input: HeroFieldInput,
  fieldComponent: StressComponent,
): HeroFieldSelection {
  if (fieldComponent === 'mises') {
    return { label: input.fieldLabel, value: input.valueMax };
  }
  // No tensor anywhere → the field IS the scalar `value` path (the switcher is
  // gated on tensor presence); naming it a σ-component would mislabel scalar
  // data, so keep the scalar summary. (Codex R0 P2 — defensive fallback.)
  if (!input.elements.some((el) => Boolean(el.stressTensor))) {
    return { label: input.fieldLabel, value: input.valueMax };
  }
  // Mixed / all-tensor frame: recompute the peak over EVERY element via the
  // SAME path the viewport colors by (viewportGeometry.colorForElement +
  // ResultMeshWebGLViewport) — tensor elements through the component,
  // scalar-only elements through their `value` fallback (componentValue
  // returns the fallback when the tensor is absent). Skipping the scalar-only
  // elements (Codex R1 P2) would under-report the maximum actually displayed.
  let peak = -Infinity;
  for (const el of input.elements) {
    const v = componentValue(el.stressTensor, fieldComponent, el.value ?? Number.NaN);
    if (Number.isFinite(v) && v > peak) peak = v;
  }
  if (!Number.isFinite(peak)) {
    return { label: input.fieldLabel, value: input.valueMax };
  }
  return { label: FIELD_COMPONENT_LABELS[fieldComponent], value: peak };
}
