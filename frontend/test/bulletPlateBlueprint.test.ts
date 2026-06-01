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
  // is intentionally NOT committed — present after a local run, absent on a
  // fresh clone / CI by design. We deliberately do NOT gate on the
  // project_state/ DIRECTORY existing: other tests may (re)create that tree
  // on CI, so neither the artifact file nor the tree's presence is a reliable
  // version-control signal. Honesty rules, by ref class:
  //  • in-repo refs (NOT under project_state/) MUST exist on disk —
  //    anti-vaporware: a fabricated or typo'd in-repo path fails.
  //  • runtime refs (under project_state/) cannot be proven present on CI,
  //    but are still checked for STRUCTURE — they must be well-formed under a
  //    known runtime subdir with a case-id segment, and every runtime ref
  //    must point at the SAME candidate case dir. A typo'd subdir or a
  //    drifted case id in any ref trips this even when the gitignored
  //    artifacts are absent (Codex remediation review P3).
  const RUNTIME_PATH_RE = /^project_state\/(?:graph_executor|runs|visualizations)\/([^/]+)\//;
  const runtimeCaseIds = new Set<string>();
  for (const evidence of availableRefs) {
    if (evidence.path.startsWith('project_state/')) {
      const match = RUNTIME_PATH_RE.exec(evidence.path);
      assert.ok(
        match,
        `${evidence.id} runtime evidence path is malformed (got ${evidence.path})`,
      );
      runtimeCaseIds.add(match[1]);
    } else {
      assert.ok(
        existsSync(resolve(repoRoot, evidence.path)),
        `${evidence.id} should point at an existing in-repo artifact (got ${evidence.path})`,
      );
    }
  }
  assert.equal(
    runtimeCaseIds.size,
    1,
    `runtime evidence refs disagree on case id: ${[...runtimeCaseIds].join(', ')}`,
  );
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
