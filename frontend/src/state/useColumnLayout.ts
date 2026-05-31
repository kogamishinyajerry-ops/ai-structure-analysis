// FM-04a Phase 44 A/B — resizable + collapsible shell column layout.
//
// 44 A delivered drag-resizable rails; 44 B adds collapse/expand AND folds in the
// two deferred Codex R2 P2 fixes:
//   P2b — NON-DESTRUCTIVE resize: a SINGLE persisted `saved` layout is the source
//         of truth; the DISPLAYED widths are PURE-DERIVED each render
//         (projectLayout) and never stored. Resize only updates a viewport-width
//         render input — it never rewrites `saved` — so narrowing then widening
//         restores the user's saved desktop layout by construction.
//   P2a — CHAT-AWARE stage reserve: the center stage internally splits '1fr 340px'
//         when Copilot chat is open, so the hook takes a `stageReservePx` option
//         (App passes showChat ? 340 : 0) added to MIN_STAGE_PX in the clamp.
//
// Collapse state lives in a SEPARATE localStorage key (fm04a.ui.columns.collapse.v1)
// so the persisted {leftW,caseW} blob + validateColumnLayout + clampLayoutToViewport
// stay byte-identical (the 44 A shape tests pin them).
//
// The trailing 1fr stage track (WebGL viewport) is never sized here — it absorbs
// the slack, so the viewport contract (flex:1 1 auto / minHeight:0) is untouched.
//
// All non-hook exports are pure and unit-testable. The SSR-safe storage adapters
// mirror uiMode.ts createUiModeStorage.
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

/** Per-rail collapsed flags — stored in a SEPARATE LS key so ColumnLayout's
 * persisted {leftW,caseW} shape (and its pinned tests) stay untouched. */
export interface CollapseState {
  left: boolean;
  case: boolean;
}

/** LocalStorage keys — siblings of fm04a.ui.mode.v1. */
export const COLUMN_LAYOUT_LS_KEY = 'fm04a.ui.columns.v1';
export const COLLAPSE_LS_KEY = 'fm04a.ui.columns.collapse.v1';

export const DEFAULT_COLUMN_LAYOUT: ColumnLayout = { leftW: 210, caseW: 300 };
const DEFAULT_COLLAPSE: CollapseState = { left: false, case: false };

// Per-track clamp bounds (px) + splitter grip width + keyboard nudges + the
// collapsed-rail strip width.
export const LEFT_MIN = 160;
export const LEFT_MAX = 360;
export const CASE_MIN = 220;
export const CASE_MAX = 480;
export const GRIP_PX = 8;
export const NUDGE_PX = 8;
export const NUDGE_PX_SHIFT = 32;
export const COLLAPSED_STRIP_PX = 14;

/** Minimum width the center stage (main viewport + the optional 340px chat
 * column when open — passed in as reservePx) must retain. Rails are clamped so
 * their combined width never starves it (Codex R0 P2 / R2 P2a). */
export const MIN_STAGE_PX = 520;

/** The responsive breakpoint below which index.css overrides the grid template
 * (`!important` single/2-column). At/below it the rails are CSS-controlled, so
 * their stored DESKTOP widths must never be clamped/rewritten (Codex R1 P2). */
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

/** Largest COMBINED rail width that still leaves MIN_STAGE_PX + reservePx (+ the
 * two grips) for the stage; never below both rails' minima. At/below the
 * responsive breakpoint there is NO clamp — the rails are CSS-overridden there
 * and the stored desktop widths must be preserved (Codex R1 P2; reservePx is
 * intentionally ignored on that branch). */
export function railBudget(viewportW: number, reservePx = 0): number {
  if (!Number.isFinite(viewportW) || viewportW <= RESIZE_BREAKPOINT_PX) {
    return LEFT_MAX + CASE_MAX;
  }
  return Math.max(LEFT_MIN + CASE_MIN, viewportW - MIN_STAGE_PX - reservePx - 2 * GRIP_PX);
}

/** Max width for ONE track given the other track's width + the viewport budget. */
function capForTrack(
  track: ColumnTrack,
  otherW: number,
  viewportW: number,
  reservePx = 0,
): number {
  const floor = track === 'left' ? LEFT_MIN : CASE_MIN;
  return Math.max(floor, railBudget(viewportW, reservePx) - otherW);
}

/** Clamp a whole layout to the viewport budget, shrinking the case rail first
 * (it has the larger default) then the left rail, each above its own minimum. */
