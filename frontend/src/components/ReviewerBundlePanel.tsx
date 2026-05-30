// FM-04a Phase 4 F — Reviewer bundle multi-select export panel.
//
// Tier 1 engineering candidate; not signed validation; not benchmark agreement.
//
// Checkbox list of every `*-candidate/` case (driven by the
// candidateCaseRegistry fallback list); "Export bundle" anchors at
// `/api/v1/reviewer-bundle?ids=...` so the download triggers a zip
// stream straight from the backend. The bundle is a Tier 1 reviewer
// hand-off, NOT a sealed FM-04b P8 packet.

import { useState } from 'react'
import { FALLBACK_CANDIDATE_CASES } from '../candidateCaseRegistry.ts'
import {
  reviewerBundleClaimImpact,
  reviewerBundleUrl,
  toggleSelection,
} from '../reviewerBundleClient.ts'
import { TIER1_BANNER } from '../trustCenterSummary.ts'

export interface ReviewerBundlePanelProps {
  apiBase: string
}

const SECTION_TITLE_STYLE = {
  fontSize: '0.7rem',
  textTransform: 'uppercase' as const,
  letterSpacing: '0.06em',
  color: 'var(--text-secondary)',
}

export function ReviewerBundlePanel({ apiBase }: ReviewerBundlePanelProps) {
  const [selected, setSelected] = useState<string[]>(() =>
    FALLBACK_CANDIDATE_CASES.map((c) => c.caseId),
  )

  const downloadUrl = selected.length > 0 ? reviewerBundleUrl(apiBase, selected) : null

  return (
    <div
      style={{
        padding: '12px 16px',
        borderRadius: '10px',
        border: '1px solid var(--border)',
        background: 'var(--bg-surface)',
        display: 'flex',
        flexDirection: 'column',
        gap: '10px',
      }}
      data-testid="reviewer-bundle-panel"
    >
      <div>
        <div style={{ ...SECTION_TITLE_STYLE, color: 'var(--text-warning, var(--warn-400))' }}>
          Reviewer bundle (multi-case zip)
        </div>
        <div style={{ fontSize: '0.65rem', color: 'var(--text-secondary)' }}>
          {TIER1_BANNER} · NOT a sealed FM-04b P8 packet
        </div>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
        {FALLBACK_CANDIDATE_CASES.map((c) => {
          const checked = selected.includes(c.caseId)
          return (
            <label
              key={c.caseId}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                fontSize: '0.78rem',
                color: 'var(--text-primary)',
                cursor: 'pointer',
              }}
            >
              <input
                type="checkbox"
                checked={checked}
                onChange={() => setSelected((current) => toggleSelection(current, c.caseId))}
                data-testid={`reviewer-bundle-checkbox-${c.caseId}`}
              />
              <code style={{ overflowWrap: 'anywhere' }}>{c.caseId}</code>
            </label>
          )
        })}
      </div>

      {downloadUrl ? (
        <a
          href={downloadUrl}
          download
          data-testid="reviewer-bundle-download"
          style={{
            padding: '8px 14px',
            borderRadius: '8px',
            border: '1px solid var(--border)',
            fontSize: '0.78rem',
            color: 'var(--text-primary)',
            background: 'var(--bg-secondary, transparent)',
            textDecoration: 'none',
            width: 'fit-content',
          }}
        >
          Export bundle ({selected.length} case{selected.length === 1 ? '' : 's'})
        </a>
      ) : (
        <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
          Pick at least one case to enable the bundle download.
        </div>
      )}

      <div style={{ fontSize: '0.65rem', color: 'var(--text-secondary)' }}>
        {reviewerBundleClaimImpact(selected.length)}
      </div>
    </div>
  )
}
