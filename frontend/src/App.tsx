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
  Download
} from 'lucide-react';
import './App.css';
import { SensitivityForm } from './components/SensitivityForm';
import { ComplianceBadge } from './components/ComplianceBadge';
import { ChatPanel } from './components/ChatPanel';
import { ProjectManager } from './components/ProjectManager';
import { ModeSelector } from './components/ModeSelector';


// --- Types ---
interface CaseMetadata {
  id: string;
  name: string;
  description: string;
  type: string;
  structure: string;
  frd_path: string;
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
  increments?: {
    index: number;
    step: number;
    type: string;
    value: number;
    max_displacement: number;
    max_von_mises: number;
  }[];
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

const API_BASE = "http://localhost:8000/api/v1";
const WS_BASE = "ws://localhost:8000/api/v1";

function App() {
  const [file, setFile] = useState<File | null>(null);
  const [activeCaseId, setActiveCaseId] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [report, setReport] = useState<ReportData | null>(null);
  const [activeTab, setActiveTab] = useState<'visual' | 'report' | 'explore'>('visual');
  const [availableCases, setAvailableCases] = useState<CaseMetadata[]>([]);
  const [selectedProjectId, setSelectedProjectId] = useState<number | null>(null);
  const [analysisType, setAnalysisType] = useState<'static' | 'modal' | 'buckling'>('static');
  const [selectedModeIndex, setSelectedModeIndex] = useState(0);
  
  // Solver & Explorer State
  const [solving, setSolving] = useState(false);
  const [logs, setLogs] = useState<string[]>([]);
  const [showConsole, setShowConsole] = useState(false);
  const [showChat, setShowChat] = useState(false);
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

  // Auto-scroll terminal
  useEffect(() => {
    terminalEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [logs]);

  const handleFileUpload = async (e: ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const selectedFile = e.target.files[0];
      setFile(selectedFile);
      setActiveCaseId(null);
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

  const selectCase = async (c: CaseMetadata) => {
    setLoading(true);
    setFile(null);
    setActiveCaseId(c.id);
    setActiveExperiment(null);
    setComparedIndices(null);
    
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
    
    try {
      const response = await fetch(`${API_BASE}/solver/run`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          case_id: activeCaseId,
          analysis_type: analysisType,
          num_modes: 5
        }),
      });
      const data = await response.json();
      if (data.job_id) {
        connectToLogs(data.job_id);
      }
    } catch (err) {
      console.error("Solver start failed", err);
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
    // 假设我们存储了当前的 jobId，或者从 logs/status 中获取
    // 这里简化处理，通过解析 logs 最后的 job_id 或状态获取
    const lastJobLog = logs.find(l => l.includes("Starting Solver Job"));
    if (!lastJobLog) return;
    
    setLogs(prev => [...prev, "[SYSTEM] Requesting stop..."]);
    // 提取 jobId
    const jobId = lastJobLog.split("Job ")[1].split(":")[0];
    
    try {
      await fetch(`${API_BASE}/solver/stop/${jobId}`, { method: 'POST' });
    } catch (err) {
      console.error("Stop failed", err);
    }
  };

  const connectToLogs = (jobId: string) => {
    const ws = new WebSocket(`${WS_BASE}/solver/ws/logs/${jobId}`);
    ws.onmessage = (event) => {
      setLogs(prev => [...prev, event.data]);
      if (event.data.includes("--- Process Finished")) {
        setSolving(false);
        if (event.data.includes("status: COMPLETED")) {
            setTimeout(() => {
                if (activeCaseId) {
                   const matchedCase = availableCases.find(c => c.id === activeCaseId);
                   if (matchedCase) selectCase(matchedCase);
                }
            }, 1000);
        }
      }
    };
    ws.onerror = () => {
      setLogs(prev => [...prev, "[ERROR] WebSocket connection died"]);
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

  return (
    <div className="app-container" style={{ display: 'grid', gridTemplateColumns: '240px 300px 1fr', height: '100vh' }}>
      
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
            <div className="glass-panel" style={{ padding: '8px', display: 'flex', gap: '8px', width: 'fit-content', marginBottom: '32px' }}>
                <TabButton active={activeTab === 'visual'} onClick={() => setActiveTab('visual')} label="3D Scene" icon={<Box size={16} />} />
                <TabButton active={activeTab === 'report'} onClick={() => setActiveTab('report')} label="Narrative" icon={<Activity size={16} />} />
                {activeCaseId && <TabButton active={activeTab === 'explore'} onClick={() => setActiveTab('explore')} label="Exploration" icon={<Compass size={16} />} />}
            </div>

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
                            <div className="glass-panel" style={{ minHeight: '600px', padding: '0', overflow: 'hidden' }}>
                                {activeTab === 'visual' ? (
                                    <div style={{ position: 'relative', width: '100%', height: '600px' }}>
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
                <ChatPanel caseId={activeCaseId} onExecuteAction={handleExecuteCopilotAction} />
            </aside>
        )}
      </div>
    </div>
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
