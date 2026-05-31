// FM-04a Phase 29 B — useTrustSections custom hook.
//
// Encapsulates the 7-section trust-strip + sections build that was
// inlined into App.tsx via Phase 28 D's granular useMemo wrapping.
// Phase 28 D was correctness-positive (memoized per-section so an
// unrelated `report` change does not bust the Overview cache) but
// cost +141 LOC in App.tsx (each useMemo + builder call + dep
// array was 6-15 lines). Centralizing in a hook restores App.tsx
// to ~1455 LOC while preserving the granular memoization.
//
// The 7 builders themselves are unchanged (Phase 26 D / 27 B / 28 B
// extractions); only the orchestration moves out of App.tsx.
//
// Anti-gaming guard D:-3 — every builder remains PURE (no ctx
// mutation). The hook does not introduce side effects beyond
// useMemo memoization.
//
// Tier 1 / Tier 2 engineering candidate; not signed validation;
// not benchmark agreement.

import { useMemo, type ReactNode } from 'react';

import {
  buildTrustStrip,
  buildOverviewSection,
  buildRuntimeSection,
  buildEvidenceSection,
  buildValidationSection,
  buildBlueprintTargetSection,
  buildBallisticSection,
  buildGateSection,
} from './trustCenterViewModel';
import type {
  OperatorStatusItem,
  OperatorStatusSection,
} from '../types/AppTypes';

/** Union of all context fields the 7 builders need. The hook
 * destructures and passes the right subset to each builder; the
 * caller (App.tsx) supplies one bundle. */
export interface UseTrustSectionsContext {
  // Strip inputs
  claimTier: Parameters<typeof buildTrustStrip>[0]['claimTier'];
  allowedClaim: Parameters<typeof buildTrustStrip>[0]['allowedClaim'];
  solverTruthSource: Parameters<typeof buildTrustStrip>[0]['solverTruthSource'];
  candidateSpine: Parameters<typeof buildTrustStrip>[0]['candidateSpine'];
  currentJobId: Parameters<typeof buildTrustStrip>[0]['currentJobId'];
  executionMode: Parameters<typeof buildTrustStrip>[0]['executionMode'];
  report: Parameters<typeof buildTrustStrip>[0]['report'];
  reportValidationStatus: Parameters<typeof buildTrustStrip>[0]['reportValidationStatus'];
  referenceStatusRaw: Parameters<typeof buildTrustStrip>[0]['referenceStatusRaw'];
  goldenSampleSummary: Parameters<typeof buildTrustStrip>[0]['goldenSampleSummary'];
  goldenSampleReviewCount: Parameters<typeof buildTrustStrip>[0]['goldenSampleReviewCount'];
  // Derive from buildBlueprintTargetSection (the RICHER blueprint shape:
  // imagePath/evidenceCaseId/claimTier/evidenceCount/… ). buildTrustStrip needs
  // only a structural subset, so it still accepts this richer value.
  blueprintSummary: Parameters<typeof buildBlueprintTargetSection>[0]['blueprintSummary'];

  // Section icons (supplied by App.tsx to keep this hook
  // lucide-icon-agnostic)
  overviewIcon: ReactNode;
  runtimeIcon: ReactNode;
  evidenceIcon: ReactNode;
  validationIcon: ReactNode;
  blueprintIcon: ReactNode;
  ballisticIcon: ReactNode;
  gateIcon: ReactNode;

  // Overview-only inputs
  activeCaseId: Parameters<typeof buildOverviewSection>[0]['activeCaseId'];
  file: Parameters<typeof buildOverviewSection>[0]['file'];
  caseLabel: Parameters<typeof buildOverviewSection>[0]['caseLabel'];
  nextAction: Parameters<typeof buildOverviewSection>[0]['nextAction'];

