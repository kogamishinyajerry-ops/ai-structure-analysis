// FM-04a Phase 43 — app-level global keyboard-shortcut registration.
//
// Consolidates App.tsx's global hotkey wiring behind one hook so the shell
// component stays lean (App.tsx LOC pin) and there is a single, discoverable
// home for future global shortcuts. A thin, behaviour-preserving wrapper over
// the generic useKeyboardShortcuts binder — the canonical-hotkey matching and
// text-input guard still live in useKeyboardShortcuts.ts.

import { useKeyboardShortcuts } from './useKeyboardShortcuts';

export interface GlobalShortcutHandlers {
  /** Toggle the command palette (⌘K on macOS / Ctrl-K elsewhere). */
  readonly togglePalette: () => void;
}

/**
 * Register the application's global keyboard shortcuts. Currently the single
 * command-palette toggle (mod+k), which fires even inside text inputs because
 * the palette IS the text input it opens.
 */
export function useGlobalShortcuts({ togglePalette }: GlobalShortcutHandlers): void {
  useKeyboardShortcuts([
    {
      hotkey: 'mod+k',
      handler: (e) => {
        e.preventDefault();
        togglePalette();
      },
      fireInTextInput: true,
    },
  ]);
}
