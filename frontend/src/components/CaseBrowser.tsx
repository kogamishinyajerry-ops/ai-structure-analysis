// FM-04a Phase 37 A — CaseBrowser canonical case-picker surface.
//
// Tier 1 / Tier 2 engineering candidate; not signed validation;
// not benchmark agreement.
//
// First canonical-surface industrial-UI parity lift since the
// rubric v2.0 baseline (Phase 33 A). The 5 canonical surfaces
// described at `.planning/test_subagents/references/` set
// Hyperworks / Abaqus / ANSYS conventions; before Phase 37 A the
// case-picker pillar was rated 3.2/10 (flat list, no grouping,
// no filter, no preview). CaseBrowser delivers Hyperworks-style
// case browser conventions:
//
//   * Tree-style grouping by `solverKind` (matches the verdict YAML
//     enum: linear_static / modal / buckling / dynamic /
//     heat_transfer_steady_state / contact_pair_static). When a
//     case lacks a solverKind in the registry, it groups under
//     "uncategorized".
//   * Filter chip row — toggle individual solver-kind chips +
//     "Tier 2 validated only" filter chip + text search input
//     (matches against displayLabel + caseId, case-insensitive).
//   * Preview pane on the right showing the focused case's
//     displayLabel + claimTier + runnerAvailable badge + a short
//     orientation derived from the same caseId-pattern lookup
//     CaseOpenAdvisorCard uses (so the browse + open surfaces
//     give the reviewer consistent copy).
//
// Anti-gaming guards:
//   Q:-1 (NEW Phase 37) — preserves the CandidateCaseRecord data
//     contract; consumes the existing FALLBACK_CANDIDATE_CASES OR
//     the live-route payload unchanged. New test pin asserts the
//     12-cohort case list is fully rendered when grouping is
//     enabled.
//   I:-1 (Phase 34 carry) — does NOT modify Phase 19 D Sidebar.
//     The Sidebar still mounts as before; CaseBrowser is a NEW
//     surface that coexists.

import type { CSSProperties } from 'react'
import { useMemo, useState } from 'react'
import type { CandidateCaseRecord } from '../candidateCaseRegistry'
import { InContextHint } from './InContextHint'

export interface CaseBrowserProps {
  /** The cohort of candidate cases to browse. Pass the same array
   * the existing case-picker consumes. */
  readonly cases: readonly CandidateCaseRecord[]
  /** Optional currently-focused case id. When provided, the preview
   * pane renders that case's details. */
  readonly focusedCaseId?: string | null
  /** Selection callback. Fires when the user clicks a case row in
   * a group. The host wires this to the same handler the existing
   * Sidebar / palette already calls. */
  readonly onSelectCase: (caseId: string) => void
}

/** Phase 37 A — Hyperworks-style canonical case-browser surface.
 *
 * Renders a 2-pane layout: left = grouped + filterable case list,
 * right = focused-case preview. */
