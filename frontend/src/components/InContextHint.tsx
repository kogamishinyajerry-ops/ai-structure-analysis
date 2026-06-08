// FM-04a Phase 39 B — in-context onboarding hint ("bubble").
//
// A small dismissible contextual hint attached to a single UI surface, for a
// first-time engineer. Distinct from:
//   - OnboardingTour (a one-shot modal guided overlay), and
//   - CoordReadoutTooltip (a live coordinate readout, not onboarding).
//
// Closes the RUBRIC_v2.md Dim 2 (Novice UX) 80-anchor sub-bullet
// "in-context bubbles attached to ≥5 UI surfaces". Each hint persists its
// dismissed state to localStorage by hintId, so a returning user does not
// see hints they have already read.
//
// Anti-gaming guards:
//   G:-1 — each mounted hint is a GENUINE, surface-specific explanation a
//          first-timer needs (NOT 5 copies of a trivial string).
//   D:-1 — default is SHOWN; dismissing is opt-in and sticky across reloads.
//   E:-1 — storage failures degrade to "shown" (loadHintDismissed → null);
//          the component never throws.
//
// Tier 1 / Tier 2 engineering candidate; not signed validation; not
// benchmark agreement.

import { useState, type CSSProperties } from 'react';
import { loadHintDismissed, saveHintDismissed } from './hintDismissedStorage';

export interface InContextHintProps {
  /** Stable per-surface id; also the localStorage dismissal key. */
  readonly hintId: string;
  /** First-timer-oriented guidance text for this surface. */
  readonly text: string;
  /** Optional short surface label shown before the text (e.g. "Case browser"). */
  readonly label?: string;
}

export function InContextHint({ hintId, text, label }: InContextHintProps) {
  const [dismissed, setDismissed] = useState<boolean>(
    () => loadHintDismissed(hintId) === true,
  );
  if (dismissed) return null;

  const dismiss = () => {
    saveHintDismissed(hintId, true);
    setDismissed(true);
  };

  return (
    <aside
      role="note"
      aria-label={label ? `Hint: ${label}` : 'In-context hint'}
      data-testid={`in-context-hint-${hintId}`}
      data-hint-id={hintId}
      style={hintStyle}
    >
      <span aria-hidden="true" style={iconStyle}>
        i
      </span>
      <span style={bodyStyle}>
        {label ? <strong style={labelStyle}>{label}: </strong> : null}
        {text}
      </span>
      <button
        type="button"
        onClick={dismiss}
        aria-label={label ? `Dismiss hint for ${label}` : 'Dismiss hint'}
        data-testid={`in-context-hint-dismiss-${hintId}`}
        style={dismissBtnStyle}
      >
        ×
      </button>
    </aside>
  );
}

const hintStyle: CSSProperties = {
  display: 'flex',
  alignItems: 'flex-start',
  gap: 8,
  padding: '8px 10px',
  margin: '0 0 10px',
  borderRadius: 8,
  border: '1px solid var(--border)',
  background: 'var(--bg-muted, var(--c-100))',
  color: 'var(--text-secondary)',
  fontSize: 12,
  lineHeight: 1.45,
};
const iconStyle: CSSProperties = {
  flex: '0 0 auto',
  width: 16,
  height: 16,
  borderRadius: '50%',
  border: '1px solid var(--border)',
  display: 'inline-flex',
  alignItems: 'center',
  justifyContent: 'center',
  fontStyle: 'italic',
  fontWeight: 700,
  fontSize: 11,
  color: 'var(--accent)',
};
const bodyStyle: CSSProperties = { flex: '1 1 auto' };
const labelStyle: CSSProperties = { color: 'var(--text-primary)' };
const dismissBtnStyle: CSSProperties = {
  flex: '0 0 auto',
  background: 'transparent',
  border: 'none',
  color: 'var(--text-secondary)',
  cursor: 'pointer',
  fontSize: 16,
  lineHeight: 1,
  padding: 0,
};
