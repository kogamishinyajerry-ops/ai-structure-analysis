// FM-04a Phase 43 — NoResultState tests (additive).
//
// Tier 1 / Tier 2 engineering candidate; not signed validation; not
// benchmark agreement.
//
// Pins that NoResultState wraps the EmptyStateCard primitive with a
// headline + body, conditionally renders the "Browse cases" primary
// action, and wires it to onBrowseCases exactly once when clicked.

import { describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen } from '@testing-library/react'
import { NoResultState } from '../src/components/NoResultState'

describe('NoResultState', () => {
  it('renders a headline and body via EmptyStateCard', () => {
    render(<NoResultState />)
    const card = screen.getByTestId('empty-state-card')
    expect(card).toHaveTextContent('No result loaded yet')
    expect(card).toHaveTextContent(/run the solver to see the 3D result/i)
  })

  it('renders a primary action and fires onBrowseCases exactly once on click', () => {
    const onBrowseCases = vi.fn()
    render(<NoResultState onBrowseCases={onBrowseCases} />)
    const action = screen.getByTestId('empty-state-action')
    expect(action).toHaveTextContent('Browse cases')
    fireEvent.click(action)
    expect(onBrowseCases).toHaveBeenCalledTimes(1)
  })

  it('renders without an action when onBrowseCases is omitted (no crash)', () => {
    render(<NoResultState />)
    expect(screen.getByTestId('no-result-state')).toBeInTheDocument()
    expect(screen.queryByTestId('empty-state-action')).toBeNull()
  })
})
