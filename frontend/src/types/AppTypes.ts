// FM-04a Phase 22 C — types extracted out of App.tsx as part of the
// LOC-discipline trajectory started Phase 19 D + 20 D + 21 D. These
// interfaces are exposed unchanged so the existing tab panels +
// components keep importing from a stable path.
//
// Tier 1 / Tier 2 engineering candidate; not signed validation; not
// benchmark agreement.

import type { ReactNode } from 'react';

export interface CaseMetadata {
  id: string;
  name: string;
  description: string;
  type: string;
  structure: string;
  frd_path: string;
}

export interface CaseReferenceDetails {
  case_id?: string;
  case_name?: string;
  status?: string;
  status_reason?: string;
  failure_pattern_ref?: string;
  metadata?: Record<string, unknown>;
}

export interface ReportData {
  summary: string;
  metrics: {
    max_displacement: number;
    max_von_mises: number;
    safety_factor: number;
    status: 'PASS' | 'FAIL' | 'CRITICAL' | 'N/A';
  };
  validation: {
    status: string;
    error_percentage: number;
  };
  markdown: string;
  candidate_report_spine?: CandidateReportSpine;
  increments?: {
    index: number;
    step: number;
    type: string;
    value: number;
    max_displacement: number;
    max_von_mises: number;
  }[];
}

export interface CandidateArtifact {
  kind: string;
  status: string;
  path: string;
  file_name?: string;
  sha256?: string;
  size_bytes?: number;
  description: string;
  unavailable_reason?: string;
  signals?: string[];
}

export interface CandidateMeshEvidence {
  status: string;
  claim_impact: string;
  result_mesh: {
    source: string;
    node_count: number;
    element_count: number;
    increment_count: number;
  };
  input_deck: {
    status: string;
    path?: string;
    node_count?: number;
    element_count?: number;
    element_types?: Record<string, number>;
    include_count?: number;
    limitation?: string;
    unavailable_reason?: string;
  };
  metadata: {
    status: string;
    source?: string;
    artifacts: CandidateArtifact[];
    generation_mode?: string | null;
    mesh_level?: string | null;
    element_order?: string | null;
    thin_wall_detected?: boolean | null;
    unavailable_reason?: string;
  };
  quality: {
    status: string;
    source?: string | null;
    metrics: Record<string, unknown>;
    thresholds?: Record<string, unknown>;
    findings?: string[];
    claim_impact?: string;
    artifact_count?: number;
    unavailable_reason?: string;
  };
  convergence_study: CandidateMeshConvergenceStudy;
}

export interface CandidateMeshConvergenceStudy {
  status: string;
  source?: string;
  study_status?: string;
  parameter?: string;
  metric?: string;
  tolerance_pct?: number;
  relative_change_pct?: number;
  run_count?: number;
  runs?: Record<string, unknown>[];
  claim_boundary?: string;
  claim_impact?: string;
  unavailable_reason?: string;
}

export interface CandidateConvergenceEvidence {
  status: string;
  claim_impact: string;
  normal_termination: string;
  latest_job_status?: string | null;
  source_artifacts: CandidateArtifact[];
  mesh_refinement_study?: CandidateMeshConvergenceStudy;
  signals: string[];
  missing_reasons: string[];
}