export function CaseBrowser({
  cases,
  focusedCaseId,
  onSelectCase,
}: CaseBrowserProps) {
  const [searchQuery, setSearchQuery] = useState('')
  const [activeKindFilters, setActiveKindFilters] = useState<ReadonlySet<string>>(
    new Set(),
  )
  const [tier2Only, setTier2Only] = useState(false)
  const [hoveredCaseId, setHoveredCaseId] = useState<string | null>(null)

  const previewCaseId = hoveredCaseId ?? focusedCaseId ?? null
  const previewCase = useMemo(
    () => cases.find((c) => c.caseId === previewCaseId) ?? null,
    [cases, previewCaseId],
  )

  const grouped = useMemo(
    () => groupAndFilterCases(cases, { searchQuery, activeKindFilters, tier2Only }),
    [cases, searchQuery, activeKindFilters, tier2Only],
  )

  // Stable solver-kind enum for the chip row.
  const allKinds = useMemo(() => {
    const set = new Set<string>()
    for (const c of cases) if (c.solverKind !== undefined) set.add(c.solverKind)
    return Array.from(set).sort()
  }, [cases])

  const toggleKindFilter = (kind: string) => {
    setActiveKindFilters((prev) => {
      const next = new Set(prev)
      if (next.has(kind)) next.delete(kind)
      else next.add(kind)
      return next
    })
  }

  const totalShown = grouped.reduce((acc, g) => acc + g.cases.length, 0)

  return (
    <section
      data-testid="case-browser"
      role="region"
      aria-label="Case browser — grouped by solver kind"
      style={rootStyle}
    >
      <InContextHint
        hintId="case-browser"
        label="Case browser"
        text="Pick a case to open. Filter by solver kind or search by name; the preview pane summarises what each case validates before you commit."
      />
      <header style={headerStyle}>
        <strong style={titleStyle}>Case browser</strong>
        <span
          data-testid="case-browser-count"
          style={countStyle}
        >{`${totalShown} of ${cases.length}`}</span>
      </header>

      <div style={filterRowStyle} data-testid="case-browser-filter-row">
        <input
          type="search"
          placeholder="Filter by name or id"
          aria-label="Filter cases by name or id"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          data-testid="case-browser-search-input"
          className="cb-search"
          style={searchInputStyle}
        />
        <button
          type="button"
          data-testid="case-browser-tier2-chip"
          aria-pressed={tier2Only}
          onClick={() => setTier2Only((v) => !v)}
          className="cb-chip"
          style={tier2Only ? chipActiveStyle : chipIdleStyle}
        >
          Tier 2 validated
        </button>
        {allKinds.map((kind) => (
          <button
            type="button"
            key={kind}
            data-testid={`case-browser-kind-chip-${kind}`}
            aria-pressed={activeKindFilters.has(kind)}
            onClick={() => toggleKindFilter(kind)}
            style={
              activeKindFilters.has(kind) ? chipActiveStyle : chipIdleStyle
            }
          >
            {prettyKind(kind)}
          </button>
        ))}
      </div>

      <div style={paneRowStyle}>
        <ol style={groupListStyle} data-testid="case-browser-group-list">
          {grouped.map((group) => (
            <li key={group.kind} style={groupItemStyle}>
              <div style={groupHeaderStyle} data-testid={`case-browser-group-${group.kind}`}>
                <span style={groupHeaderLabelStyle}>{prettyKind(group.kind)}</span>
                <span style={groupHeaderCountStyle}>{group.cases.length}</span>
              </div>
              <ul style={caseListStyle}>
                {group.cases.map((c) => (
                  <li key={c.caseId}>
                    <button
                      type="button"
                      onMouseEnter={() => setHoveredCaseId(c.caseId)}
                      onMouseLeave={() => setHoveredCaseId(null)}
                      onClick={() => onSelectCase(c.caseId)}
                      data-testid={`case-browser-row-${c.caseId}`}
                      data-active={focusedCaseId === c.caseId ? 'true' : undefined}
                      className="cb-case-card"
                      style={
                        focusedCaseId === c.caseId
                          ? caseRowActiveStyle
                          : caseRowIdleStyle
                      }
                    >
                      {c.displayLabel ?? c.caseId}
                    </button>
                  </li>
                ))}
              </ul>
            </li>
          ))}
          {grouped.length === 0 && (
            <li data-testid="case-browser-empty" style={emptyStateStyle}>
              No cases match the current filters.
            </li>
          )}
        </ol>

        <aside style={previewPaneStyle} data-testid="case-browser-preview-pane">
          {previewCase ? (
            <>
              <div style={previewHeaderStyle}>
                <strong style={previewTitleStyle}>
                  {previewCase.displayLabel ?? previewCase.caseId}
                </strong>
                {previewCase.runnerAvailable === false && (
                  <span
                    data-testid="case-browser-runner-badge"
                    style={runnerBadgeStyle}
                  >
                    demo · no live runner
                  </span>
                )}
              </div>
              <p style={previewMetaStyle}>
                <span style={previewMetaLabelStyle}>Tier:</span> {previewCase.claimTier}
              </p>
              {previewCase.solverKind !== undefined && (
                <p style={previewMetaStyle}>
                  <span style={previewMetaLabelStyle}>Solver kind:</span>{' '}
                  {prettyKind(previewCase.solverKind)}
                </p>
              )}
              <p style={previewBlurbStyle}>
                {previewBlurbFor(previewCase.caseId)}
              </p>
            </>
          ) : (
            <p style={previewEmptyStyle}>Hover or focus a case to preview it here.</p>
          )}
        </aside>
      </div>
    </section>
  )
}

/** Phase 37 A — pure helper: filter + group cases per current
 * UI controls. Exposed for testing. */
