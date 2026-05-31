// FM-04a Phase 45 A — UI density (comfortable | compact) toggle (additive).
//
// Tier 1 engineering candidate; not signed validation. Covers the useDensity
// hook + storage discipline (mirrors useColumnLayout's pattern) and the
// DensityToggle control. NO getComputedStyle / pixel assertions — the visual
// compression (token rescale) is integration scope; here we pin the state
// machine, the localStorage round-trip, and the data-density attribute the hook
// applies to document.documentElement.

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { renderHook, act, render, screen, fireEvent } from '@testing-library/react'

import {
  validateDensity,
  createDensityStorage,
  useDensity,
  DENSITY_LS_KEY,
  DEFAULT_DENSITY,
  DENSITY_ORDER,
} from '../src/state/useDensity'
import { DensityToggle } from '../src/components/DensityToggle'

beforeEach(() => {
  try {
    window.localStorage.clear()
  } catch {
    /* SSR fallback */
  }
  document.documentElement.removeAttribute('data-density')
})
afterEach(() => {
  vi.restoreAllMocks()
  document.documentElement.removeAttribute('data-density')
})

// ── Validator + defaults (pins) ──────────────────────────────────────────────
describe('Phase 45 A — density validator + defaults', () => {
  it('validateDensity passes the two valid values verbatim', () => {
    expect(validateDensity('comfortable')).toBe('comfortable')
    expect(validateDensity('compact')).toBe('compact')
  })
  it('validateDensity coerces anything malformed to the default', () => {
    for (const bad of [null, undefined, 42, 'garbage', {}, [], true]) {
      expect(validateDensity(bad)).toBe(DEFAULT_DENSITY)
    }
  })
  it('defaults + key are pinned (comfortable = no change on upgrade)', () => {
    expect(DEFAULT_DENSITY).toBe('comfortable')
    expect(DENSITY_LS_KEY).toBe('fm04a.ui.density.v1')
    expect(DENSITY_ORDER).toEqual(['comfortable', 'compact'])
  })
})

// ── Storage adapter ──────────────────────────────────────────────────────────
describe('Phase 45 A — createDensityStorage', () => {
  it('round-trips a saved value through a FRESH adapter', () => {
    createDensityStorage(globalThis).save('compact')
    expect(createDensityStorage(globalThis).load()).toBe('compact')
    createDensityStorage(globalThis).save('comfortable')
    expect(createDensityStorage(globalThis).load()).toBe('comfortable')
  })
  it('an absent key → default (a 44A/B user upgrades cleanly)', () => {
    expect(createDensityStorage(globalThis).load()).toBe('comfortable')
  })
  it('corrupt JSON → default (never throws)', () => {
    window.localStorage.setItem(DENSITY_LS_KEY, 'not-json{')
    expect(createDensityStorage(globalThis).load()).toBe('comfortable')
  })
  it('SSR adapter (no localStorage) loads the default and save is a no-op', () => {
    const s = createDensityStorage({} as typeof globalThis)
    expect(s.load()).toBe('comfortable')
    expect(() => s.save('compact')).not.toThrow()
  })
})

// ── Hook behaviour ───────────────────────────────────────────────────────────
describe('Phase 45 A — useDensity hook', () => {
  it('starts comfortable and applies data-density to <html> via the effect', () => {
    const { result } = renderHook(() => useDensity())
    expect(result.current.density).toBe('comfortable')
    expect(document.documentElement.getAttribute('data-density')).toBe('comfortable')
  })
  it('setDensity flips state, the attribute, and persists', () => {
    const { result } = renderHook(() => useDensity())
    act(() => result.current.setDensity('compact'))
    expect(result.current.density).toBe('compact')
    expect(document.documentElement.getAttribute('data-density')).toBe('compact')
    expect(JSON.parse(window.localStorage.getItem(DENSITY_LS_KEY) as string)).toBe('compact')
  })
  it('hot-start: a persisted compact value is read on mount', () => {
    window.localStorage.setItem(DENSITY_LS_KEY, JSON.stringify('compact'))
    const { result } = renderHook(() => useDensity())
    expect(result.current.density).toBe('compact')
    expect(document.documentElement.getAttribute('data-density')).toBe('compact')
  })
  it('cycleDensity steps comfortable → compact → comfortable', () => {
    const { result } = renderHook(() => useDensity())
    act(() => result.current.cycleDensity())
    expect(result.current.density).toBe('compact')
    act(() => result.current.cycleDensity())
    expect(result.current.density).toBe('comfortable')
  })
})

// ── DensityToggle control ────────────────────────────────────────────────────
describe('Phase 45 A — DensityToggle control', () => {
  it('renders both segments; the active one is aria-pressed', () => {
    render(<DensityToggle density="comfortable" onChange={vi.fn()} />)
    expect(screen.getByTestId('topbar-density-toggle')).toBeInTheDocument()
    expect(screen.getByTestId('density-opt-comfortable')).toHaveAttribute('aria-pressed', 'true')
    expect(screen.getByTestId('density-opt-compact')).toHaveAttribute('aria-pressed', 'false')
  })
  it('clicking a segment calls onChange with that density', () => {
    const onChange = vi.fn()
    render(<DensityToggle density="comfortable" onChange={onChange} />)
    fireEvent.click(screen.getByTestId('density-opt-compact'))
    expect(onChange).toHaveBeenCalledWith('compact')
  })
})
