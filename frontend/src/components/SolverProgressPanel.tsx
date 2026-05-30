import { useEffect, useLayoutEffect, useRef, useState, type CSSProperties } from 'react';
// FM-04a Phase 43 Slice 2 — the pure log→progress parse lives in a sibling
// module so this .tsx only exports a component (Fast-Refresh hygiene).
import { parseSolverProgress } from './solverProgress';

// FM-04a Phase 43 — solver progress beat.
//
// Replaces the raw black solver-log dump (a #000 terminal pane that read as
// "developer console", not "engineering workbench") with a LIGHT-surface
// "solve progress" card: a Solver header + a status chip, a progress
// affordance (determinate when a marker is parseable, otherwise an
// indeterminate tokenized sweep), an elapsed-seconds readout that counts up
// while solving and freezes on completion, a "Solve complete" success state,
// and the log lines in a scrollable monospace area styled for the warm-light
// theme (NOT #000/#fff).
//
// Honesty (project Tier discipline): the percentage is NEVER fabricated. When
// no percent / increment / step marker can be parsed from the logs the bar
// degrades to an INDETERMINATE animated sweep (or a quiet rest state when not
// solving) — it does not invent a number. The elapsed timer is measured from
// a real start timestamp; it is not derived from the logs and is omitted when
// it cannot be measured (e.g. a solve that started before mount).
//
// Surface: LIGHT (white/paper card in the app shell) — NOT a dark-glass
// viewport overlay.
//
// The indeterminate-sweep keyframe (`fm04a-solve-sweep`) lives in index.css so
// it is suppressed under prefers-reduced-motion at the foundation level
// (anti-gaming guard B:-1).

/** A solve is "complete" when the label says so and we are no longer solving. */
function isCompleteLabel(label: string | null | undefined): boolean {
  if (typeof label !== 'string') return false;
  return /\b(complete|completed|done|success|succeeded|finished|finish)\b/i.test(
    label,
  );
}

function isFailedLabel(label: string | null | undefined): boolean {
  if (typeof label !== 'string') return false;
  return /\b(fail|failed|error|aborted|cancelled|canceled)\b/i.test(label);
}

export interface SolverProgressPanelProps {
  /** Solver output lines, newest appended last. */
  logs: string[];
  /** True while a solve is running. */
  solving: boolean;
  /** Short status string, e.g. "running" / "completed" / "failed" / null. */
  jobStatusLabel?: string | null;
}

const cardStyle: CSSProperties = {
  background: 'var(--bg-surface)',
  border: '1px solid var(--border)',
  borderRadius: 'var(--r-md)',
  padding: '14px',
  display: 'flex',
  flexDirection: 'column',
  gap: '10px',
  boxShadow: 'var(--elev-1)',
};

const headerRowStyle: CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'space-between',
  gap: '8px',
};

const titleStyle: CSSProperties = {
  color: 'var(--text-primary)',
  fontSize: 'var(--fs-sm)',
  fontWeight: 700,
  letterSpacing: '-0.01em',
};

const chipBaseStyle: CSSProperties = {
  display: 'inline-flex',
  alignItems: 'center',
  gap: '5px',
  fontSize: 'var(--fs-xs)',
  fontWeight: 700,
  letterSpacing: '0.02em',
  padding: '2px 9px',
  borderRadius: 'var(--r-full)',
  border: '1px solid var(--border)',
  whiteSpace: 'nowrap',
};

type ChipTone = 'running' | 'completed' | 'failed' | 'neutral';

function chipStyleFor(tone: ChipTone): CSSProperties {
  switch (tone) {
    case 'running':
      return {
        ...chipBaseStyle,
        color: 'var(--accent-600)',
        background: 'var(--accent-glow)',
        borderColor: 'var(--border-focus)',
      };
    case 'completed':
      return {
        ...chipBaseStyle,
        color: 'var(--success-600)',
        background: 'var(--success-glow)',
        borderColor: 'rgba(63, 122, 82, 0.35)',
      };
    case 'failed':
      return {
        ...chipBaseStyle,
        color: 'var(--danger-400)',
        background: 'rgba(197, 69, 59, 0.10)',
        borderColor: 'rgba(197, 69, 59, 0.35)',
      };
    default:
      return {
        ...chipBaseStyle,
        color: 'var(--text-muted)',
        background: 'rgba(42, 39, 34, 0.04)',
      };
  }
}

