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

## What landed (41.3 — golden-path polish)

Workflow-designed (xhigh) → main-session serial implementation. UI-only diff
(`App.tsx` +6 / `ResultMeshPlaybackPanel.tsx` net −53 inline-style→class /
`Topbar.tsx` +8 / `index.css` +48). All 4 files = cross-≥3-file risk-tier → Codex.

1. **`animate-spin` BUG FIX** — the solving spinner used Tailwind's `animate-spin`,
   which is INERT in this repo (no Tailwind pipeline) → the Run-Solver spinner
   never rotated. Added a real `@keyframes fm04a-spin` + `.animate-spin` rule.
2. **`.run-solver-btn`** — glow + hover-lift + `[data-solving="true"]` pulse
   (`fm04a-solve-pulse`); wired into `Topbar` Run Solver button + `data-solving`.
3. **`.rise-in` entrance motion** — CaseBrowser wrapper / advisor row / report
   container (`App.tsx:1322` / `:1337` / `:1390`); reduced-motion-guarded.
4. **`.vp-toggle`** adoption — the 3 viewport toggles (compare-cuts / WebGL / SVG)
   in `ResultMeshPlaybackPanel` swapped inline styles → class + `aria-pressed`.
5. **`.viewport-hero` frame** + tab-pill kicker/heading restyle (verified present
   in DOM for an active case; `heading-tight` / `eyebrow` adopted).
6. **`.shimmer-active`** skeleton on the in-flight report placeholder.
7. TabButton `.tab-pill` swap SKIPPED (Phase22C/Phase38G assert its inline styles).

## ⚠️ Critical finding — the demo's 3D centerpiece does NOT render (NOT a 41.3 bug)

Live-app verification (GS-003 active, "3D Scene" tab) surfaced the dominant demo
blocker, which is **upstream of all UI polish**:

- **Backend gap:** the 3D viewport renders `result-mesh-error` (`canvasPresent:false`)
  — `result_mesh.json request failed (422)`. No `result_mesh.json` exists for a case
  until a solve produces one, and the earlier live solve leaked artifacts into the
  signed GS-001 dir + the `/visualize/result-mesh` + `/plot` routes 404/422.
- **Architecture gap:** the visual ("3D Scene") tab is a wall of **~19 governance/
  evidence panels** (cohort dashboard → substantiation → completeness → acceptance
  packet → convergence → reviewer bundle → trust score → drift narrative → …). The
  3D viewport sits at **scroll-y ≈ 11,880px — dead last.** 41.2 demoted the
  *OperatorStatusPanel*, but the entire visual tab still leads with governance, not
  the 3D result the user named the golden-path centerpiece.

41.1–41.3 correctly polished the **shell** (sidebar, topbar, case-browser hero,
tab pills, run-solver affordance, tokens) — all verified landed. But "案例→求解→
**结果可视化**" cannot pay off until: (a) the backend serves `result_mesh.json` for a
demo case, and (b) the visual tab is recomposed **3D-first** (governance panels →
a separate Evidence/Trust tab or scroll-behind). **Surfaced to user as the 41.4
decision.**

## Codex review arc (41.3 — ADR-026 risk-tier: cross-≥3-file)

- **R0** (`reports/codex_tool_reports/fm04a_phase41_3_ui_polish_r0.md`): **CLEAN /
  APPROVE — 0 P1 / 0 P2 / 0 P3.** "limited to UI styling … did not identify a
  discrete regression or correctness issue clearly introduced by this patch."
- **Relay:** primary 86gs gpt-5.4 xhigh **502'd mid-review** (Upstream unavailable,
  5 reconnects exhausted) → per CLAUDE.md relay-degrade rule, fell back to **CRS
  effort=high** (exit 0). Commit trailer: `codex_review_relay: crs (effort=high, fallback)`.

## Deferred / next (41.4 candidate)

- **Backend `result_mesh.json` for ≥1 demo case** (the real centerpiece unblocker).
- **Visual-tab 3D-first recomposition** (governance wall → Evidence/Trust tab).
- Cohort-dashboard column-overlap bug (CONVERGENCE bleeds into AUDIT) — pre-existing.
- (Optional) ADR-026 eval-fleet pass with a Claude/Codex-aesthetic rubric.
