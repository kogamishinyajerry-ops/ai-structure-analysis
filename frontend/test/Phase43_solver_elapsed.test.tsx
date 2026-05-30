/**
 * FM-04a Phase 43 — solver elapsed-timer honesty (Codex Slice-2 R1 closure).
 *
 * Tier 1 engineering candidate; not signed validation; not benchmark
 * agreement. Additive suite (no prior-phase test edited).
 *
 * Pins the SolverProgressPanel elapsed readout's honesty contract after the
 * Codex Slice-2 R1 finding (the prior mount-based heuristic under-reported
 * elapsed time when the panel mounted onto an already-running solve):
 *
 *   (a) shows MEASURED elapsed ONLY when the host hands an authoritative
 *       `solveStartedAt` (epoch ms), and counts up over wall-clock time;
 *   (b) OMITS the readout when `solveStartedAt` is null — the panel mounted
 *       onto a job whose true start it never observed (the Copilot attach
 *       path). It must NOT fabricate / under-report by measuring from mount;
 *   (c) OMITS the readout when `solveStartedAt` is omitted entirely.
 *
 * Uses fake timers so the interval-driven readout is deterministic and the
 * measurement is asserted against the controlled clock, not real time.
 */

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { act, cleanup, render, screen } from '@testing-library/react'

import { SolverProgressPanel } from '../src/components/SolverProgressPanel'

describe('SolverProgressPanel — elapsed timer honesty (authoritative start)', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    vi.setSystemTime(new Date('2026-01-01T00:00:00.000Z'))
  })
  afterEach(() => {
    cleanup()
    vi.useRealTimers()
  })

  it('(a) shows MEASURED elapsed when an authoritative solveStartedAt is supplied, and counts up', () => {
    const start = Date.now() // controlled clock origin
    render(
      <SolverProgressPanel
        logs={['Solving...']}
        solving
        jobStatusLabel="running"
        solveStartedAt={start}
      />,
    )

    // Advance 3s of controlled wall-clock — the interval ticks and the
    // readout reflects MEASURED time (Date.now() - start), not a guess.
    act(() => {
      vi.advanceTimersByTime(3000)
    })
    expect(screen.getByTestId('solver-elapsed').textContent).toBe('3s')

    // Counts up as the clock advances further.
    act(() => {
      vi.advanceTimersByTime(2000)
    })
    expect(screen.getByTestId('solver-elapsed').textContent).toBe('5s')
  })

  it('(b) OMITS the readout when solveStartedAt is null (unknown start — Copilot attach path)', () => {
    render(
      <SolverProgressPanel
        logs={['Solving...']}
        solving
        jobStatusLabel="running"
        solveStartedAt={null}
      />,
    )

    // Even after the clock advances, NO elapsed readout is fabricated.
    act(() => {
      vi.advanceTimersByTime(5000)
    })
    expect(screen.queryByTestId('solver-elapsed')).toBeNull()
  })

  it('(c) OMITS the readout when solveStartedAt is omitted entirely', () => {
    render(
      <SolverProgressPanel logs={['Solving...']} solving jobStatusLabel="running" />,
    )

    act(() => {
      vi.advanceTimersByTime(5000)
    })
    expect(screen.queryByTestId('solver-elapsed')).toBeNull()
  })

  it('(d) does not under-report: a NaN/non-finite solveStartedAt is treated as unknown', () => {
    render(
      <SolverProgressPanel
        logs={['Solving...']}
        solving
        jobStatusLabel="running"
        solveStartedAt={Number.NaN}
      />,
    )

    act(() => {
      vi.advanceTimersByTime(4000)
    })
    expect(screen.queryByTestId('solver-elapsed')).toBeNull()
  })
})