export function clampLayoutToViewport(
  layout: ColumnLayout,
  viewportW: number,
  reservePx = 0,
): ColumnLayout {
  let leftW = clampW('left', layout.leftW);
  let caseW = clampW('case', layout.caseW);
  let over = leftW + caseW - railBudget(viewportW, reservePx);
  if (over <= 0) return { leftW, caseW };
  const caseShrink = Math.min(over, caseW - CASE_MIN);
  caseW -= caseShrink;
  over -= caseShrink;
  if (over > 0) leftW -= Math.min(over, leftW - LEFT_MIN);
  return { leftW, caseW };
}

/** Project the persisted `saved` layout to the DISPLAYED grid-track widths given
 * the current collapse flags, viewport, and stage reserve. PURE — the single
 * derivation path (never stored). A collapsed rail renders as a fixed
 * COLLAPSED_STRIP_PX strip and consumes no shared budget, so the live rail (and
 * the stage) gain its space. */
export function projectLayout(
  saved: ColumnLayout,
  collapse: CollapseState,
  viewportW: number,
  reservePx = 0,
): ColumnLayout {
  if (!collapse.left && !collapse.case) {
    return clampLayoutToViewport(saved, viewportW, reservePx);
  }
  const budget = railBudget(viewportW, reservePx);
  let leftW = collapse.left ? 0 : clampW('left', saved.leftW);
  let caseW = collapse.case ? 0 : clampW('case', saved.caseW);
  let over = leftW + caseW - budget;
  if (over > 0 && !collapse.case) {
    const caseShrink = Math.min(over, caseW - CASE_MIN);
    caseW -= caseShrink;
    over -= caseShrink;
  }
  if (over > 0 && !collapse.left) {
    leftW -= Math.min(over, leftW - LEFT_MIN);
  }
  return {
    leftW: collapse.left ? COLLAPSED_STRIP_PX : leftW,
    caseW: collapse.case ? COLLAPSED_STRIP_PX : caseW,
  };
}

/** Coerce arbitrary parsed JSON into a valid ColumnLayout — clamps widths and
 * falls back to the default for any missing / malformed field. */
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

/** Coerce parsed JSON into a valid CollapseState (missing/non-boolean → false). */
export function validateCollapseState(raw: unknown): CollapseState {
  if (typeof raw !== 'object' || raw === null) return { ...DEFAULT_COLLAPSE };
  const r = raw as Record<string, unknown>;
  return {
    left: typeof r.left === 'boolean' ? r.left : false,
    case: typeof r.case === 'boolean' ? r.case : false,
  };
}

export interface ColumnLayoutStorage {
  load: () => ColumnLayout;
  save: (layout: ColumnLayout) => void;
}

export interface CollapseStorage {
  load: () => CollapseState;
  save: (collapse: CollapseState) => void;
}

/** SSR-safe localStorage adapter for the {leftW,caseW} layout. */
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

/** SSR-safe localStorage adapter for the collapse flags (separate key; an
 * absent key → both rails uncollapsed, so a 44 A user upgrades cleanly). */
export function createCollapseStorage(
  globalRef: typeof globalThis = globalThis,
): CollapseStorage {
  const ls = (globalRef as { localStorage?: Storage }).localStorage;
  if (!ls) {
    return {
      load: () => ({ ...DEFAULT_COLLAPSE }),
      save: () => {
        /* no-op (SSR / storage unavailable) */
      },
    };
  }
  return {
    load: () => {
      try {
        const raw = ls.getItem(COLLAPSE_LS_KEY);
        if (raw === null) return { ...DEFAULT_COLLAPSE };
        return validateCollapseState(JSON.parse(raw));
      } catch {
        return { ...DEFAULT_COLLAPSE };
      }
    },
    save: (collapse) => {
      try {
        ls.setItem(COLLAPSE_LS_KEY, JSON.stringify(collapse));
      } catch {
        /* swallow quota / SecurityError */
      }
    },
  };
}

/** Props the hook hands to each <ColumnSplitter/>. Declared here so the hook is
 * the single source of truth for the splitter contract. collapsed +
 * onToggleCollapse are OPTIONAL so a legacy (44 A) caller still type-checks. */
