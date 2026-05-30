// FM-04a Phase 43 — polished "no result loaded" empty state.
//
// Tier 1 / Tier 2 engineering candidate; not signed validation; not
// benchmark agreement.
//
// Replaces the pre-Phase-43 bare grey-icon + one-line blank state in the
// 3D result viewport with the existing polished EmptyStateCard primitive
// (Phase 18 D). Self-contained: takes its only affordance (Browse cases)
// via props so App.tsx wiring stays central + LOC-pinned.
//
// EmptyStateCard takes a `glyph` STRING (emoji / unicode), not a lucide
// icon component (see EmptyStateCard.tsx props) — so we degrade to a
// fitting box/cube glyph rather than forcing a lucide dependency.

import { EmptyStateCard } from './EmptyStateCard'

export interface NoResultStateProps {
  /**
   * Optional handler for the primary "Browse cases" action. The action
   * button only renders when this is supplied; otherwise the card shows
   * the headline + body with no call-to-action (no crash).
   */
  readonly onBrowseCases?: () => void
}

export function NoResultState(props: NoResultStateProps) {
  const { onBrowseCases } = props
  return (
    <div data-testid="no-result-state">
      <EmptyStateCard
        glyph="◫"
        headline="No result loaded yet"
        body="Pick or create a case and run the solver to see the 3D result here — displacement, stress and the deformed mesh will appear once a solve completes."
        action={
          onBrowseCases !== undefined
            ? { label: 'Browse cases', onClick: onBrowseCases }
            : undefined
        }
      />
    </div>
  )
}
