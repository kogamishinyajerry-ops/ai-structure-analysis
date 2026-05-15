// FM-04a Phase 3 D — Convergence study viewer.
//
// Tier 1 engineering candidate; not signed validation; not benchmark agreement.
//
// Renders the orchestrator payload as two stacked tables (mesh sweep +
// dt sweep) with tone-coded per-axis verdict badges and a combined
// verdict badge. Read-only across `golden_samples/**`; data comes
// from /api/v1/convergence-study/<case-id> (Phase 3 D endpoint).

import { useEffect, useState } from 'react'
import type {
  ConvergenceStudy,
  ConvergenceStudyAxis,
} from '../convergenceStudyClient'
import {
  axisTone,
  combinedVerdictLabel,
  combinedVerdictTone,
  fetchConvergenceStudy,
  rowDeviationTone,
} from '../convergenceStudyClient'
import { TIER1_BANNER, type TrustCenterTone } from '../trustCenterSummary'

export interface ConvergenceStudyViewerProps {
  apiBase: string
  caseId: string | null
}

const SECTION_TITLE_STYLE = {
  fontSize: '0.7rem',
  textTransform: 'uppercase' as const,
  letterSpacing: '0.06em',
  color: 'var(--text-secondary)',
}

function toneColor(tone: TrustCenterTone): string {
  if (tone === 'accent') return 'var(--accent, #0a8a4a)'
  if (tone === 'warning') return 'var(--text-warning, #b8860b)'
  if (tone === 'danger') return 'var(--danger, #c0392b)'
  return 'var(--text-secondary)'
}

function VerdictBadge({ label, tone }: { label: string; tone: TrustCenterTone }) {
  return (
    <span
      style={{
        padding: '2px 8px',
        borderRadius: '999px',
        fontSize: '0.7rem',
        border: `1px solid ${toneColor(tone)}`,
        color: toneColor(tone),
        background: 'transparent',
      }}
      data-testid="convergence-verdict-badge"
    >
      {label}
    </span>
  )
}

function AxisTable({
  title,
  axis,
  tolerancePct,
  axisColumnName,
}: {
  title: string
  axis: ConvergenceStudyAxis
  tolerancePct: number
  axisColumnName: string
}) {
  // Reference = last run (finest in the sweep) — matches the orchestrator's
  // "previous → final" delta logic so rows already in the limit highlight.
  const reference = axis.runs.length > 0 ? axis.runs[axis.runs.length - 1].metricValue : 0
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
        <div style={SECTION_TITLE_STYLE}>{title}</div>
        <VerdictBadge
          label={axis.candidateStability}
          tone={axisTone(axis.candidateStability)}
        />
        <span style={{ fontSize: '0.65rem', color: 'var(--text-secondary)' }}>
          Δ={axis.relativeChangePct === null ? '—' : `${axis.relativeChangePct.toFixed(3)}%`}{' '}
          · tolerance ±{tolerancePct}% · held {axis.heldValueLabel || '—'}
        </span>
      </div>
      {axis.runs.length === 0 ? (
        <div style={{ fontSize: '0.72rem', color: 'var(--text-secondary)' }}>
          no runs on this axis
        </div>
      ) : (
        <>
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: '120px 140px 1fr',
              gap: '8px',
              fontSize: '0.65rem',
              color: 'var(--text-secondary)',
              padding: '3px 0',
              borderBottom: '1px solid var(--border)',
              textTransform: 'uppercase',
              letterSpacing: '0.06em',
            }}
          >
            <span>label</span>
            <span>{axisColumnName}</span>
            <span>metric (residual V m/s)</span>
          </div>
          {axis.runs.map((run, idx) => {
            const tone =
              idx === axis.runs.length - 1
                ? 'accent'
                : rowDeviationTone(reference, run.metricValue, tolerancePct)
            return (
              <div
                key={`${run.label}-${idx}`}
                style={{
                  display: 'grid',
                  gridTemplateColumns: '120px 140px 1fr',
                  gap: '8px',
                  fontSize: '0.72rem',
                  padding: '3px 0',
                  borderBottom: '1px solid var(--border)',
                  color: toneColor(tone),
                }}
              >
                <code style={{ overflowWrap: 'anywhere' }}>{run.label}</code>
                <code>{run.axisValue}</code>
                <code>{run.metricValue}</code>
              </div>
            )
          })}
        </>
      )}
    </div>
  )
}

export function ConvergenceStudyViewer({ apiBase, caseId }: ConvergenceStudyViewerProps) {
  const [study, setStudy] = useState<ConvergenceStudy | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (!caseId) {
      setStudy(null)
      setError(null)
      return
    }
    const controller = new AbortController()
    setLoading(true)
    fetchConvergenceStudy(apiBase, caseId, controller.signal)
      .then((result) => {
        setStudy(result.study)
        setError(result.error ?? null)
      })
      .finally(() => setLoading(false))
    return () => controller.abort()
  }, [apiBase, caseId])

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
      data-testid="convergence-study-viewer"
    >
      <div>
        <div style={{ ...SECTION_TITLE_STYLE, color: 'var(--text-warning, #b8860b)' }}>
          Convergence study
        </div>
        <div style={{ fontSize: '0.65rem', color: 'var(--text-secondary)' }}>
          {TIER1_BANNER}
        </div>
      </div>

      {loading && (
        <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
          loading convergence_study.json…
        </div>
      )}

      {!loading && !study && (
        <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
          {!caseId
            ? 'Select a candidate case above.'
            : (error ?? 'No convergence study available; run scripts/gs102_convergence_sweep.py.')}
        </div>
      )}

      {study && (
        <>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <VerdictBadge
              label={combinedVerdictLabel(study)}
              tone={combinedVerdictTone(study)}
            />
            <span style={{ fontSize: '0.7rem', color: 'var(--text-secondary)' }}>
              metric: {study.studyMetric}
            </span>
          </div>

          <AxisTable
            title="Mesh sweep"
            axis={study.meshSweep}
            tolerancePct={study.tolerancePct}
            axisColumnName="mesh_axis_value"
          />
          <AxisTable
            title="Dt sweep"
            axis={study.dtSweep}
            tolerancePct={study.tolerancePct}
            axisColumnName="dt_axis_value"
          />

          <div>
            <div style={SECTION_TITLE_STYLE}>Energy balance observation</div>
            <div style={{ fontSize: '0.72rem', color: 'var(--text-primary)' }}>
              status: <strong>{study.energyBalanceObservation.status}</strong> ·{' '}
              rows w/ balance err:{' '}
              {study.energyBalanceObservation.rowsWithBalanceError}/
              {study.energyBalanceObservation.rowsTotal}
              {study.energyBalanceObservation.meanPct !== null && (
                <>
                  {' '}· mean {study.energyBalanceObservation.meanPct.toFixed(2)}% ·{' '}
                  min {study.energyBalanceObservation.minPct?.toFixed(2)}% ·{' '}
                  max {study.energyBalanceObservation.maxPct?.toFixed(2)}%
                </>
              )}
            </div>
          </div>

          <div style={{ fontSize: '0.65rem', color: 'var(--text-secondary)' }}>
            {study.claimImpact}
          </div>
        </>
      )}
    </div>
  )
}
