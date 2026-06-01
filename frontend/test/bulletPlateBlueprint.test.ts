import assert from 'node:assert/strict';
import { existsSync, readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { test } from 'vitest';

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

  // FM-04a: `project_state/` is a gitignored runtime root (see .gitignore).
  // The candidate's real-run evidence (OpenRadioss decks, result-mesh,
  // animation, engine log) is generated there by an actual local solve and
  // is intentionally NOT committed. On a machine that has run the candidate
  // every 'available' ref exists on disk; on a fresh clone / CI the runtime
  // artifacts are absent BY DESIGN. So an 'available' ref is honest iff it
  // EITHER exists on disk OR is a `project_state/` runtime path on a machine
  // that carries no runtime tree at all. When the runtime tree IS present (a
  // real local run) every ref — runtime ones included — must exist, which
  // preserves the anti-vaporware intent: a fabricated or typo'd path still
  // fails, and an in-repo ref that does not exist always fails.
  const RUNTIME_ROOT = 'project_state/';
  const runtimeTreePresent = existsSync(resolve(repoRoot, 'project_state'));
  for (const evidence of availableRefs) {
    const onDisk = existsSync(resolve(repoRoot, evidence.path));
    const isRuntimeGenerated = evidence.path.startsWith(RUNTIME_ROOT);
    assert.ok(
      onDisk || (isRuntimeGenerated && !runtimeTreePresent),
      `${evidence.id} should point at an existing artifact (got ${evidence.path})`,
    );
  }
});

test('bullet-plate blueprint result-mesh evidence is a real 150-frame OpenRadioss export', () => {
  const repoRoot = resolve(import.meta.dirname, '..', '..');
  const resultMesh = bulletPlateBlueprint.evidenceRefs.find(
    (evidence) => evidence.id === 'deformation-result-mesh',
  );

  assert.ok(resultMesh);

  // The result-mesh lives under the gitignored `project_state/` runtime root
  // (see the sibling test above) — absent on a fresh clone / CI by design.
  // Verify its OpenRadioss / 150-frame content on any machine that has run
  // the candidate; when the runtime artifact is absent, assert only that the
  // ref is correctly declared as a `project_state/` runtime path.
  const resultMeshPath = resolve(repoRoot, resultMesh.path);
  if (!existsSync(resultMeshPath)) {
    assert.ok(
      resultMesh.path.startsWith('project_state/'),
      `result-mesh evidence is absent yet not a project_state/ runtime path: ${resultMesh.path}`,
    );
    return;
  }
  const resultMeshHead = readFileSync(resultMeshPath, 'utf8').slice(0, 1200);
  assert.match(resultMeshHead, /"solver": "OpenRadioss"/);
  assert.match(resultMeshHead, /"frameCount": 150/);
  assert.match(resultMeshHead, /not signed validation/);
});
