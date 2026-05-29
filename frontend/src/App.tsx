import { useState, useEffect, useRef, type ChangeEvent } from 'react';
import {
  Activity,
  Box,
  LayoutDashboard,
  Compass,
  ShieldAlert,
  Database,
  ClipboardCheck,
  AlertTriangle
} from 'lucide-react';
import './App.css';
import { ComplianceBadge } from './components/ComplianceBadge';
import { CaseOpenAdvisorCard } from './components/CaseOpenAdvisorCard';
import { BCSetupAdvisorCard } from './components/BCSetupAdvisorCard';
import { BCSetupPillList, shouldShowBCSetupAdvisor } from './components/BCSetupPillList';
import { CaseBrowser } from './components/CaseBrowser';
import { type CaeReviewCard } from './components/ChatPanel';
import { ProjectManager } from './components/ProjectManager';
import { ModeSelector } from './components/ModeSelector';
import { ResultMeshPlaybackPanel } from './components/ResultMeshPlaybackPanel';
// FM-04a Phase 29 C — App-root onboarding mounts.
import { OnboardingTour } from './components/OnboardingTour';
import { AdvancedModePromo } from './components/AdvancedModePromo';
import { buildBulletPlateBlueprintSummary } from './bulletPlateBlueprint';
// FM-04a Phase 21 D — most Visual-tab panel imports moved to
// VisualTabPanel.tsx (extraction); App.tsx keeps only the ones
// referenced outside the extracted tab (e.g. ResultMeshPlaybackPanel
// mounted under the Truth-chain area, the Cmd-K palette).
import { CommandPalette } from './components/CommandPalette';
// FM-04a Phase 19 D — extracted Case sidebar (Sidebar.tsx) so the App
// shell stays under ~1900 LOC and the case-rail concerns can be tested
// in isolation. All data-testids preserved.
import { Sidebar, type SidebarCandidateCase } from './components/Sidebar';
// FM-04a Phase 20 D — Topbar + RightRail extractions, continuing the
// shell-decomposition trajectory started in Phase 19 D.
import { Topbar } from './components/Topbar';
// FM-04a Phase 21 D — Visual tab body extracted out of App.tsx.
import { VisualTabPanel } from './components/VisualTabPanel';
// FM-04a Phase 22 C — Narrative + Exploration tab bodies +
// OperatorStatusPanel + TabButton extracted from App.tsx.
import { NarrativeTabPanel } from './components/NarrativeTabPanel';
import { ExplorationTabPanel } from './components/ExplorationTabPanel';
import { OperatorStatusPanel } from './components/OperatorStatusPanel';
import { TabButton } from './components/TabButton';
import { RightRail } from './components/RightRail';
import { useKeyboardShortcuts } from './hooks/useKeyboardShortcuts';
import { type Command } from './commands/registry';
import { FALLBACK_MATERIALS, type MaterialRecord } from './materialsClient';
// FM-04a Phase 25 B — palette + topbar config extracted for LOC discipline.
import {
  buildPaletteCommands,
  buildTopbarMaterialOptions,
} from './state/paletteCommands';
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


// FM-04a Phase 22 C — types moved to ./types/AppTypes. Only the
// subset directly referenced by App.tsx state + handlers is imported
// here; tab-panel components import their own types.
import type {
  CaseMetadata,
  CaseReferenceDetails,
  ReportData,
  ExperimentStatus,
  CopilotAction,
  CopilotActionResult,
  OperatorStatusItem,
  GoldenSampleQueueItem,
  JobStatus,
} from './types/AppTypes';
// FM-04a Phase 26 D — trust strip + 5/7 trust sections + statusTone
// helper extracted to a pure view-model module.
import {
  statusTone as trustCenterStatusTone,
  humanizeStatus as trustCenterHumanizeStatus,
} from './state/trustCenterViewModel';
// FM-04a Phase 29 B — 7 useMemo'd builder calls moved into a custom
// hook so App.tsx doesn't carry ~240 LOC of orchestration. The hook
// preserves granular per-section memoization (Phase 28 D).
import { useTrustSections } from './state/useTrustSections';
// FM-04a Phase 32 B — App-root uiMode + tour-dismissed cluster
// extracted into a custom hook mirroring Phase 31 B's
// useViewportLayout pattern. Partial closure of Phase 31 honest
// gap #7 (App.tsx reducer debt). The remaining ~36 state
// surfaces are deferred to Phase 33+ for safe per-cluster
// extraction.
import { useAppUiMode } from './state/useAppUiMode';
import {
  caseLoadRecoveryOptions,
  connectionLostRecoveryOptions,
  pdfExportRecoveryOptions,
  solverStartRecoveryOptions,
  stopRequestRecoveryOptions,
  uploadRecoveryOptions,
  useUploadErrorRecovery,
} from './state/useUploadErrorRecovery';
import { useSensitivityStudy } from './state/useSensitivityStudy';
import { useBootCaseSelect } from './state/useBootCaseSelect';
import { ErrorCard } from './components/ErrorCard';
const humanizeStatus = trustCenterHumanizeStatus;

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

