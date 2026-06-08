/**
 * WCAG 2.x contrast helper — FM-04a Phase 38 C.
 *
 * Implements the published WCAG 2.x relative-luminance + contrast-ratio
 * algorithm exactly (NOT an approximation) so the Phase 38 C contrast sweep
 * is reviewable against the spec (anti-gaming guard V:-1). Reference:
 * https://www.w3.org/TR/WCAG21/#dfn-relative-luminance
 * https://www.w3.org/TR/WCAG21/#dfn-contrast-ratio
 *
 * Tier 1 engineering candidate; not signed validation; not benchmark
 * agreement.
 */

/** Parse a #rgb or #rrggbb hex string to an [r, g, b] byte triple. */
export function hexToRgb(hex: string): [number, number, number] {
  const h = hex.trim().replace(/^#/, '')
  const full =
    h.length === 3
      ? h
          .split('')
          .map((c) => c + c)
          .join('')
      : h
  if (!/^[0-9a-fA-F]{6}$/.test(full)) {
    throw new Error(`invalid hex color: ${hex}`)
  }
  return [
    parseInt(full.slice(0, 2), 16),
    parseInt(full.slice(2, 4), 16),
    parseInt(full.slice(4, 6), 16),
  ]
}

/**
 * Linearise one 8-bit sRGB channel per WCAG 2.x:
 *   c8/255 -> c; c <= 0.03928 ? c/12.92 : ((c+0.055)/1.055)^2.4
 */
export function srgbChannelToLinear(channel8bit: number): number {
  const c = channel8bit / 255
  return c <= 0.03928 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4)
}

/** WCAG relative luminance L = 0.2126 R + 0.7152 G + 0.0722 B (linearised). */
export function computeRelativeLuminance(hex: string): number {
  const [r, g, b] = hexToRgb(hex)
  return (
    0.2126 * srgbChannelToLinear(r) +
    0.7152 * srgbChannelToLinear(g) +
    0.0722 * srgbChannelToLinear(b)
  )
}

/** WCAG contrast ratio (L_lighter + 0.05) / (L_darker + 0.05), in [1, 21]. */
export function computeContrastRatio(hexA: string, hexB: string): number {
  const la = computeRelativeLuminance(hexA)
  const lb = computeRelativeLuminance(hexB)
  const lighter = Math.max(la, lb)
  const darker = Math.min(la, lb)
  return (lighter + 0.05) / (darker + 0.05)
}

/**
 * WCAG 2.x AA pass: ratio >= 4.5 for normal text, >= 3.0 for large text
 * (>= 18.66px bold or >= 24px regular).
 */
export function meetsWCAG_AA(ratio: number, isLargeText = false): boolean {
  return ratio >= (isLargeText ? 3.0 : 4.5)
}

/**
 * Alpha-composite a semi-transparent foreground hex over an opaque
 * background hex, returning the resulting opaque hex. Needed to honestly
 * measure glass surfaces (e.g. `--bg-surface: rgba(30,41,59,0.5)` over
 * `--bg-base: #020617`): WCAG contrast is only defined for opaque colors,
 * so the effective composited color must be resolved first.
 */
export function compositeHexOver(
  fgHex: string,
  alpha: number,
  bgHex: string,
): string {
  const [fr, fg, fb] = hexToRgb(fgHex)
  const [br, bg, bb] = hexToRgb(bgHex)
  const blend = (f: number, b: number): number =>
    Math.round(f * alpha + b * (1 - alpha))
  const toHex = (n: number): string =>
    Math.max(0, Math.min(255, n)).toString(16).padStart(2, '0')
  return `#${toHex(blend(fr, br))}${toHex(blend(fg, bg))}${toHex(blend(fb, bb))}`
}
