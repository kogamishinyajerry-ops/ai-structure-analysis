// FM-04a Phase 44 A/B — column splitter (draggable + collapsible separator).
//
// A vertical resize handle in a grid grip-track between two shell columns.
//   44 A: drag to resize (WINDOW-level pointermove/pointerup listeners attached
//         for the drag's duration, so the pointer is followed off the 8px grip
//         and a release ANYWHERE commits — Codex R1 P3), plus W3C window-splitter
//         keyboard (Arrow/Home/End).
//   44 B: double-click OR Enter/Space toggles the adjacent rail collapsed; when
//         collapsed the splitter renders an expand chevron and aria-valuenow=0.
//
// All event reads (clientX, refs, data-dragging) happen inside handlers, never in
// render. data-collapsed derives from the pure `collapsed` PROP (no ref read).
// onToggleCollapse + collapsed are OPTIONAL so a legacy (44 A) caller still works
// (the handlers no-op via ?.). This file exports ONLY the component.
//
// Tier 1 engineering candidate; not signed validation; not benchmark agreement.

import { useEffect, useRef } from 'react';
import { ChevronLeft, ChevronRight } from 'lucide-react';
import type {
  KeyboardEvent as ReactKeyboardEvent,
  PointerEvent as ReactPointerEvent,
} from 'react';
import {
  NUDGE_PX,
  NUDGE_PX_SHIFT,
  type ColumnSplitterModel,
} from '../state/useColumnLayout';

export function ColumnSplitter({
  track,
  valueNow,
  valueMin,
  valueMax,
  label,
  collapsed,
  onPreview,
  onCommit,
  onToggleCollapse,
}: ColumnSplitterModel) {
  const draggingRef = useRef(false);
  const startXRef = useRef(0);
  const startWRef = useRef(0);
  const lastWRef = useRef(valueNow);
  // Holds the teardown for an in-flight drag so it can be removed on unmount.
  const cleanupRef = useRef<(() => void) | null>(null);

  // Remove any stray window listeners if the splitter unmounts mid-drag.
  useEffect(() => () => cleanupRef.current?.(), []);

  const handlePointerDown = (event: ReactPointerEvent<HTMLDivElement>): void => {
    if (collapsed) return; // a collapsed rail is not drag-resizable; use the chevron
    event.preventDefault();
    cleanupRef.current?.(); // defensive: clear any prior unfinished drag
    draggingRef.current = true;
    startXRef.current = event.clientX;
    startWRef.current = valueNow;
    lastWRef.current = valueNow;
    const el = event.currentTarget;
    el.setAttribute('data-dragging', 'true');

    // Both splitters sit on the RIGHT edge of their controlled rail, so a
    // rightward drag (positive delta) widens the rail in both cases.
    const onMove = (e: PointerEvent): void => {
      if (!draggingRef.current) return;
      const next = startWRef.current + (e.clientX - startXRef.current);
      lastWRef.current = next;
      onPreview(track, next);
    };
    const teardown = (): void => {
      window.removeEventListener('pointermove', onMove);
      window.removeEventListener('pointerup', onUp);
      el.removeAttribute('data-dragging');
      draggingRef.current = false;
      cleanupRef.current = null;
    };
    const onUp = (): void => {
      if (!draggingRef.current) return;
      teardown();
      onCommit(track, lastWRef.current);
    };
    window.addEventListener('pointermove', onMove);
    window.addEventListener('pointerup', onUp);
    cleanupRef.current = teardown;
  };

  const handleKeyDown = (event: ReactKeyboardEvent<HTMLDivElement>): void => {
    // Enter / Space toggles collapse in any state (so a collapsed rail is
    // keyboard-expandable).
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault();
      onToggleCollapse?.(track);
      return;
    }
    // Resize keys are INERT while collapsed — committing here would overwrite
    // the hidden rail's saved width with valueNow(=0)±step (Codex R0 P2).
    if (collapsed) return;
    const step = event.shiftKey ? NUDGE_PX_SHIFT : NUDGE_PX;
    switch (event.key) {
      case 'ArrowLeft':
        event.preventDefault();
        onCommit(track, valueNow - step);
        break;
      case 'ArrowRight':
        event.preventDefault();
        onCommit(track, valueNow + step);
        break;
      case 'Home':
        event.preventDefault();
        onCommit(track, valueMin);
        break;
      case 'End':
        event.preventDefault();
        onCommit(track, valueMax);
        break;
      default:
        break;
    }
  };

  return (
    <div
      role="separator"
      aria-orientation="vertical"
      aria-label={label}
      aria-valuemin={valueMin}
      aria-valuemax={valueMax}
      aria-valuenow={collapsed ? 0 : Math.round(valueNow)}
      tabIndex={0}
      data-testid={`col-splitter-${track}`}
      data-collapsed={collapsed ? '' : undefined}
      className="col-splitter"
      onPointerDown={handlePointerDown}
      onKeyDown={handleKeyDown}
      onDoubleClick={() => onToggleCollapse?.(track)}
    >
      {collapsed && (
        <button
          type="button"
          className="col-splitter-chevron"
          data-testid={`col-splitter-expand-${track}`}
          aria-label={`Expand ${label.replace(/^Resize /, '')}`}
          tabIndex={-1}
          onClick={(e) => {
            e.stopPropagation();
            onToggleCollapse?.(track);
          }}
        >
          {track === 'left' ? (
            <ChevronRight size={14} aria-hidden="true" />
          ) : (
            <ChevronLeft size={14} aria-hidden="true" />
          )}
        </button>
      )}
    </div>
  );
}
