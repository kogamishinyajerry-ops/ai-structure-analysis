// FM-04a Phase 18 D — frontend workbench primitives tests.
//
// Tier 1 / Tier 2 engineering candidate; not signed validation; not
// benchmark agreement.
//
// Covers the 6 new Slice D pieces: command registry, command palette,
// keyboard-shortcut hook, drift badge, skeleton card, error card,
// empty state card.
//
// Anti-gaming guards (per Phase 18 blueprint §3.D):
//   * T:-3 command registry rejects duplicate ids
//   * A:-2 keyboard shortcuts skip firing when text input has focus
//   * Drift badge severity coloring + sign formatting pinned
//   * Empty / loading / error cards expose stable a11y roles

import { describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen } from '@testing-library/react'
import {
  CommandPalette,
  type CommandPaletteProps,
} from '../src/components/CommandPalette'
import {
  DriftBadge,
  formatSignedPercent,
  severityFromPercent,
} from '../src/components/DriftBadge'
import { EmptyStateCard } from '../src/components/EmptyStateCard'
import { ErrorCard } from '../src/components/ErrorCard'
import { SkeletonCard } from '../src/components/SkeletonCard'
import {
  assertNoDuplicateCommandIds,
  filterCommands,
  fuzzyMatch,
  normaliseQuery,
  type Command,
} from '../src/commands/registry'
import {
  canonicalHotkey,
  shouldFire,
} from '../src/hooks/useKeyboardShortcuts'

// ---------------------------------------------------------------------
// Command registry
// ---------------------------------------------------------------------

describe('command registry', () => {
  const sample: readonly Command[] = [
    {
      id: 'open-palette',
      label: 'Open command palette',
      category: 'navigation',
      hotkey: 'mod+k',
      handler: () => undefined,
    },
    {
      id: 'switch-tab-visual',
      label: 'Switch to Visual tab',
      category: 'navigation',
      hotkey: 'g 1',
      handler: () => undefined,
    },
    {
      id: 'run-solver',
      label: 'Run CalculiX solver',
      category: 'solver',
      handler: () => undefined,
    },
  ]

  it('assertNoDuplicateCommandIds passes on a clean registry', () => {
    expect(() => assertNoDuplicateCommandIds(sample)).not.toThrow()
  })

  it('assertNoDuplicateCommandIds throws on duplicate ids and names them', () => {
    const dup = [...sample, { ...sample[0], label: 'Dupe' }]
    expect(() => assertNoDuplicateCommandIds(dup)).toThrow(/open-palette/)
  })

  it('normaliseQuery lowercases and collapses whitespace', () => {
    expect(normaliseQuery('  Hello   World ')).toBe('hello world')
    expect(normaliseQuery('')).toBe('')
  })

  it('fuzzyMatch matches in-order character subsequences', () => {
    expect(fuzzyMatch('rcs', 'Run CalculiX solver')).toBe(true)
    expect(fuzzyMatch('xxx', 'Run CalculiX solver')).toBe(false)
    expect(fuzzyMatch('', 'whatever')).toBe(true)
  })

  it('filterCommands ranks substring hits above fuzzy hits', () => {
    const out = filterCommands(sample, 'tab')
    expect(out[0].id).toBe('switch-tab-visual')
  })

  it('filterCommands returns all commands when query is empty', () => {
    expect(filterCommands(sample, '')).toHaveLength(sample.length)
  })

  it('filterCommands returns empty when nothing matches', () => {
    expect(filterCommands(sample, 'qqqqqq')).toEqual([])
  })
})

// ---------------------------------------------------------------------
// CommandPalette component
// ---------------------------------------------------------------------

