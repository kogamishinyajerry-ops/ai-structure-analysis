// FM-04a Phase 12 E — defensive cohort-dashboard client parsers.
//
// Tier 1 engineering candidate; not signed validation; not benchmark agreement.
//
// Pins the slice-E anti-gaming guards from
// `.planning/FM-04A_PHASE12_BLUEPRINT.md` §3.E:
//
//   X:-2  unknown-bucket / unknown-severity / unknown-alert-kind ALL
//         fall back to the literal string "unknown" instead of the
//         most-conservative existing value (which would silently mask
//         schema drift in the UI).
//   M:-2  the three SSOT tuples (DASHBOARD_BUCKETS / DASHBOARD_SEVERITIES
//         / DASHBOARD_ALERT_KINDS) are pinned; adding a new bucket /
//         severity / kind must update the tuple in lockstep.
//   E:-2  view model degrades gracefully on partial-fallback (any 1-2
//         of the 3 backend surfaces failing must still produce a
//         renderable view model, just flagged as `source: "partial-fallback"`).

import { describe, expect, it, vi } from 'vitest'
import {
  DASHBOARD_ALERT_KINDS,
  DASHBOARD_BUCKETS,
  DASHBOARD_SEVERITIES,
  bucketColor,
  defensiveAlertKind,
  defensiveBucket,
  defensiveSeverity,
  fetchCohortDashboardViewModel,
  severityColor,
  type CohortDashboardViewModel,
} from '../src/cohortDashboardClient.ts'

// ----------------------------------------------------------------------
// SSOT tuple pins
// ----------------------------------------------------------------------


describe('DASHBOARD_BUCKETS SSOT', () => {
  it('contains exactly 4 buckets including unknown fallback', () => {
    expect(DASHBOARD_BUCKETS).toEqual([
      'healthy',
      'watching',
      'regressed',
      'unknown',
    ])
  })
})

describe('DASHBOARD_SEVERITIES SSOT', () => {
  it('contains exactly 4 severities including unknown fallback', () => {
    expect(DASHBOARD_SEVERITIES).toEqual(['info', 'warn', 'danger', 'unknown'])
  })
})

describe('DASHBOARD_ALERT_KINDS SSOT', () => {
  it('contains exactly 4 kinds including unknown fallback', () => {
    expect(DASHBOARD_ALERT_KINDS).toEqual([
      'z_score_outlier',
      'trend_slope',
      'rate_limit',
      'unknown',
    ])
  })
})

// ----------------------------------------------------------------------
// Defensive parser X:-2 anti-gaming guard
// ----------------------------------------------------------------------

describe('defensiveBucket', () => {
  it('passes through every documented bucket value verbatim', () => {
    expect(defensiveBucket('healthy')).toBe('healthy')
    expect(defensiveBucket('watching')).toBe('watching')
    expect(defensiveBucket('regressed')).toBe('regressed')
  })
  it('falls back to "unknown" on undefined / null / empty / typo', () => {
    expect(defensiveBucket(undefined)).toBe('unknown')
    expect(defensiveBucket(null)).toBe('unknown')
    expect(defensiveBucket('')).toBe('unknown')
    expect(defensiveBucket('helthy')).toBe('unknown')
    expect(defensiveBucket('REGRESSED')).toBe('unknown')
  })
})

describe('defensiveSeverity', () => {
  it('passes through every documented severity verbatim', () => {
    expect(defensiveSeverity('info')).toBe('info')
    expect(defensiveSeverity('warn')).toBe('warn')
    expect(defensiveSeverity('danger')).toBe('danger')
  })
  it('falls back to "unknown" (NOT "danger") on out-of-enum input', () => {
    expect(defensiveSeverity(undefined)).toBe('unknown')
    expect(defensiveSeverity('critical')).toBe('unknown')
    expect(defensiveSeverity('WARN')).toBe('unknown')
    // The load-bearing rule: unknown severity does NOT promote to
    // danger (would spuriously fire the dashboard danger banner).
    expect(defensiveSeverity('catastrophic')).not.toBe('danger')
  })
})

describe('defensiveAlertKind', () => {
  it('passes through every documented kind verbatim', () => {
    expect(defensiveAlertKind('z_score_outlier')).toBe('z_score_outlier')
    expect(defensiveAlertKind('trend_slope')).toBe('trend_slope')
    expect(defensiveAlertKind('rate_limit')).toBe('rate_limit')
  })
  it('falls back to "unknown" on out-of-enum input', () => {
    expect(defensiveAlertKind(undefined)).toBe('unknown')
    expect(defensiveAlertKind('z-score')).toBe('unknown')
    expect(defensiveAlertKind('future_alarm_kind')).toBe('unknown')
  })
})

// ----------------------------------------------------------------------
// Color tokens — neutral fallback for unknown
// ----------------------------------------------------------------------

