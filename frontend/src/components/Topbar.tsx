// FM-04a Phase 20 D — Topbar component (Workbench header bar).
//
// Tier 1 / Tier 2 engineering candidate; not signed validation; not
// benchmark agreement.
//
// Extracted from App.tsx so the workbench shell can drop another
// ~80 LOC and the analysis-type / Run Solver / Stop / Copilot toggle
// concerns live in one component the test suite can drive in
// isolation. Every data-testid and inline style is preserved from
// the original App.tsx header.

import { ChevronRight, Loader2, MessageSquare, Play } from 'lucide-react'
import type { ReactNode } from 'react'

export type AnalysisType = 'static' | 'modal' | 'buckling'

export interface TopbarProps {
  /** Display label shown after "Analysis › " — the active case id, or
   * a fallback like the uploaded FRD filename / "Session". */
  breadcrumbLabel: string
  /** Optional badge node rendered next to the breadcrumb (used today
   * for the ComplianceBadge). */
  badge?: ReactNode
  /** True when the analysis-type select + Run Solver / Stop should
   * be visible. App.tsx only renders these when a case is active. */
  showRunControls: boolean
  analysisType: AnalysisType
  onChangeAnalysisType: (next: AnalysisType) => void
  solving: boolean
  onRunSolver: () => void
  onStopSolver: () => void
  showChat: boolean
  onToggleChat: () => void
  /** FM-04a Phase 21 D — when /solver/run returns a material
   * citation (Phase 20 A end-to-end wiring), surface it next to the
   * breadcrumb so reviewers see WHICH material the solver actually
   * used. Truncated to its first ~60 chars in the inline chip; the
   * full citation sits in the OperatorStatusPanel "Runtime" section. */
  materialReference?: string | null
}

export function Topbar(props: TopbarProps) {
  const {
    breadcrumbLabel,
    badge,
    showRunControls,
    analysisType,
    onChangeAnalysisType,
    solving,
    onRunSolver,
    onStopSolver,
    showChat,
    onToggleChat,
    materialReference,
  } = props
  return (
    <header
      data-testid="workbench-topbar"
      style={{
        padding: '20px 40px',
        borderBottom: '1px solid var(--border)',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        position: 'sticky',
        top: 0,
        background: 'rgba(2, 6, 23, 0.8)',
        backdropFilter: 'blur(8px)',
        zIndex: 10,
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
        <div
          data-testid="topbar-breadcrumb"
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            color: 'var(--text-muted)',
            fontSize: '0.875rem',
          }}
        >
          Analysis <ChevronRight size={14} />{' '}
          <span style={{ color: 'var(--text-primary)' }}>
            {breadcrumbLabel}
          </span>
        </div>
        {badge}
        {materialReference && (
          <span
            data-testid="topbar-material-reference"
            title={materialReference}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: 6,
              padding: '4px 10px',
              borderRadius: 999,
              border: '1px solid rgba(96, 165, 250, 0.35)',
              background: 'rgba(96, 165, 250, 0.12)',
              color: '#bfdbfe',
              fontSize: '0.72rem',
              fontWeight: 700,
              maxWidth: 320,
              overflow: 'hidden',
              whiteSpace: 'nowrap',
              textOverflow: 'ellipsis',
            }}
          >
            MATL · {materialReference}
          </span>
        )}
      </div>
      <div style={{ display: 'flex', gap: '12px' }}>
        <button
          type="button"
          onClick={onToggleChat}
          data-testid="topbar-copilot-toggle"
          style={{
            padding: '8px 16px',
            borderRadius: '8px',
            background: showChat ? 'var(--accent)' : 'var(--bg-surface)',
            color: showChat ? '#000' : '#fff',
            border: '1px solid var(--border)',
            fontWeight: 600,
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            cursor: 'pointer',
          }}
        >
          <MessageSquare size={16} /> Copilot
        </button>
        {showRunControls && (
          <div
            data-testid="topbar-run-controls"
            style={{ display: 'flex', gap: '8px' }}
          >
            <select
              data-testid="topbar-analysis-type"
              value={analysisType}
              onChange={(e) =>
                onChangeAnalysisType(e.target.value as AnalysisType)
              }
              style={{
                background: 'var(--bg-surface)',
                color: '#fff',
                border: '1px solid var(--border)',
                borderRadius: '8px',
                padding: '0 12px',
                fontSize: '0.85rem',
                outline: 'none',
              }}
            >
              <option value="static">Static Analysis</option>
              <option value="modal">Modal Analysis</option>
              <option value="buckling">Linear Buckling</option>
            </select>
            <button
              type="button"
              data-testid="topbar-run-solver"
              disabled={solving}
              onClick={onRunSolver}
              style={{
                padding: '8px 16px',
                borderRadius: '8px',
                background: 'var(--accent)',
                color: '#000',
                border: 'none',
                fontWeight: 600,
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                cursor: solving ? 'not-allowed' : 'pointer',
                opacity: solving ? 0.6 : 1,
              }}
            >
              {solving ? (
                <Loader2 size={16} className="animate-spin" />
              ) : (
                <Play size={16} fill="currentColor" />
              )}
              Run Solver
            </button>
            {solving && (
              <button
                type="button"
                data-testid="topbar-stop-solver"
                onClick={onStopSolver}
                style={{
                  padding: '8px 16px',
                  borderRadius: '8px',
                  background: 'rgba(255,100,100,0.2)',
                  color: '#ff6b6b',
                  border: '1px solid rgba(255,100,100,0.3)',
                  fontWeight: 600,
                  cursor: 'pointer',
                }}
              >
                Stop
              </button>
            )}
          </div>
        )}
      </div>
    </header>
  )
}
