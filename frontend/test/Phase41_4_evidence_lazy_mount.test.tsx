// FM-04a Phase 41.4 (retro P2-B) — evidence wall lazy-mount.
//
// The "Evidence & Trust" <details> previously kept its 22 child panels
// MOUNTED while collapsed (the disclosure only hid them visually), so their
// mount-time fetch effects fired on the boot first paint. The body is now
// rendered only once the disclosure is opened, so zero panel fetches hit the
// boot path. These tests lock that: body absent (and zero fetches) while
// collapsed; body present after opening. The outer visual-tab-panel container
// + the <summary> stay unconditional (Phase21D pins).

import { describe, expect, it, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { VisualTabPanel } from '../src/components/VisualTabPanel'
import { FALLBACK_MATERIALS } from '../src/materialsClient'

describe('VisualTabPanel — evidence wall lazy-mount (retro P2-B)', () => {
  let fetchSpy: ReturnType<typeof vi.fn>

  beforeEach(() => {
    fetchSpy = vi.fn(async () => ({
      ok: false,
      status: 404,
      json: async () => ({}),
      text: async () => '',
    }))
    vi.stubGlobal('fetch', fetchSpy)
  })

  const baseProps = {
    apiBase: 'http://localhost:8000/api/v1',
    selectedCandidateCaseId: 'GS-102-candidate',
    onSelectCandidateCaseId: vi.fn(),
    comparisonCaseA: null,
    comparisonCaseB: null,
    onSelectComparisonA: vi.fn(),
    onSelectComparisonB: vi.fn(),
    snapshotLabelA: null,
    snapshotLabelB: null,
    onSelectSnapshotLabelA: vi.fn(),
    onSelectSnapshotLabelB: vi.fn(),
    selectedMaterial: FALLBACK_MATERIALS[0],
    onMaterialChange: vi.fn(),
    latestSignoff: null,
    onLatestSignoff: vi.fn(),
  }

  it('keeps the container + summary but does NOT render the 22-panel body while collapsed', () => {
    render(<VisualTabPanel {...baseProps} />)
    // Phase21D pins: outer container + the disclosure shell are unconditional.
    expect(screen.getByTestId('visual-tab-panel')).toBeInTheDocument()
    expect(screen.getByTestId('evidence-trust-section')).toBeInTheDocument()
    // The panel body (and therefore all 22 panels + their fetches) is absent.
    expect(screen.queryByTestId('evidence-trust-body')).not.toBeInTheDocument()
  })

  it('does NOT fire any panel fetch on first paint while collapsed', () => {
    render(<VisualTabPanel {...baseProps} />)
    expect(fetchSpy).not.toHaveBeenCalled()
  })

  it('renders the 22-panel body once the disclosure is opened', () => {
    render(<VisualTabPanel {...baseProps} />)
    const details = screen.getByTestId('evidence-trust-section') as HTMLDetailsElement
    details.open = true
    fireEvent(details, new Event('toggle'))
    expect(screen.getByTestId('evidence-trust-body')).toBeInTheDocument()
    // and now the lazily-mounted panels do fetch
    expect(fetchSpy).toHaveBeenCalled()
  })
})
