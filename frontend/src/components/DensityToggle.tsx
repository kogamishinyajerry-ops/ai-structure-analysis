// FM-04a Phase 45 A — density toggle (Cozy | Compact segmented pill).
//
// A 2-segment pill in the Topbar that drives the useDensity hook. Matches the
// Topbar's existing control chrome (the Copilot active-state treatment:
// accent-glow background + accent-600 text). Pure render — no clock / RNG / ref
// reads. Exports ONLY the component (react-refresh/only-export-components); the
// option list is a module-local const (not exported, so the rule is satisfied).
//
// Tier 1 engineering candidate; not signed validation; not benchmark agreement.

import type { Density } from '../state/useDensity';

const OPTS: { value: Density; label: string }[] = [
  { value: 'comfortable', label: 'Cozy' },
  { value: 'compact', label: 'Compact' },
];

export function DensityToggle({
  density,
  onChange,
}: {
  density: Density;
  onChange: (next: Density) => void;
}) {
  return (
    <div
      data-testid="topbar-density-toggle"
      role="group"
      aria-label="UI density"
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        background: 'var(--bg-surface)',
        border: '1px solid var(--border)',
        borderRadius: '8px',
        padding: '2px',
        gap: '2px',
      }}
    >
      {OPTS.map((o) => {
        const active = density === o.value;
        return (
          <button
            key={o.value}
            type="button"
            data-testid={`density-opt-${o.value}`}
            aria-pressed={active}
            onClick={() => onChange(o.value)}
            style={{
              border: 'none',
              borderRadius: '6px',
              padding: '4px 10px',
              fontSize: '0.78rem',
              fontWeight: 600,
              cursor: 'pointer',
              background: active ? 'var(--accent-glow)' : 'transparent',
              color: active ? 'var(--accent-600)' : 'var(--text-muted)',
            }}
          >
            {o.label}
          </button>
        );
      })}
    </div>
  );
}
