// FM-04a Phase 43 — ModeSelector dark-glass HUD overlay.
//
// This list floats OVER the dark 3D viewport (mounted absolute, top-right),
// so it is styled as a DARK-GLASS overlay — matching CoordReadoutTooltip and
// the ResultMeshWebGLViewport HUD — NOT as a warm-light white card.
//
// Prior to Phase 43 this component was 100% Tailwind (bg-slate-900/80,
// text-indigo-400, divide-slate-800, …) which is INERT in this raw-CSS repo:
// for modal + buckling results it painted as a bare transparent serif table
// with default link-blue text over the dark canvas. Now every style is an
// inline object referencing the design tokens in index.css :root.
//
// Selected-row highlight uses var(--accent) (clay/coral): a low-opacity accent
// fill + accent text + a pulse dot (suppressed under prefers-reduced-motion via
// the `.mode-pulse-dot` rule in index.css, anti-gaming guard B:-1).

import { Layers } from 'lucide-react';
import type { CSSProperties } from 'react';

interface IncrementData {
  index: number;
  step: number;
  type: string;
  value: number;
  max_displacement: number;
  max_von_mises: number;
}

interface ModeSelectorProps {
  increments: IncrementData[];
  selectedModeIndex: number;
  activeAnalysisType: string;
  onSelectMode: (index: number) => void;
}

// Dark-glass overlay surface (shared language with CoordReadoutTooltip /
// the WebGL HUD: deep warm-ink translucent fill + hairline light border).
const OVERLAY_BG = 'rgba(30, 27, 22, 0.82)';        // var(--c-950) @ ~0.82
const OVERLAY_BG_HEADER = 'rgba(46, 42, 35, 0.55)'; // var(--c-900) wash
const HAIRLINE = '1px solid rgba(245, 242, 235, 0.14)';
const MONO = 'ui-monospace, SFMono-Regular, "SF Mono", Menlo, monospace';
const TEXT_LIGHT = '#f5f2eb';   // var(--c-100) on dark
const TEXT_MUTED = '#aba290';   // var(--c-500) on dark

export function ModeSelector({ increments, selectedModeIndex, activeAnalysisType, onSelectMode }: ModeSelectorProps) {
  if (!increments || increments.length === 0) return null;

  const getLabel = (type: string) => {
    if (type === 'vibration') return 'Frequency (Hz)';
    if (type === 'buckling') return 'Load Factor (λ)';
    return 'Value';
  };

  return (
    <div
      data-testid="mode-selector"
      style={{
        background: OVERLAY_BG,
        border: HAIRLINE,
        borderRadius: 'var(--r-md)',
        overflow: 'hidden',
        boxShadow: 'var(--elev-3)',
        backdropFilter: 'blur(10px)',
        WebkitBackdropFilter: 'blur(10px)',
        minWidth: 220,
      }}
    >
      {/* Header row — Layers icon + title */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 8,
          padding: '10px 14px',
          background: OVERLAY_BG_HEADER,
          borderBottom: HAIRLINE,
        }}
      >
        <Layers size={15} aria-hidden style={{ color: 'var(--accent)', flexShrink: 0 }} />
        <h3
          style={{
            margin: 0,
            fontSize: 'var(--fs-xs)',
            fontWeight: 700,
            letterSpacing: '0.08em',
            textTransform: 'uppercase',
            color: TEXT_LIGHT,
          }}
        >
          {activeAnalysisType === 'modal' ? 'Vibration Modes' : 'Buckling Modes'}
        </h3>
      </div>

      <div style={{ maxHeight: 256, overflowY: 'auto' }}>
        <table
          style={{
            width: '100%',
            borderCollapse: 'collapse',
            textAlign: 'left',
            fontSize: 'var(--fs-xs)',
          }}
        >
          <thead>
            <tr>
              <th style={thStyle}>Mode</th>
              <th style={thStyle}>{getLabel(increments[0].type)}</th>
              <th style={{ ...thStyle, textAlign: 'right' }}>Max Disp</th>
            </tr>
          </thead>
          <tbody>
            {increments.map((inc) => {
              const isSelected = selectedModeIndex === inc.index - 1;
              return (
                <tr
                  key={`${inc.step}-${inc.index}`}
                  data-testid={`mode-row-${inc.index}`}
                  data-selected={isSelected ? 'true' : 'false'}
                  onClick={() => onSelectMode(inc.index - 1)}
                  onMouseEnter={(e) => {
                    if (!isSelected) e.currentTarget.style.background = 'rgba(245, 242, 235, 0.06)';
                  }}
                  onMouseLeave={(e) => {
                    if (!isSelected) e.currentTarget.style.background = 'transparent';
                  }}
                  style={{
                    cursor: 'pointer',
                    transition: 'background 120ms ease, color 120ms ease',
                    // Selected row: low-opacity accent fill + accent text.
                    background: isSelected ? 'var(--accent-glow)' : 'transparent',
                    color: isSelected ? 'var(--accent-300)' : TEXT_MUTED,
                    borderTop: HAIRLINE,
                  }}
                >
                  <td style={{ ...tdStyle, fontFamily: MONO }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      {isSelected && (
                        <span
                          className="mode-pulse-dot"
                          data-testid="mode-pulse-dot"
                          aria-hidden
                          style={{
                            width: 6,
                            height: 6,
                            borderRadius: 'var(--r-full)',
                            background: 'var(--accent)',
                            flexShrink: 0,
                          }}
                        />
                      )}
                      <span>{inc.index}</span>
                    </div>
                  </td>
                  <td style={{ ...tdStyle, fontFamily: MONO, fontWeight: 600, color: isSelected ? 'var(--accent-300)' : TEXT_LIGHT }}>
                    {inc.value.toFixed(2)}
                  </td>
                  <td style={{ ...tdStyle, fontFamily: MONO, textAlign: 'right', color: isSelected ? 'var(--accent-300)' : TEXT_MUTED }}>
                    {inc.max_displacement.toFixed(4)}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

const thStyle: CSSProperties = {
  padding: '7px 14px',
  fontWeight: 500,
  color: TEXT_MUTED,
  letterSpacing: '0.04em',
  borderBottom: HAIRLINE,
  whiteSpace: 'nowrap',
};

const tdStyle: CSSProperties = {
  padding: '9px 14px',
  whiteSpace: 'nowrap',
};