export interface ColumnSplitterModel {
  track: ColumnTrack;
  valueNow: number;
  valueMin: number;
  valueMax: number;
  label: string;
  collapsed?: boolean;
  onPreview: (track: ColumnTrack, px: number) => void;
  onCommit: (track: ColumnTrack, px: number) => void;
  onToggleCollapse?: (track: ColumnTrack) => void;
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

export function useColumnLayout(opts?: { stageReservePx?: number }): UseColumnLayoutResult {
  const reserve = opts?.stageReservePx ?? 0;
  const storage = useMemo(() => createColumnLayoutStorage(), []);
  const collapseStorage = useMemo(() => createCollapseStorage(), []);
  // SINGLE persisted source of truth (raw user intent — NOT viewport-clamped).
  const [saved, setSaved] = useState<ColumnLayout>(() => storage.load());
  const [collapse, setCollapse] = useState<CollapseState>(() => collapseStorage.load());
  // Viewport-width render input — written ONLY in the resize listener (handler
  // scope). NOT a layout duplicate; resize never persists (P2b).
  const [vw, setVw] = useState<number>(() => viewportWidth());
  const shellRef = useRef<HTMLDivElement | null>(null);
  // Mirrors the DISPLAYED layout for the imperative preview path (handlers only).
  const layoutRef = useRef<ColumnLayout>(saved);
  // The in-flight drag width, or null when not dragging.
  const dragWidthRef = useRef<{ track: ColumnTrack; px: number } | null>(null);

  // The DISPLAYED widths — pure-derived, never stored.
  const displayed = useMemo(
    () => projectLayout(saved, collapse, vw, reserve),
    [saved, collapse, vw, reserve],
  );

  // Imperative drag PREVIEW — DOM custom-property only, no setState. Capped to
  // the viewport budget so it cannot overshoot the commit. data-anim is forced
  // off so a live drag is never animated.
  const onPreview = useCallback(
    (track: ColumnTrack, px: number): void => {
      const node = shellRef.current;
      if (!node) return;
      node.setAttribute('data-anim', '0');
      const other = track === 'left' ? layoutRef.current.caseW : layoutRef.current.leftW;
      const v = Math.min(clampW(track, px), capForTrack(track, other, viewportWidth(), reserve));
      dragWidthRef.current = { track, px: v };
      node.style.setProperty(varName(track), `${v}px`);
    },
    [reserve],
  );

  // COMMIT on pointer-up / keyboard — write the user's intent to `saved` and
  // persist. The viewport cap is applied at DISPLAY time (projectLayout), so
  // `saved` stays the honest intent.
  const onCommit = useCallback(
    (track: ColumnTrack, px: number): void => {
      dragWidthRef.current = null;
      setSaved((prev) => {
        const v = clampW(track, px);
        const next: ColumnLayout =
          track === 'left' ? { ...prev, leftW: v } : { ...prev, caseW: v };
        storage.save(next);
        return next;
      });
    },
    [storage],
  );

  // Toggle a rail collapsed; persist to the separate collapse key. data-anim is
  // turned ON so the grid-template change animates (drag/resize turn it back off).
  const onToggleCollapse = useCallback(
    (track: ColumnTrack): void => {
      shellRef.current?.setAttribute('data-anim', '1');
      setCollapse((prev) => {
        const next: CollapseState =
          track === 'left' ? { ...prev, left: !prev.left } : { ...prev, case: !prev.case };
        collapseStorage.save(next);
        return next;
      });
    },
    [collapseStorage],
  );

  // Re-assert an in-flight drag width after ANY unrelated re-render (solver log /
  // job-status polling) would otherwise reapply the stale railVars and fight the
  // pointer (Codex R0 P1). Also keeps layoutRef = DISPLAYED for the preview path.
  useLayoutEffect(() => {
    layoutRef.current = displayed;
    const node = shellRef.current;
    const drag = dragWidthRef.current;
    if (node && drag) node.style.setProperty(varName(drag.track), `${drag.px}px`);
  });

  // Resize → update the viewport-width render input ONLY (no persist → P2b). Also
  // clear data-anim so a window drag-resize is never animated.
  useEffect(() => {
    const onResize = (): void => {
      shellRef.current?.setAttribute('data-anim', '0');
      setVw(viewportWidth());
    };
    window.addEventListener('resize', onResize);
    return () => window.removeEventListener('resize', onResize);
  }, []);

  const railVars = {
    '--rail-w': `${displayed.leftW}px`,
    '--caserail-w': `${displayed.caseW}px`,
    '--grip': `${GRIP_PX}px`,
  } as CSSProperties;

  const splitterProps = {
    left: {
      track: 'left' as const,
      valueNow: collapse.left ? 0 : displayed.leftW,
      valueMin: LEFT_MIN,
      valueMax: LEFT_MAX,
      label: 'Resize project rail',
      collapsed: collapse.left,
      onPreview,
      onCommit,
      onToggleCollapse,
    },
    case: {
      track: 'case' as const,
      valueNow: collapse.case ? 0 : displayed.caseW,
      valueMin: CASE_MIN,
      valueMax: CASE_MAX,
      label: 'Resize case rail',
      collapsed: collapse.case,
      onPreview,
      onCommit,
      onToggleCollapse,
    },
  };

  return {
    shellRef,
    railVars,
    splitterProps,
    leftW: displayed.leftW,
    caseW: displayed.caseW,
  };
}
