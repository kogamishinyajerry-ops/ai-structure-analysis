// FM-04a Phase 22 C — TabButton extracted out of App.tsx as part of
// the LOC-discipline trajectory.
//
// Tier 1 / Tier 2 engineering candidate; not signed validation; not
// benchmark agreement.

import type { ReactNode } from 'react';

export function TabButton({
  active,
  onClick,
  label,
  icon,
}: {
  active: boolean;
  onClick: () => void;
  label: string;
  icon: ReactNode;
}) {
  // FM-04a Phase 42: adopt the calm `.tab-pill` primitive (index.css) — it
  // brings tokenized padding/radius/typography, a real idle→hover color lift
  // (idle text-secondary, hover text-primary), and reduced-motion-safe
  // transitions, replacing the old un-tokenized `transition: all 0.2s` + raw
  // #000/#fff. The active fill (accent bg + #04130d text) comes from
  // `.tab-pill.active`; the inline background on the active branch is the
  // single value Phase22C pins via `style.background` (kept in sync, not a
  // visual override), and is OMITTED when idle so `.tab-pill:hover` is free
  // to paint the hover background (an inline value would block the :hover rule).
  return (
    <button
      onClick={onClick}
      className={`tab-pill${active ? ' active' : ''}`}
      style={active ? { background: 'var(--accent)' } : undefined}
    >
      {icon} {label}
    </button>
  );
}
