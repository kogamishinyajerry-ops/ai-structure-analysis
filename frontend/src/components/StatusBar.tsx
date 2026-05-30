import { type CSSProperties, type ReactElement } from 'react';

// FM-04a Phase 43 — persistent CAE-style status strip.
//
// A thin (~28px) horizontal strip pinned to the bottom of the LIGHT app
// shell — the analogue of the status bar every reference solver
// (Abaqus / ANSYS / Hyperworks / Simcenter) carries. It surfaces the
// ambient session context that otherwise has no home: the unit system,
// the active case, the run/job state, and (when the viewport is
// hovering a mesh) a live cursor coordinate readout.
//
// Surface: LIGHT (warm-paper sidebar wash, ink text, hairline TOP
// border) — it sits in the app chrome, NOT over the dark 3D canvas, so
// it must NOT be styled as a dark-glass overlay (cf. ViewportNavGizmo /
// CoordReadoutTooltip, which DO float over the dark canvas).
//
// Honesty (project Tier discipline): every segment is driven purely by
// the props the host hands down. Nothing is fabricated — a null/blank
// prop yields an OMITTED segment rather than a guessed value. The only
// defaulted value is the unit-system label, which falls back to the
// repo-wide canonical "SI · m, Pa" (a presentation default, not solver
// data).
//
// Presentational only — no state, no effects, no network.

export type RunStateTone = 'muted' | 'accent' | 'success' | 'danger';

export interface StatusBarProps {
  /** Active case label (left cluster). Omitted when null/blank. */
  caseLabel?: string | null;
  /** Run-state label (right cluster), e.g. "Solved" / "Running" / "Idle". */
  runStateLabel?: string | null;
  /** Tone for the run-state label → mapped to a design-token color. */
  runStateTone?: RunStateTone;
  /** Job/solver status line (right cluster), e.g. "1 job queued". */
  jobStatusLabel?: string | null;
  /** Unit-system label (left cluster). Defaults to "SI · m, Pa". */
  unitSystem?: string | null;
  /** Live cursor world-coords. When null, the readout segment is omitted. */
  hoverCoords?: { x: number; y: number; z: number } | null;
}

/** Canonical fallback when the host does not declare a unit system. This
 * is a presentation default (matches the repo's SI convention), NOT
 * fabricated solver data. */
const DEFAULT_UNIT_SYSTEM = 'SI · m, Pa';

/** runStateTone → design-token color. */
const TONE_COLOR: Record<RunStateTone, string> = {
  muted: 'var(--text-muted)',
  accent: 'var(--accent)',
  success: 'var(--success-500)',
  danger: 'var(--danger-400)',
};

const barStyle: CSSProperties = {
  width: '100%',
  height: 28,
  boxSizing: 'border-box',
  flex: '0 0 auto',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'space-between',
  gap: 'var(--sp-3)',
  padding: '0 var(--sp-4)',
  borderTop: '1px solid var(--border)',
  background: 'var(--bg-sidebar)',
  color: 'var(--text-secondary)',
  fontSize: 'var(--fs-xs)',
  lineHeight: 1,
  // No wrapping — the bar is a single fixed-height strip.
  whiteSpace: 'nowrap',
  overflow: 'hidden',
  userSelect: 'none',
};

const clusterStyle: CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  gap: 'var(--sp-2)',
  minWidth: 0,
  overflow: 'hidden',
};

const segmentStyle: CSSProperties = {
  display: 'inline-flex',
  alignItems: 'center',
  minWidth: 0,
  overflow: 'hidden',
  textOverflow: 'ellipsis',
  whiteSpace: 'nowrap',
};

const dividerStyle: CSSProperties = {
  flex: '0 0 auto',
  width: 1,
  height: 12,
  background: 'var(--border)',
};

const coordReadoutStyle: CSSProperties = {
  fontFamily: 'var(--font-mono)',
  color: 'var(--text-secondary)',
  letterSpacing: '0.01em',
  flex: '0 0 auto',
};

const coordAxisLabelStyle: CSSProperties = {
  color: 'var(--text-muted)',
  fontWeight: 700,
  marginRight: 2,
};

function isFiniteNum(n: unknown): n is number {
  return typeof n === 'number' && Number.isFinite(n);
}