function chipToneFor(
  label: string | null | undefined,
  solving: boolean,
): ChipTone {
  if (isFailedLabel(label)) return 'failed';
  if (isCompleteLabel(label)) return 'completed';
  if (solving || /\b(running|solving|in[\s_-]?progress)\b/i.test(label ?? '')) {
    return 'running';
  }
  return 'neutral';
}

const trackStyle: CSSProperties = {
  position: 'relative',
  width: '100%',
  height: '6px',
  borderRadius: 'var(--r-full)',
  background: 'var(--c-200)',
  overflow: 'hidden',
};

const stageRowStyle: CSSProperties = {
  display: 'flex',
  alignItems: 'baseline',
  justifyContent: 'space-between',
  gap: '8px',
  fontSize: 'var(--fs-xs)',
  color: 'var(--text-muted)',
};

const elapsedStyle: CSSProperties = {
  fontVariantNumeric: 'tabular-nums',
  color: 'var(--text-secondary)',
};

const logAreaStyle: CSSProperties = {
  maxHeight: '160px',
  overflowY: 'auto',
  background: 'var(--c-100)',
  border: '1px solid var(--border)',
  borderRadius: 'var(--r-sm)',
  padding: '8px 10px',
  fontFamily: 'var(--font-mono)',
  fontSize: 'var(--fs-xs)',
  lineHeight: 1.55,
  color: 'var(--text-secondary)',
  whiteSpace: 'pre-wrap',
  wordBreak: 'break-word',
};

const completeRowStyle: CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  gap: '6px',
  color: 'var(--success-600)',
  fontSize: 'var(--fs-sm)',
  fontWeight: 700,
};

const emptyLogStyle: CSSProperties = {
  color: 'var(--text-muted)',
  fontStyle: 'italic',
  fontSize: 'var(--fs-xs)',
};

/**
 * LIGHT-surface solve-progress panel. See module header for the honesty
 * contract (no fabricated percent / measured-only elapsed timer).
 */
