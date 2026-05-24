/**
 * FM-04a Phase 38 I — sensitivity-study run/poll error recovery (act-on #6).
 *
 * Eval-fleet finding #6 (Phase 38 E): the study flow swallowed errors in a
 * bare `console.error` catch and, because the backend never rolls a failed
 * sweep run up to a FAILED experiment status, a failed/unreachable backend
 * left the UI stuck in `loading` forever. These tests pin the disposition:
 *   - a start failure is surfaced (ErrorCard) and resets loading;
 *   - a success with no experiment_id is treated as a failure (not stuck);
 *   - a COMPLETED study calls onComplete and stops polling;
 *   - a FAILED run surfaces the error AND stops polling (no infinite loop);
 *   - a poll fetch error surfaces the error AND stops polling.
 *
 * Tier 1 / Tier 2 engineering candidate; not signed validation; not benchmark
 * agreement.
 */

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { act, renderHook } from '@testing-library/react'

import {
  useSensitivityStudy,
  type UseSensitivityStudyOptions,
} from '../src/state/useSensitivityStudy'
import type { ErrorCardProps } from '../src/components/ErrorCard'

const POLL_MS = 10

function makeOpts(
  overrides: Partial<UseSensitivityStudyOptions> = {},
): UseSensitivityStudyOptions & {
  setLoading: ReturnType<typeof vi.fn>
  onComplete: ReturnType<typeof vi.fn>
  appendLog: ReturnType<typeof vi.fn>
  setUploadError: ReturnType<typeof vi.fn>
  setActiveExperiment: ReturnType<typeof vi.fn>
} {
  const setLoading = vi.fn()
  const setActiveExperiment = vi.fn()
  const onComplete = vi.fn()
  const appendLog = vi.fn()
  const setUploadError = vi.fn()
  const clearUploadError = vi.fn()
  // Mirror the real withRecovery contract: run fn; on success return its
  // value; on throw surface the ErrorCard and return undefined.
  const withRecovery = vi.fn(
    async <T,>(fn: () => Promise<T>, options: unknown): Promise<T | undefined> => {
      try {
        return await fn()
      } catch {
        setUploadError({ ...(options as object) } as ErrorCardProps)
        return undefined
      }
    },
  )
  return {
    apiBase: '/api/v1',
    activeCaseId: 'case-x',
    setLoading,
    setActiveExperiment,
    onComplete,
    appendLog,
    withRecovery: withRecovery as UseSensitivityStudyOptions['withRecovery'],
    setUploadError,
    clearUploadError,
    pollIntervalMs: POLL_MS,
    ...overrides,
  }
}

/** Route fetch by URL suffix. Each entry is a one-shot responder. */
function routeFetch(handlers: {
  run?: () => Promise<unknown> | unknown
  status?: () => Promise<unknown> | unknown
}) {
  global.fetch = vi.fn((url: string) => {
    if (url.includes('/sensitivity/run')) return Promise.resolve(handlers.run!())
    if (url.includes('/sensitivity/status/'))
      return Promise.resolve(handlers.status!())
    throw new Error(`unexpected fetch ${url}`)
  }) as unknown as typeof fetch
}

const okJson = (body: unknown) => ({ ok: true, json: async () => body })
const errJson = (status: number, body: unknown = {}) => ({
  ok: false,
  status,
  json: async () => body,
})

beforeEach(() => vi.useFakeTimers())
afterEach(() => {
  vi.useRealTimers()
  vi.restoreAllMocks()
})

