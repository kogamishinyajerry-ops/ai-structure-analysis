import React from 'react';
import { Activity, Hash, Layers } from 'lucide-react';

interface IncrementData {
  index: int;
  step: int;
  type: string;
  value: float;
  max_displacement: float;
  max_von_mises: float;
}

interface ModeSelectorProps {
  increments: IncrementData[];
  selectedModeIndex: number;
  activeAnalysisType: string;
  onSelectMode: (index: number) => void;
}

export function ModeSelector({ increments, selectedModeIndex, activeAnalysisType, onSelectMode }: ModeSelectorProps) {
  if (!increments || increments.length === 0) return null;

  const getLabel = (type: string) => {
    if (type === 'vibration') return 'Frequency (Hz)';
    if (type === 'buckling') return 'Load Factor (λ)';
    return 'Value';
  };

  return (
    <div className="bg-slate-900/80 border border-slate-800 rounded-xl overflow-hidden shadow-xl backdrop-blur-md">
      <div className="px-4 py-3 bg-slate-800/50 border-b border-slate-700 flex items-center space-x-2">
        <Layers className="w-4 h-4 text-indigo-400" />
        <h3 className="text-sm font-bold text-slate-200 uppercase tracking-wider">
          {activeAnalysisType === 'modal' ? 'Vibration Modes' : 'Buckling Modes'}
        </h3>
      </div>
      
      <div className="max-h-64 overflow-y-auto">
        <table className="w-full text-left text-xs border-collapse">
          <thead>
            <tr className="bg-slate-900 text-slate-500">
              <th className="px-4 py-2 font-medium border-b border-slate-800">Mode</th>
              <th className="px-4 py-2 font-medium border-b border-slate-800">{getLabel(increments[0].type)}</th>
              <th className="px-4 py-2 font-medium border-b border-slate-800 text-right">Max Disp</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/50">
            {increments.map((inc) => (
              <tr 
                key={`${inc.step}-${inc.index}`}
                onClick={() => onSelectMode(inc.index - 1)}
                className={`cursor-pointer transition-colors group ${
                  selectedModeIndex === inc.index - 1 
                    ? 'bg-indigo-600/20 text-indigo-100' 
                    : 'hover:bg-slate-800 text-slate-400 hover:text-slate-200'
                }`}
              >
                <td className="px-4 py-3 font-mono">
                  <div className="flex items-center space-x-2">
                    {selectedModeIndex === inc.index - 1 && <div className="w-1.5 h-1.5 rounded-full bg-indigo-500 animate-pulse" />}
                    <span>{inc.index}</span>
                  </div>
                </td>
                <td className="px-4 py-3 font-semibold">
                  {inc.value.toFixed(2)}
                </td>
                <td className="px-4 py-3 text-right text-slate-500">
                  {inc.max_displacement.toFixed(4)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
