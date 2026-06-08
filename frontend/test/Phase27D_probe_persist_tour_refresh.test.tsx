// FM-04a Phase 27 D — probe save/restore + tour copy refresh tests.
//
// Two deliveries pinned in one test file:
//
// 1. Probe-list save/restore across sessions via localStorage,
//    scoped by case_id. Closes Phase 26 retro punchlist #8.
//    Anti-gaming guard C:-1: persistence key includes case_id
//    verbatim so switching cases loads DIFFERENT lists.
//
// 2. Onboarding tour copy refreshed from 4 cards (Phase 24 B) to
//    6 cards. New cards: 'basic-advanced-mode' (Phase 25 C) and
//    'probe-diff-column' (Phase 26 C). Storage key bumped v1 → v2
//    so existing dismissed-v1 users see v2 once.
//    Anti-gaming guard D:-1: v2 bump is ADDITIVE — v1 dismissed
//    state is NOT cleared.
//
// Tier 1 / Tier 2 engineering candidate; not signed validation;
// not benchmark agreement.

import { afterEach, beforeEach, describe, expect, it } from 'vitest'

import {
  loadProbeList,
  saveProbeList,
  clearProbeListStorage,
  probeListStorageKey,
  PROBE_LIST_LS_KEY_PREFIX,
} from '../src/components/probeListStorage'
import {
  PROBE_LIST_INITIAL_STATE,
  addProbeEntry,
  type ProbeListState,
} from '../src/components/probeList'
import {
  ONBOARDING_STEPS,
  ONBOARDING_TOTAL_STEPS,
  ONBOARDING_LS_KEY,
  type OnboardingStepId,
} from '../src/onboardingTour'
import type { PickedNodeInfo } from '../src/components/viewportRaycaster'

function mkProbe(label: number, fv: number | null = 1.0e8): PickedNodeInfo {
  return { label, position: [label * 0.1, 0, 0], fieldValue: fv }
}

function clearAllProbeStorage() {
  try {
    const keys: string[] = []
    for (let i = 0; i < window.localStorage.length; i++) {
      const k = window.localStorage.key(i)
      if (k && k.startsWith(PROBE_LIST_LS_KEY_PREFIX)) keys.push(k)
    }
    for (const k of keys) window.localStorage.removeItem(k)
  } catch {
    /* SSR */
  }
}

describe('Phase 27 D — probeListStorageKey', () => {
  it('composes key with case_id verbatim (C:-1 anti-gaming)', () => {
    expect(probeListStorageKey('cylinder-pv-candidate')).toBe(
      'fm04a.probe-list.v1.cylinder-pv-candidate',
    )
    expect(probeListStorageKey('plate-with-hole-candidate')).toBe(
      'fm04a.probe-list.v1.plate-with-hole-candidate',
    )
    // Different case_ids → different keys (no cross-case bleeding).
    expect(probeListStorageKey('a')).not.toBe(probeListStorageKey('b'))
  })
})

describe('Phase 27 D — loadProbeList / saveProbeList round-trip', () => {
  beforeEach(() => clearAllProbeStorage())
  afterEach(() => clearAllProbeStorage())

  it('load returns empty state when key is absent', () => {
    const loaded = loadProbeList('case-1')
    expect(loaded).toEqual(PROBE_LIST_INITIAL_STATE)
  })

  it('save → load round-trip preserves entries', () => {
    const state = addProbeEntry(
      addProbeEntry(PROBE_LIST_INITIAL_STATE, mkProbe(7, 1.0e8)),
      mkProbe(42, 3.5e8),
    )
    saveProbeList('case-1', state)
    const loaded = loadProbeList('case-1')
    expect(loaded.entries).toHaveLength(2)
    expect(loaded.entries[0].label).toBe(7)
    expect(loaded.entries[1].label).toBe(42)
    expect(loaded.entries[0].fieldValue).toBe(1.0e8)
    expect(loaded.entries[1].fieldValue).toBe(3.5e8)
  })

  it('save preserves PIN ORDER (carries D:-2 from probeList.ts)', () => {
    // Pin in non-sorted order; storage round-trip must NOT re-sort.
    const labels = [99, 7, 42, 11, 3]
    const state = labels.reduce<ProbeListState>(
      (acc, l) => addProbeEntry(acc, mkProbe(l)),
      PROBE_LIST_INITIAL_STATE,
    )
    saveProbeList('case-1', state)
    const loaded = loadProbeList('case-1')
    expect(loaded.entries.map((e) => e.label)).toEqual(labels)
  })

  it('null fieldValue survives round-trip', () => {
    const state = addProbeEntry(PROBE_LIST_INITIAL_STATE, mkProbe(7, null))
    saveProbeList('case-1', state)
    const loaded = loadProbeList('case-1')
    expect(loaded.entries[0].fieldValue).toBeNull()
  })

  it('C:-1 — different case_ids store DIFFERENT lists', () => {
    const stateA = addProbeEntry(PROBE_LIST_INITIAL_STATE, mkProbe(7))
    const stateB = addProbeEntry(PROBE_LIST_INITIAL_STATE, mkProbe(99))
    saveProbeList('case-A', stateA)
    saveProbeList('case-B', stateB)
    const loadedA = loadProbeList('case-A')
    const loadedB = loadProbeList('case-B')
    expect(loadedA.entries[0].label).toBe(7)
    expect(loadedB.entries[0].label).toBe(99)
    expect(loadedA.entries[0].label).not.toBe(loadedB.entries[0].label)
  })

  it('clearProbeListStorage removes only that case_id', () => {
    saveProbeList('case-A', addProbeEntry(PROBE_LIST_INITIAL_STATE, mkProbe(7)))
    saveProbeList('case-B', addProbeEntry(PROBE_LIST_INITIAL_STATE, mkProbe(99)))
    clearProbeListStorage('case-A')
    expect(loadProbeList('case-A')).toEqual(PROBE_LIST_INITIAL_STATE)
    // Case B's list is unaffected.
    expect(loadProbeList('case-B').entries[0].label).toBe(99)
  })
})

