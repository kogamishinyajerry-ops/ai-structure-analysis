// FM-04a Phase 27 C — Apple-tier polish breadth pass · global style
// injection.
//
// Three affordances:
//   1. Probe-list row entrance fade-in (200ms ease-out + 6px lift).
//      Applied via .fm04a-probe-row-mount class on <tr>.
//      Exit animation is intentionally NOT shipped (would require
//      AnimatePresence-style state held outside the table); honest
//      scope reduction.
//   2. Threshold-filter slider gradient track (blue → green →
//      orange matching the legend gradient). Applied via the
//      .fm04a-gradient-slider class. Both -webkit- and -moz-
//      pseudo-elements styled.
//   3. Section-cut hover preview readout. The readout is React-
//      managed (isDragging state); the CSS here only positions
//      it absolutely.
//
// Anti-gaming guard B:-1 — `prefers-reduced-motion: reduce` honored.
// All animations become instant in reduce mode; the gradient track
// and the position readout are static visual affordances and stay
// visible (they communicate state, not motion).
//
// Tier 1 / Tier 2 engineering candidate; not signed validation;
// not benchmark agreement.

const STYLE_ID = 'fm04a-phase27c-polish-styles';

/** Inject the polish CSS once into <head>. Safe to call multiple
 * times — the style tag is deduplicated by ID. */
export function installPolishStyles(): void {
  if (typeof document === 'undefined') return; // SSR no-op
  if (document.getElementById(STYLE_ID)) return; // already installed
  const style = document.createElement('style');
  style.id = STYLE_ID;
  style.textContent = POLISH_CSS;
  document.head.appendChild(style);
}

/** Uninstall (for test teardown). */
export function uninstallPolishStyles(): void {
  if (typeof document === 'undefined') return;
  const existing = document.getElementById(STYLE_ID);
  if (existing) existing.remove();
}

/** Whether the polish styles are currently installed. Test helper. */
export function isPolishInstalled(): boolean {
  if (typeof document === 'undefined') return false;
  return document.getElementById(STYLE_ID) !== null;
}

/** Stable class names exported for the components that consume them
 * (no string-leak duplication between TS and CSS). */
export const POLISH_CLASS_PROBE_ROW_MOUNT = 'fm04a-probe-row-mount';
export const POLISH_CLASS_PROBE_ROW_UNMOUNT = 'fm04a-probe-row-unmount';
export const POLISH_CLASS_GRADIENT_SLIDER = 'fm04a-gradient-slider';
export const POLISH_CLASS_SECTION_CUT_READOUT = 'fm04a-section-cut-readout';
export const POLISH_CLASS_RESTORED_TOAST = 'fm04a-restored-toast';

const POLISH_CSS = `
@keyframes fm04a-probe-row-fade-in {
  from { opacity: 0; transform: translateY(-6px); }
  to   { opacity: 1; transform: translateY(0); }
}
@keyframes fm04a-probe-row-fade-out {
  from { opacity: 1; transform: translateY(0); }
  to   { opacity: 0; transform: translateY(-6px); }
}
@keyframes fm04a-restored-toast-fade-in {
  from { opacity: 0; transform: translateY(8px); }
  to   { opacity: 1; transform: translateY(0); }
}

.${POLISH_CLASS_PROBE_ROW_MOUNT} {
  animation: fm04a-probe-row-fade-in 200ms ease-out;
}

.${POLISH_CLASS_PROBE_ROW_UNMOUNT} {
  animation: fm04a-probe-row-fade-out 150ms ease-in forwards;
}

.${POLISH_CLASS_RESTORED_TOAST} {
  position: absolute;
  top: 14px;
  right: 14px;
  z-index: 20;
  padding: 6px 10px 6px 12px;
  background: rgba(2, 6, 23, 0.92);
  color: #93c5fd;
  border: 1px solid rgba(37, 99, 235, 0.45);
  border-radius: 6px;
  font-size: 0.72rem;
  font-family: inherit;
  display: flex;
  gap: 8px;
  align-items: center;
  animation: fm04a-restored-toast-fade-in 200ms ease-out;
}
.${POLISH_CLASS_RESTORED_TOAST} button {
  background: transparent;
  border: 1px solid rgba(148, 163, 184, 0.35);
  color: #cbd5e1;
  border-radius: 3px;
  padding: 1px 6px;
  font-size: 0.66rem;
  cursor: pointer;
}

/* Threshold-filter slider gradient track. Matches the legend
   gradient at the bottom-right of the viewport (#2563eb → #10b981
   → #f97316). */
.${POLISH_CLASS_GRADIENT_SLIDER}::-webkit-slider-runnable-track {
  height: 6px;
  background: linear-gradient(to right, #2563eb 0%, #10b981 50%, #f97316 100%);
  border-radius: 3px;
}
.${POLISH_CLASS_GRADIENT_SLIDER}::-moz-range-track {
  height: 6px;
  background: linear-gradient(to right, #2563eb 0%, #10b981 50%, #f97316 100%);
  border-radius: 3px;
}
.${POLISH_CLASS_GRADIENT_SLIDER} {
  -webkit-appearance: none;
  appearance: none;
  background: transparent;
}

/* Section-cut position hover preview. Positioned by the React
   component; this just styles the readout itself. */
.${POLISH_CLASS_SECTION_CUT_READOUT} {
  position: absolute;
  background: rgba(2, 6, 23, 0.92);
  color: #e2e8f0;
  border: 1px solid rgba(148, 163, 184, 0.4);
  border-radius: 4px;
  padding: 2px 8px;
  font-size: 0.66rem;
  font-family: ui-monospace, SFMono-Regular, "SF Mono", Menlo, monospace;
  pointer-events: none;
  white-space: nowrap;
  z-index: 10;
  transform: translate(-50%, -120%);
}

@media (prefers-reduced-motion: reduce) {
  .${POLISH_CLASS_PROBE_ROW_MOUNT},
  .${POLISH_CLASS_PROBE_ROW_UNMOUNT},
  .${POLISH_CLASS_RESTORED_TOAST} {
    animation: none;
  }
}
`;

/** The raw CSS, exported for tests that want to assert keyword
 * presence without parsing the DOM. */
export const POLISH_CSS_TEXT = POLISH_CSS;