export function groupAndFilterCases(
  cases: readonly CandidateCaseRecord[],
  opts: {
    readonly searchQuery: string
    readonly activeKindFilters: ReadonlySet<string>
    readonly tier2Only: boolean
  },
): ReadonlyArray<{ readonly kind: string; readonly cases: readonly CandidateCaseRecord[] }> {
  const q = opts.searchQuery.trim().toLowerCase()
  const filtered = cases.filter((c) => {
    if (opts.tier2Only && !c.claimTier.toLowerCase().includes('tier 2')) {
      return false
    }
    if (opts.activeKindFilters.size > 0) {
      const kind = c.solverKind ?? 'uncategorized'
      if (!opts.activeKindFilters.has(kind)) return false
    }
    if (q.length > 0) {
      const hay = `${c.displayLabel ?? ''} ${c.caseId}`.toLowerCase()
      if (!hay.includes(q)) return false
    }
    return true
  })

  // Group by solverKind (or "uncategorized" when absent)
  const groups = new Map<string, CandidateCaseRecord[]>()
  for (const c of filtered) {
    const kind = c.solverKind ?? 'uncategorized'
    const bucket = groups.get(kind) ?? []
    bucket.push(c)
    groups.set(kind, bucket)
  }
  const out: { kind: string; cases: readonly CandidateCaseRecord[] }[] = []
  for (const kind of Array.from(groups.keys()).sort()) {
    out.push({ kind, cases: groups.get(kind) ?? [] })
  }
  return out
}

/** Phase 37 A — friendly label for a solver-kind enum value. */
export function prettyKind(kind: string): string {
  switch (kind) {
    case 'linear_static':
      return 'Linear static'
    case 'modal':
      return 'Modal'
    case 'buckling':
      return 'Buckling'
    case 'dynamic':
      return 'Dynamic'
    case 'heat_transfer_steady_state':
      return 'Heat transfer (steady state)'
    case 'contact_pair_static':
      return 'Contact pair (static)'
    case 'uncategorized':
      return 'Uncategorized'
    default:
      return kind
  }
}

/** Phase 37 A — preview blurb derived from caseId pattern. Matches
 * the Phase 35 A `orientationForCaseKind` lookup so the browse
 * surface and the case-open surface share their copy. */
export function previewBlurbFor(caseId: string): string {
  const id = caseId.toLowerCase()
  if (id.startsWith('hertz-contact-')) return 'Contact-mechanics candidate.'
  if (id.startsWith('cantilever-buckle')) return 'Linear buckling case.'
  if (id.startsWith('cantilever-dynamic')) return 'Dynamic cantilever case.'
  if (id.startsWith('cantilever-beam-modal') || id.startsWith('modal-cantilever'))
    return 'Modal analysis case.'
  if (id.startsWith('cantilever-')) return 'Cantilever beam case.'
  if (id.startsWith('cylinder-pv-')) return 'Pressure-vessel case.'
  if (id.startsWith('euler-column')) return 'Euler column buckling case.'
  if (id.startsWith('plate-with-hole')) return 'Stress-concentration case.'
  if (id.startsWith('plate-simply-supported') || id.startsWith('plate-ss-shell'))
    return 'Simply-supported plate case.'
  if (id.startsWith('heat-transfer-')) return 'Heat-transfer case.'
  if (id.startsWith('rod-wave-impact-energy-leak'))
    return 'Wave-propagation case in its known-bad configuration.'
  if (id.startsWith('rod-wave-impact-')) return 'Axial wave-propagation case.'
  if (id.startsWith('gs-1')) return 'Ballistic-impact demo case.'
  return 'Engineering candidate case.'
}

