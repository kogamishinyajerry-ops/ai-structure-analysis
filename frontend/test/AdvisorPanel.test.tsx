// FM-04a Phase 11 E — headless smoke for AdvisorPanel + typed client.
//
// Tier 1 engineering candidate; not signed validation; not benchmark agreement.
//
// Pins binding rubric (anti-gaming guards) from
// `.planning/FM-04A_PHASE11_BLUEPRINT.md` section 4 — slice E subset:
//
//  * **M:-2 / X:-2**: the frontend ADVISOR_STATUS_TUPLE +
//    FOUR_QUESTION_GATE_KEYS + ADVISOR_FORBIDDEN_TOKENS pin the
//    backend SSOT byte-for-byte; the parser falls back to `'unknown'`
//    on a value not in the tuple so a future MINOR backend bump
//    cannot crash the panel.
//  * **C:-8**: every rendered payload carries the Tier 1 disclaimer
//    trio AND the panel client-side-audits each concern entry before
//    rendering (defense in depth on top of the backend audit).
//  * **A:-3**: a forbidden-positive-claim entry that somehow reached
//    the panel (proxy injection, MITM, etc.) is suppressed with a
//    visible marker rather than silently rendered.

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { AdvisorPanel } from '../src/components/AdvisorPanel.tsx'
import {
  ADVISOR_FORBIDDEN_TOKENS,
  ADVISOR_STATUS_TUPLE,
  FOUR_QUESTION_GATE_KEYS,
  isAdvisorEntrySafe,
  parseAdvisorCritique,
  parseAdvisorStatus,
} from '../src/advisorCritiqueClient.ts'

// ------------------------------------------------------------------
// canonical happy-path payload
// ------------------------------------------------------------------

const HAPPY_BODY = {
  schema_version: '1.0.0',
  case_id: 'cylinder-pv-candidate',
  snapshot_label: '2026-05-16T120000Z',
  advisor_status: 'stub',
  advisor_backend: 'stub-rule-based',
  generated_at_utc: '2026-05-16T12:00:00+00:00',
  four_question_gate: {
    llm_offline_ok: true,
    artifacts_user_owned: true,
    trustgate_explains: true,
    advisor_only: true,
  },
  mesh_quality_concerns: ['mesh density looks adequate for the gradient'],
  boundary_condition_questions: ['is the closed-end assumption load-cycle-safe?'],
  failure_modes_to_consider: [
    'Linear static analysis is BLIND to: plasticity, contact separation',
  ],
  unhandled_load_cases: ['Reviewer: enumerate the load cases NOT analyzed'],
  degrade_reason: null,
  claim_tier: 'Tier 1 engineering candidate',
  claim_boundary:
    'tier1_engineering_candidate; not_signed_validation; not_benchmark_agreement',
  claim_impact:
    'Tier 1 candidate AI advisor critique; not signed validation; not benchmark agreement.',
}

function stubFetch(body: unknown, ok = true, status = 200) {
  global.fetch = vi.fn().mockResolvedValue({
    ok,
    status,
    json: async () => body,
  } as Response)
}

// ------------------------------------------------------------------
// SSOT tuple pins (M:-2 / X:-2)
// ------------------------------------------------------------------

describe('ADVISOR_STATUS_TUPLE frontend SSOT', () => {
  it('matches the backend tuple exactly', () => {
    expect(ADVISOR_STATUS_TUPLE).toEqual(['online', 'offline', 'stub'])
  })
})

describe('FOUR_QUESTION_GATE_KEYS frontend SSOT', () => {
  it('matches the backend tuple exactly', () => {
    expect(FOUR_QUESTION_GATE_KEYS).toEqual([
      'llm_offline_ok',
      'artifacts_user_owned',
      'trustgate_explains',
      'advisor_only',
    ])
  })
})

describe('ADVISOR_FORBIDDEN_TOKENS frontend mirror', () => {
  it('contains the Phase-11 advisor-specific additions', () => {
    expect(ADVISOR_FORBIDDEN_TOKENS).toContain('production ready')
    expect(ADVISOR_FORBIDDEN_TOKENS).toContain('certified')
    expect(ADVISOR_FORBIDDEN_TOKENS).toContain('approved for service')
    expect(ADVISOR_FORBIDDEN_TOKENS).toContain('asme compliant')
    expect(ADVISOR_FORBIDDEN_TOKENS).toContain('signed off')
  })
  it('contains the Tier 1 base list as well', () => {
    expect(ADVISOR_FORBIDDEN_TOKENS).toContain('validated against')
    expect(ADVISOR_FORBIDDEN_TOKENS).toContain('validated physics')
  })
})

