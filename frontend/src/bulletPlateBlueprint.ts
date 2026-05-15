export interface BulletPlateBlueprintAnchor {
  id: string;
  label: string;
  chineseLabel: string;
  evidenceRole: string;
  status: 'visual_target' | 'frontend_surface' | 'evidence_required';
  claimImpact: string;
}

export interface BulletPlateEvidenceRef {
  id: string;
  anchorId: BulletPlateBlueprintAnchor['id'];
  label: string;
  path: string;
  sourceKind:
    | 'run_deck'
    | 'solver_log'
    | 'metric_sidecar'
    | 'animation_manifest'
    | 'animation_gif'
    | 'result_mesh'
    | 'vtu_manifest'
    | 'run_report'
    | 'review_gate';
  status: 'available' | 'disabled' | 'deferred';
  signal: string;
  claimImpact: string;
}

export interface BulletPlateBlueprintSlice {
  id: string;
  label: string;
  status: 'started' | 'available' | 'deferred';
  verification: string;
}

export interface BulletPlateBlueprintContract {
  id: string;
  title: string;
  chineseTitle: string;
  claimTier: string;
  allowedClaim: string;
  imagePath: string;
  evidenceCaseId: string;
  visualAnchors: BulletPlateBlueprintAnchor[];
  evidenceRefs: BulletPlateEvidenceRef[];
  implementationSlices: BulletPlateBlueprintSlice[];
  tier2Blockers: string[];
}

export interface BulletPlateBlueprintSummary {
  label: string;
  claimTier: string;
  allowedClaim: string;
  imagePath: string;
  anchorCount: number;
  evidenceCaseId: string;
  availableEvidenceCount: number;
  evidenceCount: number;
  coveredAnchorCount: number;
  startedSlices: number;
  blockerCount: number;
  nextSlice: string;
}

const REAL_RUN_CASE_ID = 'GS-102-transient-refined-cfl085-v365-bracket-20260512';
const REAL_RUN_GRAPH_DIR = `project_state/graph_executor/${REAL_RUN_CASE_ID}`;
const REAL_RUN_DATA_DIR = `project_state/runs/${REAL_RUN_CASE_ID}/data`;
const REAL_RUN_VIEWER_DIR = `project_state/visualizations/${REAL_RUN_CASE_ID}`;

