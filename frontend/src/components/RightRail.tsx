// FM-04a Phase 20 D — RightRail component (Copilot chat side drawer).
//
// Tier 1 / Tier 2 engineering candidate; not signed validation; not
// benchmark agreement.
//
// Extracted from App.tsx so the conditional `<aside>` wrapping the
// ChatPanel lives in one place. The component renders nothing when
// `showChat` is false so the grid template `'1fr'` (vs '1fr 340px'
// when open) collapses cleanly in App.tsx.

import { ChatPanel, type CaeReviewCard } from './ChatPanel'
import type { ComponentProps } from 'react'

// Pulled from ChatPanel's typed `onExecuteAction` signature without
// importing the (non-exported) ChatPanelProps interface.
type ChatPanelOnExecuteAction = ComponentProps<typeof ChatPanel>['onExecuteAction']

export interface RightRailProps {
  /** Whether the right rail is mounted. App.tsx flips this via the
   * Topbar's Copilot toggle. */
  showChat: boolean
  /** Active case id forwarded to ChatPanel. */
  caseId: string | null
  /** Copilot action executor. */
  onExecuteAction: ChatPanelOnExecuteAction
  /** CAE review cards forwarded to ChatPanel. */
  reviewCards: CaeReviewCard[]
  /** Tier-2-claim plumbing forwarded to ChatPanel. */
  claimTier?: string
  allowedClaim?: string
}

export function RightRail({
  showChat,
  caseId,
  onExecuteAction,
  reviewCards,
  claimTier,
  allowedClaim,
}: RightRailProps) {
  if (!showChat) {
    return null
  }
  return (
    <aside
      data-testid="workbench-right-rail"
      style={{
        borderLeft: '1px solid var(--border)',
        background: 'var(--bg-sidebar)',
        zIndex: 5,
      }}
    >
      <ChatPanel
        caseId={caseId}
        onExecuteAction={onExecuteAction}
        reviewCards={reviewCards}
        claimTier={claimTier}
        allowedClaim={allowedClaim}
      />
    </aside>
  )
}
