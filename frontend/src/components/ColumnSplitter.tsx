// FM-04a Phase 44 A — column splitter (draggable + keyboard separator).
//
// A vertical resize handle sitting in a grid grip-track between two shell
// columns. Drag it to resize the controlled rail; the live drag updates a CSS
// custom property on the shell node imperatively (via the hook's onPreview) so
// there is NO React re-render per frame; release commits + persists. Also
// keyboard-operable per the W3C window-splitter pattern (Arrow / Home / End).
// ARIA: role="separator", aria-orientation, aria-valuemin/max/now.
//
// Drag tracking uses WINDOW-level pointermove/pointerup listeners attached for
// the drag's duration (Codex R1 P3): the pointer is followed even when it
// leaves the 8px grip, and a release ANYWHERE commits — independent of
// pointer-capture support. Listeners are torn down on release and on unmount.
//
// All event reads (clientX, refs, data-dragging) happen inside handlers, never
// in render (react-hooks/purity-safe). This file exports ONLY the component
// (react-refresh/only-export-components).
//
// Tier 1 engineering candidate; not signed validation; not benchmark agreement.

import { useEffect, useRef } from 'react';
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
  onPreview,
  onCommit,
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
      aria-valuenow={Math.round(valueNow)}
      tabIndex={0}
      data-testid={`col-splitter-${track}`}
      className="col-splitter"
      onPointerDown={handlePointerDown}
      onKeyDown={handleKeyDown}
    />
  );
}