export const bulletPlateBlueprint: BulletPlateBlueprintContract = {
  id: 'fm04a-bullet-plate-target-blueprint',
  title: 'Bullet-plate target blueprint',
  chineseTitle: '子弹-板目标工程蓝图',
  claimTier: 'Tier 1 engineering candidate',
  allowedClaim: 'visual target and evidence map only; not signed validation; not benchmark agreement',
  imagePath: 'docs/visualization/blueprints/bullet_plate_target_blueprint.png',
  evidenceCaseId: REAL_RUN_CASE_ID,
  visualAnchors: [
    {
      id: 'trajectory',
      label: 'Impact trajectory',
      chineseLabel: '冲击路径',
      evidenceRole: 'links the visual target to projectile initial-condition provenance',
      status: 'frontend_surface',
      claimImpact: 'trajectory is a UI target marker, not a validated launch condition',
    },
    {
      id: 'plate-mesh',
      label: 'Target plate mesh',
      chineseLabel: '靶板网格',
      evidenceRole: 'maps to future mesh topology and mesh-quality evidence',
      status: 'frontend_surface',
      claimImpact: 'mesh drawing is schematic until deck and quality sidecars are attached',
    },
    {
      id: 'boundary-constraints',
      label: 'Boundary constraints',
      chineseLabel: '边界约束',
      evidenceRole: 'maps to boundary-condition assumptions in the candidate report spine',
      status: 'frontend_surface',
      claimImpact: 'constraint glyphs do not prove physical fixture equivalence',
    },
    {
      id: 'deformation-contour',
      label: 'Deformation contour',
      chineseLabel: '变形云图',
      evidenceRole: 'maps to future result-mesh frames and ballistic metric sidecars',
      status: 'frontend_surface',
      claimImpact: 'contour is schematic unless backed by result_mesh and metric artifacts',
    },
    {
      id: 'validation-data',
      label: 'Validation data nodes',
      chineseLabel: '验证数据',
      evidenceRole: 'maps to manifest, hashes, convergence evidence, and reviewer summary',
      status: 'evidence_required',
      claimImpact: 'data nodes stay Tier 1 until benchmark, tolerance, and signoff exist',
    },
  ],
  evidenceRefs: [
    {
      id: 'trajectory-metrics',
      anchorId: 'trajectory',
      label: 'Projectile velocity and crossing sidecar',
      path: `${REAL_RUN_GRAPH_DIR}/ballistic/ballistic_metrics.json`,
      sourceKind: 'metric_sidecar',
      status: 'available',
      signal: 'V0=365 m/s, residual_velocity_candidate_m_per_s, crossing_evidence',
      claimImpact: 'Tier 1 metric extraction only; not benchmark agreement',
    },
    {
      id: 'plate-runtime-deck',
      anchorId: 'plate-mesh',
      label: 'Runtime OpenRadioss deck',
      path: `${REAL_RUN_DATA_DIR}/model_00_0000.rad`,
      sourceKind: 'run_deck',
      status: 'available',
      signal: 'runtime deck used by the candidate run',
      claimImpact: 'deck provenance exists but does not prove mesh adequacy or signed validation',
    },
    {
      id: 'boundary-runtime-deck',
      anchorId: 'boundary-constraints',
      label: 'Boundary and contact assumptions in runtime deck',
      path: `${REAL_RUN_DATA_DIR}/model_00_0000.rad`,
      sourceKind: 'run_deck',
      status: 'available',
      signal: 'clamped-plate/contact setup is inspectable in the runtime deck',
      claimImpact: 'fixture assumptions remain Tier 1 until reviewer and benchmark gates exist',
    },
    {
      id: 'deformation-result-mesh',
      anchorId: 'deformation-contour',
      label: 'Text-to-CAE result mesh from real A-frame output',
      path: `${REAL_RUN_VIEWER_DIR}/result_mesh.json`,
      sourceKind: 'result_mesh',
      status: 'available',
      signal: '150 dynamic frames exported from OpenRadioss A### files',
      claimImpact: 'viewer playback evidence only; not validated physics',
    },
    {
      id: 'deformation-animation-manifest',
      anchorId: 'deformation-contour',
      label: 'OpenRadioss animation manifest',
      path: `${REAL_RUN_GRAPH_DIR}/visualization/openradioss_animation_manifest.json`,
      sourceKind: 'animation_manifest',
      status: 'available',
      signal: '150 solver-emitted animation frames and element-deletion state',
      claimImpact: 'visualization evidence only; not benchmark agreement',
    },
    {
      id: 'deformation-animation-gif',
      anchorId: 'deformation-contour',
      label: 'OpenRadioss animation GIF',
      path: `${REAL_RUN_GRAPH_DIR}/visualization/openradioss_animation.gif`,
      sourceKind: 'animation_gif',
      status: 'available',
      signal: 'rendered frame sequence for reviewer inspection',
      claimImpact: 'human-readable visual artifact only; not signed validation',
    },
    {
      id: 'validation-engine-log',
      anchorId: 'validation-data',
      label: 'OpenRadioss engine log',
      path: `${REAL_RUN_DATA_DIR}/engine.log`,
      sourceKind: 'solver_log',
      status: 'available',
      signal: 'NORMAL TERMINATION, cycle count, deletion events',
      claimImpact: 'solver termination evidence only; not physical validation',
    },
    {
      id: 'validation-run-report',
      anchorId: 'validation-data',
      label: 'Candidate run report',
      path: `reports/gs102_${REAL_RUN_CASE_ID}_candidate_run.md`,
      sourceKind: 'run_report',
      status: 'available',
      signal: 'candidate metrics, artifact hashes, limitations, and no-overclaim wording',
      claimImpact: 'review packet ingredient; Tier 2 still blocked',
    },
    {
      id: 'validation-vtu-manifest-disabled',
      anchorId: 'validation-data',
      label: 'VTU manifest placeholder',
      path: `${REAL_RUN_VIEWER_DIR}/vtu_manifest.json`,
      sourceKind: 'vtu_manifest',
      status: 'disabled',
      signal: 'VTU sidecars intentionally disabled for this local export',
      claimImpact: 'not a missing validation gate; browser playback uses result_mesh.json',
    },
    {
      id: 'validation-independent-review',
      anchorId: 'validation-data',
      label: 'Independent reviewer/signoff evidence',
      path: 'reports/codex_tool_reports/<pending-review>.md',
      sourceKind: 'review_gate',
      status: 'deferred',
      signal: 'required before any stronger claim or Tier 2 promotion',
      claimImpact: 'Tier 2 remains blocked without independent review/signoff',
    },
  ],
  implementationSlices: [
    {
      id: 'blueprint-memory',
      label: 'Persist generated blueprint image and goal contract',
      status: 'started',
      verification: 'docs image and five-section goal file exist in the repo',
    },
    {
      id: 'frontend-blueprint-panel',
      label: 'Surface blueprint in the Workbench Trust Center path',
      status: 'started',
      verification: 'frontend build renders the blueprint panel without backend changes',
    },
    {
      id: 'real-run-evidence',
      label: 'Attach real OpenRadioss run evidence to the blueprint anchors',
      status: 'available',
      verification: 'real-run metrics, engine log, animation manifest, result_mesh, and report paths are indexed',
    },
    {
      id: 'independent-review-evidence',
      label: 'Attach independent reviewer/signoff evidence',
      status: 'deferred',
      verification: 'requires reviewer artifact before any stronger claim or Tier 2 promotion',
    },
  ],
  tier2Blockers: [
    'single public benchmark case is not locked',
    'tolerance and uncertainty interval are not locked',
    'citation compliance review is not complete',
    'sealed artifact hash packet is not present',
    'independent reviewer/signoff evidence is not present',
    'user milestone-experience acceptance is not recorded',
  ],
};

