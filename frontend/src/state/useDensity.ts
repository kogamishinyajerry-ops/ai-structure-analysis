// FM-04a Phase 45 A — UI density (comfortable | compact) state hook.
//
// The 3rd Dim-3 "90-anchor" layout system, after 44A (drag-resizable rails) and
// 44B (collapsible rails). It toggles a `data-density` attribute on
// document.documentElement; index.css redefines the design-token VALUES under
// :root[data-density="compact"] so every var(--sp-*)/var(--fs-*)/var(--r-*)
// consumer rescales with zero per-component edits.
//
// HONEST SCOPE (Tier 1): this is TOKEN-SURFACE density, not a full-UI shrink —
// the ~91% of spacing that is hardcoded inline px (Topbar, Sidebar, advisor
// cards) stays at comfortable until a later slice migrates it to tokens. Compact
// visibly tightens the type scale, card/panel radius, and token-spacing rhythm.
//
// Mirrors useColumnLayout.ts discipline: an SSR-safe localStorage adapter, a
// strict validator that coerces malformed input to the default, a LAZY useState
// initializer (deferred LS read → lint-clean for react-hooks/purity), and a
// document-root setAttribute in an EFFECT (no setState-in-effect, no render-scope
// impurity). Default 'comfortable' → an existing user upgrades to a byte-identical
// UI until they opt into compact. Non-component exports live in this .ts file
// (NOT .tsx) so react-refresh/only-export-components stays satisfied.
//
// Tier 1 engineering candidate; not signed validation; not benchmark agreement.

import { useCallback, useLayoutEffect, useMemo, useState } from 'react';

export type Density = 'comfortable' | 'compact';

export const DENSITY_LS_KEY = 'fm04a.ui.density.v1';
export const DEFAULT_DENSITY: Density = 'comfortable';
/** Cycle order. A 3rd tier (e.g. 'cozy') is a 1-line array edit — seat reserved,
 * not built (mirrors ADR-026 Layer-3 discipline). */
export const DENSITY_ORDER: Density[] = ['comfortable', 'compact'];

/** Coerce arbitrary parsed JSON into a valid Density (anything else → default). */
export function validateDensity(raw: unknown): Density {
  return raw === 'comfortable' || raw === 'compact' ? raw : DEFAULT_DENSITY;
}

export interface DensityStorage {
  load: () => Density;
  save: (density: Density) => void;
}

/** SSR-safe localStorage adapter for the density preference. */
export function createDensityStorage(
  globalRef: typeof globalThis = globalThis,
): DensityStorage {
  const ls = (globalRef as { localStorage?: Storage }).localStorage;
  if (!ls) {
    return {
      load: () => DEFAULT_DENSITY,
      save: () => {
        /* no-op (SSR / storage unavailable) */
      },
    };
  }
  return {
    load: () => {
      try {
        const raw = ls.getItem(DENSITY_LS_KEY);
        if (raw === null) return DEFAULT_DENSITY;
        return validateDensity(JSON.parse(raw));
      } catch {
        return DEFAULT_DENSITY;
      }
    },
    save: (density) => {
      try {
        ls.setItem(DENSITY_LS_KEY, JSON.stringify(density));
      } catch {
        /* swallow quota / SecurityError */
      }
    },
  };
}

export interface UseDensityResult {
  density: Density;
  setDensity: (density: Density) => void;
  cycleDensity: () => void;
}

export function useDensity(): UseDensityResult {
  const storage = useMemo(() => createDensityStorage(), []);
  const [density, setDensityState] = useState<Density>(() => storage.load());

  const setDensity = useCallback(
    (next: Density): void => {
      setDensityState(next);
      storage.save(next);
    },
    [storage],
  );

  const cycleDensity = useCallback((): void => {
    const next =
      DENSITY_ORDER[(DENSITY_ORDER.indexOf(density) + 1) % DENSITY_ORDER.length];
    setDensity(next);
  }, [density, setDensity]);

  // Apply to the document root so the compact token block (index.css) takes
  // effect document-wide. useLayoutEffect (NOT useEffect) runs synchronously
  // after the render commit but BEFORE the browser paints, so a persisted
  // 'compact' preference is honored on the FIRST paint — no comfortable→compact
  // flash/reflow on reload (Codex 45A R0 P2). Topbar (this hook's caller) is in
  // App's initial tree, so this fires before the first meaningful paint. Layout
  // -effect scope → no render-scope impurity, no setState-in-effect; the
  // attribute persists across Topbar re-renders.
  useLayoutEffect(() => {
    document.documentElement.setAttribute('data-density', density);
  }, [density]);

  return { density, setDensity, cycleDensity };
}
