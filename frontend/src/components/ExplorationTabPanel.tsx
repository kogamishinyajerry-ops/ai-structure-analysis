// FM-04a Phase 22 C — Exploration tab body extracted out of App.tsx
// as part of the LOC-discipline trajectory. Hosts the SensitivityForm
// + experiment-comparison overlay. State is owned by the App
// composition root; this panel emits intent callbacks.
//
// Tier 1 / Tier 2 engineering candidate; not signed validation; not
// benchmark agreement.

import { ArrowRightLeft } from 'lucide-react';
import { SensitivityForm } from './SensitivityForm';
import type { ExperimentStatus } from '../types/AppTypes';

export interface ExplorationTabPanelProps {
  activeCaseId: string;
  loading: boolean;
  activeExperiment: ExperimentStatus | null;
  comparedIndices: [number, number] | null;
  onCompareIndex: (index: number) => void;
  onRunStudy: (param: string, values: number[]) => void | Promise<void>;
}

export function ExplorationTabPanel({
  activeCaseId,
  loading,
  activeExperiment,
  comparedIndices,
  onCompareIndex,
  onRunStudy,
}: ExplorationTabPanelProps) {
  return (
    <div
      data-testid="exploration-tab-panel"
      style={{ display: 'grid', gridTemplateColumns: 'minmax(400px, 500px) 1fr', gap: '32px' }}
    >
      <SensitivityForm
        activeCaseId={activeCaseId}
        onRunStudy={onRunStudy}
        loading={loading}
      />
      {activeExperiment && activeExperiment.status === 'COMPLETED' && (
        <div
          data-testid="exploration-result-comparison"
          className="glass-panel"
          style={{ padding: '24px' }}
        >
          <h3
            style={{
              fontSize: '1rem',
              marginBottom: '16px',
              display: 'flex',
              alignItems: 'center',
              gap: '10px',
            }}
          >
            <ArrowRightLeft size={18} color="var(--accent)" /> Result Comparison
          </h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {activeExperiment.runs.map((r, i) => (
              <div
                key={i}
                className="glass-panel"
                style={{
                  padding: '12px',
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                }}
              >
                <span>
                  Iteration {i + 1} (Value: {r.value})
                </span>
                <button
                  data-testid={`exploration-compare-button-${i}`}
                  onClick={() => onCompareIndex(i)}
                  style={{
                    background: comparedIndices?.includes(i) ? 'var(--accent)' : 'transparent',
                    border: '1px solid var(--accent)',
                    color: comparedIndices?.includes(i) ? '#fff' : 'var(--accent)',
                    padding: '4px 12px',
                    borderRadius: '4px',
                    fontSize: '0.75rem',
                    cursor: 'pointer',
                  }}
                >
                  {comparedIndices?.includes(i) ? 'Selected' : 'Compare'}
                </button>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
