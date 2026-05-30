// FM-04a Phase 3 C — Case comparison reviewer panel.
//
// Tier 1 engineering candidate; not signed validation; not benchmark agreement.
//
// Two-dropdown picker (a / b) driven by `candidateCaseRegistry`. Fetches
// `/api/v1/case-comparison?a=<id>&b=<id>` and renders a structured diff
// table with tone-coded cells:
//   ≤  5% delta → accent
//   ≤ 15% delta → warning
//    > 15% delta → danger
// The comparison is case-vs-case; both inputs are Tier 1 candidate
// acceptance packets and the panel surfaces the boundary explicitly.

import { useEffect, useState } from 'react'
import type { CandidateCaseRecord } from '../candidateCaseRegistry'
import type { CaseComparison, DeltaTone } from '../caseComparisonClient'
import {
  absoluteDeltaTone,
  fetchCaseComparison,
  numericDeltaTone,
} from '../caseComparisonClient'
import { TIER1_BANNER } from '../trustCenterSummary'

export interface CaseComparisonPanelProps {
  apiBase: string
  cases: CandidateCaseRecord[]
  caseA: string | null
  caseB: string | null
  onSelectA: (caseId: string) => void
  onSelectB: (caseId: string) => void
}

const SECTION_TITLE_STYLE = {
  fontSize: '0.7rem',
  textTransform: 'uppercase' as const,
  letterSpacing: '0.06em',
  color: 'var(--text-secondary)',
}

/**
 * Phase 34 A — analysis-type-aware axis-label visibility.
 *
 * The CaseComparison schema (Phase 3 C) was designed for ballistic
 * impact analyses and includes hard-coded ballistic axes (residual
 * velocity / perforation marker / energy balance). For non-ballistic
 * cases (cantilever-static, plate-with-hole, modal, heat-transfer,
 * etc.), the backend returns null/empty for these axes. Phase 33 C
 * novice_simulator triple-flagged the resulting dash-filled
 * ballistic-labelled rows as a high-friction event across P1+P2+P5
 * personas ("residual velocity? perforation? this is a cantilever
 * beam").
 *
 * The fix: when ALL ballistic-specific axes report no data, hide the
 * ballistic rows and show a clear "not applicable for this analysis"
 * notice. Convergence verdict + artifact diffs are analysis-type-
 * neutral and remain rendered.
 *
 * NOT changed: CSV export schema, backend response schema, the
 * ballistic comparison rendering itself (preserved when ballistic
 * cases ARE compared — Phase 25 D + Phase 3 C invariants honored).
 */
function hasAnyBallisticAxisData(comparison: CaseComparison): boolean {
  const rv = comparison.residualVelocityDiff
  const pm = comparison.perforationMarkerDiff
  const eb = comparison.energyBalanceErrorDiff
  return (
    rv.a !== null ||
    rv.b !== null ||
    pm.a !== null ||
    pm.b !== null ||
    eb.a !== null ||
    eb.b !== null
  )
}

function toneColor(tone: DeltaTone): string {
  if (tone === 'accent') return 'var(--accent, #bd5d3a)'
  if (tone === 'warning') return 'var(--text-warning, var(--warn-400))'
  if (tone === 'danger') return 'var(--danger, var(--danger-400))'
  return 'var(--text-secondary)'
}

function CaseDropdown({
  label,
  value,
  options,
  onSelect,
}: {
  label: string
  value: string | null
  options: CandidateCaseRecord[]
  onSelect: (caseId: string) => void
}) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
      <label style={SECTION_TITLE_STYLE}>{label}</label>
      <select
        value={value ?? ''}
        onChange={(event) => onSelect(event.target.value)}
        style={{
          padding: '6px 8px',
          borderRadius: '8px',
          border: '1px solid var(--border)',
          background: 'var(--bg-surface)',
          color: 'var(--text-primary)',
          fontSize: '0.8rem',
        }}
        data-testid={`case-comparison-${label.toLowerCase()}-select`}
      >
        <option value="" disabled>
          Choose…
        </option>
        {options.map((c) => (
          <option key={c.caseId} value={c.caseId}>
            {c.caseId}
          </option>
        ))}
      </select>
    </div>
  )
}