export interface CandidateBallisticEvidence {
  status: string;
  claim_impact: string;
  claim_boundary: string;
  projectile_initial_velocity: {
    status: string;
    value_m_per_s?: number | null;
    source?: string;
    unavailable_reason?: string;
  };
  residual_velocity_candidate: {
    status: string;
    value_m_per_s?: number | null;
    extraction_source?: string;
    claim_impact?: string;
    unavailable_reason?: string;
  };
  perforation_marker: {
    status: string;
    evidence_path?: string | null;
    claim_impact?: string;
    unavailable_reason?: string;
  };
  energy_balance_candidate: {
    status: string;
    source?: string;
    initial_kinetic_energy_j?: number | null;
    plastic_dissipation_j?: number | null;
    contact_friction_j?: number | null;
    hourglass_energy_j?: number | null;
    residual_kinetic_energy_j?: number | null;
    energy_ratio?: number | null;
    claim_impact?: string;
    unavailable_reason?: string;
  };
  animation_manifest: {
    status: string;
    path?: string;
    sha256?: string;
    size_bytes?: number;
    claim_impact?: string;
    unavailable_reason?: string;
  };
  time_step_series_summary: {
    status: string;
    source?: string;
    step_count?: number | null;
    min_dt_s?: number | null;
    max_dt_s?: number | null;
    mean_dt_s?: number | null;
    claim_impact?: string;
    unavailable_reason?: string;
  };
  time_step_convergence_study: {
    status: string;
    source?: string;
    study_status?: string;
    parameter?: string;
    metric?: string;
    tolerance_pct?: number | null;
    relative_change_pct?: number | null;
    candidate_stability?: string;
    run_count?: number;
    runs?: Record<string, unknown>[];
    claim_boundary?: string;
    claim_impact?: string;
    unavailable_reason?: string;
  };
  tier2_blockers_ballistic: string[];
}

export interface CandidateReportSpine {
  schema_version: string;
  claim_tier: string;
  allowed_claim: string;
  no_overclaim: string;
  case: {
    case_id: string;
    case_name: string;
    expected_results_status: string;
    status_reason: string;
    failure_pattern_ref: string;
  };
  provenance: {
    report_surface: string;
    parser: string;
    result_file_name: string;
    original_filename: string;
    file_size_bytes: number;
    parse_time_s: number;
    is_binary_frd: boolean;
    node_count: number;
    element_count: number;
    increment_count: number;
    solver_truth_source: string;
  };
  solver: {
    truth_source: string;
    latest_job_id?: string | null;
    latest_job_status?: string | null;
    normal_termination_state: string;
    logs: {
      status: string;
      line_count?: number | null;
      tail: string[];
      artifact_paths: string[];
      unavailable_reason?: string;
    };
  };
  assumptions: {
    unit_system: {
      status: string;
      stress_unit: string;
      length_unit: string;
    };
    material: {
      status: string;
      value?: unknown;
      unavailable_reason?: string;
    };
    boundary_conditions: {
      status: string;
      value?: unknown;
      unavailable_reason?: string;
    };
    contact: {
      status: string;
      unavailable_reason?: string;
    };
  };
  mesh_evidence?: CandidateMeshEvidence;
  convergence_evidence?: CandidateConvergenceEvidence;
  ballistic?: CandidateBallisticEvidence;
  artifact_manifest: {
    manifest_id: string;
    hash_algorithm: string;
    hash_count: number;
    items: CandidateArtifact[];
  };
  limitations: string[];
  reviewer_summary: {
    verdict: string;
    summary: string;
    blocked_findings: string[];
    next_actions: string[];
  };
  tier2_blockers: string[];
}

export interface ExperimentStatus {
  id: string;
  parameter: string;
  status: string;
  runs: {
    iteration: number;
    value: number;
    job_id: string;
    status: string;
    inp_path: string;
  }[];
}

export interface CopilotAction {
  action_type: string;
  parameters: Record<string, unknown>;
  description: string;
}

export interface CopilotActionResult {
  job_id?: string;
  experiment_id?: string;
  message?: string;
}

export interface OperatorStatusItem {
  label: string;
  value: string;
  tone?: 'accent' | 'warning' | 'muted' | 'danger';
  detail?: string;
}

export interface OperatorStatusSection {
  title: string;
  icon: ReactNode;
  items: OperatorStatusItem[];
}

export interface GoldenSampleQueueItem {
  caseId: string;
  name: string;
  status: string;
  reason: string;
  failurePatternRef: string;
  tone: OperatorStatusItem['tone'];
}

export type JobStatus =
  | 'idle'
  | 'starting'
  | 'running'
  | 'stop_requested'
  | 'completed'
  | 'failed'
  | 'stopped'
  | 'connection_lost';
