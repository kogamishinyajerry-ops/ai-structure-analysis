// FM-04a Phase 10 A — headless smoke for SignoffSubmissionForm.
//
// Tier 1 engineering candidate; not signed validation; not benchmark agreement.

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { SignoffSubmissionForm } from '../src/components/SignoffSubmissionForm.tsx'
import {
  SUPPORTED_SIGNOFF_VERDICTS,
  detectForbiddenClaim,
} from '../src/signoffHistoryClient.ts'

function stubFetchSuccess(record: Record<string, unknown>) {
  global.fetch = vi.fn().mockResolvedValue({
    ok: true,
    status: 200,
    headers: {
      get: () => null,
    },
    json: async () => record,
  } as unknown as Response)
}

function stubFetchStatus(
  status: number,
  detail: string,
  headers: Record<string, string> = {},
) {
  global.fetch = vi.fn().mockResolvedValue({
    ok: false,
    status,
    headers: {
      get: (name: string) => headers[name] ?? null,
    },
    json: async () => ({ detail }),
  } as unknown as Response)
}

describe('SUPPORTED_SIGNOFF_VERDICTS as-const tuple', () => {
  it('contains exactly the 4 Phase 8 A whitelist verdicts', () => {
    expect(SUPPORTED_SIGNOFF_VERDICTS).toEqual([
      'watching',
      'needs_more_evidence',
      'needs_more_convergence',
      'blocked_pending_input',
    ])
  })

  it('does not include any Tier 2 promotion verb (anti-gaming guard C: -10)', () => {
    const forbidden = [
      'tier_2',
      'tier 2',
      'signed_validation',
      'benchmark_agreement',
      'promoted',
      'ready_for_fm04b',
      'ready_for_tier_2',
    ]
    for (const f of forbidden) {
      expect(SUPPORTED_SIGNOFF_VERDICTS).not.toContain(f)
    }
  })
})

describe('detectForbiddenClaim client-side preview', () => {
  it('detects bare positive claim', () => {
    expect(detectForbiddenClaim('this case is validated against ASTM E8')).toBe(
      'validated against',
    )
  })

  it('accepts disclaimer-form `not <claim>`', () => {
    expect(detectForbiddenClaim('not signed validation; not benchmark agreement')).toBeNull()
  })

  it('returns null on empty notes', () => {
    expect(detectForbiddenClaim('')).toBeNull()
  })

  it('returns null on benign notes', () => {
    expect(detectForbiddenClaim('reviewer is monitoring this candidate.')).toBeNull()
  })
})

