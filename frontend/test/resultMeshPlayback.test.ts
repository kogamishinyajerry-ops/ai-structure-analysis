import assert from 'node:assert/strict';
import test from 'node:test';

import {
  clampResultMeshFrameIndex,
  summarizeResultMeshPlayback,
} from '../src/resultMeshPlayback.ts';

const payload = {
  schemaVersion: 1,
  analysisType: 'dynamic',
  fieldLabel: 'von Mises stress',
  modelTree: {
    children: [
      { partRole: 'projectile', elementCount: 8 },
      { partRole: 'plate', elementCount: 72 },
    ],
  },
  fieldRanges: { valueMin: 0, valueMax: 320, maxDisplacement: 12.5 },
  dynamicFrames: [
    {
      frame: 0,
      timeMs: 0,
      nodes: [{ label: 1 }, { label: 2 }],
      elements: [
        { partRole: 'projectile', alive: true },
        { partRole: 'plate', alive: true },
      ],
    },
    {
      frame: 1,
      timeMs: 0.04,
      nodes: [{ label: 1 }, { label: 2 }],
      elements: [
        { partRole: 'projectile', alive: true },
        { partRole: 'plate', alive: false },
      ],
    },
  ],
};

test('summarizeResultMeshPlayback exposes model tree and frame status', () => {
  const summary = summarizeResultMeshPlayback(payload, 1);

  assert.equal(summary.frameCount, 2);
  assert.equal(summary.selectedFrameIndex, 1);
  assert.equal(summary.timeMs, 0.04);
  assert.equal(summary.nodeCount, 2);
  assert.equal(summary.elementCount, 2);
  assert.equal(summary.projectileElements, 1);
  assert.equal(summary.plateElements, 1);
  assert.equal(summary.deletedElements, 1);
  assert.equal(summary.fieldLabel, 'von Mises stress');
  assert.equal(summary.modelTree.length, 2);
});

test('clampResultMeshFrameIndex keeps slider input inside frame range', () => {
  assert.equal(clampResultMeshFrameIndex(payload, -5), 0);
  assert.equal(clampResultMeshFrameIndex(payload, 9), 1);
  assert.equal(clampResultMeshFrameIndex(payload, 0), 0);
});