describe('CommandPalette', () => {
  const commands: readonly Command[] = [
    {
      id: 'open-palette',
      label: 'Open command palette',
      category: 'navigation',
      hotkey: 'mod+k',
      handler: vi.fn(),
    },
    {
      id: 'switch-tab-visual',
      label: 'Switch to Visual tab',
      category: 'navigation',
      hotkey: 'g 1',
      handler: vi.fn(),
    },
    {
      id: 'run-solver',
      label: 'Run CalculiX solver',
      category: 'solver',
      handler: vi.fn(),
    },
  ]
  const baseProps: CommandPaletteProps = {
    open: true,
    onClose: vi.fn(),
    commands,
  }

  it('renders nothing when open=false', () => {
    render(<CommandPalette {...baseProps} open={false} />)
    expect(screen.queryByTestId('command-palette')).toBeNull()
  })

  it('renders dialog with input + all rows when open', () => {
    render(<CommandPalette {...baseProps} />)
    expect(screen.getByTestId('command-palette')).toBeInTheDocument()
    expect(screen.getByTestId('command-palette-input')).toBeInTheDocument()
    expect(screen.getByTestId('command-palette-row-open-palette')).toBeInTheDocument()
    expect(screen.getByTestId('command-palette-row-switch-tab-visual')).toBeInTheDocument()
    expect(screen.getByTestId('command-palette-row-run-solver')).toBeInTheDocument()
  })

  it('filters rows when the user types a query', () => {
    render(<CommandPalette {...baseProps} initialQuery="run" />)
    expect(screen.queryByTestId('command-palette-row-run-solver')).toBeInTheDocument()
    expect(screen.queryByTestId('command-palette-row-switch-tab-visual')).toBeNull()
  })

  it('shows empty-state message when no commands match', () => {
    render(<CommandPalette {...baseProps} initialQuery="zzzzzz" />)
    expect(screen.getByTestId('command-palette-empty')).toBeInTheDocument()
  })

  it('Escape key closes the palette', () => {
    const onClose = vi.fn()
    render(<CommandPalette {...baseProps} onClose={onClose} />)
    const input = screen.getByTestId('command-palette-input')
    fireEvent.keyDown(input, { key: 'Escape' })
    expect(onClose).toHaveBeenCalledTimes(1)
  })

  it('Enter on the active row invokes its handler and closes', () => {
    const handler = vi.fn()
    const onClose = vi.fn()
    const cmds: readonly Command[] = [
      {
        id: 'run',
        label: 'Run thing',
        category: 'solver',
        handler,
      },
    ]
    render(<CommandPalette open onClose={onClose} commands={cmds} />)
    const input = screen.getByTestId('command-palette-input')
    fireEvent.keyDown(input, { key: 'Enter' })
    expect(handler).toHaveBeenCalledTimes(1)
    expect(onClose).toHaveBeenCalledTimes(1)
  })

  it('clicking a row invokes its handler', () => {
    const handler = vi.fn()
    const cmds: readonly Command[] = [
      {
        id: 'pick-me',
        label: 'Pick me',
        category: 'view',
        handler,
      },
    ]
    render(<CommandPalette open onClose={vi.fn()} commands={cmds} />)
    fireEvent.click(screen.getByTestId('command-palette-row-pick-me'))
    expect(handler).toHaveBeenCalledTimes(1)
  })

  it('arrow keys move the active row indicator', () => {
    render(<CommandPalette {...baseProps} />)
    const input = screen.getByTestId('command-palette-input')
    // First row is active by default.
    expect(
      screen.getByTestId('command-palette-row-open-palette').getAttribute('data-active'),
    ).toBe('true')
    fireEvent.keyDown(input, { key: 'ArrowDown' })
    expect(
      screen.getByTestId('command-palette-row-switch-tab-visual').getAttribute('data-active'),
    ).toBe('true')
    fireEvent.keyDown(input, { key: 'ArrowUp' })
    expect(
      screen.getByTestId('command-palette-row-open-palette').getAttribute('data-active'),
    ).toBe('true')
  })

  it('refuses to render with duplicate command ids (T:-3)', () => {
    const dup: readonly Command[] = [
      {
        id: 'a',
        label: 'A',
        category: 'view',
        handler: vi.fn(),
      },
      {
        id: 'a',
        label: 'Also A',
        category: 'view',
        handler: vi.fn(),
      },
    ]
    expect(() =>
      render(<CommandPalette open onClose={vi.fn()} commands={dup} />),
    ).toThrow(/duplicate/i)
  })

  it('renders aria-modal=true and accessible name', () => {
    render(<CommandPalette {...baseProps} />)
    const dialog = screen.getByRole('dialog', { name: /command palette/i })
    expect(dialog).toBeInTheDocument()
    expect(dialog.getAttribute('aria-modal')).toBe('true')
  })
})

