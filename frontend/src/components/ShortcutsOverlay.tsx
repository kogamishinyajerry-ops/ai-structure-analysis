// FM-04a Phase 43 — keyboard-shortcuts cheat-sheet overlay.
//
// Tier 1 engineering candidate; not signed validation; not benchmark
// agreement.
//
// A discoverability affordance modeled on experience-grade CAE/IDE
// tools (Abaqus, VS Code): press `?` anywhere to toggle a centered
// modal listing the application's GLOBAL keyboard shortcuts. The
// component is fully self-contained — the host mounts <ShortcutsOverlay/>
// with no props; it owns its open state, its own window keydown
// listener, focus-trap, and backdrop dismissal.
//
// Honesty contract (guard G:-1): this panel documents ONLY shortcuts
// that genuinely exist in the codebase. The set below was verified
// against src/App.tsx (useKeyboardShortcuts 'mod+k'), CommandPalette.tsx
// (Escape / ArrowUp / ArrowDown / Enter), and this component's own `?`
// binding. No fabricated/aspirational hotkeys are listed.

import { useEffect, useRef, useState } from 'react';
import { X } from 'lucide-react';
import { shouldFire } from '../hooks/useKeyboardShortcuts';
import { useFocusTrap } from './useFocusTrap';

// `mod` = Cmd on macOS, Ctrl elsewhere — mirrors the canonicalHotkey
// convention in useKeyboardShortcuts.ts. Detect platform defensively
// (navigator may be absent in non-browser environments); default to
// the Ctrl label when undetectable.
const IS_MAC =
  typeof navigator !== 'undefined' &&
  /Mac|iPhone|iPad|iPod/i.test(navigator.platform ?? '');
const MOD_LABEL = IS_MAC ? '⌘' : 'Ctrl';

// Each row: the chip key(s) on the left, the honest description on the
// right. `keys` is rendered as a sequence of <kbd>-style chips.
interface ShortcutRow {
  readonly keys: readonly string[];
  readonly description: string;
}

const SHORTCUTS: readonly ShortcutRow[] = [
  { keys: [MOD_LABEL, 'K'], description: 'Open / toggle the command palette' },
  {
    keys: ['Esc'],
    description: 'Close the command palette / clear the current 3D node selection',
  },
  { keys: ['↑', '↓'], description: 'Move selection in the command palette' },
  { keys: ['Enter'], description: 'Run the highlighted command in the palette' },
  { keys: ['?'], description: 'Toggle this shortcuts panel' },
];

export function ShortcutsOverlay() {
  const [open, setOpen] = useState(false);
  const dialogRef = useRef<HTMLDivElement | null>(null);

  // Trap Tab focus inside the dialog while it is open (WCAG 2.4.3),
  // reusing the project's established focus-trap hook. Paused when
  // closed; the conditional render below also tears it down.
  useFocusTrap({ containerRef: dialogRef, active: open });

  // Global `?` toggle + Escape-to-close. A direct window listener is
  // the established self-contained pattern (cf. ResultMeshWebGLViewport)
  // — we deliberately do NOT route this through useKeyboardShortcuts so
  // the host needs zero wiring.
  useEffect(() => {
    const handler = (event: KeyboardEvent): void => {
      if (event.key === '?') {
        // Reuse the project text-input policy: never hijack `?` while
        // the user is typing into an input / textarea / contenteditable.
        if (!shouldFire({ fireInTextInput: false }, document.activeElement)) {
          return;
        }
        event.preventDefault();
        setOpen((prev) => !prev);
        return;
      }
      if (event.key === 'Escape') {
        // Only act on Escape when we are the open dialog; otherwise let
        // it pass through to the palette / selection-clear handlers.
        setOpen((prev) => (prev ? false : prev));
      }
    };
    window.addEventListener('keydown', handler);
    return () => {
      window.removeEventListener('keydown', handler);
    };
  }, []);

  if (!open) return null;

  const close = (): void => setOpen(false);

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label="Keyboard shortcuts"
      data-testid="shortcuts-overlay"
      onClick={(e) => {
        // Backdrop click (this element) closes; clicks on the inner
        // card do not bubble a close.
        if (e.target === e.currentTarget) close();
      }}
      style={backdropStyle}
    >
      <div ref={dialogRef} style={cardStyle}>
        <div style={headerRowStyle}>
          <span style={titleStyle}>Keyboard shortcuts</span>
          <button
            type="button"
            onClick={close}
            aria-label="Close keyboard shortcuts"
            data-testid="shortcuts-close"
            style={closeButtonStyle}
          >
            <X size={16} aria-hidden="true" />
          </button>
        </div>
        <ul style={listStyle}>
          {SHORTCUTS.map((row) => (
            <li
              key={row.description}
              data-testid="shortcuts-row"
              style={rowStyle}
            >
              <span style={keysCellStyle}>
                {row.keys.map((k, i) => (
                  <kbd key={`${k}-${i}`} style={kbdStyle}>
                    {k}
                  </kbd>
                ))}
              </span>
              <span style={descriptionStyle}>{row.description}</span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}

// Inline raw-CSS styles via design tokens — there is no Tailwind step.
const backdropStyle: React.CSSProperties = {
  position: 'fixed',
  inset: 0,
  background: 'rgba(20,18,15,0.45)',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  zIndex: 60,
};
const cardStyle: React.CSSProperties = {
  background: 'var(--bg-surface)',
  color: 'var(--text-primary)',
  border: '1px solid var(--border)',
  borderRadius: 'var(--r-md)',
  boxShadow: 'var(--elev-3)',
  padding: 'var(--sp-4)',
  minWidth: 360,
  maxWidth: 480,
  boxSizing: 'border-box',
};
const headerRowStyle: React.CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'space-between',
  gap: 'var(--sp-3)',
  marginBottom: 'var(--sp-3)',
};
const titleStyle: React.CSSProperties = {
  fontSize: 'var(--fs-md)',
  fontWeight: 700,
};
const closeButtonStyle: React.CSSProperties = {
  display: 'inline-flex',
  alignItems: 'center',
  justifyContent: 'center',
  background: 'transparent',
  border: 'none',
  color: 'var(--accent)',
  cursor: 'pointer',
  padding: 2,
  borderRadius: 'var(--r-xs)',
  lineHeight: 0,
};
const listStyle: React.CSSProperties = {
  listStyle: 'none',
  margin: 0,
  padding: 0,
  display: 'flex',
  flexDirection: 'column',
  gap: 'var(--sp-2)',
};
const rowStyle: React.CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'space-between',
  gap: 'var(--sp-4)',
};
const keysCellStyle: React.CSSProperties = {
  display: 'inline-flex',
  alignItems: 'center',
  gap: 4,
  flexShrink: 0,
};
const kbdStyle: React.CSSProperties = {
  background: 'var(--c-100)',
  border: '1px solid var(--border)',
  borderRadius: 'var(--r-xs)',
  padding: '2px 6px',
  fontFamily: 'var(--font-mono)',
  fontSize: 'var(--fs-xs)',
};
const descriptionStyle: React.CSSProperties = {
  color: 'var(--text-secondary)',
  fontSize: 'var(--fs-sm)',
  textAlign: 'right',
};
