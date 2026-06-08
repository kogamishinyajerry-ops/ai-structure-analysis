// FM-04a Phase 5 B — Reproducibility manifest client tests.
//
// Tier 1 engineering candidate; not signed validation; not benchmark agreement.

import { strict as assert } from 'node:assert'
import { describe, it } from 'vitest'
import {
  gitStateLabel,
  parseReproducibilityManifest,
  shortenCommit,
} from '../src/reproducibilityManifestClient.ts'

describe('parseReproducibilityManifest', () => {
  it('parses a complete payload and preserves schemaVersion', () => {
    const parsed = parseReproducibilityManifest({
      schema_version: '1.0.0',
      case_id: 'GS-102-candidate',
      generated_at_utc: '2026-05-16T00:00:00+00:00',
      claim_tier: 'Tier 1 engineering candidate',
      claim_boundary:
        'tier1_engineering_candidate; not_signed_validation; not_benchmark_agreement',
      git_commit_sha: 'abcdef0123456789abcdef0123456789abcdef01',
      git_branch: 'claude/FM-04a-tier1-ballistic-candidate',
      git_dirty: true,
      python_version: '3.11.15',
      python_implementation: 'CPython',
      platform_summary: 'macOS-15.0-arm64',
      tracked_packages: [
        { name: 'fastapi', version: '0.118.3' },
        { name: 'numpy', version: '2.2.1' },
      ],
      scripts: [
        {
          relpath: 'scripts/gen_gs102_deck.py',
          sha256: 'a'.repeat(64),
          bytes: 4096,
        },
      ],
      tier2_blockers_remaining: ['FM-04b P8 sealed packet'],
      claim_impact: 'Tier 1 candidate; not benchmark agreement',
    })
    assert.ok(parsed)
    assert.equal(parsed!.schemaVersion, '1.0.0')
    assert.equal(parsed!.caseId, 'GS-102-candidate')
    assert.equal(parsed!.gitCommitSha, 'abcdef0123456789abcdef0123456789abcdef01')
    assert.equal(parsed!.gitDirty, true)
    assert.equal(parsed!.trackedPackages.length, 2)
    assert.equal(parsed!.trackedPackages[0].name, 'fastapi')
    assert.equal(parsed!.scripts.length, 1)
    assert.equal(parsed!.scripts[0].bytes, 4096)
  })

  it('returns null when case_id is missing', () => {
    const parsed = parseReproducibilityManifest({ schema_version: '1.0.0' })
    assert.equal(parsed, null)
  })

  it('returns null on non-object payloads', () => {
    assert.equal(parseReproducibilityManifest(null), null)
    assert.equal(parseReproducibilityManifest(undefined), null)
  })

  it('tolerates missing optional fields without crashing', () => {
    const parsed = parseReproducibilityManifest({
      case_id: 'GS-pre-phase5',
    })
    assert.ok(parsed)
    assert.equal(parsed!.schemaVersion, '')
    assert.equal(parsed!.gitCommitSha, null)
    assert.equal(parsed!.gitBranch, null)
    assert.equal(parsed!.gitDirty, false)
    assert.deepEqual(parsed!.trackedPackages, [])
    assert.deepEqual(parsed!.scripts, [])
  })

  it('filters out malformed scripts but keeps valid ones', () => {
    const parsed = parseReproducibilityManifest({
      case_id: 'GS-102-candidate',
      scripts: [
        { relpath: 'scripts/ok.py', sha256: 'b'.repeat(64), bytes: 12 },
        { relpath: 'scripts/no-hash.py' }, // missing sha256 -> dropped
        null, // dropped
      ] as never,
    })
    assert.ok(parsed)
    assert.equal(parsed!.scripts.length, 1)
    assert.equal(parsed!.scripts[0].relpath, 'scripts/ok.py')
  })

  it('filters out packages without a name', () => {
    const parsed = parseReproducibilityManifest({
      case_id: 'GS-102-candidate',
      tracked_packages: [
        { name: 'fastapi', version: '0.118.3' },
        { version: '1.2.3' } as never,
      ],
    })
    assert.ok(parsed)
    assert.equal(parsed!.trackedPackages.length, 1)
    assert.equal(parsed!.trackedPackages[0].name, 'fastapi')
  })
})

describe('shortenCommit', () => {
  it('returns "unknown" when sha is null', () => {
    assert.equal(shortenCommit(null), 'unknown')
  })

  it('truncates a full sha to 7 chars', () => {
    assert.equal(shortenCommit('abcdef0123456789'), 'abcdef0')
  })

  it('returns short shas as-is', () => {
    assert.equal(shortenCommit('abc'), 'abc')
  })
})

describe('gitStateLabel', () => {
  it('surfaces "git state unavailable" when commit is null', () => {
    const label = gitStateLabel({
      schemaVersion: '1.0.0',
      caseId: 'GS-102-candidate',
      generatedAtUtc: '',
      claimTier: '',
      claimBoundary: '',
      gitCommitSha: null,
      gitBranch: null,
      gitDirty: false,
      pythonVersion: '',
      pythonImplementation: '',
      platformSummary: '',
      trackedPackages: [],
      scripts: [],
      tier2BlockersRemaining: [],
      claimImpact: '',
    })
    assert.equal(label, 'git state unavailable')
  })

  it('marks a dirty working tree explicitly', () => {
    const label = gitStateLabel({
      schemaVersion: '1.0.0',
      caseId: 'GS-102-candidate',
      generatedAtUtc: '',
      claimTier: '',
      claimBoundary: '',
      gitCommitSha: 'abcdef0123456789',
      gitBranch: 'main',
      gitDirty: true,
      pythonVersion: '',
      pythonImplementation: '',
      platformSummary: '',
      trackedPackages: [],
      scripts: [],
      tier2BlockersRemaining: [],
      claimImpact: '',
    })
    assert.equal(label, 'main@abcdef0 (dirty)')
  })

  it('omits "(dirty)" when working tree is clean', () => {
    const label = gitStateLabel({
      schemaVersion: '1.0.0',
      caseId: 'GS-102-candidate',
      generatedAtUtc: '',
      claimTier: '',
      claimBoundary: '',
      gitCommitSha: 'abcdef0123456789',
      gitBranch: 'main',
      gitDirty: false,
      pythonVersion: '',
      pythonImplementation: '',
      platformSummary: '',
      trackedPackages: [],
      scripts: [],
      tier2BlockersRemaining: [],
      claimImpact: '',
    })
    assert.equal(label, 'main@abcdef0')
  })
})