// ---------------------------------------------------------------------
// Keyboard shortcuts hook helpers
// ---------------------------------------------------------------------

describe('useKeyboardShortcuts helpers', () => {
  it('shouldFire returns false when an INPUT is focused (A:-2)', () => {
    const input = document.createElement('input')
    expect(shouldFire({}, input)).toBe(false)
  })

  it('shouldFire returns false when a TEXTAREA is focused', () => {
    const ta = document.createElement('textarea')
    expect(shouldFire({}, ta)).toBe(false)
  })

  it('shouldFire respects fireInTextInput=true override', () => {
    const input = document.createElement('input')
    expect(shouldFire({ fireInTextInput: true }, input)).toBe(true)
  })

  it('shouldFire returns true on body / no focus', () => {
    expect(shouldFire({}, null)).toBe(true)
    expect(shouldFire({}, document.body)).toBe(true)
  })

  it('canonicalHotkey converts a plain `k` keydown', () => {
    const ev = new KeyboardEvent('keydown', { key: 'k' })
    expect(canonicalHotkey(ev)).toBe('k')
  })

  it('canonicalHotkey converts a Cmd+K with shift modifier', () => {
    const ev = new KeyboardEvent('keydown', {
      key: 'K',
      ctrlKey: true,
      shiftKey: true,
    })
    // On non-Mac jsdom, ctrlKey is the mod; "mod+shift+k" expected.
    expect(canonicalHotkey(ev)).toBe('mod+shift+k')
  })
})

// ---------------------------------------------------------------------
// DriftBadge
// ---------------------------------------------------------------------

describe('DriftBadge', () => {
  it('formatSignedPercent prepends explicit sign and rounds to 1 dp', () => {
    expect(formatSignedPercent(2.5)).toBe('+2.5%')
    expect(formatSignedPercent(-3.07)).toBe('-3.1%')
    expect(formatSignedPercent(0)).toBe('+0.0%')
  })

  it('severityFromPercent thresholds info/warn/danger', () => {
    expect(severityFromPercent(0.5)).toBe('info')
    expect(severityFromPercent(2)).toBe('warn')
    expect(severityFromPercent(7)).toBe('danger')
    expect(severityFromPercent(-12)).toBe('danger')
  })

  it('renders text and accessible label', () => {
    render(
      <DriftBadge
        axis="trust_score"
        percentDelta={-3.2}
        severity="warn"
      />,
    )
    const node = screen.getByTestId('drift-badge')
    expect(node).toHaveTextContent('trust_score -3.2%')
    expect(node.getAttribute('aria-label')).toMatch(/drifted -3\.2%/)
    expect(node.getAttribute('data-severity')).toBe('warn')
    expect(node.getAttribute('data-axis')).toBe('trust_score')
  })

  it('respects ariaLabel override', () => {
    render(
      <DriftBadge
        axis="x"
        percentDelta={1}
        severity="info"
        ariaLabel="custom label"
      />,
    )
    expect(screen.getByTestId('drift-badge').getAttribute('aria-label')).toBe(
      'custom label',
    )
  })
})

// ---------------------------------------------------------------------
// SkeletonCard
// ---------------------------------------------------------------------

