// FM-04a Phase 18 D — global keyboard shortcut hook.
//
// Tier 1 / Tier 2 engineering candidate; not signed validation; not
// benchmark agreement.
//
// Binds a set of keyboard shortcuts at the `window` level. Skips
// firing when focus is inside a text editor (input, textarea,
// contenteditable) — without this guard, hitting `s` to "submit
// signoff" would also drop an `s` character into whatever the
// reviewer is typing.
//
// Anti-gaming guards (per Phase 18 blueprint §3.D A:-2):
//   * `shouldFire` is exported so the unit tests can verify the
//     text-input guard explicitly without faking a DOM focus.

import { useEffect } from 'react'

export interface ShortcutBinding {
  /** Canonical key string: `"mod+k"`, `"g 1"`, `"s"`, `"?"`. */
  readonly hotkey: string
  /** Invoked when the hotkey fires. */
  readonly handler: (event: KeyboardEvent) => void
  /**
   * When `true`, fires even if the user is typing in a text input.
   * Defaults to `false` (the safe choice; Cmd-K is the rare exception
   * because the palette IS the text input).
   */
  readonly fireInTextInput?: boolean
}

/**
 * Decide whether a shortcut should fire given the active element
 * and the binding's `fireInTextInput` flag.
 *
 * Exported so tests can verify the policy without DOM focus.
 */
export function shouldFire(
  binding: Pick<ShortcutBinding, 'fireInTextInput'>,
  activeElement: Element | null,
): boolean {
  if (binding.fireInTextInput === true) return true
  if (activeElement === null) return true
  const tag = activeElement.tagName.toUpperCase()
  if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return false
  // contenteditable hosts behave like text inputs.
  const editable = (activeElement as HTMLElement).isContentEditable
  if (editable === true) return false
  return true
}

/**
 * Convert a `KeyboardEvent` to its canonical hotkey string for
 * matching against `ShortcutBinding.hotkey`. The string format:
 *
 *   * Modifier `mod` = Cmd on macOS, Ctrl elsewhere (mirrors the
 *     web convention used by VS Code / GitHub).
 *   * Plus-separated lowercase tokens (e.g., `"mod+shift+k"`).
 *   * Bare keys are single characters or special names: `"?"`,
 *     `"escape"`, `"arrowdown"`.
 *
 * Exported so tests can verify the conversion.
 */
export function canonicalHotkey(event: KeyboardEvent): string {
  const parts: string[] = []
  const isMac =
    typeof navigator !== 'undefined' &&
    /Mac|iPhone|iPad|iPod/i.test(navigator.platform ?? '')
  const mod = isMac ? event.metaKey : event.ctrlKey
  if (mod) parts.push('mod')
  if (event.shiftKey) parts.push('shift')
  if (event.altKey) parts.push('alt')
  const key = event.key.toLowerCase()
  // Skip modifier keys themselves (Shift-down alone shouldn't fire).
  if (key === 'control' || key === 'meta' || key === 'shift' || key === 'alt') {
    return parts.join('+')
  }
  parts.push(key)
  return parts.join('+')
}

/**
 * Bind a set of keyboard shortcuts at the window level.
 *
 * The hook re-registers when the binding list changes; tests that
 * mount a component with different bindings get the right behavior
 * without manual cleanup.
 */
export function useKeyboardShortcuts(bindings: readonly ShortcutBinding[]): void {
  useEffect(() => {
    const handler = (event: KeyboardEvent): void => {
      const fired = canonicalHotkey(event)
      for (const binding of bindings) {
        if (binding.hotkey.toLowerCase() !== fired) continue
        if (!shouldFire(binding, document.activeElement)) continue
        binding.handler(event)
      }
    }
    window.addEventListener('keydown', handler)
    return () => {
      window.removeEventListener('keydown', handler)
    }
  }, [bindings])
}
