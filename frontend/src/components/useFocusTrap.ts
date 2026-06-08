// FM-04a Phase 29 C — minimal focus-trap hook (WCAG 2.4.3).
//
// Both modal overlays in the project (OnboardingTour +
// AdvancedModePromo) declare role="dialog" but Tab/Shift-Tab
// previously escaped to the underlying page. Phase 28 UI audit
// flagged this as the single most concrete WCAG gap; Abaqus
// job-edit modals trap focus per the same standard.
//
// Scope (intentionally narrow):
//   * Cycle Tab / Shift-Tab among the dialog's tabbable elements
//     (anything matching the standard "naturally-tabbable" CSS
//     selectors with tabIndex >= 0 and not disabled).
//   * Initial focus = first tabbable element on mount (D:-2 guard).
//   * Restore focus to the previously-focused element on unmount.
//   * Pause when `active=false` (lets the parent disable the trap
//     without unmounting the component).
//
// Not in scope:
//   * Inert-everything-else outside the dialog. JSDOM/browsers
//     don't honor `inert` attribute uniformly; the trap-cycle on
//     Tab is sufficient for the WCAG 2.4.3 minimum.
//   * Focus management on async DOM mutations inside the dialog
//     (re-snapshot on demand instead).
//
// Anti-gaming guards:
//   D:-2 — initial focus is FIRST-tabbable. Pinned by test.
//   E:-1 — keydown handler only intercepts Tab keys; does NOT
//          consume other keys (Esc / Enter etc. pass through).
//
// Tier 1 / Tier 2 engineering candidate; not signed validation;
// not benchmark agreement.

import { useEffect, useRef, type RefObject } from 'react';

const FOCUSABLE_SELECTOR = [
  'a[href]',
  'button:not([disabled])',
  'textarea:not([disabled])',
  'input:not([disabled])',
  'select:not([disabled])',
  '[tabindex]:not([tabindex="-1"])',
].join(',');

function getTabbables(container: HTMLElement): HTMLElement[] {
  const nodes = Array.from(
    container.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTOR),
  );
  return nodes.filter((el) => {
    if (el.hasAttribute('disabled')) return false;
    if (el.getAttribute('aria-hidden') === 'true') return false;
    // hidden via style/attribute
    if (
      el.offsetWidth === 0 &&
      el.offsetHeight === 0 &&
      !(el as HTMLInputElement).type?.includes('hidden')
    ) {
      // In JSDOM offsetWidth/Height are often 0 even for visible
      // elements; do NOT filter on that alone. Only filter when the
      // element is also `hidden`.
      if (el.hidden) return false;
    }
    return true;
  });
}

export interface UseFocusTrapOptions {
  /** Ref to the dialog container. Required. */
  // React 19 / TS6: useRef<T>(null) yields RefObject<T | null>, so accept the
  // nullable ref the callers (AdvancedModePromo / OnboardingTour / ShortcutsOverlay)
  // pass; the effect already guards `containerRef.current` before use.
  containerRef: RefObject<HTMLElement | null>;
  /** When false, the trap is disabled (no key handler, no initial
   * focus side effect). Useful when the parent toggles visibility
   * via conditional render — but if you ARE conditionally rendering,
   * the unmount also tears down the trap so this is mostly for
   * single-mount overlays. */
  active: boolean;
  /** When true, do NOT auto-focus the first tabbable on mount.
   * Useful for read-only/status dialogs. Default false. */
  skipInitialFocus?: boolean;
}

/** Trap Tab / Shift-Tab focus inside containerRef while active.
 * Restores prior focus on cleanup. */
export function useFocusTrap({
  containerRef,
  active,
  skipInitialFocus = false,
}: UseFocusTrapOptions): void {
  // Stash the focused element BEFORE the dialog mounts so we can
  // restore it on cleanup.
  const priorFocusRef = useRef<HTMLElement | null>(null);

  useEffect(() => {
    if (!active) return;
    const container = containerRef.current;
    if (!container) return;

    // Capture prior focus.
    priorFocusRef.current =
      document.activeElement instanceof HTMLElement
        ? document.activeElement
        : null;

    // D:-2 — initial focus on first tabbable.
    if (!skipInitialFocus) {
      const tabbables = getTabbables(container);
      if (tabbables.length > 0) tabbables[0].focus();
      else container.focus(); // fallback to container if no tabbable
    }

    function handleKeyDown(e: KeyboardEvent) {
      if (e.key !== 'Tab') return; // E:-1 — Tab only
      if (!container) return;
      const tabbables = getTabbables(container);
      if (tabbables.length === 0) {
        e.preventDefault();
        return;
      }
      const first = tabbables[0];
      const last = tabbables[tabbables.length - 1];
      const activeEl = document.activeElement;
      if (e.shiftKey) {
        // Shift-Tab cycling: if focus is on the first (or outside),
        // wrap to the last.
        if (activeEl === first || !container.contains(activeEl)) {
          e.preventDefault();
          last.focus();
        }
      } else {
        // Tab cycling: if focus is on the last (or outside), wrap
        // to the first.
        if (activeEl === last || !container.contains(activeEl)) {
          e.preventDefault();
          first.focus();
        }
      }
    }

    document.addEventListener('keydown', handleKeyDown);
    return () => {
      document.removeEventListener('keydown', handleKeyDown);
      // Restore prior focus on cleanup.
      const prior = priorFocusRef.current;
      if (prior && typeof prior.focus === 'function') {
        try {
          prior.focus();
        } catch {
          /* swallow — JSDOM may have removed the node */
        }
      }
    };
  }, [active, containerRef, skipInitialFocus]);
}
