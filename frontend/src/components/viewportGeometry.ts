// FM-04a Phase 24 C — viewport geometry helpers extracted from
// ResultMeshWebGLViewport.tsx for LOC discipline. Pure functions, no
// React, no Three.js mesh-state mutation beyond the BufferGeometry
// build.
//
// Constraint: ZERO behavior change. The functions and constants here
// are byte-identical to their Phase 22-23 home in
// ResultMeshWebGLViewport.tsx — only the module location changed.

import * as THREE from 'three';
import type { ResultMeshElement, ResultMeshFrame } from '../resultMeshPlayback';
import { componentValue, type StressComponent } from '../stressDerivatives';
import { applyValueFilter, type ValueFilterState } from './viewportRaycaster';
import { sampleColormap, DEFAULT_COLORMAP, type ColormapId } from './colormaps';

/** Phase 22 B — section-cut clipping plane state. */
export interface SectionCutState {
  /** Axis the clipping plane is perpendicular to. */
  axis: 'x' | 'y' | 'z';
  /** Position along the axis (m) at which the plane sits. */
  positionM: number;
  /** When true, render only the "low" half (coord < positionM).
   * When false, render only the "high" half. */
  showLow: boolean;
}

// Tet (4-node) faces, 0-indexed into the connectivity array.
export const TET_FACES: ReadonlyArray<readonly [number, number, number]> = [
  [0, 1, 2],
  [0, 1, 3],
  [1, 2, 3],
  [0, 2, 3],
];

// Hex (8-node) faces split into two triangles per face. Indices follow
// the CalculiX C3D8 convention: bottom 0-1-2-3, top 4-5-6-7 with 4 above
// 0, etc.
export const HEX_FACES: ReadonlyArray<readonly [number, number, number]> = [
  [0, 1, 2], [0, 2, 3], // bottom
  [4, 6, 5], [4, 7, 6], // top
  [0, 5, 1], [0, 4, 5], // front
  [1, 6, 2], [1, 5, 6], // right
  [2, 7, 3], [2, 6, 7], // back
  [3, 4, 0], [3, 7, 4], // left
];

// Quad face (4-node) split into two triangles.
export const QUAD_FACES: ReadonlyArray<readonly [number, number, number]> = [
  [0, 1, 2],
  [0, 2, 3],
];

export interface Triangle {
  positions: [number, number, number, number, number, number, number, number, number];
  colorRgb: [number, number, number];
}

export function elementTriangles(
  element: ResultMeshElement,
  nodeCoords: Map<number, [number, number, number]>,
  colorRgb: [number, number, number],
): Triangle[] {
  const connectivity = element.connectivity;
  if (!connectivity || connectivity.length < 3) return [];

  let faceTable: ReadonlyArray<readonly [number, number, number]>;
  if (connectivity.length === 4) {
    // 4-node element: either a quad (planar 4 nodes) or a tet (3D 4
    // nodes). Both render fine when treated as a tet; for a planar
    // quad, two of the four "tet faces" collapse, leaving the visible
    // surface. The honest, simple, conservative choice — Phase 21 C
    // doesn't need to disambiguate.
    faceTable = TET_FACES;
  } else if (connectivity.length === 8) {
    faceTable = HEX_FACES;
  } else if (connectivity.length === 3) {
    faceTable = [[0, 1, 2]];
  } else {
    // Higher-order or unsupported element kinds: triangulate as a
    // simple fan from node 0. Far from accurate for curved elements
    // but keeps the viewport from going blank on unexpected input.
    faceTable = Array.from({ length: connectivity.length - 2 }, (_, i) => [
      0,
      i + 1,
      i + 2,
    ] as readonly [number, number, number]);
  }

  const out: Triangle[] = [];
  for (const [a, b, c] of faceTable) {
    const pa = nodeCoords.get(connectivity[a]);
    const pb = nodeCoords.get(connectivity[b]);
    const pc = nodeCoords.get(connectivity[c]);
    if (!pa || !pb || !pc) continue;
    out.push({
      positions: [...pa, ...pb, ...pc] as Triangle['positions'],
      colorRgb,
    });
  }
  return out;
}

// FM-04a Phase 43 Slice 4 — the blue→green→orange ramp is now the 'spectral'
// colormap (colormaps.ts). gradientStop is retained as a thin spectral alias
// (kept byte-identical: sampleColormap('spectral', …) reproduces the original
// piecewise-linear arithmetic) so legacy internal callers are unaffected.
export function gradientStop(t: number): [number, number, number] {
  return sampleColormap('spectral', t);
}

export function colorForElement(
  element: ResultMeshElement,
  valueMin: number,
  valueMax: number,
  fieldComponent: StressComponent = 'mises',
  colormap: ColormapId = DEFAULT_COLORMAP,
): [number, number, number] {
  if (element.alive === false) return [0.94, 0.27, 0.27]; // red for deleted
  if (element.partRole === 'projectile') return [0.9, 0.92, 0.94];
  // FM-04a Phase 23 B — when the element carries a stressTensor, the
  // per-component switcher derives the scalar; fall back to `value`
  // when no tensor present (Phase 22 D path).
  const fallback = element.value ?? valueMin;
  const v = element.stressTensor
    ? componentValue(element.stressTensor, fieldComponent, fallback)
    : fallback;
  const t = valueMax > valueMin ? (v - valueMin) / (valueMax - valueMin) : 0;
  return sampleColormap(colormap, t);
}