export function buildBulletPlateBlueprintSummary(
  contract: BulletPlateBlueprintContract = bulletPlateBlueprint,
): BulletPlateBlueprintSummary {
  const startedSlices = contract.implementationSlices.filter(
    (slice) => slice.status === 'started' || slice.status === 'available',
  );
  const availableEvidence = contract.evidenceRefs.filter(
    (evidence) => evidence.status === 'available',
  );
  const coveredAnchorIds = new Set(availableEvidence.map((evidence) => evidence.anchorId));
  const nextSlice =
    contract.implementationSlices.find((slice) => slice.status === 'deferred')?.label ??
    'No deferred blueprint slice is listed';

  return {
    label: contract.chineseTitle,
    claimTier: contract.claimTier,
    allowedClaim: contract.allowedClaim,
    imagePath: contract.imagePath,
    anchorCount: contract.visualAnchors.length,
    evidenceCaseId: contract.evidenceCaseId,
    availableEvidenceCount: availableEvidence.length,
    evidenceCount: contract.evidenceRefs.length,
    coveredAnchorCount: coveredAnchorIds.size,
    startedSlices: startedSlices.length,
    blockerCount: contract.tier2Blockers.length,
    nextSlice,
  };
}

export function evidenceRefsForAnchor(
  anchorId: BulletPlateBlueprintAnchor['id'],
  contract: BulletPlateBlueprintContract = bulletPlateBlueprint,
): BulletPlateEvidenceRef[] {
  return contract.evidenceRefs.filter((evidence) => evidence.anchorId === anchorId);
}