describe('useSensitivityStudy — start failures surface, never hang (Phase 38 I)', () => {
  it('HTTP error on /run surfaces the ErrorCard and resets loading', async () => {
    const opts = makeOpts()
    routeFetch({ run: () => errJson(500, { detail: 'boom' }) })
    const { result } = renderHook(() => useSensitivityStudy(opts))

    await act(async () => {
      await result.current.handleRunStudy('thickness', [1, 2])
    })

    expect(opts.setLoading).toHaveBeenCalledWith(true)
    expect(opts.setLoading).toHaveBeenLastCalledWith(false)
    expect(opts.setUploadError).toHaveBeenCalledTimes(1) // surfaced, not silent
    expect(opts.appendLog).toHaveBeenCalledWith(
      expect.stringContaining('failed to start'),
    )
  })

  it('success with no experiment_id is treated as failure (not stuck loading)', async () => {
    const opts = makeOpts()
    routeFetch({ run: () => okJson({}) }) // 200 but missing experiment_id
    const { result } = renderHook(() => useSensitivityStudy(opts))

    await act(async () => {
      await result.current.handleRunStudy('thickness', [1])
    })

    expect(opts.setUploadError).toHaveBeenCalledTimes(1)
    expect(opts.setLoading).toHaveBeenLastCalledWith(false)
  })

  it('no-op when no case is selected', async () => {
    const opts = makeOpts({ activeCaseId: null })
    routeFetch({ run: () => okJson({ experiment_id: 'e1' }) })
    const { result } = renderHook(() => useSensitivityStudy(opts))

    await act(async () => {
      await result.current.handleRunStudy('thickness', [1])
    })
    expect(opts.setLoading).not.toHaveBeenCalled()
    expect(global.fetch).not.toHaveBeenCalled()
  })
})

describe('useSensitivityStudy — poll terminal states stop the interval (Phase 38 I)', () => {
  it('COMPLETED calls onComplete, records the experiment, and stops polling', async () => {
    const opts = makeOpts()
    routeFetch({
      run: () => okJson({ experiment_id: 'e1' }),
      status: () => okJson({ status: 'COMPLETED', runs: [] }),
    })
    const { result } = renderHook(() => useSensitivityStudy(opts))

    await act(async () => {
      await result.current.handleRunStudy('thickness', [1])
    })
    await act(async () => {
      await vi.advanceTimersByTimeAsync(POLL_MS)
    })

    expect(opts.setActiveExperiment).toHaveBeenCalled()
    expect(opts.onComplete).toHaveBeenCalledTimes(1)
    const statusCallsAfterComplete = (global.fetch as ReturnType<typeof vi.fn>)
      .mock.calls.length
    await act(async () => {
      await vi.advanceTimersByTimeAsync(POLL_MS * 3)
    })
    // interval cleared → no further status polls
    expect((global.fetch as ReturnType<typeof vi.fn>).mock.calls.length).toBe(
      statusCallsAfterComplete,
    )
  })

  it('a FAILED sweep run surfaces the error and stops polling (no infinite loop)', async () => {
    const opts = makeOpts()
    routeFetch({
      run: () => okJson({ experiment_id: 'e1' }),
      // backend never rolls up to FAILED, so the failure is on the run.
      status: () => okJson({ status: 'RUNNING', runs: [{ status: 'FAILED' }] }),
    })
    const { result } = renderHook(() => useSensitivityStudy(opts))

    await act(async () => {
      await result.current.handleRunStudy('thickness', [1])
    })
    await act(async () => {
      await vi.advanceTimersByTimeAsync(POLL_MS)
    })

    expect(opts.setUploadError).toHaveBeenCalledTimes(1)
    expect(opts.setLoading).toHaveBeenLastCalledWith(false)
    const callsAfterFail = (global.fetch as ReturnType<typeof vi.fn>).mock.calls
      .length
    await act(async () => {
      await vi.advanceTimersByTimeAsync(POLL_MS * 5)
    })
    expect((global.fetch as ReturnType<typeof vi.fn>).mock.calls.length).toBe(
      callsAfterFail,
    )
  })

  it('a poll fetch error surfaces the error and stops polling', async () => {
    const opts = makeOpts()
    routeFetch({
      run: () => okJson({ experiment_id: 'e1' }),
      status: () => errJson(503),
    })
    const { result } = renderHook(() => useSensitivityStudy(opts))

    await act(async () => {
      await result.current.handleRunStudy('thickness', [1])
    })
    await act(async () => {
      await vi.advanceTimersByTimeAsync(POLL_MS)
    })

    expect(opts.setUploadError).toHaveBeenCalledTimes(1)
    expect(opts.setLoading).toHaveBeenLastCalledWith(false)
    const callsAfterErr = (global.fetch as ReturnType<typeof vi.fn>).mock.calls
      .length
    await act(async () => {
      await vi.advanceTimersByTimeAsync(POLL_MS * 5)
    })
    expect((global.fetch as ReturnType<typeof vi.fn>).mock.calls.length).toBe(
      callsAfterErr,
    )
  })
})
