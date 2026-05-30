// FM-04a Phase 44 A — resizable shell column layout (pure model + hook).
//
// Phase 43's industrial-UI audit named drag-resizable panel docks the single
// highest-leverage Dim-3 lift: the shell was a hard-pinned
// `gridTemplateColumns: '210px 300px 1fr'`. This module owns the resize state
// for the two LEFT rails (project rail + case rail). The trailing 1fr stage
// track (which holds the WebGL viewport + the optional 340px chat column) is
// NEVER sized here — it absorbs the slack, so the viewport contract
// (flex:1 1 auto / minHeight:0) is untouched.
//
// Two-tier update model (perf): a live DRAG mutates only the CSS custom
// property on the shell node imperatively (no React re-render per frame, so the
// WebGL canvas box only changes by the resize itself); the COMMIT on pointer-up
// / keyboard writes React state + persists.
//
// Codex R0 hardening:
//   P1 — a useLayoutEffect re-asserts the in-flight drag width after ANY
//        unrelated re-render (solver-log / job-status polling) which would
//        otherwise reapply the stale committed railVars and fight the pointer.
//   P2 — rail widths are clamped against the remaining stage width
//        (railBudget / clampLayoutToViewport) on load, commit, and resize so a
//        layout persisted on a larger monitor cannot starve the center stage.
//
// Collapse-to-strip is deferred to Phase 44 B (its rail-clip + chevron UX has a
// visual/layout surface jsdom cannot verify; shipping the fully-unit-testable
// resize first is the lower-risk win — same scope discipline as useAppUiMode).
//
// All non-hook exports are pure and unit-testable in isolation. The SSR-safe
// storage adapter mirrors uiMode.ts createUiModeStorage.
//
// Tier 1 engineering candidate; not signed validation; not benchmark agreement.

import { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react';
import type { CSSProperties, RefObject } from 'react';

export type ColumnTrack = 'left' | 'case';

export interface ColumnLayout {
  /** Project-rail width in px (the leading grid track). */
  leftW: number;
  /** Case-rail width in px (the third grid track). */
  caseW: number;
}

/** LocalStorage key — sibling of fm04a.ui.mode.v1. */
export const COLUMN_LAYOUT_LS_KEY = 'fm04a.ui.columns.v1';

export const DEFAULT_COLUMN_LAYOUT: ColumnLayout = { leftW: 210, caseW: 300 };

// Per-track clamp bounds (px) + the splitter grip-track width + keyboard nudges.
export const LEFT_MIN = 160;
export const LEFT_MAX = 360;
export const CASE_MIN = 220;
export const CASE_MAX = 480;
export const GRIP_PX = 8;
export const NUDGE_PX = 8;
export const NUDGE_PX_SHIFT = 32;

/** Minimum width the center stage (main viewport + the optional 340px chat
 * column) must retain. The rails are clamped so their combined width never
 * starves it — even for widths persisted on a larger monitor (Codex R0 P2).
 * With chat OPEN on a narrow screen the viewport is still tight, but never the
 * ~84px collapse the static maxima alone allowed. */
export const MIN_STAGE_PX = 520;

/** The responsive breakpoint below which index.css overrides the grid template
 * (`!important` single/2-column). At or below it the rails are CSS-controlled,
 * so their stored DESKTOP widths must never be clamped or rewritten (Codex R1
 * P2) — otherwise widening back to desktop loses the saved layout. */
export const RESIZE_BREAKPOINT_PX = 1024;

/** Clamp a proposed width to the track's [min,max]; non-finite → the default. */
export function clampW(track: ColumnTrack, px: number): number {
  const min = track === 'left' ? LEFT_MIN : CASE_MIN;
  const max = track === 'left' ? LEFT_MAX : CASE_MAX;
  if (!Number.isFinite(px)) {
    return track === 'left'
      ? DEFAULT_COLUMN_LAYOUT.leftW
      : DEFAULT_COLUMN_LAYOUT.caseW;
  }
  return Math.max(min, Math.min(max, px));
}

/** Current viewport width — handler/effect-only (reads window); generous
 * fallback in SSR / non-DOM so it never over-clamps. */
function viewportWidth(): number {
  if (
    typeof window !== 'undefined' &&
    Number.isFinite(window.innerWidth) &&
    window.innerWidth > 0
  ) {
    return window.innerWidth;
  }
  return 1920;
}

/** Largest COMBINED rail width that still leaves MIN_STAGE_PX (+ the two grips)
 * for the stage at the given viewport width; never below both rails' minima.
 * At/below the responsive breakpoint there is NO clamp — the rails are
 * CSS-overridden there and the stored desktop widths must be preserved
 * (Codex R1 P2). */
export function railBudget(viewportW: number): number {
  if (!Number.isFinite(viewportW) || viewportW <= RESIZE_BREAKPOINT_PX) {
    return LEFT_MAX + CASE_MAX;
  }
  return Math.max(LEFT_MIN + CASE_MIN, viewportW - MIN_STAGE_PX - 2 * GRIP_PX);
}

/** Max width for ONE track given the other track's width + the viewport budget. */
function capForTrack(track: ColumnTrack, otherW: number, viewportW: number): number {
  const floor = track === 'left' ? LEFT_MIN : CASE_MIN;
  return Math.max(floor, railBudget(viewportW) - otherW);
}

/** Clamp a whole layout to the viewport budget, shrinking the case rail first
 * (it has the larger default) then the left rail, each above its own minimum.
 * Used on load + resize so widths that fit a larger window cannot starve the
 * stage. */
export function clampLayoutToViewport(
  layout: ColumnLayout,
  viewportW: number,
): ColumnLayout {
  let leftW = clampW('left', layout.leftW);
  let caseW = clampW('case', layout.caseW);
  let over = leftW + caseW - railBudget(viewportW);
  if (over <= 0) return { leftW, caseW };
  const caseShrink = Math.min(over, caseW - CASE_MIN);
  caseW -= caseShrink;
  over -= caseShrink;
  if (over > 0) leftW -= Math.min(over, leftW - LEFT_MIN);
  return { leftW, caseW };
}

/** Coerce arbitrary parsed JSON into a valid ColumnLayout — clamps widths and
 * falls back to the default for any missing / malformed field (covers
 * corrupted storage). */
export function validateColumnLayout(raw: unknown): ColumnLayout {
  if (typeof raw !== 'object' || raw === null) {
    return { ...DEFAULT_COLUMN_LAYOUT };
  }
  const r = raw as Record<string, unknown>;
  const leftW =
    typeof r.leftW === 'number' && Number.isFinite(r.leftW)
      ? clampW('left', r.leftW)
      : DEFAULT_COLUMN_LAYOUT.leftW;
  const caseW =
    typeof r.caseW === 'number' && Number.isFinite(r.caseW)
      ? clampW('case', r.caseW)
      : DEFAULT_COLUMN_LAYOUT.caseW;
  return { leftW, caseW };
}

export interface ColumnLayoutStorage {
  load: () => ColumnLayout;
  save: (layout: ColumnLayout) => void;
}

/** SSR-safe localStorage adapter (mirrors uiMode.createUiModeStorage). */
export function createColumnLayoutStorage(
  globalRef: typeof globalThis = globalThis,
): ColumnLayoutStorage {
  const ls = (globalRef as { localStorage?: Storage }).localStorage;
  if (!ls) {
    return {
      load: () => ({ ...DEFAULT_COLUMN_LAYOUT }),
      save: () => {
        /* no-op (SSR / storage unavailable) */
      },
    };
  }
  return {
    load: () => {
      try {
        const raw = ls.getItem(COLUMN_LAYOUT_LS_KEY);
        if (raw === null) return { ...DEFAULT_COLUMN_LAYOUT };
        return validateColumnLayout(JSON.parse(raw));
      } catch {
        return { ...DEFAULT_COLUMN_LAYOUT };
      }
    },
    save: (layout) => {
      try {
        ls.setItem(COLUMN_LAYOUT_LS_KEY, JSON.stringify(layout));
      } catch {
        /* swallow quota / SecurityError */
      }
    },
  };
}

/** Props the hook hands to each <ColumnSplitter/>. Declared here so the hook is
 * the single source of truth for the splitter contract. */
export interface ColumnSplitterModel {
  track: ColumnTrack;
  valueNow: number;
  valueMin: number;
  valueMax: number;
  label: string;
  onPreview: (track: ColumnTrack, px: number) => void;
  onCommit: (track: ColumnTrack, px: number) => void;
}

export interface UseColumnLayoutResult {
  shellRef: RefObject<HTMLDivElement | null>;
  railVars: CSSProperties;
  splitterProps: { left: ColumnSplitterModel; case: ColumnSplitterModel };
  leftW: number;
  caseW: number;
}

const varName = (track: ColumnTrack): string =>
  track === 'left' ? '--rail-w' : '--caserail-w';

export function useColumnLayout(): UseColumnLayoutResult {
  const storage = useMemo(() => createColumnLayoutStorage(), []);
  const [layout, setLayout] = useState<ColumnLayout>(() =>
    clampLayoutToViewport(storage.load(), viewportWidth()),
  );
  const shellRef = useRef<HTMLDivElement | null>(null);
  // Mirrors `layout` for the imperative preview path (read in handlers only).
  const layoutRef = useRef(layout);
  // The in-flight drag width, or null when not dragging.
  const dragWidthRef = useRef<{ track: ColumnTrack; px: number } | null>(null);

  // Imperative drag PREVIEW — DOM custom-property only, no setState (so a drag
  // never re-renders the WebGL stage). Capped against the viewport budget so it
  // cannot visually overshoot what commit will allow. Reads happen in the
  // handler, never in render.
  const onPreview = useCallback((track: ColumnTrack, px: number): void => {
    const node = shellRef.current;
    if (!node) return;
    const other = track === 'left' ? layoutRef.current.caseW : layoutRef.current.leftW;
    const v = Math.min(clampW(track, px), capForTrack(track, other, viewportWidth()));
    dragWidthRef.current = { track, px: v };
    node.style.setProperty(varName(track), `${v}px`);
  }, []);

  // COMMIT on pointer-up / keyboard — clamp the active rail against its bounds
  // AND the remaining stage budget, write state, persist.
  const onCommit = useCallback(
    (track: ColumnTrack, px: number): void => {
      dragWidthRef.current = null;
      setLayout((prev) => {
        const other = track === 'left' ? prev.caseW : prev.leftW;
        const v = Math.min(clampW(track, px), capForTrack(track, other, viewportWidth()));
        const next: ColumnLayout =
          track === 'left' ? { ...prev, leftW: v } : { ...prev, caseW: v };
        storage.save(next);
        return next;
      });
    },
    [storage],
  );

  // Re-assert an in-flight drag width after ANY unrelated re-render (solver log
  // / job-status polling, etc.) would otherwise reapply the stale committed
  // railVars and fight the pointer (Codex R0 P1). Also keeps layoutRef fresh for
  // the imperative preview path. Runs every render; DOM re-assert only — no
  // setState here.
  useLayoutEffect(() => {
    layoutRef.current = layout;
    const node = shellRef.current;
    const drag = dragWidthRef.current;
    if (node && drag) node.style.setProperty(varName(drag.track), `${drag.px}px`);
  });

  // Re-clamp on viewport shrink so a layout that fit a larger window cannot
  // starve the stage after a resize (Codex R0 P2). setState lives in the
  // listener callback, not the effect body.
  useEffect(() => {
    const onResize = (): void => {
      setLayout((prev) => {
        const next = clampLayoutToViewport(prev, viewportWidth());
        if (next.leftW === prev.leftW && next.caseW === prev.caseW) return prev;
        storage.save(next);
        return next;
      });
    };
    window.addEventListener('resize', onResize);
    return () => window.removeEventListener('resize', onResize);
  }, [storage]);

  const railVars = {
    '--rail-w': `${layout.leftW}px`,
    '--caserail-w': `${layout.caseW}px`,
    '--grip': `${GRIP_PX}px`,
  } as CSSProperties;

  const splitterProps = {
    left: {
      track: 'left' as const,
      valueNow: layout.leftW,
      valueMin: LEFT_MIN,
      valueMax: LEFT_MAX,
      label: 'Resize project rail',
      onPreview,
      onCommit,
    },
    case: {
      track: 'case' as const,
      valueNow: layout.caseW,
      valueMin: CASE_MIN,
      valueMax: CASE_MAX,
      label: 'Resize case rail',
      onPreview,
      onCommit,
    },
  };

  return {
    shellRef,
    railVars,
    splitterProps,
    leftW: layout.leftW,
    caseW: layout.caseW,
  };
}
