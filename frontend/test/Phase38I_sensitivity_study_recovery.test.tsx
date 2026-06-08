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
  // value; on throw surface the ErrorCard (with an onRetry that reruns ONLY
  // the closure, as useUploadErrorRecovery does) and return undefined.
  const withRecovery = vi.fn(
    async <T,>(fn: () => Promise<T>, options: unknown): Promise<T | undefined> => {
      try {
        return await fn()
      } catch {
        setUploadError({
          ...(options as object),
          onRetry: () => withRecovery(fn, options),
        } as ErrorCardProps)
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

  it('a retried failed start restores loading — Codex R2 P1', async () => {
    const opts = makeOpts()
    routeFetch({ run: () => errJson(500, { detail: 'boom' }) }) // always fails
    const { result } = renderHook(() => useSensitivityStudy(opts))

    await act(async () => {
      await result.current.handleRunStudy('thickness', [1])
    })
    // First failure resets loading.
    expect(opts.setLoading).toHaveBeenLastCalledWith(false)

    // Click Retry: withRecovery reruns ONLY the closure. The cleanup must run
    // again so loading is not left stuck true after a second failure.
    const onRetry = opts.setUploadError.mock.calls.at(-1)?.[0].onRetry as () => void
    await act(async () => {
      await onRetry()
    })
    expect(opts.setLoading).toHaveBeenLastCalledWith(false)
    // sanity: it did try again (true was set on the retry) before resetting.
    expect(opts.setLoading.mock.calls.filter((c) => c[0] === true).length).toBe(
      2,
    )
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

  it('a FAILED run normalises stored status to FAILED (no stale RUNNING) — Codex R0 P2-b', async () => {
    const opts = makeOpts()
    routeFetch({
      run: () => okJson({ experiment_id: 'e1' }),
      status: () => okJson({ status: 'RUNNING', runs: [{ status: 'FAILED' }] }),
    })
    const { result } = renderHook(() => useSensitivityStudy(opts))

    await act(async () => {
      await result.current.handleRunStudy('thickness', [1])
    })
    await act(async () => {
      await vi.advanceTimersByTimeAsync(POLL_MS)
    })

    // The backend reports experiment-level RUNNING with a failed run; the
    // stored status must be normalised to FAILED so the UI stops showing
    // an active study.
    const lastExp = opts.setActiveExperiment.mock.calls.at(-1)?.[0] as {
      status: string
    }
    expect(lastExp.status).toBe('FAILED')
  })

  it('a terminal FAILED sweep Retry relaunches the study, not re-polls — Codex R1 P2-b', async () => {
    const opts = makeOpts()
    let runCalls = 0
    routeFetch({
      run: () => {
        runCalls += 1
        return okJson({ experiment_id: `e${runCalls}` })
      },
      // backend keeps the experiment terminal: re-polling would loop FAILED.
      status: () => okJson({ status: 'RUNNING', runs: [{ status: 'FAILED' }] }),
    })
    const { result } = renderHook(() => useSensitivityStudy(opts))

    await act(async () => {
      await result.current.handleRunStudy('thickness', [1]) // runCalls → 1
    })
    await act(async () => {
      await vi.advanceTimersByTimeAsync(POLL_MS) // poll → FAILED → surface(relaunch)
    })
    expect(opts.setUploadError).toHaveBeenCalledTimes(1)

    const onRetry = opts.setUploadError.mock.calls[0][0].onRetry as () => void
    await act(async () => {
      onRetry() // must RELAUNCH (new /run POST), not re-poll the dead experiment
    })
    expect(runCalls).toBe(2)
  })

  it('a 404 status (experiment lost) relaunches instead of re-polling forever — Codex R2 P2', async () => {
    const opts = makeOpts()
    let runCalls = 0
    routeFetch({
      run: () => {
        runCalls += 1
        return okJson({ experiment_id: `e${runCalls}` })
      },
      status: () => errJson(404), // backend lost the in-memory experiment
    })
    const { result } = renderHook(() => useSensitivityStudy(opts))

    await act(async () => {
      await result.current.handleRunStudy('thickness', [1]) // runCalls → 1
    })
    await act(async () => {
      await vi.advanceTimersByTimeAsync(POLL_MS) // poll → 404 → surface(relaunch)
    })
    expect(opts.setUploadError).toHaveBeenCalledTimes(1)

    const onRetry = opts.setUploadError.mock.calls[0][0].onRetry as () => void
    await act(async () => {
      onRetry() // relaunch (new /run), not re-poll the 404
    })
    expect(runCalls).toBe(2)
  })

  it('poll-failure Retry resumes polling rather than abandoning the study — Codex R0 P2-c', async () => {
    const opts = makeOpts()
    // Stateful status: first poll 503 (transient), resumed poll COMPLETED.
    // (Don't reassign global.fetch mid-test — that would reset the counter.)
    let statusCalls = 0
    routeFetch({
      run: () => okJson({ experiment_id: 'e1' }),
      status: () => {
        statusCalls += 1
        return statusCalls === 1
          ? errJson(503)
          : okJson({ status: 'COMPLETED', runs: [] })
      },
    })
    const { result } = renderHook(() => useSensitivityStudy(opts))

    await act(async () => {
      await result.current.handleRunStudy('thickness', [1])
    })
    await act(async () => {
      await vi.advanceTimersByTimeAsync(POLL_MS) // 1st poll → 503 → fail
    })
    expect(opts.setUploadError).toHaveBeenCalledTimes(1)

    // Clicking Retry must resume polling, not just dismiss the banner.
    const onRetry = opts.setUploadError.mock.calls[0][0].onRetry as () => void
    await act(async () => {
      onRetry()
    })
    await act(async () => {
      await vi.advanceTimersByTimeAsync(POLL_MS) // resumed poll → COMPLETED
    })

    expect(statusCalls).toBeGreaterThanOrEqual(2) // resumed → polled again
    expect(opts.onComplete).toHaveBeenCalledTimes(1) // resumed poll completed
  })
})
