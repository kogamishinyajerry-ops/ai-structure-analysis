// FM-04a Phase 26 D — trust center view-model builder tests.
//
// App.tsx Phase 26 D extraction: trustStrip + 4 sections + Gate
// section now flow through pure builders in
// `src/state/trustCenterViewModel.ts`. The Blueprint target +
// Ballistic candidate sections stay inline in App.tsx (honest scope
// — they close over many derived locals; extracting them would have
// ballooned the context interface).
//
// Anti-gaming guards:
//   * D:-1 — purity. Same context → byte-equal output. No
//     Date.now / localStorage / random.
//   * D:-2 — tone discriminator (`statusTone`) is the SAME function
//     used inline before extraction; existing callsites' behavior
//     is preserved (de-dup, not refactor).
//   * D:-3 — context objects do NOT mutate any field; builders may
//     destructure but must not call `Object.assign` / `splice` etc.
//     against ctx.
//
// Tier 1 / Tier 2 engineering candidate; not signed validation; not
// benchmark agreement.

import { describe, expect, it } from 'vitest'

import {
  buildEvidenceSection,
  buildGateSection,
  buildOverviewSection,
  buildRuntimeSection,
  buildTrustStrip,
  buildValidationSection,
  statusTone,
} from '../src/state/trustCenterViewModel'

describe('Phase 26 D — statusTone helper', () => {
  it('undefined → muted', () => {
    expect(statusTone(undefined)).toBe('muted')
  })
  it('case-insensitive PASS / PASSED / COMPLETED / ACCEPT → accent', () => {
    expect(statusTone('PASS')).toBe('accent')
    expect(statusTone('Passed')).toBe('accent')
    expect(statusTone('completed')).toBe('accent')
    expect(statusTone('accept')).toBe('accent')
  })
  it('case-insensitive FAIL / FAILED / CRITICAL / REJECTED → danger', () => {
    expect(statusTone('FAIL')).toBe('danger')
    expect(statusTone('failed')).toBe('danger')
    expect(statusTone('Critical')).toBe('danger')
    expect(statusTone('rejected')).toBe('danger')
  })
  it('other strings → warning', () => {
    expect(statusTone('observed')).toBe('warning')
    expect(statusTone('in_progress')).toBe('warning')
  })
})

describe('Phase 26 D — buildTrustStrip', () => {
  function baseCtx() {
    return {
      claimTier: 'Tier 1 engineering candidate',
      allowedClaim: 'not_signed_validation',
      solverTruthSource: 'No live solver',
      candidateSpine: null,
      currentJobId: null,
      executionMode: 'Local fixture',
      report: null,
      reportValidationStatus: 'Not surfaced',
      referenceStatusRaw: undefined,
      goldenSampleSummary: '5 indexed',
      goldenSampleReviewCount: 0,
      blueprintSummary: {
        label: 'Workbench parity scope',
        coveredAnchorCount: 1,
        anchorCount: 5,
        availableEvidenceCount: 1,
        allowedClaim: 'not_signed_validation',
      },
    }
  }

  it('emits 7 items in pinned order', () => {
    const strip = buildTrustStrip(baseCtx())
    expect(strip).toHaveLength(7)
    expect(strip.map((s) => s.label)).toEqual([
      'Claim tier',
      'Solver truth',
      'Execution mode',
      'Validation status',
      'Golden samples',
      'Blueprint target',
      'Allowed claim',
    ])
  })

  it('Solver-truth tone flips to accent when a job is running', () => {
    const ctx = baseCtx()
    expect(buildTrustStrip(ctx)[1].tone).toBe('warning')
    ctx.currentJobId = 'job-42'
    expect(buildTrustStrip(ctx)[1].tone).toBe('accent')
  })

  it('Solver-truth tone is accent when a candidate spine is present', () => {
    const ctx = baseCtx()
    ctx.candidateSpine = { whatever: true }
    expect(buildTrustStrip(ctx)[1].tone).toBe('accent')
  })

  it('Allowed-claim row is always danger-toned', () => {
    expect(buildTrustStrip(baseCtx())[6].tone).toBe('danger')
  })

  it('Validation-status tone propagates from report.validation.status', () => {
    const ctx = baseCtx()
    ctx.report = { validation: { status: 'failed' } }
    expect(buildTrustStrip(ctx)[3].tone).toBe('danger')
  })

  it('Validation-status tone falls back to referenceStatusRaw', () => {
    const ctx = baseCtx()
    ctx.referenceStatusRaw = 'pass'
    expect(buildTrustStrip(ctx)[3].tone).toBe('accent')
  })

  it('Golden-samples tone is warning when reviewCount > 0', () => {
    const ctx = baseCtx()
    ctx.goldenSampleReviewCount = 2
    expect(buildTrustStrip(ctx)[4].tone).toBe('warning')
  })

  it('purity — same context returns deep-equal output across two calls', () => {
    const ctx = baseCtx()
    const a = buildTrustStrip(ctx)
    const b = buildTrustStrip(ctx)
    expect(a).toEqual(b)
  })
})

