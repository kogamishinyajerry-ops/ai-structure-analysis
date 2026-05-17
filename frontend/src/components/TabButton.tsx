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
  return (
    <button
      onClick={onClick}
      style={{
        padding: '8px 16px',
        border: 'none',
        borderRadius: '8px',
        background: active ? 'var(--accent)' : 'transparent',
        color: active ? '#000' : '#fff',
        fontWeight: 600,
        cursor: 'pointer',
        transition: 'all 0.2s',
        display: 'flex',
        alignItems: 'center',
        gap: '8px',
      }}
    >
      {icon} {label}
    </button>
  );
}