// FM-04a Phase 28 B — re-exported from state/trustCenterViewModel so
// buildBallisticSection composes it. Local alias preserves existing
// callsites with no churn.

// FM-04a Phase 26 D — re-exported from state/trustCenterViewModel.
// The body lives there so the builders compose it; this alias
// preserves the existing callsites' identifier without churn.
const statusTone = trustCenterStatusTone;

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
  // FM-04a Phase 21 D — surface the material reference returned by
  // /solver/run (Phase 20 A wired the route end-to-end but no UI
  // consumer existed; reviewers couldn't see which material was
  // actually used after pressing Run Solver). Cleared on each run start.
  const [lastSolverMaterialReference, setLastSolverMaterialReference] =
    useState<string | null>(null);
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
    // FM-04a Phase 36 B — FormData rebuilds inside the closure so
    // Retry sends a fresh request body (FormData stream is one-shot).
    const matchedCaseId = caseId ??
        availableCases.find(c => f.name.toLowerCase().includes(c.id.toLowerCase().replace("-","")))?.id;
    const data = await withUploadRecovery(async () => {
      const formData = new FormData();
      formData.append('file', f);
      if (matchedCaseId) formData.append('case_id', matchedCaseId);
      const response = await fetch(`${API_BASE}/report/generate`, {
        method: 'POST',
        body: formData,
      });
      if (!response.ok) throw new Error(`upload HTTP ${response.status}`);
      return response.json();
    }, uploadRecoveryOptions(f.name));
    if (data && data.success) setReport(data);
    setLoading(false);
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

    // FM-04a Phase 36 B — FormData must rebuild inside the
    // withUploadRecovery closure so the Retry callback sends a
    // fresh request body (the FormData stream is consumed once
    // per submit; reusing the same instance would break Retry).
    const data = await withUploadRecovery(async () => {
      const formData = new FormData();
      formData.append('case_id', c.id);
      formData.append('file', new File(["dummy"], "dummy.frd"));
      const response = await fetch(`${API_BASE}/report/generate`, {
        method: 'POST',
        body: formData,
      });
      if (!response.ok) throw new Error(`case-load HTTP ${response.status}`);
      return response.json();
    }, caseLoadRecoveryOptions(c.id));
    if (data && data.success) setReport(data);
    setLoading(false);
  };

  useBootCaseSelect(availableCases, activeCaseId, Boolean(file || report), selectedCandidateCaseId ?? FALLBACK_CANDIDATE_CASES[0]?.caseId ?? null, selectCase);

  const runSolver = async () => {
    if (!activeCaseId) return;
    const caseIdForRun = activeCaseId;
    setSolving(true);
    setLogs([]);
    setShowConsole(true);
    setCurrentJobId(null);
    setCurrentJobStatus('starting');
    setCurrentJobAnalysis(analysisType);
    setLastSolverMaterialReference(null);
    // FM-04a Phase 37 C — withUploadRecovery surfaces solver-start
    // failures via ErrorCard alongside the existing [ERROR] log
    // line (closes 5th of 5 silent paths; Phase 36 D friction
    // point c).
    const data = await withUploadRecovery(async () => {
      const response = await fetch(`${API_BASE}/solver/run`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          case_id: caseIdForRun,
          analysis_type: analysisType,
          num_modes: 5,
          material_id: selectedMaterial.id,
        }),
      });
      const body = await response.json().catch(() => ({}));
      if (!response.ok) {
        const detail = typeof body.detail === 'string' ? body.detail : `HTTP ${response.status}`;
        throw new Error(detail);
      }
      if (!body.job_id) throw new Error('missing job id');
      return body;
    }, solverStartRecoveryOptions(caseIdForRun));
    if (!data) {
      setLogs(prev => [...prev, '[ERROR] Solver start failed (see workbench banner)']);
      setCurrentJobStatus('failed');
      setSolving(false);
      return;
    }
    setCurrentJobId(data.job_id);
    setCurrentJobStatus('running');
    if (typeof data.material_reference === 'string' && data.material_reference) {
      setLastSolverMaterialReference(data.material_reference);
      setLogs(prev => [...prev, `[REF] material: ${data.material_reference}`]);
    }
    connectToLogs(data.job_id);
  };

  const downloadPDFReport = async () => {
    if (!activeCaseId) return;
    setLoading(true);
    // FM-04a Phase 36 A — replaces crude alert("Failed to export
    // PDF: ") with the Phase 35 C ErrorCard surface + retry.
    await withUploadRecovery(async () => {
      const response = await fetch(`${API_BASE}/report/export/pdf/${activeCaseId}`);
      if (!response.ok) throw new Error(`PDF export HTTP ${response.status}`);
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `Report_${activeCaseId}.pdf`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
    }, pdfExportRecoveryOptions(activeCaseId));
    setLoading(false);
  };

  const stopSolver = async () => {
    if (!currentJobId) return;
    const jobId = currentJobId;
    setLogs(prev => [...prev, "[SYSTEM] Requesting stop..."]);
    setCurrentJobStatus('stop_requested');
    // FM-04a Phase 36 A — wrap the stop-request fetch in
    // withUploadRecovery so a failure surfaces an ErrorCard
    // alongside the existing console log (was silent pre-36 A).
    const ok = await withUploadRecovery(async () => {
      const response = await fetch(`${API_BASE}/solver/stop/${jobId}`, { method: 'POST' });
      if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        const detail = typeof data.detail === 'string' ? `: ${data.detail}` : '';
        throw new Error(`stop-request HTTP ${response.status}${detail}`);
      }
      return true;
    }, stopRequestRecoveryOptions(jobId));
    if (ok) {
      setLogs(prev => [...prev, "[SYSTEM] Stop request accepted."]);
      setCurrentJobStatus('stopped');
      setSolving(false);
    } else {
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
      // FM-04a Phase 39 A — surface a recovery ErrorCard (was silent: only the
      // console log above). Live-job context, so call setUploadError directly
      // (not the async withRecovery wrapper); Retry reconnects to the same
      // job's log stream. Closes the novice WS-death finding — the 6th/last
      // silent error-recovery path.
      setUploadError({
        ...connectionLostRecoveryOptions(jobId),
        onRetry: () => { clearUploadError(); connectToLogs(jobId); },
      });
    };
  };

  // FM-04a Phase 38 I — sensitivity-study run + poll flow lives in the
  // useSensitivityStudy hook (closes eval finding #6: silent study errors
  // + stuck `loading`). `handleRunStudy` is sourced from that hook call
  // alongside the other recovery wiring (see below).

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
  // FM-04a Phase 38 I (Codex R1 P3) — a terminally FAILED sweep must read as
  // a warning, not the healthy accent, even though activeExperiment is set.
  const studyFailed = activeExperiment?.status === 'FAILED';
  const runStateTone =
    studyFailed ||
    currentJobStatus === 'failed' ||
    currentJobStatus === 'connection_lost'
      ? 'warning'
      : solving || activeExperiment
        ? 'accent'
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
  // FM-04a Phase 29 C — App-root uiMode + tour-dismissed state.
  // FM-04a Phase 32 B — extracted into useAppUiMode hook to close
  // part of the App.tsx reducer debt (Phase 31 honest gap #7).
  // The OnboardingTour + AdvancedModePromo mount at App-root so
  // tabs other than Visual receive onboarding; uiMode is
  // forwarded to ResultMeshPlaybackPanel via the optional
  // `uiMode` prop so the panel honors the same state.
  const {
    state: { appUiMode, appTourDismissedInSession },
    actions: { handleAppUiModeChange, markTourDismissedInSession },
  } = useAppUiMode();

  // FM-04a Phase 35 C — upload/case-load ErrorCard surface; hook
  // absorbs state + retry so App.tsx stays under the <1500 pin.
  const {
    state: { uploadError },
    actions: {
      withRecovery: withUploadRecovery,
      setUploadError,
      clearUploadError,
    },
  } = useUploadErrorRecovery();

  // FM-04a Phase 38 I — sensitivity-study run/poll flow (eval finding #6).
  // Routes both start and poll/run failures through the shared ErrorCard
  // recovery surface above, and stops polling on a failed run so `loading`
  // never hangs.
  const { handleRunStudy, pollExperiment } = useSensitivityStudy({
    apiBase: API_BASE,
    activeCaseId,
    setLoading,
    setActiveExperiment,
    onComplete: () => setActiveTab('visual'),
    appendLog: (line) => setLogs((prev) => [...prev, line]),
    withRecovery: withUploadRecovery,
    setUploadError,
    clearUploadError,
  });

  // FM-04a Phase 29 B — useTrustSections custom hook encapsulates
  // the 7-section build with granular per-section memoization
  // (Phase 28 D semantics preserved). Replaces ~240 LOC of inline
  // useMemo orchestration with a single hook call. App.tsx LOC
  // delta vs Phase 28 D: target -200 (1596 → ~1396).
  const { trustStrip, sections: trustSections } = useTrustSections({
    claimTier,
    allowedClaim,
    solverTruthSource,
    candidateSpine,
    currentJobId,
    executionMode,
    report,
    reportValidationStatus,
    referenceStatusRaw,
    goldenSampleSummary,
    goldenSampleReviewCount,
    blueprintSummary,
    overviewIcon: <LayoutDashboard size={16} />,
    runtimeIcon: <Database size={16} />,
    evidenceIcon: <ClipboardCheck size={16} />,
    validationIcon: <ShieldAlert size={16} />,
    blueprintIcon: <ClipboardCheck size={16} />,
    ballisticIcon: <ShieldAlert size={16} />,
    gateIcon: <AlertTriangle size={16} />,
    activeCaseId,
    file,
    caseLabel,
    nextAction,
    analysisModeLabel,
    currentJobLabel,
    lastSolverMaterialReference,
    runState,
    runStateTone,
    latestEvent,
    solverLogSummary,
    solverLogState,
    convergenceSummary,
    candidateConvergenceEvidence,
    convergenceClaimImpact,
    evidenceState,
    manifestState,
    candidateManifest,
    backendProvenance,
    meshArtifactSource,
    candidateMeshEvidence,
    convergenceArtifactList,
    meshConvergenceStudySource,
    meshConvergenceStudy,
    meshConvergenceClaimImpact,
    referenceStatus,
    referenceReason,
    referenceDeviation,
    unitSummary,
    candidateAssumptions,
    materialSummary,
    boundarySummary,
    meshTopologySummary,
    meshDeckElementTypes,
    meshQualitySummary,
    meshClaimImpact,
    meshConvergenceStudySummary,
    convergenceMissingSummary,
    failurePatternRef,
    candidateBallistic,
    ballisticInitialVelocitySummary,
    ballisticResidualVelocitySummary,
    ballisticPerforationSummary,
    ballisticPerforationTone,
    ballisticEnergySummary,
    ballisticEnergyTone,
    ballisticAnimationSummary,
    ballisticTimeStepStudySummary,
    ballisticTimeStepStudyTone,
    ballisticTimeStepStudy,
    ballisticTier2BlockerSummary,
    reviewerSummary,
    candidateReviewer,
    candidateLimitations,
    tier2BlockerSummary,
  });
  // FM-04a Phase 29 B — Phase 28 D inline useMemo block removed;
  // replaced by useTrustSections hook above. Net LOC delta: -240.
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
  const commands: Command[] = buildPaletteCommands({
    setActiveTab,
    runSolverFromPalette: _runSolverFromPalette,
    pickMaterialByIndex: (i) => setSelectedMaterial(FALLBACK_MATERIALS[i]),
    openMaterialPickerPanel: () => {
      if (typeof document === 'undefined') return;
      const target = document.getElementById('material-picker-panel');
      target?.scrollIntoView({ behavior: 'smooth', block: 'center' });
    },
    closePalette: () => setPaletteOpen(false),
    activeCaseId,
    materials: FALLBACK_MATERIALS,
  });
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
    <div className="app-container" style={{ display: 'grid', gridTemplateColumns: '210px 300px 1fr', height: '100vh' }}>
      {/* FM-04a Phase 29 C — onboarding tour + advanced-mode auto-
          promote mounted at App-root so reviewers landing on the
          Narrative tab (or any future tab) still see onboarding.
          Phase 28 D's prior mount was inside ResultMeshPlaybackPanel
          and the Visual-tab-only coupling was flagged by the UX
          audit. The promo's visibility is fully self-gated by its
          storage predicate; uiMode lives in App-root via
          appUiModeStorage / appUiMode below. */}
      <OnboardingTour onDismissed={markTourDismissedInSession} />
      <AdvancedModePromo
        uiMode={appUiMode}
        tourDismissedInSession={appTourDismissedInSession}
        onSwitchToAdvanced={() => handleAppUiModeChange('advanced')}
      />
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

      {/* Case Sidebar — extracted to Sidebar.tsx in Phase 19 D */}
      <Sidebar
        availableCases={availableCases}
        candidateCases={FALLBACK_CANDIDATE_CASES.map<SidebarCandidateCase>((c) => ({
          caseId: c.caseId,
          displayLabel: c.displayLabel ?? c.caseId,
        }))}
        selectedCandidateCaseId={selectedCandidateCaseId}
        onSelectCandidateCase={(id) => {
          setSelectedCandidateCaseId(id)
          // Phase 20 E (round 1 → round 2 fix) — close the state-
          // divergence defect the UX agent flagged: selecting a
          // candidate previously left `activeCaseId` null so the
          // Topbar's Run Solver button stayed hidden. Unify the
          // selection now so the Phase 20 A material_id route flow
          // (which keys on `activeCaseId`) is reachable end-to-end
          // from the Sidebar candidate roster click.
          setActiveCaseId(id)
          try {
            window.localStorage.setItem('fm04a.candidateCaseId', id)
          } catch {
            /* no-op when storage is unavailable */
          }
        }}
        activeCaseId={activeCaseId}
        onSelectCase={(c) => selectCase(c)}
        activeExperiment={activeExperiment}
        onFileUpload={handleFileUpload}
        onOpenPalette={() => setPaletteOpen(true)}
      />

      {/* Main Content Area */}
      <div style={{ display: 'grid', gridTemplateColumns: showChat ? '1fr 340px' : '1fr', height: '100vh', overflow: 'hidden' }}>
        <main style={{ overflowY: 'auto', background: 'var(--bg-base)', position: 'relative', display: 'flex', flexDirection: 'column' }}>
            <Topbar
              breadcrumbLabel={activeCaseId || (file ? file.name : "Session")}
              badge={report && <ComplianceBadge status={report.metrics.status} standard="GB50017" />}
              showRunControls={Boolean(activeCaseId)}
              analysisType={analysisType}
              onChangeAnalysisType={setAnalysisType}
              solving={solving}
              onRunSolver={runSolver}
              onStopSolver={stopSolver}
              showChat={showChat}
              onToggleChat={() => setShowChat(!showChat)}
              materialReference={lastSolverMaterialReference}
              materialOptions={buildTopbarMaterialOptions(FALLBACK_MATERIALS)}
              selectedMaterialId={selectedMaterial.id}
              onChangeMaterialId={(id) => {
                const found = FALLBACK_MATERIALS.find((m) => m.id === id);
                if (found) setSelectedMaterial(found);
              }}
            />

            {/* FM-04a Phase 41.2 — demo-first: case + 3D viewport lead; the
                trust panel is authored DOM-last (below) so visual + focus order
                agree (Codex R0 P2). ErrorCard stays first for failure visibility. */}
            <div style={{ padding: '40px', flex: 1 }}>
            {/* FM-04a Phase 36 B — ErrorCard mounts ABOVE
                OperatorStatusPanel so a failed user sees the red
                error band before the trust prose (Phase 35 R3
                friction point b). */}
            {uploadError && (
                <div data-testid="app-upload-error-mount" style={{ marginBottom: '24px', order: 0 }}>
                    <ErrorCard {...uploadError} />
                </div>
            )}

            {/* FM-04a Phase 37 A — CaseBrowser canonical surface, browse mode. */}
            {!activeCaseId && (
                <div className="rise-in" style={{ marginBottom: '24px' }}>
                    <CaseBrowser cases={FALLBACK_CANDIDATE_CASES} focusedCaseId={selectedCandidateCaseId} onSelectCase={(caseId) => setSelectedCandidateCaseId(caseId)} />
                </div>
            )}

            <div className="tab-pill-bar" style={{ marginBottom: '32px' }}>
                <TabButton active={activeTab === 'visual'} onClick={() => setActiveTab('visual')} label="3D Scene" icon={<Box size={16} />} />
                <TabButton active={activeTab === 'report'} onClick={() => setActiveTab('report')} label="Narrative" icon={<Activity size={16} />} />
                {activeCaseId && <TabButton active={activeTab === 'explore'} onClick={() => setActiveTab('explore')} label="Exploration" icon={<Compass size={16} />} />}
            </div>

            <div style={{ padding: '0', flex: 1 }}>
                {activeTab === 'explore' ? (
                    <ExplorationTabPanel
                        activeCaseId={activeCaseId!}
                        loading={loading}
                        activeExperiment={activeExperiment}
                        comparedIndices={comparedIndices}
                        onCompareIndex={(i) => {
                            if (comparedIndices) {
                                if (comparedIndices[0] === i) {
                                    setComparedIndices(null);
                                } else {
                                    setComparedIndices([comparedIndices[0], i]);
                                }
                            } else {
                                setComparedIndices([i, -1]);
                            }
                        }}
                        onRunStudy={handleRunStudy}
                    />
                ) : (
                    <>
                    {loading ? (
                        <div className="shimmer-active" style={{ height: '400px', width: '100%', borderRadius: '12px', background: 'var(--bg-surface)' }}></div>
                    ) : report ? (
                        <div className="rise-in" style={{ display: 'flex', flexDirection: 'column', gap: '32px' }}>
                            <div className={activeTab === 'visual' && activeCaseId ? 'viewport-hero' : 'glass-panel'} style={{ minHeight: activeTab === 'visual' && activeCaseId ? '820px' : '600px', padding: '0', overflow: 'hidden' }}>
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
                                            uiMode={appUiMode}
                                            onUiModeChange={handleAppUiModeChange}
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
                                    <NarrativeTabPanel
                                        report={report}
                                        onDownloadPDF={downloadPDFReport}
                                    />
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

            {/* FM-04a Phase 41.4 — 3D-first: advisor guidance + the VisualTabPanel governance/evidence wall are demoted BELOW the 3D viewport (were above it) so the result visualization leads the visual tab. */}
            {activeCaseId && (() => {
                // FM-04a Phase 37 B — pair BCSetupAdvisorCard with CaseOpenAdvisorCard (3rd advisor surface; closes Dim 4 80-anchor 3-stage sub-bullet).
                const caseOpenRecord = findCandidateCase(FALLBACK_CANDIDATE_CASES, activeCaseId);
                return caseOpenRecord ? (
                    <div className="rise-in" style={{ marginTop: '32px', marginBottom: '24px', display: 'flex', flexDirection: 'row', flexWrap: 'wrap', gap: '12px' }}>
                        <CaseOpenAdvisorCard caseRecord={caseOpenRecord} />
                        {shouldShowBCSetupAdvisor(caseOpenRecord) && <BCSetupAdvisorCard caseRecord={caseOpenRecord} />}
                        <BCSetupPillList caseRecord={caseOpenRecord} />
                    </div>
                ) : null;
            })()}

            {activeTab === 'visual' && (
                <VisualTabPanel
                    apiBase={API_BASE}
                    selectedCandidateCaseId={selectedCandidateCaseId}
                    onSelectCandidateCaseId={setSelectedCandidateCaseId}
                    comparisonCaseA={comparisonCaseA}
                    comparisonCaseB={comparisonCaseB}
                    onSelectComparisonA={setComparisonCaseA}
                    onSelectComparisonB={setComparisonCaseB}
                    snapshotLabelA={snapshotLabelA}
                    snapshotLabelB={snapshotLabelB}
                    onSelectSnapshotLabelA={setSnapshotLabelA}
                    onSelectSnapshotLabelB={setSnapshotLabelB}
                    selectedMaterial={selectedMaterial}
                    onMaterialChange={setSelectedMaterial}
                    latestSignoff={latestSignoff}
                    onLatestSignoff={setLatestSignoff}
                />
            )}

            {/* Evidence & trust center — DOM-last (see top-of-container note). */}
            <div style={{ marginTop: '32px' }}>
            <OperatorStatusPanel
              strip={trustStrip}
              sections={trustSections}
              goldenSamples={goldenSampleQueue}
            />
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

        <RightRail
            showChat={showChat}
            caseId={activeCaseId}
            onExecuteAction={handleExecuteCopilotAction}
            reviewCards={caeReviewCards}
            claimTier={claimTier}
            allowedClaim={allowedClaim}
        />
      </div>
    </div>
  );
}

export default App;
