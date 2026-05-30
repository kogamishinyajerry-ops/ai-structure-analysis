# FM-04a Phase 42 — Codex review R0 (warm-light "Claude app" UI redesign)

> ADR-026 risk-tier: cross-≥3-file frontend refactor (51 files) + a backend
> reporting-path touch (`_viz_helpers.py` plot fallback HTML). Relay: CRS
> effort=high (86gs xhigh relay truncated mid-review on the large diff — a
> different failure mode from the milestone-long 502s; switched per the
> degraded-path protocol). Round cap = 3; this is R0.

## Scope

User verdict on the prior dark-slate/emerald theme: **"UI设计灾难 · 重文字 + 配色暗淡"**.
Pivoted the whole workbench to the Claude-app aesthetic.

| Area | Change |
|---|---|
| `frontend/src/index.css` | Foundation re-themed dark→warm-light (token NAMES preserved → all `var(--token)` consumers flip for free): warm paper bg, warm-ink text, clay/coral accent, white cards + hairline borders + soft warm shadows, generous radii. New `--success` sage-green token (validated/pass ≠ coral). Accent `#b3552f` + status text tokens tuned for white-text / text-on-white AA. |
| 43 components | 271 color values migrated via a parallel agent workflow (one agent/file, context-aware rule sheet). Neutral chrome→light tokens; semantic status (warn/danger/info/success) preserved; data-viz colormaps + the dark 3D canvas/HUD intentionally kept. Agents also fixed latent dark-island bugs (undefined `var(--surface)` / `var(--token,#darkfallback)`). |
| `Topbar.tsx` (hand) | Fixed invisible dropdowns (`#fff` text on now-white `--bg-surface`); coral Run Solver / Copilot; warm sticky bar. |
| `ResultMeshPlaybackPanel.tsx` (hand) | Panel chrome → white card; metrics/legend → light (floating legend chip); **3D canvas `#020617` + field-value colormap kept dark** (correct "dark viewport in a light app"). |
| slice-1 (folded in) | SkeletonCard frozen-animation bug fix (defined the missing `skeleton-shimmer` keyframe); TabButton → `.tab-pill`; status-hue tokenization. |
| `backend/.../_viz_helpers.py` | 3 plot fallback HTML cards (no-FRD / render-failed / unavailable) re-themed warm-light (paper bg, ink text). `html.escape` XSS guards untouched. Requires a backend restart to serve (running process not killed per the no-kill rule). |

## Review arc (R0, 1 finding, fixed)

- **R0 — 1×P2 (REAL, fixed):** `index.css:43-52` — on the warm-light theme,
  `--warn-400` (`#b3791a` ≈ **3.7:1**) and `--success-500` (`#4a8a5e` ≈ **4.1:1**)
  fell below the 4.5:1 AA floor on white cards, yet warn/success **text** routes
  through them (CaseCompletenessCard, CohortDashboardPanel, ComplianceBadge).
  **FIX:** darkened `--warn-400` → `#8f6200` (5.4:1) and `--success-500` → `#3f7a52`
  (5.1:1); `--success-400` (`#5fa977`) retained for fills/icons only. (danger `#c5453b`
  = 4.88:1 and info `#2f6fdb` = 4.75:1 already pass — Codex correctly did not flag them.)
  **Verified + pinned:** added a status-text-on-white AA sweep to
  `Phase42_aesthetic_motion.test.tsx`, computed by the spec WCAG algorithm
  (`wcagContrast`, itself pinned against published WCAG examples in Phase 38 C) —
  authoritative for a contrast-value fix. A non-security P2 does not force an R1
  re-iteration (per ~/CLAUDE.md); the algorithmic test pin supersedes a re-eyeball.

  Earlier, an analogous accent issue was caught pre-review: white-on-`--accent`
  (`#bd5d3a`) was 4.36:1 → darkened to `#b3552f` (white-on-accent ≥ AA), also pinned.

## Verification

- `tsc --noEmit` clean; vitest **977 passed** (973 + 4 new status-AA assertions);
  eslint **70 problems = byte-identical to HEAD baseline (0 introduced)**;
  App.tsx **1498** (<1500 pin green, untouched).
- LIVE (preview, 1440×900): shell / sidebar / topbar / tabs / 3D result panel /
  expanded evidence-wall panels all warm-light + coherent (white cards, ink text,
  green success checks, light info callouts, coral active states). 0 agent
  problem-flags across all 43 migrated files; 2 diffs spot-read (CommandPalette
  nesting hierarchy + scrim-kept-dark; SectionFrame card→white) confirm fidelity.

## Residual

- The boot view's dark "no-FRD" plot card is the **stale running backend** serving
  pre-edit HTML (no `--reload`); the on-disk fix is correct + serves warm-light on
  the next backend restart. Not killed per the no-kill rule.
