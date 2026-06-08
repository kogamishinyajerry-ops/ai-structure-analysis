// FM-04a Phase 5 A — Schema-version pass-through audit.
//
// Tier 1 engineering candidate; not signed validation; not benchmark agreement.
//
// Enforces the Phase 5 X-axis anti-gaming guard from
// .planning/FM-04A_PHASE5_BLUEPRINT.md:
//
//   X: -2 if any frontend client silently drops `schemaVersion`
//
// Every Tier 1 candidate fetch client whose backend stamps a
// `schema_version` field MUST surface it on the parsed object as
// `schemaVersion`. A reviewer opening a Phase 5 snapshot needs to see
// which schema each captured artifact was emitted under.

import { strict as assert } from 'node:assert'
import { describe, it } from 'vitest'
import { parseAcceptancePacket } from '../src/acceptancePacketClient.ts'
import { parseArchivedPacketDiff } from '../src/archivedPacketDiffClient.ts'
import { parseCaseComparison } from '../src/caseComparisonClient.ts'
import { parseCaseCompletenessScore } from '../src/caseCompletenessClient.ts'
import { parseCohortOverview } from '../src/cohortOverviewClient.ts'
import { parseConvergenceStudy } from '../src/convergenceStudyClient.ts'

describe('schema_version pass-through (X-axis anti-gaming guard)', () => {
  it('acceptance packet preserves schema_version on parsed payload', () => {
    const parsed = parseAcceptancePacket({
      schema_version: '1.0.0',
      case_id: 'GS-102-x-guard',
      claim_tier: 'Tier 1 engineering candidate',
      claim_boundary:
        'tier1_engineering_candidate; not_signed_validation; not_benchmark_agreement',
    })
    assert.ok(parsed)
    assert.equal(parsed!.schemaVersion, '1.0.0')
  })

  it('case completeness preserves schema_version AND rubric_version', () => {
    const parsed = parseCaseCompletenessScore({
      schema_version: '1.0.0',
      rubric_version: '1.0.0',
      case_id: 'GS-102-x-guard',
    })
    assert.ok(parsed)
    assert.equal(parsed!.schemaVersion, '1.0.0')
    assert.equal(parsed!.rubricVersion, '1.0.0')
  })

  it('cohort overview preserves schema_version', () => {
    const parsed = parseCohortOverview({
      schema_version: '1.0.0',
      entries: [],
      cohort_count: 0,
    })
    assert.ok(parsed)
    assert.equal(parsed!.schemaVersion, '1.0.0')
  })

  it('case comparison preserves schema_version', () => {
    const parsed = parseCaseComparison({
      schema_version: '1.0.0',
      case_a: 'GS-A',
      case_b: 'GS-B',
    })
    assert.ok(parsed)
    assert.equal(parsed!.schemaVersion, '1.0.0')
  })

  it('archived packet diff preserves schema_version', () => {
    const parsed = parseArchivedPacketDiff({
      schema_version: '1.0.0',
      archive_a: { case_id: 'GS-A' },
      archive_b: { case_id: 'GS-B' },
    })
    assert.ok(parsed)
    assert.equal(parsed!.schemaVersion, '1.0.0')
  })

  it('convergence study preserves schema_version', () => {
    const parsed = parseConvergenceStudy({
      schema_version: '1.0.0',
      case_id: 'GS-102-x-guard',
    })
    assert.ok(parsed)
    assert.equal(parsed!.schemaVersion, '1.0.0')
  })

  it('missing schema_version surfaces as empty string, not as crash', () => {
    // Forward-compat: an older snapshot taken before Phase 5 A will
    // not carry the field. The client must not crash; it must surface
    // an empty string so the UI can flag "schema version unknown".
    const parsed = parseAcceptancePacket({
      case_id: 'GS-pre-phase5',
    })
    assert.ok(parsed)
    assert.equal(parsed!.schemaVersion, '')
  })
})
