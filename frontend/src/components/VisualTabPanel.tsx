// FM-04a Phase 21 D — Visual tab body extraction.
//
// Tier 1 / Tier 2 engineering candidate; not signed validation; not
// benchmark agreement.
//
// Extracted from App.tsx (~150 LOC of dense JSX with 20+ panel
// components). Trimming App.tsx is one of the Phase 21 D blueprint
// commitments; the Narrative and Exploration tab bodies are even
// larger and remain inlined for now (honestly documented in FINAL.md
// as Phase 22+ scope).
//
// Every panel below was on the Phase 1-20 "Visual" tab — this
// extraction is rendering-equivalent: same components, same props,
// same render order. Tests pinning the Visual tab in test/Phase21D_*
// assert presence of each panel via testid.

import { useCallback, useState, type CSSProperties } from 'react'
import {
  FALLBACK_CANDIDATE_CASES,
} from '../candidateCaseRegistry'
import type { MaterialRecord } from '../materialsClient'
import type { SignoffRecord } from '../signoffHistoryClient'
import { AcceptancePacketPanel } from './AcceptancePacketPanel'
import { AdvisorPanel } from './AdvisorPanel'
import { ArchivedPacketDiffPanel } from './ArchivedPacketDiffPanel'
import { BulletPlateBlueprintPanel } from './BulletPlateBlueprintPanel'
import { CandidateCasePicker } from './CandidateCasePicker'
import { CaseComparisonPanel } from './CaseComparisonPanel'
import { CaseCompletenessCard } from './CaseCompletenessCard'
import { CohortAnomaliesPanel } from './CohortAnomaliesPanel'
import { CohortDashboardPanel } from './CohortDashboardPanel'
import { CohortExecutiveSummaryPanel } from './CohortExecutiveSummaryPanel'
import { CohortSnapshotPanel } from './CohortSnapshotPanel'
import { CohortSubstantiationPanel } from './CohortSubstantiationPanel'
import { CohortTrendAnomaliesPanel } from './CohortTrendAnomaliesPanel'
import { ConvergenceStudyViewer } from './ConvergenceStudyViewer'
import { DriftNarrativePanel } from './DriftNarrativePanel'
import { MaterialPickerPanel } from './MaterialPickerPanel'
import { ProvenancePanel } from './ProvenancePanel'
import { ReproducibilityManifestCard } from './ReproducibilityManifestCard'
import { ReviewerBundlePanel } from './ReviewerBundlePanel'
import { SignoffHistoryPanel } from './SignoffHistoryPanel'
import { TrustScoreGauge } from './TrustScoreGauge'
import { TrustScoreTimelineChart } from './TrustScoreTimelineChart'

export interface VisualTabPanelProps {
  apiBase: string
  selectedCandidateCaseId: string | null
  onSelectCandidateCaseId: (id: string | null) => void
  comparisonCaseA: string | null
  comparisonCaseB: string | null
  onSelectComparisonA: (id: string | null) => void
  onSelectComparisonB: (id: string | null) => void
  snapshotLabelA: string | null
  snapshotLabelB: string | null
  onSelectSnapshotLabelA: (label: string | null) => void
  onSelectSnapshotLabelB: (label: string | null) => void
  selectedMaterial: MaterialRecord
  onMaterialChange: (next: MaterialRecord) => void
  latestSignoff: SignoffRecord | null
  onLatestSignoff: (record: SignoffRecord | null) => void
}

