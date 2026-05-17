// FM-04a Phase 24 C — viewport raycaster + filter helpers extracted
// from ResultMeshWebGLViewport.tsx for LOC discipline. Pure functions
// only. No Three.js, no React.
//
// Constraint: ZERO behavior change. The functions and types here are
// byte-identical to their Phase 23 home in
// ResultMeshWebGLViewport.tsx — only the module location changed.

import type { ResultMeshElement, ResultMeshFrame } from '../resultMeshPlayback';
import { componentValue, type StressComponent } from '../stressDerivatives';

/** FM-04a Phase 23 D — element-value threshold filter. */
export interface ValueFilterState {
  /** Lower bound; null means -∞. */
  minValue: number | null;
  /** Upper bound; null means +∞. */
  maxValue: number | null;
  /** 'inside' keeps elements inside [minValue, maxValue];
   *  'outside' keeps elements OUTSIDE that range. */
  mode: 'inside' | 'outside';
}

/** FM-04a Phase 23 C — payload of a successful node pick. */
export interface PickedNodeInfo {
  /** Original node label from the frame's `nodes` list. */
  label: number;
  /** World-space coordinates (m). */
  position: [number, number, number];
  /** The scalar value the viewport is currently coloring by
   * (Mises / σ_xx / etc — depends on `fieldComponent`). Falls back
   * to `value` when no tensor is present. May be `null` when no
   * element near the picked node carries a value. */
  fieldValue: number | null;
}

/** FM-04a Phase 23 C — find the closest node in the frame to a
 * world-space point. Used after raycasting to map an intersection
 * point back to a frame node label. Returns null when the frame
 * has no nodes. */
export function findClosestNode(
  frame: ResultMeshFrame,
  worldPoint: [number, number, number],
  nodeCoords: Map<number, [number, number, number]>,
): { label: number; position: [number, number, number]; distance: number } | null {
  let best: { label: number; position: [number, number, number]; distance: number } | null = null;
  for (const node of frame.nodes) {
    const coords = nodeCoords.get(node.label);
    if (!coords) continue;
    const dx = coords[0] - worldPoint[0];
    const dy = coords[1] - worldPoint[1];
    const dz = coords[2] - worldPoint[2];
    const d2 = dx * dx + dy * dy + dz * dz;
    if (best === null || d2 < best.distance) {
      best = {
        label: node.label,
        position: [coords[0], coords[1], coords[2]],
        distance: d2,
      };
    }
  }
  if (best) {
    return { ...best, distance: Math.sqrt(best.distance) };
  }
  return null;
}

/** FM-04a Phase 23 C — find the field value of the element nearest
 * (in connectivity) to the picked node. Walks the frame's elements
 * to find one whose connectivity contains `nodeLabel`; returns its
 * derived scalar via the same component-switcher path. Returns null
 * when no element references this node or the candidate element has
 * no value. */
export function fieldValueAtNode(
  frame: ResultMeshFrame,
  nodeLabel: number,
  fieldComponent: StressComponent,
): number | null {
  for (const element of frame.elements) {
    if (!element.connectivity?.includes(nodeLabel)) continue;
    if (element.stressTensor) {
      return componentValue(element.stressTensor, fieldComponent, element.value ?? 0);
    }
    if (element.value !== undefined) return element.value;
  }
  return null;
}

/** FM-04a Phase 23 D — element value selector for the threshold
 * filter. Uses the same component-switcher path as the coloring
 * (`colorForElement`) so the filter compares against the SAME
 * scalar the reviewer sees on the gradient. */
function elementFilterValue(
  element: ResultMeshElement,
  fieldComponent: StressComponent,
): number | undefined {
  if (element.alive === false) return undefined;
  if (element.partRole === 'projectile') return undefined;
  if (element.stressTensor) {
    return componentValue(
      element.stressTensor,
      fieldComponent,
      element.value ?? 0,
    );
  }
  return element.value;
}

/** FM-04a Phase 23 D — pure-function filter predicate. Returns true
 * when the element should RENDER. Elements with no derivable value
 * (alive=false, projectile, no value, no tensor) ALWAYS render
 * regardless of filter — that's the D:-1 anti-gaming guard. */
export function applyValueFilter(
  element: ResultMeshElement,
  filter: ValueFilterState | null | undefined,
  fieldComponent: StressComponent = 'mises',
): boolean {
  if (!filter) return true;
  const v = elementFilterValue(element, fieldComponent);
  // D:-1: elements without a value are retained.
  if (v === undefined || !Number.isFinite(v)) return true;
  const lo = filter.minValue ?? Number.NEGATIVE_INFINITY;
  const hi = filter.maxValue ?? Number.POSITIVE_INFINITY;
  const inside = v >= lo && v <= hi;
  return filter.mode === 'inside' ? inside : !inside;
}
