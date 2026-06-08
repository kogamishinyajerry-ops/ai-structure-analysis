// FM-04a Phase 36 B — ErrorCard a11y / WCAG semantic pin +
// codeFriendly priority pin.
//
// Closes Phase 35 R3 novice_simulator friction points (c) and (d):
//   (c) ErrorCard's role="alert" / aria-live screen-reader semantics
//       need verification — this file makes them a hard pin.
//   (d) Verbatim UPLOAD / CASE-LOAD codes surfaced to novices look
//       like internal enums — codeFriendly takes priority for the
//       pill render; the raw code is preserved via data-error-code
//       for support-ticket scraping.
//
// Phase 18 D ErrorCard tests are NOT modified (I:-1 carryover);
// this file ADDS coverage. Phase 35 C hook tests are NOT touched.
//
// Anti-gaming guards:
//   P:-1 (NEW Phase 36) — WCAG assertions are semantic
//     (getByRole / getAttribute), not vibe-check role-attribute
//     presence
//   N:-1 (NEW Phase 36) — codeFriendly is a pure additive option
//     on ErrorCardProps + WithRecoveryOptions; the legacy `code`
//     field is preserved as a fallback

import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import { ErrorCard } from '../src/components/ErrorCard'

describe('Phase 36 B — ErrorCard WCAG semantics (friction point c)', () => {
  it('queryByRole("alert") finds the card with its accessible name', () => {
    render(
      <ErrorCard
        title="Could not load case cantilever-beam-candidate"
        message="The backend did not return a report."
      />,
    )
    const alert = screen.getByRole('alert', {
      name: /Could not load case cantilever-beam-candidate/i,
    })
    expect(alert).toBeTruthy()
  })

  it('the alert region carries aria-live="assertive"', () => {
    render(<ErrorCard title="x" message="y" />)
    const alert = screen.getByRole('alert')
    expect(alert.getAttribute('aria-live')).toBe('assertive')
  })

  it('the warning icon is aria-hidden (decorative)', () => {
    const { container } = render(<ErrorCard title="x" message="y" />)
    const icon = container.querySelector('[aria-hidden="true"]')
    expect(icon).toBeTruthy()
    expect(icon?.textContent).toBe('⚠')
  })

  it('the retry button is reachable by role name "Retry"', () => {
    const onRetry = () => undefined
    render(<ErrorCard title="x" message="y" onRetry={onRetry} />)
    const button = screen.getByRole('button', { name: /retry/i })
    expect(button).toBeTruthy()
  })
})

describe('Phase 36 B — codeFriendly priority pin (friction point d)', () => {
  it('renders codeFriendly in the pill when present', () => {
    render(
      <ErrorCard
        title="x"
        message="y"
        code="UPLOAD"
        codeFriendly="Upload"
      />,
    )
    const pill = screen.getByTestId('error-code')
    expect(pill.textContent).toBe('Upload')
  })

  it('falls back to code when codeFriendly is absent', () => {
    render(<ErrorCard title="x" message="y" code="UPLOAD" />)
    const pill = screen.getByTestId('error-code')
    expect(pill.textContent).toBe('UPLOAD')
  })

  it('preserves the raw code in data-error-code for support scraping', () => {
    render(
      <ErrorCard
        title="x"
        message="y"
        code="PDF-EXPORT"
        codeFriendly="PDF export"
      />,
    )
    const pill = screen.getByTestId('error-code')
    expect(pill.textContent).toBe('PDF export')
    expect(pill.getAttribute('data-error-code')).toBe('PDF-EXPORT')
  })

  it('omits the pill entirely when neither code nor codeFriendly is provided', () => {
    render(<ErrorCard title="x" message="y" />)
    expect(screen.queryByTestId('error-code')).toBeNull()
  })
})
