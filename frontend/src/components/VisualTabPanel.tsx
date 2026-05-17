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

import { useCallback } from 'react'
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
      style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}
    >
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
  )
}
