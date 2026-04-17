import React, { useState } from 'react';
import { Settings, Play, Info } from 'lucide-react';

interface SensitivityFormProps {
  activeCaseId: string;
  onRunStudy: (param: string, values: number[]) => void;
  loading: boolean;
}

export function SensitivityForm({ activeCaseId, onRunStudy, loading }: SensitivityFormProps) {
  const [param, setParam] = useState('load');
  const [min, setMin] = useState(100);
  const [max, setMax] = useState(500);
  const [steps, setSteps] = useState(3);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const values = [];
    const stepSize = steps > 1 ? (max - min) / (steps - 1) : 0;
    for (let i = 0; i < steps; i++) {
      values.push(min + stepSize * i);
    }
    onRunStudy(param, values);
  };

  return (
    <div className="glass-panel" style={{ padding: '24px' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '20px' }}>
        <Settings size={18} color="var(--accent)" />
        <h3 style={{ margin: 0, fontSize: '1rem' }}>Parametric Study: {activeCaseId}</h3>
      </div>

      <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
        <div>
          <label style={{ display: 'block', fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '8px', fontWeight: 600 }}>TARGET PARAMETER</label>
          <select 
            value={param} 
            onChange={(e) => setParam(e.target.value)}
            style={{ width: '100%', padding: '10px', borderRadius: '8px', background: 'var(--bg-base)', border: '1px solid var(--border)', color: '#fff' }}
          >
            <option value="load">Load Magnitude (*CLOAD)</option>
            <option value="elastic_modulus">Young's Modulus (*ELASTIC)</option>
          </select>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '12px' }}>
          <div>
            <label style={{ display: 'block', fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '8px' }}>MIN</label>
            <input type="number" value={min} onChange={(e) => setMin(Number(e.target.value))} style={{ width: '100%', padding: '8px', borderRadius: '6px', background: 'var(--bg-base)', border: '1px solid var(--border)', color: '#fff' }} />
          </div>
          <div>
            <label style={{ display: 'block', fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '8px' }}>MAX</label>
            <input type="number" value={max} onChange={(e) => setMax(Number(e.target.value))} style={{ width: '100%', padding: '8px', borderRadius: '6px', background: 'var(--bg-base)', border: '1px solid var(--border)', color: '#fff' }} />
          </div>
          <div>
            <label style={{ display: 'block', fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '8px' }}>STEPS</label>
            <input type="number" value={steps} onChange={(e) => setSteps(Number(e.target.value))} style={{ width: '100%', padding: '8px', borderRadius: '6px', background: 'var(--bg-base)', border: '1px solid var(--border)', color: '#fff' }} />
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'flex-start', gap: '10px', padding: '12px', background: 'rgba(59, 130, 246, 0.1)', borderRadius: '8px', border: '1px solid rgba(59, 130, 246, 0.2)' }}>
          <Info size={16} color="#3b82f6" style={{ marginTop: '2px' }} />
          <p style={{ margin: 0, fontSize: '0.75rem', color: '#93c5fd' }}>
            This will trigger <strong>{steps}</strong> simulation runs in parallel. 
            Automated report generation will follow each completion.
          </p>
        </div>

        <button 
          type="submit" 
          disabled={loading}
          style={{ width: '100%', padding: '12px', borderRadius: '8px', background: 'var(--accent)', color: '#000', border: 'none', fontWeight: 700, cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px', opacity: loading ? 0.6 : 1 }}
        >
          <Play size={16} fill="currentColor" /> {loading ? 'Exploration in Progress...' : 'Start Study'}
        </button>
      </form>
    </div>
  );
}
