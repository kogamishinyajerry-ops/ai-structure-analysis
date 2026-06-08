// FM-04a Phase 5 C/D — Cohort snapshot client tests.
//
// Tier 1 engineering candidate; not signed validation; not benchmark agreement.

import { strict as assert } from 'node:assert'
import { describe, it } from 'vitest'
import {
  parseCohortSnapshotDiff,
  parseSnapshotListing,
  snapshotLabelIsValid,
  summarizeCompletenessDrift,
  summarizeReproDrift,
} from '../src/cohortSnapshotClient.ts'

describe('parseSnapshotListing', () => {
  it('preserves schemaVersion and returns ordered entries', () => {
    const parsed = parseSnapshotListing({
      schema_version: '1.0.0',
      generated_at_utc: '2026-05-16T00:00:00+00:00',
      claim_tier: 'Tier 1 engineering candidate',
      claim_boundary: 'tier1_engineering_candidate; not_signed_validation',
      snapshot_count: 2,
      snapshots: [
        {
          schema_version: '1.0.0',
          snapshot_label: '2026-05-16T200000Z',
          captured_at_utc: '2026-05-16T20:00:00+00:00',
          claim_tier: 'Tier 1 engineering candidate',
          claim_boundary: 'tier1_engineering_candidate',
          cohort_count: 2,
          cases: ['GS-A-candidate', 'GS-B-candidate'],
          reviewer_bundle_written: true,
        },
        {
          schema_version: '1.0.0',
          snapshot_label: '2026-05-16T100000Z',
          captured_at_utc: '2026-05-16T10:00:00+00:00',
          claim_tier: 'Tier 1 engineering candidate',
          claim_boundary: 'tier1_engineering_candidate',
          cohort_count: 1,
          cases: ['GS-A-candidate'],
          reviewer_bundle_written: false,
        },
      ],
      claim_impact: 'Tier 1 candidate; not benchmark agreement',
    })
    assert.ok(parsed)
    assert.equal(parsed!.schemaVersion, '1.0.0')
    assert.equal(parsed!.snapshotCount, 2)
    assert.equal(parsed!.snapshots[0].snapshotLabel, '2026-05-16T200000Z')
    assert.equal(parsed!.snapshots[0].cohortCount, 2)
    assert.equal(parsed!.snapshots[1].reviewerBundleWritten, false)
  })

  it('filters out entries without a label', () => {
    const parsed = parseSnapshotListing({
      snapshots: [
        { snapshot_label: '2026-05-16T200000Z' },
        { cohort_count: 1 } as never,
      ],
    })
    assert.ok(parsed)
    assert.equal(parsed!.snapshots.length, 1)
  })

  it('returns null for non-object payloads', () => {
    assert.equal(parseSnapshotListing(null), null)
  })
})

describe('parseCohortSnapshotDiff', () => {
  it('preserves schemaVersion + every drift signal', () => {
    const parsed = parseCohortSnapshotDiff({
      schema_version: '1.0.0',
      generated_at_utc: '2026-05-16T00:00:00+00:00',
      claim_tier: 'Tier 1 engineering candidate',
      claim_boundary: 'tier1_engineering_candidate',
      snapshot_a_label: '2026-05-16T100000Z',
      snapshot_b_label: '2026-05-16T200000Z',
      a_cohort_count: 2,
      b_cohort_count: 3,
      cohort_added: ['GS-C-candidate'],
      cohort_removed: [],
      cohort_shared: ['GS-A-candidate', 'GS-B-candidate'],
      completeness_deltas: [
        { case_id: 'GS-A-candidate', a_score: 80, b_score: 85, delta: 5 },
        { case_id: 'GS-B-candidate', a_score: 70, b_score: 65, delta: -5 },
      ],
      reproducibility_deltas: [
        {
          case_id: 'GS-A-candidate',
          a_git_sha: 'a'.repeat(40),
          b_git_sha: 'b'.repeat(40),
          git_sha_changed: true,
          a_git_dirty: false,
          b_git_dirty: true,
          dirty_changed: true,
          a_python_version: '3.11.15',
          b_python_version: '3.11.16',
          python_version_changed: true,
          package_version_changes: [
            { name: 'fastapi', a_version: '0.118.0', b_version: '0.119.0' },
          ],
          script_sha_changes: [
            { relpath: 'scripts/gen.py', a_sha256: 'aa'.repeat(32), b_sha256: 'bb'.repeat(32) },
          ],
        },
      ],
      claim_impact: 'Tier 1 candidate cohort snapshot diff only; not benchmark agreement',
    })
    assert.ok(parsed)
    assert.equal(parsed!.schemaVersion, '1.0.0')
    assert.equal(parsed!.cohortAdded.length, 1)
    assert.equal(parsed!.completenessDeltas[0].delta, 5)
    assert.equal(parsed!.completenessDeltas[1].delta, -5)
    assert.equal(parsed!.reproducibilityDeltas[0].gitShaChanged, true)
    assert.equal(parsed!.reproducibilityDeltas[0].packageVersionChanges[0].name, 'fastapi')
    assert.equal(parsed!.reproducibilityDeltas[0].scriptShaChanges[0].relpath, 'scripts/gen.py')
  })

  it('returns null when label fields are missing', () => {
    assert.equal(parseCohortSnapshotDiff({ schema_version: '1.0.0' }), null)
  })

  it('filters malformed delta entries', () => {
    const parsed = parseCohortSnapshotDiff({
      snapshot_a_label: '2026-05-16T100000Z',
      snapshot_b_label: '2026-05-16T200000Z',
      completeness_deltas: [
        { case_id: 'GS-A-candidate', a_score: 80, b_score: 85, delta: 5 },
        { a_score: 70 } as never,
      ],
      reproducibility_deltas: [
        { a_git_sha: 'a' } as never, // missing case_id
      ],
    })
    assert.ok(parsed)
    assert.equal(parsed!.completenessDeltas.length, 1)
    assert.equal(parsed!.reproducibilityDeltas.length, 0)
  })
})

