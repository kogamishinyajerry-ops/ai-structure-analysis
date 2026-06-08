// FM-04a Phase 12 I — Headless vitest for CohortSubstantiationPanel.
//
// Tier 1 engineering candidate; not signed validation; not benchmark agreement.
//
// **Load-bearing closure for slice-E TAA MEDIUM finding** (Phase 13 §2
// in the slice-G retrospective; FINAL TAA's T-axis and X-axis -1
// shared deduction). The slice-E `cohortDashboardClient.ts`
// orchestrator's defensive parsers were proven correct in
// isolation by 20 vitest cases, but the load-bearing X:-2
// anti-promotion guard ("unknown bucket MUST NOT colour as
// regressed; unknown severity MUST NOT colour as danger") was
// logically dead at the user-visible surface until a consumer
// panel rendered the orchestrator's view-model.
//
// This test pins the consumer-surface contract:
//
//   1. **`'unknown'` bucket renders neutral gray, NOT regressed
//      red** — a schema-drift bucket flows through the orchestrator
//      → view-model → panel → rendered DOM without being silently
//      promoted to `'regressed'`. The textual content shows the
//      literal string `'unknown'` (not coerced away).
//
//   2. **`'unknown'` severity renders neutral gray, NOT danger red**
//      — same anti-promotion contract on the alert row severity.
//
//   3. **Bucket distribution chips show all four bucket categories
//      (healthy / watching / regressed / unknown)** — the panel
//      surface includes the `'unknown'` count visibly so a reviewer
//      can SEE schema drift on the cohort, not have it hidden.
//
//   4. **Tier 1 disclaimer trio present** — `TIER1_BANNER` rendered
//      verbatim; no forbidden positive claim in the panel chrome.
//
//   5. **Visual deferral disclosed honestly**: this panel is the
//      consumer-side completion of the X:-2 guard; whether App.tsx
//      mounts it (and a reviewer sees it live) is a SEPARATE
//      integration concern that requires a running dev-server smoke
//      this engineering pass cannot perform. The component-level
//      contract is fully pinned here.

