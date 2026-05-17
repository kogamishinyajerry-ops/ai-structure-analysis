// FM-04a Phase 2 C — Workbench candidate-case picker component.
//
// Tier 1 engineering candidate; not signed validation; not benchmark agreement.
//
// Dropdown listing the on-disk `golden_samples/*-candidate/` cases plus
// a Tier 1 banner and the NOTES.md excerpt for the selected case. The
// caller drives the selection (`selectedCaseId` + `onSelect`) so the
// picker can live alongside other Workbench state.

import { useEffect, useState } from 'react'
import type { CandidateCaseRecord } from '../candidateCaseRegistry'
import {
  fetchCandidateCases,
  findCandidateCase,
  FALLBACK_CANDIDATE_CASES,
} from '../candidateCaseRegistry'

export interface CandidateCasePickerProps {
  apiBase: string
  selectedCaseId: string | null
  onSelect: (caseId: string) => void
}

export function CandidateCasePicker({
  apiBase,
  selectedCaseId,
  onSelect,
}: CandidateCasePickerProps) {
  const [cases, setCases] = useState<CandidateCaseRecord[]>(FALLBACK_CANDIDATE_CASES)
  const [source, setSource] = useState<'live' | 'fallback'>('fallback')
  const [error, setError] = useState<string | null>(null)
  const [claimImpact, setClaimImpact] = useState<string>(
    'Tier 1 candidate-case picker fallback list; not signed validation; not benchmark agreement',
  )

  useEffect(() => {
    const controller = new AbortController()
    fetchCandidateCases(apiBase, controller.signal).then((result) => {
      setCases(result.cases)
      setSource(result.source)
      setClaimImpact(result.claimImpact)
      setError(result.error ?? null)
    })
    return () => controller.abort()
  }, [apiBase])

  const selected = findCandidateCase(cases, selectedCaseId)

  return (
    <div
      style={{
        padding: '12px 16px',
        borderRadius: '10px',
        border: '1px solid var(--border)',
        background: 'var(--bg-surface)',
        display: 'grid',
        gridTemplateColumns: 'minmax(220px, 280px) 1fr',
        gap: '16px',
        alignItems: 'start',
      }}
      data-testid="candidate-case-picker"
    >
      <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
        <label
          style={{
            fontSize: '0.75rem',
            color: 'var(--text-secondary)',
            textTransform: 'uppercase',
            letterSpacing: '0.05em',
          }}
        >
          Candidate case
        </label>
        <select
          value={selectedCaseId ?? ''}
          onChange={(event) => onSelect(event.target.value)}
          style={{
            padding: '8px 10px',
            borderRadius: '8px',
            border: '1px solid var(--border)',
            background: 'var(--bg-surface)',
            color: 'var(--text-primary)',
          }}
          data-testid="candidate-case-select"
        >
          <option value="" disabled>
            Choose a Tier 1 candidate case…
          </option>
          {cases.map((c) => (
            <option key={c.caseId} value={c.caseId}>
              {/* Phase 18 E (round 3) — surface human displayLabel
                  when available; falls back to caseId for back-compat. */}
              {c.displayLabel ?? c.caseId}
            </option>
          ))}
        </select>
        <span
          style={{
            fontSize: '0.7rem',
            color:
              source === 'live'
                ? 'var(--text-secondary)'
                : 'var(--text-warning, #b8860b)',
          }}
        >
          source: {source === 'live' ? 'live /candidate-cases endpoint' : 'static fallback list'}
        </span>
        {error && (
          <span style={{ fontSize: '0.65rem', color: 'var(--text-secondary)' }}>
            {error}
          </span>
        )}
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
        <div
          style={{
            fontSize: '0.7rem',
            color: 'var(--text-warning, #b8860b)',
            textTransform: 'uppercase',
            letterSpacing: '0.05em',
          }}
          data-testid="candidate-case-tier-banner"
        >
          {selected?.claimTier ?? 'Tier 1 engineering candidate'} · not signed validation · not benchmark agreement
        </div>
        <div style={{ fontSize: '0.85rem', color: 'var(--text-primary)' }}>
          {selected?.notesExcerpt ?? 'Select a candidate case to see its NOTES excerpt.'}
        </div>
        <div
          style={{
            display: 'flex',
            gap: '12px',
            fontSize: '0.7rem',
            color: 'var(--text-secondary)',
            flexWrap: 'wrap',
          }}
        >
          <span>
            starter:{' '}
            <code data-testid="candidate-case-starter">
              {selected?.starterDeckRelpath ?? '—'}
            </code>
          </span>
          <span>
            engine:{' '}
            <code data-testid="candidate-case-engine">
              {selected?.engineDeckRelpath ?? '—'}
            </code>
          </span>
          <span>
            generator:{' '}
            <code data-testid="candidate-case-generator">
              {selected?.generatorScriptRelpath ?? 'n/a'}
            </code>
          </span>
        </div>
        <div style={{ fontSize: '0.65rem', color: 'var(--text-secondary)' }}>
          {claimImpact}
        </div>
      </div>
    </div>
  )
}
