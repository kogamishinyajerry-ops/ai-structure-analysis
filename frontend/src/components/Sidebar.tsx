// FM-04a Phase 19 D — Case sidebar extraction.
//
// Tier 1 engineering candidate; not signed validation; not benchmark agreement.
//
// Pulled out of App.tsx so the workbench shell stays under ~1900 LOC and
// the case-rail concerns (Cmd-K hint, nav, case gallery, active
// experiment surface, FRD upload) live in one component the test suite
// can drive in isolation. Every data-testid, class name, and inline
// style is preserved verbatim from the App.tsx original so the existing
// visual snapshot and round-3 UX adoption tests do not regress.
//
// EmptyStateCard is mounted when the case-gallery list is empty (Phase
// 18 D primitive adoption, UI agent round-2 finding follow-through).

import type { ChangeEvent } from 'react'
import { Box, FileUp, LayoutDashboard, Zap } from 'lucide-react'
import { EmptyStateCard } from './EmptyStateCard'

export interface SidebarCaseMetadata {
  id: string
  name: string
  description: string
  type: string
  structure: string
  frd_path: string
}

export interface SidebarExperimentRun {
  iteration: number
  value: number
  status: string
}

export interface SidebarExperimentStatus {
  parameter: string
  runs: SidebarExperimentRun[]
}

export interface SidebarCandidateCase {
  caseId: string
  displayLabel: string
}

export interface SidebarProps {
  availableCases: SidebarCaseMetadata[]
  /**
   * FM-04a Phase 20 D — candidate-case roster surfaced inline in the
   * left rail (closes the Phase 19 E UX finding that cylinder-pv was
   * invisible from the Sidebar because it only existed in the
   * candidate registry, not the DB-backed availableCases list).
   * Selecting one fires `onSelectCandidateCase` (a distinct callback
   * so the App can route candidate selection through the
   * `selectedCandidateCaseId` state separately from DB cases).
   */
  candidateCases?: SidebarCandidateCase[]
  selectedCandidateCaseId?: string | null
  onSelectCandidateCase?: (caseId: string) => void
  activeCaseId: string | null
  onSelectCase: (c: SidebarCaseMetadata) => void
  activeExperiment: SidebarExperimentStatus | null
  onFileUpload: (e: ChangeEvent<HTMLInputElement>) => void
  onOpenPalette: () => void
}