  // Runtime-only inputs
  analysisModeLabel: Parameters<typeof buildRuntimeSection>[0]['analysisModeLabel'];
  currentJobLabel: Parameters<typeof buildRuntimeSection>[0]['currentJobLabel'];
  lastSolverMaterialReference: Parameters<typeof buildRuntimeSection>[0]['lastSolverMaterialReference'];
  runState: Parameters<typeof buildRuntimeSection>[0]['runState'];
  runStateTone: Parameters<typeof buildRuntimeSection>[0]['runStateTone'];
  latestEvent: Parameters<typeof buildRuntimeSection>[0]['latestEvent'];
  solverLogSummary: Parameters<typeof buildRuntimeSection>[0]['solverLogSummary'];
  solverLogState: Parameters<typeof buildRuntimeSection>[0]['solverLogState'];
  convergenceSummary: Parameters<typeof buildRuntimeSection>[0]['convergenceSummary'];
  candidateConvergenceEvidence: Parameters<typeof buildRuntimeSection>[0]['candidateConvergenceEvidence'];
  convergenceClaimImpact: Parameters<typeof buildRuntimeSection>[0]['convergenceClaimImpact'];

  // Evidence-only inputs
  evidenceState: Parameters<typeof buildEvidenceSection>[0]['evidenceState'];
  manifestState: Parameters<typeof buildEvidenceSection>[0]['manifestState'];
  candidateManifest: Parameters<typeof buildEvidenceSection>[0]['candidateManifest'];
  backendProvenance: Parameters<typeof buildEvidenceSection>[0]['backendProvenance'];
  meshArtifactSource: Parameters<typeof buildEvidenceSection>[0]['meshArtifactSource'];
  // Derive from buildValidationSection (typed `{ quality } | null`), not
  // buildEvidenceSection (which loosely types it `unknown`). buildEvidenceSection
  // accepts the narrower type (unknown accepts anything).
  candidateMeshEvidence: Parameters<typeof buildValidationSection>[0]['candidateMeshEvidence'];
  convergenceArtifactList: Parameters<typeof buildEvidenceSection>[0]['convergenceArtifactList'];
  meshConvergenceStudySource: Parameters<typeof buildEvidenceSection>[0]['meshConvergenceStudySource'];
  meshConvergenceStudy: Parameters<typeof buildEvidenceSection>[0]['meshConvergenceStudy'];
  meshConvergenceClaimImpact: Parameters<typeof buildEvidenceSection>[0]['meshConvergenceClaimImpact'];

  // Validation-only inputs
  referenceStatus: Parameters<typeof buildValidationSection>[0]['referenceStatus'];
  referenceReason: Parameters<typeof buildValidationSection>[0]['referenceReason'];
  referenceDeviation: Parameters<typeof buildValidationSection>[0]['referenceDeviation'];
  unitSummary: Parameters<typeof buildValidationSection>[0]['unitSummary'];
  candidateAssumptions: Parameters<typeof buildValidationSection>[0]['candidateAssumptions'];
  materialSummary: Parameters<typeof buildValidationSection>[0]['materialSummary'];
  boundarySummary: Parameters<typeof buildValidationSection>[0]['boundarySummary'];
  meshTopologySummary: Parameters<typeof buildValidationSection>[0]['meshTopologySummary'];
  meshDeckElementTypes: Parameters<typeof buildValidationSection>[0]['meshDeckElementTypes'];
  meshQualitySummary: Parameters<typeof buildValidationSection>[0]['meshQualitySummary'];
  meshClaimImpact: Parameters<typeof buildValidationSection>[0]['meshClaimImpact'];
  meshConvergenceStudySummary: Parameters<typeof buildValidationSection>[0]['meshConvergenceStudySummary'];
  convergenceMissingSummary: Parameters<typeof buildValidationSection>[0]['convergenceMissingSummary'];
  failurePatternRef: Parameters<typeof buildValidationSection>[0]['failurePatternRef'];

