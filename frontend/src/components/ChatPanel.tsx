import { useState, useRef, useEffect } from 'react';
import { Send, Bot, User, Check, X, Sparkles, MessageSquare } from 'lucide-react';

interface Action {
  action_type: string;
  parameters: any;
  description: string;
}

interface Message {
  role: 'user' | 'assistant';
  content: string;
  proposedAction?: Action;
  executed?: boolean;
}

interface ChatPanelProps {
  caseId: string | null;
  onExecuteAction: (action: Action) => Promise<any>;
}

export function ChatPanel({ caseId, onExecuteAction }: ChatPanelProps) {
  const [messages, setMessages] = useState<Message[]>([
    { role: 'assistant', content: 'Hello! I am your AI Design Copilot. How can I help you analyze this structure today?' }
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
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
    } catch (err) {
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

  return (
    <div className="glass-panel" style={{ height: '100%', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
      <div style={{ padding: '16px', borderBottom: '1px solid var(--border)', display: 'flex', alignItems: 'center', gap: '8px' }}>
        <MessageSquare size={18} color="var(--accent)" />
        <h3 style={{ margin: 0, fontSize: '0.9rem' }}>Design Copilot</h3>
      </div>

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
    </div>
  );
}

function Loader2({ size, className }: { size: number, className: string }) {
    return <div className={className} style={{ width: size, height: size, border: '2px solid currentColor', borderTopColor: 'transparent', borderRadius: '50%' }} />
}
