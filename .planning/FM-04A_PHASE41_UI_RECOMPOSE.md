# FM-04a Phase 41 — demo-first UI recomposition (Claude/Codex aesthetic)

> Tier 0 sandbox/demo — experience-grade UI polish. NOT signed validation; NOT a
> composite-rubric phase. claim-tier discipline untouched (all "not signed
> validation" / tier-boundary copy preserved verbatim). 绝对诚实客观.
> Direction set by user 2026-05-29: "极其优秀的 UI 的 e2e 工作台（体验级，有一定
> 可靠性），先针对 demo", aesthetic anchor = Claude app / Codex app design language.

## Why this phase exists (vs the Tier-2 / composite track)

Live-app inspection (backend + frontend up) found the demo's core defect: **opening
a case led with an internal governance/compliance dashboard** ("Evidence-first
workbench state": CLAIM TIER / SOLVER TRUTH / BLUEPRINT TARGET / FM-01 milestone /
Linear-Notion copy), with the actual 3D result buried several steps down, dev-phase
labels ("PHASE 23 B") leaking to users, and a broken-looking empty left rail. The
product led with governance, not the wow.

## What landed (41.0 → 41.2)

- **41.0 baseline** — traced the case→solve→3D golden path on the live app;
  captured the 6 demo-killers (governance-first landing, jargon, CN/EN mix,
  negative empty-states, buried 3D, wasted left rail, label leaks).
- **41.1 design-token foundation** — `frontend/src/index.css` extended to a real
  modern-premium token system (neutral 12-step ramp, accent ramp, spacing/type/
  radius/elevation/motion scales, ambient depth) — all prior token + `.glass-*`
  names preserved (back-compat).
- **41.2 recomposition** (workflow-designed: 4 parallel design agents → 1
  synthesized conflict-free blueprint; main session implemented serially):
  1. token de-neon (`--accent-glow` 0.18→0.10, `--glow-accent` halo→ring+elev,
     tab de-glow) — calms the whole app.
  2. design primitives (`.surface-card` / `.heading-tight` / `.body-muted` /
     `.rise-in` / `.cb-*` / `.viewport-hero` / `.tab-pill` / `.vp-toggle`).
  3. **governance panel (OperatorStatusPanel) demoted to DOM-last** — case + 3D
     lead; trust center reachable by scroll (honesty info fully retained).
  4. dev-phase label leaks removed (`OnboardingTour`, `AdvancedModePromo`).
  5. grid rebalance 240→210px + `.tab-pill-bar`.
  6. **CaseBrowser → premium card landing hero** (token upgrade + hover-lift +
     sticky preview; all WCAG-asserted colors preserved).
  7. **ProjectManager dead-Tailwind FIX** — the left rail used Tailwind utility
     classes but the project has no Tailwind pipeline, so every class was inert
     (the "broken empty rail"); rewritten on real tokens + `.glass-sidebar` /
     `.case-item`.

## Codex review arc (ADR-026 risk-tier: cross-≥3-file)

- **R0** (`reports/codex_tool_reports/fm04a_phase41_2_ui_recompose_r0.md`):
  0 P1 / 0 BLOCKER, **2 × P2** (both real user-visible regressions):
  - P2-1: empty-project hint flashed during in-flight/failed fetch → **fixed**:
    gated on `loadStatus` ('loading'|'ready'|'error'); error shows a distinct hint.
  - P2-2: CSS `order:5` reorder left visual≠DOM focus/reading order (WCAG 2.4.3)
    → **fixed**: OperatorStatusPanel moved to genuine DOM-last; `order` hack removed.
  - Both fixes are verbatim Codex R0 suggestions (CLAUDE.md verbatim-exception).

## Verification (vs pre-implementation baseline)

| Gate | Baseline | After 41.1+41.2 (incl. R0 fixes) |
|---|---|---|
| vitest | 951 pass / 0 fail (65 files) | **951 pass / 0 fail** |
| `tsc -b` | 16 errors (pre-existing) | **16** (0 net new) |
| eslint | 70 problems (pre-existing) | re-check at commit |
| App.tsx LOC | 1495 / 1500 pin | **1492** |

## Honesty / governance guards held

- claim-tier boundary copy, Evidence panel, runner badge, GS review queue — all
  verbatim; only demoted/restyled, never deleted or fabricated.
- No solver-truth / schema / golden_samples / backend / WebGL-math touched.
- TabButton inline→class swap SKIPPED — `Phase22C` + `Phase38G` tests assert its
  inline styles; honoring the additive-test discipline (no test-threshold edits).
- All new motion wired into the single `prefers-reduced-motion: reduce` block
  (anti-gaming guard B:-1).

## Deferred to 41.3 (golden-path polish)

- viewport-hero step (premium 3D viewport chrome + `.vp-toggle` adoption) — needs
  an active-case render to verify + a vp-toggle test-coupling check.
- Run/solve affordance + result-reveal motion; refined loading/success states.
- (Optional) ADR-026 eval-fleet pass (industrial-ui-comparator is industrial-CAE
  anchored; a Claude/Codex-aesthetic rubric would fit this demo direction better).