const rootStyle: CSSProperties = {
  borderRadius: 'var(--r-lg)',
  border: '1px solid var(--border)',
  background: 'var(--bg-surface)',
  padding: 'var(--sp-6)',
  display: 'flex',
  flexDirection: 'column',
  gap: 'var(--sp-4)',
  color: 'var(--text-primary)',
  boxShadow: 'var(--elev-2)',
}
const headerStyle: CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  gap: 10,
  justifyContent: 'space-between',
}
const titleStyle: CSSProperties = {
  fontSize: 'var(--fs-lg)',
  fontWeight: 700,
  letterSpacing: 'var(--tracking-tight)',
}
const countStyle: CSSProperties = {
  fontSize: 11,
  color: 'var(--text-secondary)',
  fontFamily:
    'ui-monospace, SFMono-Regular, "SF Mono", Menlo, monospace',
}
const filterRowStyle: CSSProperties = {
  display: 'flex',
  flexWrap: 'wrap',
  gap: 6,
  alignItems: 'center',
}
const searchInputStyle: CSSProperties = {
  flex: '1 1 200px',
  minWidth: 0,
  background: 'var(--c-50)',
  border: '1px solid var(--border)',
  color: 'var(--text-primary)',
  padding: '8px 12px',
  borderRadius: 'var(--r-sm)',
  fontSize: 'var(--fs-sm)',
}
const chipBase: CSSProperties = {
  fontSize: 11,
  padding: '4px 10px',
  borderRadius: 999,
  cursor: 'pointer',
  fontFamily: 'inherit',
}
const chipIdleStyle: CSSProperties = {
  ...chipBase,
  background: 'transparent',
  border: '1px solid var(--border)',
  color: 'var(--text-secondary)',
}
const chipActiveStyle: CSSProperties = {
  ...chipBase,
  background: 'var(--accent, #bd5d3a)',
  border: '1px solid var(--accent, #bd5d3a)',
  color: '#fff',
}
const paneRowStyle: CSSProperties = {
  display: 'grid',
  gridTemplateColumns: 'minmax(0, 1fr) minmax(220px, 280px)',
  gap: 12,
  alignItems: 'start',
}
const groupListStyle: CSSProperties = {
  margin: 0,
  paddingInlineStart: 0,
  listStyle: 'none',
  display: 'flex',
  flexDirection: 'column',
  gap: 8,
}
const groupItemStyle: CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  gap: 4,
}
const groupHeaderStyle: CSSProperties = {
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'center',
  fontSize: 11,
  textTransform: 'uppercase',
  letterSpacing: '0.06em',
  color: 'var(--text-secondary)',
}
const groupHeaderLabelStyle: CSSProperties = {}
const groupHeaderCountStyle: CSSProperties = {
  fontFamily:
    'ui-monospace, SFMono-Regular, "SF Mono", Menlo, monospace',
}
const caseListStyle: CSSProperties = {
  margin: 0,
  paddingInlineStart: 0,
  listStyle: 'none',
  display: 'flex',
  flexDirection: 'column',
  gap: 'var(--sp-1)',
}
const caseRowBase: CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'space-between',
  gap: 'var(--sp-3)',
  width: '100%',
  textAlign: 'left',
  fontSize: 'var(--fs-sm)',
  padding: 'var(--sp-3) var(--sp-4)',
  borderRadius: 'var(--r-md)',
  border: '1px solid transparent',
  cursor: 'pointer',
  fontFamily: 'inherit',
  color: 'var(--text-primary)',
}
const caseRowIdleStyle: CSSProperties = {
  ...caseRowBase,
  background: 'transparent',
}
const caseRowActiveStyle: CSSProperties = {
  ...caseRowBase,
  background: 'var(--accent-glow)',
  border: '1px solid var(--border-focus)',
}
const previewPaneStyle: CSSProperties = {
  borderRadius: 'var(--r-lg)',
  border: '1px solid var(--border)',
  background: 'var(--c-50)',
  padding: 'var(--sp-5)',
  display: 'flex',
  flexDirection: 'column',
  gap: 'var(--sp-2)',
  minHeight: 100,
  boxShadow: 'var(--elev-1)',
  position: 'sticky',
  top: 'var(--sp-4)',
}
const previewHeaderStyle: CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  gap: 6,
  flexWrap: 'wrap',
}
const previewTitleStyle: CSSProperties = {
  fontSize: 13,
  fontWeight: 600,
  flex: '1 1 auto',
  minWidth: 0,
}
const previewMetaStyle: CSSProperties = {
  margin: 0,
  fontSize: 12,
  color: 'var(--text-primary)',
  lineHeight: 1.45,
}
const previewMetaLabelStyle: CSSProperties = {
  color: 'var(--text-secondary)',
  fontSize: 11,
  textTransform: 'uppercase',
  letterSpacing: '0.05em',
  marginInlineEnd: 4,
}
const previewBlurbStyle: CSSProperties = {
  margin: '6px 0 0',
  fontSize: 12,
  fontStyle: 'italic',
  color: 'var(--text-secondary)',
  lineHeight: 1.45,
}
const previewEmptyStyle: CSSProperties = {
  margin: 0,
  fontSize: 12,
  color: 'var(--text-secondary)',
  fontStyle: 'italic',
}
const emptyStateStyle: CSSProperties = {
  margin: 0,
  fontSize: 12,
  color: 'var(--text-secondary)',
  fontStyle: 'italic',
  padding: '8px 10px',
}
const runnerBadgeStyle: CSSProperties = {
  fontSize: 10,
  fontFamily:
    'ui-monospace, SFMono-Regular, "SF Mono", Menlo, monospace',
  padding: '1px 6px',
  borderRadius: 6,
  background: 'rgba(179, 121, 26, 0.10)',
  border: '1px solid rgba(179, 121, 26, 0.30)',
  color: 'var(--warn-400)',
}