describe('SkeletonCard', () => {
  it('renders aria-busy with default 3 lines', () => {
    render(<SkeletonCard />)
    const card = screen.getByTestId('skeleton-card')
    expect(card.getAttribute('aria-busy')).toBe('true')
    expect(card.getAttribute('role')).toBe('status')
    expect(screen.getAllByTestId('skeleton-line')).toHaveLength(3)
  })

  it('respects custom line count', () => {
    render(<SkeletonCard lines={5} />)
    expect(screen.getAllByTestId('skeleton-line')).toHaveLength(5)
  })

  it('clamps line count to >=1', () => {
    render(<SkeletonCard lines={0} />)
    expect(screen.getAllByTestId('skeleton-line')).toHaveLength(1)
  })

  it('renders the optional sr-only label', () => {
    render(<SkeletonCard label="Loading cohort overview" />)
    expect(screen.getByText('Loading cohort overview')).toBeInTheDocument()
  })
})

// ---------------------------------------------------------------------
// ErrorCard
// ---------------------------------------------------------------------

describe('ErrorCard', () => {
  it('renders title and message with role=alert', () => {
    render(
      <ErrorCard
        title="Could not load cohort"
        message="The server returned 500."
      />,
    )
    const node = screen.getByTestId('error-card')
    expect(node.getAttribute('role')).toBe('alert')
    expect(node).toHaveTextContent('Could not load cohort')
    expect(node).toHaveTextContent('The server returned 500.')
  })

  it('renders remediation steps as ordered list', () => {
    render(
      <ErrorCard
        title="Solver failed"
        message="ccx exited non-zero."
        remediation={['Check the .inp file', 'Re-run with --verbose']}
      />,
    )
    const list = screen.getByTestId('error-remediation')
    expect(list.tagName).toBe('OL')
    expect(list).toHaveTextContent('Check the .inp file')
    expect(list).toHaveTextContent('Re-run with --verbose')
  })

  it('shows error code when provided', () => {
    render(
      <ErrorCard
        title="x"
        message="y"
        code="HTTP-500"
      />,
    )
    expect(screen.getByTestId('error-code')).toHaveTextContent('HTTP-500')
  })

  it('renders retry button when onRetry provided and invokes it', () => {
    const onRetry = vi.fn()
    render(<ErrorCard title="x" message="y" onRetry={onRetry} />)
    const btn = screen.getByTestId('error-retry')
    fireEvent.click(btn)
    expect(onRetry).toHaveBeenCalledTimes(1)
  })

  it('omits retry button when onRetry not provided', () => {
    render(<ErrorCard title="x" message="y" />)
    expect(screen.queryByTestId('error-retry')).toBeNull()
  })
})

// ---------------------------------------------------------------------
// EmptyStateCard
// ---------------------------------------------------------------------

describe('EmptyStateCard', () => {
  it('renders headline and body', () => {
    render(
      <EmptyStateCard
        headline="No cases yet"
        body="Pick a candidate case from the registry to start."
      />,
    )
    const card = screen.getByTestId('empty-state-card')
    expect(card).toHaveTextContent('No cases yet')
    expect(card).toHaveTextContent(
      'Pick a candidate case from the registry to start.',
    )
  })

  it('renders action button and fires onClick', () => {
    const onClick = vi.fn()
    render(
      <EmptyStateCard
        headline="x"
        body="y"
        action={{ label: 'Open registry', onClick }}
      />,
    )
    fireEvent.click(screen.getByTestId('empty-state-action'))
    expect(onClick).toHaveBeenCalledTimes(1)
  })

  it('omits action button when not provided', () => {
    render(<EmptyStateCard headline="x" body="y" />)
    expect(screen.queryByTestId('empty-state-action')).toBeNull()
  })

  it('exposes role=status for screen readers', () => {
    render(<EmptyStateCard headline="x" body="y" />)
    expect(
      screen.getByTestId('empty-state-card').getAttribute('role'),
    ).toBe('status')
  })
})
