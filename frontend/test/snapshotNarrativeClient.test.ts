// FM-04a Phase 6 C — Snapshot drift narrative client tests.
//
// Tier 1 engineering candidate; not signed validation; not benchmark agreement.

import { strict as assert } from 'node:assert'
import { describe, it } from 'node:test'
import {
  groupBySeverity,
  parseSnapshotNarrative,
} from '../src/snapshotNarrativeClient.ts'

describe('parseSnapshotNarrative', () => {
  it('preserves schemaVersion + template_id + severity verbatim', () => {
    const parsed = parseSnapshotNarrative({
      schema_version: '1.0.0',
      snapshot_a_label: '2026-05-16T100000Z',
      snapshot_b_label: '2026-05-16T200000Z',
      generated_at_utc: '2026-05-16T00:00:00+00:00',
      claim_tier: 'Tier 1 engineering candidate',
      claim_boundary: 'tier1_engineering_candidate; not_signed_validation',
      narratives: [
        {
          case_id: 'GS-A-candidate',
          lines: [
            {
              template_id: 'residual_velocity_delta',
              severity: 'info',
              text: 'Residual velocity changed from 75 to 80 m/s.',
            },
            {
              template_id: 'script_sha_changed',
              severity: 'warn',
              text: 'Generator script SHA-256 changed.',
            },
          ],
        },
      ],
      claim_impact: 'Tier 1 candidate; not benchmark agreement',
    })
    assert.ok(parsed)
    assert.equal(parsed!.schemaVersion, '1.0.0')
    assert.equal(parsed!.narratives.length, 1)
    assert.equal(parsed!.narratives[0].caseId, 'GS-A-candidate')
    assert.equal(parsed!.narratives[0].lines[0].templateId, 'residual_velocity_delta')
    assert.equal(parsed!.narratives[0].lines[0].severity, 'info')
    assert.equal(parsed!.narratives[0].lines[1].severity, 'warn')
  })

  it('returns null when label fields are missing', () => {
    assert.equal(parseSnapshotNarrative({ schema_version: '1.0.0' }), null)
  })

  it('drops malformed lines (missing template_id)', () => {
    const parsed = parseSnapshotNarrative({
      snapshot_a_label: '2026-05-16T100000Z',
      snapshot_b_label: '2026-05-16T200000Z',
      narratives: [
        {
          case_id: 'GS-A-candidate',
          lines: [
            { template_id: 'cohort_added', severity: 'info', text: 'ok' },
            { severity: 'warn' } as never,
          ],
        },
      ],
    })
    assert.ok(parsed)
    assert.equal(parsed!.narratives[0].lines.length, 1)
  })

  it('falls back to severity "info" for unknown severity values', () => {
    const parsed = parseSnapshotNarrative({
      snapshot_a_label: '2026-05-16T100000Z',
      snapshot_b_label: '2026-05-16T200000Z',
      narratives: [
        {
          case_id: 'GS-A-candidate',
          lines: [
            { template_id: 'unknown_thing', severity: 'CRITICAL', text: 'x' } as never,
          ],
        },
      ],
    })
    assert.ok(parsed)
    assert.equal(parsed!.narratives[0].lines[0].severity, 'info')
  })

  it('drops narrative groups missing case_id', () => {
    const parsed = parseSnapshotNarrative({
      snapshot_a_label: '2026-05-16T100000Z',
      snapshot_b_label: '2026-05-16T200000Z',
      narratives: [
        { case_id: 'GS-A-candidate', lines: [] },
        { lines: [] } as never,
      ],
    })
    assert.ok(parsed)
    assert.equal(parsed!.narratives.length, 1)
  })
})

describe('groupBySeverity', () => {
  it('partitions lines into info/warn/danger buckets', () => {
    const result = groupBySeverity([
      { templateId: 'a', severity: 'info', text: '' },
      { templateId: 'b', severity: 'warn', text: '' },
      { templateId: 'c', severity: 'danger', text: '' },
      { templateId: 'd', severity: 'info', text: '' },
    ])
    assert.equal(result.info.length, 2)
    assert.equal(result.warn.length, 1)
    assert.equal(result.danger.length, 1)
  })

  it('returns empty buckets when input is empty', () => {
    const result = groupBySeverity([])
    assert.deepEqual(result, { info: [], warn: [], danger: [] })
  })
})
