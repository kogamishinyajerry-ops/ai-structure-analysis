// FM-04a Phase 18 D — drift severity badge.
//
// Tier 1 / Tier 2 engineering candidate; not signed validation; not
// benchmark agreement.
//
// Renders `{dominant_axis} {±N.N%}` with severity coloring sourced
// from the Phase 16-17 per-axis floor. Designed to embed inline in
// the cohort anomaly + signoff-history surfaces; small footprint,
// no external state.

import type { CSSProperties } from 'react'

export type DriftSeverity = 'info' | 'warn' | 'danger'

export interface DriftBadgeProps {
  /** Axis label (e.g., `"trust_score"`, `"completeness_score"`). */
  readonly axis: string
  /**
   * Signed percentage delta. Positive = upward drift; negative =
   * downward. The formatter always prepends a sign character.
   */
  readonly percentDelta: number
  /** Severity bucket; drives the colour. */
  readonly severity: DriftSeverity
  /**
   * Optional accessible label override; defaults to a sentence
   * built from axis + percent + severity.
   */
  readonly ariaLabel?: string
}

/**
 * Format a signed percentage to 1 decimal with an explicit sign.
 *
 *   formatSignedPercent(2.5)   === "+2.5%"
 *   formatSignedPercent(-3.07) === "-3.1%"
 *   formatSignedPercent(0)     === "+0.0%"
 *
 * Exported so consumers + tests can share the formatter.
 */
export function formatSignedPercent(value: number): string {
  const rounded = Math.round(value * 10) / 10
  const sign = rounded >= 0 ? '+' : '-'
  const magnitude = Math.abs(rounded).toFixed(1)
  return `${sign}${magnitude}%`
}

/**
 * Decide severity from absolute percent drift. The thresholds are
 * conservative defaults; consumers pass their own `severity` to this
 * component when they have richer context (the Phase 16-17 per-axis
 * floor varies by axis).
 *
 *   |Δ| < 1%   → 'info'
 *   |Δ| < 5%   → 'warn'
 *   else       → 'danger'
 *
 * Exported so tests + consumers can share the policy.
 */
export function severityFromPercent(absPercent: number): DriftSeverity {
  const x = Math.abs(absPercent)
  if (x < 1) return 'info'
  if (x < 5) return 'warn'
  return 'danger'
}

export function DriftBadge(props: DriftBadgeProps) {
  const { axis, percentDelta, severity, ariaLabel } = props
  const text = `${axis} ${formatSignedPercent(percentDelta)}`
  const label =
    ariaLabel ??
    `${axis} drifted ${formatSignedPercent(percentDelta)}, severity ${severity}`
  return (
    <span
      data-testid="drift-badge"
      data-severity={severity}
      data-axis={axis}
      aria-label={label}
      style={severityStyles[severity]}
    >
      {text}
    </span>
  )
}

const baseStyle: CSSProperties = {
  display: 'inline-block',
  padding: '2px 8px',
  borderRadius: 12,
  fontSize: 12,
  fontWeight: 500,
  fontFamily:
    'ui-monospace, SFMono-Regular, "SF Mono", Menlo, monospace',
  letterSpacing: 0.2,
  lineHeight: 1.4,
}

const severityStyles: Record<DriftSeverity, CSSProperties> = {
  info: { ...baseStyle, background: '#1e3a5f', color: '#cfe4ff' },
  warn: { ...baseStyle, background: '#5c4416', color: '#ffe3b3' },
  danger: { ...baseStyle, background: '#5c1e1e', color: '#ffcdcd' },
}