describe('bucketColor', () => {
  it('maps each documented bucket to a distinct color token', () => {
    const colors = new Set([
      bucketColor('healthy'),
      bucketColor('watching'),
      bucketColor('regressed'),
    ])
    expect(colors.size).toBe(3)
  })
  it('maps "unknown" to a neutral color token (NOT a danger token)', () => {
    const unknownColor = bucketColor('unknown')
    expect(unknownColor).not.toBe(bucketColor('regressed'))
    expect(unknownColor).not.toBe(bucketColor('healthy'))
  })
})

describe('severityColor', () => {
  it('maps each documented severity to a distinct color token', () => {
    const colors = new Set([
      severityColor('info'),
      severityColor('warn'),
      severityColor('danger'),
    ])
    expect(colors.size).toBe(3)
  })
  it('maps "unknown" severity to a neutral color (NOT danger)', () => {
    expect(severityColor('unknown')).not.toBe(severityColor('danger'))
  })
})

// ----------------------------------------------------------------------
// View-model builder degradation modes
// ----------------------------------------------------------------------


function stubFetchSequence(responses: (object | { status: number })[]) {
  const queue = [...responses]
  global.fetch = vi.fn(async () => {
    const r = queue.shift()
    if (!r) throw new Error('stubFetchSequence: queue exhausted')
    if ('status' in r) {
      return {
        ok: r.status >= 200 && r.status < 300,
        status: r.status,
        json: async () => ({}),
      } as Response
    }
    return { ok: true, status: 200, json: async () => r } as Response
  })
}


const EXEC_OK = {
  schema_version: '1.0.0',
  generated_at_utc: '2026-05-16T00:00:00+00:00',
  claim_tier: 'Tier 1 engineering candidate',
  claim_boundary: 'tier1_engineering_candidate; not_signed_validation; not_benchmark_agreement',
  cohort_count: 1,
  healthy_count: 1,
  watching_count: 0,
  regressed_count: 0,
  cases: [
    {
      case_id: 'modal-cantilever-candidate',
      latest_trust_score: 96,
      latest_snapshot_label: '2026-05-16T120000Z',
      latest_signoff_verdict: null,
      alarm_count_warn_or_danger: 0,
      bucket: 'healthy',
    },
  ],
  claim_impact: 'Tier 1 candidate cohort scorecard only.',
}

const ANOM_OK = {
  schema_version: '1.0.0',
  generated_at_utc: '2026-05-16T00:00:00+00:00',
  claim_tier: 'Tier 1 engineering candidate',
  claim_boundary: 'tier1_engineering_candidate; not_signed_validation; not_benchmark_agreement',
  cohort_count: 6,
  anomaly_count: 1,
  anomalies: [
    {
      case_id: 'modal-cantilever-stiff-candidate',
      axis: 'energy_audit',
      score: 0,
      cohort_mean: 12.5,
      cohort_stdev: 5.59,
      z_score: -2.236,
      severity: 'info',
    },
  ],
  claim_impact: 'Tier 1 candidate cohort statistical outliers only.',
}

const TREND_OK = {
  schema_version: '1.0.0',
  generated_at_utc: '2026-05-16T00:00:00+00:00',
  claim_tier: 'Tier 1 engineering candidate',
  claim_boundary: 'tier1_engineering_candidate; not_signed_validation; not_benchmark_agreement',
  cohort_count: 6,
  point_count_floor: 3,
  anomaly_count: 1,
  anomalies: [
    {
      case_id: 'cylinder-pv-extended-candidate',
      axis: 'completeness',
      slope: -6.0,
      point_count: 3,
      severity: 'danger',
    },
  ],
  claim_impact: 'Tier 1 candidate trend slope alarms only.',
}