export function SolverProgressPanel({
  logs,
  solving,
  jobStatusLabel,
}: SolverProgressPanelProps) {
  const safeLogs = Array.isArray(logs) ? logs : [];

  const progress = parseSolverProgress(safeLogs);
  const tone = chipToneFor(jobStatusLabel, solving);
  const complete = !solving && isCompleteLabel(jobStatusLabel);

  // ---- Elapsed timer: measured from a real start timestamp ----------------
  // Resets when a NEW solve starts (solving false→true). Counts up via an
  // interval while solving, then freezes when solving ends. We never derive
  // elapsed from the logs; if a solve was already running at mount (no rising
  // edge observed) we omit the readout rather than show a wrong number.
  const startRef = useRef<number | null>(null);
  // null = effect has not run yet (mount). After the first run it holds the
  // previous `solving` value so we can detect a genuine false→true transition.
  const prevSolvingRef = useRef<boolean | null>(null);
  const [elapsedMs, setElapsedMs] = useState<number | null>(null);

  useEffect(() => {
    const prevSolving = prevSolvingRef.current;
    prevSolvingRef.current = solving;

    // Start (or restart) the MEASURED clock when a solve begins. Two genuine
    // starts: (a) a rising edge (false→true) on an already-mounted panel, and
    // (b) the COMMON case (Codex R0 P2) where this panel is conditionally
    // mounted AT solve start — `showConsole` flips true together with the run,
    // so the first effect run sees prevSolving===null && solving===true. Both
    // are real starts (mount ≈ solve start, so the measurement is accurate);
    // only an ONGOING solve (prevSolving===true) must not reset. Ref write
    // only — NO setState in the effect body (react-hooks/set-state-in-effect);
    // the readout updates from the timer callbacks below and freezes at its
    // last value when they are cleared on stop.
    if (solving && prevSolving !== true) {
      startRef.current = Date.now();
    }

    if (!solving || startRef.current === null) return undefined;

    const tick = () => {
      if (startRef.current !== null) setElapsedMs(Date.now() - startRef.current);
    };
    // A 0ms kick paints (and, on a re-solve, resets) the readout promptly
    // without a synchronous setState; the interval then counts up.
    const kick = window.setTimeout(tick, 0);
    const id = window.setInterval(tick, 250);
    return () => {
      window.clearTimeout(kick);
      window.clearInterval(id);
    };
  }, [solving]);

  // `elapsedMs` is set to a number ONLY after a measurable start (rising edge);
  // it stays null when a solve was already running at mount. So it alone tells
  // us whether to show the readout — we must NOT read startRef.current during
  // render (react-hooks: no ref access in render).
  const showElapsed = elapsedMs !== null;
  const elapsedSeconds = showElapsed ? Math.floor((elapsedMs as number) / 1000) : 0;

  // ---- Auto-scroll the log area to the newest line ------------------------
  const logRef = useRef<HTMLDivElement | null>(null);
  useLayoutEffect(() => {
    const el = logRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [safeLogs.length]);

  const chipText =
    typeof jobStatusLabel === 'string' && jobStatusLabel.trim().length > 0
      ? jobStatusLabel.trim()
      : null;

  return (
    <div data-testid="solver-progress-panel" style={cardStyle}>
      <div style={headerRowStyle}>
        <span style={titleStyle}>Solver</span>
        {chipText ? (
          <span data-testid="solver-status-chip" data-tone={tone} style={chipStyleFor(tone)}>
            {chipText}
          </span>
        ) : null}
      </div>

      {/* Progress affordance — determinate bar OR indeterminate sweep. */}
      {complete ? null : progress.mode === 'determinate' ? (
        <div>
          <div
            data-testid="solver-progress-track"
            data-mode="determinate"
            role="progressbar"
            aria-valuemin={0}
            aria-valuemax={100}
            aria-valuenow={Math.round((progress.fraction ?? 0) * 100)}
            style={trackStyle}
          >
            <div
              data-testid="solver-progress-fill"
              style={{
                position: 'absolute',
                inset: 0,
                width: `${Math.round((progress.fraction ?? 0) * 100)}%`,
                background: 'var(--accent)',
                borderRadius: 'var(--r-full)',
                transition: 'width var(--dur-base) var(--ease-out)',
              }}
            />
          </div>
          {progress.stage ? (
            <div style={{ ...stageRowStyle, marginTop: '6px' }}>
              <span>{progress.stage}</span>
              {showElapsed ? (
                <span data-testid="solver-elapsed" style={elapsedStyle}>
                  {elapsedSeconds}s
                </span>
              ) : null}
            </div>
          ) : null}
        </div>
      ) : (
        <div>
          <div
            data-testid="solver-progress-track"
            data-mode="indeterminate"
            role="progressbar"
            aria-label={solving ? 'Solving (progress indeterminate)' : 'Solver idle'}
            style={trackStyle}
          >
            {solving ? (
              <div
                data-testid="solver-progress-sweep"
                className="solve-sweep"
                style={{
                  position: 'absolute',
                  top: 0,
                  bottom: 0,
                  width: '38%',
                  background:
                    'linear-gradient(90deg, transparent, var(--accent-400), transparent)',
                  borderRadius: 'var(--r-full)',
                }}
              />
            ) : null}
          </div>
          {solving ? (
            <div style={{ ...stageRowStyle, marginTop: '6px' }}>
              <span>Solving…</span>
              {showElapsed ? (
                <span data-testid="solver-elapsed" style={elapsedStyle}>
                  {elapsedSeconds}s
                </span>
              ) : null}
            </div>
          ) : null}
        </div>
      )}

      {/* Solve-complete success state. */}
      {complete ? (
        <div data-testid="solver-complete" style={completeRowStyle}>
          <span aria-hidden style={{ fontSize: 'var(--fs-md)', lineHeight: 1 }}>
            ✓
          </span>
          <span>Solve complete</span>
          {showElapsed ? (
            <span
              data-testid="solver-elapsed"
              style={{ ...elapsedStyle, fontWeight: 600, marginLeft: 'auto' }}
            >
              {elapsedSeconds}s
            </span>
          ) : null}
        </div>
      ) : null}

      {/* Scrollable monospace log area — LIGHT theme (NOT #000/#fff). */}
      <div ref={logRef} data-testid="solver-log-area" style={logAreaStyle}>
        {safeLogs.length === 0 ? (
          <span data-testid="solver-log-empty" style={emptyLogStyle}>
            No solver output yet.
          </span>
        ) : (
          safeLogs.map((line, i) => (
            <div key={i} data-testid="solver-log-line">
              {line}
            </div>
          ))
        )}
      </div>
    </div>
  );
}