  // Ballistic-only inputs
  candidateBallistic: Parameters<typeof buildBallisticSection>[0]['candidateBallistic'];
  ballisticInitialVelocitySummary: Parameters<typeof buildBallisticSection>[0]['ballisticInitialVelocitySummary'];
  ballisticResidualVelocitySummary: Parameters<typeof buildBallisticSection>[0]['ballisticResidualVelocitySummary'];
  ballisticPerforationSummary: Parameters<typeof buildBallisticSection>[0]['ballisticPerforationSummary'];
  ballisticPerforationTone: Parameters<typeof buildBallisticSection>[0]['ballisticPerforationTone'];
  ballisticEnergySummary: Parameters<typeof buildBallisticSection>[0]['ballisticEnergySummary'];
  ballisticEnergyTone: Parameters<typeof buildBallisticSection>[0]['ballisticEnergyTone'];
  ballisticAnimationSummary: Parameters<typeof buildBallisticSection>[0]['ballisticAnimationSummary'];
  ballisticTimeStepStudySummary: Parameters<typeof buildBallisticSection>[0]['ballisticTimeStepStudySummary'];
  ballisticTimeStepStudyTone: Parameters<typeof buildBallisticSection>[0]['ballisticTimeStepStudyTone'];
  ballisticTimeStepStudy: Parameters<typeof buildBallisticSection>[0]['ballisticTimeStepStudy'];
  ballisticTier2BlockerSummary: Parameters<typeof buildBallisticSection>[0]['ballisticTier2BlockerSummary'];

  // Gate-only inputs
  reviewerSummary: Parameters<typeof buildGateSection>[0]['reviewerSummary'];
  candidateReviewer: Parameters<typeof buildGateSection>[0]['candidateReviewer'];
  candidateLimitations: Parameters<typeof buildGateSection>[0]['candidateLimitations'];
  tier2BlockerSummary: Parameters<typeof buildGateSection>[0]['tier2BlockerSummary'];
}

export interface UseTrustSectionsResult {
  trustStrip: OperatorStatusItem[];
  sections: OperatorStatusSection[];
}

/** Build trust strip + 7 trust sections with granular per-section
 * memoization. Each section is independently memoized so unrelated
 * input changes do NOT bust an unrelated section's cached output.
 *
 * Callers MUST pass a stable `ctx` shape; primitive fields are
 * compared by value (React useMemo dep arrays); object fields are
 * compared by identity (so caller is responsible for not creating
 * fresh ones on every render unless the data actually changed). */
