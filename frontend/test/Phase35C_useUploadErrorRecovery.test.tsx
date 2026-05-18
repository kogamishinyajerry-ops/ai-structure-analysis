// FM-04a Phase 35 C — useUploadErrorRecovery hook tests.
//
// Pin the upload + case-load error-recovery surface that Phase 35 C
// extracts out of App.tsx (the same state machinery Phase 33 D tried
// to wire inline + rolled back when App.tsx tripped the <1500 LOC
// pin).
//
// Anti-gaming guards:
//   M:-1 — hook absorbs the state + retry mechanism so App.tsx can
//     mount ErrorCard with minimal LOC growth (verified separately
//     in the App.tsx LOC pin after wiring lands).
//   I:-1 — ErrorCard.tsx (Phase 18 D) is composed, not modified;
//     these tests do NOT touch the underlying ErrorCard contract.
//   D:-1 — every state transition (setUploadError / clearUploadError
//     / withRecovery success / withRecovery error / retry) has an
//     explicit test pin.

import { describe, expect, it, vi } from 'vitest'
import { act, renderHook } from '@testing-library/react'
import { useUploadErrorRecovery } from '../src/state/useUploadErrorRecovery'

describe('Phase 35 C — useUploadErrorRecovery base state', () => {
  it('starts with no error', () => {
    const { result } = renderHook(() => useUploadErrorRecovery())
    expect(result.current.state.uploadError).toBeNull()
  })

  it('exposes setUploadError / clearUploadError / withRecovery', () => {
    const { result } = renderHook(() => useUploadErrorRecovery())
    expect(typeof result.current.actions.setUploadError).toBe('function')
    expect(typeof result.current.actions.clearUploadError).toBe('function')
    expect(typeof result.current.actions.withRecovery).toBe('function')
  })
})

describe('Phase 35 C — setUploadError + clearUploadError', () => {
  it('setUploadError pushes the payload to state', () => {
    const { result } = renderHook(() => useUploadErrorRecovery())
    act(() => {
      result.current.actions.setUploadError({
        title: 'Custom failure',
        message: 'something went sideways',
      })
    })
    expect(result.current.state.uploadError).not.toBeNull()
    expect(result.current.state.uploadError?.title).toBe('Custom failure')
    expect(result.current.state.uploadError?.message).toBe('something went sideways')
  })

  it('clearUploadError resets the state to null', () => {
    const { result } = renderHook(() => useUploadErrorRecovery())
    act(() => {
      result.current.actions.setUploadError({
        title: 'x',
        message: 'y',
      })
    })
    expect(result.current.state.uploadError).not.toBeNull()
    act(() => {
      result.current.actions.clearUploadError()
    })
    expect(result.current.state.uploadError).toBeNull()
  })
})

describe('Phase 35 C — withRecovery success path', () => {
  it('returns the awaited value', async () => {
    const { result } = renderHook(() => useUploadErrorRecovery())
    const fn = vi.fn(async () => 42)
    let returned: number | undefined
    await act(async () => {
      returned = await result.current.actions.withRecovery(fn, {
        title: 'unused',
        message: 'unused',
      })
    })
    expect(returned).toBe(42)
    expect(fn).toHaveBeenCalledTimes(1)
  })

  it('does NOT surface an error when fn resolves', async () => {
    const { result } = renderHook(() => useUploadErrorRecovery())
    await act(async () => {
      await result.current.actions.withRecovery(async () => 'ok', {
        title: 'unused',
        message: 'unused',
      })
    })
    expect(result.current.state.uploadError).toBeNull()
  })

  it('clears any stale error on a successful subsequent call', async () => {
    const { result } = renderHook(() => useUploadErrorRecovery())
    act(() => {
      result.current.actions.setUploadError({
        title: 'stale',
        message: 'leftover',
      })
    })
    expect(result.current.state.uploadError).not.toBeNull()
    await act(async () => {
      await result.current.actions.withRecovery(async () => 1, {
        title: 'unused',
        message: 'unused',
      })
    })
    expect(result.current.state.uploadError).toBeNull()
  })
})

