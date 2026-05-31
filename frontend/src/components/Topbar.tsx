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
import { useDensity } from '../state/useDensity'
import { DensityToggle } from './DensityToggle'

export type AnalysisType = 'static' | 'modal' | 'buckling'

export interface TopbarMaterialOption {
  id: string
  label: string
}

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
  /** FM-04a Phase 22 D — compact material picker in the Topbar.
   * Mirrors the analysis-type dropdown so the swap path is 1 click
   * from the top rail. Renders only when at least one option is
   * provided; null/empty list collapses the control. */
  materialOptions?: TopbarMaterialOption[]
  selectedMaterialId?: string
  onChangeMaterialId?: (next: string) => void
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
    materialOptions,
    selectedMaterialId,
    onChangeMaterialId,
  } = props
  const { density, setDensity } = useDensity()
  const showMaterialSelect =
    showRunControls &&
    materialOptions !== undefined &&
    materialOptions.length > 0
  return (
    <header
      data-testid="workbench-topbar"
      style={{
        padding: 'var(--sp-5) var(--sp-10)',
        borderBottom: '1px solid var(--border)',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        // Wrap (not clip) when the main column is narrow — e.g. chat open at
        // ~1280 + a long case id + the matl chip + 5 right-side controls. Only
        // engages under pressure; identical single-line layout at wide widths.
        // Intrinsic wrap, no media query (Codex 45 P2; desktop-overflow path).
        flexWrap: 'wrap',
        rowGap: 'var(--sp-2)',
        position: 'sticky',
        top: 0,
        background: 'rgba(250, 249, 245, 0.82)',
        backdropFilter: 'blur(8px)',
        zIndex: 10,
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--sp-4)' }}>
        <div
          data-testid="topbar-breadcrumb"
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 'var(--sp-2)',
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
              border: '1px solid rgba(47, 111, 219, 0.30)',
              background: 'rgba(47, 111, 219, 0.10)',
              color: 'var(--info-400)',
              fontSize: 'var(--fs-xs)',
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
      <div style={{ display: 'flex', flexWrap: 'wrap', justifyContent: 'flex-end', marginLeft: 'auto', gap: 'var(--sp-3)' }}>
        <DensityToggle density={density} onChange={setDensity} />
        <button
          type="button"
          onClick={onToggleChat}
          data-testid="topbar-copilot-toggle"
          style={{
            padding: 'var(--sp-2) var(--sp-4)',
            borderRadius: 'var(--r-sm)',
            background: showChat ? 'var(--accent-glow)' : 'var(--bg-surface)',
            color: showChat ? 'var(--accent-600)' : 'var(--text-primary)',
            border: showChat ? '1px solid var(--border-focus)' : '1px solid var(--border)',
            fontWeight: 600,
            display: 'flex',
            alignItems: 'center',
            gap: 'var(--sp-2)',
            cursor: 'pointer',
          }}
        >
          <MessageSquare size={16} /> Copilot
        </button>
        {showRunControls && (
          <div
            data-testid="topbar-run-controls"
            style={{ display: 'flex', gap: 'var(--sp-2)' }}
          >
            {showMaterialSelect && (
              <select
                data-testid="topbar-material-select"
                aria-label="Active material"
                value={selectedMaterialId ?? ''}
                onChange={(e) => onChangeMaterialId?.(e.target.value)}
                style={{
                  background: 'var(--bg-surface)',
                  color: 'var(--text-primary)',
                  border: '1px solid var(--border)',
                  borderRadius: 'var(--r-sm)',
                  padding: '0 var(--sp-3)',
                  fontSize: '0.85rem',
                  outline: 'none',
                  maxWidth: 220,
                }}
              >
                {materialOptions!.map((opt) => (
                  <option key={opt.id} value={opt.id}>
                    {opt.label}
                  </option>
                ))}
              </select>
            )}
            <select
              data-testid="topbar-analysis-type"
              value={analysisType}
              onChange={(e) =>
                onChangeAnalysisType(e.target.value as AnalysisType)
              }
              style={{
                background: 'var(--bg-surface)',
                color: 'var(--text-primary)',
                border: '1px solid var(--border)',
                borderRadius: 'var(--r-sm)',
                padding: '0 var(--sp-3)',
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
              className="run-solver-btn"
              data-solving={solving ? 'true' : 'false'}
              disabled={solving}
              onClick={onRunSolver}
              style={{
                padding: 'var(--sp-2) var(--sp-4)',
                borderRadius: 'var(--r-sm)',
                background: 'var(--accent)',
                color: '#fff',
                border: 'none',
                fontWeight: 600,
                display: 'flex',
                alignItems: 'center',
                gap: 'var(--sp-2)',
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
                  padding: 'var(--sp-2) var(--sp-4)',
                  borderRadius: 'var(--r-sm)',
                  background: 'rgba(197, 69, 59, 0.10)',
                  color: 'var(--danger-400)',
                  border: '1px solid rgba(197, 69, 59, 0.30)',
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
