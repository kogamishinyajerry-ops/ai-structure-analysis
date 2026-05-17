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
