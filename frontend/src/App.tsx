import { useState, useEffect, useRef, type ChangeEvent, type ReactNode } from 'react';
import { 
  FileUp, 
  Activity, 
  ChevronRight,
  Zap,
  Box,
  LayoutDashboard,
  Play,
  Loader2,
  Compass,
  ArrowRightLeft,
  BookOpen,
  MessageSquare,
  Download,
  ShieldAlert,
  Database,
  ClipboardCheck,
  AlertTriangle
} from 'lucide-react';
import './App.css';
import { SensitivityForm } from './components/SensitivityForm';
import { ComplianceBadge } from './components/ComplianceBadge';
import { ChatPanel, type CaeReviewCard } from './components/ChatPanel';
import { ProjectManager } from './components/ProjectManager';
import { ModeSelector } from './components/ModeSelector';
import { ResultMeshPlaybackPanel } from './components/ResultMeshPlaybackPanel';
import { BulletPlateBlueprintPanel } from './components/BulletPlateBlueprintPanel';
import { buildBulletPlateBlueprintSummary } from './bulletPlateBlueprint';
import { CandidateCasePicker } from './components/CandidateCasePicker';
import { AcceptancePacketPanel } from './components/AcceptancePacketPanel';
import { CaseComparisonPanel } from './components/CaseComparisonPanel';
import { ConvergenceStudyViewer } from './components/ConvergenceStudyViewer';
import { CohortDashboardPanel } from './components/CohortDashboardPanel';
import { CohortSubstantiationPanel } from './components/CohortSubstantiationPanel';
import { CaseCompletenessCard } from './components/CaseCompletenessCard';
import { ReviewerBundlePanel } from './components/ReviewerBundlePanel';
import { ArchivedPacketDiffPanel } from './components/ArchivedPacketDiffPanel';
import { CohortSnapshotPanel } from './components/CohortSnapshotPanel';
import { ReproducibilityManifestCard } from './components/ReproducibilityManifestCard';
import { TrustScoreGauge } from './components/TrustScoreGauge';
import { DriftNarrativePanel } from './components/DriftNarrativePanel';
import { TrustScoreTimelineChart } from './components/TrustScoreTimelineChart';
import { SignoffHistoryPanel } from './components/SignoffHistoryPanel';
import { CohortExecutiveSummaryPanel } from './components/CohortExecutiveSummaryPanel';
import { CohortAnomaliesPanel } from './components/CohortAnomaliesPanel';
import { CohortTrendAnomaliesPanel } from './components/CohortTrendAnomaliesPanel';
import { ProvenancePanel } from './components/ProvenancePanel';
// FM-04a Phase 11 E — AI advisor critique panel; mounted adjacent to
// ProvenancePanel below. The advisor surface is read-only / advisor-only
// per the project four-question gate.
import { AdvisorPanel } from './components/AdvisorPanel';
// FM-04a Phase 18 D/E — Tier 2 workbench primitives (round 2 integration).
import { CommandPalette } from './components/CommandPalette';
import { MaterialPickerPanel } from './components/MaterialPickerPanel';
import { useKeyboardShortcuts } from './hooks/useKeyboardShortcuts';
import {
  type Command,
  type CommandCategory,
} from './commands/registry';
import { FALLBACK_MATERIALS, type MaterialRecord } from './materialsClient';
import type { SignoffRecord } from './signoffHistoryClient';
import { FALLBACK_CANDIDATE_CASES, findCandidateCase } from './candidateCaseRegistry';
import {
    TIER1_BANNER,
    candidateCaseSelectionLabel,
    candidateCaseSelectionTone,
    convergenceLabel,
    convergenceTone,
    energyBalanceLabel,
    energyBalanceTone,
} from './trustCenterSummary';
import type {
    CandidateCaseSelectionSummary,
    ConvergenceStudySummary,
    EnergyBalanceSummary,
} from './trustCenterSummary';


// --- Types ---
interface CaseMetadata {
  id: string;
  name: string;
  description: string;
  type: string;
  structure: string;
  frd_path: string;
}

interface CaseReferenceDetails {
  case_id?: string;
  case_name?: string;
  status?: string;
  status_reason?: string;
  failure_pattern_ref?: string;
  metadata?: Record<string, unknown>;
}

interface ReportData {
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

interface CandidateArtifact {
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

interface CandidateMeshEvidence {
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

interface CandidateMeshConvergenceStudy {
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

interface CandidateConvergenceEvidence {
  status: string;
  claim_impact: string;
  normal_termination: string;
  latest_job_status?: string | null;
  source_artifacts: CandidateArtifact[];
  mesh_refinement_study?: CandidateMeshConvergenceStudy;
  signals: string[];
  missing_reasons: string[];
}

interface CandidateBallisticEvidence {
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

interface CandidateReportSpine {
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

interface ExperimentStatus {
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

interface CopilotAction {
  action_type: string;
  parameters: Record<string, unknown>;
  description: string;
}

interface CopilotActionResult {
  job_id?: string;
  experiment_id?: string;
  message?: string;
}

interface OperatorStatusItem {
  label: string;
  value: string;
  tone?: 'accent' | 'warning' | 'muted' | 'danger';
  detail?: string;
}

interface OperatorStatusSection {
  title: string;
  icon: ReactNode;
  items: OperatorStatusItem[];
}

interface GoldenSampleQueueItem {
  caseId: string;
  name: string;
  status: string;
  reason: string;
  failurePatternRef: string;
  tone: OperatorStatusItem['tone'];
}

type JobStatus = 'idle' | 'starting' | 'running' | 'stop_requested' | 'completed' | 'failed' | 'stopped' | 'connection_lost';

const API_BASE = "http://localhost:8000/api/v1";
const WS_BASE = "ws://localhost:8000/api/v1";

const SOLVER_FAILURE_MARKERS = [
  'System Error:',
  'Solver exited with code:',
  'Error: Job not found',
  'Socket Error:',
];

const isSolverFailureLog = (message: string) =>
  SOLVER_FAILURE_MARKERS.some(marker => message.includes(marker));

const humanizeStatus = (status?: string) => {
  if (!status) return 'Unknown';
  return status
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
};

const statusTone = (status?: string): OperatorStatusItem['tone'] => {
  if (!status) return 'muted';
  if (['pass', 'passed', 'completed', 'accept'].includes(status.toLowerCase())) return 'accent';
  if (['fail', 'failed', 'critical', 'rejected'].includes(status.toLowerCase())) return 'danger';
  return 'warning';
};

const compactText = (value?: string, fallback = 'No backend detail surfaced') =>
  value && value.trim().length > 0 ? value : fallback;

const compactJson = (value: unknown, fallback = 'Unavailable') => {
  if (value === undefined || value === null) return fallback;
  if (typeof value === 'string') return value;
  if (typeof value === 'object' && Object.keys(value as Record<string, unknown>).length === 0) return fallback;
  try {
    return JSON.stringify(value);
  } catch {
    return fallback;
  }
};

function App() {
  const [file, setFile] = useState<File | null>(null);
  const [activeCaseId, setActiveCaseId] = useState<string | null>(null);
  // FM-04a Phase 2 C — Tier 1 candidate-case picker selection (parallel to
  // backend DB case selection; drives blueprint label + trust-center cards).
  const [selectedCandidateCaseId, setSelectedCandidateCaseId] = useState<string | null>(() => {
    if (typeof window === 'undefined') return FALLBACK_CANDIDATE_CASES[0]?.caseId ?? null;
    try {
      return window.localStorage.getItem('fm04a.candidateCaseId') ?? (FALLBACK_CANDIDATE_CASES[0]?.caseId ?? null);
    } catch {
      return FALLBACK_CANDIDATE_CASES[0]?.caseId ?? null;
    }
  });
  // FM-04a Phase 3 C — Case-vs-case comparison pair selection.
  const [comparisonCaseA, setComparisonCaseA] = useState<string | null>(() => {
    if (typeof window === 'undefined') return FALLBACK_CANDIDATE_CASES[0]?.caseId ?? null;
    try {
      return window.localStorage.getItem('fm04a.comparisonCaseA') ?? (FALLBACK_CANDIDATE_CASES[0]?.caseId ?? null);
    } catch {
      return FALLBACK_CANDIDATE_CASES[0]?.caseId ?? null;
    }
  });
  const [comparisonCaseB, setComparisonCaseB] = useState<string | null>(() => {
    if (typeof window === 'undefined') return FALLBACK_CANDIDATE_CASES[1]?.caseId ?? null;
    try {
      return window.localStorage.getItem('fm04a.comparisonCaseB') ?? (FALLBACK_CANDIDATE_CASES[1]?.caseId ?? null);
    } catch {
      return FALLBACK_CANDIDATE_CASES[1]?.caseId ?? null;
    }
  });
  // FM-04a Phase 6 E — lifted snapshot label selection so DriftNarrativePanel
  // can read the same labels the CohortSnapshotPanel picks.
  const [snapshotLabelA, setSnapshotLabelA] = useState<string | null>(null);
  const [snapshotLabelB, setSnapshotLabelB] = useState<string | null>(null);
  const [latestSignoff, setLatestSignoff] = useState<SignoffRecord | null>(null);
  const [loading, setLoading] = useState(false);
  const [report, setReport] = useState<ReportData | null>(null);
  const [activeTab, setActiveTab] = useState<'visual' | 'report' | 'explore'>('visual');
  // FM-04a Phase 18 D/E — Cmd-K palette + selected material (round 2).
  const [paletteOpen, setPaletteOpen] = useState(false);
  const [selectedMaterial, setSelectedMaterial] = useState<MaterialRecord>(
    FALLBACK_MATERIALS[0],
  );
  const [availableCases, setAvailableCases] = useState<CaseMetadata[]>([]);
  const [caseDetailsById, setCaseDetailsById] = useState<Record<string, CaseReferenceDetails>>({});
  const [selectedProjectId, setSelectedProjectId] = useState<number | null>(null);
  const [analysisType, setAnalysisType] = useState<'static' | 'modal' | 'buckling'>('static');
  const [selectedModeIndex, setSelectedModeIndex] = useState(0);
  
  // Solver & Explorer State
  const [solving, setSolving] = useState(false);
  const [logs, setLogs] = useState<string[]>([]);
  const [showConsole, setShowConsole] = useState(false);
  const [showChat, setShowChat] = useState(false);
  const [currentJobId, setCurrentJobId] = useState<string | null>(null);
  const [currentJobStatus, setCurrentJobStatus] = useState<JobStatus>('idle');
  const [currentJobAnalysis, setCurrentJobAnalysis] = useState<'static' | 'modal' | 'buckling'>('static');
  const [activeExperiment, setActiveExperiment] = useState<ExperimentStatus | null>(null);
  const [comparedIndices, setComparedIndices] = useState<[number, number] | null>(null);
  const terminalEndRef = useRef<HTMLDivElement>(null);

  // Fetch available cases when project changes
  useEffect(() => {
    const url = selectedProjectId 
      ? `${API_BASE}/cases?project_id=${selectedProjectId}` 
      : `${API_BASE}/cases`;
      
    fetch(url)
      .then(res => res.json())
      .then(data => setAvailableCases(data))
      .catch(err => console.error("Failed to fetch cases", err));
  }, [selectedProjectId]);

  useEffect(() => {
    let cancelled = false;

    if (availableCases.length === 0) {
      setCaseDetailsById({});
      return;
    }

    Promise.all(
      availableCases.map(async (c) => {
        try {
          const res = await fetch(`${API_BASE}/cases/${encodeURIComponent(c.id)}`);
          if (!res.ok) return [c.id, {}] as const;
          const details = await res.json() as CaseReferenceDetails;
          return [c.id, details] as const;
        } catch (err) {
          console.error(`Failed to fetch case details for ${c.id}`, err);
          return [c.id, {}] as const;
        }
      })
    ).then((entries) => {
      if (!cancelled) {
        setCaseDetailsById(Object.fromEntries(entries));
      }
    });

    return () => {
      cancelled = true;
    };
  }, [availableCases]);

  // Auto-scroll terminal
  useEffect(() => {
    terminalEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [logs]);

  const clearJobContext = () => {
    setSolving(false);
    setLogs([]);
    setShowConsole(false);
    setCurrentJobId(null);
    setCurrentJobStatus('idle');
    setCurrentJobAnalysis(analysisType);
  };

  const handleFileUpload = async (e: ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const selectedFile = e.target.files[0];
      setFile(selectedFile);
      setActiveCaseId(null);
      clearJobContext();
      await generateReportFromFile(selectedFile);
    }
  };

  const generateReportFromFile = async (f: File, caseId?: string) => {
    setLoading(true);
    const formData = new FormData();
    formData.append('file', f);
    
    if (caseId) {
      formData.append('case_id', caseId);
    } else {
        const matchedCase = availableCases.find(c => f.name.toLowerCase().includes(c.id.toLowerCase().replace("-","")));
        if (matchedCase) formData.append('case_id', matchedCase.id);
    }

    try {
      const response = await fetch(`${API_BASE}/report/generate`, {
        method: 'POST',
        body: formData,
      });
      const data = await response.json();
      if (data.success) {
        setReport(data);
      }
    } catch (err) {
      console.error("Upload failed", err);
    } finally {
      setLoading(false);
    }
  };

  const selectCase = async (c: CaseMetadata, options: { preserveJob?: boolean } = {}) => {
    setLoading(true);
    setFile(null);
    setActiveCaseId(c.id);
    setActiveExperiment(null);
    setComparedIndices(null);
    if (!options.preserveJob) {
      clearJobContext();
    }
    
    const formData = new FormData();
    formData.append('case_id', c.id);
    formData.append('file', new File(["dummy"], "dummy.frd"));

    try {
      const response = await fetch(`${API_BASE}/report/generate`, {
        method: 'POST',
        body: formData,
      });
      const data = await response.json();
      if (data.success) {
        setReport(data);
      }
    } catch (err) {
      console.error("Case selection failed", err);
    } finally {
      setLoading(false);
    }
  };

  const runSolver = async () => {
    if (!activeCaseId) return;
    setSolving(true);
    setLogs([]);
    setShowConsole(true);
    setCurrentJobId(null);
    setCurrentJobStatus('starting');
    setCurrentJobAnalysis(analysisType);
    
    try {
      const response = await fetch(`${API_BASE}/solver/run`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          case_id: activeCaseId,
          analysis_type: analysisType,
          num_modes: 5,
          // Phase 18 E (round 3 honesty fix) — propagate the reviewer's
          // material pick into the solver request body. Backend
          // `RunRequest` now declares this field (post round-3 FEA agent
          // disclosure: pre-fix the backend silently dropped it). The
          // field is RECEIVED but NOT yet plumbed into the solver
          // pipeline — Phase 19 priority-0.5 item closes the back-half.
          // Until then the picker is a UI affordance with a wire-level
          // contract, not an end-to-end material-swap-and-re-solve flow.
          material_id: selectedMaterial.id,
        }),
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) {
        const detail = typeof data.detail === 'string' ? data.detail : `HTTP ${response.status}`;
        setLogs(prev => [...prev, `[ERROR] Solver start failed: ${detail}`]);
        setCurrentJobStatus('failed');
        setSolving(false);
        return;
      }
      if (data.job_id) {
        setCurrentJobId(data.job_id);
        setCurrentJobStatus('running');
        connectToLogs(data.job_id);
      } else {
        setLogs(prev => [...prev, "[ERROR] Solver start failed: missing job id"]);
        setCurrentJobStatus('failed');
        setSolving(false);
      }
    } catch (err) {
      console.error("Solver start failed", err);
      setCurrentJobStatus('failed');
      setSolving(false);
    }
  };

