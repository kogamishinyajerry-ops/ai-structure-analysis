// FM-04a Phase 18 D — standard loading skeleton.
//
// Tier 1 / Tier 2 engineering candidate; not signed validation; not
// benchmark agreement.
//
// One shimmering card the workbench reuses wherever a panel is
// fetching. Stable role="status" + aria-busy so screen readers
// announce the loading state.

import type { CSSProperties } from 'react'

export interface SkeletonCardProps {
  /** Number of shimmering lines to render. Defaults to 3. */
  readonly lines?: number
  /** Optional short label rendered above the lines for screen readers. */
  readonly label?: string
}

export function SkeletonCard(props: SkeletonCardProps) {
  const lines = Math.max(1, props.lines ?? 3)
  const lineNodes = []
  for (let i = 0; i < lines; i += 1) {
    lineNodes.push(
      <div
        key={i}
        data-testid="skeleton-line"
        className="skeleton-line"
        style={{ width: i === lines - 1 ? '60%' : '100%' }}
      />,
    )
  }
  return (
    <div
      role="status"
      aria-busy="true"
      aria-live="polite"
      data-testid="skeleton-card"
      className="skeleton-block"
      style={cardStyle}
    >
      <span style={srOnly}>{props.label ?? 'Loading'}</span>
      {lineNodes}
    </div>
  )
}

// FM-04a Phase 42: surface tokens (bg/border/radius) now come from the
// `.skeleton-block` class; only layout stays inline. The per-line gradient +
// the (previously dead) shimmer animation live in the `.skeleton-line` class.
const cardStyle: CSSProperties = {
  padding: 16,
  display: 'flex',
  flexDirection: 'column',
  gap: 10,
}

const srOnly: CSSProperties = {
  position: 'absolute',
  width: 1,
  height: 1,
  padding: 0,
  margin: -1,
  overflow: 'hidden',
  clip: 'rect(0, 0, 0, 0)',
  whiteSpace: 'nowrap',
  border: 0,
}