describe('fetchCohortDashboardViewModel', () => {
  it('builds a live view model when all 3 surfaces respond OK', async () => {
    stubFetchSequence([EXEC_OK, ANOM_OK, TREND_OK])
    const { view, errors } = await fetchCohortDashboardViewModel('/api/v1')
    expect(view.source).toBe('live')
    expect(errors).toEqual([])
    expect(view.cases).toHaveLength(1)
    expect(view.cases[0].caseId).toBe('modal-cantilever-candidate')
    expect(view.cases[0].bucket).toBe('healthy')
    // 1 z-score + 1 trend = 2 alerts.
    expect(view.alerts).toHaveLength(2)
    expect(view.alarmCountTotal).toBe(2)
    // Schema footprint surfaces all three versions.
    expect(view.schemaVersions.cohortExecutiveSummary).toBe('1.0.0')
    expect(view.schemaVersions.cohortAnomalies).toBe('1.0.0')
    expect(view.schemaVersions.cohortTrendAnomalies).toBe('1.0.0')
  })

  it('degrades to partial-fallback when one of 3 surfaces 5xx-errors', async () => {
    stubFetchSequence([EXEC_OK, ANOM_OK, { status: 500 }])
    const { view, errors } = await fetchCohortDashboardViewModel('/api/v1')
    expect(view.source).toBe('partial-fallback')
    expect(errors.length).toBeGreaterThan(0)
    // Trend surface unavailable → no trend alerts in the view.
    const trendAlerts = view.alerts.filter((a) => a.kind === 'trend_slope')
    expect(trendAlerts).toEqual([])
    // The executive + anomalies surfaces still populated.
    expect(view.cases).toHaveLength(1)
    const zAlerts = view.alerts.filter((a) => a.kind === 'z_score_outlier')
    expect(zAlerts).toHaveLength(1)
  })

  it('degrades to fallback when all 3 surfaces error', async () => {
    stubFetchSequence([{ status: 500 }, { status: 500 }, { status: 500 }])
    const { view, errors } = await fetchCohortDashboardViewModel('/api/v1')
    expect(view.source).toBe('fallback')
    expect(errors.length).toBe(3)
    expect(view.cases).toEqual([])
    expect(view.alerts).toEqual([])
    // Schema versions all carry the 'unknown' literal.
    expect(view.schemaVersions.cohortExecutiveSummary).toBe('unknown')
    expect(view.schemaVersions.cohortAnomalies).toBe('unknown')
    expect(view.schemaVersions.cohortTrendAnomalies).toBe('unknown')
  })

  it('surfaces unknown bucket when the backend payload carries an unrecognized value', async () => {
    const drifted = {
      ...EXEC_OK,
      cases: [
        {
          ...EXEC_OK.cases[0],
          bucket: 'panicking',  // future-schema drift
        },
      ],
    }
    stubFetchSequence([drifted, ANOM_OK, TREND_OK])
    const { view } = await fetchCohortDashboardViewModel('/api/v1')
    // The bucket in the parsed view IS "unknown" via the defensive parser,
    // not silently coerced to "regressed" (which the underlying client
    // does). The dashboard client re-parses and surfaces drift.
    const c = view.cases[0]
    expect(c.bucket).toBe('unknown')
  })

  it('surfaces unknown severity when the backend payload carries an unrecognized severity', async () => {
    const drifted = {
      ...ANOM_OK,
      anomalies: [
        {
          ...ANOM_OK.anomalies[0],
          severity: 'catastrophic',  // future-schema drift
        },
      ],
    }
    stubFetchSequence([EXEC_OK, drifted, TREND_OK])
    const { view } = await fetchCohortDashboardViewModel('/api/v1')
    const drift = view.alerts.find((a) => a.kind === 'z_score_outlier')
    expect(drift).toBeDefined()
    // The dashboard surfaces unknown severity, not the underlying
    // client's 'info' fallback (which would silently downgrade a
    // post-danger drift to invisibility).
    expect(drift?.severity).toBe('unknown')
  })

  it('counts buckets across the four dashboard buckets (including unknown)', async () => {
    const mixed = {
      ...EXEC_OK,
      cohort_count: 4,
      cases: [
        { ...EXEC_OK.cases[0], case_id: 'A', bucket: 'healthy' },
        { ...EXEC_OK.cases[0], case_id: 'B', bucket: 'watching' },
        { ...EXEC_OK.cases[0], case_id: 'C', bucket: 'regressed' },
        { ...EXEC_OK.cases[0], case_id: 'D', bucket: 'unobserved' },  // drift
      ],
    }
    stubFetchSequence([mixed, ANOM_OK, TREND_OK])
    const { view } = await fetchCohortDashboardViewModel('/api/v1')
    expect(view.bucketCounts.healthy).toBe(1)
    expect(view.bucketCounts.watching).toBe(1)
    expect(view.bucketCounts.regressed).toBe(1)
    expect(view.bucketCounts.unknown).toBe(1)
    // Sum equals cohort.
    const sum =
      view.bucketCounts.healthy +
      view.bucketCounts.watching +
      view.bucketCounts.regressed +
      view.bucketCounts.unknown
    expect(sum).toBe(view.cases.length)
  })
})

// ----------------------------------------------------------------------
// Tier 1 disclaimer envelope audit (C:-8 inherited)
// ----------------------------------------------------------------------

describe('Tier 1 disclaimer trio preserved', () => {
  it('every alert payload carries case_id + axis + bucketed severity', async () => {
    stubFetchSequence([EXEC_OK, ANOM_OK, TREND_OK])
    const { view } = await fetchCohortDashboardViewModel('/api/v1')
    for (const alert of view.alerts) {
      expect(typeof alert.caseId).toBe('string')
      expect(alert.caseId).not.toBe('')
      expect(typeof alert.axis).toBe('string')
      expect(DASHBOARD_SEVERITIES).toContain(alert.severity)
    }
  })
})

// Type-only sanity: ensure CohortDashboardViewModel exists at compile
// time (this test is more about TS inference than runtime behavior).
const _typecheck: CohortDashboardViewModel | null = null
void _typecheck
