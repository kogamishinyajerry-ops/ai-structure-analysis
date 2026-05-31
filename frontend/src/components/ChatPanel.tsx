import { useState, useRef, useEffect } from 'react';
import { Send, Bot, User, Check, X, Sparkles, MessageSquare, ShieldAlert, FileText, Wrench } from 'lucide-react';

interface Action {
  action_type: string;
  parameters: Record<string, unknown>;
  description: string;
}

interface ExecuteActionResult {
  message?: string;
}

export interface CaeReviewCard {
  card_type: string;
  severity: 'info' | 'warning' | 'critical';
  finding: string;
  evidence: string;
  recommended_action: string;
  claim_impact: string;
}

interface Message {
  role: 'user' | 'assistant';
  content: string;
  proposedAction?: Action;
  executed?: boolean;
}

interface ChatPanelProps {
  caseId: string | null;
  onExecuteAction: (action: Action) => Promise<ExecuteActionResult>;
  reviewCards?: CaeReviewCard[];
  claimTier?: string;
  allowedClaim?: string;
}

type CopilotTab = 'command' | 'review' | 'evidence' | 'fix';

export function ChatPanel({
  caseId,
  onExecuteAction,
  reviewCards = [],
  claimTier = 'Tier 0 sandbox/demo',
  allowedClaim = 'demo-only / software-path evidence only',
}: ChatPanelProps) {
  const [messages, setMessages] = useState<Message[]>([
    { role: 'assistant', content: 'Trust-aware AI engineer online. I can run commands, review claim boundaries, and propose the next safe action for this case.' }
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState<CopilotTab>('command');
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (caseId) {
      fetch(`http://localhost:8000/api/v1/history/${caseId}`)
        .then(res => res.json())
        .then(data => {
            if (data && data.length > 0) {
                setMessages(data);
            }
        })
        .catch(err => console.error("History fetch failed", err));
    }
  }, [caseId]);

  useEffect(() => {
    scrollRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSend = async () => {
    if (!input.trim() || loading) return;
    
    const userText = input;
    setInput('');
    setMessages(prev => [...prev, { role: 'user', content: userText }]);
    setLoading(true);

    try {
      const res = await fetch('http://localhost:8000/api/v1/parse-nl', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: userText, context: { case_id: caseId } })
      });
      const data = await res.json();
      
      let assistantMsg: Message = { role: 'assistant', content: "I couldn't quite understand that. Try instructions like 'Run a study' or 'Show stress'." };
      
      if (data.success && data.actions && data.actions.length > 0) {
        const action = data.actions[0];
        assistantMsg = {
          role: 'assistant',
          content: `I've analyzed your request: ${action.description}. Do you want me to proceed?`,
          proposedAction: action
        };
      } else if (data.success) {
          assistantMsg = { role: 'assistant', content: `Parsing successful, but no executable action was found for intent: ${data.intent}.` };
      }

      setMessages(prev => [...prev, assistantMsg]);
    } catch {
      setMessages(prev => [...prev, { role: 'assistant', content: "Sorry, I had trouble connecting to the brain." }]);
    } finally {
      setLoading(false);
    }
  };

  const confirmAction = async (msgIndex: number, action: Action) => {
    setLoading(true);
    const result = await onExecuteAction(action);
    setMessages(prev => prev.map((m, i) => i === msgIndex ? { ...m, executed: true, content: `Action executed successfully: ${result.message || 'Complete'}` } : m));
    setLoading(false);
  };

  const cardsForTab = reviewCards.filter((card) => {
    if (activeTab === 'review') return ['blueprint_target', 'reference_validation', 'mesh_quality', 'mesh_convergence_study', 'convergence_evidence', 'golden_sample_status', 'ballistic_candidate', 'ballistic_perforation', 'time_step_convergence_study', 'energy_balance_status', 'convergence_study_status', 'candidate_case_selection'].includes(card.card_type);
    if (activeTab === 'evidence') return ['blueprint_target', 'claim_boundary', 'evidence_packet', 'solver_truth', 'assumptions', 'mesh_quality', 'mesh_convergence_study', 'convergence_evidence', 'ballistic_candidate', 'time_step_convergence_study', 'energy_balance_status', 'convergence_study_status', 'candidate_case_selection'].includes(card.card_type);
    if (activeTab === 'fix') return true;
    return false;
  });

  const severityColor = (severity: CaeReviewCard['severity']) => {
    if (severity === 'critical') return 'var(--danger-400)';
    if (severity === 'warning') return 'var(--warn-400)';
    return 'var(--accent)';
  };

  const renderReviewCards = () => (
    <div style={{ flex: 1, overflowY: 'auto', padding: 'var(--sp-4)', display: 'flex', flexDirection: 'column', gap: 'var(--sp-3)' }}>
      <div style={{ display: 'grid', gap: 'var(--sp-2)' }}>
        <div style={{ padding: 'var(--sp-3)', borderRadius: 'var(--r-sm)', border: '1px solid var(--border)', background: 'var(--c-50)' }}>
          <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 700, marginBottom: '6px' }}>Current claim boundary</div>
          <div style={{ color: 'var(--warn-400)', fontSize: '0.84rem', fontWeight: 700 }}>{claimTier}</div>
          <div style={{ color: 'var(--text-secondary)', fontSize: '0.78rem', marginTop: '6px', lineHeight: 1.4 }}>{allowedClaim}</div>
        </div>
      </div>

      {cardsForTab.length === 0 ? (
        <div style={{ color: 'var(--text-muted)', fontSize: 'var(--fs-sm)', lineHeight: 1.45, padding: 'var(--sp-3)' }}>
          No structured card is available for this view yet. Load a case or run/report a solver path before promoting evidence.
        </div>
      ) : (
        cardsForTab.map((card) => (
          <div key={`${card.card_type}-${card.finding}`} style={{ padding: '14px', borderRadius: 'var(--r-sm)', border: `1px solid ${severityColor(card.severity)}`, background: 'var(--c-50)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', gap: 'var(--sp-3)', alignItems: 'center', marginBottom: 'var(--sp-2)' }}>
              <div style={{ fontSize: '0.68rem', color: severityColor(card.severity), textTransform: 'uppercase', fontWeight: 800 }}>{card.card_type.replace(/_/g, ' ')}</div>
              <div style={{ color: severityColor(card.severity), fontSize: '0.68rem', fontWeight: 800 }}>{card.severity}</div>
            </div>
            <div style={{ fontSize: '0.84rem', color: 'var(--text-primary)', fontWeight: 700, lineHeight: 1.35 }}>{card.finding}</div>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: 'var(--sp-2)', lineHeight: 1.45 }}>
              <strong style={{ color: 'var(--text-primary)' }}>Evidence:</strong> {card.evidence}
            </div>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: '6px', lineHeight: 1.45 }}>
              <strong style={{ color: 'var(--text-primary)' }}>Action:</strong> {card.recommended_action}
            </div>
            <div style={{ fontSize: '0.75rem', color: 'var(--warn-400)', marginTop: '6px', lineHeight: 1.45 }}>
              {card.claim_impact}
            </div>
          </div>
        ))
      )}
    </div>
  );

  return (
    <div className="glass-panel" style={{ height: '100%', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
      <div style={{ padding: 'var(--sp-4)', borderBottom: '1px solid var(--border)', display: 'flex', flexDirection: 'column', gap: 'var(--sp-3)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--sp-2)' }}>
          <MessageSquare size={18} color="var(--accent)" />
          <h3 style={{ margin: 0, fontSize: '0.9rem' }}>Trust-aware AI Engineer</h3>
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '6px' }}>
          {[
            { id: 'command', label: 'Command', icon: <MessageSquare size={12} /> },
            { id: 'review', label: 'Review', icon: <ShieldAlert size={12} /> },
            { id: 'evidence', label: 'Evidence', icon: <FileText size={12} /> },
            { id: 'fix', label: 'Fix Plan', icon: <Wrench size={12} /> },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as CopilotTab)}
              style={{
                minWidth: 0,
                padding: '7px 6px',
                borderRadius: '6px',
                border: '1px solid var(--border)',
                background: activeTab === tab.id ? 'var(--accent)' : 'var(--c-50)',
                color: activeTab === tab.id ? '#fff' : 'var(--text-secondary)',
                fontSize: '0.68rem',
                fontWeight: 800,
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: 'var(--sp-1)',
              }}
            >
              {tab.icon}
              <span>{tab.label}</span>
            </button>
          ))}
        </div>
      </div>

      {activeTab === 'command' ? (
      <div style={{ flex: 1, overflowY: 'auto', padding: 'var(--sp-4)', display: 'flex', flexDirection: 'column', gap: 'var(--sp-4)' }}>
        {messages.map((m, i) => (
          <div key={i} style={{ display: 'flex', gap: '10px', alignSelf: m.role === 'user' ? 'flex-end' : 'flex-start', maxWidth: '85%' }}>
            {m.role === 'assistant' && <div style={{ minWidth: '32px', height: '32px', borderRadius: '50%', background: 'var(--accent-glow)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}><Bot size={16} color="var(--accent)" /></div>}
            <div style={{ background: m.role === 'user' ? 'var(--accent)' : 'var(--c-100)', color: m.role === 'user' ? '#fff' : 'var(--text-primary)', padding: 'var(--sp-3)', borderRadius: 'var(--r-md)', fontSize: '0.85rem', lineHeight: '1.4' }}>
              {m.content}
              
              {m.proposedAction && !m.executed && (
                <div style={{ marginTop: 'var(--sp-3)', padding: 'var(--sp-3)', background: 'var(--c-200)', borderRadius: 'var(--r-sm)', border: '1px solid var(--border)' }}>
                   <div style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--accent)', marginBottom: 'var(--sp-2)', display: 'flex', alignItems: 'center', gap: 'var(--sp-1)' }}>
                      <Sparkles size={12} /> PROPOSED ACTION
                   </div>
                   <p style={{ margin: '0 0 var(--sp-3) 0', fontSize: '0.75rem', color: 'var(--text-muted)' }}>{m.proposedAction.description}</p>
                   <div style={{ display: 'flex', gap: 'var(--sp-2)' }}>
                     <button 
                       onClick={() => confirmAction(i, m.proposedAction!)}
                       style={{ flex: 1, padding: '6px', background: 'var(--accent)', color: '#fff', border: 'none', borderRadius: '4px', fontSize: '0.7rem', fontWeight: 700, cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 'var(--sp-1)' }}
                     >
                       <Check size={12} /> Confirm
                     </button>
                     <button style={{ flex: 1, padding: '6px', background: 'transparent', color: 'var(--danger-400)', border: '1px solid rgba(197, 69, 59, 0.30)', borderRadius: '4px', fontSize: '0.7rem', cursor: 'pointer' }}>
                       <X size={12} /> Cancel
                     </button>
                   </div>
                </div>
              )}
            </div>
            {m.role === 'user' && <div style={{ minWidth: '32px', height: '32px', borderRadius: '50%', background: 'var(--c-100)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}><User size={16} /></div>}
          </div>
        ))}
        <div ref={scrollRef} />
      </div>
      ) : renderReviewCards()}

      {activeTab === 'command' && (
      <div style={{ padding: 'var(--sp-4)', borderTop: '1px solid var(--border)', background: 'var(--c-50)' }}>
        <div style={{ position: 'relative' }}>
          <input 
            type="text" 
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSend()}
            placeholder="Ask copilot to run a study..."
            style={{ width: '100%', padding: 'var(--sp-3) var(--sp-10) var(--sp-3) var(--sp-3)', borderRadius: 'var(--r-sm)', background: 'var(--bg-base)', border: '1px solid var(--border)', color: 'var(--text-primary)', fontSize: '0.85rem' }}
          />
          <button 
             onClick={handleSend}
             style={{ position: 'absolute', right: '8px', top: '50%', transform: 'translateY(-50%)', background: 'transparent', border: 'none', color: 'var(--accent)', cursor: 'pointer' }}
          >
            {loading ? <Loader2 size={18} className="animate-spin" /> : <Send size={18} />}
          </button>
        </div>
      </div>
      )}
    </div>
  );
}

function Loader2({ size, className }: { size: number, className: string }) {
    return <div className={className} style={{ width: size, height: size, border: '2px solid currentColor', borderTopColor: 'transparent', borderRadius: '50%' }} />
}