export function VisualTabPanel(props: VisualTabPanelProps) {
  const {
    apiBase,
    selectedCandidateCaseId,
    onSelectCandidateCaseId,
    comparisonCaseA,
    comparisonCaseB,
    onSelectComparisonA,
    onSelectComparisonB,
    snapshotLabelA,
    snapshotLabelB,
    onSelectSnapshotLabelA,
    onSelectSnapshotLabelB,
    selectedMaterial,
    onMaterialChange,
    latestSignoff,
    onLatestSignoff,
  } = props

  // FM-04a Phase 41.4 (retro P2-B) — lazy-mount the 22-panel evidence stack: the
  // <details> only HIDES children (jsdom + browsers keep them mounted), so their
  // mount-time fetch effects fired on the boot first paint even while collapsed.
  // Render the body only AFTER the disclosure is first opened so zero panel fetches
  // hit the boot path. `hasOpened` LATCHES (never resets), so once opened the subtree
  // stays mounted — collapsing/reopening preserves panel state and fires no re-fetch
  // (this-round Codex P2: don't unmount on collapse). `open` keeps React owning the
  // native disclosure state so the open/collapse animation stays in sync.
  const [open, setOpen] = useState(false)
  const [hasOpened, setHasOpened] = useState(false)

  // Memoise the persistence-aware case-picker callbacks so the inner
  // components don't see new function identities every render.
  const onCohortDashboardSelectCase = useCallback(
    (id: string) => {
      onSelectCandidateCaseId(id)
      try {
        window.localStorage.setItem('fm04a.candidateCaseId', id)
      } catch {
        /* no-op when storage is unavailable */
      }
    },
    [onSelectCandidateCaseId],
  )
  const onCandidatePickerSelect = onCohortDashboardSelectCase
  const onSelectA = useCallback(
    (id: string) => {
      onSelectComparisonA(id)
      try {
        window.localStorage.setItem('fm04a.comparisonCaseA', id)
      } catch {
        /* no-op */
      }
    },
    [onSelectComparisonA],
  )
  const onSelectB = useCallback(
    (id: string) => {
      onSelectComparisonB(id)
      try {
        window.localStorage.setItem('fm04a.comparisonCaseB', id)
      } catch {
        /* no-op */
      }
    },
    [onSelectComparisonB],
  )

  return (
    <div
      data-testid="visual-tab-panel"
      style={{ display: 'flex', flexDirection: 'column', gap: 'var(--sp-3)' }}
    >
      {/* FM-04a Phase 41.4 (B.2 + retro P2-B) — the 22 evidence/governance panels
          were a dense "wall" directly under the 3D hero. Collapse them into one
          default-closed "Evidence & Trust" disclosure so the demo's first paint
          stays the clean centerpiece; reviewers expand for the full
          provenance/convergence/sign-off stack. The body is lazily rendered
          (only after the first open, then kept mounted) so the panels' mount-time
          fetches never hit the boot path yet survive collapse/reopen. The outer
          visual-tab-panel div + <summary> stay unconditional, and Provenance/Advisor
          remain null-gated, so the Phase21D pins hold. */}
      <style>{EVIDENCE_WALL_STYLES}</style>
      <details
        className="fm04a-evidence-wall"
        data-testid="evidence-trust-section"
        open={open}
        onToggle={(e) => {
          const isOpen = (e.currentTarget as HTMLDetailsElement).open
          setOpen(isOpen)
          if (isOpen) setHasOpened(true)
        }}
      >
        <summary className="fm04a-evidence-summary" style={EVIDENCE_SUMMARY_STYLE}>
          <span className="fm04a-evidence-chevron" style={EVIDENCE_CHEVRON_STYLE} aria-hidden="true">
            ▸
          </span>
          <span style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
            <span style={{ fontWeight: 600, color: 'var(--text-primary)', fontSize: '14px' }}>
              Evidence &amp; Trust
            </span>
            <span style={{ color: 'var(--text-muted)', fontSize: '12px' }}>
              Governance, provenance, convergence &amp; sign-off — expand to review
            </span>
          </span>
        </summary>
        {hasOpened && (
        <div data-testid="evidence-trust-body" style={{ display: 'flex', flexDirection: 'column', gap: 'var(--sp-3)', marginTop: '14px' }}>
      <CohortDashboardPanel
        apiBase={apiBase}
        selectedCaseId={selectedCandidateCaseId}
        onSelectCase={onCohortDashboardSelectCase}
      />
      {/* FM-04a Phase 12 I — Cohort substantiation panel. */}
      <CohortSubstantiationPanel apiBase={apiBase} />
      <CaseCompletenessCard apiBase={apiBase} caseId={selectedCandidateCaseId} />
      <CandidateCasePicker
        apiBase={apiBase}
        selectedCaseId={selectedCandidateCaseId}
        onSelect={onCandidatePickerSelect}
      />
      <AcceptancePacketPanel apiBase={apiBase} caseId={selectedCandidateCaseId} />
      <ConvergenceStudyViewer apiBase={apiBase} caseId={selectedCandidateCaseId} />
      <CaseComparisonPanel
        apiBase={apiBase}
        cases={FALLBACK_CANDIDATE_CASES}
        caseA={comparisonCaseA}
        caseB={comparisonCaseB}
        onSelectA={onSelectA}
        onSelectB={onSelectB}
      />
      <ReviewerBundlePanel apiBase={apiBase} />
      <ArchivedPacketDiffPanel apiBase={apiBase} />
      <ReproducibilityManifestCard apiBase={apiBase} caseId={selectedCandidateCaseId} />
      <CohortExecutiveSummaryPanel apiBase={apiBase} />
      <CohortAnomaliesPanel apiBase={apiBase} />
      <CohortTrendAnomaliesPanel apiBase={apiBase} />
      <TrustScoreGauge
        apiBase={apiBase}
        caseId={selectedCandidateCaseId}
        latestSignoffVerdict={latestSignoff?.verdict ?? null}
        latestSignoffReviewer={latestSignoff?.reviewer ?? null}
        latestSignoffUtc={latestSignoff?.signoffUtc ?? null}
      />
      <SignoffHistoryPanel
        apiBase={apiBase}
        caseId={selectedCandidateCaseId}
        onLatestRecord={onLatestSignoff}
      />
      <TrustScoreTimelineChart apiBase={apiBase} caseId={selectedCandidateCaseId} />
      <CohortSnapshotPanel
        apiBase={apiBase}
        selectedLabelA={snapshotLabelA}
        selectedLabelB={snapshotLabelB}
        onSelectLabelA={onSelectSnapshotLabelA}
        onSelectLabelB={onSelectSnapshotLabelB}
      />
      {/* FM-04a Phase 9 E — Provenance panel mounts only when both
          a case id and snapshot label are known. */}
      {selectedCandidateCaseId && snapshotLabelA && (
        <ProvenancePanel
          apiBase={apiBase}
          caseId={selectedCandidateCaseId}
          snapshotLabel={snapshotLabelA}
        />
      )}
      {/* FM-04a Phase 11 E — Advisor critique panel (advisor-only). */}
      {selectedCandidateCaseId && snapshotLabelA && (
        <AdvisorPanel
          apiBase={apiBase}
          caseId={selectedCandidateCaseId}
          snapshotLabel={snapshotLabelA}
        />
      )}
      <DriftNarrativePanel
        apiBase={apiBase}
        labelA={snapshotLabelA}
        labelB={snapshotLabelB}
      />
      {/* FM-04a Phase 18 E (round 2) — materials library picker.
          Tier 1 banner inline; reviewer can swap material by click
          or via the Cmd-K palette. Selection wired to
          `selectedMaterial` state for downstream INP composition. */}
      <MaterialPickerPanel
        apiBase={apiBase}
        selectedMaterialId={selectedMaterial.id}
        onMaterialChange={onMaterialChange}
      />
      <BulletPlateBlueprintPanel />
        </div>
        )}
      </details>
    </div>
  )
}

