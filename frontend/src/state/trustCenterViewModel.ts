// FM-04a Phase 26 D — Trust Center view-model builders.
//
// Extracts the trustStrip + trustSections object literals from
// App.tsx into pure builder functions. App.tsx still computes the
// many derived variables (the "facts of the world" as seen by the
// reviewer); these builders just translate that fact-set into the
// shape OperatorStatusPanel expects.
//
// Phase 26 D scope (honest):
//   * trustStrip (7 items)
//   * 7 trustSections: Overview, Runtime, Evidence, Validation,
//     Blueprint target, Ballistic candidate, Gate
//   * statusTone helper (moved here so the builders can call it
//     without importing back from App.tsx)
//
// Anti-gaming guard D:-1 — the builders are PURE. Same context →
// byte-equal output. No hidden time-dependent state, no `Date.now()`,
// no localStorage. Renderers can memoize on context identity.
//
// Tier 1 / Tier 2 engineering candidate; not signed validation; not
// benchmark agreement.

import type { ReactNode } from 'react';

import type {
  OperatorStatusItem,
  OperatorStatusSection,
} from '../types/AppTypes';

/** Status → tone color discriminator. Moved out of App.tsx so the
 * builders can compose it. */
export function statusTone(status?: string): OperatorStatusItem['tone'] {
  if (!status) return 'muted';
  const s = status.toLowerCase();
  if (['pass', 'passed', 'completed', 'accept'].includes(s)) return 'accent';
  if (['fail', 'failed', 'critical', 'rejected'].includes(s)) return 'danger';
  return 'warning';
}

// ---------------------------------------------------------------------
// trustStrip
// ---------------------------------------------------------------------

export interface TrustStripContext {
  claimTier: string;
  allowedClaim: string;
  solverTruthSource: string;
  candidateSpine: unknown; // truthy/falsy is the only thing we care about
  currentJobId: string | null;
  executionMode: string;
  report: { validation: { status?: string } } | null;
  reportValidationStatus: string;
  referenceStatusRaw: string | undefined;
  goldenSampleSummary: string;
  goldenSampleReviewCount: number;
  blueprintSummary: {
    label: string;
    coveredAnchorCount: number;
    anchorCount: number;
    availableEvidenceCount: number;
    allowedClaim: string;
  };
}

export function buildTrustStrip(ctx: TrustStripContext): OperatorStatusItem[] {
  const liveSolver = Boolean(ctx.candidateSpine) || Boolean(ctx.currentJobId);
  return [
    { label: 'Claim tier', value: ctx.claimTier, tone: 'warning', detail: ctx.allowedClaim },
    { label: 'Solver truth', value: ctx.solverTruthSource, tone: liveSolver ? 'accent' : 'warning' },
    { label: 'Execution mode', value: ctx.executionMode, tone: liveSolver ? 'accent' : ctx.report ? 'warning' : 'muted' },
    {
      label: 'Validation status',
      value: ctx.reportValidationStatus,
      tone: ctx.report?.validation.status ? statusTone(ctx.report.validation.status) : statusTone(ctx.referenceStatusRaw),
    },
    { label: 'Golden samples', value: ctx.goldenSampleSummary, tone: ctx.goldenSampleReviewCount > 0 ? 'warning' : 'accent' },
    {
      label: 'Blueprint target',
      value: ctx.blueprintSummary.label,
      tone: 'warning',
      detail: `${ctx.blueprintSummary.coveredAnchorCount}/${ctx.blueprintSummary.anchorCount} anchors covered by ${ctx.blueprintSummary.availableEvidenceCount} available evidence ref(s); ${ctx.blueprintSummary.allowedClaim}`,
    },
    { label: 'Allowed claim', value: 'not signed validation', tone: 'danger', detail: ctx.allowedClaim },
  ];
}

// ---------------------------------------------------------------------
// section builders
// ---------------------------------------------------------------------

export interface OverviewSectionContext {
  icon: ReactNode;
  candidateSpine: unknown;
  activeCaseId: string | null;
  file: File | null;
  caseLabel: string;
  nextAction: string;
}

export function buildOverviewSection(
  ctx: OverviewSectionContext,
): OperatorStatusSection {
  return {
    title: 'Overview',
    icon: ctx.icon,
    items: [
      { label: 'Milestone', value: ctx.candidateSpine ? 'FM-03 Candidate Report Spine' : 'FM-01 Web Console Operator Shell', tone: 'accent' },
      { label: 'Work control', value: 'User blueprint scope; no Linear/Notion external write in this local slice', tone: 'warning' },
      { label: 'Active case', value: ctx.caseLabel, tone: ctx.activeCaseId || ctx.file ? 'accent' : 'muted' },
      { label: 'Next action', value: ctx.nextAction, tone: 'accent' },
    ],
  };
}