// ------------------------------------------------------------------
// Defensive parser pins
// ------------------------------------------------------------------

describe('parseAdvisorStatus defensive coercion', () => {
  it('returns unknown for undefined / unknown values', () => {
    expect(parseAdvisorStatus(undefined)).toBe('unknown')
    expect(parseAdvisorStatus('some_future_status')).toBe('unknown')
  })

  it('round-trips every member of ADVISOR_STATUS_TUPLE', () => {
    for (const status of ADVISOR_STATUS_TUPLE) {
      expect(parseAdvisorStatus(status)).toBe(status)
    }
  })
})

describe('parseAdvisorCritique defensive parser', () => {
  it('rejects null / non-object input', () => {
    expect(parseAdvisorCritique(null)).toBeNull()
    expect(parseAdvisorCritique(undefined)).toBeNull()
  })

  it('rejects payload missing case_id', () => {
    expect(
      parseAdvisorCritique({
        snapshot_label: 'x',
      } as Parameters<typeof parseAdvisorCritique>[0]),
    ).toBeNull()
  })

  it('falls back to unknown advisor_status for values not in the tuple', () => {
    const parsed = parseAdvisorCritique({
      ...HAPPY_BODY,
      advisor_status: 'some_future_status',
    })
    expect(parsed).not.toBeNull()
    expect(parsed!.advisorStatus).toBe('unknown')
  })

  it('coerces a pre-Phase-11 payload missing the new keys into a valid critique', () => {
    // A 0.x-era payload may not have four_question_gate / degrade_reason
    // — the parser must NOT crash; it defaults to {}, null, [], '' as
    // appropriate (forward-compat with frontend updates).
    const parsed = parseAdvisorCritique({
      case_id: 'cylinder-pv-candidate',
      snapshot_label: '2026-05-16T120000Z',
    } as Parameters<typeof parseAdvisorCritique>[0])
    expect(parsed).not.toBeNull()
    expect(parsed!.fourQuestionGate).toEqual({})
    expect(parsed!.meshQualityConcerns).toEqual([])
    expect(parsed!.degradeReason).toBeNull()
    expect(parsed!.advisorStatus).toBe('unknown')
  })
})

// ------------------------------------------------------------------
// Client-side preview audit (defense in depth — A:-3)
// ------------------------------------------------------------------

describe('isAdvisorEntrySafe client-side audit', () => {
  it('allows entries with no forbidden token', () => {
    expect(isAdvisorEntrySafe('mesh density looks adequate')).toBe(true)
  })

  it('refuses each ADVISOR_FORBIDDEN_TOKENS entry outside not-claim form', () => {
    for (const token of ADVISOR_FORBIDDEN_TOKENS) {
      expect(isAdvisorEntrySafe(`This design is ${token}.`)).toBe(false)
    }
  })

  it('allows the not-<claim> disclaimer form (case-folded)', () => {
    expect(isAdvisorEntrySafe('This is not certified for service.')).toBe(true)
    // Audit case-folds the haystack first, so 'NOT ' becomes 'not ' and
    // the disclaimer prefix matches. This is INTENTIONAL — a maintainer
    // capitalizing the disclaimer must not break the audit.
    expect(isAdvisorEntrySafe('NOT production ready.')).toBe(true)
  })

  it('is case-insensitive (catches mixed-case ASME Compliant)', () => {
    expect(isAdvisorEntrySafe('This part is ASME Compliant.')).toBe(false)
  })
})

// ------------------------------------------------------------------
// AdvisorPanel render smoke
// ------------------------------------------------------------------