// FM-04a Phase 41.4 (B.2) — disclosure styling for the "Evidence & Trust"
// wall. Injected <style> (mirrors the OnboardingTour keyframe pattern) so the
// native marker is removed cross-browser and the chevron rotates on open;
// hover/focus tint uses the shared design tokens.
const EVIDENCE_WALL_STYLES = `
.fm04a-evidence-summary { list-style: none; }
.fm04a-evidence-summary::-webkit-details-marker { display: none; }
.fm04a-evidence-summary::marker { content: ''; }
.fm04a-evidence-summary:hover { border-color: var(--border-strong); background: var(--accent-glow); }
.fm04a-evidence-wall[open] .fm04a-evidence-chevron { transform: rotate(90deg); }
`

const EVIDENCE_SUMMARY_STYLE: CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  gap: 'var(--sp-3)',
  padding: '14px var(--sp-4)',
  background: 'var(--bg-surface)',
  border: '1px solid var(--border)',
  borderRadius: '10px',
  cursor: 'pointer',
  userSelect: 'none',
  transition: 'border-color 140ms ease, background 140ms ease',
}

const EVIDENCE_CHEVRON_STYLE: CSSProperties = {
  display: 'inline-block',
  color: 'var(--text-muted)',
  fontSize: '12px',
  transition: 'transform 160ms ease',
  transform: 'rotate(0deg)',
}
