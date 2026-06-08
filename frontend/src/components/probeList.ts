// FM-04a Phase 24 D — multi-node probe list pure-function state machine.
//
// Phase 23 C shipped single-node pick; Phase 24 D lifts the reviewer
// affordance to multi-pick comparison. State is a small immutable
// reducer; the UI component imports and dispatches.
//
// Anti-gaming guard D:-2 — entries are stored in PIN ORDER (the
// chronological order user pinned them). Renderers must NOT sort by
// label or array index; if 5 nodes pinned as [7, 42, 99, 11, 3] the
// list reads [7, 42, 99, 11, 3].
//
// Tier 1 / Tier 2 engineering candidate; not signed validation; not
// benchmark agreement.

import type { PickedNodeInfo } from './viewportRaycaster';

/** Hard cap. When pinning a 9th node, the FIRST-pinned entry is
 * evicted (FIFO). Chosen so the comparison table stays scannable
 * on a 1080p reviewer monitor. */
export const PROBE_LIST_MAX = 8;

export interface ProbeListState {
  /** Pinned nodes in INSERTION ORDER. Max length = PROBE_LIST_MAX. */
  entries: readonly PickedNodeInfo[];
}

export const PROBE_LIST_INITIAL_STATE: ProbeListState = {
  entries: [],
};

/**
 * Add a probe to the list. If a probe with the same node label is
 * already pinned, this is a no-op (de-duplication). When the list is
 * at capacity, the OLDEST entry (index 0) is evicted to make room.
 *
 * Pure: returns a new ProbeListState, never mutates input.
 */
export function addProbeEntry(
  state: ProbeListState,
  entry: PickedNodeInfo,
): ProbeListState {
  // De-dup by label so the same node doesn't appear twice.
  if (state.entries.some((e) => e.label === entry.label)) {
    return state;
  }
  const existing = state.entries.slice();
  if (existing.length >= PROBE_LIST_MAX) {
    existing.shift();
  }
  existing.push(entry);
  return { entries: existing };
}

/**
 * Remove a probe by node label. No-op if label is not present.
 */
export function removeProbeEntry(
  state: ProbeListState,
  label: number,
): ProbeListState {
  if (!state.entries.some((e) => e.label === label)) return state;
  return { entries: state.entries.filter((e) => e.label !== label) };
}

/**
 * Clear all probes. Returns initial state.
 */
export function clearAllProbes(_state: ProbeListState): ProbeListState {
  return PROBE_LIST_INITIAL_STATE;
}

/**
 * Whether a given node label is already pinned.
 */
export function hasProbe(state: ProbeListState, label: number): boolean {
  return state.entries.some((e) => e.label === label);
}

/**
 * Count of pinned probes (0..PROBE_LIST_MAX).
 */
export function probeCount(state: ProbeListState): number {
  return state.entries.length;
}

/**
 * Serialize the probe list to a CSV string. Header row +
 * one row per entry, in PIN ORDER (carries Phase 24 D's D:-2
 * anti-gaming guarantee to the export layer).
 *
 * Empty list → header-only string (still valid CSV).
 *
 * Phase 25 D D:-1 anti-gaming guard: any field containing a comma,
 * a double-quote, or a newline gets RFC-4180 quoted; double-quotes
 * inside such a field are doubled. Numeric NaN / ±∞ are serialized
 * as the empty cell so spreadsheets don't choke. Null fieldValue
 * becomes the empty cell too.
 */
export function serializeProbeListAsCsv(state: ProbeListState): string {
  const header = 'node_label,x_m,y_m,z_m,field_value';
  const rows = state.entries.map((entry) => {
    const cells = [
      formatNumericCell(entry.label),
      formatNumericCell(entry.position[0]),
      formatNumericCell(entry.position[1]),
      formatNumericCell(entry.position[2]),
      entry.fieldValue === null ? '' : formatNumericCell(entry.fieldValue),
    ];
    return cells.map(escapeCsvCell).join(',');
  });
  return [header, ...rows].join('\n') + '\n';
}

function formatNumericCell(value: number): string {
  if (!Number.isFinite(value)) return '';
  // Use full-precision JS toString so reviewers can copy verbatim.
  return String(value);
}

function escapeCsvCell(value: string): string {
  if (/[",\n\r]/.test(value)) {
    return '"' + value.replace(/"/g, '""') + '"';
  }
  return value;
}

/** FM-04a Phase 26 C — diff pair against the baseline probe.
 *
 * Each entry pairs with its absolute Δ vs entry 0 (the BASELINE,
 * which is the FIRST-pinned probe by D:-2 PIN-ORDER contract):
 *
 *   - baseline (index 0) itself has `diff: null` (Δ vs self is 0
 *     but rendering null avoids the meaningless 0 row that
 *     suggests a real measurement)
 *   - any entry whose `fieldValue` is null gets `diff: null`
 *   - any entry where the baseline's `fieldValue` is null gets
 *     `diff: null` (no anchor to subtract from)
 *   - otherwise `diff = entry.fieldValue - baseline.fieldValue`
 *
 * Reviewer narrative: "Pin the reference point first, then pin the
 * comparison points. The Δ column reads stress concentration ratios
 * without context-switching back to the legend gradient."
 *
 * Pure: returns a new array; mutates nothing.
 */
export interface ProbeDiffPair {
  entry: PickedNodeInfo;
  /** Δ = entry.fieldValue − baseline.fieldValue, or null when either
   * side is null OR when this row IS the baseline. */
  diff: number | null;
  /** Whether this row is the baseline (entry index 0). */
  isBaseline: boolean;
}

export function buildDiffPairs(state: ProbeListState): ProbeDiffPair[] {
  if (state.entries.length === 0) return [];
  const baseline = state.entries[0];
  return state.entries.map((entry, index) => {
    if (index === 0) {
      return { entry, diff: null, isBaseline: true };
    }
    if (entry.fieldValue === null || baseline.fieldValue === null) {
      return { entry, diff: null, isBaseline: false };
    }
    return {
      entry,
      diff: entry.fieldValue - baseline.fieldValue,
      isBaseline: false,
    };
  });
}