function DiffRow({
  axis,
  a,
  b,
  delta,
  tone,
}: {
  axis: string
  a: string
  b: string
  delta: string
  tone: DeltaTone
}) {
  return (
    <div
      style={{
        display: 'grid',
        gridTemplateColumns: '200px 1fr 1fr 140px',
        gap: '8px',
        fontSize: '0.78rem',
        padding: '4px 0',
        borderBottom: '1px solid var(--border)',
        color: 'var(--text-primary)',
        alignItems: 'baseline',
      }}
    >
      <span style={{ color: 'var(--text-secondary)' }}>{axis}</span>
      <code style={{ overflowWrap: 'anywhere' }}>{a}</code>
      <code style={{ overflowWrap: 'anywhere' }}>{b}</code>
      <strong style={{ color: toneColor(tone) }}>{delta}</strong>
    </div>
  )
}

function renderArtifactBucket(label: string, kinds: string[]) {
  if (kinds.length === 0) return null
  return (
    <div style={{ fontSize: '0.72rem', color: 'var(--text-primary)' }}>
      <strong>{label}:</strong> {kinds.join(', ')}
    </div>
  )
}

export function CaseComparisonPanel({
  apiBase,
  cases,
  caseA,
  caseB,
  onSelectA,
  onSelectB,
}: CaseComparisonPanelProps) {
  const [comparison, setComparison] = useState<CaseComparison | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (!caseA || !caseB) {
      setComparison(null)
      setError(null)
      return
    }
    const controller = new AbortController()
    setLoading(true)
    fetchCaseComparison(apiBase, caseA, caseB, controller.signal)
      .then((result) => {
        setComparison(result.comparison)
        setError(result.error ?? null)
      })
      .finally(() => setLoading(false))
    return () => controller.abort()
  }, [apiBase, caseA, caseB])

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
      data-testid="case-comparison-panel"
    >
      <div>
        <div style={{ ...SECTION_TITLE_STYLE, color: 'var(--text-warning, var(--warn-400))' }}>
          Case-vs-case comparison
        </div>
        <div style={{ fontSize: '0.65rem', color: 'var(--text-secondary)' }}>
          {TIER1_BANNER} · case-vs-case only (not vs experimental benchmark)
        </div>
      </div>

      <div
        style={{
          display: 'grid',
          gridTemplateColumns: '1fr 1fr',
          gap: '12px',
        }}
      >
        <CaseDropdown label="A" value={caseA} options={cases} onSelect={onSelectA} />
        <CaseDropdown label="B" value={caseB} options={cases} onSelect={onSelectB} />
      </div>

      {loading && (
        <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
          building comparison…
        </div>
      )}

      {!loading && !comparison && (
        <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
          {!caseA || !caseB
            ? 'Pick two candidate cases above to see a structured diff.'
            : (error ?? 'No comparison available.')}
        </div>
      )}

      {comparison && (
        <>
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: '200px 1fr 1fr 140px',
              gap: '8px',
              fontSize: '0.65rem',
              color: 'var(--text-secondary)',
              padding: '4px 0',
              borderBottom: '1px solid var(--border)',
              textTransform: 'uppercase',
              letterSpacing: '0.06em',
            }}
          >
            <span>axis</span>
            <span>case A · {comparison.caseA}</span>
            <span>case B · {comparison.caseB}</span>
            <span>delta</span>
          </div>

          {hasAnyBallisticAxisData(comparison) ? (
            <>
              <DiffRow
                axis="residual velocity"
                a={
                  comparison.residualVelocityDiff.a !== null
                    ? `${comparison.residualVelocityDiff.a} m/s`
                    : '—'
                }
                b={
                  comparison.residualVelocityDiff.b !== null
                    ? `${comparison.residualVelocityDiff.b} m/s`
                    : '—'
                }
                delta={
                  comparison.residualVelocityDiff.deltaPct !== null
                    ? `${comparison.residualVelocityDiff.deltaPct.toFixed(2)}%`
                    : '—'
                }
                tone={numericDeltaTone(comparison.residualVelocityDiff)}
              />

              <DiffRow
                axis="perforation marker"
                a={comparison.perforationMarkerDiff.a ?? '—'}
                b={comparison.perforationMarkerDiff.b ?? '—'}
                delta={comparison.perforationMarkerDiff.sameMarker ? 'same' : 'differ'}
                tone={comparison.perforationMarkerDiff.sameMarker ? 'accent' : 'danger'}
              />

              <DiffRow
                axis="energy balance error"
                a={
                  comparison.energyBalanceErrorDiff.a !== null
                    ? `${comparison.energyBalanceErrorDiff.a}%`
                    : '—'
                }
                b={
                  comparison.energyBalanceErrorDiff.b !== null
                    ? `${comparison.energyBalanceErrorDiff.b}%`
                    : '—'
                }
                delta={
                  comparison.energyBalanceErrorDiff.deltaAbsPct !== null
                    ? `${comparison.energyBalanceErrorDiff.deltaAbsPct.toFixed(2)}%`
                    : '—'
                }
                tone={absoluteDeltaTone(comparison.energyBalanceErrorDiff)}
              />

              <DiffRow
                axis="energy audit status"
                a={comparison.energyAuditStatusDiff.a}
                b={comparison.energyAuditStatusDiff.b}
                delta={comparison.energyAuditStatusDiff.bothClosed ? 'both closed' : 'differ'}
            tone={comparison.energyAuditStatusDiff.bothClosed ? 'accent' : 'warning'}
          />

            </>
          ) : (
            <div
              data-testid="case-comparison-non-ballistic-notice"
              style={{
                fontSize: '0.72rem',
                color: 'var(--text-secondary)',
                padding: '8px 10px',
                borderRadius: '6px',
                background: 'var(--bg-muted, var(--c-100))',
                border: '1px dashed var(--border)',
                lineHeight: 1.5,
              }}
            >
              Residual-velocity / perforation-marker / energy-balance axes apply to
              ballistic-impact analyses. Neither selected case reports these signals,
              so they are hidden. Convergence verdict and artifact diffs below remain
              applicable to all analysis types.
            </div>
          )}

          <DiffRow
            axis="convergence verdict"
            a={comparison.convergenceVerdictDiff.a}
            b={comparison.convergenceVerdictDiff.b}
            delta={comparison.convergenceVerdictDiff.sameVerdict ? 'same' : 'differ'}
            tone={comparison.convergenceVerdictDiff.sameVerdict ? 'accent' : 'warning'}
          />

          <div>
            <div style={SECTION_TITLE_STYLE}>Deck artifact diff</div>
            {renderArtifactBucket('shared', comparison.deckArtifactDiff.shared)}
            {renderArtifactBucket('a only', comparison.deckArtifactDiff.aOnly)}
            {renderArtifactBucket('b only', comparison.deckArtifactDiff.bOnly)}
            {comparison.deckArtifactDiff.hashChanged.length > 0 && (
              <div style={{ fontSize: '0.72rem', color: 'var(--text-warning, var(--warn-400))' }}>
                <strong>hash changed:</strong>{' '}
                {comparison.deckArtifactDiff.hashChanged.map((h) => h.kind).join(', ')}
              </div>
            )}
          </div>

          <div>
            <div style={SECTION_TITLE_STYLE}>Evidence artifact diff</div>
            {renderArtifactBucket('shared', comparison.evidenceArtifactDiff.shared)}
            {renderArtifactBucket('a only', comparison.evidenceArtifactDiff.aOnly)}
            {renderArtifactBucket('b only', comparison.evidenceArtifactDiff.bOnly)}
            {comparison.evidenceArtifactDiff.hashChanged.length > 0 && (
              <div style={{ fontSize: '0.72rem', color: 'var(--text-warning, var(--warn-400))' }}>
                <strong>hash changed:</strong>{' '}
                {comparison.evidenceArtifactDiff.hashChanged.map((h) => h.kind).join(', ')}
              </div>
            )}
          </div>

          <div style={{ fontSize: '0.65rem', color: 'var(--text-secondary)' }}>
            generated {comparison.generatedAtUtc} · {comparison.claimImpact}
          </div>
        </>
      )}
    </div>
  )
}
