// FM-04a Phase 43 — persistent CAE-style status strip.
//
// Tier 1 engineering candidate; not signed validation; not benchmark
// agreement. This suite verifies the StatusBar subcomponent
// (frontend/src/components/StatusBar.tsx), the thin status strip the app
// shell pins to the bottom of the LIGHT chrome (the analogue of the
// status bar every reference solver carries).
//
// What it pins (per the Phase 43 spec):
//   (a) the active case label + a default unit system render;
//   (b) the run-state label shows and reflects runStateTone via its
//       inline style color (tone → design-token color map);
//   (c) hoverCoords set → an X/Y/Z monospace readout with 3-decimal
//       values; hoverCoords null → NO coords segment;
//   (d) renders without crashing when ALL optional props are omitted.
//
// Honesty (Tier discipline): null/blank props yield OMITTED segments —
// the bar never fabricates a case, run-state, or coordinate it was not
// given.

import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { StatusBar } from '../src/components/StatusBar';

describe('StatusBar — Phase 43 persistent status strip', () => {
  it('(a) renders the active case label + a default unit system', () => {
    render(<StatusBar caseLabel="GS-102 bullet-plate" />);

    // Case label present.
    expect(screen.getByTestId('status-bar-case').textContent).toBe(
      'GS-102 bullet-plate',
    );
    // Unit system defaults to the canonical SI label (not fabricated solver
    // data — a presentation default) when no unitSystem prop is supplied.
    expect(screen.getByTestId('status-bar-unit-system').textContent).toBe(
      'SI · m, Pa',
    );
  });

  it('(a2) honors an explicit unit-system prop over the default', () => {
    render(<StatusBar unitSystem="US · in, psi" />);
    expect(screen.getByTestId('status-bar-unit-system').textContent).toBe(
      'US · in, psi',
    );
  });

  it('(b) shows the run-state label in its tone color (success)', () => {
    render(<StatusBar runStateLabel="Solved" runStateTone="success" />);

    const runState = screen.getByTestId('status-bar-run-state') as HTMLElement;
    expect(runState.textContent).toBe('Solved');
    // Tone → token color. success maps to --success-500.
    expect(runState.style.color).toBe('var(--success-500)');
  });

  it('(b2) maps each tone to its design token (muted/accent/danger)', () => {
    const cases: Array<[
      'muted' | 'accent' | 'danger',
      string,
    ]> = [
      ['muted', 'var(--text-muted)'],
      ['accent', 'var(--accent)'],
      ['danger', 'var(--danger-400)'],
    ];
    for (const [tone, token] of cases) {
      const { unmount } = render(
        <StatusBar runStateLabel="State" runStateTone={tone} />,
      );
      const el = screen.getByTestId('status-bar-run-state') as HTMLElement;
      expect(el.style.color).toBe(token);
      unmount();
    }
  });

  it('(c) renders an X/Y/Z coords readout with 3-decimal values when hoverCoords set', () => {
    render(<StatusBar hoverCoords={{ x: 1.23456, y: -0.5, z: 42 }} />);

    const readout = screen.getByTestId('status-bar-hover-coords');
    expect(readout).toBeTruthy();
    // Three fixed decimals each (mm precision on a 1-m scale mesh).
    expect(screen.getByTestId('status-bar-coord-x').textContent).toBe('1.235');
    expect(screen.getByTestId('status-bar-coord-y').textContent).toBe('-0.500');
    expect(screen.getByTestId('status-bar-coord-z').textContent).toBe('42.000');
    // Rendered monospace (CAE cursor-readout convention).
    expect((readout as HTMLElement).style.fontFamily).toBe('var(--font-mono)');
  });

  it('(c2) omits the coords segment when hoverCoords is null', () => {
    render(<StatusBar caseLabel="C" hoverCoords={null} />);
    expect(screen.queryByTestId('status-bar-hover-coords')).toBeNull();
    expect(screen.queryByTestId('status-bar-coord-x')).toBeNull();
  });

  it('(c3) omits the coords segment when a coordinate is non-finite (no NaN readout)', () => {
    render(<StatusBar hoverCoords={{ x: Number.NaN, y: 1, z: 2 }} />);
    expect(screen.queryByTestId('status-bar-hover-coords')).toBeNull();
  });

  it('(d) renders without crashing when ALL optional props are omitted', () => {
    const { container } = render(<StatusBar />);

    // The strip itself still mounts.
    expect(screen.getByTestId('status-bar')).toBeTruthy();
    // Default unit system is the only guaranteed segment.
    expect(screen.getByTestId('status-bar-unit-system').textContent).toBe(
      'SI · m, Pa',
    );
    // Optional segments are gracefully absent (nothing fabricated).
    expect(screen.queryByTestId('status-bar-case')).toBeNull();
    expect(screen.queryByTestId('status-bar-run-state')).toBeNull();
    expect(screen.queryByTestId('status-bar-job-status')).toBeNull();
    expect(screen.queryByTestId('status-bar-hover-coords')).toBeNull();
    // The bar carries the hairline TOP border (CAE status-strip convention).
    const bar = container.querySelector('[data-testid="status-bar"]') as HTMLElement;
    expect(bar.style.borderTop).toContain('var(--border)');
  });

  it('(d2) omits the case + job-status segments when those props are null/blank', () => {
    render(
      <StatusBar
        caseLabel={null}
        jobStatusLabel="   "
        runStateLabel="Running"
        runStateTone="accent"
      />,
    );
    expect(screen.queryByTestId('status-bar-case')).toBeNull();
    expect(screen.queryByTestId('status-bar-job-status')).toBeNull();
    // The supplied run-state still shows.
    expect(screen.getByTestId('status-bar-run-state').textContent).toBe('Running');
  });
});