describe('snapshotLabelIsValid', () => {
  it('accepts canonical UTC labels', () => {
    assert.equal(snapshotLabelIsValid('2026-05-16T120000Z'), true)
  })

  it('rejects malformed labels', () => {
    assert.equal(snapshotLabelIsValid('2026-05-16'), false)
    assert.equal(snapshotLabelIsValid('not-a-label'), false)
    assert.equal(snapshotLabelIsValid(''), false)
  })
})

describe('summarizeCompletenessDrift', () => {
  it('counts improvements, regressions, and unchanged', () => {
    const summary = summarizeCompletenessDrift({
      schemaVersion: '1.0.0',
      generatedAtUtc: '',
      claimTier: '',
      claimBoundary: '',
      snapshotALabel: '2026-05-16T100000Z',
      snapshotBLabel: '2026-05-16T200000Z',
      aCohortCount: 4,
      bCohortCount: 4,
      cohortAdded: [],
      cohortRemoved: [],
      cohortShared: ['a', 'b', 'c', 'd'],
      completenessDeltas: [
        { caseId: 'a', aScore: 80, bScore: 90, delta: 10 },
        { caseId: 'b', aScore: 80, bScore: 70, delta: -10 },
        { caseId: 'c', aScore: 80, bScore: 80, delta: 0 },
        { caseId: 'd', aScore: null, bScore: 80, delta: null },
      ],
      reproducibilityDeltas: [],
      claimImpact: '',
    })
    assert.equal(summary.improved, 1)
    assert.equal(summary.regressed, 1)
    assert.equal(summary.unchanged, 1)
  })
})

describe('summarizeReproDrift', () => {
  it('counts git/python/script drift independently', () => {
    const summary = summarizeReproDrift({
      schemaVersion: '1.0.0',
      generatedAtUtc: '',
      claimTier: '',
      claimBoundary: '',
      snapshotALabel: '2026-05-16T100000Z',
      snapshotBLabel: '2026-05-16T200000Z',
      aCohortCount: 2,
      bCohortCount: 2,
      cohortAdded: [],
      cohortRemoved: [],
      cohortShared: ['a', 'b'],
      completenessDeltas: [],
      reproducibilityDeltas: [
        {
          caseId: 'a',
          aGitSha: null,
          bGitSha: null,
          gitShaChanged: true,
          aGitDirty: null,
          bGitDirty: null,
          dirtyChanged: false,
          aPythonVersion: null,
          bPythonVersion: null,
          pythonVersionChanged: true,
          packageVersionChanges: [],
          scriptShaChanges: [
            { relpath: 'scripts/x.py', aSha256: null, bSha256: null },
          ],
        },
        {
          caseId: 'b',
          aGitSha: null,
          bGitSha: null,
          gitShaChanged: false,
          aGitDirty: null,
          bGitDirty: null,
          dirtyChanged: false,
          aPythonVersion: null,
          bPythonVersion: null,
          pythonVersionChanged: false,
          packageVersionChanges: [],
          scriptShaChanges: [],
        },
      ],
      claimImpact: '',
    })
    assert.equal(summary.gitChanged, 1)
    assert.equal(summary.pythonChanged, 1)
    assert.equal(summary.scriptsChanged, 1)
  })
})
