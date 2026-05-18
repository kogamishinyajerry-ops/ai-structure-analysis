// FM-04a Phase 18 D — standard error display.
//
// Tier 1 / Tier 2 engineering candidate; not signed validation; not
// benchmark agreement.
//
// One opinionated error card with (title, message, remediation,
// retry). Used by panels in lieu of bespoke per-component error
// surfaces. Stable role="alert" so screen readers announce.

import type { CSSProperties } from 'react'
import { useId } from 'react'

export interface ErrorCardProps {
  /** Headline (e.g., "Could not load cohort overview"). */
  readonly title: string
  /** Human-readable summary of what failed. */
  readonly message: string
  /**
   * Ordered remediation steps shown to the user. Optional; when
   * omitted, the card renders without a steps section.
   */
  readonly remediation?: readonly string[]
  /**
   * Optional retry callback; when present, a retry button is shown
   * with `Retry` label. The handler receives no arguments.
   */
  readonly onRetry?: () => void
  /**
   * Optional error code surfaced as a small monospace pill (useful
   * for support tickets / log correlation).
   */
  readonly code?: string
  /**
   * FM-04a Phase 36 B — optional novice-friendly label that takes
   * priority over `code` for the pill render. The `code` value
   * remains available via the `data-error-code` attribute on the
   * pill for support-ticket correlation.
   *
   * Use when the underlying `code` is an internal enum (e.g.
   * "UPLOAD", "CASE-LOAD") that novices may mistake for a
   * verbatim instruction. Falls back to `code` when not provided.
   */
  readonly codeFriendly?: string
}

export function ErrorCard(props: ErrorCardProps) {
  const { title, message, remediation, onRetry, code, codeFriendly } = props
  // Phase 36 B — friendly label takes priority for the visible
  // pill copy; the raw code is preserved via data-error-code so
  // support tickets / log correlation can still scrape the enum.
  const pillCopy = codeFriendly ?? code
  // Phase 36 B — give the alert region an accessible name via
  // aria-labelledby → title id; without this, screen readers
  // announce the entire card text as the alert name.
  const titleId = useId()
  return (
    <div
      role="alert"
      aria-live="assertive"
      aria-labelledby={titleId}
      data-testid="error-card"
      style={cardStyle}
    >
      <div style={headerStyle}>
        <span aria-hidden="true" style={iconStyle}>
          ⚠
        </span>
        <strong id={titleId} style={titleStyle}>{title}</strong>
        {pillCopy !== undefined && (
          <span
            data-testid="error-code"
            data-error-code={code}
            style={codeStyle}
          >
            {pillCopy}
          </span>
        )}
      </div>
      <p style={messageStyle}>{message}</p>
      {remediation !== undefined && remediation.length > 0 && (
        <>
          <p style={remediationHeadingStyle}>Try the following:</p>
          <ol data-testid="error-remediation" style={remediationListStyle}>
            {remediation.map((step, i) => (
              <li key={i} style={remediationItemStyle}>
                {step}
              </li>
            ))}
          </ol>
        </>
      )}
      {onRetry !== undefined && (
        <button
          type="button"
          onClick={onRetry}
          data-testid="error-retry"
          style={retryButtonStyle}
        >
          Retry
        </button>
      )}
    </div>
  )
}

const cardStyle: CSSProperties = {
  background: '#2a1414',
  border: '1px solid #5c1e1e',
  borderRadius: 8,
  padding: 16,
  color: '#ffcdcd',
  display: 'flex',
  flexDirection: 'column',
  gap: 8,
}
const headerStyle: CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  gap: 8,
}
const iconStyle: CSSProperties = {
  fontSize: 16,
}
const titleStyle: CSSProperties = {
  fontSize: 15,
}
const codeStyle: CSSProperties = {
  marginLeft: 'auto',
  background: '#3a1818',
  border: '1px solid #5c1e1e',
  borderRadius: 4,
  padding: '1px 6px',
  fontFamily:
    'ui-monospace, SFMono-Regular, "SF Mono", Menlo, monospace',
  fontSize: 11,
  color: '#ffe3e3',
}
const messageStyle: CSSProperties = {
  margin: 0,
  fontSize: 13,
  lineHeight: 1.5,
}
const remediationHeadingStyle: CSSProperties = {
  margin: '4px 0 0',
  fontSize: 13,
  fontWeight: 500,
}
const remediationListStyle: CSSProperties = {
  margin: 0,
  paddingInlineStart: 20,
  fontSize: 13,
  lineHeight: 1.5,
}
const remediationItemStyle: CSSProperties = {
  marginBottom: 2,
}
const retryButtonStyle: CSSProperties = {
  alignSelf: 'flex-start',
  marginTop: 6,
  background: '#5c1e1e',
  border: '1px solid #8a3535',
  borderRadius: 6,
  color: '#fff',
  padding: '6px 14px',
  fontSize: 13,
  cursor: 'pointer',
}
