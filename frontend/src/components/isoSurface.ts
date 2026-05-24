// FM-04a Phase 40 A — iso-surface extraction (pure, frontend-only, no WebGL).
//
// HONESTY (Phase 40 T:-1, per the 绝对诚实客观 contract): the solved FEA result
// field is per-ELEMENT and genuinely DISCONTINUOUS across element boundaries.
// An iso-surface needs a NODAL (continuous) field, so this module averages each
// element's scalar onto its corner nodes — the standard "cell data → point data"
// smoothing (e.g. ParaView's CellDataToPointData). The output is therefore a
// **SMOOTHED VIZ APPROXIMATION (Tier 0 viz)**, NOT the solved per-element field:
// it can imply more continuity than the FEA actually produced. Callers MUST label
// it as such, and the per-element coloring MUST remain the default truth view.
//
// v1 scope: tetrahedral elements only (C3D4 / C3D10 — the first 4 connectivity
// entries are the corner nodes). Non-tet elements (C3D8 hex / C3D6 wedge / S4
// shell / B31 beam) are SKIPPED and reported in `metadata.skippedElementTypes`
// (hex/wedge tet-decomposition is a future increment). This keeps v1 correct and
// honest rather than approximating mixed elements badly.
//
// Pure geometry — no three.js, no DOM — so it is fully unit-testable in jsdom.

import type { ResultMeshElement, ResultMeshFrame } from '../resultMeshPlayback';

/** A scalar accessor: maps an element to the field value the iso-surface is cut
 * against (e.g. von Mises, σ_xx, or the generic `value`). Returns undefined/NaN
 * to exclude the element. Decouples this module from the legend's
 * field-component logic. */
export type ElementScalarAccessor = (element: ResultMeshElement) => number | undefined;

export interface IsoTriangle {
  readonly a: readonly [number, number, number];
  readonly b: readonly [number, number, number];
  readonly c: readonly [number, number, number];
}

export interface IsoSurfaceMetadata {
  /** Always true: the nodal field was averaged from per-element values. */
  readonly smoothed: true;
  readonly threshold: number;
  readonly includedElementTypes: string[];
  readonly skippedElementTypes: string[];
  /** Nodes that received at least one averaged element value. */
  readonly nodalCount: number;
  /** Tetrahedra actually marched (had 4 corner nodes with value + coords). */
  readonly tetCount: number;
  readonly triangleCount: number;
  /** Human-readable honesty note for the caller to surface verbatim. */
  readonly note: string;
}

export interface IsoSurfaceResult {
  readonly triangles: IsoTriangle[];
  readonly metadata: IsoSurfaceMetadata;
}

type Vec3 = [number, number, number];

const TET_TYPES = new Set(['C3D4', 'C3D10']);

function isTetType(type: string | undefined): boolean {
  return type != null && TET_TYPES.has(type.toUpperCase());
}

const HONESTY_NOTE =
  'Smoothed viz approximation (Tier 0): nodal field averaged from per-element ' +
  'values; the solved per-element field is discontinuous. Not signed validation.';

/**
 * Average each element's scalar onto its corner nodes (cell→point smoothing).
 * Returns a Map of nodeLabel → averaged value. Only tetrahedral elements with a
 * finite scalar and ≥4 connectivity entries contribute. Exported for direct
 * unit testing of the smoothing step.
 */
export function averageElementValuesToNodes(
  frame: ResultMeshFrame,
  scalarFor: ElementScalarAccessor,
): Map<number, number> {
  const sums = new Map<number, number>();
  const counts = new Map<number, number>();
  for (const element of frame.elements) {
    if (!isTetType(element.type)) continue;
    const scalar = scalarFor(element);
    if (scalar == null || !Number.isFinite(scalar)) continue;
    const conn = element.connectivity;
    if (!conn || conn.length < 4) continue;
    for (let i = 0; i < 4; i++) {
      const label = conn[i];
      sums.set(label, (sums.get(label) ?? 0) + scalar);
      counts.set(label, (counts.get(label) ?? 0) + 1);
    }
  }
  const averaged = new Map<number, number>();
  for (const [label, sum] of sums) {
    const count = counts.get(label) ?? 1;
    averaged.set(label, sum / count);
  }
  return averaged;
}

/** Linear interpolation of the iso-crossing point on edge (pa,va)→(pb,vb). */
function interpEdge(pa: Vec3, va: number, pb: Vec3, vb: number, threshold: number): Vec3 {
  const delta = vb - va;
  // Endpoints straddle the threshold so delta ≠ 0 here; the 0.5 fallback is
  // defensive only (never reached for a genuine crossing).
  const frac = delta === 0 ? 0.5 : (threshold - va) / delta;
  return [
    pa[0] + (pb[0] - pa[0]) * frac,
    pa[1] + (pb[1] - pa[1]) * frac,
    pa[2] + (pb[2] - pa[2]) * frac,
  ];
}

