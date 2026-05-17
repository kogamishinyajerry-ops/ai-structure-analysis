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
export const POLISH_CLASS_GRADIENT_SLIDER = 'fm04a-gradient-slider';
export const POLISH_CLASS_SECTION_CUT_READOUT = 'fm04a-section-cut-readout';

const POLISH_CSS = `
@keyframes fm04a-probe-row-fade-in {
  from { opacity: 0; transform: translateY(-6px); }
  to   { opacity: 1; transform: translateY(0); }
}

.${POLISH_CLASS_PROBE_ROW_MOUNT} {
  animation: fm04a-probe-row-fade-in 200ms ease-out;
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
  .${POLISH_CLASS_PROBE_ROW_MOUNT} {
    animation: none;
  }
}
`;

/** The raw CSS, exported for tests that want to assert keyword
 * presence without parsing the DOM. */
export const POLISH_CSS_TEXT = POLISH_CSS;
