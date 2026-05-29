// FM-04a Phase 18 E (round 2) — materials library picker panel.
//
// Tier 1 / Tier 2 engineering candidate; not signed validation; not
// benchmark agreement.
//
// Renders the materials library from /api/v1/materials/. When the
// reviewer picks a row, the panel surfaces the selected material's
// id + display label via the `onMaterialChange` callback so the
// host can compose downstream INP writes / solver re-runs.
//
// The panel falls back to the static library when the backend is
// unreachable, and surfaces the Tier 1 boundary banner inline.

import { useEffect, useState } from 'react'
import {
  fetchMaterials,
  formatDensity,
  formatPascalsAsGPa,
  formatPascalsAsMPa,
  type MaterialRecord,
} from '../materialsClient'
import { ErrorCard } from './ErrorCard'
import { SkeletonCard } from './SkeletonCard'

export interface MaterialPickerPanelProps {
  readonly apiBase: string
  readonly selectedMaterialId?: string | null
  readonly onMaterialChange?: (material: MaterialRecord) => void
}

export function MaterialPickerPanel(props: MaterialPickerPanelProps) {
  const { apiBase, selectedMaterialId, onMaterialChange } = props
  const [materials, setMaterials] = useState<MaterialRecord[] | null>(null)
  const [source, setSource] = useState<'live' | 'fallback' | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const ctrl = new AbortController()
    setLoading(true)
    fetchMaterials(apiBase, ctrl.signal)
      .then((res) => {
        setMaterials(res.materials)
        setSource(res.source)
        setError(res.error ?? null)
      })
      .finally(() => setLoading(false))
    return () => ctrl.abort()
  }, [apiBase])

  if (loading) {
    return (
      // FM-04a 41.4: keep the #material-picker-panel scroll anchor present during
      // load too — the palette 'open material picker' command (App.tsx) scrolls here
      // right after the lazy Evidence & Trust wall mounts, before the fetch resolves.
      <section id="material-picker-panel" style={panelStyle} aria-labelledby="material-picker-heading">
        <h3 id="material-picker-heading" style={headingStyle}>
          Materials library
        </h3>
        <SkeletonCard lines={4} label="Loading materials library" />
      </section>
    )
  }

  if (materials === null) {
    return (
      <section style={panelStyle}>
        <h3 style={headingStyle}>Materials library</h3>
        <ErrorCard
          title="Could not load materials"
          message={error ?? 'Unknown error fetching /api/v1/materials/.'}
          code="MATERIALS-LOAD"
          remediation={[
            'Check that the backend is running (`make backend`).',
            'Verify /api/v1/materials/ responds 200 (curl http://localhost:8000/api/v1/materials/).',
            'Reload the page once the backend is back.',
          ]}
        />
      </section>
    )
  }

  return (
    <section
      id="material-picker-panel"
      style={panelStyle}
      aria-labelledby="material-picker-heading"
      data-testid="material-picker-panel"
    >
      <header style={headerStyle}>
        <h3 id="material-picker-heading" style={headingStyle}>
          Materials library
        </h3>
        <span style={countBadgeStyle}>{materials.length} cited</span>
      </header>
      <p style={bannerStyle}>
        <strong>Tier 1 engineering candidate</strong>
        {' · '}not signed validation
        {' · '}not benchmark agreement
        {source === 'fallback' && (
          <>
            {' · '}
            <span data-testid="materials-fallback-marker" style={fallbackStyle}>
              static fallback (backend unreachable)
            </span>
          </>
        )}
      </p>
      <ul style={listStyle} role="listbox" aria-label="Materials">
        {materials.map((m) => {
          const selected = m.id === selectedMaterialId
          return (
            <li
              key={m.id}
              role="option"
              aria-selected={selected}
              data-testid={`material-row-${m.id}`}
              data-selected={selected ? 'true' : 'false'}
              onClick={() => onMaterialChange?.(m)}
              style={selected ? selectedRowStyle : rowStyle}
            >
              <div style={titleRowStyle}>
                <span style={nameStyle}>{m.name}</span>
                <span style={idPillStyle}>{m.id}</span>
              </div>
              <dl style={propsGridStyle}>
                <div style={propCellStyle}>
                  <dt style={dtStyle}>Young's modulus</dt>
                  <dd style={ddStyle}>{formatPascalsAsGPa(m.youngsModulusPa)}</dd>
                </div>
                <div style={propCellStyle}>
                  <dt style={dtStyle}>Poisson ratio</dt>
                  <dd style={ddStyle}>{m.poissonRatio.toFixed(3)}</dd>
                </div>
                <div style={propCellStyle}>
                  <dt style={dtStyle}>Density</dt>
                  <dd style={ddStyle}>{formatDensity(m.densityKgM3)}</dd>
                </div>
                {m.yieldStressPa !== null && (
                  <div style={propCellStyle}>
                    <dt style={dtStyle}>Yield stress</dt>
                    <dd style={ddStyle}>{formatPascalsAsMPa(m.yieldStressPa)}</dd>
                  </div>
                )}
                {m.ultimateStressPa !== null && (
                  <div style={propCellStyle}>
                    <dt style={dtStyle}>Ultimate stress</dt>
                    <dd style={ddStyle}>{formatPascalsAsMPa(m.ultimateStressPa)}</dd>
                  </div>
                )}
              </dl>
              <p style={referenceStyle}>
                <strong>Source: </strong>
                {m.reference}
              </p>
            </li>
          )
        })}
      </ul>
    </section>
  )
}

