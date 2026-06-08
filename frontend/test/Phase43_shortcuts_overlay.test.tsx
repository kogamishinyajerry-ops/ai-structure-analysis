// FM-04a Phase 43 — ShortcutsOverlay tests (additive).
//
// Tier 1 engineering candidate. Verifies the keyboard-shortcuts
// cheat-sheet overlay: it is closed by default, toggles open on `?`,
// honestly documents the command-palette key, closes on Escape /
// close-button / backdrop, and — critically — respects the
// shouldFire text-input guard so `?` does NOT hijack typing.

import { describe, it, expect, afterEach, vi } from 'vitest';
import { render, screen, fireEvent, cleanup } from '@testing-library/react';
import { ShortcutsOverlay } from '../src/components/ShortcutsOverlay';

afterEach(() => {
  cleanup();
});

describe('ShortcutsOverlay', () => {
  it('renders nothing initially', () => {
    render(<ShortcutsOverlay />);
    expect(screen.queryByTestId('shortcuts-overlay')).toBeNull();
  });

  it('opens on `?` and shows the documented rows', () => {
    render(<ShortcutsOverlay />);
    fireEvent.keyDown(window, { key: '?' });
    expect(screen.getByTestId('shortcuts-overlay')).not.toBeNull();
    const rows = screen.getAllByTestId('shortcuts-row');
    expect(rows.length).toBeGreaterThanOrEqual(5);
  });

  it('documents the command-palette key (K + "palette")', () => {
    render(<ShortcutsOverlay />);
    fireEvent.keyDown(window, { key: '?' });
    const rows = screen.getAllByTestId('shortcuts-row');
    const hasK = rows.some((row) =>
      Array.from(row.querySelectorAll('kbd')).some((kbd) =>
        (kbd.textContent ?? '').includes('K'),
      ),
    );
    expect(hasK).toBe(true);
    const hasPalette = rows.some((row) =>
      (row.textContent ?? '').toLowerCase().includes('palette'),
    );
    expect(hasPalette).toBe(true);
  });

  it('toggles closed on a second `?`', () => {
    render(<ShortcutsOverlay />);
    fireEvent.keyDown(window, { key: '?' });
    expect(screen.getByTestId('shortcuts-overlay')).not.toBeNull();
    fireEvent.keyDown(window, { key: '?' });
    expect(screen.queryByTestId('shortcuts-overlay')).toBeNull();
  });

  it('closes on Escape while open', () => {
    render(<ShortcutsOverlay />);
    fireEvent.keyDown(window, { key: '?' });
    expect(screen.getByTestId('shortcuts-overlay')).not.toBeNull();
    fireEvent.keyDown(window, { key: 'Escape' });
    expect(screen.queryByTestId('shortcuts-overlay')).toBeNull();
  });

  it('closes when the close button is clicked', () => {
    render(<ShortcutsOverlay />);
    fireEvent.keyDown(window, { key: '?' });
    fireEvent.click(screen.getByTestId('shortcuts-close'));
    expect(screen.queryByTestId('shortcuts-overlay')).toBeNull();
  });

  it('closes when the backdrop is clicked', () => {
    render(<ShortcutsOverlay />);
    fireEvent.keyDown(window, { key: '?' });
    const overlay = screen.getByTestId('shortcuts-overlay');
    fireEvent.click(overlay);
    expect(screen.queryByTestId('shortcuts-overlay')).toBeNull();
  });

  it('does NOT open on `?` while a text input is focused (shouldFire guard)', () => {
    const input = document.createElement('input');
    document.body.appendChild(input);
    input.focus();
    expect(document.activeElement).toBe(input);

    render(<ShortcutsOverlay />);
    fireEvent.keyDown(window, { key: '?' });
    expect(screen.queryByTestId('shortcuts-overlay')).toBeNull();

    document.body.removeChild(input);
  });

  it('consumes Escape when open — does not leak to other global handlers (Codex R0)', () => {
    render(<ShortcutsOverlay />);
    // A sibling window keydown listener standing in for the viewport's
    // selection-clear Escape handler.
    const sibling = vi.fn();
    window.addEventListener('keydown', sibling); // bubble phase
    try {
      fireEvent.keyDown(window, { key: '?' });
      expect(screen.getByTestId('shortcuts-overlay')).not.toBeNull();
      sibling.mockClear();
      // Dispatch on a focused element so capture/bubble phases are distinct
      // (mirrors a real keydown). The overlay's capture-phase handler must
      // consume Escape BEFORE the bubble-phase sibling can run.
      fireEvent.keyDown(document.body, { key: 'Escape' });
      expect(screen.queryByTestId('shortcuts-overlay')).toBeNull();
      expect(sibling).not.toHaveBeenCalled();
    } finally {
      window.removeEventListener('keydown', sibling);
    }
  });
});
