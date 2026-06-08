// FM-04a Phase 40 A — iso-surface extraction kernel + cell→point smoothing.
// Pure geometry; runs under `node --test` (via tsx), matching the
// resultMeshPlayback.test.ts convention. Asserts the marching-tetrahedra cases
// against hand-computed crossings + the honesty metadata contract.

import assert from 'node:assert/strict';
import { test } from 'vitest';

import {
  averageElementValuesToNodes,
  extractIsoSurface,
  marchTetrahedron,
} from '../src/components/isoSurface.ts';
import type { ResultMeshFrame } from '../src/resultMeshPlayback.ts';

type Vec3 = [number, number, number];

const TET_POS: Vec3[] = [
  [0, 0, 0], // n0
  [1, 0, 0], // n1
  [0, 1, 0], // n2
  [0, 0, 1], // n3
];

function vecClose(a: readonly number[], b: readonly number[]): boolean {
  return (
    Math.abs(a[0] - b[0]) < 1e-9 &&
    Math.abs(a[1] - b[1]) < 1e-9 &&
    Math.abs(a[2] - b[2]) < 1e-9
  );
}

function assertTriHasAll(
  tri: { a: readonly number[]; b: readonly number[]; c: readonly number[] },
  expected: Vec3[],
  msg: string,
): void {
  const verts = [tri.a, tri.b, tri.c];
  for (const e of expected) {
    assert.ok(
      verts.some((v) => vecClose(v, e)),
      `${msg}: missing ${JSON.stringify(e)} in ${JSON.stringify(verts)}`,
    );
  }
}

// ---- marchTetrahedron: the 5 topological cases ----

test('marchTetrahedron: 1 inside vertex → 1 triangle at the 3 incident-edge crossings', () => {
  const tris = marchTetrahedron(TET_POS, [1, 0, 0, 0], 0.5);
  assert.equal(tris.length, 1);
  assertTriHasAll(tris[0], [
    [0.5, 0, 0],
    [0, 0.5, 0],
    [0, 0, 0.5],
  ], '1-inside');
});

test('marchTetrahedron: 3 inside vertices → 1 triangle around the single outside vertex', () => {
  const tris = marchTetrahedron(TET_POS, [1, 1, 1, 0], 0.5);
  assert.equal(tris.length, 1);
  assertTriHasAll(tris[0], [
    [0, 0, 0.5], // edge n3-n0
    [0.5, 0, 0.5], // edge n3-n1
    [0, 0.5, 0.5], // edge n3-n2
  ], '3-inside');
});

test('marchTetrahedron: 2 inside vertices → quad (2 triangles, 4 crossings)', () => {
  const tris = marchTetrahedron(TET_POS, [1, 1, 0, 0], 0.5);
  assert.equal(tris.length, 2);
  // The 4 crossing points across the inside-pair {n0,n1} → outside-pair {n2,n3}.
  const expected: Vec3[] = [
    [0, 0.5, 0], // n0-n2
    [0, 0, 0.5], // n0-n3
    [0.5, 0.5, 0], // n1-n2
    [0.5, 0, 0.5], // n1-n3
  ];
  const allVerts = tris.flatMap((t) => [t.a, t.b, t.c]);
  for (const e of expected) {
    assert.ok(allVerts.some((v) => vecClose(v, e)), `2-inside missing ${JSON.stringify(e)}`);
  }
});

test('marchTetrahedron: all inside or all outside → no triangles', () => {
  assert.equal(marchTetrahedron(TET_POS, [1, 1, 1, 1], 0.5).length, 0);
  assert.equal(marchTetrahedron(TET_POS, [0, 0, 0, 0], 0.5).length, 0);
});

test('marchTetrahedron: threshold equality counts as inside (≥)', () => {
  // n0 exactly at threshold → inside; others below → 1 triangle.
  const tris = marchTetrahedron(TET_POS, [0.5, 0, 0, 0], 0.5);
  assert.equal(tris.length, 1);
});

// ---- averageElementValuesToNodes: cell→point smoothing ----

test('averageElementValuesToNodes: shared nodes get the mean of incident element values', () => {
  const frame: ResultMeshFrame = {
    frame: 0,
    timeMs: 0,
    nodes: [1, 2, 3, 4, 5].map((label) => ({ label, coordinates: [0, 0, 0] })),
    elements: [
      { type: 'C3D4', connectivity: [1, 2, 3, 4], value: 10 },
      { type: 'C3D4', connectivity: [1, 2, 3, 5], value: 20 },
    ],
  };
  const nodal = averageElementValuesToNodes(frame, (el) => el.value);
  assert.equal(nodal.get(1), 15); // (10+20)/2
  assert.equal(nodal.get(2), 15);
  assert.equal(nodal.get(3), 15);
  assert.equal(nodal.get(4), 10); // only tet A
  assert.equal(nodal.get(5), 20); // only tet B
});

test('averageElementValuesToNodes: non-tet + non-finite scalars are excluded', () => {
  const frame: ResultMeshFrame = {
    frame: 0,
    timeMs: 0,
    nodes: [1, 2, 3, 4].map((label) => ({ label, coordinates: [0, 0, 0] })),
    elements: [
      { type: 'C3D8', connectivity: [1, 2, 3, 4], value: 99 }, // hex → skipped
      { type: 'C3D4', connectivity: [1, 2, 3, 4], value: Number.NaN }, // NaN → skipped
    ],
  };
  const nodal = averageElementValuesToNodes(frame, (el) => el.value);
  assert.equal(nodal.size, 0);
});