import { describe, it, expect, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'

import { CohortSubstantiationPanel } from '../src/components/CohortSubstantiationPanel.tsx'
import {
  bucketColor,
  severityColor,
  type CohortDashboardViewModel,
  type DashboardFetchResult,
} from '../src/cohortDashboardClient.ts'

// ---------------------------------------------------------------------
// Canonical happy-path view-model (mirrors slice-D's snapshot 1 baseline)
// ---------------------------------------------------------------------

const HAPPY_VIEW: CohortDashboardViewModel = {
  cases: [
    {
      caseId: 'cylinder-pv-candidate',
      bucket: 'healthy',
      latestTrustScore: 95,
      latestSignoffVerdict: null,
      alarmCount: 0,
    },
    {
      caseId: 'modal-cantilever-candidate',
      bucket: 'watching',
      latestTrustScore: 70,
      latestSignoffVerdict: 'watching',
      alarmCount: 1,
    },
    {
      caseId: 'cylinder-pv-extended-candidate',
      bucket: 'regressed',
      latestTrustScore: 45,
      latestSignoffVerdict: 'needs_more_evidence',
      alarmCount: 2,
    },
  ],
  alerts: [
    {
      kind: 'z_score_outlier',
      caseId: 'modal-cantilever-stiff-candidate',
      axis: 'energy_audit',
      severity: 'danger',
      rawValue: -5.12,
      rawSlope: null,
    },
    {
      kind: 'trend_slope',
      caseId: 'cylinder-pv-extended-candidate',
      axis: 'completeness',
      severity: 'warn',
      rawValue: null,
      rawSlope: -1.5,
    },
  ],
  schemaVersions: {
    cohortExecutiveSummary: '1.0.0',
    cohortAnomalies: '1.0.0',
    cohortTrendAnomalies: '1.0.0',
  },
  bucketCounts: {
    healthy: 1,
    watching: 1,
    regressed: 1,
    unknown: 0,
  },
  alarmCountTotal: 2,
  source: 'live',
}

// View-model with an UNKNOWN bucket + UNKNOWN severity flowing through.
// This is what the X:-2 anti-promotion guard MUST surface as 'unknown'
// neutral gray — NOT silently coerce to 'regressed' / 'danger'.
const SCHEMA_DRIFT_VIEW: CohortDashboardViewModel = {
  cases: [
    {
      caseId: 'future-rate-limited-candidate',
      bucket: 'unknown',
      latestTrustScore: null,
      latestSignoffVerdict: null,
      alarmCount: 0,
    },
  ],
  alerts: [
    {
      kind: 'unknown',
      caseId: 'future-sealed-drift-candidate',
      axis: 'reproducibility',
      severity: 'unknown',
      rawValue: null,
      rawSlope: null,
    },
  ],
  schemaVersions: {
    cohortExecutiveSummary: '2.0.0-future',
    cohortAnomalies: '2.0.0-future',
    cohortTrendAnomalies: '2.0.0-future',
  },
  bucketCounts: {
    healthy: 0,
    watching: 0,
    regressed: 0,
    unknown: 1,
  },
  alarmCountTotal: 1,
  source: 'live',
}

function makeFetchStub(view: CohortDashboardViewModel, errors: string[] = []) {
  return vi.fn(
    async (_apiBase: string, _signal?: AbortSignal): Promise<DashboardFetchResult> => ({
      view,
      errors,
    }),
  )
}

// ---------------------------------------------------------------------
// Happy-path render contract
// ---------------------------------------------------------------------

describe('CohortSubstantiationPanel — happy path', () => {
  it('renders the Tier 1 disclaimer + bucket distribution + case rows', async () => {
    const stub = makeFetchStub(HAPPY_VIEW)
    render(<CohortSubstantiationPanel apiBase="http://test" fetchViewModel={stub} />)

    await waitFor(() => {
      expect(screen.getByTestId('cohort-substantiation-panel')).toBeTruthy()
    })

    // Tier 1 banner present (C:-8 chrome audit).
    expect(screen.getByText(/Tier 1 engineering candidate/i)).toBeTruthy()
    expect(screen.getByText(/multi-snapshot evidence view/i)).toBeTruthy()

    // Source badge + cohort counts.
    const sourceBadge = screen.getByTestId('substantiation-source-badge')
    expect(sourceBadge.textContent).toContain('live')
    expect(sourceBadge.textContent).toContain('cases 3')
    expect(sourceBadge.textContent).toContain('alerts 2')

    // All 3 case rows rendered with bucket text.
    expect(screen.getByTestId('substantiation-case-row-cylinder-pv-candidate')).toBeTruthy()
    expect(screen.getByTestId('substantiation-case-row-modal-cantilever-candidate')).toBeTruthy()
    expect(
      screen.getByTestId('substantiation-case-row-cylinder-pv-extended-candidate'),
    ).toBeTruthy()

    // Per-case bucket badges show the bucket value verbatim.
    expect(
      screen.getByTestId('substantiation-bucket-cylinder-pv-candidate').textContent,
    ).toBe('healthy')
    expect(
      screen.getByTestId('substantiation-bucket-modal-cantilever-candidate').textContent,
    ).toBe('watching')
    expect(
      screen.getByTestId('substantiation-bucket-cylinder-pv-extended-candidate').textContent,
    ).toBe('regressed')
  })

  it('renders the bucket distribution chips for all four bucket categories', async () => {
    const stub = makeFetchStub(HAPPY_VIEW)
    render(<CohortSubstantiationPanel apiBase="http://test" fetchViewModel={stub} />)

    await waitFor(() => {
      expect(screen.getByTestId('substantiation-bucket-summary')).toBeTruthy()
    })

    // All four bucket categories rendered as chips, INCLUDING 'unknown'.
    // (X:-2 surface visibility — reviewer sees schema drift, never hidden.)
    expect(screen.getByTestId('substantiation-bucket-chip-healthy')).toBeTruthy()
    expect(screen.getByTestId('substantiation-bucket-chip-watching')).toBeTruthy()
    expect(screen.getByTestId('substantiation-bucket-chip-regressed')).toBeTruthy()
    expect(screen.getByTestId('substantiation-bucket-chip-unknown')).toBeTruthy()
  })

  it('renders alert rows with their severity values verbatim', async () => {
    const stub = makeFetchStub(HAPPY_VIEW)
    render(<CohortSubstantiationPanel apiBase="http://test" fetchViewModel={stub} />)

    await waitFor(() => {
      expect(
        screen.getByTestId('substantiation-alert-row-modal-cantilever-stiff-candidate-energy_audit'),
      ).toBeTruthy()
    })

    expect(
      screen.getByTestId(
        'substantiation-severity-modal-cantilever-stiff-candidate-energy_audit',
      ).textContent,
    ).toBe('danger')
    expect(
      screen.getByTestId('substantiation-severity-cylinder-pv-extended-candidate-completeness')
        .textContent,
    ).toBe('warn')
  })

  it('renders the 3-schema-versions footer', async () => {
    const stub = makeFetchStub(HAPPY_VIEW)
    render(<CohortSubstantiationPanel apiBase="http://test" fetchViewModel={stub} />)

    await waitFor(() => {
      const footer = screen.getByTestId('substantiation-schema-versions')
      expect(footer.textContent).toContain('exec=1.0.0')
      expect(footer.textContent).toContain('anomalies=1.0.0')
      expect(footer.textContent).toContain('trend=1.0.0')
    })
  })
})

// ---------------------------------------------------------------------
// Load-bearing X:-2 anti-promotion contract at the consumer surface
// ---------------------------------------------------------------------

describe('CohortSubstantiationPanel — X:-2 anti-promotion guards at consumer surface', () => {
  it('renders unknown bucket as neutral-gray text NOT promoted to regressed red', async () => {
    const stub = makeFetchStub(SCHEMA_DRIFT_VIEW)
    render(<CohortSubstantiationPanel apiBase="http://test" fetchViewModel={stub} />)

    await waitFor(() => {
      expect(screen.getByTestId('substantiation-case-row-future-rate-limited-candidate')).toBeTruthy()
    })

    // Bucket text says LITERALLY "unknown" — NOT "regressed".
    const bucketCell = screen.getByTestId('substantiation-bucket-future-rate-limited-candidate')
    expect(bucketCell.textContent).toBe('unknown')
    expect(bucketCell.textContent).not.toBe('regressed')

    // Bucket color matches the orchestrator's `bucketColor('unknown')`
    // SSOT (neutral gray), NOT `bucketColor('regressed')` (red).
    // This is the load-bearing X:-2 anti-promotion guard at the
    // user-visible surface: a future MINOR backend bump that
    // introduces a new bucket category lands as 'unknown' neutral,
    // never as 'regressed' false-alarm.
    const cellStyle = (bucketCell as HTMLElement).style.color
    expect(cellStyle).toBe(bucketColor('unknown'))
    expect(cellStyle).not.toBe(bucketColor('regressed'))
  })

  it('renders unknown severity as neutral-gray NOT promoted to danger red', async () => {
    const stub = makeFetchStub(SCHEMA_DRIFT_VIEW)
    render(<CohortSubstantiationPanel apiBase="http://test" fetchViewModel={stub} />)

    await waitFor(() => {
      expect(
        screen.getByTestId('substantiation-alert-row-future-sealed-drift-candidate-reproducibility'),
      ).toBeTruthy()
    })

    const severityCell = screen.getByTestId(
      'substantiation-severity-future-sealed-drift-candidate-reproducibility',
    )
    expect(severityCell.textContent).toBe('unknown')
    expect(severityCell.textContent).not.toBe('danger')

    // Severity color matches `severityColor('unknown')` SSOT, NOT
    // `severityColor('danger')` — the X:-2 anti-promotion contract on
    // the severity axis. A schema-drift severity NEVER false-alarms
    // as danger.
    const cellStyle = (severityCell as HTMLElement).style.color
    expect(cellStyle).toBe(severityColor('unknown'))
    expect(cellStyle).not.toBe(severityColor('danger'))
  })

  it('surfaces the unknown bucket count visibly in the bucket-distribution chips', async () => {
    const stub = makeFetchStub(SCHEMA_DRIFT_VIEW)
    render(<CohortSubstantiationPanel apiBase="http://test" fetchViewModel={stub} />)

    await waitFor(() => {
      expect(screen.getByTestId('substantiation-bucket-chip-unknown')).toBeTruthy()
    })

    const unknownChip = screen.getByTestId('substantiation-bucket-chip-unknown')
    // The chip's text content must include the count '1'.
    expect(unknownChip.textContent).toContain('1')
    expect(unknownChip.textContent).toContain('unknown')
    // The chip border + color use the unknown bucket color SSOT, NOT
    // the regressed-bucket red.
    expect(unknownChip.style.color).toBe(bucketColor('unknown'))
    expect(unknownChip.style.color).not.toBe(bucketColor('regressed'))
  })

  it('renders the future schema-version values in the footer (does not silently coerce them)', async () => {
    const stub = makeFetchStub(SCHEMA_DRIFT_VIEW)
    render(<CohortSubstantiationPanel apiBase="http://test" fetchViewModel={stub} />)

    await waitFor(() => {
      const footer = screen.getByTestId('substantiation-schema-versions')
      // Future-version values appear verbatim — reviewer sees "we are
      // looking at a payload from a schema version this dashboard
      // doesn't recognize" rather than silently coerced.
      expect(footer.textContent).toContain('2.0.0-future')
    })
  })
})

// ---------------------------------------------------------------------
// Loading + error states
// ---------------------------------------------------------------------

describe('CohortSubstantiationPanel — loading + degradation', () => {
  it('shows loading state then resolves to view', async () => {
    // Slow fetch — first render captures loading, await resolves.
    let resolve!: (v: DashboardFetchResult) => void
    const slowPromise = new Promise<DashboardFetchResult>((r) => {
      resolve = r
    })
    const stub = vi.fn(async () => slowPromise)
    render(<CohortSubstantiationPanel apiBase="http://test" fetchViewModel={stub} />)

    expect(screen.getByText(/loading cohort substantiation view/i)).toBeTruthy()

    resolve({ view: HAPPY_VIEW, errors: [] })
    await waitFor(() => {
      expect(screen.getByTestId('substantiation-source-badge')).toBeTruthy()
    })
  })

  it('surfaces partial-fallback errors verbatim', async () => {
    const partialView: CohortDashboardViewModel = {
      ...HAPPY_VIEW,
      source: 'partial-fallback',
    }
    const stub = makeFetchStub(partialView, [
      'summary: 503 backend unavailable',
      'anomalies: timeout',
    ])
    render(<CohortSubstantiationPanel apiBase="http://test" fetchViewModel={stub} />)

    await waitFor(() => {
      const errorsBlock = screen.getByTestId('substantiation-errors')
      expect(errorsBlock.textContent).toContain('summary: 503 backend unavailable')
      expect(errorsBlock.textContent).toContain('anomalies: timeout')
    })

    // Source badge reflects degraded state.
    expect(screen.getByTestId('substantiation-source-badge').textContent).toContain(
      'partial-fallback',
    )
  })
})