export interface RuntimeSectionContext {
  icon: ReactNode;
  solverTruthSource: string;
  candidateSpine: unknown;
  currentJobId: string | null;
  executionMode: string;
  report: unknown;
  analysisModeLabel: string;
  currentJobLabel: string;
  lastSolverMaterialReference: string | null;
  runState: string;
  runStateTone: OperatorStatusItem['tone'];
  latestEvent: string;
  solverLogSummary: string;
  solverLogState: { status?: string; unavailable_reason?: string | null } | null;
  convergenceSummary: string;
  candidateConvergenceEvidence: unknown;
  convergenceClaimImpact: string | undefined;
}

export function buildRuntimeSection(
  ctx: RuntimeSectionContext,
): OperatorStatusSection {
  const liveSolver = Boolean(ctx.candidateSpine) || Boolean(ctx.currentJobId);
  return {
    title: 'Runtime',
    icon: ctx.icon,
    items: [
      { label: 'Solver truth source', value: ctx.solverTruthSource, tone: liveSolver ? 'accent' : 'warning' },
      { label: 'Execution mode', value: ctx.executionMode, tone: liveSolver ? 'accent' : ctx.report ? 'warning' : 'muted' },
      { label: 'Analysis mode', value: ctx.analysisModeLabel },
      { label: 'Current job', value: ctx.currentJobLabel, tone: ctx.currentJobId ? 'accent' : 'muted' },
      {
        label: 'Material reference',
        value: ctx.lastSolverMaterialReference ?? 'No solver run with material citation yet',
        tone: ctx.lastSolverMaterialReference ? 'accent' : 'muted',
        detail: ctx.lastSolverMaterialReference ?? undefined,
      },
      { label: 'Run state', value: ctx.runState, tone: ctx.runStateTone },
      { label: 'Latest event', value: ctx.latestEvent },
      {
        label: 'Solver logs',
        value: ctx.solverLogSummary,
        tone: ctx.solverLogState?.status === 'unavailable' ? 'warning' : ctx.candidateSpine ? 'accent' : 'muted',
        detail: ctx.solverLogState?.unavailable_reason ?? undefined,
      },
      {
        label: 'Solver convergence',
        value: ctx.convergenceSummary,
        tone: ctx.candidateConvergenceEvidence ? 'warning' : 'muted',
        detail: ctx.convergenceClaimImpact,
      },
    ],
  };
}

export interface EvidenceSectionContext {
  icon: ReactNode;
  report: unknown;
  evidenceState: string;
  manifestState: string;
  candidateManifest: { items: { kind: string; status: string }[] } | null;
  currentJobId: string | null;
  backendProvenance: string;
  meshArtifactSource: string;
  candidateMeshEvidence: unknown;
  convergenceArtifactList: string;
  candidateConvergenceEvidence: unknown;
  meshConvergenceStudySource: string;
  meshConvergenceStudy: { status?: string } | null;
  meshConvergenceClaimImpact: string | undefined;
}

export function buildEvidenceSection(
  ctx: EvidenceSectionContext,
): OperatorStatusSection {
  return {
    title: 'Evidence',
    icon: ctx.icon,
    items: [
      { label: 'Evidence state', value: ctx.evidenceState, tone: ctx.report ? 'accent' : 'warning' },
      { label: 'Manifest / hashes', value: ctx.manifestState, tone: ctx.candidateManifest ? 'accent' : ctx.currentJobId ? 'warning' : 'muted' },
      { label: 'Backend provenance', value: ctx.backendProvenance },
      {
        label: 'Artifact list',
        value: ctx.candidateManifest
          ? ctx.candidateManifest.items.map((item) => `${item.kind}:${item.status}`).join(', ')
          : 'No candidate artifact list surfaced',
        tone: ctx.candidateManifest ? 'accent' : 'muted',
      },
      { label: 'Mesh artifact source', value: ctx.meshArtifactSource, tone: ctx.candidateMeshEvidence ? 'accent' : 'muted' },
      { label: 'Convergence artifacts', value: ctx.convergenceArtifactList, tone: ctx.candidateConvergenceEvidence ? 'accent' : 'muted' },
      {
        label: 'Mesh convergence study',
        value: ctx.meshConvergenceStudySource,
        tone: ctx.meshConvergenceStudy?.status === 'available' ? 'accent' : 'warning',
        detail: ctx.meshConvergenceClaimImpact,
      },
      { label: 'Runtime SSOT', value: 'runs/ directory + CI artifacts; UI only surfaces current session state', tone: 'muted' },
    ],
  };
}

