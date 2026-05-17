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
        style={{
          ...lineStyle,
          width: i === lines - 1 ? '60%' : '100%',
        }}
      />,
    )
  }
  return (
    <div
      role="status"
      aria-busy="true"
      aria-live="polite"
      data-testid="skeleton-card"
      style={cardStyle}
    >
      <span style={srOnly}>{props.label ?? 'Loading'}</span>
      {lineNodes}
    </div>
  )
}

const cardStyle: CSSProperties = {
  background: '#1a1a1a',
  border: '1px solid #2a2a2a',
  borderRadius: 8,
  padding: 16,
  display: 'flex',
  flexDirection: 'column',
  gap: 10,
}

const lineStyle: CSSProperties = {
  height: 12,
  borderRadius: 6,
  background:
    'linear-gradient(90deg, #232323 0%, #2f2f2f 50%, #232323 100%)',
  backgroundSize: '200% 100%',
  animation: 'skeleton-shimmer 1.5s infinite linear',
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
