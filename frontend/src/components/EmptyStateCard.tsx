// FM-04a Phase 18 D — standard empty-state card.
//
// Tier 1 / Tier 2 engineering candidate; not signed validation; not
// benchmark agreement.
//
// One uniform empty-state design with (icon, headline, body, primary
// action). Encourages onboarding affordances rather than the
// pre-Phase-18 blank-panel-with-grey-text pattern. Per the Phase 18
// UI rubric, "empty states should explain what would fill them and
// offer the next click".

import type { CSSProperties } from 'react'

export interface EmptyStateAction {
  readonly label: string
  readonly onClick: () => void
}

export interface EmptyStateCardProps {
  /** Headline (e.g., "No cases selected yet"). */
  readonly headline: string
  /** One-paragraph body explaining the empty state's cause. */
  readonly body: string
  /**
   * Optional primary action; renders a button when present.
   */
  readonly action?: EmptyStateAction
  /**
   * Single visual glyph to display (an emoji or a unicode symbol).
   * Defaults to a friendly dashboard glyph.
   */
  readonly glyph?: string
}

export function EmptyStateCard(props: EmptyStateCardProps) {
  const { headline, body, action, glyph = '○' } = props
  return (
    <div
      role="status"
      data-testid="empty-state-card"
      style={cardStyle}
    >
      <div aria-hidden="true" style={glyphStyle}>
        {glyph}
      </div>
      <h3 style={headlineStyle}>{headline}</h3>
      <p style={bodyStyle}>{body}</p>
      {action !== undefined && (
        <button
          type="button"
          onClick={action.onClick}
          data-testid="empty-state-action"
          style={actionStyle}
        >
          {action.label}
        </button>
      )}
    </div>
  )
}

const cardStyle: CSSProperties = {
  background: 'var(--bg-surface)',
  border: '1px dashed var(--border)',
  borderRadius: 8,
  padding: 24,
  textAlign: 'center',
  color: 'var(--text-muted)',
  display: 'flex',
  flexDirection: 'column',
  alignItems: 'center',
  gap: 8,
}
const glyphStyle: CSSProperties = {
  fontSize: 36,
  opacity: 0.55,
  marginBottom: 4,
}
const headlineStyle: CSSProperties = {
  margin: 0,
  fontSize: 16,
  fontWeight: 600,
  color: 'var(--text-primary)',
}
const bodyStyle: CSSProperties = {
  margin: 0,
  fontSize: 13,
  lineHeight: 1.55,
  maxWidth: 460,
}
const actionStyle: CSSProperties = {
  marginTop: 8,
  background: 'var(--accent)',
  border: 'none',
  borderRadius: 6,
  color: '#fff',
  padding: '8px 18px',
  fontSize: 13,
  cursor: 'pointer',
}