describe('SignoffSubmissionForm', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('renders all 4 verdicts in the dropdown', () => {
    render(<SignoffSubmissionForm apiBase="/api/v1" caseId="GS-A-candidate" />)
    const select = screen.getByTestId('signoff-form-verdict') as HTMLSelectElement
    const optionValues = Array.from(select.options).map((o) => o.value)
    expect(optionValues).toContain('')
    for (const verdict of SUPPORTED_SIGNOFF_VERDICTS) {
      expect(optionValues).toContain(verdict)
    }
  })

  it('does NOT render any Tier 2 verb option', () => {
    render(<SignoffSubmissionForm apiBase="/api/v1" caseId="GS-A-candidate" />)
    const select = screen.getByTestId('signoff-form-verdict') as HTMLSelectElement
    const optionValues = Array.from(select.options).map((o) => o.value)
    for (const forbidden of [
      'ready_for_tier_2',
      'promoted',
      'signed_validation',
      'benchmark_agreement',
    ]) {
      expect(optionValues).not.toContain(forbidden)
    }
  })

  it('keeps submit disabled until reviewer + verdict are set', () => {
    render(<SignoffSubmissionForm apiBase="/api/v1" caseId="GS-A-candidate" />)
    const button = screen.getByTestId('signoff-form-submit') as HTMLButtonElement
    expect(button.disabled).toBe(true)
    fireEvent.change(screen.getByTestId('signoff-form-reviewer'), {
      target: { value: 'alice' },
    })
    expect(button.disabled).toBe(true) // verdict still empty
    fireEvent.change(screen.getByTestId('signoff-form-verdict'), {
      target: { value: 'watching' },
    })
    expect(button.disabled).toBe(false)
  })

  it('keeps submit disabled when reviewer is whitespace-only', () => {
    render(<SignoffSubmissionForm apiBase="/api/v1" caseId="GS-A-candidate" />)
    fireEvent.change(screen.getByTestId('signoff-form-reviewer'), {
      target: { value: '   ' },
    })
    fireEvent.change(screen.getByTestId('signoff-form-verdict'), {
      target: { value: 'watching' },
    })
    const button = screen.getByTestId('signoff-form-submit') as HTMLButtonElement
    expect(button.disabled).toBe(true)
  })

  it('surfaces forbidden-claim preview when notes contain bare positive claim', () => {
    render(<SignoffSubmissionForm apiBase="/api/v1" caseId="GS-A-candidate" />)
    fireEvent.change(screen.getByTestId('signoff-form-notes'), {
      target: { value: 'this is validated against E8' },
    })
    expect(screen.getByTestId('signoff-form-forbidden-preview')).toBeInTheDocument()
  })

  it('hides forbidden-claim preview when notes are disclaimer-form', () => {
    render(<SignoffSubmissionForm apiBase="/api/v1" caseId="GS-A-candidate" />)
    fireEvent.change(screen.getByTestId('signoff-form-notes'), {
      target: { value: 'not signed validation; not benchmark agreement' },
    })
    expect(screen.queryByTestId('signoff-form-forbidden-preview')).toBeNull()
  })

  it('calls onSubmitSuccess and clears form on 200 response', async () => {
    stubFetchSuccess({
      schema_version: '1.0.0',
      case_id: 'GS-A-candidate',
      reviewer: 'alice',
      verdict: 'watching',
      signoff_utc: '2026-05-16T100000Z',
      notes: 'ok',
      claim_tier: 'Tier 1 engineering candidate',
      claim_boundary:
        'tier1_engineering_candidate; not_signed_validation; not_benchmark_agreement',
      claim_impact: 'Tier 1 candidate only; not signed validation.',
    })
    const onSuccess = vi.fn()
    render(
      <SignoffSubmissionForm
        apiBase="/api/v1"
        caseId="GS-A-candidate"
        onSubmitSuccess={onSuccess}
      />,
    )
    const reviewerInput = screen.getByTestId('signoff-form-reviewer') as HTMLInputElement
    fireEvent.change(reviewerInput, { target: { value: 'alice' } })
    fireEvent.change(screen.getByTestId('signoff-form-verdict'), {
      target: { value: 'watching' },
    })
    fireEvent.change(screen.getByTestId('signoff-form-notes'), {
      target: { value: 'ok' },
    })
    fireEvent.click(screen.getByTestId('signoff-form-submit'))
    await waitFor(() => {
      expect(onSuccess).toHaveBeenCalledTimes(1)
    })
    expect(reviewerInput.value).toBe('') // cleared after success
    expect(screen.getByTestId('signoff-form-success')).toBeInTheDocument()
  })

  it('surfaces 422 detail inline', async () => {
    stubFetchStatus(422, 'verdict not in the whitelist')
    render(<SignoffSubmissionForm apiBase="/api/v1" caseId="GS-A-candidate" />)
    fireEvent.change(screen.getByTestId('signoff-form-reviewer'), {
      target: { value: 'alice' },
    })
    fireEvent.change(screen.getByTestId('signoff-form-verdict'), {
      target: { value: 'watching' },
    })
    fireEvent.click(screen.getByTestId('signoff-form-submit'))
    await waitFor(() => {
      expect(screen.getByTestId('signoff-form-error')).toBeInTheDocument()
    })
    expect(screen.getByTestId('signoff-form-error').textContent).toContain(
      'verdict not in the whitelist',
    )
  })

  it('surfaces 429 Retry-After countdown', async () => {
    stubFetchStatus(429, 'rate limit exceeded', { 'Retry-After': '42' })
    render(<SignoffSubmissionForm apiBase="/api/v1" caseId="GS-A-candidate" />)
    fireEvent.change(screen.getByTestId('signoff-form-reviewer'), {
      target: { value: 'alice' },
    })
    fireEvent.change(screen.getByTestId('signoff-form-verdict'), {
      target: { value: 'watching' },
    })
    fireEvent.click(screen.getByTestId('signoff-form-submit'))
    await waitFor(() => {
      expect(screen.getByTestId('signoff-form-error')).toBeInTheDocument()
    })
    expect(screen.getByTestId('signoff-form-error').textContent).toContain('42s')
  })

  it('renders Tier 1 disclaimer trio in form footer', () => {
    render(<SignoffSubmissionForm apiBase="/api/v1" caseId="GS-A-candidate" />)
    const disclaimer = screen.getByTestId('signoff-form-disclaimer')
    const text = disclaimer.textContent?.toLowerCase() ?? ''
    expect(text).toContain('tier 1 engineering candidate')
    expect(text).toContain('not signed validation')
    expect(text).toContain('not benchmark agreement')
  })
})
