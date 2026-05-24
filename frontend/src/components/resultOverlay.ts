// FM-04a Phase 40 B step 1 — two-result comparison overlay: mesh-correspondence
// kernel (pure, frontend-only, no WebGL).
//
// PURPOSE: the workbench needs to overlay TWO DISTINCT solved results (two cases,
// or two steps / runs of the same model) in the result-mesh viewport — the last
// unmet Dim 5 90-anchor sub-bullet ("comparison cuts — overlay two results"). This
// is NOT the CompanionViewport (which is a side-by-side compare-CUTS of ONE result).
//
// HONESTY (绝对诚实客观): a per-node DIFFERENCE field between two results is only
// meaningful when the two meshes actually correspond — i.e. share node labels. The
// node `label` (ResultMeshNode.label, always present) is the ONLY stable join key;
// element `label` is optional, so elements are never joined. When the two meshes do
// NOT share enough node labels (e.g. two unrelated cases with different meshes),
// there is NO honest difference field — the caller must fall back to a geometric
// overlay only and say so. This module NEVER resamples / interpolates one mesh onto
// the other (that would be a solver-truth concern); it reports the label-set
// correspondence and lets the caller render + label honestly.
//
// Pure set arithmetic — no three.js, no DOM — fully unit-testable.

import type { ResultMeshFrame } from '../resultMeshPlayback';

export interface MeshCorrespondence {
  /** Node labels present in BOTH frames, sorted ascending. The ONLY basis on
   * which a per-node difference field could honestly be computed. */
  readonly sharedLabels: number[];
  /** Node labels present only in frame A / only in frame B (sorted). */
  readonly onlyALabels: number[];
  readonly onlyBLabels: number[];
  /** Distinct node-label counts (deduplicated). */
  readonly countA: number;
  readonly countB: number;
  readonly sharedCount: number;
  /** sharedCount / max(countA, countB). 1 = identical label sets; 0 = disjoint. */
  readonly correspondenceRatio: number;
  /** Whether the two meshes correspond ENOUGH to support an honest difference
   * field: sharedCount > 0 AND correspondenceRatio ≥ the threshold. When false,
   * the caller MUST render a geometric overlay only (no fabricated Δ). */
  readonly corresponds: boolean;
  /** The threshold used for `corresponds` (echoed for transparency). */
  readonly diffThreshold: number;
  /** Human-readable honesty note for the caller to surface verbatim. */
  readonly note: string;
}

/** Default minimum correspondence ratio to consider a difference field honest:
 * at least half of the larger mesh's nodes must be shared. Below this, a Δ would
 * be computed on a coincidental label sliver and mislead. */
export const DEFAULT_DIFF_THRESHOLD = 0.5;

function distinctLabels(frame: ResultMeshFrame | null | undefined): Set<number> {
  const labels = new Set<number>();
  if (!frame) return labels;
  for (const node of frame.nodes) {
    if (Number.isFinite(node.label)) labels.add(node.label);
  }
  return labels;
}

/**
 * Compute the node-label correspondence between two result frames. Pure: depends
 * only on the frames' node-label sets. Sorted outputs are deterministic for
 * stable tests. `diffThreshold` ∈ [0,1] gates the honest `corresponds` flag.
 */
export function computeMeshCorrespondence(
  frameA: ResultMeshFrame | null | undefined,
  frameB: ResultMeshFrame | null | undefined,
  diffThreshold: number = DEFAULT_DIFF_THRESHOLD,
): MeshCorrespondence {
  const a = distinctLabels(frameA);
  const b = distinctLabels(frameB);

  const shared: number[] = [];
  const onlyA: number[] = [];
  for (const label of a) (b.has(label) ? shared : onlyA).push(label);
  const onlyB: number[] = [];
  for (const label of b) if (!a.has(label)) onlyB.push(label);

  const countA = a.size;
  const countB = b.size;
  const sharedCount = shared.length;
  const correspondenceRatio =
    Math.max(countA, countB) > 0 ? sharedCount / Math.max(countA, countB) : 0;
  const corresponds = sharedCount > 0 && correspondenceRatio >= diffThreshold;

  const note = corresponds
    ? `${sharedCount} shared node label(s) of ${countA}/${countB} ` +
      `(${(correspondenceRatio * 100).toFixed(0)}%); a difference field is ` +
      `computable on the shared set only — unmatched nodes are excluded.`
    : sharedCount === 0
      ? `No shared node labels — the two meshes do not correspond; ` +
        `geometric overlay only, no difference field.`
      : `Only ${sharedCount} of ${countA}/${countB} node labels shared ` +
        `(${(correspondenceRatio * 100).toFixed(0)}% < ` +
        `${(diffThreshold * 100).toFixed(0)}% threshold) — too little to ` +
        `support an honest difference field; geometric overlay only.`;

  return {
    sharedLabels: shared.sort((x, y) => x - y),
    onlyALabels: onlyA.sort((x, y) => x - y),
    onlyBLabels: onlyB.sort((x, y) => x - y),
    countA,
    countB,
    sharedCount,
    correspondenceRatio,
    corresponds,
    diffThreshold,
    note,
  };
}
