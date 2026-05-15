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
    if (activeTab === 'review') return ['blueprint_target', 'reference_validation', 'mesh_quality', 'mesh_convergence_study', 'convergence_evidence', 'golden_sample_status', 'ballistic_candidate', 'ballistic_perforation', 'time_step_convergence_study'].includes(card.card_type);
    if (activeTab === 'evidence') return ['blueprint_target', 'claim_boundary', 'evidence_packet', 'solver_truth', 'assumptions', 'mesh_quality', 'mesh_convergence_study', 'convergence_evidence', 'ballistic_candidate', 'time_step_convergence_study'].includes(card.card_type);
    if (activeTab === 'fix') return true;
    return false;
  });

  const severityColor = (severity: CaeReviewCard['severity']) => {
    if (severity === 'critical') return '#ef4444';
    if (severity === 'warning') return '#f59e0b';
    return 'var(--accent)';
  };

  const renderReviewCards = () => (
    <div style={{ flex: 1, overflowY: 'auto', padding: '16px', display: 'flex', flexDirection: 'column', gap: '12px' }}>
      <div style={{ display: 'grid', gap: '8px' }}>
        <div style={{ padding: '12px', borderRadius: '8px', border: '1px solid var(--border)', background: 'rgba(15, 23, 42, 0.65)' }}>
          <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 700, marginBottom: '6px' }}>Current claim boundary</div>
          <div style={{ color: '#f59e0b', fontSize: '0.84rem', fontWeight: 700 }}>{claimTier}</div>
          <div style={{ color: 'var(--text-secondary)', fontSize: '0.78rem', marginTop: '6px', lineHeight: 1.4 }}>{allowedClaim}</div>
        </div>
      </div>

      {cardsForTab.length === 0 ? (
        <div style={{ color: 'var(--text-muted)', fontSize: '0.82rem', lineHeight: 1.45, padding: '12px' }}>
          No structured card is available for this view yet. Load a case or run/report a solver path before promoting evidence.
        </div>
      ) : (
        cardsForTab.map((card) => (
          <div key={`${card.card_type}-${card.finding}`} style={{ padding: '14px', borderRadius: '8px', border: `1px solid ${severityColor(card.severity)}`, background: 'rgba(2, 6, 23, 0.5)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', gap: '12px', alignItems: 'center', marginBottom: '8px' }}>
              <div style={{ fontSize: '0.68rem', color: severityColor(card.severity), textTransform: 'uppercase', fontWeight: 800 }}>{card.card_type.replace(/_/g, ' ')}</div>
              <div style={{ color: severityColor(card.severity), fontSize: '0.68rem', fontWeight: 800 }}>{card.severity}</div>
            </div>
            <div style={{ fontSize: '0.84rem', color: 'var(--text-primary)', fontWeight: 700, lineHeight: 1.35 }}>{card.finding}</div>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: '8px', lineHeight: 1.45 }}>
              <strong style={{ color: 'var(--text-primary)' }}>Evidence:</strong> {card.evidence}
            </div>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: '6px', lineHeight: 1.45 }}>
              <strong style={{ color: 'var(--text-primary)' }}>Action:</strong> {card.recommended_action}
            </div>
            <div style={{ fontSize: '0.75rem', color: '#f59e0b', marginTop: '6px', lineHeight: 1.45 }}>
              {card.claim_impact}
            </div>
          </div>
        ))
      )}
    </div>
  );

  return (
    <div className="glass-panel" style={{ height: '100%', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
      <div style={{ padding: '16px', borderBottom: '1px solid var(--border)', display: 'flex', flexDirection: 'column', gap: '12px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
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
                background: activeTab === tab.id ? 'var(--accent)' : 'rgba(15, 23, 42, 0.65)',
                color: activeTab === tab.id ? '#000' : 'var(--text-secondary)',
                fontSize: '0.68rem',
                fontWeight: 800,
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '4px',
              }}
            >
              {tab.icon}
              <span>{tab.label}</span>
            </button>
          ))}
        </div>
      </div>

      {activeTab === 'command' ? (
      <div style={{ flex: 1, overflowY: 'auto', padding: '16px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
        {messages.map((m, i) => (
          <div key={i} style={{ display: 'flex', gap: '10px', alignSelf: m.role === 'user' ? 'flex-end' : 'flex-start', maxWidth: '85%' }}>
            {m.role === 'assistant' && <div style={{ minWidth: '32px', height: '32px', borderRadius: '50%', background: 'var(--accent-glow)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}><Bot size={16} color="var(--accent)" /></div>}
            <div style={{ background: m.role === 'user' ? 'var(--accent)' : 'rgba(255,255,255,0.05)', color: m.role === 'user' ? '#000' : '#fff', padding: '12px', borderRadius: '12px', fontSize: '0.85rem', lineHeight: '1.4' }}>
              {m.content}
              
              {m.proposedAction && !m.executed && (
                <div style={{ marginTop: '12px', padding: '12px', background: 'rgba(0,0,0,0.2)', borderRadius: '8px', border: '1px solid var(--border)' }}>
                   <div style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--accent)', marginBottom: '8px', display: 'flex', alignItems: 'center', gap: '4px' }}>
                      <Sparkles size={12} /> PROPOSED ACTION
                   </div>
                   <p style={{ margin: '0 0 12px 0', fontSize: '0.75rem', color: '#ccc' }}>{m.proposedAction.description}</p>
                   <div style={{ display: 'flex', gap: '8px' }}>
                     <button 
                       onClick={() => confirmAction(i, m.proposedAction!)}
                       style={{ flex: 1, padding: '6px', background: 'var(--accent)', color: '#000', border: 'none', borderRadius: '4px', fontSize: '0.7rem', fontWeight: 700, cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '4px' }}
                     >
                       <Check size={12} /> Confirm
                     </button>
                     <button style={{ flex: 1, padding: '6px', background: 'transparent', color: '#ef4444', border: '1px solid #ef4444', borderRadius: '4px', fontSize: '0.7rem', cursor: 'pointer' }}>
                       <X size={12} /> Cancel
                     </button>
                   </div>
                </div>
              )}
            </div>
            {m.role === 'user' && <div style={{ minWidth: '32px', height: '32px', borderRadius: '50%', background: 'rgba(255,255,255,0.1)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}><User size={16} /></div>}
          </div>
        ))}
        <div ref={scrollRef} />
      </div>
      ) : renderReviewCards()}

      {activeTab === 'command' && (
      <div style={{ padding: '16px', borderTop: '1px solid var(--border)', background: 'rgba(0,0,0,0.2)' }}>
        <div style={{ position: 'relative' }}>
          <input 
            type="text" 
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSend()}
            placeholder="Ask copilot to run a study..."
            style={{ width: '100%', padding: '12px 40px 12px 12px', borderRadius: '8px', background: 'var(--bg-base)', border: '1px solid var(--border)', color: '#fff', fontSize: '0.85rem' }}
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
