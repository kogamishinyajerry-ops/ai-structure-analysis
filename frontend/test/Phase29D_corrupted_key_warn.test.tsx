// FM-04a Phase 29 D — corrupted localStorage payload now emits a
// console.warn (was silent in Phase 27 D — retro carry-over).
//
// Anti-gaming guard E:-1: warning is INFORMATIONAL, never throws.
// The loader still returns PROBE_LIST_INITIAL_STATE on every failure
// path; the warn is observability, not error propagation.
//
// Tier 1 / Tier 2 engineering candidate; not signed validation;
// not benchmark agreement.

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import {
  loadProbeList,
  probeListStorageKey,
  PROBE_LIST_LS_KEY_PREFIX,
} from '../src/components/probeListStorage'
import { PROBE_LIST_INITIAL_STATE } from '../src/components/probeList'

function clearAllProbeStorage() {
  const keys: string[] = []
  for (let i = 0; i < window.localStorage.length; i++) {
    const k = window.localStorage.key(i)
    if (k && k.startsWith(PROBE_LIST_LS_KEY_PREFIX)) keys.push(k)
  }
  for (const k of keys) window.localStorage.removeItem(k)
}

describe('Phase 29 D — loadProbeList console.warn on corruption', () => {
  let warnSpy: ReturnType<typeof vi.spyOn>

  beforeEach(() => {
    clearAllProbeStorage()
    warnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {})
  })
  afterEach(() => {
    clearAllProbeStorage()
    warnSpy.mockRestore()
  })

  it('missing key — NO warning (normal first-load)', () => {
    expect(loadProbeList('phase29d-no-key')).toEqual(PROBE_LIST_INITIAL_STATE)
    expect(warnSpy).not.toHaveBeenCalled()
  })

  it('malformed JSON — emits a warning with the case_id', () => {
    window.localStorage.setItem(
      probeListStorageKey('phase29d-bad-json'),
      'not{valid}json}}',
    )
    const result = loadProbeList('phase29d-bad-json')
    expect(result).toEqual(PROBE_LIST_INITIAL_STATE)
    expect(warnSpy).toHaveBeenCalledTimes(1)
    const msg = warnSpy.mock.calls[0][0] as string
    expect(msg).toContain('probeListStorage')
    expect(msg).toContain('phase29d-bad-json')
    expect(msg.toLowerCase()).toContain('malformed json')
  })

  it('wrong-shape payload — emits a warning with the case_id', () => {
    window.localStorage.setItem(
      probeListStorageKey('phase29d-bad-shape'),
      JSON.stringify({ totally: 'wrong' }),
    )
    const result = loadProbeList('phase29d-bad-shape')
    expect(result).toEqual(PROBE_LIST_INITIAL_STATE)
    expect(warnSpy).toHaveBeenCalledTimes(1)
    const msg = warnSpy.mock.calls[0][0] as string
    expect(msg).toContain('wrong-shape')
    expect(msg).toContain('phase29d-bad-shape')
  })

  it('wrong-entry-shape payload — emits a warning', () => {
    window.localStorage.setItem(
      probeListStorageKey('phase29d-bad-entry'),
      JSON.stringify({
        entries: [{ label: 'not-a-number', position: [0, 0, 0] }],
      }),
    )
    const result = loadProbeList('phase29d-bad-entry')
    expect(result).toEqual(PROBE_LIST_INITIAL_STATE)
    expect(warnSpy).toHaveBeenCalled()
  })

  it('E:-1 — warning is informational; load still returns initial state (never throws)', () => {
    window.localStorage.setItem(
      probeListStorageKey('phase29d-throw-check'),
      '][not-json',
    )
    // The call must not throw.
    expect(() => loadProbeList('phase29d-throw-check')).not.toThrow()
  })

  it('valid payload — NO warning', () => {
    window.localStorage.setItem(
      probeListStorageKey('phase29d-valid'),
      JSON.stringify({ entries: [] }),
    )
    expect(loadProbeList('phase29d-valid')).toEqual(PROBE_LIST_INITIAL_STATE)
    expect(warnSpy).not.toHaveBeenCalled()
  })
})