describe('AdvisorPanel', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('renders all 4 content sections + status badge + gate checklist on happy path', async () => {
    stubFetch(HAPPY_BODY)
    render(
      <AdvisorPanel
        apiBase="/api/v1"
        caseId="cylinder-pv-candidate"
        snapshotLabel="2026-05-16T120000Z"
      />,
    )
    await waitFor(() => {
      expect(screen.getByTestId('advisor-status-badge')).toBeInTheDocument()
    })
    expect(screen.getByTestId('advisor-mesh-concerns')).toBeInTheDocument()
    expect(screen.getByTestId('advisor-bc-questions')).toBeInTheDocument()
    expect(screen.getByTestId('advisor-failure-modes')).toBeInTheDocument()
    expect(screen.getByTestId('advisor-unhandled-loads')).toBeInTheDocument()
    expect(screen.getByTestId('advisor-gate-checklist')).toBeInTheDocument()
    // All 4 gate keys rendered, each with a green tick on the happy path.
    for (const key of FOUR_QUESTION_GATE_KEYS) {
      expect(screen.getByTestId(`advisor-gate-${key}`)).toBeInTheDocument()
    }
  })

  it('renders the Tier 1 disclaimer trio in the footer', async () => {
    stubFetch(HAPPY_BODY)
    render(
      <AdvisorPanel
        apiBase="/api/v1"
        caseId="cylinder-pv-candidate"
        snapshotLabel="2026-05-16T120000Z"
      />,
    )
    await waitFor(() => {
      const footer = screen.getByTestId('advisor-claim-footer')
      expect(footer.textContent).toContain('Tier 1 engineering candidate')
      expect(footer.textContent).toContain('not_signed_validation')
      expect(footer.textContent).toContain('not_benchmark_agreement')
    })
  })

  it('renders the offline status banner with a degrade_reason', async () => {
    const offlineBody = {
      ...HAPPY_BODY,
      advisor_status: 'offline',
      advisor_backend: 'llm-advisor-anthropic-unwired',
      degrade_reason: "provider 'llm-advisor-anthropic-unwired' is_available() == False",
    }
    stubFetch(offlineBody)
    render(
      <AdvisorPanel
        apiBase="/api/v1"
        caseId="cylinder-pv-candidate"
        snapshotLabel="2026-05-16T120000Z"
      />,
    )
    await waitFor(() => {
      const banner = screen.getByTestId('advisor-degrade-reason')
      expect(banner.textContent).toContain('is_available')
    })
  })

  it('suppresses an entry containing a forbidden positive claim (client-side defense in depth)', async () => {
    const tainted = {
      ...HAPPY_BODY,
      mesh_quality_concerns: [
        'This part is production ready for service.', // forbidden
        'mesh density looks adequate', // safe
      ],
    }
    stubFetch(tainted)
    render(
      <AdvisorPanel
        apiBase="/api/v1"
        caseId="cylinder-pv-candidate"
        snapshotLabel="2026-05-16T120000Z"
      />,
    )
    await waitFor(() => {
      const tainted0 = screen.getByTestId('advisor-mesh-concerns-item-0')
      expect(tainted0.getAttribute('data-safe')).toBe('false')
      expect(tainted0.textContent).toContain('suppressed')
      const safe1 = screen.getByTestId('advisor-mesh-concerns-item-1')
      expect(safe1.getAttribute('data-safe')).toBe('true')
      expect(safe1.textContent).toContain('mesh density')
    })
  })

  it('renders an error banner when the fetch fails', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 500,
      json: async () => ({}),
    } as Response)
    render(
      <AdvisorPanel
        apiBase="/api/v1"
        caseId="cylinder-pv-candidate"
        snapshotLabel="2026-05-16T120000Z"
      />,
    )
    await waitFor(() => {
      expect(screen.getByTestId('advisor-panel-error')).toBeInTheDocument()
    })
  })

  it('renders unknown-status badge when backend ships a future MINOR-bump value', async () => {
    stubFetch({ ...HAPPY_BODY, advisor_status: 'some_future_status' })
    render(
      <AdvisorPanel
        apiBase="/api/v1"
        caseId="cylinder-pv-candidate"
        snapshotLabel="2026-05-16T120000Z"
      />,
    )
    await waitFor(() => {
      const badge = screen.getByTestId('advisor-status-badge')
      // The badge text comes from _STATUS_LABEL['unknown'] — does not
      // silently surface 'online' (X:-2).
      expect(badge.textContent).toContain('frontend out of date')
    })
  })
})

// ------------------------------------------------------------------
// Phase 13 A — refused_claims surface
// ------------------------------------------------------------------

