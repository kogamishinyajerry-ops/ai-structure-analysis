/**
 * FM-04a Phase 38 H — the offline fallback registry must cover the whole
 * on-disk cohort (act-on #3).
 *
 * Eval-fleet finding #3 (Phase 38 E): FALLBACK_CANDIDATE_CASES carried only
 * 7 of the 24 `golden_samples/*-candidate/` directories, so 17 cohort cases
 * were invisible whenever `/api/v1/candidate-cases` was unreachable. This
 * test is the DRIFT GUARD that keeps the static list honest: it reads the
 * actual on-disk cohort and fails loudly if the two ever diverge again. When
 * it fails after a new case lands, re-run
 * `scripts/gen_fallback_candidate_registry.py` and paste the new block in.
 *
 * Tier 1 / Tier 2 engineering candidate; not signed validation; not benchmark
 * agreement.
 */

import { describe, expect, it } from 'vitest'
import { existsSync, readdirSync, statSync } from 'fs'
import { resolve } from 'path'

import { FALLBACK_CANDIDATE_CASES } from '../src/candidateCaseRegistry'

const REPO_ROOT = resolve(__dirname, '..', '..')
const GOLDEN = resolve(REPO_ROOT, 'golden_samples')

// Same admission rule as the backend route (candidate_cases.py): a directory
// whose name ends in `-candidate` and matches the candidate id shape. The
// `^GS-\d{3}$` signed registry never matches `-candidate`, so it is excluded
// here exactly as the read-only endpoint excludes it.
const CASE_ID_RE = /^[A-Za-z0-9_-]+-candidate$/

function onDiskCandidateDirs(): string[] {
  return readdirSync(GOLDEN)
    .filter((name) => {
      if (!name.endsWith('-candidate')) return false
      if (!CASE_ID_RE.test(name)) return false
      return statSync(resolve(GOLDEN, name)).isDirectory()
    })
    .sort()
}

describe('FALLBACK_CANDIDATE_CASES cohort coverage (Phase 38 H — eval #3)', () => {
  const fallbackIds = new Set(FALLBACK_CANDIDATE_CASES.map((c) => c.caseId))
  const diskDirs = onDiskCandidateDirs()

  it('covers EVERY on-disk *-candidate directory (no case invisible offline)', () => {
    const missing = diskDirs.filter((dir) => !fallbackIds.has(dir))
    expect(
      missing,
      `on-disk cohort cases absent from the offline fallback (re-run ` +
        `scripts/gen_fallback_candidate_registry.py): ${missing.join(', ')}`,
    ).toEqual([])
  })

  it('has NO phantom entries (every fallback case exists on disk)', () => {
    const diskSet = new Set(diskDirs)
    const phantom = FALLBACK_CANDIDATE_CASES.map((c) => c.caseId).filter(
      (id) => !diskSet.has(id),
    )
    expect(
      phantom,
      `fallback entries with no golden_samples/<id>/ directory: ${phantom.join(', ')}`,
    ).toEqual([])
  })

  it('count matches the on-disk cohort exactly', () => {
    expect(FALLBACK_CANDIDATE_CASES.length).toBe(diskDirs.length)
  })

  it('no Tier-2 over-claim: every "Tier 2" entry has a verdict file on disk', () => {
    // Tier 2 requires a real-solver cross-check verdict. Necessary-condition
    // guard against a fabricated promotion in the static list (the backend
    // _claim_tier SSOT additionally gates on registry membership + PASS).
    const overclaim = FALLBACK_CANDIDATE_CASES.filter(
      (c) =>
        c.claimTier.includes('Tier 2') &&
        !existsSync(
          resolve(GOLDEN, c.caseId, 'cross_check_verdict.yaml'),
        ),
    ).map((c) => c.caseId)
    expect(
      overclaim,
      `entries labelled Tier 2 with no cross_check_verdict.yaml: ${overclaim.join(', ')}`,
    ).toEqual([])
  })

  it('keeps the App.tsx default-selection anchors stable at indices 0 and 1', () => {
    // App.tsx seeds selectedCaseId / comparisonCaseA from FALLBACK[0] and
    // comparisonCaseB from FALLBACK[1]. Appending new cases must not disturb
    // these, so pin them explicitly (a future --all regen would reorder).
    expect(FALLBACK_CANDIDATE_CASES[0]?.caseId).toBe('GS-102-candidate')
    expect(FALLBACK_CANDIDATE_CASES[1]?.caseId).toBe('GS-102-refined-candidate')
  })
})