  const downloadPDFReport = async () => {
    if (!activeCaseId) return;
    try {
      setLoading(true);
      const response = await fetch(`${API_BASE}/report/export/pdf/${activeCaseId}`);
      if (!response.ok) throw new Error("PDF generation failed");
      
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `Report_${activeCaseId}.pdf`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      console.error("Export failed", err);
      alert("Failed to export PDF: " + err);
    } finally {
      setLoading(false);
    }
  };

  const stopSolver = async () => {
    if (!currentJobId) return;
    
    setLogs(prev => [...prev, "[SYSTEM] Requesting stop..."]);
    setCurrentJobStatus('stop_requested');
    
    try {
      const response = await fetch(`${API_BASE}/solver/stop/${currentJobId}`, { method: 'POST' });
      if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        const detail = typeof data.detail === 'string' ? `: ${data.detail}` : '';
        setLogs(prev => [...prev, `[SYSTEM] Stop request failed${detail}`]);
        setCurrentJobStatus('failed');
        setSolving(false);
        return;
      }
      setLogs(prev => [...prev, "[SYSTEM] Stop request accepted."]);
      setCurrentJobStatus('stopped');
      setSolving(false);
    } catch (err) {
      console.error("Stop failed", err);
      setLogs(prev => [...prev, "[SYSTEM] Stop request failed"]);
      setCurrentJobStatus('failed');
      setSolving(false);
    }
  };

  const connectToLogs = (jobId: string) => {
    const ws = new WebSocket(`${WS_BASE}/solver/ws/logs/${jobId}`);
    ws.onmessage = (event) => {
      const message = event.data;
      setLogs(prev => [...prev, message]);
      if (isSolverFailureLog(message)) {
        setSolving(false);
        setCurrentJobStatus('failed');
        return;
      }
      if (message.includes("[SYSTEM] Job terminated")) {
        setSolving(false);
        setCurrentJobStatus('stopped');
        return;
      }
      if (message.includes("--- Process Finished")) {
        setSolving(false);
        setCurrentJobStatus(message.includes("status: COMPLETED") ? 'completed' : 'failed');
        if (message.includes("status: COMPLETED")) {
            setTimeout(() => {
                if (activeCaseId) {
                   const matchedCase = availableCases.find(c => c.id === activeCaseId);
                   if (matchedCase) selectCase(matchedCase, { preserveJob: true });
                }
            }, 1000);
        }
      }
    };
    ws.onerror = () => {
      setLogs(prev => [...prev, "[ERROR] WebSocket connection died"]);
      setCurrentJobStatus('connection_lost');
      setSolving(false);
    };
  };

