// FM-04a Phase 18 D — Cmd-K command palette.
//
// Tier 1 / Tier 2 engineering candidate; not signed validation; not
// benchmark agreement.
//
// Renders a fuzzy-searchable list of commands. The host wires
// `useKeyboardShortcuts` to bind `mod+k` (Cmd-K) to opening the
// palette; the palette itself owns input + arrow nav + Enter.
//
// Anti-gaming guards (per Phase 18 blueprint §3.D T:-3):
//   * Commands are validated by `assertNoDuplicateCommandIds` on
//     mount so a registry merge conflict surfaces loudly.
//   * Escape always closes; tab is intentionally NOT trapped (the
//     reviewer can leave the palette without picking a command).

import { useEffect, useMemo, useRef, useState } from 'react'
import {
  assertNoDuplicateCommandIds,
  filterCommands,
  type Command,
} from '../commands/registry'

export interface CommandPaletteProps {
  /** Whether the palette is visible. Owner controls open/close. */
  readonly open: boolean
  /** Called when the user dismisses (Escape, click backdrop, picks a command). */
  readonly onClose: () => void
  /** Full command set; will be filtered by the typed query. */
  readonly commands: readonly Command[]
  /**
   * Optional initial query. Mainly for tests; production usually opens
   * with an empty input.
   */
  readonly initialQuery?: string
}

export function CommandPalette(props: CommandPaletteProps) {
  const { open, onClose, commands, initialQuery = '' } = props

  // Refuse duplicate ids loudly; the throw bubbles up to the error
  // boundary in production and trips the unit test directly.
  assertNoDuplicateCommandIds(commands)

  const [query, setQuery] = useState(initialQuery)
  const [activeIdx, setActiveIdx] = useState(0)
  const inputRef = useRef<HTMLInputElement | null>(null)

  const filtered = useMemo(
    () => filterCommands(commands, query),
    [commands, query],
  )

  // Reset active index whenever the filtered set changes shape.
  useEffect(() => {
    setActiveIdx(0)
  }, [query])

  // Auto-focus the input on open; restore the query to initialQuery
  // each time the palette opens fresh.
  useEffect(() => {
    if (open) {
      setQuery(initialQuery)
      // Defer focus to next tick so the input exists in the DOM.
      const t = setTimeout(() => inputRef.current?.focus(), 0)
      return () => clearTimeout(t)
    }
  }, [open, initialQuery])

  if (!open) return null

  const move = (delta: number): void => {
    if (filtered.length === 0) return
    setActiveIdx((cur) => {
      const next = cur + delta
      if (next < 0) return filtered.length - 1
      if (next >= filtered.length) return 0
      return next
    })
  }

  const invoke = (cmd: Command): void => {
    onClose()
    void cmd.handler()
  }

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label="Command palette"
      data-testid="command-palette"
      onClick={(e) => {
        // Click on the backdrop (this element) closes; click on the
        // inner card does not.
        if (e.target === e.currentTarget) onClose()
      }}
      style={backdropStyle}
    >
      <div style={cardStyle}>
        <input
          ref={inputRef}
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Escape') {
              e.preventDefault()
              onClose()
              return
            }
            if (e.key === 'ArrowDown') {
              e.preventDefault()
              move(1)
              return
            }
            if (e.key === 'ArrowUp') {
              e.preventDefault()
              move(-1)
              return
            }
            if (e.key === 'Enter') {
              e.preventDefault()
              const cmd = filtered[activeIdx]
              if (cmd !== undefined) invoke(cmd)
            }
          }}
          placeholder="Type a command — Cmd-K"
          aria-label="Command palette query"
          data-testid="command-palette-input"
          style={inputStyle}
        />
        <ul role="listbox" aria-label="Commands" style={listStyle}>
          {filtered.length === 0 && (
            <li style={emptyStyle} data-testid="command-palette-empty">
              No matching commands. Press Escape to close.
            </li>
          )}
          {filtered.map((cmd, idx) => {
            const active = idx === activeIdx
            return (
              <li
                key={cmd.id}
                role="option"
                aria-selected={active}
                data-testid={`command-palette-row-${cmd.id}`}
                data-active={active ? 'true' : 'false'}
                onMouseEnter={() => setActiveIdx(idx)}
                onClick={() => invoke(cmd)}
                style={active ? activeRowStyle : rowStyle}
              >
                <div style={labelRowStyle}>
                  <span style={labelStyle}>{cmd.label}</span>
                  {cmd.hotkey !== undefined && (
                    <kbd style={hotkeyStyle}>{cmd.hotkey}</kbd>
                  )}
                </div>
                <div style={categoryRowStyle}>
                  <span style={categoryStyle}>{cmd.category}</span>
                  {cmd.description !== undefined && (
                    <span style={descriptionStyle}>{cmd.description}</span>
                  )}
                </div>
              </li>
            )
          })}
        </ul>
      </div>
    </div>
  )
}

// Inline styles intentionally — no CSS-Modules / Tailwind step in
// Phase 18 D. The full design-system pass is Slice E+ territory.
const backdropStyle: React.CSSProperties = {
  position: 'fixed',
  inset: 0,
  background: 'rgba(0, 0, 0, 0.45)',
  display: 'flex',
  alignItems: 'flex-start',
  justifyContent: 'center',
  zIndex: 1000,
  paddingTop: '12vh',
}
const cardStyle: React.CSSProperties = {
  width: 'min(680px, 92vw)',
  background: 'var(--bg-surface)',
  color: 'var(--text-primary)',
  border: '1px solid var(--border)',
  borderRadius: 8,
  boxShadow: 'var(--elev-3)',
  overflow: 'hidden',
}
const inputStyle: React.CSSProperties = {
  width: '100%',
  background: 'var(--c-50)',
  color: 'var(--text-primary)',
  border: 'none',
  borderBottom: '1px solid var(--border)',
  padding: '14px 18px',
  fontSize: 16,
  outline: 'none',
  boxSizing: 'border-box',
}
const listStyle: React.CSSProperties = {
  listStyle: 'none',
  padding: 0,
  margin: 0,
  maxHeight: 420,
  overflowY: 'auto',
}
const emptyStyle: React.CSSProperties = {
  padding: '20px 18px',
  color: 'var(--text-muted)',
  fontSize: 14,
}
const rowStyle: React.CSSProperties = {
  padding: '10px 18px',
  cursor: 'pointer',
  borderBottom: '1px solid var(--border)',
}
const activeRowStyle: React.CSSProperties = {
  ...rowStyle,
  background: 'var(--c-100)',
}
const labelRowStyle: React.CSSProperties = {
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'center',
  gap: 12,
}
const labelStyle: React.CSSProperties = {
  fontSize: 14,
  fontWeight: 500,
}
const hotkeyStyle: React.CSSProperties = {
  background: 'var(--c-200)',
  borderRadius: 4,
  padding: '2px 6px',
  fontSize: 12,
  color: 'var(--text-muted)',
}
const categoryRowStyle: React.CSSProperties = {
  display: 'flex',
  gap: 10,
  marginTop: 2,
  alignItems: 'baseline',
}
const categoryStyle: React.CSSProperties = {
  fontSize: 11,
  textTransform: 'uppercase',
  letterSpacing: 0.6,
  color: 'var(--text-muted)',
}
const descriptionStyle: React.CSSProperties = {
  fontSize: 12,
  color: 'var(--text-muted)',
}
