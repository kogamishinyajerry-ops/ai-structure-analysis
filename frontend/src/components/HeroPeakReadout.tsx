import { type CSSProperties } from 'react';
import { HERO_VALUE_FONT_SIZE_TOKEN, formatHeroValue } from './heroPeakFormat';

// FM-04a Phase 43 — hero peak-result readout banner.
//
// The demo payoff number (peak von Mises stress / peak displacement)
// was previously buried as a ~0.9rem cell inside the MetricGrid with no
// visual emphasis. This banner lifts the field label + the formatted
// peak value (summary.valueMax) to the top of the result panel at a
// clearly larger type size so it reads like the headline result.
//
// Surface: LIGHT (white/paper RMPP card) — NOT a dark-glass viewport
// overlay. Styling matches the surrounding RMPP card tokens.
//
// Honesty (project Tier discipline): units are NOT fabricated. They are
// only shown when supplied by the caller (the panel's `fieldUnits`
// prop). When absent/blank, the label + value render without a unit
// suffix rather than guessing a wrong one.
//
// The font-size token + formatHeroValue live in ./heroPeakFormat (pure
// module) so this file only exports a component (Fast-Refresh hygiene).

export interface HeroPeakReadoutProps {
  /** Human-readable field label, e.g. "Peak von Mises" / summary.fieldLabel. */
  fieldLabel: string | null | undefined;
  /** Peak (max) field value — summary.valueMax. */
  valueMax: number | null | undefined;
  /** Unit suffix (e.g. "Pa", "MPa", "mm"). Omitted/blank => no unit shown. */
  units?: string | null;
}

const containerStyle: CSSProperties = {
  border: '1px solid var(--border)',
  borderRadius: 'var(--r-md)',
  background: 'var(--bg-surface)',
  padding: '12px 14px',
  display: 'flex',
  flexDirection: 'column',
  gap: '4px',
};

const labelStyle: CSSProperties = {
  color: 'var(--text-muted)',
  fontSize: 'var(--fs-xs)',
  fontWeight: 800,
  textTransform: 'uppercase',
  letterSpacing: '0.04em',
};

const valueRowStyle: CSSProperties = {
  display: 'flex',
  alignItems: 'baseline',
  gap: '6px',
  lineHeight: 1.1,
};

const valueStyle: CSSProperties = {
  color: 'var(--accent)',
  fontSize: HERO_VALUE_FONT_SIZE_TOKEN,
  fontWeight: 800,
  letterSpacing: '-0.01em',
};

const unitStyle: CSSProperties = {
  color: 'var(--text-secondary)',
  fontSize: 'var(--fs-md)',
  fontWeight: 700,
};

/**
 * Compact, prominent peak-result banner. Renders the field label + the
 * formatted peak value + (optionally) units at a headline type size.
 *
 * Graceful absence: when there is no field label AND no finite value to
 * show (e.g. summary is null), renders nothing.
 */
export function HeroPeakReadout({ fieldLabel, valueMax, units }: HeroPeakReadoutProps) {
  const hasValue =
    valueMax !== null && valueMax !== undefined && Number.isFinite(valueMax);
  const hasLabel = typeof fieldLabel === 'string' && fieldLabel.trim().length > 0;

  // Nothing meaningful to surface — render nothing rather than a "0".
  if (!hasValue && !hasLabel) return null;

  const trimmedUnits = typeof units === 'string' ? units.trim() : '';

  return (
    <div data-testid="hero-peak-readout" style={containerStyle}>
      <div style={labelStyle}>{hasLabel ? fieldLabel : 'Peak result'}</div>
      <div style={valueRowStyle}>
        <span data-testid="hero-peak-value" style={valueStyle}>
          {formatHeroValue(valueMax)}
        </span>
        {trimmedUnits ? <span style={unitStyle}>{trimmedUnits}</span> : null}
      </div>
    </div>
  );
}
