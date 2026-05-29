// FM-04a Phase 41.4 — useBootCaseSelect onboarding auto-show policy.
//
// Pins the Codex R0 P2 ×2 fixes: the first-visit tour/promo auto-show must
// never flash over the boot 3D hero (P2 #2) and must never re-arm during an
// upload/report session that has cleared activeCaseId (P2 #1) — while still
// surfacing on the genuine no-case landing (reachability).

import { describe, expect, it, vi } from 'vitest'
import { renderHook } from '@testing-library/react'
import { useBootCaseSelect } from '../src/state/useBootCaseSelect'
import type { CaseMetadata } from '../src/types/AppTypes'

const mkCase = (id: string): CaseMetadata => ({ id }) as CaseMetadata
const BOOT = 'GS-102-candidate'
const cases = [mkCase('GS-001'), mkCase(BOOT)]

function gates(args: {
  available: CaseMetadata[]
  activeCaseId: string | null
  sessionActive: boolean
  preferred: string | null
  casesLoaded: boolean
}): { tourAutoShow: boolean; promoAutoShow: boolean } {
  const onSelect = vi.fn()
  const { result } = renderHook(() =>
    useBootCaseSelect(
      args.available,
      args.activeCaseId,
      args.sessionActive,
      args.preferred,
      onSelect,
      args.casesLoaded,
    ),
  )
  return result.current
}

describe('useBootCaseSelect — tour auto-show policy', () => {
  it('is HIDDEN before /cases resolves (no pre-load flash)', () => {
    expect(
      gates({ available: [], activeCaseId: null, sessionActive: false, preferred: BOOT, casesLoaded: false }).tourAutoShow,
    ).toBe(false)
  })

  it('is HIDDEN when the preferred boot case is available (boot pending — Codex R0 P2 #2)', () => {
    // Even though activeCaseId is still null in the paint before the effect
    // auto-selects, a boot IS pending, so the overlay must not flash.
    expect(
      gates({ available: cases, activeCaseId: null, sessionActive: false, preferred: BOOT, casesLoaded: true }).tourAutoShow,
    ).toBe(false)
  })

  it('is HIDDEN during an upload/report session that cleared activeCaseId (Codex R0 P2 #1)', () => {
    expect(
      gates({ available: cases, activeCaseId: null, sessionActive: true, preferred: BOOT, casesLoaded: true }).tourAutoShow,
    ).toBe(false)
  })

  it('is HIDDEN when a case is already open', () => {
    expect(
      gates({ available: cases, activeCaseId: BOOT, sessionActive: false, preferred: BOOT, casesLoaded: true }).tourAutoShow,
    ).toBe(false)
  })

  it('is SHOWN on the genuine no-case landing (cases loaded, none on disk)', () => {
    expect(
      gates({ available: [], activeCaseId: null, sessionActive: false, preferred: BOOT, casesLoaded: true }).tourAutoShow,
    ).toBe(true)
  })

  it('is SHOWN when the preferred case is absent from the loaded list (no boot pending)', () => {
    expect(
      gates({
        available: [mkCase('GS-001'), mkCase('GS-002')],
        activeCaseId: null,
        sessionActive: false,
        preferred: BOOT,
        casesLoaded: true,
      }).tourAutoShow,
    ).toBe(true)
  })
})

describe('useBootCaseSelect — promo auto-show policy (Codex R1 P2 #1: stays reachable)', () => {
  it('is HIDDEN during the boot first-paint flash window', () => {
    // boot pending (preferred available, no active case) → no flash over the hero
    expect(
      gates({ available: cases, activeCaseId: null, sessionActive: false, preferred: BOOT, casesLoaded: true }).promoAutoShow,
    ).toBe(false)
  })

  it('is HIDDEN before /cases resolves and during an upload session', () => {
    expect(
      gates({ available: [], activeCaseId: null, sessionActive: false, preferred: BOOT, casesLoaded: false }).promoAutoShow,
    ).toBe(false)
    expect(
      gates({ available: cases, activeCaseId: null, sessionActive: true, preferred: BOOT, casesLoaded: true }).promoAutoShow,
    ).toBe(false)
  })

  it('is REACHABLE once the boot case has settled (does not stay permanently suppressed)', () => {
    expect(
      gates({ available: cases, activeCaseId: BOOT, sessionActive: false, preferred: BOOT, casesLoaded: true }).promoAutoShow,
    ).toBe(true)
  })

  it('is REACHABLE on the genuine no-case landing', () => {
    expect(
      gates({ available: [], activeCaseId: null, sessionActive: false, preferred: BOOT, casesLoaded: true }).promoAutoShow,
    ).toBe(true)
  })

  it('still auto-selects the preferred boot case exactly once (selection unchanged)', () => {
    const onSelect = vi.fn()
    const { rerender } = renderHook(
      ({ loaded }: { loaded: boolean }) =>
        useBootCaseSelect(cases, null, false, BOOT, onSelect, loaded),
      { initialProps: { loaded: true } },
    )
    rerender({ loaded: true })
    expect(onSelect).toHaveBeenCalledTimes(1)
    expect(onSelect).toHaveBeenCalledWith(expect.objectContaining({ id: BOOT }))
  })
})
