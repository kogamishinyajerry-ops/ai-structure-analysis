// FM-04a Phase 43 Slice 2 — solver-progress parsing (pure helpers).
//
// Extracted from SolverProgressPanel.tsx so the .tsx file only exports a
// component (Vite Fast-Refresh / react-refresh hygiene) and the log→progress
// parse is unit-testable in isolation, shared with the component.

export type SolverProgressMode = 'determinate' | 'indeterminate';

export interface SolverProgress {
  /** 'determinate' when a fraction was parsed; 'indeterminate' otherwise. */
  mode: SolverProgressMode;
  /** Clamped 0..1 progress fraction — present ONLY on the determinate path. */
  fraction?: number;
  /** Short human stage label parsed from the marker, e.g. "Increment 3 of 10". */
  stage?: string;
}

/**
 * Pure log → progress parse. Scans the most-recent-first lines for, in order:
 *   1. an explicit percentage    e.g. "Solving... 42%" / "progress: 42 %"
 *   2. an "increment/step k of N" e.g. "increment 3 of 10" / "step 3/10"
 * The first parseable marker wins (newest line is authoritative). When nothing
 * matches it returns { mode: 'indeterminate' } — it NEVER fabricates a number.
 *
 * Graceful: empty / non-array input → indeterminate.
 */
export function parseSolverProgress(logs: string[]): SolverProgress {
  if (!Array.isArray(logs) || logs.length === 0) {
    return { mode: 'indeterminate' };
  }

  // Newest line is the most authoritative — walk from the end.
  for (let i = logs.length - 1; i >= 0; i -= 1) {
    const line = logs[i];
    if (typeof line !== 'string' || line.trim().length === 0) continue;

    // 1) explicit percentage: a number (optionally fractional) followed by %.
    const pct = line.match(/(\d+(?:\.\d+)?)\s*%/);
    if (pct) {
      const value = Number.parseFloat(pct[1]);
      if (Number.isFinite(value)) {
        const fraction = clamp01(value / 100);
        return {
          mode: 'determinate',
          fraction,
          stage: `${trimPct(value)}%`,
        };
      }
    }

    // 2) "increment/step k of N" or "increment/step k / N".
    const kofn = line.match(
      /\b(increment|step|iteration|iter)\b\s*#?\s*(\d+)\s*(?:of|\/)\s*(\d+)/i,
    );
    if (kofn) {
      const k = Number.parseInt(kofn[2], 10);
      const n = Number.parseInt(kofn[3], 10);
      if (Number.isFinite(k) && Number.isFinite(n) && n > 0) {
        const fraction = clamp01(k / n);
        const word = capitalize(kofn[1].toLowerCase());
        return {
          mode: 'determinate',
          fraction,
          stage: `${word} ${k} of ${n}`,
        };
      }
    }
  }

  return { mode: 'indeterminate' };
}

function clamp01(x: number): number {
  if (!Number.isFinite(x)) return 0;
  if (x < 0) return 0;
  if (x > 1) return 1;
  return x;
}

function trimPct(value: number): string {
  // Whole numbers render bare; fractions keep at most one decimal.
  return Number.isInteger(value) ? String(value) : value.toFixed(1);
}

function capitalize(s: string): string {
  return s.length === 0 ? s : s[0].toUpperCase() + s.slice(1);
}