const panelStyle: React.CSSProperties = {
  background: '#161616',
  border: '1px solid #2a2a2a',
  borderRadius: 10,
  padding: 16,
  display: 'flex',
  flexDirection: 'column',
  gap: 10,
  color: '#e5e5e5',
}
const headerStyle: React.CSSProperties = {
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'baseline',
}
const headingStyle: React.CSSProperties = {
  margin: 0,
  fontSize: 14,
  fontWeight: 600,
  letterSpacing: 0.3,
  textTransform: 'uppercase',
  color: '#cfcfcf',
}
const countBadgeStyle: React.CSSProperties = {
  fontSize: 11,
  background: '#22303f',
  color: '#cfe4ff',
  padding: '2px 8px',
  borderRadius: 10,
}
const bannerStyle: React.CSSProperties = {
  margin: 0,
  fontSize: 11.5,
  color: '#9a9a9a',
  lineHeight: 1.5,
}
const fallbackStyle: React.CSSProperties = {
  color: '#e8b865',
}
const listStyle: React.CSSProperties = {
  listStyle: 'none',
  padding: 0,
  margin: 0,
  display: 'flex',
  flexDirection: 'column',
  gap: 8,
}
const rowStyle: React.CSSProperties = {
  background: '#1c1c1c',
  border: '1px solid #2c2c2c',
  borderRadius: 8,
  padding: 12,
  cursor: 'pointer',
  display: 'flex',
  flexDirection: 'column',
  gap: 8,
}
const selectedRowStyle: React.CSSProperties = {
  ...rowStyle,
  borderColor: '#3a5fa8',
  background: '#1f2940',
}
const titleRowStyle: React.CSSProperties = {
  display: 'flex',
  alignItems: 'baseline',
  justifyContent: 'space-between',
  gap: 8,
}
const nameStyle: React.CSSProperties = {
  fontSize: 14,
  fontWeight: 600,
  color: '#f0f0f0',
}
const idPillStyle: React.CSSProperties = {
  fontSize: 11,
  fontFamily:
    'ui-monospace, SFMono-Regular, "SF Mono", Menlo, monospace',
  color: '#9a9a9a',
}
const propsGridStyle: React.CSSProperties = {
  display: 'grid',
  gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))',
  gap: 8,
  margin: 0,
}
const propCellStyle: React.CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  gap: 2,
}
const dtStyle: React.CSSProperties = {
  fontSize: 11,
  color: '#888',
  textTransform: 'uppercase',
  letterSpacing: 0.4,
}
const ddStyle: React.CSSProperties = {
  margin: 0,
  fontSize: 13,
  fontWeight: 500,
  color: '#dcdcdc',
}
const referenceStyle: React.CSSProperties = {
  margin: 0,
  fontSize: 11.5,
  color: '#9a9a9a',
  lineHeight: 1.45,
  fontStyle: 'italic',
}