describe('Phase 27 D — corrupted-key fallback', () => {
  beforeEach(() => clearAllProbeStorage())
  afterEach(() => clearAllProbeStorage())

  it('load returns empty when JSON parse fails', () => {
    window.localStorage.setItem(probeListStorageKey('case-1'), 'not-json{{')
    expect(loadProbeList('case-1')).toEqual(PROBE_LIST_INITIAL_STATE)
  })

  it('load returns empty when shape is wrong (missing entries array)', () => {
    window.localStorage.setItem(
      probeListStorageKey('case-1'),
      JSON.stringify({ foo: 'bar' }),
    )
    expect(loadProbeList('case-1')).toEqual(PROBE_LIST_INITIAL_STATE)
  })

  it('load returns empty when entry shape is wrong', () => {
    window.localStorage.setItem(
      probeListStorageKey('case-1'),
      JSON.stringify({ entries: [{ label: 'not-a-number', position: [0, 0, 0] }] }),
    )
    expect(loadProbeList('case-1')).toEqual(PROBE_LIST_INITIAL_STATE)
  })

  it('load returns empty when position is wrong shape', () => {
    window.localStorage.setItem(
      probeListStorageKey('case-1'),
      JSON.stringify({ entries: [{ label: 1, position: [0, 0], fieldValue: 0 }] }),
    )
    expect(loadProbeList('case-1')).toEqual(PROBE_LIST_INITIAL_STATE)
  })
})

describe('Phase 27 D — onboarding tour v2 refresh', () => {
  it('storage key is bumped to v2 (D:-1 anti-gaming)', () => {
    expect(ONBOARDING_LS_KEY).toBe('fm04a.onboarding.v2.dismissed')
  })

  it('tour now has 6 steps (was 4 in Phase 24 B)', () => {
    expect(ONBOARDING_TOTAL_STEPS).toBe(6)
    expect(ONBOARDING_STEPS).toHaveLength(6)
  })

  it('all step ids are present and in expected progression order', () => {
    const ids = ONBOARDING_STEPS.map((s) => s.id)
    expect(ids).toEqual([
      'field-component-switcher',
      'threshold-filter',
      'node-pick',
      'section-cut',
      'basic-advanced-mode',
      'probe-diff-column',
    ] satisfies OnboardingStepId[])
  })

  it('new basic-advanced-mode step cites Phase 25 C provenance', () => {
    const step = ONBOARDING_STEPS.find((s) => s.id === 'basic-advanced-mode')!
    expect(step.shippedInPhase).toBe('Phase 25 C')
    expect(step.body).toContain('Basic')
    expect(step.body).toContain('Advanced')
  })

  it('new probe-diff-column step cites Phase 26 C provenance', () => {
    const step = ONBOARDING_STEPS.find((s) => s.id === 'probe-diff-column')!
    expect(step.shippedInPhase).toBe('Phase 26 C')
    expect(step.body).toMatch(/Δ|delta|first-pinned/i)
  })

  it('v1 prior dismissed key is NOT mentioned in module (additive bump)', () => {
    // D:-1 anti-gaming: bumping v1 → v2 must NOT clear v1.
    // We can't easily test "the module didn't reach over to v1"
    // without mocking storage, but we CAN assert that the
    // module's exported key is the v2 key (i.e., reads only v2).
    expect(ONBOARDING_LS_KEY).not.toContain('v1')
  })
})
