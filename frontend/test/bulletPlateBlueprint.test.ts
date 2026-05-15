import assert from 'node:assert/strict';
import { existsSync, readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import test from 'node:test';

import {
  buildBulletPlateBlueprintSummary,
  bulletPlateBlueprint,
} from '../src/bulletPlateBlueprint.ts';

test('bullet-plate blueprint keeps a Tier 1 no-overclaim boundary', () => {
  const summary = buildBulletPlateBlueprintSummary();

  assert.equal(summary.claimTier, 'Tier 1 engineering candidate');
  assert.match(summary.allowedClaim, /not signed validation/);
  assert.match(summary.allowedClaim, /not benchmark agreement/);
  assert.equal(summary.imagePath, 'docs/visualization/blueprints/bullet_plate_target_blueprint.png');
  assert.equal(summary.anchorCount, 5);
  assert.equal(summary.coveredAnchorCount, 5);
  assert.equal(summary.availableEvidenceCount, 8);
  assert.equal(summary.evidenceCount, 10);
  assert.equal(summary.blockerCount, 6);
});

test('bullet-plate blueprint maps all required visual anchors to evidence roles', () => {
  const anchorIds = bulletPlateBlueprint.visualAnchors.map((anchor) => anchor.id);

  assert.deepEqual(anchorIds, [
    'trajectory',
    'plate-mesh',
    'boundary-constraints',
    'deformation-contour',
    'validation-data',
  ]);

  assert.ok(
    bulletPlateBlueprint.visualAnchors.every((anchor) => anchor.evidenceRole.length > 0),
  );
  assert.ok(
    bulletPlateBlueprint.visualAnchors.every((anchor) => anchor.claimImpact.length > 0),
  );
});

test('bullet-plate blueprint separates started frontend work from deferred run evidence', () => {
  const summary = buildBulletPlateBlueprintSummary();

  assert.equal(summary.startedSlices, 3);
  assert.equal(
    summary.nextSlice,
    'Attach independent reviewer/signoff evidence',
  );
});

test('bullet-plate blueprint evidence refs point at available local Tier 1 artifacts', () => {
  const repoRoot = resolve(import.meta.dirname, '..', '..');
  const availableRefs = bulletPlateBlueprint.evidenceRefs.filter(
    (evidence) => evidence.status === 'available',
  );

  assert.equal(availableRefs.length, 8);
  for (const evidence of availableRefs) {
    assert.ok(
      existsSync(resolve(repoRoot, evidence.path)),
      `${evidence.id} should point at an existing artifact`,
    );
  }
});

test('bullet-plate blueprint result-mesh evidence is a real 150-frame OpenRadioss export', () => {
  const repoRoot = resolve(import.meta.dirname, '..', '..');
  const resultMesh = bulletPlateBlueprint.evidenceRefs.find(
    (evidence) => evidence.id === 'deformation-result-mesh',
  );

  assert.ok(resultMesh);
  const resultMeshHead = readFileSync(resolve(repoRoot, resultMesh.path), 'utf8').slice(0, 1200);
  assert.match(resultMeshHead, /"solver": "OpenRadioss"/);
  assert.match(resultMeshHead, /"frameCount": 150/);
  assert.match(resultMeshHead, /not signed validation/);
});
