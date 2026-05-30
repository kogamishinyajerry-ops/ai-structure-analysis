/**
 * FM-04a Phase 43 — solver progress beat.
 *
 * Tier 1 engineering candidate; not signed validation; not benchmark
 * agreement. Additive suite (no prior-phase test edited) pinning the new
 * SolverProgressPanel (frontend/src/components/SolverProgressPanel.tsx),
 * which replaces the raw black solver-log dump with a LIGHT-surface
 * solve-progress card.
 *
 * What it pins (per the Phase 43 spec):
 *   (a) solving=true + logs with NO percent marker → an INDETERMINATE
 *       progress affordance is present and NO fabricated percentage text;
 *   (b) logs with a parseable marker → the determinate fraction is reflected
 *       (aria-valuenow + fill width);
 *   (c) jobStatusLabel="completed" + solving=false → a complete/success state
 *       renders;
 *   (d) the pure parseSolverProgress helper on a couple of fixtures;
 *   (e) the indeterminate-sweep keyframe is reduced-motion-gated in index.css
 *       (anti-gaming guard B:-1).
 *
 * Honesty (Tier discipline): the panel never fabricates a percentage; the
 * indeterminate path is asserted to carry no "%"/digit-fraction text.
 */

import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

import { describe, expect, it } from 'vitest'
import { render, screen, within } from '@testing-library/react'

import { SolverProgressPanel } from '../src/components/SolverProgressPanel'
import { parseSolverProgress } from '../src/components/solverProgress'

// vitest root is frontend/, so the foundation stylesheet resolves off cwd.
const INDEX_CSS = readFileSync(resolve(process.cwd(), 'src/index.css'), 'utf-8')

describe('parseSolverProgress — pure log → progress helper', () => {
  it('returns indeterminate for empty / non-marker logs (no fabrication)', () => {
    expect(parseSolverProgress([])).toEqual({ mode: 'indeterminate' })
    expect(parseSolverProgress(['booting solver', 'reading input deck'])).toEqual({
      mode: 'indeterminate',
    })
    // Defensive: non-array input degrades gracefully.
    expect(parseSolverProgress(undefined as unknown as string[])).toEqual({
      mode: 'indeterminate',
    })
  })

  it('parses an explicit percentage marker → determinate fraction', () => {
    const r = parseSolverProgress(['Solving...', 'progress: 42%'])
    expect(r.mode).toBe('determinate')
    expect(r.fraction).toBeCloseTo(0.42, 5)
    expect(r.stage).toBe('42%')
  })

  it('parses an "increment k of N" marker → determinate fraction', () => {
    const r = parseSolverProgress(['STEP 1', 'increment 3 of 10'])
    expect(r.mode).toBe('determinate')
    expect(r.fraction).toBeCloseTo(0.3, 5)
    expect(r.stage).toBe('Increment 3 of 10')
  })

  it('parses a "step k/N" slash marker and prefers the newest line', () => {
    const r = parseSolverProgress(['step 1/4', 'step 3/4'])
    expect(r.mode).toBe('determinate')
    expect(r.fraction).toBeCloseTo(0.75, 5)
    expect(r.stage).toBe('Step 3 of 4')
  })

  it('clamps an out-of-range percentage to [0,1]', () => {
    expect(parseSolverProgress(['done 120%']).fraction).toBe(1)
  })
})

