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

export interface SidebarProps {
  availableCases: SidebarCaseMetadata[]
  activeCaseId: string | null
  onSelectCase: (c: SidebarCaseMetadata) => void
  activeExperiment: SidebarExperimentStatus | null
  onFileUpload: (e: ChangeEvent<HTMLInputElement>) => void
  onOpenPalette: () => void
}

export function Sidebar({
  availableCases,
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
        borderLeft: '1px solid rgba(255,255,255,0.05)',
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
          <Zap size={24} color="#000" />
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
          background: 'rgba(255,255,255,0.04)',
          border: '1px solid rgba(255,255,255,0.08)',
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
            background: 'rgba(255,255,255,0.08)',
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
                    activeCaseId === c.id ? 'rgba(255,255,255,0.05)' : 'transparent',
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