export function useTrustSections(
  ctx: UseTrustSectionsContext,
): UseTrustSectionsResult {
  const trustStrip = useMemo(
    () =>
      buildTrustStrip({
        claimTier: ctx.claimTier,
        allowedClaim: ctx.allowedClaim,
        solverTruthSource: ctx.solverTruthSource,
        candidateSpine: ctx.candidateSpine,
        currentJobId: ctx.currentJobId,
        executionMode: ctx.executionMode,
        report: ctx.report,
        reportValidationStatus: ctx.reportValidationStatus,
        referenceStatusRaw: ctx.referenceStatusRaw,
        goldenSampleSummary: ctx.goldenSampleSummary,
        goldenSampleReviewCount: ctx.goldenSampleReviewCount,
        blueprintSummary: ctx.blueprintSummary,
      }),
    [
      ctx.claimTier,
      ctx.allowedClaim,
      ctx.solverTruthSource,
      ctx.candidateSpine,
      ctx.currentJobId,
      ctx.executionMode,
      ctx.report,
      ctx.reportValidationStatus,
      ctx.referenceStatusRaw,
      ctx.goldenSampleSummary,
      ctx.goldenSampleReviewCount,
      ctx.blueprintSummary,
    ],
  );

  const overviewSection = useMemo(
    () =>
      buildOverviewSection({
        icon: ctx.overviewIcon,
        candidateSpine: ctx.candidateSpine,
        activeCaseId: ctx.activeCaseId,
        file: ctx.file,
        caseLabel: ctx.caseLabel,
        nextAction: ctx.nextAction,
      }),
    [
      ctx.overviewIcon,
      ctx.candidateSpine,
      ctx.activeCaseId,
      ctx.file,
      ctx.caseLabel,
      ctx.nextAction,
    ],
  );

  const runtimeSection = useMemo(
    () =>
      buildRuntimeSection({
        icon: ctx.runtimeIcon,
        solverTruthSource: ctx.solverTruthSource,
        candidateSpine: ctx.candidateSpine,
        currentJobId: ctx.currentJobId,
        executionMode: ctx.executionMode,
        report: ctx.report,
        analysisModeLabel: ctx.analysisModeLabel,
        currentJobLabel: ctx.currentJobLabel,
        lastSolverMaterialReference: ctx.lastSolverMaterialReference,
        runState: ctx.runState,
        runStateTone: ctx.runStateTone,
        latestEvent: ctx.latestEvent,
        solverLogSummary: ctx.solverLogSummary,
        solverLogState: ctx.solverLogState,
        convergenceSummary: ctx.convergenceSummary,
        candidateConvergenceEvidence: ctx.candidateConvergenceEvidence,
        convergenceClaimImpact: ctx.convergenceClaimImpact,
      }),
    [
      ctx.runtimeIcon,
      ctx.solverTruthSource,
      ctx.candidateSpine,
      ctx.currentJobId,
      ctx.executionMode,
      ctx.report,
      ctx.analysisModeLabel,
      ctx.currentJobLabel,
      ctx.lastSolverMaterialReference,
      ctx.runState,
      ctx.runStateTone,
      ctx.latestEvent,
      ctx.solverLogSummary,
      ctx.solverLogState,
      ctx.convergenceSummary,
      ctx.candidateConvergenceEvidence,
      ctx.convergenceClaimImpact,
    ],
  );

  const evidenceSection = useMemo(
    () =>
      buildEvidenceSection({
        icon: ctx.evidenceIcon,
        report: ctx.report,
        evidenceState: ctx.evidenceState,
        manifestState: ctx.manifestState,
        candidateManifest: ctx.candidateManifest,
        currentJobId: ctx.currentJobId,
        backendProvenance: ctx.backendProvenance,
        meshArtifactSource: ctx.meshArtifactSource,
        candidateMeshEvidence: ctx.candidateMeshEvidence,
        convergenceArtifactList: ctx.convergenceArtifactList,
        candidateConvergenceEvidence: ctx.candidateConvergenceEvidence,
        meshConvergenceStudySource: ctx.meshConvergenceStudySource,
        meshConvergenceStudy: ctx.meshConvergenceStudy,
        meshConvergenceClaimImpact: ctx.meshConvergenceClaimImpact,
      }),
    [
      ctx.evidenceIcon,
      ctx.report,
      ctx.evidenceState,
      ctx.manifestState,
      ctx.candidateManifest,
      ctx.currentJobId,
      ctx.backendProvenance,
      ctx.meshArtifactSource,
      ctx.candidateMeshEvidence,
      ctx.convergenceArtifactList,
      ctx.candidateConvergenceEvidence,
      ctx.meshConvergenceStudySource,
      ctx.meshConvergenceStudy,
      ctx.meshConvergenceClaimImpact,
    ],
  );

  const validationSection = useMemo(
    () =>
      buildValidationSection({
        icon: ctx.validationIcon,
        referenceStatus: ctx.referenceStatus,
        referenceStatusRaw: ctx.referenceStatusRaw,
        referenceReason: ctx.referenceReason,
        referenceDeviation: ctx.referenceDeviation,
        report: ctx.report,
        reportValidationStatus: ctx.reportValidationStatus,
        unitSummary: ctx.unitSummary,
        candidateAssumptions: ctx.candidateAssumptions,
        materialSummary: ctx.materialSummary,
        boundarySummary: ctx.boundarySummary,
        meshTopologySummary: ctx.meshTopologySummary,
        meshDeckElementTypes: ctx.meshDeckElementTypes,
        candidateMeshEvidence: ctx.candidateMeshEvidence,
        meshQualitySummary: ctx.meshQualitySummary,
        meshClaimImpact: ctx.meshClaimImpact,
        meshConvergenceStudy: ctx.meshConvergenceStudy,
        meshConvergenceStudySummary: ctx.meshConvergenceStudySummary,
        meshConvergenceClaimImpact: ctx.meshConvergenceClaimImpact,
        convergenceMissingSummary: ctx.convergenceMissingSummary,
        failurePatternRef: ctx.failurePatternRef,
      }),
    [
      ctx.validationIcon,
      ctx.referenceStatus,
      ctx.referenceStatusRaw,
      ctx.referenceReason,
      ctx.referenceDeviation,
      ctx.report,
      ctx.reportValidationStatus,
      ctx.unitSummary,
      ctx.candidateAssumptions,
      ctx.materialSummary,
      ctx.boundarySummary,
      ctx.meshTopologySummary,
      ctx.meshDeckElementTypes,
      ctx.candidateMeshEvidence,
      ctx.meshQualitySummary,
      ctx.meshClaimImpact,
      ctx.meshConvergenceStudy,
      ctx.meshConvergenceStudySummary,
      ctx.meshConvergenceClaimImpact,
      ctx.convergenceMissingSummary,
      ctx.failurePatternRef,
    ],
  );

  const blueprintTargetSection = useMemo(
    () =>
      buildBlueprintTargetSection({
        icon: ctx.blueprintIcon,
        blueprintSummary: ctx.blueprintSummary,
      }),
    [ctx.blueprintIcon, ctx.blueprintSummary],
  );

  const ballisticSection = useMemo(
    () =>
      buildBallisticSection({
        icon: ctx.ballisticIcon,
        candidateBallistic: ctx.candidateBallistic,
        ballisticInitialVelocitySummary: ctx.ballisticInitialVelocitySummary,
        ballisticResidualVelocitySummary: ctx.ballisticResidualVelocitySummary,
        ballisticPerforationSummary: ctx.ballisticPerforationSummary,
        ballisticPerforationTone: ctx.ballisticPerforationTone,
        ballisticEnergySummary: ctx.ballisticEnergySummary,
        ballisticEnergyTone: ctx.ballisticEnergyTone,
        ballisticAnimationSummary: ctx.ballisticAnimationSummary,
        ballisticTimeStepStudySummary: ctx.ballisticTimeStepStudySummary,
        ballisticTimeStepStudyTone: ctx.ballisticTimeStepStudyTone,
        ballisticTimeStepStudy: ctx.ballisticTimeStepStudy,
        ballisticTier2BlockerSummary: ctx.ballisticTier2BlockerSummary,
      }),
    [
      ctx.ballisticIcon,
      ctx.candidateBallistic,
      ctx.ballisticInitialVelocitySummary,
      ctx.ballisticResidualVelocitySummary,
      ctx.ballisticPerforationSummary,
      ctx.ballisticPerforationTone,
      ctx.ballisticEnergySummary,
      ctx.ballisticEnergyTone,
      ctx.ballisticAnimationSummary,
      ctx.ballisticTimeStepStudySummary,
      ctx.ballisticTimeStepStudyTone,
      ctx.ballisticTimeStepStudy,
      ctx.ballisticTier2BlockerSummary,
    ],
  );

  const gateSection = useMemo(
    () =>
      buildGateSection({
        icon: ctx.gateIcon,
        reviewerSummary: ctx.reviewerSummary,
        candidateReviewer: ctx.candidateReviewer,
        allowedClaim: ctx.allowedClaim,
        candidateLimitations: ctx.candidateLimitations,
        tier2BlockerSummary: ctx.tier2BlockerSummary,
      }),
    [
      ctx.gateIcon,
      ctx.reviewerSummary,
      ctx.candidateReviewer,
      ctx.allowedClaim,
      ctx.candidateLimitations,
      ctx.tier2BlockerSummary,
    ],
  );

  const sections = useMemo(
    () => [
      overviewSection,
      runtimeSection,
      evidenceSection,
      validationSection,
      blueprintTargetSection,
      ballisticSection,
      gateSection,
    ],
    [
      overviewSection,
      runtimeSection,
      evidenceSection,
      validationSection,
      blueprintTargetSection,
      ballisticSection,
      gateSection,
    ],
  );

  return { trustStrip, sections };
}
