// FM-04a Phase 18 D — command registry SSOT for the Cmd-K palette.
//
// Tier 1 / Tier 2 engineering candidate; not signed validation; not
// benchmark agreement.
//
// The Workbench command palette (`CommandPalette.tsx`) reads from this
// registry. Every reviewer action that should be discoverable by
// fuzzy-search registers a command here. The registry is a typed
// data structure (no runtime singleton) so test fixtures can build
// their own command sets.
//
// Anti-gaming guards (per Phase 18 blueprint §3.D T:-3):
//   * Every command exposes (id, label, handler); duplicate IDs
//     trip `assertNoDuplicateCommandIds`.
//   * Hotkey strings, when present, follow a canonical lowercase
//     `mod+letter` / `mod+shift+letter` shape pinned by tests.

export type CommandCategory =
  | 'navigation'
  | 'solver'
  | 'mesh'
  | 'material'
  | 'signoff'
  | 'view'
  | 'help'

export interface Command {
  /** Stable kebab-case identifier; must be unique across the registry. */
  readonly id: string
  /** Human-readable label shown in the palette + cheatsheet. */
  readonly label: string
  /** One-line description shown under the label when a row is focused. */
  readonly description?: string
  /** Optional keyboard shortcut string (e.g., `"mod+k"`, `"g 1"`). */
  readonly hotkey?: string
  /** Grouping category surfaced in the palette UI. */
  readonly category: CommandCategory
  /** Invoked when the user picks the command. */
  readonly handler: () => void | Promise<void>
}

/**
 * Refuse a registry that contains duplicate command IDs. Throws a
 * `RangeError` whose message lists every offending id (helps a
 * future maintainer find the merge conflict source).
 */
export function assertNoDuplicateCommandIds(commands: readonly Command[]): void {
  const seen = new Set<string>()
  const dupes: string[] = []
  for (const cmd of commands) {
    if (seen.has(cmd.id)) dupes.push(cmd.id)
    seen.add(cmd.id)
  }
  if (dupes.length > 0) {
    throw new RangeError(
      `command registry contains duplicate id(s): ${dupes.join(', ')}`,
    )
  }
}

/**
 * Lowercase + collapse whitespace so the fuzzy matcher can compare
 * apples to apples. Kept as its own helper so tests can pin the
 * normalisation rules.
 */
export function normaliseQuery(input: string): string {
  return input.trim().toLowerCase().replace(/\s+/g, ' ')
}

/**
 * Lightweight fuzzy match: returns `true` iff every character of
 * `needle` appears in `haystack` in order (not necessarily
 * contiguously). Case-insensitive via `normaliseQuery`.
 *
 * This is intentionally cheap and predictable; the palette does not
 * pull in a fuzzy-search library at Phase 18 D scope.
 */
export function fuzzyMatch(needle: string, haystack: string): boolean {
  const n = normaliseQuery(needle)
  const h = normaliseQuery(haystack)
  if (n === '') return true
  let i = 0
  for (const ch of h) {
    if (ch === n[i]) {
      i += 1
      if (i === n.length) return true
    }
  }
  return false
}

/**
 * Filter + rank the registry by a query string. Exact substring hits
 * sort above pure-fuzzy hits; otherwise stable ordering is preserved.
 */
export function filterCommands(
  registry: readonly Command[],
  query: string,
): Command[] {
  const q = normaliseQuery(query)
  if (q === '') return [...registry]
  type Scored = { cmd: Command; rank: number; idx: number }
  const scored: Scored[] = []
  for (let idx = 0; idx < registry.length; idx += 1) {
    const cmd = registry[idx]
    const label = normaliseQuery(cmd.label)
    const id = cmd.id.toLowerCase()
    let rank: number | null = null
    if (label.includes(q) || id.includes(q)) rank = 0
    else if (fuzzyMatch(q, cmd.label) || fuzzyMatch(q, cmd.id)) rank = 1
    if (rank !== null) scored.push({ cmd, rank, idx })
  }
  scored.sort((a, b) => (a.rank - b.rank) || (a.idx - b.idx))
  return scored.map((s) => s.cmd)
}