describe('Phase 26 D — section builders', () => {
  it('buildOverviewSection emits 4 items and correct title', () => {
    const section = buildOverviewSection({
      icon: 'overview-icon',
      candidateSpine: null,
      activeCaseId: null,
      file: null,
      caseLabel: 'No active case',
      nextAction: 'Pick a case',
    })
    expect(section.title).toBe('Overview')
    expect(section.icon).toBe('overview-icon')
    expect(section.items).toHaveLength(4)
    expect(section.items[0].label).toBe('Milestone')
    expect(section.items[0].value).toContain('FM-01')
  })

  it('buildOverviewSection Milestone flips to FM-03 when candidate spine is present', () => {
    const section = buildOverviewSection({
      icon: 'overview-icon',
      candidateSpine: { foo: 'bar' },
      activeCaseId: 'case-001',
      file: null,
      caseLabel: 'case-001',
      nextAction: 'Run solver',
    })
    expect(section.items[0].value).toContain('FM-03')
  })

  it('buildRuntimeSection emits 9 items', () => {
    const section = buildRuntimeSection({
      icon: 'runtime-icon',
      solverTruthSource: 'No live solver',
      candidateSpine: null,
      currentJobId: null,
      executionMode: 'Local fixture',
      report: null,
      analysisModeLabel: 'Static',
      currentJobLabel: 'No current job',
      lastSolverMaterialReference: null,
      runState: 'idle',
      runStateTone: 'muted',
      latestEvent: 'None',
      solverLogSummary: 'No logs',
      solverLogState: null,
      convergenceSummary: 'No convergence',
      candidateConvergenceEvidence: null,
      convergenceClaimImpact: undefined,
    })
    expect(section.title).toBe('Runtime')
    expect(section.items).toHaveLength(9)
    // Material reference falls back to a friendly placeholder when null.
    const matRow = section.items.find((i) => i.label === 'Material reference')!
    expect(matRow.value).toContain('No solver run')
  })

  it('buildRuntimeSection Material reference passes citation through when present', () => {
    const section = buildRuntimeSection({
      icon: null,
      solverTruthSource: 'live',
      candidateSpine: { ok: true },
      currentJobId: 'job-99',
      executionMode: 'ccx subprocess',
      report: { validation: {} },
      analysisModeLabel: 'Static',
      currentJobLabel: 'job-99',
      lastSolverMaterialReference: 'EN 10025-2:2019',
      runState: 'running',
      runStateTone: 'accent',
      latestEvent: 'Step 1',
      solverLogSummary: 'available',
      solverLogState: { status: 'available' },
      convergenceSummary: 'converged',
      candidateConvergenceEvidence: { history: [] },
      convergenceClaimImpact: 'Tier 1 health',
    })
    const matRow = section.items.find((i) => i.label === 'Material reference')!
    expect(matRow.value).toBe('EN 10025-2:2019')
    expect(matRow.tone).toBe('accent')
  })

  it('buildEvidenceSection emits 8 items', () => {
    const section = buildEvidenceSection({
      icon: 'evidence-icon',
      report: null,
      evidenceState: 'No evidence',
      manifestState: 'No manifest',
      candidateManifest: null,
      currentJobId: null,
      backendProvenance: 'Local fixture',
      meshArtifactSource: 'None',
      candidateMeshEvidence: null,
      convergenceArtifactList: 'None',
      candidateConvergenceEvidence: null,
      meshConvergenceStudySource: 'None',
      meshConvergenceStudy: null,
      meshConvergenceClaimImpact: undefined,
    })
    expect(section.title).toBe('Evidence')
    expect(section.items).toHaveLength(8)
  })

  it('buildEvidenceSection Artifact list joins kind:status pairs', () => {
    const section = buildEvidenceSection({
      icon: null,
      report: { ok: true },
      evidenceState: 'present',
      manifestState: 'sha256:abc',
      candidateManifest: {
        items: [
          { kind: 'mesh', status: 'available' },
          { kind: 'result_mesh', status: 'available' },
        ],
      },
      currentJobId: 'job-1',
      backendProvenance: 'ccx 2.20',
      meshArtifactSource: 'gmsh',
      candidateMeshEvidence: { ok: true },
      convergenceArtifactList: '1 row',
      candidateConvergenceEvidence: { ok: true },
      meshConvergenceStudySource: 'none',
      meshConvergenceStudy: null,
      meshConvergenceClaimImpact: undefined,
    })
    const artifactRow = section.items.find((i) => i.label === 'Artifact list')!
    expect(artifactRow.value).toBe('mesh:available, result_mesh:available')
  })

  it('buildValidationSection emits 11 items', () => {
    const section = buildValidationSection({
      icon: 'validation-icon',
      referenceStatus: 'Not surfaced',
      referenceStatusRaw: undefined,
      referenceReason: 'No reference snapshot',
      referenceDeviation: 'N/A',
      report: null,
      reportValidationStatus: 'Not surfaced',
      unitSummary: 'Not declared',
      candidateAssumptions: null,
      materialSummary: 'Not declared',
      boundarySummary: 'Not declared',
      meshTopologySummary: 'Not declared',
      meshDeckElementTypes: undefined,
      candidateMeshEvidence: null,
      meshQualitySummary: 'Not declared',
      meshClaimImpact: 'Tier 1 candidate',
      meshConvergenceStudy: null,
      meshConvergenceStudySummary: 'Not declared',
      meshConvergenceClaimImpact: undefined,
      convergenceMissingSummary: 'None',
      failurePatternRef: 'FP-001',
    })
    expect(section.title).toBe('Validation')
    expect(section.items).toHaveLength(11)
    const fpRow = section.items.find((i) => i.label === 'FailurePattern')!
    expect(fpRow.tone).toBe('warning')
  })

  it('buildValidationSection FailurePattern tone is muted for non-FP refs', () => {
    const section = buildValidationSection({
      icon: null,
      referenceStatus: '',
      referenceStatusRaw: undefined,
      referenceReason: '',
      referenceDeviation: '',
      report: null,
      reportValidationStatus: '',
      unitSummary: '',
      candidateAssumptions: null,
      materialSummary: '',
      boundarySummary: '',
      meshTopologySummary: '',
      meshDeckElementTypes: undefined,
      candidateMeshEvidence: null,
      meshQualitySummary: '',
      meshClaimImpact: '',
      meshConvergenceStudy: null,
      meshConvergenceStudySummary: '',
      meshConvergenceClaimImpact: undefined,
      convergenceMissingSummary: '',
      failurePatternRef: 'no-pattern',
    })
    const fpRow = section.items.find((i) => i.label === 'FailurePattern')!
    expect(fpRow.tone).toBe('muted')
  })

  it('buildGateSection emits 5 items', () => {
    const section = buildGateSection({
      icon: 'gate-icon',
      reviewerSummary: 'Not surfaced',
      candidateReviewer: null,
      allowedClaim: 'not signed validation',
      candidateLimitations: [],
      tier2BlockerSummary: '4 blockers',
    })
    expect(section.title).toBe('Gate')
    expect(section.items).toHaveLength(5)
  })

  it('buildGateSection Reviewer-gate tone flips to accent when verdict is ready', () => {
    const section = buildGateSection({
      icon: null,
      reviewerSummary: 'Ready for review',
      candidateReviewer: {
        verdict: 'candidate_ready_for_review',
        summary: 'All checks green',
      },
      allowedClaim: 'not signed validation',
      candidateLimitations: ['short report'],
      tier2BlockerSummary: '0 blockers',
    })
    const reviewerRow = section.items.find((i) => i.label === 'Reviewer gate')!
    expect(reviewerRow.tone).toBe('accent')
    // Limitations row joins on '; '
    const limRow = section.items.find((i) => i.label === 'Limitations')!
    expect(limRow.value).toBe('short report')
  })

  it('buildGateSection Limitations falls back when empty', () => {
    const section = buildGateSection({
      icon: null,
      reviewerSummary: '',
      candidateReviewer: null,
      allowedClaim: '',
      candidateLimitations: [],
      tier2BlockerSummary: '',
    })
    const limRow = section.items.find((i) => i.label === 'Limitations')!
    expect(limRow.value).toBe('No candidate limitations surfaced')
  })
})

describe('Phase 26 D — D:-3 purity (no context mutation)', () => {
  it('buildTrustStrip does not mutate its ctx', () => {
    const ctx = {
      claimTier: 'x',
      allowedClaim: 'x',
      solverTruthSource: 'x',
      candidateSpine: null,
      currentJobId: null,
      executionMode: 'x',
      report: null,
      reportValidationStatus: 'x',
      referenceStatusRaw: undefined,
      goldenSampleSummary: 'x',
      goldenSampleReviewCount: 0,
      blueprintSummary: {
        label: 'x',
        coveredAnchorCount: 0,
        anchorCount: 0,
        availableEvidenceCount: 0,
        allowedClaim: 'x',
      },
    }
    const before = JSON.parse(JSON.stringify(ctx))
    buildTrustStrip(ctx)
    expect(ctx).toEqual(before)
  })
})