export function Sidebar({
  availableCases,
  candidateCases,
  selectedCandidateCaseId,
  onSelectCandidateCase,
  activeCaseId,
  onSelectCase,
  activeExperiment,
  onFileUpload,
  onOpenPalette,
}: SidebarProps) {
  return (
    <aside
      className="glass-sidebar"
      data-testid="case-sidebar"
      style={{
        padding: '24px',
        display: 'flex',
        flexDirection: 'column',
        gap: '24px',
        borderLeft: '1px solid var(--border)',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
        <div
          style={{
            width: '40px',
            height: '40px',
            background: 'var(--accent)',
            borderRadius: '10px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}
        >
          <Zap size={24} color="#fff" />
        </div>
        <h2 style={{ fontSize: '1.25rem', fontWeight: 700, margin: 0 }}>
          Structure<span style={{ color: 'var(--accent)' }}>AI</span>
        </h2>
      </div>

      {/* Phase 18 E (round 3) — discoverable Cmd-K hint (UX agent
          round-2 finding). Click also opens the palette. */}
      <button
        type="button"
        onClick={onOpenPalette}
        data-testid="cmd-k-hint"
        aria-label="Open command palette (Cmd-K)"
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: '8px',
          padding: '6px 10px',
          borderRadius: '6px',
          background: 'var(--c-50)',
          border: '1px solid var(--border)',
          color: 'var(--text-secondary)',
          cursor: 'pointer',
          fontSize: '0.75rem',
          textAlign: 'left',
        }}
      >
        <span>Command palette</span>
        <kbd
          style={{
            fontSize: '0.7rem',
            padding: '1px 6px',
            borderRadius: 4,
            background: 'var(--c-100)',
            fontFamily: 'ui-monospace, Menlo, monospace',
          }}
        >
          ⌘K
        </kbd>
      </button>

      <nav style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
        <button
          className="nav-item active"
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '12px',
            padding: '12px',
            borderRadius: '8px',
            background: 'var(--accent-glow)',
            color: 'var(--accent)',
            border: 'none',
            cursor: 'pointer',
            textAlign: 'left',
            fontWeight: 600,
          }}
        >
          <LayoutDashboard size={18} /> Workbench
        </button>
      </nav>

      <div data-testid="case-gallery">
        <div
          style={{
            fontSize: '0.75rem',
            fontWeight: 600,
            color: 'var(--text-muted)',
            textTransform: 'uppercase',
            marginBottom: '12px',
            paddingLeft: '12px',
          }}
        >
          Case Gallery
        </div>
        {availableCases.length === 0 ? (
          <div data-testid="case-gallery-empty">
            <EmptyStateCard
              headline="No cases yet"
              body="Drop an FRD file below or load a candidate case from the workbench to populate this gallery."
              glyph="∅"
            />
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
            {availableCases.map((c) => (
              <button
                key={c.id}
                onClick={() => onSelectCase(c)}
                data-testid={`case-item-${c.id}`}
                className={`case-item ${activeCaseId === c.id ? 'active' : ''}`}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '12px',
                  padding: '10px 12px',
                  borderRadius: '8px',
                  background:
                    activeCaseId === c.id ? 'var(--accent-glow)' : 'transparent',
                  color:
                    activeCaseId === c.id ? 'var(--accent)' : 'var(--text-secondary)',
                  border: 'none',
                  cursor: 'pointer',
                  textAlign: 'left',
                  fontSize: '0.875rem',
                }}
              >
                <Box size={16} /> {c.name}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Phase 20 D — candidate-case roster. Surfaces *-candidate
          entries (cylinder-pv, plate-with-hole, cantilever, etc.)
          in the left rail so the Phase 19 E UX finding "cylinder-pv
          is invisible because it lives only in the candidate
          registry" is closed. Only renders when the parent supplies
          a non-empty list. */}
      {candidateCases && candidateCases.length > 0 && (
        <div data-testid="candidate-case-roster">
          <div
            style={{
              fontSize: '0.75rem',
              fontWeight: 600,
              color: 'var(--text-muted)',
              textTransform: 'uppercase',
              marginBottom: '12px',
              paddingLeft: '12px',
            }}
          >
            Candidate Cases
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
            {candidateCases.map((cc) => {
              const isActive = selectedCandidateCaseId === cc.caseId
              return (
                <button
                  key={cc.caseId}
                  type="button"
                  onClick={() => onSelectCandidateCase?.(cc.caseId)}
                  data-testid={`candidate-case-${cc.caseId}`}
                  className={`case-item ${isActive ? 'active' : ''}`}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '12px',
                    padding: '10px 12px',
                    borderRadius: '8px',
                    background: isActive
                      ? 'var(--accent-glow)'
                      : 'transparent',
                    color: isActive
                      ? 'var(--accent)'
                      : 'var(--text-secondary)',
                    border: 'none',
                    cursor: 'pointer',
                    textAlign: 'left',
                    fontSize: '0.875rem',
                  }}
                >
                  <Box size={16} /> {cc.displayLabel}
                </button>
              )
            })}
          </div>
        </div>
      )}

      {activeExperiment && (
        <div
          className="glass-panel"
          data-testid="active-experiment-summary"
          style={{ padding: '16px' }}
        >
          <div
            style={{
              fontSize: '0.75rem',
              fontWeight: 600,
              color: 'var(--accent)',
              marginBottom: '8px',
            }}
          >
            EXP: {activeExperiment.parameter.toUpperCase()}
          </div>
          {activeExperiment.runs.map((r) => (
            <div
              key={r.iteration}
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                fontSize: '0.75rem',
                marginBottom: '4px',
              }}
            >
              <span>V={r.value}</span>
              <span
                style={{
                  color:
                    r.status === 'COMPLETED' ? 'var(--accent)' : 'var(--text-muted)',
                }}
              >
                {r.status}
              </span>
            </div>
          ))}
        </div>
      )}

      <div style={{ marginTop: 'auto' }}>
        <label
          className="glass-panel"
          data-testid="frd-upload-label"
          style={{
            display: 'block',
            padding: '20px',
            textAlign: 'center',
            border: '2px dashed var(--border)',
            cursor: 'pointer',
            transition: 'border-color 0.2s',
          }}
        >
          <input
            type="file"
            data-testid="frd-upload-input"
            onChange={onFileUpload}
            style={{ display: 'none' }}
          />
          <FileUp
            size={24}
            style={{ marginBottom: '8px', color: 'var(--text-secondary)' }}
          />
          <div style={{ fontSize: '0.875rem', fontWeight: 500 }}>Upload FRD</div>
        </label>
      </div>
    </aside>
  )
}