export function colorForValueFraction(
  t: number,
  colormap: ColormapId = DEFAULT_COLORMAP,
): [number, number, number] {
  return sampleColormap(colormap, t);
}

/** Phase 22 B — build node-coordinate map honouring optional
 * deformation magnification AND optional frame interpolation. When
 * `nextFrame` is provided + `tInterp` ∈ (0, 1), node positions blend
 * linearly between the two frames' DEFORMED coordinates (or fall
 * back to undeformed coords when deformed is absent). The
 * `deformationScale` multiplier amplifies the deformed displacement
 * relative to undeformed for visualization on small-strain results. */
export function buildNodeCoords(
  frame: ResultMeshFrame,
  nextFrame: ResultMeshFrame | null | undefined,
  tInterp: number,
  deformationScale: number,
): Map<number, [number, number, number]> {
  const nodeCoords = new Map<number, [number, number, number]>();
  // Index nextFrame nodes by label for blend lookup.
  const nextByLabel = new Map<number, [number, number, number]>();
  if (nextFrame && tInterp > 0) {
    for (const nn of nextFrame.nodes) {
      const p = nn.deformed ?? nn.coordinates;
      if (p && p.length >= 3) {
        nextByLabel.set(nn.label, [p[0], p[1], p[2]]);
      }
    }
  }
  const t = nextFrame ? Math.max(0, Math.min(1, tInterp)) : 0;
  for (const node of frame.nodes) {
    const undef = node.coordinates;
    const def = node.deformed ?? node.coordinates;
    if (!def || def.length < 3) continue;
    const baseX = def[0];
    const baseY = def[1];
    const baseZ = def[2];
    // Magnify deformation relative to undeformed coords when available.
    let x = baseX;
    let y = baseY;
    let z = baseZ;
    if (
      deformationScale !== 1 &&
      undef &&
      undef.length >= 3 &&
      node.deformed &&
      node.deformed.length >= 3
    ) {
      x = undef[0] + (node.deformed[0] - undef[0]) * deformationScale;
      y = undef[1] + (node.deformed[1] - undef[1]) * deformationScale;
      z = undef[2] + (node.deformed[2] - undef[2]) * deformationScale;
    }
    // Blend toward nextFrame when t > 0.
    const nxt = nextByLabel.get(node.label);
    if (nxt && t > 0) {
      x = x + (nxt[0] - x) * t;
      y = y + (nxt[1] - y) * t;
      z = z + (nxt[2] - z) * t;
    }
    nodeCoords.set(node.label, [x, y, z]);
  }
  return nodeCoords;
}

export function buildBufferGeometry(
  frame: ResultMeshFrame,
  valueMin: number,
  valueMax: number,
  options: {
    nextFrame?: ResultMeshFrame | null;
    tInterp?: number;
    deformationScale?: number;
    fieldComponent?: StressComponent;
    valueFilter?: ValueFilterState | null;
    colormap?: ColormapId;
  } = {},
): {
  geometry: THREE.BufferGeometry;
  bounds: THREE.Box3;
  triangleCount: number;
} {
  const nodeCoords = buildNodeCoords(
    frame,
    options.nextFrame ?? null,
    options.tInterp ?? 0,
    options.deformationScale ?? 1,
  );

  const triangles: Triangle[] = [];
  for (const element of frame.elements) {
    // Phase 23 D — apply value filter (returns true for retain).
    if (
      !applyValueFilter(element, options.valueFilter ?? null, options.fieldComponent ?? 'mises')
    ) {
      continue;
    }
    const color = colorForElement(
      element,
      valueMin,
      valueMax,
      options.fieldComponent ?? 'mises',
      options.colormap ?? DEFAULT_COLORMAP,
    );
    triangles.push(...elementTriangles(element, nodeCoords, color));
  }

  const positions = new Float32Array(triangles.length * 9);
  const colors = new Float32Array(triangles.length * 9);
  for (let i = 0; i < triangles.length; i++) {
    positions.set(triangles[i].positions, i * 9);
    const [r, g, b] = triangles[i].colorRgb;
    for (let v = 0; v < 3; v++) {
      colors[i * 9 + v * 3 + 0] = r;
      colors[i * 9 + v * 3 + 1] = g;
      colors[i * 9 + v * 3 + 2] = b;
    }
  }

  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
  geometry.setAttribute('color', new THREE.BufferAttribute(colors, 3));
  geometry.computeVertexNormals();

  const bounds = new THREE.Box3();
  bounds.setFromBufferAttribute(geometry.getAttribute('position') as THREE.BufferAttribute);

  return { geometry, bounds, triangleCount: triangles.length };
}
