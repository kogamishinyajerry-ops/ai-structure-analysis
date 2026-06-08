// FM-04a Phase 43 — ModeSelector dark-glass token migration guard.
//
// Tier 1 engineering candidate; not signed validation; not benchmark agreement.
//
// ModeSelector floats OVER the dark 3D viewport (absolute, top-right). It used
// to be 100% Tailwind, which is INERT in this raw-CSS repo — so for modal +
// buckling results it painted as a bare transparent serif table with default
// link-blue text. This test pins the token migration so the regression can't
// silently return:
//
//  (a) NO element carries an inert Tailwind slate/indigo/utility class.
//  (b) the selected row references the var(--accent) clay/coral token.
//  (c) clicking a row calls onSelectMode(inc.index - 1) — behavior preserved.

import { describe, it, expect, vi } from 'vitest';
import { render, fireEvent } from '@testing-library/react';
import { ModeSelector } from '../src/components/ModeSelector.tsx';

const FIXTURE = [
  { index: 1, step: 1, type: 'vibration', value: 12.34, max_displacement: 0.0012, max_von_mises: 0 },
  { index: 2, step: 1, type: 'vibration', value: 45.67, max_displacement: 0.0034, max_von_mises: 0 },
  { index: 3, step: 1, type: 'vibration', value: 89.01, max_displacement: 0.0056, max_von_mises: 0 },
];

// The inert Tailwind utilities the old component leaned on (and any sibling
// utility token). A re-introduction of ANY of these is the defect we guard.
const INERT_TAILWIND = /bg-slate-|text-indigo-|divide-slate-|text-slate-|bg-indigo-/;

describe('Phase 43 — ModeSelector dark-glass token migration', () => {
  it('(a) renders NO inert Tailwind slate/indigo/utility class', () => {
    const { container } = render(
      <ModeSelector
        increments={FIXTURE}
        selectedModeIndex={1}
        activeAnalysisType="modal"
        onSelectMode={() => {}}
      />,
    );
    const all = container.querySelectorAll('*');
    expect(all.length).toBeGreaterThan(0);
    for (const el of Array.from(all)) {
      // className can be a string or an SVGAnimatedString (lucide svg) — coerce.
      const raw = el.getAttribute('class') ?? '';
      expect(raw).not.toMatch(INERT_TAILWIND);
    }
  });

  it('(b) selected row references the var(--accent) token in its inline style', () => {
    const { getByTestId } = render(
      <ModeSelector
        increments={FIXTURE}
        selectedModeIndex={1}
        activeAnalysisType="modal"
        onSelectMode={() => {}}
      />,
    );
    // selectedModeIndex=1 highlights the row with inc.index === 2.
    const selectedRow = getByTestId('mode-row-2');
    expect(selectedRow.getAttribute('data-selected')).toBe('true');
    const style = selectedRow.getAttribute('style') ?? '';
    // Accept the accent token in any form jsdom may serialize it to, plus
    // the resolved clay hex, so the test pins intent without over-coupling.
    expect(style).toMatch(/var\(--accent|--accent-glow|--accent-300|#b3552f|#a64f30|#e6a385/i);

    // The pulse dot is present on the selected row and uses the accent fill.
    const dot = getByTestId('mode-pulse-dot');
    const dotStyle = dot.getAttribute('style') ?? '';
    expect(dotStyle).toMatch(/var\(--accent/i);
    // Pulse animation runs via a CSS class so reduced-motion can suppress it.
    expect(dot.getAttribute('class') ?? '').toContain('mode-pulse-dot');
  });

  it('(c) clicking a row calls onSelectMode with (inc.index - 1)', () => {
    const onSelectMode = vi.fn();
    const { getByTestId } = render(
      <ModeSelector
        increments={FIXTURE}
        selectedModeIndex={0}
        activeAnalysisType="buckling"
        onSelectMode={onSelectMode}
      />,
    );
    fireEvent.click(getByTestId('mode-row-3'));
    expect(onSelectMode).toHaveBeenCalledTimes(1);
    expect(onSelectMode).toHaveBeenCalledWith(2); // inc.index(3) - 1
  });

  it('null-guard: empty increments renders nothing', () => {
    const { container } = render(
      <ModeSelector
        increments={[]}
        selectedModeIndex={0}
        activeAnalysisType="modal"
        onSelectMode={() => {}}
      />,
    );
    expect(container.firstChild).toBeNull();
  });
});
