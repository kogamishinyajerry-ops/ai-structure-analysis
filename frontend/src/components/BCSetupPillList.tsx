/**
 * BCSetupPillList — FM-04a Phase 38 D.
 *
 * A read-only "boundary conditions" pill list for the active candidate case.
 * Lifts the `bc_setup_panel` canonical surface from a 2.0/10 stub toward a
 * concrete read-only affordance: the novice can SEE which BCs the case kind
 * expects, even before any authoring UI exists.
 *
 * Phase 38 D friction fixes (Phase 37 D FINAL points 1-3):
 *   - #1 the App.tsx advisor row switches column → row (handled in App.tsx)
 *   - #2 BCSetupAdvisorCard hides once BCs are assigned (shouldShowBCSetupAdvisor)
 *   - #3 this pill list is the concrete read-only BC affordance
 *
 * Read-only by design: no authoring, no mutation. Tier 1 engineering
 * candidate; not signed validation; not benchmark agreement.
 */

import type { CandidateCaseRecord } from '../candidateCaseRegistry'

/**
 * Infer the boundary conditions a case KIND expects, from its caseId.
 * Read-only inference for display; the real BC authoring path is future
 * scope. Deterministic + pure so it is trivially unit-testable.
 */
export function assignedBCsForCaseKind(caseId: string): string[] {
  const id = caseId.toLowerCase()
  if (id.includes('cylinder') || id.includes('-pv'))
    return ['Internal pressure', 'Axial end restraint']
  if (id.includes('cantilever'))
    return [
      'Fixed end (encastre)',
      id.includes('modal') || id.includes('dynamic')
        ? 'Free vibration (no external load)'
        : 'Tip load',
    ]
  if (id.includes('plate-with-hole'))
    return ['Far-field tension', 'Symmetry edges']
  if (id.includes('plate-ss') || id.includes('simply-supported'))
    return ['Simply-supported edges', 'Uniform pressure']
  if (id.includes('euler') || id.includes('buckle') || id.includes('column'))
    return ['Pinned / clamped ends', 'Axial compression']
  if (id.includes('wedge-c3d6'))
    return ['Base z-clamp', 'Top prescribed displacement']
  if (id.includes('heat-transfer'))
    return ['Fixed boundary temperatures']
  if (id.includes('rod-wave') || id.includes('gs-102') || id.includes('ballistic'))
    return ['Impact velocity', 'Clamped supports']
  return ['Boundary conditions per case setup']
}

/**
 * Mount predicate for BCSetupAdvisorCard (Phase 38 D friction #2): the
 * advisor that HELPS set up BCs should hide once BCs are assigned. Absent
 * `bcAssigned` (the current default for every cohort case — none have BCs
 * assigned yet) reads as not-assigned, so the advisor shows.
 */
export function shouldShowBCSetupAdvisor(record: {
  bcAssigned?: boolean
}): boolean {
  return !record.bcAssigned
}

export interface BCSetupPillListProps {
  caseRecord: CandidateCaseRecord
}

export function BCSetupPillList({ caseRecord }: BCSetupPillListProps) {
  const bcs = assignedBCsForCaseKind(caseRecord.caseId)
  const assigned = Boolean(caseRecord.bcAssigned)

  return (
    <section
      role="region"
      aria-label="Boundary-condition setup summary"
      className="glass-panel"
      style={{ padding: '16px', minWidth: '240px', flex: '1 1 240px' }}
      data-testid="bc-setup-pill-list"
      data-bc-assigned={assigned ? 'true' : 'false'}
    >
      <h3 style={{ margin: '0 0 4px', fontSize: '0.8rem', color: 'var(--text-primary)' }}>
        {assigned ? 'Assigned BCs' : 'Expected BCs'}
      </h3>
      <p style={{ margin: '0 0 12px', fontSize: '0.7rem', color: 'var(--text-secondary)' }}>
        {assigned
          ? 'Boundary conditions assigned for this case.'
          : 'Boundary conditions this case kind expects — not yet assigned.'}
      </p>
      <ul
        style={{
          listStyle: 'none',
          margin: 0,
          padding: 0,
          display: 'flex',
          flexWrap: 'wrap',
          gap: '8px',
        }}
      >
        {bcs.map((bc) => (
          <li
            key={bc}
            data-testid="bc-pill"
            style={{
              fontSize: '0.7rem',
              padding: '4px 10px',
              borderRadius: '999px',
              color: assigned ? 'var(--accent)' : 'var(--text-secondary)',
              background: assigned ? 'var(--accent-glow)' : 'var(--bg-surface)',
              border: '1px solid var(--border)',
            }}
          >
            {bc}
          </li>
        ))}
      </ul>
    </section>
  )
}