export interface ValidationSectionContext {
  icon: ReactNode;
  referenceStatus: string;
  referenceStatusRaw: string | undefined;
  referenceReason: string;
  referenceDeviation: string;
  report: { validation: { status?: string } } | null;
  reportValidationStatus: string;
  unitSummary: string;
  candidateAssumptions: {
    material: { status: string };
    boundary_conditions: { status: string };
  } | null;
  materialSummary: string;
  boundarySummary: string;
  meshTopologySummary: string;
  meshDeckElementTypes: string | undefined;
  candidateMeshEvidence: { quality: { status: string; unavailable_reason?: string | null } } | null;
  meshQualitySummary: string;
  meshClaimImpact: string;
  meshConvergenceStudy: { status?: string } | null;
  meshConvergenceStudySummary: string;
  meshConvergenceClaimImpact: string | undefined;
  convergenceMissingSummary: string;
  failurePatternRef: string;
}

export function buildValidationSection(
  ctx: ValidationSectionContext,
): OperatorStatusSection {
  return {
    title: 'Validation',
    icon: ctx.icon,
    items: [
      { label: 'Golden sample status', value: ctx.referenceStatus, tone: statusTone(ctx.referenceStatusRaw), detail: ctx.referenceReason },
      { label: 'Reference deviation', value: ctx.referenceDeviation, tone: ctx.report?.validation.status ? statusTone(ctx.report.validation.status) : 'muted' },
      { label: 'Report validation', value: ctx.reportValidationStatus, tone: ctx.report?.validation.status ? statusTone(ctx.report.validation.status) : 'muted' },
      { label: 'Units', value: ctx.unitSummary, tone: ctx.candidateAssumptions ? 'accent' : 'warning' },
      { label: 'Material', value: ctx.materialSummary, tone: ctx.candidateAssumptions?.material.status === 'declared' ? 'accent' : 'warning' },
      { label: 'BC / loads', value: ctx.boundarySummary, tone: ctx.candidateAssumptions?.boundary_conditions.status === 'declared' ? 'accent' : 'warning' },
      { label: 'Mesh topology', value: ctx.meshTopologySummary, tone: ctx.candidateMeshEvidence ? 'accent' : 'warning', detail: ctx.meshDeckElementTypes },
      {
        label: 'Mesh quality',
        value: ctx.meshQualitySummary,
        tone: ctx.candidateMeshEvidence?.quality.status === 'available' ? 'accent' : 'warning',
        detail: ctx.candidateMeshEvidence?.quality.unavailable_reason ?? ctx.meshClaimImpact,
      },
      {
        label: 'Mesh convergence',
        value: ctx.meshConvergenceStudySummary,
        tone: ctx.meshConvergenceStudy?.status === 'available' ? 'accent' : 'warning',
        detail: ctx.meshConvergenceClaimImpact,
      },
      { label: 'Convergence gaps', value: ctx.convergenceMissingSummary, tone: 'warning' },
      { label: 'FailurePattern', value: ctx.failurePatternRef, tone: ctx.failurePatternRef.startsWith('FP-') ? 'warning' : 'muted' },
    ],
  };
}

export interface GateSectionContext {
  icon: ReactNode;
  reviewerSummary: string;
  candidateReviewer: { verdict?: string; summary?: string } | null;
  allowedClaim: string;
  candidateLimitations: string[];
  tier2BlockerSummary: string;
}

export function buildGateSection(
  ctx: GateSectionContext,
): OperatorStatusSection {
  return {
    title: 'Gate',
    icon: ctx.icon,
    items: [
      {
        label: 'Reviewer gate',
        value: ctx.reviewerSummary,
        tone: ctx.candidateReviewer?.verdict === 'candidate_ready_for_review' ? 'accent' : 'warning',
        detail: ctx.candidateReviewer?.summary,
      },
      { label: 'Human / Claude handoff', value: 'Required before milestone acceptance or signed claim promotion', tone: 'warning' },
      { label: 'Allowed claim', value: ctx.allowedClaim, tone: 'danger' },
      {
        label: 'Limitations',
        value: ctx.candidateLimitations.length > 0 ? ctx.candidateLimitations.join('; ') : 'No candidate limitations surfaced',
        tone: 'warning',
      },
      { label: 'Tier 2 blockers', value: ctx.tier2BlockerSummary, tone: 'danger' },
    ],
  };
}