describe('AdvisorPanel — Phase 13 A refused_claims surface', () => {
  it('does NOT render the refused-claims section when refused_claims is empty', async () => {
    // HAPPY_BODY has no refused_claims field → parsed to empty array.
    stubFetch(HAPPY_BODY)
    render(
      <AdvisorPanel
        apiBase="/api/v1"
        caseId="cylinder-pv-candidate"
        snapshotLabel="2026-05-16T120000Z"
      />,
    )
    await waitFor(() => {
      expect(screen.getByTestId('advisor-claim-footer')).toBeInTheDocument()
    })
    // The refused-claims section is conditionally mounted; expect
    // it to be absent on a clean envelope.
    expect(screen.queryByTestId('advisor-refused-claims')).toBeNull()
  })

  it('parses pre-1.1.0 payloads (no refused_claims field) as empty list (back-compat)', async () => {
    // Explicitly strip the field to simulate a pre-1.1.0 producer.
    const pre110 = { ...HAPPY_BODY }
    stubFetch(pre110)
    render(
      <AdvisorPanel
        apiBase="/api/v1"
        caseId="cylinder-pv-candidate"
        snapshotLabel="2026-05-16T120000Z"
      />,
    )
    await waitFor(() => {
      expect(screen.getByTestId('advisor-claim-footer')).toBeInTheDocument()
    })
    expect(screen.queryByTestId('advisor-refused-claims')).toBeNull()
  })

  it('renders the refused-claims section with count when refused_claims has entries', async () => {
    stubFetch({
      ...HAPPY_BODY,
      schema_version: '1.1.0',
      refused_claims: ['refused: production ready', 'refused: signed off'],
    })
    render(
      <AdvisorPanel
        apiBase="/api/v1"
        caseId="cylinder-pv-candidate"
        snapshotLabel="2026-05-16T120000Z"
      />,
    )
    await waitFor(() => {
      expect(screen.getByTestId('advisor-refused-claims')).toBeInTheDocument()
    })
    const header = screen.getByTestId('advisor-refused-claims-header')
    expect(header.textContent).toContain('Refused LLM claims (2)')
    expect(screen.getByTestId('advisor-refused-claims-item-0').textContent).toBe(
      'refused: production ready',
    )
    expect(screen.getByTestId('advisor-refused-claims-item-1').textContent).toBe(
      'refused: signed off',
    )
  })

  it('discards non-marker strings from the refused_claims list (X:-2 anti-tampering)', async () => {
    // Defensive parser MUST filter out entries that do NOT start with
    // the marker prefix — a tampered payload cannot inject arbitrary
    // text under the refused-claim banner.
    stubFetch({
      ...HAPPY_BODY,
      schema_version: '1.1.0',
      refused_claims: [
        'refused: certified', // valid marker
        'arbitrary text without prefix', // tampering attempt
        'refused: signed off', // valid marker
        12345, // wrong type
      ],
    })
    render(
      <AdvisorPanel
        apiBase="/api/v1"
        caseId="cylinder-pv-candidate"
        snapshotLabel="2026-05-16T120000Z"
      />,
    )
    await waitFor(() => {
      expect(screen.getByTestId('advisor-refused-claims')).toBeInTheDocument()
    })
    const header = screen.getByTestId('advisor-refused-claims-header')
    // Only the two valid markers survived the parser.
    expect(header.textContent).toContain('Refused LLM claims (2)')
    expect(screen.queryByTestId('advisor-refused-claims-item-2')).toBeNull()
  })

  it('renders a truncation indicator when refused_claims exceeds the render cap', async () => {
    // REFUSED_CLAIMS_MAX_ITEMS = 24; build 30 markers so 6 are truncated.
    const many = Array.from(
      { length: 30 },
      (_, i) => `refused: ${ADVISOR_FORBIDDEN_TOKENS[i % ADVISOR_FORBIDDEN_TOKENS.length]}`,
    )
    stubFetch({
      ...HAPPY_BODY,
      schema_version: '1.1.0',
      refused_claims: many,
    })
    render(
      <AdvisorPanel
        apiBase="/api/v1"
        caseId="cylinder-pv-candidate"
        snapshotLabel="2026-05-16T120000Z"
      />,
    )
    await waitFor(() => {
      const trunc = screen.queryByTestId('advisor-refused-claims-truncated')
      expect(trunc).not.toBeNull()
      expect(trunc!.textContent).toContain('6 more')
    })
    const header = screen.getByTestId('advisor-refused-claims-header')
    // Header count reflects total markers, not rendered count.
    expect(header.textContent).toContain('Refused LLM claims (30)')
  })

  it('client-side parser keeps refused-marker strings even when they contain forbidden token substrings', async () => {
    // The marker 'refused: validated against' contains the forbidden
    // token substring 'validated against'. The parser MUST allow it
    // through (because the suffix matches a close-set forbidden token);
    // the panel's content sections still go through isAdvisorEntrySafe
    // so the forbidden token NEVER reaches a content section via a
    // misroute.
    stubFetch({
      ...HAPPY_BODY,
      schema_version: '1.1.0',
      refused_claims: ['refused: validated against'],
    })
    render(
      <AdvisorPanel
        apiBase="/api/v1"
        caseId="cylinder-pv-candidate"
        snapshotLabel="2026-05-16T120000Z"
      />,
    )
    await waitFor(() => {
      expect(screen.getByTestId('advisor-refused-claims-item-0').textContent).toBe(
        'refused: validated against',
      )
    })
  })

  // -------------------------------------------------------------------
  // Phase 13 B — close-set suffix validation (closes slice-A TAA HIGH
  // finding on `_parseRefusedClaims`). The defensive parser now requires
  // the suffix after `refused: ` to be an EXACT member of
  // ADVISOR_FORBIDDEN_TOKENS; otherwise the entry is discarded.
  //
  // Threat model: an attacker on the wire (MITM, malicious proxy, or a
  // backend regression) sends a string that LOOKS like a refused marker
  // but smuggles positive-claim copy after the forbidden token, e.g.
  // `"refused: production ready for service deployment"`. The previous
  // prefix-only check let this render verbatim inside
  // `_RefusedClaimsSection` (which does NOT apply `isAdvisorEntrySafe`
  // because markers are reviewer-readable suppression records, not
  // advisor copy). The close-set suffix gate closes the vector.
  // -------------------------------------------------------------------

  it('discards refused-marker strings whose suffix is NOT a close-set forbidden token (TAA HIGH)', async () => {
    stubFetch({
      ...HAPPY_BODY,
      schema_version: '1.1.0',
      refused_claims: [
        'refused: production ready', // valid close-set member
        'refused: production ready for service deployment', // SMUGGLED — must be dropped
        'refused: signed off', // valid close-set member
        'refused: ', // empty suffix — must be dropped
        'refused: totally-not-a-token', // bogus suffix — must be dropped
      ],
    })
    render(
      <AdvisorPanel
        apiBase="/api/v1"
        caseId="cylinder-pv-candidate"
        snapshotLabel="2026-05-16T120000Z"
      />,
    )
    await waitFor(() => {
      expect(screen.getByTestId('advisor-refused-claims')).toBeInTheDocument()
    })
    const header = screen.getByTestId('advisor-refused-claims-header')
    // Only the two close-set members survived.
    expect(header.textContent).toContain('Refused LLM claims (2)')
    expect(screen.getByTestId('advisor-refused-claims-item-0').textContent).toBe(
      'refused: production ready',
    )
    expect(screen.getByTestId('advisor-refused-claims-item-1').textContent).toBe(
      'refused: signed off',
    )
    expect(screen.queryByTestId('advisor-refused-claims-item-2')).toBeNull()
  })

  it('case-folds the suffix when validating against ADVISOR_FORBIDDEN_TOKENS', async () => {
    // Tokens in ADVISOR_FORBIDDEN_TOKENS are stored lower-case. A backend
    // that emits a marker with title-cased copy (e.g. via a future bump
    // that forgets to lower-case before embedding) should still parse
    // cleanly, but suffix-validation is the gate — keep it tight.
    stubFetch({
      ...HAPPY_BODY,
      schema_version: '1.1.0',
      refused_claims: [
        'refused: ASME compliant', // upper-cased close-set member
        'refused: Signed Off', // mixed-case close-set member
      ],
    })
    render(
      <AdvisorPanel
        apiBase="/api/v1"
        caseId="cylinder-pv-candidate"
        snapshotLabel="2026-05-16T120000Z"
      />,
    )
    await waitFor(() => {
      expect(screen.getByTestId('advisor-refused-claims')).toBeInTheDocument()
    })
    const header = screen.getByTestId('advisor-refused-claims-header')
    expect(header.textContent).toContain('Refused LLM claims (2)')
  })
})