  const handleRunStudy = async (param: string, values: number[]) => {
    if (!activeCaseId) return;
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/sensitivity/run`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ case_id: activeCaseId, parameter: param, values: values })
      });
      const data = await res.json();
      if (data.experiment_id) {
        pollExperiment(data.experiment_id);
      }
    } catch (err) {
      console.error("Study failed", err);
      setLoading(false);
    }
  };

  const pollExperiment = async (id: string) => {
    const interval = setInterval(async () => {
        const res = await fetch(`${API_BASE}/sensitivity/status/${id}`);
        const data = await res.json();
        setActiveExperiment(data);
        if (data.status === 'COMPLETED') {
            clearInterval(interval);
            setLoading(false);
            setActiveTab('visual'); 
        }
    }, 2000);
  };

  const handleExecuteCopilotAction = async (action: CopilotAction): Promise<CopilotActionResult> => {
    try {
      const res = await fetch(`${API_BASE}/execute`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: action, context: { case_id: activeCaseId } })
      });
      const data = await res.json() as CopilotActionResult;
      
      if (data.job_id) {
          setCurrentJobId(data.job_id);
          setCurrentJobStatus('running');
          setCurrentJobAnalysis(analysisType);
          setShowConsole(true);
          setSolving(true);
          connectToLogs(data.job_id);
      } else if (data.experiment_id) {
          pollExperiment(data.experiment_id);
      }
      
      return data;
    } catch (err) {
      console.error("Copilot action execution failed", err);
      throw err;
    }
  };

  const activeCase = activeCaseId ? availableCases.find(c => c.id === activeCaseId) : null;
  const activeCaseDetails = activeCaseId ? caseDetailsById[activeCaseId] : undefined;
  const caseLabel = activeCase
    ? `${activeCase.id} / ${activeCase.name}`
    : file
      ? `Uploaded FRD / ${file.name}`
      : 'No active case';
  const jobStatusLabel = currentJobStatus.replace('_', ' ');
  const analysisModeLabel = `${currentJobAnalysis} analysis`;
  const currentJobLabel = currentJobId ? `${currentJobId} / ${jobStatusLabel}` : 'No solver job started';
  const runState = currentJobId
    ? `${analysisModeLabel} / ${jobStatusLabel}`
    : solving
    ? `Running ${analysisType} solver`
    : activeExperiment
      ? `Study ${activeExperiment.status}`
      : loading
        ? 'Preparing report/status'
        : report
          ? 'Report loaded'
          : 'Idle';
  const referenceStatusRaw = activeCaseDetails?.status;
  const referenceStatus = activeCaseId
    ? humanizeStatus(referenceStatusRaw)
    : 'No golden-sample reference selected';
  const referenceReason = compactText(
    activeCaseDetails?.status_reason,
    activeCaseId ? 'Expected-results status is still loading or unavailable' : 'Select GS-001/002/003 to load expected_results.json'
  );
  const failurePatternRef = activeCaseDetails?.failure_pattern_ref ?? 'No FailurePattern reference surfaced';
  const reportValidationStatus = report?.validation.status ? humanizeStatus(report.validation.status) : 'No report validation yet';
  const referenceDeviation = typeof report?.validation.error_percentage === 'number'
    ? `${report.validation.error_percentage}%`
    : 'No report-side delta available';
  const candidateSpine = report?.candidate_report_spine;
  const candidateManifest = candidateSpine?.artifact_manifest;
  const solverLogState = candidateSpine?.solver.logs;
  const candidateReviewer = candidateSpine?.reviewer_summary;
  const candidateAssumptions = candidateSpine?.assumptions;
  const candidateMeshEvidence = candidateSpine?.mesh_evidence;
  const candidateConvergenceEvidence = candidateSpine?.convergence_evidence;
  const candidateLimitations = candidateSpine?.limitations ?? [];
  const candidateTier2Blockers = candidateSpine?.tier2_blockers ?? [];
  const candidateBallistic = candidateSpine?.ballistic;
  const claimTier = candidateSpine?.claim_tier ?? 'Tier 0 sandbox/demo';
  const solverTruthSource = candidateSpine
    ? candidateSpine.provenance.solver_truth_source
    : currentJobId
    ? 'CalculiX solver job requested through /solver/run'
    : report
      ? 'Backend report artifact; fresh solver truth not proven in this session'
      : 'Unknown until a report or solver job exists';
  const executionMode = currentJobId
    ? 'fresh solver job requested'
    : file
      ? 'uploaded FRD artifact review'
      : report
        ? 'report-only artifact review'
        : 'not started';
  const manifestState = candidateManifest
    ? `${candidateManifest.hash_count} ${candidateManifest.hash_algorithm} artifacts / ${candidateManifest.manifest_id}`
    : currentJobId
    ? 'Job console stream exists; manifest/hash is not surfaced in this UI slice'
    : activeCaseId
      ? 'expected_results.json reference loaded through /cases/:id'
      : 'No artifact manifest loaded';
  const allowedClaim = candidateSpine
    ? `${candidateSpine.allowed_claim}; ${candidateSpine.no_overclaim}`
    : currentJobStatus === 'completed' && report
      ? 'demo-only software-path evidence; Tier 1 remains blocked until FM-03 manifest, hashes, solver logs, and limitations are attached'
      : 'demo-only / software-path evidence only; not signed validation';
  const evidenceState = candidateSpine
    ? `${candidateSpine.schema_version}; ${candidateSpine.no_overclaim}`
    : currentJobId && logs.length > 0
    ? `Job console stream for ${currentJobId}; not signed validation`
    : currentJobId
      ? `Job id received from /solver/run; not signed validation`
      : report
    ? `Software-path report ${report.metrics.status}; not signed validation`
    : logs.length > 0
      ? 'Solver log stream only; not signed validation'
      : 'No run evidence yet';
  const latestEvent = logs.length > 0 ? logs[logs.length - 1].slice(0, 96) : 'No runtime log event';
  const backendProvenance = candidateSpine
    ? `${candidateSpine.provenance.parser}; ${candidateSpine.provenance.node_count} nodes / ${candidateSpine.provenance.element_count} elements / ${candidateSpine.provenance.increment_count} increments`
    : currentJobId
    ? `Existing /solver/run CalculiX path, job ${currentJobId}; software-path evidence only`
    : 'AERON L0 / CalculiX path awaits a solver job response';
  const solverLogSummary = solverLogState
    ? `${solverLogState.status}; ${solverLogState.artifact_paths.length} log artifact(s)`
    : 'No solver logs surfaced';
  const materialSummary = candidateAssumptions
    ? `${candidateAssumptions.material.status}: ${compactJson(candidateAssumptions.material.value, candidateAssumptions.material.unavailable_reason)}`
    : 'No material provenance surfaced';
  const boundarySummary = candidateAssumptions
    ? `${candidateAssumptions.boundary_conditions.status}: ${compactJson(candidateAssumptions.boundary_conditions.value, candidateAssumptions.boundary_conditions.unavailable_reason)}`
    : 'No boundary-condition provenance surfaced';
  const unitSummary = candidateAssumptions
    ? `${candidateAssumptions.unit_system.stress_unit}; ${candidateAssumptions.unit_system.length_unit}`
    : 'No unit assumptions surfaced';
  const reviewerSummary = candidateReviewer
    ? `${humanizeStatus(candidateReviewer.verdict)}; ${candidateReviewer.blocked_findings.length} blocker(s)`
    : 'Pending until reviewer verdict is attached';
  const tier2BlockerSummary = candidateTier2Blockers.length > 0
    ? candidateTier2Blockers.join('; ')
    : 'Benchmark, convergence, and signoff requirements are not attached';
  const meshDeckElementTypes = candidateMeshEvidence?.input_deck.element_types
    ? Object.entries(candidateMeshEvidence.input_deck.element_types).map(([name, count]) => `${name}:${count}`).join(', ')
    : 'No element type inventory';
  const meshTopologySummary = candidateMeshEvidence
    ? `FRD ${candidateMeshEvidence.result_mesh.node_count} nodes / ${candidateMeshEvidence.result_mesh.element_count} elements; deck ${candidateMeshEvidence.input_deck.node_count ?? 'unknown'} nodes / ${candidateMeshEvidence.input_deck.element_count ?? 'unknown'} elements`
    : 'No mesh evidence surfaced';
  const meshArtifactSource = candidateMeshEvidence
    ? [
        candidateMeshEvidence.input_deck.path ? `deck ${candidateMeshEvidence.input_deck.path}` : candidateMeshEvidence.input_deck.unavailable_reason,
        candidateMeshEvidence.metadata.source ? `mesh_meta ${candidateMeshEvidence.metadata.source}` : candidateMeshEvidence.metadata.unavailable_reason,
      ].filter(Boolean).join('; ')
    : 'No mesh artifact source surfaced';
  const meshQualitySummary = candidateMeshEvidence
    ? `${humanizeStatus(candidateMeshEvidence.quality.status)}; ${compactJson(candidateMeshEvidence.quality.metrics, candidateMeshEvidence.quality.unavailable_reason)}`
    : 'Mesh quality evidence is not surfaced';
  const meshClaimImpact = candidateMeshEvidence?.claim_impact ?? 'Tier 2 blocked until mesh evidence and reviewer signoff are attached';
  const meshConvergenceStudy = candidateMeshEvidence?.convergence_study ?? candidateConvergenceEvidence?.mesh_refinement_study;
  const meshConvergenceStudySummary = meshConvergenceStudy
    ? meshConvergenceStudy.status === 'available'
      ? `${humanizeStatus(meshConvergenceStudy.study_status ?? meshConvergenceStudy.status)}; ${meshConvergenceStudy.run_count ?? 0} ${meshConvergenceStudy.parameter ?? 'mesh'} run(s); ${meshConvergenceStudy.metric ?? 'metric'} delta ${meshConvergenceStudy.relative_change_pct ?? 'unknown'}%`
      : `${humanizeStatus(meshConvergenceStudy.status)}; ${meshConvergenceStudy.unavailable_reason ?? 'mesh refinement study is not attached'}`
    : 'Mesh refinement convergence study is not surfaced';
  const meshConvergenceStudySource = meshConvergenceStudy?.source ?? 'No mesh convergence artifact source surfaced';
  const meshConvergenceClaimImpact = meshConvergenceStudy?.claim_impact ?? 'Tier 2 blocked until a mesh-refinement convergence study, benchmark, and signoff are attached';
  const convergenceArtifactList = candidateConvergenceEvidence?.source_artifacts.length
    ? candidateConvergenceEvidence.source_artifacts.map((item) => `${item.kind}:${item.path}`).join('; ')
    : 'No solver convergence/status artifact surfaced';
  const convergenceSummary = candidateConvergenceEvidence
    ? `${humanizeStatus(candidateConvergenceEvidence.status)}; normal termination ${candidateConvergenceEvidence.normal_termination}; ${candidateConvergenceEvidence.source_artifacts.length} artifact(s)`
    : 'No convergence evidence surfaced';
  const convergenceMissingSummary = candidateConvergenceEvidence?.missing_reasons.length
    ? candidateConvergenceEvidence.missing_reasons.join('; ')
    : 'No current convergence gaps surfaced; Tier 2 still requires benchmark and signoff';
  const convergenceClaimImpact = candidateConvergenceEvidence?.claim_impact ?? 'Tier 2 blocked until convergence study and signoff are attached';
  const ballisticInitialVelocityValue = candidateBallistic?.projectile_initial_velocity.value_m_per_s;
  const ballisticInitialVelocitySummary = candidateBallistic
    ? candidateBallistic.projectile_initial_velocity.status === 'declared' && typeof ballisticInitialVelocityValue === 'number'
      ? `${ballisticInitialVelocityValue.toFixed(1)} m/s (${candidateBallistic.projectile_initial_velocity.source ?? 'source unknown'})`
      : candidateBallistic.projectile_initial_velocity.unavailable_reason ?? 'Initial velocity is unavailable'
    : 'Ballistic block is not present in the report payload';
  const ballisticResidualVelocityValue = candidateBallistic?.residual_velocity_candidate.value_m_per_s;
  const ballisticResidualVelocitySummary = candidateBallistic
    ? candidateBallistic.residual_velocity_candidate.status === 'candidate_observed' && typeof ballisticResidualVelocityValue === 'number'
      ? `${ballisticResidualVelocityValue.toFixed(1)} m/s (Tier 1 candidate; not benchmark agreement)`
      : candidateBallistic.residual_velocity_candidate.unavailable_reason ?? 'Residual velocity is unavailable'
    : 'No ballistic residual velocity surfaced';
  const ballisticPerforationMarker = candidateBallistic?.perforation_marker.status ?? 'unknown';
  const ballisticPerforationSummary = candidateBallistic
    ? `${humanizeStatus(ballisticPerforationMarker)}${ballisticPerforationMarker === 'unknown' && candidateBallistic.perforation_marker.unavailable_reason ? `; ${candidateBallistic.perforation_marker.unavailable_reason}` : ''}`
    : 'No perforation marker surfaced';
  const ballisticEnergyRatio = candidateBallistic?.energy_balance_candidate.energy_ratio ?? null;
  const ballisticEnergySummary = candidateBallistic
    ? candidateBallistic.energy_balance_candidate.status === 'available'
      ? `Initial KE ${candidateBallistic.energy_balance_candidate.initial_kinetic_energy_j ?? '?'} J; ratio ${typeof ballisticEnergyRatio === 'number' ? ballisticEnergyRatio.toFixed(3) : 'unknown'} (Tier 1 health indicator)`
      : candidateBallistic.energy_balance_candidate.unavailable_reason ?? 'Energy balance is unavailable'
    : 'No energy balance surfaced';
  const ballisticEnergyTone: OperatorStatusItem['tone'] = candidateBallistic && candidateBallistic.energy_balance_candidate.status === 'available'
    ? typeof ballisticEnergyRatio === 'number' && (ballisticEnergyRatio < 0.95 || ballisticEnergyRatio > 1.05)
      ? 'warning'
      : 'accent'
    : 'muted';
  const ballisticPerforationTone: OperatorStatusItem['tone'] = ballisticPerforationMarker === 'perforated_candidate' || ballisticPerforationMarker === 'embedded_candidate'
    ? 'warning'
    : ballisticPerforationMarker === 'stopped_candidate'
      ? 'accent'
      : 'muted';
  const ballisticTimeStepStudy = candidateBallistic?.time_step_convergence_study;
  const ballisticTimeStepStudySummary = ballisticTimeStepStudy
    ? ballisticTimeStepStudy.status === 'available'
      ? `${humanizeStatus(ballisticTimeStepStudy.candidate_stability ?? ballisticTimeStepStudy.study_status ?? 'available')}; ${ballisticTimeStepStudy.run_count ?? 0} dt run(s); Δ ${typeof ballisticTimeStepStudy.relative_change_pct === 'number' ? ballisticTimeStepStudy.relative_change_pct : 'unknown'}% vs ${typeof ballisticTimeStepStudy.tolerance_pct === 'number' ? ballisticTimeStepStudy.tolerance_pct : 'unknown'}% tol`
      : ballisticTimeStepStudy.unavailable_reason ?? 'Time-step convergence study is not attached'
    : 'No time-step convergence study surfaced';
  const ballisticTimeStepStudyTone: OperatorStatusItem['tone'] = ballisticTimeStepStudy?.status === 'available'
    ? ballisticTimeStepStudy.candidate_stability === 'candidate_observed_unstable'
      ? 'warning'
      : 'accent'
    : 'muted';
  const ballisticTier2BlockerSummary = candidateBallistic && candidateBallistic.tier2_blockers_ballistic.length > 0
    ? candidateBallistic.tier2_blockers_ballistic.join('; ')
    : 'Ballistic Tier 2 blockers are not surfaced (no ballistic block).';
  const ballisticAnimationSummary = candidateBallistic
    ? candidateBallistic.animation_manifest.status === 'available'
      ? `${candidateBallistic.animation_manifest.path ?? 'animation_manifest.json'} (sha256 ${candidateBallistic.animation_manifest.sha256?.slice(0, 12) ?? '...'})`
      : candidateBallistic.animation_manifest.unavailable_reason ?? 'Animation manifest is unavailable'
    : 'No animation manifest surfaced';
  const blueprintSummary = buildBulletPlateBlueprintSummary();

  // FM-04a Phase 2 D — Trust Center industrial review card summaries.
  const phase2EnergyBalanceSummary: EnergyBalanceSummary = candidateBallistic
    ? {
        status:
          candidateBallistic.energy_balance_candidate.status === 'available'
            ? 'partial_candidate'
            : 'unavailable',
        initialKineticEnergyJ:
          candidateBallistic.energy_balance_candidate.initial_kinetic_energy_j ?? null,
        residualKineticEnergyJ:
          candidateBallistic.energy_balance_candidate.residual_kinetic_energy_j ?? null,
        aggregateInternalEnergyJ: null,
        externalWorkJ: null,
        energyBalanceErrorPct: null,
        claimImpact:
          candidateBallistic.energy_balance_candidate.unavailable_reason ??
          'Tier 1 partial energy audit: kinetic energies only; aggregate ' +
            'internal energy and external work require the engine .out energy ' +
            'table (FM-04a Phase 2 A); not signed validation; not benchmark agreement.',
      }
    : {
        status: 'unavailable',
        initialKineticEnergyJ: null,
        residualKineticEnergyJ: null,
        aggregateInternalEnergyJ: null,
        externalWorkJ: null,
        energyBalanceErrorPct: null,
        claimImpact: 'Energy audit unavailable: no candidate ballistic spine in scope',
      };
  const phase2EnergyBalanceTone = energyBalanceTone(phase2EnergyBalanceSummary);
  const phase2EnergyBalanceLabel = energyBalanceLabel(phase2EnergyBalanceSummary);

  const phase2ConvergenceSummary: ConvergenceStudySummary = ballisticTimeStepStudy && ballisticTimeStepStudy.status === 'available'
    ? {
        combinedVerdict:
          ballisticTimeStepStudy.candidate_stability ?? 'insufficient_data',
        meshSweepStability: 'unknown',
        dtSweepStability: ballisticTimeStepStudy.candidate_stability ?? 'unknown',
        rowCount: ballisticTimeStepStudy.run_count ?? 0,
        tolerancePct:
          typeof ballisticTimeStepStudy.tolerance_pct === 'number'
            ? ballisticTimeStepStudy.tolerance_pct
            : 5,
      }
    : {
        combinedVerdict: 'insufficient_data',
        meshSweepStability: 'unknown',
        dtSweepStability: 'unknown',
        rowCount: 0,
        tolerancePct: 5,
      };
  const phase2ConvergenceTone = convergenceTone(phase2ConvergenceSummary);
  const phase2ConvergenceLabel = convergenceLabel(phase2ConvergenceSummary);

  const phase2CandidateCase = findCandidateCase(
    FALLBACK_CANDIDATE_CASES,
    selectedCandidateCaseId,
  );
  const phase2CandidateCaseSummary: CandidateCaseSelectionSummary = {
    caseId: phase2CandidateCase?.caseId ?? null,
    starterDeckRelpath: phase2CandidateCase?.starterDeckRelpath ?? null,
    engineDeckRelpath: phase2CandidateCase?.engineDeckRelpath ?? null,
    generatorScriptRelpath: phase2CandidateCase?.generatorScriptRelpath ?? null,
    // Best-effort: the picker fetch resolves live vs fallback at runtime; for
    // the Trust Center card we expose the static-list source unless a refined
    // live-source flag is plumbed through.
    source: 'fallback',
  };
  const phase2CandidateCaseTone = candidateCaseSelectionTone(
    phase2CandidateCaseSummary,
  );
  const phase2CandidateCaseLabel = candidateCaseSelectionLabel(
    phase2CandidateCaseSummary,
  );
  const goldenSampleQueue: GoldenSampleQueueItem[] = availableCases
    .filter((c) => c.id.startsWith('GS-'))
    .map((c) => {
      const details = caseDetailsById[c.id];
      const status = humanizeStatus(details?.status);
      const tone = statusTone(details?.status);
      return {
        caseId: c.id,
        name: c.name,
        status,
        reason: compactText(details?.status_reason, 'expected_results.json status not loaded yet'),
        failurePatternRef: details?.failure_pattern_ref ?? 'No FailurePattern reference surfaced',
        tone,
      };
    });
  const goldenSampleReviewCount = goldenSampleQueue.filter((item) => item.tone !== 'accent').length;
  const goldenSampleSummary = goldenSampleQueue.length > 0
    ? `${goldenSampleReviewCount}/${goldenSampleQueue.length} need review or evidence`
    : 'No golden samples loaded';
  const runStateTone = solving || activeExperiment
    ? 'accent'
    : currentJobStatus === 'failed' || currentJobStatus === 'connection_lost'
      ? 'warning'
      : 'muted';
  const nextAction = solving
    ? 'Watch the solver console or stop the job; do not promote evidence'
    : loading
      ? 'Wait for report generation to finish'
      : !activeCaseId && !file
        ? 'Select a gallery case or upload an FRD file'
        : !report
          ? 'Generate a report, then inspect software-path evidence'
          : activeCaseId
            ? 'Run a solver smoke or export the report with Tier 0 wording'
            : 'Review the uploaded report; select a gallery case before solver run';
  const trustStrip: OperatorStatusItem[] = [
    { label: 'Claim tier', value: claimTier, tone: 'warning', detail: allowedClaim },
    { label: 'Solver truth', value: solverTruthSource, tone: candidateSpine || currentJobId ? 'accent' : 'warning' },
    { label: 'Execution mode', value: executionMode, tone: candidateSpine || currentJobId ? 'accent' : report ? 'warning' : 'muted' },
    { label: 'Validation status', value: reportValidationStatus, tone: report?.validation.status ? statusTone(report.validation.status) : statusTone(referenceStatusRaw) },
    { label: 'Golden samples', value: goldenSampleSummary, tone: goldenSampleReviewCount > 0 ? 'warning' : 'accent' },
    { label: 'Blueprint target', value: blueprintSummary.label, tone: 'warning', detail: `${blueprintSummary.coveredAnchorCount}/${blueprintSummary.anchorCount} anchors covered by ${blueprintSummary.availableEvidenceCount} available evidence ref(s); ${blueprintSummary.allowedClaim}` },
    { label: 'Allowed claim', value: 'not signed validation', tone: 'danger', detail: allowedClaim },
  ];
  const trustSections: OperatorStatusSection[] = [
    {
      title: 'Overview',
      icon: <LayoutDashboard size={16} />,
      items: [
        { label: 'Milestone', value: candidateSpine ? 'FM-03 Candidate Report Spine' : 'FM-01 Web Console Operator Shell', tone: 'accent' },
        { label: 'Work control', value: 'User blueprint scope; no Linear/Notion external write in this local slice', tone: 'warning' },
        { label: 'Active case', value: caseLabel, tone: activeCaseId || file ? 'accent' : 'muted' },
        { label: 'Next action', value: nextAction, tone: 'accent' },
      ],
    },
    {
      title: 'Runtime',
      icon: <Database size={16} />,
      items: [
        { label: 'Solver truth source', value: solverTruthSource, tone: candidateSpine || currentJobId ? 'accent' : 'warning' },
        { label: 'Execution mode', value: executionMode, tone: candidateSpine || currentJobId ? 'accent' : report ? 'warning' : 'muted' },
        { label: 'Analysis mode', value: analysisModeLabel },
        { label: 'Current job', value: currentJobLabel, tone: currentJobId ? 'accent' : 'muted' },
        { label: 'Run state', value: runState, tone: runStateTone },
        { label: 'Latest event', value: latestEvent },
        { label: 'Solver logs', value: solverLogSummary, tone: solverLogState?.status === 'unavailable' ? 'warning' : candidateSpine ? 'accent' : 'muted', detail: solverLogState?.unavailable_reason },
        { label: 'Solver convergence', value: convergenceSummary, tone: candidateConvergenceEvidence ? 'warning' : 'muted', detail: convergenceClaimImpact },
      ],
    },
    {
      title: 'Evidence',
      icon: <ClipboardCheck size={16} />,
      items: [
        { label: 'Evidence state', value: evidenceState, tone: report ? 'accent' : 'warning' },
        { label: 'Manifest / hashes', value: manifestState, tone: candidateManifest ? 'accent' : currentJobId ? 'warning' : 'muted' },
        { label: 'Backend provenance', value: backendProvenance },
        { label: 'Artifact list', value: candidateManifest ? candidateManifest.items.map((item) => `${item.kind}:${item.status}`).join(', ') : 'No candidate artifact list surfaced', tone: candidateManifest ? 'accent' : 'muted' },
        { label: 'Mesh artifact source', value: meshArtifactSource, tone: candidateMeshEvidence ? 'accent' : 'muted' },
        { label: 'Convergence artifacts', value: convergenceArtifactList, tone: candidateConvergenceEvidence ? 'accent' : 'muted' },
        { label: 'Mesh convergence study', value: meshConvergenceStudySource, tone: meshConvergenceStudy?.status === 'available' ? 'accent' : 'warning', detail: meshConvergenceClaimImpact },
        { label: 'Runtime SSOT', value: 'runs/ directory + CI artifacts; UI only surfaces current session state', tone: 'muted' },
      ],
    },
    {
      title: 'Validation',
      icon: <ShieldAlert size={16} />,
      items: [
        { label: 'Golden sample status', value: referenceStatus, tone: statusTone(referenceStatusRaw), detail: referenceReason },
        { label: 'Reference deviation', value: referenceDeviation, tone: report?.validation.status ? statusTone(report.validation.status) : 'muted' },
        { label: 'Report validation', value: reportValidationStatus, tone: report?.validation.status ? statusTone(report.validation.status) : 'muted' },
        { label: 'Units', value: unitSummary, tone: candidateAssumptions ? 'accent' : 'warning' },
        { label: 'Material', value: materialSummary, tone: candidateAssumptions?.material.status === 'declared' ? 'accent' : 'warning' },
        { label: 'BC / loads', value: boundarySummary, tone: candidateAssumptions?.boundary_conditions.status === 'declared' ? 'accent' : 'warning' },
        { label: 'Mesh topology', value: meshTopologySummary, tone: candidateMeshEvidence ? 'accent' : 'warning', detail: meshDeckElementTypes },
        { label: 'Mesh quality', value: meshQualitySummary, tone: candidateMeshEvidence?.quality.status === 'available' ? 'accent' : 'warning', detail: candidateMeshEvidence?.quality.unavailable_reason ?? meshClaimImpact },
        { label: 'Mesh convergence', value: meshConvergenceStudySummary, tone: meshConvergenceStudy?.status === 'available' ? 'accent' : 'warning', detail: meshConvergenceClaimImpact },
        { label: 'Convergence gaps', value: convergenceMissingSummary, tone: 'warning' },
        { label: 'FailurePattern', value: failurePatternRef, tone: failurePatternRef.startsWith('FP-') ? 'warning' : 'muted' },
      ],
    },
    {
      title: 'Blueprint target',
      icon: <ClipboardCheck size={16} />,
      items: [
        { label: 'Blueprint memory', value: blueprintSummary.imagePath, tone: 'accent' },
        { label: 'Evidence case', value: blueprintSummary.evidenceCaseId, tone: 'accent' },
        { label: 'Claim tier', value: blueprintSummary.claimTier, tone: 'warning', detail: blueprintSummary.allowedClaim },
        { label: 'Visual anchors', value: `${blueprintSummary.anchorCount} evidence-mapped anchor(s)`, tone: 'accent' },
        { label: 'Available evidence', value: `${blueprintSummary.availableEvidenceCount}/${blueprintSummary.evidenceCount} indexed evidence ref(s)`, tone: blueprintSummary.availableEvidenceCount > 0 ? 'accent' : 'warning' },
        { label: 'Covered anchors', value: `${blueprintSummary.coveredAnchorCount}/${blueprintSummary.anchorCount}`, tone: blueprintSummary.coveredAnchorCount === blueprintSummary.anchorCount ? 'accent' : 'warning' },
        { label: 'Started slices', value: `${blueprintSummary.startedSlices} local frontend/docs slice(s) started`, tone: 'accent' },
        { label: 'Next deferred slice', value: blueprintSummary.nextSlice, tone: 'warning' },
        { label: 'Tier 2 blockers', value: `${blueprintSummary.blockerCount} blocker(s) still active`, tone: 'danger' },
      ],
    },
    {
      title: 'Ballistic candidate',
      icon: <ShieldAlert size={16} />,
      items: [
        { label: 'Ballistic block', value: candidateBallistic ? humanizeStatus(candidateBallistic.status) : 'Not surfaced', tone: candidateBallistic?.status === 'candidate_observed' ? 'warning' : 'muted', detail: candidateBallistic?.claim_impact ?? 'Tier 1 candidate; not signed validation; not benchmark agreement' },
        { label: 'Initial velocity', value: ballisticInitialVelocitySummary, tone: candidateBallistic?.projectile_initial_velocity.status === 'declared' ? 'accent' : 'muted' },
        { label: 'Residual velocity', value: ballisticResidualVelocitySummary, tone: candidateBallistic?.residual_velocity_candidate.status === 'candidate_observed' ? 'warning' : 'muted', detail: 'Tier 1 candidate; not benchmark agreement' },
        { label: 'Perforation marker', value: ballisticPerforationSummary, tone: ballisticPerforationTone, detail: 'perforated_candidate is NOT "perforation completed"' },
        { label: 'Energy balance', value: ballisticEnergySummary, tone: ballisticEnergyTone, detail: candidateBallistic?.energy_balance_candidate.claim_impact ?? 'energy ratio is a Tier 1 candidate health indicator only' },
        { label: 'Animation manifest', value: ballisticAnimationSummary, tone: candidateBallistic?.animation_manifest.status === 'available' ? 'accent' : 'muted' },
        { label: 'Time-step convergence', value: ballisticTimeStepStudySummary, tone: ballisticTimeStepStudyTone, detail: ballisticTimeStepStudy?.claim_impact ?? 'Tier 2 dt convergence is reserved for FM-04b' },
        { label: 'Ballistic Tier 2 blockers', value: ballisticTier2BlockerSummary, tone: 'danger' },
      ],
    },
    {
      title: 'Gate',
      icon: <AlertTriangle size={16} />,
      items: [
        { label: 'Reviewer gate', value: reviewerSummary, tone: candidateReviewer?.verdict === 'candidate_ready_for_review' ? 'accent' : 'warning', detail: candidateReviewer?.summary },
        { label: 'Human / Claude handoff', value: 'Required before milestone acceptance or signed claim promotion', tone: 'warning' },
        { label: 'Allowed claim', value: allowedClaim, tone: 'danger' },
        { label: 'Limitations', value: candidateLimitations.length > 0 ? candidateLimitations.join('; ') : 'No candidate limitations surfaced', tone: 'warning' },
        { label: 'Tier 2 blockers', value: tier2BlockerSummary, tone: 'danger' },
      ],
    },
  ];
  const caeReviewCards: CaeReviewCard[] = [
    {
      card_type: 'blueprint_target',
      severity: 'info',
      finding: `${blueprintSummary.label}: ${blueprintSummary.claimTier}.`,
      evidence: `${blueprintSummary.imagePath}; case ${blueprintSummary.evidenceCaseId}; ${blueprintSummary.coveredAnchorCount}/${blueprintSummary.anchorCount} anchors covered; ${blueprintSummary.availableEvidenceCount}/${blueprintSummary.evidenceCount} evidence refs available`,
      recommended_action: 'Use the blueprint as the Workbench target map. The real OpenRadioss evidence is indexed for Tier 1 review; attach independent review/signoff before any stronger claim.',
      claim_impact: blueprintSummary.allowedClaim,
    },
    // FM-04a Phase 2 D — three industrial Trust Center cards.
    {
      card_type: 'energy_balance_status',
      severity:
        phase2EnergyBalanceTone === 'danger'
          ? 'critical'
          : phase2EnergyBalanceTone === 'warning'
            ? 'warning'
            : 'info',
      finding: `Tier 1 energy audit: ${phase2EnergyBalanceLabel}.`,
      evidence: (() => {
        const parts: string[] = [];
        if (phase2EnergyBalanceSummary.initialKineticEnergyJ !== null) {
          parts.push(
            `KE_initial=${phase2EnergyBalanceSummary.initialKineticEnergyJ.toExponential(3)}`,
          );
        }
        if (phase2EnergyBalanceSummary.residualKineticEnergyJ !== null) {
          parts.push(
            `KE_residual=${phase2EnergyBalanceSummary.residualKineticEnergyJ.toExponential(3)}`,
          );
        }
        if (phase2EnergyBalanceSummary.aggregateInternalEnergyJ !== null) {
          parts.push(
            `I_internal=${phase2EnergyBalanceSummary.aggregateInternalEnergyJ.toExponential(3)}`,
          );
        }
        if (phase2EnergyBalanceSummary.energyBalanceErrorPct !== null) {
          parts.push(
            `balance_err=${phase2EnergyBalanceSummary.energyBalanceErrorPct.toFixed(3)}%`,
          );
        }
        return parts.length > 0 ? parts.join('; ') : 'No energy audit data attached.';
      })(),
      recommended_action:
        phase2EnergyBalanceSummary.status === 'closed_aggregate'
          ? 'Closed aggregate audit; per-term plastic / contact / hourglass split requires /TH/PART cards in the starter — track as a FM-04b prerequisite, do not promote Tier 1 evidence as benchmark agreement.'
          : phase2EnergyBalanceSummary.status === 'partial_candidate'
            ? 'Partial audit (KE only). Run scripts/gs102_transient_candidate_pipeline.py so the engine .out energy table is parsed alongside ballistic metrics.'
            : 'No energy audit available; load a candidate spine from a real OpenRadioss run before drawing energy conclusions.',
      claim_impact: phase2EnergyBalanceSummary.claimImpact,
    },
    {
      card_type: 'convergence_study_status',
      severity:
        phase2ConvergenceTone === 'danger'
          ? 'critical'
          : phase2ConvergenceTone === 'warning'
            ? 'warning'
            : 'info',
      finding: `Tier 1 convergence study: ${phase2ConvergenceLabel}.`,
      evidence:
        phase2ConvergenceSummary.rowCount > 0
          ? `combined_verdict=${phase2ConvergenceSummary.combinedVerdict}; mesh=${phase2ConvergenceSummary.meshSweepStability}; dt=${phase2ConvergenceSummary.dtSweepStability}; tolerance=±${phase2ConvergenceSummary.tolerancePct}%; rows=${phase2ConvergenceSummary.rowCount}`
          : 'No convergence study attached; run scripts/gs102_convergence_sweep.py against existing project_state runs.',
      recommended_action:
        phase2ConvergenceSummary.combinedVerdict === 'candidate_observed_stable'
          ? 'Both mesh and dt sweeps stable inside tolerance; Tier 1 convergence evidence is supportable but is NOT benchmark agreement and NOT signed validation.'
          : phase2ConvergenceSummary.combinedVerdict === 'candidate_observed_unstable'
            ? 'Sweep crosses tolerance; refine the sweep grid and re-run before drawing any convergence conclusion. Do not promote Tier 1 unstable evidence.'
            : 'Insufficient data; add additional mesh / dt rows to the sweep before reporting a verdict.',
      claim_impact: TIER1_BANNER,
    },
    {
      card_type: 'candidate_case_selection',
      severity: phase2CandidateCaseTone === 'warning' ? 'warning' : 'info',
      finding: `Workbench candidate-case picker: ${phase2CandidateCaseLabel}.`,
      evidence:
        `starter=${phase2CandidateCaseSummary.starterDeckRelpath ?? 'n/a'}; ` +
        `engine=${phase2CandidateCaseSummary.engineDeckRelpath ?? 'n/a'}; ` +
        `generator=${phase2CandidateCaseSummary.generatorScriptRelpath ?? 'n/a'}; ` +
        `source=${phase2CandidateCaseSummary.source}`,
      recommended_action: phase2CandidateCaseSummary.caseId
        ? 'Switch the candidate case from the picker above to drive blueprint anchor evidence + result-mesh playback for a different fixture.'
        : 'Pick a Tier 1 candidate case from the picker above to surface deck paths and generator script provenance.',
      claim_impact: TIER1_BANNER,
    },
    // FM-04a Phase 4 E — cohort completeness review card.
    {
      card_type: 'cohort_completeness_status',
      severity: 'info',
      finding:
        'Cohort dashboard surfaces every *-candidate/ case with completeness score, perforation marker, residual velocity, audit / convergence verdict, last-modified.',
      evidence:
        'GET /api/v1/cohort-overview (Phase 4 B); per-case drill into GET /api/v1/case-completeness/<id> (Phase 4 A); CohortDashboardPanel + CaseCompletenessCard rendered above the Phase 3 panels.',
      recommended_action:
        'Use the score as an *evidence-presence* gate, NOT a validation-quality gate; even a 100/100 score does NOT authorize Tier 2 promotion — every FM-04b blocker remains gated per the rendered tier2_blockers_remaining list.',
      claim_impact:
        TIER1_BANNER + '; completeness score is evidence-presence only — not validation quality.',
    },
    // FM-04a Phase 3 C — two reviewer-experience review cards.
    {
      card_type: 'acceptance_packet_status',
      severity: selectedCandidateCaseId ? 'info' : 'warning',
      finding: selectedCandidateCaseId
        ? `Acceptance evidence packet available for ${selectedCandidateCaseId} via /api/v1/acceptance-packet/${selectedCandidateCaseId}.`
        : 'No candidate case selected; acceptance packet endpoint cannot be exercised.',
      evidence: selectedCandidateCaseId
        ? `Download URL: /api/v1/acceptance-packet/${selectedCandidateCaseId}; rendered by AcceptancePacketPanel above the blueprint.`
        : 'Pick a Tier 1 candidate case from the picker above to enable the acceptance packet download.',
      recommended_action: selectedCandidateCaseId
        ? 'Download the JSON, archive the artifact hashes, and treat it as a Tier 1 candidate manifest only — NOT a sealed FM-04b P8 packet.'
        : 'Select a candidate case so the AcceptancePacketPanel can fetch the manifest.',
      claim_impact: TIER1_BANNER + '; acceptance packet is Tier 1 manifest, not a sealed Tier 2 bundle.',
    },
    {
      card_type: 'case_comparison_status',
      severity: comparisonCaseA && comparisonCaseB && comparisonCaseA !== comparisonCaseB ? 'info' : 'warning',
      finding: comparisonCaseA && comparisonCaseB
        ? (comparisonCaseA === comparisonCaseB
          ? `Comparison A and B point at the same case (${comparisonCaseA}); pick two different candidate cases to see structured diffs.`
          : `Case-vs-case comparison available for A=${comparisonCaseA}, B=${comparisonCaseB} via /api/v1/case-comparison.`)
        : 'Comparison pair not fully selected; pick both A and B in the comparison panel above.',
      evidence: comparisonCaseA && comparisonCaseB
        ? `Endpoint: /api/v1/case-comparison?a=${comparisonCaseA}&b=${comparisonCaseB}; rendered by CaseComparisonPanel.`
        : 'CaseComparisonPanel shows the picker; nothing fetched until both A and B are set.',
      recommended_action: comparisonCaseA && comparisonCaseB && comparisonCaseA !== comparisonCaseB
        ? 'Inspect the structured diff; tone-coded cells flag deltas > 15% as danger. Comparison is case-vs-case only, NOT case-vs-benchmark.'
        : 'Select two different candidate cases in the comparison panel to surface the structured diff.',
      claim_impact: TIER1_BANNER + '; comparison is case-vs-case only (not vs experimental benchmark data).',
    },
    {
      card_type: 'claim_boundary',
      severity: 'warning',
      finding: `${claimTier}; signed validation is not available from this surface.`,
      evidence: candidateSpine ? `${candidateSpine.schema_version} from /report/generate` : 'ADR-023 + current FM-01 UI state',
      recommended_action: candidateSpine ? 'Use this as a reviewer-ready candidate package; do not promote beyond Tier 1 without Tier 2 blockers resolved.' : 'Keep the result labeled as demo-only until a Tier 1/2 evidence packet exists.',
      claim_impact: allowedClaim,
    },
    {
      card_type: 'solver_truth',
      severity: candidateSpine || currentJobId ? 'info' : 'warning',
      finding: solverTruthSource,
      evidence: candidateSpine ? `${solverLogSummary}; normal termination: ${candidateSpine.solver.normal_termination_state}` : currentJobId ? `solver job ${currentJobId}` : 'current frontend session has no fresh solver job id',
      recommended_action: candidateSpine ? 'Inspect solver log status and artifact hashes before reviewer handoff.' : currentJobId ? 'Inspect solver logs and attach manifest/hash evidence before promotion.' : 'Run a solver smoke only after selecting a case; keep current report as artifact review.',
      claim_impact: candidateSpine ? 'Tier 1 candidate evidence exists; Tier 2 remains blocked.' : currentJobId ? 'Fresh job evidence may support a candidate packet after manifest/hash capture.' : 'Tier 1 blocked; current evidence remains Tier 0.',
    },
    {
      card_type: 'evidence_packet',
      severity: candidateManifest ? 'info' : 'warning',
      finding: manifestState,
      evidence: candidateManifest ? candidateManifest.items.map((item) => `${item.kind}:${item.path}`).join('; ') : currentJobId ? 'WebSocket log stream' : activeCaseId ? '/cases/:id expected_results.json' : 'none',
      recommended_action: candidateManifest ? 'Attach the candidate manifest and limitations to review evidence.' : 'Prepare FM-03 Candidate Report Spine before treating this as engineering-candidate evidence.',
      claim_impact: candidateManifest ? 'Tier 1 evidence packet is available; Tier 2 remains blocked until benchmark/convergence/signoff.' : 'Tier 2 blocked; Tier 1 blocked until manifest, logs, units/material/BC provenance, hashes, and limitations are packaged.',
    },
    {
      card_type: 'assumptions',
      severity: candidateAssumptions?.material.status === 'declared' && candidateAssumptions.boundary_conditions.status === 'declared' ? 'info' : 'warning',
      finding: `Units/material/BC: ${unitSummary}`,
      evidence: `Material: ${materialSummary}; BC/loads: ${boundarySummary}`,
      recommended_action: 'Resolve unavailable assumptions before making stronger engineering or validation claims.',
      claim_impact: 'Tier 1 can carry explicit limitations; Tier 2 requires traceable assumptions and signoff.',
    },
    {
      card_type: 'golden_sample_status',
      severity: referenceStatusRaw && referenceStatusRaw !== 'pass' ? 'warning' : 'info',
      finding: `${activeCaseId ? activeCaseId : 'No active GS case'}: ${referenceStatus}`,
      evidence: activeCaseId ? `${activeCaseId}/expected_results.json via /cases/:id` : 'No active golden-sample reference',
      recommended_action: activeCaseId ? referenceReason : 'Select GS-001, GS-002, or GS-003 to inspect current review blockers.',
      claim_impact: referenceStatusRaw === 'insufficient_evidence' ? 'Signed validation is blocked by golden-sample evidence status.' : 'No signed claim is implied.',
    },
    {
      card_type: 'reference_validation',
      severity: report?.validation.status === 'FAIL' ? 'warning' : 'info',
      finding: `Report validation: ${reportValidationStatus}; reference deviation: ${referenceDeviation}.`,
      evidence: report ? 'backend /report/generate response' : 'no report response loaded',
      recommended_action: report?.validation.status === 'FAIL' ? 'Route to reviewer/failure attribution before any claim promotion.' : 'Load or regenerate the report before review.',
      claim_impact: report?.validation.status === 'PASS' ? 'Still not signed validation without Tier 2 packet.' : 'Claim boundary remains demo-only or needs review.',
    },
    {
      card_type: 'mesh_quality',
      severity: candidateMeshEvidence?.quality.status === 'available' ? 'info' : 'warning',
      finding: candidateMeshEvidence ? `${meshTopologySummary}; quality ${humanizeStatus(candidateMeshEvidence.quality.status)}.` : 'Mesh evidence is not present in the current report payload.',
      evidence: candidateMeshEvidence ? `${meshArtifactSource}; element types ${meshDeckElementTypes}` : 'current ReportData lacks mesh_evidence fields',
      recommended_action: candidateMeshEvidence?.quality.status === 'available' ? 'Attach this evidence to reviewer handoff, but keep the claim at Tier 1.' : 'Attach scaled-Jacobian/aspect-ratio quality output or mesh_meta quality evidence before claiming mesh adequacy.',
      claim_impact: meshClaimImpact,
    },
    {
      card_type: 'mesh_convergence_study',
      severity: meshConvergenceStudy?.status === 'available' ? 'info' : 'warning',
      finding: meshConvergenceStudySummary,
      evidence: meshConvergenceStudySource,
      recommended_action: meshConvergenceStudy?.status === 'available' ? 'Use this as Tier 1 reviewer evidence; do not treat it as benchmark agreement.' : 'Attach mesh_convergence.json from a refinement sweep before claiming mesh convergence evidence.',
      claim_impact: meshConvergenceClaimImpact,
    },
    {
      card_type: 'convergence_evidence',
      severity: candidateConvergenceEvidence?.status === 'job_completed' || candidateConvergenceEvidence?.status === 'solver_artifact_converged' ? 'info' : 'warning',
      finding: convergenceSummary,
      evidence: convergenceArtifactList,
      recommended_action: candidateConvergenceEvidence ? `Resolve remaining gaps: ${convergenceMissingSummary}` : 'Attach .sta/.cvg/.dat or solver job status before reviewer handoff.',
      claim_impact: convergenceClaimImpact,
    },
    {
      card_type: 'ballistic_candidate',
      severity: candidateBallistic?.status === 'candidate_observed' ? 'warning' : 'info',
      finding: candidateBallistic
        ? `${humanizeStatus(candidateBallistic.status)}: V0 ${ballisticInitialVelocitySummary}; vR ${ballisticResidualVelocitySummary}.`
        : 'Ballistic block not present; FM-04a P1+ spine v2 is not loaded yet.',
      evidence: candidateBallistic ? `claim_boundary: ${candidateBallistic.claim_boundary}` : 'no ballistic block in candidate_report_spine response',
      recommended_action: candidateBallistic
        ? 'Treat residual velocity / energy balance / perforation marker as Tier 1 candidate evidence ONLY. Do NOT promote to "benchmark agreement" or "perforation completed".'
        : 'Run a ballistic candidate case through the FM-04a P4 OpenRadioss adapter and write a ballistic_metrics.json sidecar before reviewing.',
      claim_impact: candidateBallistic?.claim_impact ?? 'Tier 1 candidate ballistic evidence only; not benchmark agreement; not signed validation',
    },
    {
      card_type: 'ballistic_perforation',
      severity: ballisticPerforationMarker === 'perforated_candidate' || ballisticPerforationMarker === 'embedded_candidate' ? 'warning' : 'info',
      finding: `Perforation marker: ${ballisticPerforationSummary}.`,
      evidence: candidateBallistic?.perforation_marker.evidence_path ?? 'no candidate perforation evidence path surfaced',
      recommended_action: 'Reaffirm in any reviewer-facing wording that perforated_candidate is NOT "steel perforation completed" / "bullet-through-steel complete" / "signed GS101" / "validated physics".',
      claim_impact: 'Tier 1 candidate marker only; benchmark agreement and signed perforation claims are reserved for FM-04b (ADR-024 full).',
    },
    {
      card_type: 'time_step_convergence_study',
      severity: ballisticTimeStepStudy?.candidate_stability === 'candidate_observed_unstable' ? 'critical' : ballisticTimeStepStudy?.status === 'available' ? 'info' : 'warning',
      finding: `Time-step convergence: ${ballisticTimeStepStudySummary}`,
      evidence: ballisticTimeStepStudy?.source ?? 'no time_step_convergence.json sidecar surfaced',
      recommended_action: ballisticTimeStepStudy?.candidate_stability === 'candidate_observed_unstable'
        ? 'Treat dt-axis as unstable; tighten dt and re-run before any reviewer handoff. The candidate-stability rule is NOT a Tier 2 tolerance comparison.'
        : ballisticTimeStepStudy?.status === 'available'
          ? 'Tier 1 candidate dt convergence indicator only; do not promote to benchmark agreement.'
          : 'Attach a 3-level dt sweep sidecar (time_step_convergence.json) under project_state/.../ballistic/ to surface candidate stability.',
      claim_impact: ballisticTimeStepStudy?.claim_impact ?? 'Tier 2 dt convergence and benchmark tolerance are reserved for FM-04b.',
    },
  ];

  // FM-04a Phase 18 D/E — Cmd-K command registry (round 2 integration).
  // Every action a reviewer needs to take from a keyboard / palette
  // is registered here; new tasks land as new entries.
  const _runSolverFromPalette = (): void => {
    if (!activeCaseId) {
      // No-op when no case is selected; the palette closes regardless.
      console.warn('Run Solver command invoked with no active case selected.')
      return
    }
    // Re-uses the existing solver flow; safer than duplicating fetch logic.
    void fetch(`${API_BASE}/solver/run`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        case_id: activeCaseId,
        analysis_type: analysisType,
        // Phase 18 E (round 3) — palette-fired re-runs carry the
        // material pick too; symmetric with the main solver flow.
        // Same Phase 19 priority-0.5 caveat: field declared on the
        // backend RunRequest model but not yet plumbed into the
        // solver pipeline. Wire-level contract only.
        material_id: selectedMaterial.id,
      }),
    })
  }
  const commands: Command[] = [
    {
      id: 'cmd-switch-tab-visual',
      label: 'Switch to 3D Scene tab',
      hotkey: 'g 1',
      category: 'navigation' as CommandCategory,
      handler: () => setActiveTab('visual'),
    },
    {
      id: 'cmd-switch-tab-narrative',
      label: 'Switch to Narrative tab',
      hotkey: 'g 2',
      category: 'navigation' as CommandCategory,
      handler: () => setActiveTab('report'),
    },
    {
      id: 'cmd-switch-tab-exploration',
      label: 'Switch to Exploration tab',
      hotkey: 'g 3',
      category: 'navigation' as CommandCategory,
      handler: () => setActiveTab('explore'),
    },
    {
      id: 'cmd-run-solver',
      label: 'Run CalculiX solver on active case',
      description: activeCaseId
        ? `Active case: ${activeCaseId}`
        : 'No case selected — pick one first',
      category: 'solver' as CommandCategory,
      handler: _runSolverFromPalette,
    },
    {
      id: 'cmd-pick-material-steel',
      label: 'Pick material — Structural Steel S355',
      category: 'material' as CommandCategory,
      handler: () => setSelectedMaterial(FALLBACK_MATERIALS[0]),
    },
    {
      id: 'cmd-pick-material-aluminium',
      label: 'Pick material — Aluminium 6061-T6',
      category: 'material' as CommandCategory,
      handler: () => setSelectedMaterial(FALLBACK_MATERIALS[1]),
    },
    {
      id: 'cmd-pick-material-titanium',
      label: 'Pick material — Titanium Ti-6Al-4V',
      category: 'material' as CommandCategory,
      handler: () => setSelectedMaterial(FALLBACK_MATERIALS[2]),
    },
    {
      id: 'cmd-close-palette',
      label: 'Close command palette',
      hotkey: 'escape',
      category: 'navigation' as CommandCategory,
      handler: () => setPaletteOpen(false),
    },
  ]
  useKeyboardShortcuts([
    {
      hotkey: 'mod+k',
      handler: (e) => {
        e.preventDefault()
        setPaletteOpen((prev) => !prev)
      },
      fireInTextInput: true,
    },
  ])

  return (
    <div className="app-container" style={{ display: 'grid', gridTemplateColumns: '240px 300px 1fr', height: '100vh' }}>
      <CommandPalette
        open={paletteOpen}
        onClose={() => setPaletteOpen(false)}
        commands={commands}
      />

      {/* Project Sidebar */}
      <ProjectManager
        selectedProjectId={selectedProjectId}
        onSelectProject={(id) => setSelectedProjectId(id)}
      />

      {/* Case Sidebar */}
      <aside className="glass-sidebar" style={{ padding: '24px', display: 'flex', flexDirection: 'column', gap: '24px', borderLeft: '1px solid rgba(255,255,255,0.05)' }}>

        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div style={{ width: '40px', height: '40px', background: 'var(--accent)', borderRadius: '10px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <Zap size={24} color="#000" />
          </div>
          <h2 style={{ fontSize: '1.25rem', fontWeight: 700, margin: 0 }}>Structure<span style={{ color: 'var(--accent)' }}>AI</span></h2>
        </div>
        {/* FM-04a Phase 18 E (round 3) — discoverable Cmd-K hint.
            Addresses UX agent round-2 finding that the palette was
            real but undiscoverable. Clicking the chip also opens it. */}
        <button
          type="button"
          onClick={() => setPaletteOpen(true)}
          data-testid="cmd-k-hint"
          aria-label="Open command palette (Cmd-K)"
          style={{
            display: 'flex', alignItems: 'center', justifyContent: 'space-between',
            gap: '8px', padding: '6px 10px', borderRadius: '6px',
            background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.08)',
            color: 'var(--text-secondary)', cursor: 'pointer', fontSize: '0.75rem',
            textAlign: 'left',
          }}
        >
          <span>Command palette</span>
          <kbd style={{ fontSize: '0.7rem', padding: '1px 6px', borderRadius: 4, background: 'rgba(255,255,255,0.08)', fontFamily: 'ui-monospace, Menlo, monospace' }}>⌘K</kbd>
        </button>

        <nav style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
          <button className="nav-item active" style={{ display: 'flex', alignItems: 'center', gap: '12px', padding: '12px', borderRadius: '8px', background: 'var(--accent-glow)', color: 'var(--accent)', border: 'none', cursor: 'pointer', textAlign: 'left', fontWeight: 600 }}>
            <LayoutDashboard size={18} /> Workbench
          </button>
        </nav>

        {/* Case Gallery */}
        <div>
          <div style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '12px', paddingLeft: '12px' }}>Case Gallery</div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
            {availableCases.map(c => (
              <button key={c.id} onClick={() => selectCase(c)} className={`case-item ${activeCaseId === c.id ? 'active' : ''}`} style={{ display: 'flex', alignItems: 'center', gap: '12px', padding: '10px 12px', borderRadius: '8px', background: activeCaseId === c.id ? 'rgba(255,255,255,0.05)' : 'transparent', color: activeCaseId === c.id ? 'var(--accent)' : 'var(--text-secondary)', border: 'none', cursor: 'pointer', textAlign: 'left', fontSize: '0.875rem' }}>
                <Box size={16} /> {c.name}
              </button>
            ))}
          </div>
        </div>

        {activeExperiment && (
           <div className="glass-panel" style={{ padding: '16px' }}>
              <div style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--accent)', marginBottom: '8px' }}>EXP: {activeExperiment.parameter.toUpperCase()}</div>
              {activeExperiment.runs.map(r => (
                  <div key={r.iteration} style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', marginBottom: '4px' }}>
                     <span>V={r.value}</span>
                     <span style={{ color: r.status === 'COMPLETED' ? 'var(--accent)' : 'var(--text-muted)' }}>{r.status}</span>
                  </div>
              ))}
           </div>
        )}

        <div style={{ marginTop: 'auto' }}>
          <label className="glass-panel" style={{ display: 'block', padding: '20px', textAlign: 'center', border: '2px dashed var(--border)', cursor: 'pointer', transition: 'border-color 0.2s' }}>
            <input type="file" onChange={handleFileUpload} style={{ display: 'none' }} />
            <FileUp size={24} style={{ marginBottom: '8px', color: 'var(--text-secondary)' }} />
            <div style={{ fontSize: '0.875rem', fontWeight: 500 }}>Upload FRD</div>
          </label>
        </div>
      </aside>

      {/* Main Content Area */}
      <div style={{ display: 'grid', gridTemplateColumns: showChat ? '1fr 340px' : '1fr', height: '100vh', overflow: 'hidden' }}>
        <main style={{ overflowY: 'auto', background: 'var(--bg-base)', position: 'relative', display: 'flex', flexDirection: 'column' }}>
            <header style={{ padding: '20px 40px', borderBottom: '1px solid var(--border)', display: 'flex', justifyContent: 'space-between', alignItems: 'center', position: 'sticky', top: 0, background: 'rgba(2, 6, 23, 0.8)', backdropFilter: 'blur(8px)', zIndex: 10 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--text-muted)', fontSize: '0.875rem' }}>
                    Analysis <ChevronRight size={14} /> <span style={{ color: 'var(--text-primary)' }}>{activeCaseId || (file ? file.name : "Session")}</span>
                </div>
                {report && <ComplianceBadge status={report.metrics.status} standard="GB50017" />}
            </div>
            <div style={{ display: 'flex', gap: '12px' }}>
                <button onClick={() => setShowChat(!showChat)} style={{ padding: '8px 16px', borderRadius: '8px', background: showChat ? 'var(--accent)' : 'var(--bg-surface)', color: showChat ? '#000' : '#fff', border: '1px solid var(--border)', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer' }}>
                    <MessageSquare size={16} /> Copilot
                </button>
                {activeCaseId && (
                <div style={{ display: 'flex', gap: '8px' }}>
                    <select 
                        value={analysisType} 
                        onChange={(e) => setAnalysisType(e.target.value as 'static' | 'modal' | 'buckling')}
                        style={{ background: 'var(--bg-surface)', color: '#fff', border: '1px solid var(--border)', borderRadius: '8px', padding: '0 12px', fontSize: '0.85rem', outline: 'none' }}
                    >
                        <option value="static">Static Analysis</option>
                        <option value="modal">Modal Analysis</option>
                        <option value="buckling">Linear Buckling</option>
                    </select>
                    <button disabled={solving} onClick={runSolver} style={{ padding: '8px 16px', borderRadius: '8px', background: 'var(--accent)', color: '#000', border: 'none', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '8px', cursor: solving ? 'not-allowed' : 'pointer', opacity: solving ? 0.6 : 1 }}>
                        {solving ? <Loader2 size={16} className="animate-spin" /> : <Play size={16} fill="currentColor" />}
                        Run Solver
                    </button>
                    {solving && (
                      <button onClick={stopSolver} style={{ padding: '8px 16px', borderRadius: '8px', background: 'rgba(255,100,100,0.2)', color: '#ff6b6b', border: '1px solid rgba(255,100,100,0.3)', fontWeight: 600, cursor: 'pointer' }}>
                        Stop
                      </button>
                    )}
                </div>
                )}
            </div>
            </header>

            <div style={{ padding: '40px', flex: 1 }}>
            <OperatorStatusPanel
              strip={trustStrip}
              sections={trustSections}
              goldenSamples={goldenSampleQueue}
            />

            <div className="glass-panel" style={{ padding: '8px', display: 'flex', gap: '8px', width: 'fit-content', marginBottom: '32px' }}>
                <TabButton active={activeTab === 'visual'} onClick={() => setActiveTab('visual')} label="3D Scene" icon={<Box size={16} />} />
                <TabButton active={activeTab === 'report'} onClick={() => setActiveTab('report')} label="Narrative" icon={<Activity size={16} />} />
                {activeCaseId && <TabButton active={activeTab === 'explore'} onClick={() => setActiveTab('explore')} label="Exploration" icon={<Compass size={16} />} />}
            </div>

            {activeTab === 'visual' && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                    <CohortDashboardPanel
                        apiBase={API_BASE}
                        selectedCaseId={selectedCandidateCaseId}
                        onSelectCase={(id) => {
                            setSelectedCandidateCaseId(id);
                            try {
                                window.localStorage.setItem('fm04a.candidateCaseId', id);
                            } catch {
                                /* no-op when storage is unavailable */
                            }
                        }}
                    />
                    {/*
                        FM-04a Phase 12 I — Cohort substantiation panel.
                        Consumes the Phase 12 E `cohortDashboardClient.ts`
                        orchestrator + its load-bearing X:-2 defensive
                        parsers. Rendered as a SECOND cohort surface
                        alongside (not replacing) the legacy
                        CohortDashboardPanel; the two surfaces serve
                        different blueprints (#04 vs #07) and Phase 13
                        may unify them once both are observed-stable.
                        Component-level contract pinned by
                        `frontend/test/CohortSubstantiationPanel.test.tsx`;
                        visual integration requires running dev-server
                        smoke (deferred as Phase 13 carry-forward).
                    */}
                    <CohortSubstantiationPanel apiBase={API_BASE} />
                    <CaseCompletenessCard
                        apiBase={API_BASE}
                        caseId={selectedCandidateCaseId}
                    />
                    <CandidateCasePicker
                        apiBase={API_BASE}
                        selectedCaseId={selectedCandidateCaseId}
                        onSelect={(id) => {
                            setSelectedCandidateCaseId(id);
                            try {
                                window.localStorage.setItem('fm04a.candidateCaseId', id);
                            } catch {
                                /* no-op when storage is unavailable */
                            }
                        }}
                    />
                    <AcceptancePacketPanel
                        apiBase={API_BASE}
                        caseId={selectedCandidateCaseId}
                    />
                    <ConvergenceStudyViewer
                        apiBase={API_BASE}
                        caseId={selectedCandidateCaseId}
                    />
                    <CaseComparisonPanel
                        apiBase={API_BASE}
                        cases={FALLBACK_CANDIDATE_CASES}
                        caseA={comparisonCaseA}
                        caseB={comparisonCaseB}
                        onSelectA={(id) => {
                            setComparisonCaseA(id);
                            try {
                                window.localStorage.setItem('fm04a.comparisonCaseA', id);
                            } catch {
                                /* no-op when storage is unavailable */
                            }
                        }}
                        onSelectB={(id) => {
                            setComparisonCaseB(id);
                            try {
                                window.localStorage.setItem('fm04a.comparisonCaseB', id);
                            } catch {
                                /* no-op when storage is unavailable */
                            }
                        }}
                    />
                    <ReviewerBundlePanel apiBase={API_BASE} />
                    <ArchivedPacketDiffPanel apiBase={API_BASE} />
                    <ReproducibilityManifestCard
                        apiBase={API_BASE}
                        caseId={selectedCandidateCaseId}
                    />
                    <CohortExecutiveSummaryPanel apiBase={API_BASE} />
                    <CohortAnomaliesPanel apiBase={API_BASE} />
                    <CohortTrendAnomaliesPanel apiBase={API_BASE} />
                    <TrustScoreGauge
                        apiBase={API_BASE}
                        caseId={selectedCandidateCaseId}
                        latestSignoffVerdict={latestSignoff?.verdict ?? null}
                        latestSignoffReviewer={latestSignoff?.reviewer ?? null}
                        latestSignoffUtc={latestSignoff?.signoffUtc ?? null}
                    />
                    <SignoffHistoryPanel
                        apiBase={API_BASE}
                        caseId={selectedCandidateCaseId}
                        onLatestRecord={setLatestSignoff}
                    />
                    <TrustScoreTimelineChart
                        apiBase={API_BASE}
                        caseId={selectedCandidateCaseId}
                    />
                    <CohortSnapshotPanel
                        apiBase={API_BASE}
                        selectedLabelA={snapshotLabelA}
                        selectedLabelB={snapshotLabelB}
                        onSelectLabelA={setSnapshotLabelA}
                        onSelectLabelB={setSnapshotLabelB}
                    />
                    {/* FM-04a Phase 9 E — Provenance panel; only mounts when a
                        snapshot label is known so we never fire a fetch with
                        empty params (Phase 9 anti-gaming guard X: -2). */}
                    {selectedCandidateCaseId && snapshotLabelA && (
                        <ProvenancePanel
                            apiBase={API_BASE}
                            caseId={selectedCandidateCaseId}
                            snapshotLabel={snapshotLabelA}
                        />
                    )}
                    {/* FM-04a Phase 11 E — Advisor critique panel; same mount
                        guard as ProvenancePanel above. The advisor surface is
                        advisor-only (NOT driver); reviewer agency preserved. */}
                    {selectedCandidateCaseId && snapshotLabelA && (
                        <AdvisorPanel
                            apiBase={API_BASE}
                            caseId={selectedCandidateCaseId}
                            snapshotLabel={snapshotLabelA}
                        />
                    )}
                    <DriftNarrativePanel
                        apiBase={API_BASE}
                        labelA={snapshotLabelA}
                        labelB={snapshotLabelB}
                    />
                    {/* FM-04a Phase 18 E (round 2) — materials library picker.
                        Tier 1 banner inline; reviewer can swap material by
                        click or via the Cmd-K palette. Selection wired to
                        `selectedMaterial` state for downstream INP composition. */}
                    <MaterialPickerPanel
                        apiBase={API_BASE}
                        selectedMaterialId={selectedMaterial.id}
                        onMaterialChange={setSelectedMaterial}
                    />
                    <BulletPlateBlueprintPanel />
                </div>
            )}

            <div style={{ padding: '0', flex: 1 }}>
                {activeTab === 'explore' ? (
                    <div style={{ display: 'grid', gridTemplateColumns: 'minmax(400px, 500px) 1fr', gap: '32px' }}>
                        <SensitivityForm activeCaseId={activeCaseId!} onRunStudy={handleRunStudy} loading={loading} />
                        {activeExperiment && activeExperiment.status === 'COMPLETED' && (
                        <div className="glass-panel" style={{ padding: '24px' }}>
                            <h3 style={{ fontSize: '1rem', marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '10px' }}>
                                <ArrowRightLeft size={18} color="var(--accent)" /> Result Comparison
                            </h3>
                            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                                {activeExperiment.runs.map((r, i) => (
                                <div key={i} className="glass-panel" style={{ padding: '12px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                    <span>Iteration {i+1} (Value: {r.value})</span>
                                    <button onClick={() => { if (comparedIndices) { if (comparedIndices[0] === i) setComparedIndices(null); else setComparedIndices([comparedIndices[0], i]); } else setComparedIndices([i, -1]); }} style={{ background: comparedIndices?.includes(i) ? 'var(--accent)' : 'transparent', border: '1px solid var(--accent)', color: comparedIndices?.includes(i) ? '#000' : 'var(--accent)', padding: '4px 12px', borderRadius: '4px', fontSize: '0.75rem', cursor: 'pointer' }}>
                                        {comparedIndices?.includes(i) ? 'Selected' : 'Compare'}
                                    </button>
                                </div>
                                ))}
                            </div>
                        </div>
                        )}
                    </div>
                ) : (
                    <>
                    {loading ? (
                        <div className="shimmer-active" style={{ height: '400px', width: '100%', borderRadius: '12px', background: 'var(--bg-surface)' }}></div>
                    ) : report ? (
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '32px' }}>
                            <div className="glass-panel" style={{ minHeight: activeTab === 'visual' && activeCaseId ? '820px' : '600px', padding: '0', overflow: 'hidden' }}>
                                {activeTab === 'visual' ? (
                                    <div
                                      style={{
                                        display: 'grid',
                                        gridTemplateRows: activeCaseId ? '400px minmax(300px, 1fr)' : '1fr',
                                        gap: activeCaseId ? '12px' : 0,
                                        padding: activeCaseId ? '12px' : 0,
                                        minHeight: activeCaseId ? '820px' : '600px',
                                      }}
                                    >
                                        {activeCaseId && (
                                          <ResultMeshPlaybackPanel
                                            caseId={activeCaseId}
                                            apiBase={API_BASE}
                                            enabled={activeTab === 'visual'}
                                          />
                                        )}
                                        <div
                                          style={{
                                            position: 'relative',
                                            width: '100%',
                                            minHeight: '300px',
                                            overflow: 'hidden',
                                            border: activeCaseId ? '1px solid var(--border)' : 'none',
                                            borderRadius: activeCaseId ? '8px' : 0,
                                          }}
                                        >
                                        <iframe 
                                            src={comparedIndices && comparedIndices[1] !== -1 
                                                ? `${API_BASE}/visualize/delta?file1=${activeExperiment?.runs[comparedIndices[0]].inp_path.replace('.inp','.frd')}&file2=${activeExperiment?.runs[comparedIndices[1]].inp_path.replace('.inp','.frd')}` 
                                                : `${API_BASE}/visualize/plot?case_id=${activeCaseId || 'last'}&output_format=html&increment_index=${selectedModeIndex}`} 
                                            style={{ width: '100%', height: '100%', border: 'none' }} 
                                            title="FEA Visualization" 
                                        />
                                        
                                        {report?.increments && report.increments.length > 0 && (
                                            <div style={{ position: 'absolute', top: '24px', right: '24px', width: '320px', zIndex: 10 }}>
                                                <ModeSelector 
                                                    increments={report.increments}
                                                    selectedModeIndex={selectedModeIndex}
                                                    activeAnalysisType={analysisType}
                                                    onSelectMode={(idx) => setSelectedModeIndex(idx)}
                                                />
                                            </div>
                                        )}
                                        </div>
                                    </div>
                                ) : (
                                <div style={{ padding: '40px', color: 'var(--text-secondary)' }} className="report-markdown">
                                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '24px', paddingBottom: '16px', borderBottom: '1px solid var(--border)' }}>
                                        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                                            <BookOpen size={20} color="var(--accent)" />
                                            <h2 style={{ margin: 0 }}>Design Auditor Insight</h2>
                                        </div>
                                        <button 
                                            onClick={downloadPDFReport}
                                            style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)', color: 'var(--accent)', padding: '6px 14px', borderRadius: '6px', fontSize: '0.85rem', fontWeight: 600, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '8px' }}
                                        >
                                            <Download size={14} /> Export PDF Document
                                        </button>
                                    </div>
                                    <div dangerouslySetInnerHTML={{ __html: report.markdown.replace(/\n/g, '<br/>') }} />
                                </div>
                                )}
                            </div>
                        </div>
                    ) : (
                        <div style={{ height: '400px', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', color: 'var(--text-muted)', gap: '16px' }}>
                            <LayoutDashboard size={48} strokeWidth={1} />
                            <div>Select a structural case from the gallery to begin analysis</div>
                        </div>
                    )}
                    </>
                )}
            </div>
            </div>

            {showConsole && (
            <div className="glass-panel" style={{ margin: '0 40px 40px 40px', height: '160px', display: 'flex', flexDirection: 'column', background: '#000' }}>
                <div style={{ flex: 1, padding: '12px', overflowY: 'auto', fontFamily: 'monospace', fontSize: '0.8rem', color: '#ccc' }}>
                {logs.map((log, i) => <div key={i}>{log}</div>)}
                <div ref={terminalEndRef} />
                </div>
            </div>
            )}
        </main>

        {showChat && (
            <aside style={{ borderLeft: '1px solid var(--border)', background: 'var(--bg-sidebar)', zIndex: 5 }}>
                <ChatPanel
                  caseId={activeCaseId}
                  onExecuteAction={handleExecuteCopilotAction}
                  reviewCards={caeReviewCards}
                  claimTier={claimTier}
                  allowedClaim={allowedClaim}
                />
            </aside>
        )}
      </div>
    </div>
  );
}

function OperatorStatusPanel({
  strip,
  sections,
  goldenSamples,
}: {
  strip: OperatorStatusItem[];
  sections: OperatorStatusSection[];
  goldenSamples: GoldenSampleQueueItem[];
}) {
  const toneColor = (tone?: OperatorStatusItem['tone']) => {
    if (tone === 'accent') return 'var(--accent)';
    if (tone === 'warning') return '#f59e0b';
    if (tone === 'danger') return '#ef4444';
    return 'var(--text-primary)';
  };

  const toneBackground = (tone?: OperatorStatusItem['tone']) => {
    if (tone === 'accent') return 'rgba(16, 185, 129, 0.08)';
    if (tone === 'warning') return 'rgba(245, 158, 11, 0.08)';
    if (tone === 'danger') return 'rgba(239, 68, 68, 0.08)';
    return 'rgba(15, 23, 42, 0.55)';
  };

  const toneBorder = (tone?: OperatorStatusItem['tone']) => {
    if (tone === 'accent') return 'rgba(16, 185, 129, 0.35)';
    if (tone === 'warning') return 'rgba(245, 158, 11, 0.35)';
    if (tone === 'danger') return 'rgba(239, 68, 68, 0.35)';
    return 'var(--border)';
  };

  return (
    <section className="glass-panel" style={{ padding: '18px 20px', marginBottom: '24px' }} aria-label="Validation and trust center">
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '16px', marginBottom: '16px', flexWrap: 'wrap' }}>
        <div>
          <div style={{ fontSize: '0.72rem', fontWeight: 700, color: 'var(--accent)', textTransform: 'uppercase' }}>Validation & Trust Center</div>
          <h2 style={{ fontSize: '1.1rem', margin: '4px 0 0 0' }}>Evidence-first workbench state</h2>
        </div>
        <div style={{ color: '#ef4444', fontSize: '0.78rem', fontWeight: 800, border: '1px solid rgba(239, 68, 68, 0.35)', borderRadius: '999px', padding: '5px 10px', background: 'rgba(239, 68, 68, 0.08)' }}>
          not signed validation
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '10px', marginBottom: '18px' }}>
        {strip.map((item) => (
          <div key={item.label} style={{ background: toneBackground(item.tone), border: `1px solid ${toneBorder(item.tone)}`, borderRadius: '8px', padding: '12px', minHeight: '78px' }}>
            <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 700, marginBottom: '6px' }}>{item.label}</div>
            <div style={{ color: toneColor(item.tone), fontSize: '0.88rem', fontWeight: 650, lineHeight: 1.35, overflowWrap: 'anywhere' }}>{item.value}</div>
            {item.detail && <div style={{ color: 'var(--text-secondary)', fontSize: '0.72rem', lineHeight: 1.35, marginTop: '6px', overflowWrap: 'anywhere' }}>{item.detail}</div>}
          </div>
        ))}
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: '12px' }}>
        {sections.map((section) => (
          <div key={section.title} style={{ background: 'rgba(15, 23, 42, 0.48)', border: '1px solid var(--border)', borderRadius: '8px', padding: '14px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--text-primary)', fontSize: '0.86rem', fontWeight: 800, marginBottom: '10px' }}>
              <span style={{ color: 'var(--accent)', display: 'flex' }}>{section.icon}</span>
              {section.title}
            </div>
            <div style={{ display: 'grid', gap: '9px' }}>
              {section.items.map((item) => (
                <div key={`${section.title}-${item.label}`} style={{ borderTop: '1px solid var(--border)', paddingTop: '9px' }}>
                  <div style={{ fontSize: '0.66rem', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 700, marginBottom: '4px' }}>{item.label}</div>
                  <div style={{ color: toneColor(item.tone), fontSize: '0.82rem', fontWeight: 650, lineHeight: 1.35, overflowWrap: 'anywhere' }}>{item.value}</div>
                  {item.detail && <div style={{ color: 'var(--text-secondary)', fontSize: '0.72rem', lineHeight: 1.35, marginTop: '4px', overflowWrap: 'anywhere' }}>{item.detail}</div>}
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>

      <div style={{ marginTop: '14px', background: 'rgba(15, 23, 42, 0.48)', border: '1px solid var(--border)', borderRadius: '8px', padding: '14px' }}>
        <div style={{ fontSize: '0.86rem', fontWeight: 800, marginBottom: '10px', display: 'flex', alignItems: 'center', gap: '8px' }}>
          <ShieldAlert size={16} color="var(--accent)" />
          Golden Sample Review Queue
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '10px' }}>
          {goldenSamples.map((sample) => (
            <div key={sample.caseId} style={{ border: `1px solid ${toneBorder(sample.tone)}`, background: toneBackground(sample.tone), borderRadius: '8px', padding: '12px', minHeight: '106px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '8px', marginBottom: '6px' }}>
                <div style={{ color: 'var(--text-primary)', fontWeight: 800, fontSize: '0.82rem' }}>{sample.caseId}</div>
                <div style={{ color: toneColor(sample.tone), fontWeight: 800, fontSize: '0.68rem', textTransform: 'uppercase' }}>{sample.status}</div>
              </div>
              <div style={{ color: 'var(--text-secondary)', fontSize: '0.74rem', lineHeight: 1.35, marginBottom: '6px' }}>{sample.name}</div>
              <div style={{ color: 'var(--text-secondary)', fontSize: '0.72rem', lineHeight: 1.35, overflowWrap: 'anywhere' }}>{sample.reason}</div>
              <div style={{ color: toneColor(sample.tone), fontSize: '0.7rem', lineHeight: 1.35, marginTop: '6px', overflowWrap: 'anywhere' }}>{sample.failurePatternRef}</div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

function TabButton({ active, onClick, label, icon }: { active: boolean, onClick: () => void, label: string, icon: ReactNode }) {
  return (
    <button onClick={onClick} style={{ padding: '8px 16px', border: 'none', borderRadius: '8px', background: active ? 'var(--accent)' : 'transparent', color: active ? '#000' : '#fff', fontWeight: 600, cursor: 'pointer', transition: 'all 0.2s', display: 'flex', alignItems: 'center', gap: '8px' }}>
      {icon} {label}
    </button>
  )
}

export default App;
