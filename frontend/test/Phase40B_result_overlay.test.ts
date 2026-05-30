// FM-04a Phase 40 B step 1 — two-result overlay mesh-correspondence kernel.
// Pure set arithmetic; runs under `node --test` (via tsx), matching the
// Phase40A_iso_surface.test.ts convention. Asserts the node-label correspondence
// + the honesty gate (a difference field is only "corresponds:true" when the two
// meshes actually share enough node labels).

import assert from 'node:assert/strict';
import { test } from 'vitest';

import {
  computeMeshCorrespondence,
  DEFAULT_DIFF_THRESHOLD,
} from '../src/components/resultOverlay.ts';
import type { ResultMeshFrame } from '../src/resultMeshPlayback.ts';

function mkFrame(labels: number[]): ResultMeshFrame {
  return {
    frame: 0,
    timeMs: 0,
    nodes: labels.map((label) => ({ label, coordinates: [0, 0, 0] })),
    elements: [],
  };
}

test('identical meshes → ratio 1, all shared, corresponds true', () => {
  const c = computeMeshCorrespondence(mkFrame([1, 2, 3, 4]), mkFrame([4, 3, 2, 1]));
  assert.deepEqual(c.sharedLabels, [1, 2, 3, 4]);
  assert.deepEqual(c.onlyALabels, []);
  assert.deepEqual(c.onlyBLabels, []);
  assert.equal(c.correspondenceRatio, 1);
  assert.equal(c.corresponds, true);
});

test('disjoint meshes → ratio 0, corresponds false, honest "do not correspond" note', () => {
  const c = computeMeshCorrespondence(mkFrame([1, 2, 3]), mkFrame([4, 5, 6]));
  assert.equal(c.sharedCount, 0);
  assert.equal(c.correspondenceRatio, 0);
  assert.equal(c.corresponds, false);
  assert.match(c.note, /do not correspond/i);
  assert.deepEqual(c.onlyALabels, [1, 2, 3]);
  assert.deepEqual(c.onlyBLabels, [4, 5, 6]);
});

test('partial overlap above threshold → correct intersection, corresponds true', () => {
  // A=[1,2,3,4] B=[1,2,3,5] → shared {1,2,3}=3 / max(4,4)=4 → 0.75 ≥ 0.5.
  const c = computeMeshCorrespondence(mkFrame([1, 2, 3, 4]), mkFrame([1, 2, 3, 5]));
  assert.deepEqual(c.sharedLabels, [1, 2, 3]);
  assert.deepEqual(c.onlyALabels, [4]);
  assert.deepEqual(c.onlyBLabels, [5]);
  assert.equal(c.correspondenceRatio, 0.75);
  assert.equal(c.corresponds, true);
});

test('partial overlap below threshold → corresponds false, honest "too little" note', () => {
  // 1 shared of 8 → 0.125 < 0.5.
  const c = computeMeshCorrespondence(
    mkFrame([1, 2, 3, 4, 5, 6, 7, 8]),
    mkFrame([1, 9, 10, 11, 12, 13, 14, 15]),
  );
  assert.equal(c.sharedCount, 1);
  assert.equal(c.correspondenceRatio, 0.125);
  assert.equal(c.corresponds, false);
  assert.match(c.note, /too little/i);
});

test('custom diffThreshold gates corresponds (0.75 ratio fails an 0.8 threshold)', () => {
  const c = computeMeshCorrespondence(
    mkFrame([1, 2, 3, 4]),
    mkFrame([1, 2, 3, 5]),
    0.8,
  );
  assert.equal(c.correspondenceRatio, 0.75);
  assert.equal(c.corresponds, false);
  assert.equal(c.diffThreshold, 0.8);
});

test('null / empty frames → ratio 0, corresponds false (no crash)', () => {
  const c1 = computeMeshCorrespondence(null, mkFrame([1, 2]));
  assert.equal(c1.countA, 0);
  assert.equal(c1.countB, 2);
  assert.equal(c1.correspondenceRatio, 0);
  assert.equal(c1.corresponds, false);

  const c2 = computeMeshCorrespondence(mkFrame([]), mkFrame([]));
  assert.equal(c2.correspondenceRatio, 0);
  assert.equal(c2.corresponds, false);
});

test('duplicate node labels are deduplicated in the counts', () => {
  const c = computeMeshCorrespondence(mkFrame([1, 1, 2]), mkFrame([1, 2, 2, 3]));
  assert.equal(c.countA, 2); // {1,2}
  assert.equal(c.countB, 3); // {1,2,3}
  assert.deepEqual(c.sharedLabels, [1, 2]);
  assert.deepEqual(c.onlyBLabels, [3]);
});

test('DEFAULT_DIFF_THRESHOLD is the documented 0.5', () => {
  assert.equal(DEFAULT_DIFF_THRESHOLD, 0.5);
  const c = computeMeshCorrespondence(mkFrame([1, 2]), mkFrame([3, 4]));
  assert.equal(c.diffThreshold, 0.5);
});