/**
 * Marching-tetrahedra for a single tet. `pos`/`val` are the 4 corner positions
 * and nodal values; a corner is "inside" when its value ≥ threshold. Emits 0, 1,
 * or 2 triangles per the standard 4-vertex cases. Exported for direct unit
 * testing of the geometry kernel (independent of the cell→point smoothing).
 */
export function marchTetrahedron(
  pos: readonly Vec3[],
  val: readonly number[],
  threshold: number,
): IsoTriangle[] {
  const inside: number[] = [];
  const outside: number[] = [];
  for (let i = 0; i < 4; i++) (val[i] >= threshold ? inside : outside).push(i);

  if (inside.length === 0 || inside.length === 4) return [];

  if (inside.length === 1) {
    const i = inside[0];
    const [o0, o1, o2] = outside;
    return [
      {
        a: interpEdge(pos[i], val[i], pos[o0], val[o0], threshold),
        b: interpEdge(pos[i], val[i], pos[o1], val[o1], threshold),
        c: interpEdge(pos[i], val[i], pos[o2], val[o2], threshold),
      },
    ];
  }

  if (inside.length === 3) {
    const o = outside[0];
    const [i0, i1, i2] = inside;
    return [
      {
        a: interpEdge(pos[o], val[o], pos[i0], val[i0], threshold),
        b: interpEdge(pos[o], val[o], pos[i1], val[i1], threshold),
        c: interpEdge(pos[o], val[o], pos[i2], val[i2], threshold),
      },
    ];
  }

  // inside.length === 2 → the crossing is a quad (two triangles).
  const [i0, i1] = inside;
  const [o0, o1] = outside;
  const p00 = interpEdge(pos[i0], val[i0], pos[o0], val[o0], threshold);
  const p01 = interpEdge(pos[i0], val[i0], pos[o1], val[o1], threshold);
  const p10 = interpEdge(pos[i1], val[i1], pos[o0], val[o0], threshold);
  const p11 = interpEdge(pos[i1], val[i1], pos[o1], val[o1], threshold);
  return [
    { a: p00, b: p01, c: p11 },
    { a: p00, b: p11, c: p10 },
  ];
}

/**
 * Extract an iso-surface (triangle soup) from a result frame at `threshold`,
 * cutting against the field exposed by `scalarFor`. See the module header for
 * the honesty contract: this is a smoothed Tier-0 viz approximation over
 * tetrahedral elements only.
 */
export function extractIsoSurface(
  frame: ResultMeshFrame,
  threshold: number,
  scalarFor: ElementScalarAccessor,
): IsoSurfaceResult {
  const nodalValues = averageElementValuesToNodes(frame, scalarFor);

  const nodeCoords = new Map<number, Vec3>();
  for (const node of frame.nodes) {
    const c = node.coordinates;
    if (c && c.length >= 3) nodeCoords.set(node.label, [c[0], c[1], c[2]]);
  }

  const included = new Set<string>();
  const skipped = new Set<string>();
  const triangles: IsoTriangle[] = [];
  let tetCount = 0;

  for (const element of frame.elements) {
    const typeLabel = (element.type ?? 'UNKNOWN').toUpperCase();
    if (!isTetType(element.type)) {
      skipped.add(typeLabel);
      continue;
    }
    const conn = element.connectivity;
    if (!conn || conn.length < 4) {
      skipped.add(typeLabel);
      continue;
    }
    const pos: Vec3[] = [];
    const val: number[] = [];
    let usable = true;
    for (let i = 0; i < 4; i++) {
      const label = conn[i];
      const p = nodeCoords.get(label);
      const v = nodalValues.get(label);
      if (!p || v == null || !Number.isFinite(v)) {
        usable = false;
        break;
      }
      pos.push(p);
      val.push(v);
    }
    if (!usable) {
      skipped.add(typeLabel);
      continue;
    }
    included.add(typeLabel);
    tetCount += 1;
    triangles.push(...marchTetrahedron(pos, val, threshold));
  }

  return {
    triangles,
    metadata: {
      smoothed: true,
      threshold,
      includedElementTypes: [...included].sort(),
      skippedElementTypes: [...skipped].sort(),
      nodalCount: nodalValues.size,
      tetCount,
      triangleCount: triangles.length,
      note: HONESTY_NOTE,
    },
  };
}