// ---- extractIsoSurface: integration + honesty metadata ----

test('extractIsoSurface: a single constant tet yields NO iso-surface (honest smoothing)', () => {
  // One element's value averages identically onto all 4 corners → all-inside or
  // all-outside → 0 triangles. This is the honest consequence of cell→point
  // smoothing on an isolated element.
  const frame: ResultMeshFrame = {
    frame: 0,
    timeMs: 0,
    nodes: TET_POS.map((c, i) => ({ label: i + 1, coordinates: c })),
    elements: [{ type: 'C3D4', connectivity: [1, 2, 3, 4], value: 10 }],
  };
  const below = extractIsoSurface(frame, 5, (el) => el.value);
  const above = extractIsoSurface(frame, 15, (el) => el.value);
  assert.equal(below.triangles.length, 0);
  assert.equal(above.triangles.length, 0);
  assert.equal(below.metadata.tetCount, 1);
  assert.deepEqual(below.metadata.includedElementTypes, ['C3D4']);
  assert.equal(below.metadata.smoothed, true);
  assert.ok(below.metadata.note.includes('Tier 0'));
  assert.equal(below.metadata.threshold, 5);
});

test('extractIsoSurface: a 2-tet mesh with a varying field yields a crossing surface', () => {
  // Shared face {1,2,3} → avg 5; apex node4 (tet A, value 0) → 0; apex node5
  // (tet B, value 10) → 10. At t=2.5 only tet A straddles → 1 triangle.
  const frame: ResultMeshFrame = {
    frame: 0,
    timeMs: 0,
    nodes: [
      { label: 1, coordinates: [0, 0, 0] },
      { label: 2, coordinates: [1, 0, 0] },
      { label: 3, coordinates: [0, 1, 0] },
      { label: 4, coordinates: [0, 0, -1] },
      { label: 5, coordinates: [0, 0, 1] },
    ],
    elements: [
      { type: 'C3D4', connectivity: [1, 2, 3, 4], value: 0 },
      { type: 'C3D4', connectivity: [1, 2, 3, 5], value: 10 },
    ],
  };
  const iso = extractIsoSurface(frame, 2.5, (el) => el.value);
  assert.equal(iso.metadata.tetCount, 2);
  assert.equal(iso.triangles.length, 1); // only tet A crosses
  assertTriHasAll(iso.triangles[0], [
    [0, 0, -0.5], // edge node4-node1
    [0.5, 0, -0.5], // edge node4-node2
    [0, 0.5, -0.5], // edge node4-node3
  ], '2-tet crossing');
});

test('extractIsoSurface: non-tet elements are reported as skipped, not silently dropped', () => {
  const frame: ResultMeshFrame = {
    frame: 0,
    timeMs: 0,
    nodes: TET_POS.map((c, i) => ({ label: i + 1, coordinates: c })),
    elements: [
      { type: 'C3D4', connectivity: [1, 2, 3, 4], value: 1 },
      { type: 'C3D8', connectivity: [1, 2, 3, 4, 1, 2, 3, 4], value: 1 },
      { type: 'S4', connectivity: [1, 2, 3, 4], value: 1 },
    ],
  };
  const iso = extractIsoSurface(frame, 0.5, (el) => el.value);
  assert.deepEqual(iso.metadata.includedElementTypes, ['C3D4']);
  assert.deepEqual(iso.metadata.skippedElementTypes, ['C3D8', 'S4']);
});

test('extractIsoSurface: a tet referencing a node with no coordinates is skipped gracefully', () => {
  const frame: ResultMeshFrame = {
    frame: 0,
    timeMs: 0,
    nodes: [
      { label: 1, coordinates: [0, 0, 0] },
      { label: 2, coordinates: [1, 0, 0] },
      { label: 3, coordinates: [0, 1, 0] },
      { label: 4 }, // no coordinates
    ],
    elements: [{ type: 'C3D4', connectivity: [1, 2, 3, 4], value: 10 }],
  };
  const iso = extractIsoSurface(frame, 5, (el) => el.value);
  assert.equal(iso.triangles.length, 0);
  assert.equal(iso.metadata.tetCount, 0);
  // Codex R1 P3: a real C3D4 skipped for a DATA defect (missing coords)
  // is reported as an INCOMPLETE tet, NOT mislabeled as a "non-tet"
  // skipped type. skippedElementTypes is reserved for the genuine
  // non-tet scope limitation.
  assert.deepEqual(iso.metadata.skippedElementTypes, []);
  assert.deepEqual(iso.metadata.incompleteTetTypes, ['C3D4']);
});

test('extractIsoSurface: C3D10 uses the first 4 connectivity entries as corners', () => {
  const frame: ResultMeshFrame = {
    frame: 0,
    timeMs: 0,
    nodes: Array.from({ length: 10 }, (_unused, i) => ({
      label: i + 1,
      coordinates: TET_POS[i % 4],
    })),
    elements: [
      { type: 'C3D10', connectivity: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10], value: 7 },
    ],
  };
  const iso = extractIsoSurface(frame, 3, (el) => el.value);
  assert.equal(iso.metadata.tetCount, 1);
  assert.deepEqual(iso.metadata.includedElementTypes, ['C3D10']);
});
