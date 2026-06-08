// FM-04a Phase 25 C — Basic / Advanced UI mode toggle (segmented control).
//
// Compact segmented control mounted in the topbar (or wherever the
// parent threads the prop). Persists to localStorage via the
// uiMode storage adapter. State preservation across toggle is owned
// at the parent level — this component is presentational.

import { type CSSProperties } from 'react';

import { type UiMode } from '../uiMode';

export interface UiModeToggleProps {
  mode: UiMode;
  onChange: (mode: UiMode) => void;
}

export function UiModeToggle({ mode, onChange }: UiModeToggleProps) {
  return (
    <div
      data-testid="ui-mode-toggle"
      role="radiogroup"
      aria-label="UI mode"
      style={STYLES.container}
    >
      <button
        type="button"
        role="radio"
        aria-checked={mode === 'basic'}
        data-testid="ui-mode-basic"
        onClick={() => onChange('basic')}
        style={mode === 'basic' ? STYLES.segmentActive : STYLES.segment}
      >
        Basic
      </button>
      <button
        type="button"
        role="radio"
        aria-checked={mode === 'advanced'}
        data-testid="ui-mode-advanced"
        onClick={() => onChange('advanced')}
        style={mode === 'advanced' ? STYLES.segmentActive : STYLES.segment}
      >
        Advanced
      </button>
    </div>
  );
}

const STYLES: Record<string, CSSProperties> = {
  container: {
    display: 'inline-flex',
    background: 'var(--c-100)',
    border: '1px solid var(--border)',
    borderRadius: 6,
    padding: 2,
    gap: 0,
  },
  segment: {
    background: 'transparent',
    color: 'var(--text-secondary)',
    border: 'none',
    padding: '4px 12px',
    fontSize: '0.72rem',
    fontWeight: 600,
    letterSpacing: 0.3,
    cursor: 'pointer',
    borderRadius: 4,
  },
  segmentActive: {
    background: 'var(--accent)',
    color: 'white',
    border: 'none',
    padding: '4px 12px',
    fontSize: '0.72rem',
    fontWeight: 700,
    letterSpacing: 0.3,
    cursor: 'pointer',
    borderRadius: 4,
  },
};