/**
 * Thin persistent status strip for the bottom of the app shell.
 *
 * Layout: LEFT = unit system + active case · RIGHT = run-state (tone
 * color) + job status + hover-coords readout. Any segment whose prop is
 * null / undefined / blank is gracefully omitted; hairline dividers sit
 * only between segments that actually render.
 */
export function StatusBar({
  caseLabel,
  runStateLabel,
  runStateTone = 'muted',
  jobStatusLabel,
  unitSystem,
  hoverCoords,
}: StatusBarProps) {
  // ---- LEFT cluster ----------------------------------------------------
  const trimmedUnit = typeof unitSystem === 'string' ? unitSystem.trim() : '';
  // The unit system always shows (defaults to SI) — it is ambient context,
  // not solver output.
  const unitLabel = trimmedUnit || DEFAULT_UNIT_SYSTEM;
  const trimmedCase = typeof caseLabel === 'string' ? caseLabel.trim() : '';

  const leftSegments: ReactSegment[] = [
    {
      key: 'unit',
      node: (
        <span data-testid="status-bar-unit-system" style={segmentStyle} title={unitLabel}>
          {unitLabel}
        </span>
      ),
    },
  ];
  if (trimmedCase) {
    leftSegments.push({
      key: 'case',
      node: (
        <span data-testid="status-bar-case" style={segmentStyle} title={trimmedCase}>
          {trimmedCase}
        </span>
      ),
    });
  }

  // ---- RIGHT cluster ---------------------------------------------------
  const trimmedRunState =
    typeof runStateLabel === 'string' ? runStateLabel.trim() : '';
  const trimmedJobStatus =
    typeof jobStatusLabel === 'string' ? jobStatusLabel.trim() : '';

  const rightSegments: ReactSegment[] = [];
  if (trimmedRunState) {
    rightSegments.push({
      key: 'run-state',
      node: (
        <span
          data-testid="status-bar-run-state"
          style={{
            ...segmentStyle,
            color: TONE_COLOR[runStateTone] ?? TONE_COLOR.muted,
            fontWeight: 700,
          }}
          title={trimmedRunState}
        >
          {trimmedRunState}
        </span>
      ),
    });
  }
  if (trimmedJobStatus) {
    rightSegments.push({
      key: 'job-status',
      node: (
        <span data-testid="status-bar-job-status" style={segmentStyle} title={trimmedJobStatus}>
          {trimmedJobStatus}
        </span>
      ),
    });
  }
  // Hover coords: only when a non-null, all-finite coordinate triple is
  // supplied. We never render NaN / a stale readout.
  if (
    hoverCoords != null
    && isFiniteNum(hoverCoords.x)
    && isFiniteNum(hoverCoords.y)
    && isFiniteNum(hoverCoords.z)
  ) {
    rightSegments.push({
      key: 'hover-coords',
      node: (
        <span
          data-testid="status-bar-hover-coords"
          style={coordReadoutStyle}
          title="Cursor position (world coordinates)"
        >
          <span style={coordAxisLabelStyle}>X:</span>
          <span data-testid="status-bar-coord-x">{hoverCoords.x.toFixed(3)}</span>
          {'  '}
          <span style={coordAxisLabelStyle}>Y:</span>
          <span data-testid="status-bar-coord-y">{hoverCoords.y.toFixed(3)}</span>
          {'  '}
          <span style={coordAxisLabelStyle}>Z:</span>
          <span data-testid="status-bar-coord-z">{hoverCoords.z.toFixed(3)}</span>
        </span>
      ),
    });
  }

  return (
    <div data-testid="status-bar" role="status" aria-live="off" style={barStyle}>
      <div style={clusterStyle}>{withDividers(leftSegments)}</div>
      <div style={{ ...clusterStyle, justifyContent: 'flex-end' }}>
        {withDividers(rightSegments)}
      </div>
    </div>
  );
}

interface ReactSegment {
  key: string;
  node: ReactElement;
}

/** Interleaves hairline dividers between rendered segments only — so a
 * cluster with a single (or zero) segment never shows a dangling rule. */
function withDividers(segments: ReactSegment[]): ReactElement[] {
  const out: ReactElement[] = [];
  segments.forEach((seg, i) => {
    if (i > 0) {
      out.push(<span key={`div-${seg.key}`} aria-hidden="true" style={dividerStyle} />);
    }
    out.push(<span key={seg.key} style={{ display: 'contents' }}>{seg.node}</span>);
  });
  return out;
}