describe('Phase 35 C — withRecovery error path', () => {
  it('returns undefined when fn rejects', async () => {
    const { result } = renderHook(() => useUploadErrorRecovery())
    const consoleError = vi
      .spyOn(console, 'error')
      .mockImplementation(() => undefined)
    let returned: unknown = 'sentinel'
    await act(async () => {
      returned = await result.current.actions.withRecovery(
        async () => {
          throw new Error('boom')
        },
        { title: 'upload', message: 'failed' },
      )
    })
    expect(returned).toBeUndefined()
    consoleError.mockRestore()
  })

  it('surfaces the ErrorCard payload with title + message', async () => {
    const { result } = renderHook(() => useUploadErrorRecovery())
    const consoleError = vi
      .spyOn(console, 'error')
      .mockImplementation(() => undefined)
    await act(async () => {
      await result.current.actions.withRecovery(
        async () => {
          throw new Error('boom')
        },
        {
          title: 'Could not upload file',
          message: 'The server rejected the upload',
        },
      )
    })
    expect(result.current.state.uploadError).not.toBeNull()
    expect(result.current.state.uploadError?.title).toBe(
      'Could not upload file',
    )
    expect(result.current.state.uploadError?.message).toBe(
      'The server rejected the upload',
    )
    consoleError.mockRestore()
  })

  it('passes through remediation + code when provided', async () => {
    const { result } = renderHook(() => useUploadErrorRecovery())
    const consoleError = vi
      .spyOn(console, 'error')
      .mockImplementation(() => undefined)
    await act(async () => {
      await result.current.actions.withRecovery(
        async () => {
          throw new Error('boom')
        },
        {
          title: 'x',
          message: 'y',
          remediation: ['try smaller file', 'check network'],
          code: 'UPLOAD-500',
        },
      )
    })
    expect(result.current.state.uploadError?.remediation).toEqual([
      'try smaller file',
      'check network',
    ])
    expect(result.current.state.uploadError?.code).toBe('UPLOAD-500')
    consoleError.mockRestore()
  })

  it('logs the original error to console for dev diagnostics', async () => {
    const { result } = renderHook(() => useUploadErrorRecovery())
    const consoleError = vi
      .spyOn(console, 'error')
      .mockImplementation(() => undefined)
    const original = new Error('original-fault')
    await act(async () => {
      await result.current.actions.withRecovery(
        async () => {
          throw original
        },
        { title: 'op', message: 'failed' },
      )
    })
    expect(consoleError).toHaveBeenCalled()
    // The call records the title + the underlying error
    const [tag, err] = consoleError.mock.calls[0]
    expect(tag).toMatch(/useUploadErrorRecovery/)
    expect(tag).toMatch(/op/)
    expect(err).toBe(original)
    consoleError.mockRestore()
  })
})

describe('Phase 35 C — withRecovery retry callback', () => {
  it('attaches an onRetry callback to the ErrorCard payload', async () => {
    const { result } = renderHook(() => useUploadErrorRecovery())
    const consoleError = vi
      .spyOn(console, 'error')
      .mockImplementation(() => undefined)
    await act(async () => {
      await result.current.actions.withRecovery(
        async () => {
          throw new Error('boom')
        },
        { title: 'x', message: 'y' },
      )
    })
    expect(typeof result.current.state.uploadError?.onRetry).toBe('function')
    consoleError.mockRestore()
  })

  it('onRetry re-runs the original fn', async () => {
    const { result } = renderHook(() => useUploadErrorRecovery())
    const consoleError = vi
      .spyOn(console, 'error')
      .mockImplementation(() => undefined)
    const fn = vi
      .fn<() => Promise<string>>()
      .mockRejectedValueOnce(new Error('first attempt'))
      .mockResolvedValueOnce('second-ok')
    await act(async () => {
      await result.current.actions.withRecovery(fn, {
        title: 'op',
        message: 'failed',
      })
    })
    expect(fn).toHaveBeenCalledTimes(1)
    expect(result.current.state.uploadError).not.toBeNull()
    const retry = result.current.state.uploadError?.onRetry
    expect(retry).toBeDefined()
    await act(async () => {
      retry?.()
      // Let the in-flight withRecovery resolve.
      await Promise.resolve()
      await Promise.resolve()
    })
    expect(fn).toHaveBeenCalledTimes(2)
    consoleError.mockRestore()
  })

  it('onRetry clears the error before re-running', async () => {
    const { result } = renderHook(() => useUploadErrorRecovery())
    const consoleError = vi
      .spyOn(console, 'error')
      .mockImplementation(() => undefined)
    let pendingResolve: ((v: string) => void) | undefined
    const fn = vi
      .fn<() => Promise<string>>()
      .mockRejectedValueOnce(new Error('first attempt'))
      .mockImplementationOnce(
        () =>
          new Promise((res) => {
            pendingResolve = res
          }),
      )
    await act(async () => {
      await result.current.actions.withRecovery(fn, {
        title: 'op',
        message: 'failed',
      })
    })
    expect(result.current.state.uploadError).not.toBeNull()
    const retry = result.current.state.uploadError?.onRetry
    await act(async () => {
      retry?.()
    })
    // While the retry is pending, the previous error should have
    // cleared (so the user sees the operation restarting rather
    // than the stale error).
    expect(result.current.state.uploadError).toBeNull()
    // Settle the pending promise to avoid a hanging act.
    await act(async () => {
      pendingResolve?.('ok')
      await Promise.resolve()
    })
    consoleError.mockRestore()
  })
})
