// FM-04a Phase 27 D — probe-list save/restore across sessions.
//
// Phase 25 D shipped probe-list CSV export (one-way data flow);
// Phase 27 D closes the loop with localStorage persistence so a
// reviewer's pinned-probe list survives a browser refresh.
//
// Anti-gaming guard C:-1 — persistence is scoped BY case_id. The
// localStorage key includes the case_id verbatim
// (`fm04a.probe-list.v1.<case_id>`), so switching cases loads
// DIFFERENT lists, not bleeding state across cases. A reviewer
// inspecting cantilever-beam-modal-candidate sees their pinned
// probes for THAT case; switching to plate-simply-supported-
// candidate loads ITS pinned probes (empty by default).
//
// Failure modes (graceful fallback to PROBE_LIST_INITIAL_STATE):
//   * localStorage unavailable (SSR / test env without jsdom)
//   * key absent
//   * value malformed JSON
//   * value JSON but wrong shape (missing entries / non-array)
//   * any entry missing required label / position / fieldValue
//
// Pure-function module. All I/O wrapped in try/catch so callers
// can compose without defensive surrounding.
//
// Tier 1 / Tier 2 engineering candidate; not signed validation;
// not benchmark agreement.

import type { PickedNodeInfo } from './viewportRaycaster';
import {
  PROBE_LIST_INITIAL_STATE,
  type ProbeListState,
} from './probeList';

/** LocalStorage key prefix. Case_id is appended verbatim. */
export const PROBE_LIST_LS_KEY_PREFIX = 'fm04a.probe-list.v1.';

/** Compose the storage key for a given case_id. Pure helper. */
export function probeListStorageKey(caseId: string): string {
  return `${PROBE_LIST_LS_KEY_PREFIX}${caseId}`;
}

/** Load the persisted probe list for `caseId`. Returns initial
 * state on ANY failure (missing key / malformed JSON / wrong shape /
 * storage unavailable). Never throws.
 *
 * FM-04a Phase 29 D — emit a single console.warn on parse/shape
 * failure so reviewers can debug a corrupted localStorage payload
 * instead of getting a silent reset. The warning is keyed by
 * caseId + reason; missing-key (raw === null) is NOT a warning
 * (that's the normal first-load path). */
export function loadProbeList(
  caseId: string,
  globalRef: typeof globalThis = globalThis,
): ProbeListState {
  const ls = (globalRef as { localStorage?: Storage }).localStorage;
  if (!ls) return PROBE_LIST_INITIAL_STATE;
  try {
    const raw = ls.getItem(probeListStorageKey(caseId));
    if (!raw) return PROBE_LIST_INITIAL_STATE;
    let parsed: unknown;
    try {
      parsed = JSON.parse(raw);
    } catch (err) {
      console.warn(
        `[FM-04a probeListStorage] discarded malformed JSON for case '${caseId}': ${(err as Error).message}`,
      );
      return PROBE_LIST_INITIAL_STATE;
    }
    if (!isValidPersistedShape(parsed)) {
      console.warn(
        `[FM-04a probeListStorage] discarded wrong-shape payload for case '${caseId}'`,
      );
      return PROBE_LIST_INITIAL_STATE;
    }
    return { entries: parsed.entries };
  } catch (err) {
    console.warn(
      `[FM-04a probeListStorage] storage access failed for case '${caseId}': ${(err as Error).message}`,
    );
    return PROBE_LIST_INITIAL_STATE;
  }
}

/** Save the probe list for `caseId`. Silently swallows quota /
 * SecurityError exceptions; never throws. */
export function saveProbeList(
  caseId: string,
  state: ProbeListState,
  globalRef: typeof globalThis = globalThis,
): void {
  const ls = (globalRef as { localStorage?: Storage }).localStorage;
  if (!ls) return;
  try {
    // Serialize ONLY the entries array; the wrapping
    // { entries: [...] } shape matches ProbeListState so load can
    // hand the result back unchanged.
    const payload = JSON.stringify({ entries: state.entries });
    ls.setItem(probeListStorageKey(caseId), payload);
  } catch {
    /* swallow */
  }
}

/** Remove the persisted entry for `caseId`. Useful for "clear all"
 * UX flows or test teardown. */
export function clearProbeListStorage(
  caseId: string,
  globalRef: typeof globalThis = globalThis,
): void {
  const ls = (globalRef as { localStorage?: Storage }).localStorage;
  if (!ls) return;
  try {
    ls.removeItem(probeListStorageKey(caseId));
  } catch {
    /* swallow */
  }
}

/** Type-guard: does the parsed JSON match { entries: PickedNodeInfo[] }? */
function isValidPersistedShape(
  candidate: unknown,
): candidate is { entries: PickedNodeInfo[] } {
  if (!candidate || typeof candidate !== 'object') return false;
  const c = candidate as { entries?: unknown };
  if (!Array.isArray(c.entries)) return false;
  return c.entries.every((entry) => isValidPickedNode(entry));
}

function isValidPickedNode(candidate: unknown): candidate is PickedNodeInfo {
  if (!candidate || typeof candidate !== 'object') return false;
  const c = candidate as {
    label?: unknown;
    position?: unknown;
    fieldValue?: unknown;
  };
  if (typeof c.label !== 'number') return false;
  if (!Array.isArray(c.position) || c.position.length !== 3) return false;
  if (!c.position.every((x) => typeof x === 'number')) return false;
  if (c.fieldValue !== null && typeof c.fieldValue !== 'number') return false;
  return true;
}