describe('SolverProgressPanel — Phase 43 solve-progress beat', () => {
  it('(a) shows an INDETERMINATE affordance with NO fabricated percent while solving', () => {
    render(
      <SolverProgressPanel
        logs={['booting CalculiX', 'assembling stiffness matrix']}
        solving
        jobStatusLabel="running"
      />,
    )

    const track = screen.getByTestId('solver-progress-track')
    expect(track.getAttribute('data-mode')).toBe('indeterminate')
    // The animated sweep element is present while solving.
    expect(screen.getByTestId('solver-progress-sweep')).toBeTruthy()
    // It carries the reduced-motion-gated class (not an inline animation).
    expect(screen.getByTestId('solver-progress-sweep').className).toContain('solve-sweep')

    // Honesty: NO fabricated percentage anywhere in the panel.
    const panel = screen.getByTestId('solver-progress-panel')
    expect(panel.textContent).not.toMatch(/\d+\s*%/)
    // No determinate progressbar value is asserted on the indeterminate track.
    expect(track.getAttribute('aria-valuenow')).toBeNull()
  })

  it('(b) reflects a determinate fraction when logs contain a parseable marker', () => {
    render(
      <SolverProgressPanel
        logs={['increment 3 of 10']}
        solving
        jobStatusLabel="running"
      />,
    )

    const track = screen.getByTestId('solver-progress-track')
    expect(track.getAttribute('data-mode')).toBe('determinate')
    expect(track.getAttribute('aria-valuenow')).toBe('30')

    const fill = screen.getByTestId('solver-progress-fill')
    expect(fill.style.width).toBe('30%')

    // The stage label is surfaced, not a fabricated number.
    expect(screen.getByText('Increment 3 of 10')).toBeTruthy()
  })

  it('(c) renders a complete/success state when completed + not solving', () => {
    render(
      <SolverProgressPanel
        logs={['Job finished.', 'wrote results.frd']}
        solving={false}
        jobStatusLabel="completed"
      />,
    )

    expect(screen.getByTestId('solver-complete')).toBeTruthy()
    expect(screen.getByText('Solve complete')).toBeTruthy()

    // The status chip carries the completed tone.
    const chip = screen.getByTestId('solver-status-chip')
    expect(chip.getAttribute('data-tone')).toBe('completed')
    expect(chip.textContent).toBe('completed')

    // No active sweep / progressbar once complete.
    expect(screen.queryByTestId('solver-progress-sweep')).toBeNull()
    expect(screen.queryByTestId('solver-progress-track')).toBeNull()
  })

  it('chip tones: running→accent, failed→danger', () => {
    const { rerender } = render(
      <SolverProgressPanel logs={[]} solving jobStatusLabel="running" />,
    )
    expect(screen.getByTestId('solver-status-chip').getAttribute('data-tone')).toBe(
      'running',
    )

    rerender(<SolverProgressPanel logs={['fatal error']} solving={false} jobStatusLabel="failed" />)
    expect(screen.getByTestId('solver-status-chip').getAttribute('data-tone')).toBe(
      'failed',
    )
  })

  it('renders gracefully with empty logs (no throw, empty-state placeholder)', () => {
    render(<SolverProgressPanel logs={[]} solving={false} jobStatusLabel={null} />)
    expect(screen.getByTestId('solver-progress-panel')).toBeTruthy()
    expect(screen.getByTestId('solver-log-empty')).toBeTruthy()
    // No status chip when the label is null.
    expect(screen.queryByTestId('solver-status-chip')).toBeNull()
  })

  it('renders the log lines in the scrollable monospace area', () => {
    render(
      <SolverProgressPanel
        logs={['line one', 'line two', 'line three']}
        solving={false}
        jobStatusLabel="completed"
      />,
    )
    const area = screen.getByTestId('solver-log-area')
    const lines = within(area).getAllByTestId('solver-log-line')
    expect(lines).toHaveLength(3)
    expect(lines[2].textContent).toBe('line three')
    // LIGHT theme — the area is NOT a #000/#fff terminal.
    expect(area.style.background).toBe('var(--c-100)')
    expect(area.style.color).toBe('var(--text-secondary)')
  })

  it('(e) the indeterminate-sweep keyframe is defined AND reduced-motion-gated', () => {
    expect(INDEX_CSS).toContain('@keyframes fm04a-solve-sweep')
    expect(INDEX_CSS).toContain('animation: fm04a-solve-sweep')
    // Suppressed under prefers-reduced-motion (anti-gaming guard B:-1).
    expect(INDEX_CSS).toMatch(
      /prefers-reduced-motion[\s\S]*\.solve-sweep\s*\{\s*animation:\s*none/,
    )
  })
})
