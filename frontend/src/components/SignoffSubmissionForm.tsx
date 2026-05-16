// FM-04a Phase 10 A — Signoff submission form.
//
// Tier 1 engineering candidate; not signed validation; not benchmark agreement.
//
// Renders a verdict dropdown bound to SUPPORTED_SIGNOFF_VERDICTS
// as-const tuple (so the UI cannot offer a Tier 2 verb — Phase 10
// anti-gaming guard C: -10), a reviewer input, and a notes textarea
// with a client-side forbidden-claim preview. Submits via
// `submitSignoff()` and surfaces 422 detail + 429 Retry-After inline.
//
// On successful submit, calls `onSubmitSuccess()` so the parent panel
// can re-fetch the history exactly once (Phase 10 anti-gaming guard
// X: -2 — single refresh, no duplicate fetch).

import { useState, type FormEvent } from 'react'
import {
  CLIENT_FORBIDDEN_NOTES_TOKENS,
  SUPPORTED_SIGNOFF_VERDICTS,
  detectForbiddenClaim,
  submitSignoff,
  type SignoffSubmitResult,
  type SignoffVerdict,
} from '../signoffHistoryClient.ts'

export interface SignoffSubmissionFormProps {
  apiBase: string
  caseId: string
  onSubmitSuccess?: () => void
}

export function SignoffSubmissionForm({
  apiBase,
  caseId,
  onSubmitSuccess,
}: SignoffSubmissionFormProps) {
  const [reviewer, setReviewer] = useState('')
  const [verdict, setVerdict] = useState<SignoffVerdict | ''>('')
  const [notes, setNotes] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [result, setResult] = useState<SignoffSubmitResult | null>(null)

  const trimmedReviewer = reviewer.trim()
  const forbiddenPreview = notes ? detectForbiddenClaim(notes) : null
  const canSubmit =
    trimmedReviewer.length > 0 && verdict !== '' && !submitting

  async function handleSubmit(ev: FormEvent<HTMLFormElement>) {
    ev.preventDefault()
    if (!canSubmit) return
    // `canSubmit` already requires verdict !== '' so the cast below is
    // narrowed by TypeScript's control-flow analysis.
    setSubmitting(true)
    setResult(null)
    const res = await submitSignoff(apiBase, caseId, {
      reviewer: trimmedReviewer,
      verdict,
      notes,
    })
    setSubmitting(false)
    setResult(res)
    if (res.ok) {
      // Phase 10 X: -2 — clear-on-success + single refresh callback.
      setReviewer('')
      setVerdict('')
      setNotes('')
      onSubmitSuccess?.()
    }
  }

  return (
    <form
      data-testid="signoff-submission-form"
      onSubmit={handleSubmit}
      style={{
        display: 'flex',
        flexDirection: 'column',
        gap: '6px',
        padding: '8px',
        marginBottom: '12px',
        border: '1px solid var(--border)',
        borderRadius: '6px',
        background: 'var(--surface-subtle, #fafafa)',
      }}
    >
      <div
        style={{
          fontSize: '0.78rem',
          fontWeight: 600,
        }}
      >
        Record a signoff
      </div>
      <input
        type="text"
        placeholder="reviewer"
        value={reviewer}
        onChange={(e) => setReviewer(e.target.value)}
        data-testid="signoff-form-reviewer"
        disabled={submitting}
        style={{
          padding: '4px 8px',
          fontSize: '0.78rem',
          border: '1px solid var(--border)',
          borderRadius: '3px',
          fontFamily: 'inherit',
        }}
      />
      <select
        value={verdict}
        onChange={(e) => setVerdict(e.target.value as SignoffVerdict | '')}
        data-testid="signoff-form-verdict"
        disabled={submitting}
        style={{
          padding: '4px 8px',
          fontSize: '0.78rem',
          border: '1px solid var(--border)',
          borderRadius: '3px',
          fontFamily: 'inherit',
        }}
      >
        <option value="">— select verdict —</option>
        {SUPPORTED_SIGNOFF_VERDICTS.map((v) => (
          <option key={v} value={v}>
            {v}
          </option>
        ))}
      </select>
      <textarea
        placeholder="notes (Tier 1 disclaimers OK; bare positive claims refused server-side)"
        value={notes}
        onChange={(e) => setNotes(e.target.value)}
        data-testid="signoff-form-notes"
        disabled={submitting}
        rows={3}
        style={{
          padding: '4px 8px',
          fontSize: '0.78rem',
          border: '1px solid var(--border)',
          borderRadius: '3px',
          fontFamily: 'inherit',
          resize: 'vertical',
        }}
      />
      {forbiddenPreview && (
        <div
          data-testid="signoff-form-forbidden-preview"
          style={{
            fontSize: '0.7rem',
            color: 'var(--text-warning, #b8860b)',
          }}
        >
          notes contain forbidden positive claim {`"${forbiddenPreview}"`} outside
          the {'`not <claim>`'} disclaimer form — server will refuse the POST
        </div>
      )}
      <button
        type="submit"
        disabled={!canSubmit}
        data-testid="signoff-form-submit"
        style={{
          padding: '4px 8px',
          fontSize: '0.78rem',
          fontWeight: 600,
          cursor: canSubmit ? 'pointer' : 'not-allowed',
          opacity: canSubmit ? 1 : 0.5,
        }}
      >
        {submitting ? 'submitting…' : 'submit signoff'}
      </button>
      {result && !result.ok && (
        <div
          data-testid="signoff-form-error"
          style={{
            fontSize: '0.72rem',
            color: 'var(--danger, #c0392b)',
          }}
        >
          {result.error}
          {result.status === 429 && result.retryAfterSeconds !== undefined && (
            <span> · retry in {result.retryAfterSeconds}s</span>
          )}
        </div>
      )}
      {result && result.ok && (
        <div
          data-testid="signoff-form-success"
          style={{
            fontSize: '0.72rem',
            color: 'var(--accent, #0a8a4a)',
          }}
        >
          signoff recorded as {result.record?.verdict} at {result.record?.signoffUtc}
        </div>
      )}
      {/* Tier 1 disclaimer trio in form footer. */}
      <div
        data-testid="signoff-form-disclaimer"
        style={{
          fontSize: '0.66rem',
          color: 'var(--text-secondary)',
        }}
      >
        Tier 1 engineering candidate; not signed validation; not benchmark
        agreement. Forbidden tokens checked client-side ({CLIENT_FORBIDDEN_NOTES_TOKENS.length}):
        server-side audit is load-bearing.
      </div>
    </form>
  )
}
