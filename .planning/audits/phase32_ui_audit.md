# FM-04a Phase 32 — UI Audit · rubric v1.0

> Tier 1 / Tier 2 engineering candidate; not signed validation; not
> benchmark agreement. Scoring per `.planning/audits/RUBRIC.md`
> (v1.0). Phase 31 UI composite baseline = **89.0** (92/90/90/88/88/86).
>
> Phase 32 commits audited:
> - `1808c2f` Phase 32 blueprint (planning doc only).
> - `cda554d` Phase 32 A — FEA-only (convergence/Richardson on 3
>   more cases); zero UI surface change.
> - `682e8f6` Phase 32 B — `useAppUiMode` hook (104 LOC NEW at
>   `frontend/src/state/useAppUiMode.ts`). PARTIAL closure of Phase
>   31 honest gap #7 (App.tsx reducer debt). LOC NET ZERO on
>   App.tsx (1457 → 1457 verified by `wc -l`; 17+/17- swap).
>   Blueprint projected "1457 → 1200-1250" but full extraction is
>   multi-phase work; ~36 surfaces deferred to Phase 33+.
> - `ee11aca` Phase 32 C — Tier-2 polish bundle:
>   - C1 coord-readout advanced-gating (closes Phase 30 FINAL gap
>     #9 + Phase 31 UX honest gap #2).
>   - C2 companion entrance opacity fade (closes Phase 31 UX
>     honest gap #3) — 7th surface in the 200 ms motion vocabulary.
>   - C3 Compare-cuts basic-mode unlock (closes Phase 30 FINAL
>     gap #10 + Phase 31 UI honest gap #11).
>   - C4 Richardson r=2 spike — sibling artifact only; NOT a UI
>     surface change (FEA Dim 5 territory, audited elsewhere).
>
> Frontend tests: 755/755 pass (734 prior + 21 new in
> `Phase32C_polish_bundle.test.tsx`, +14 in
> `Phase32B_use_app_ui_mode.test.tsx`; 3 structural pin updates
> in Phase25C / Phase30B test files to track the registry swap).
> No Codex review, no charter trigger — all four slices remain
> within `frontend/src/components/`, `frontend/src/state/`,
> `frontend/src/uiMode.ts`, `frontend/test/`, and
> `golden_samples/*-candidate/` (HF1.7b carve-out PASS).

## Sub-axes

### 1. Micro-interaction polish + animation quality: **94/100**

- Evidence:
  - **7th surface in the 200 ms ease-out vocabulary** —
    `polishStyles.ts:103-105` defines `@keyframes
    fm04a-companion-mount-fade-in { from { opacity: 0 } to {
    opacity: 1 } }`; `polishStyles.ts:144-146` declares
    `.fm04a-companion-mount { animation: fm04a-companion-mount-
    fade-in 200ms ease-out; }`. The keyframe sits adjacent to
    `fm04a-restored-toast-fade-in` and `fm04a-advanced-mode-promo-
    fade-slide-in` — same vocabulary file, same 200 ms anchor.
    Vocabulary inventory: probe-row mount/unmount, restored-toast,
    advanced-mode-promo, chevron rotation, gradient-slider,
    viewport-flex-row layout-swap (Phase 31 D), and now
    companion-mount = 7 cohesive surfaces. Phase 31's "6th surface"
    claim is now 7.
  - **Applied at the correct mount boundary** —
    `CompanionViewport.tsx:113` puts `className={POLISH_CLASS_
    COMPANION_MOUNT}` on the outermost `<div data-testid=
    "companion-viewport">` so the fade fires on the FIRST mount
    only, NOT on every re-render. Pinned by
    `Phase32C_polish_bundle.test.tsx:117-126` (`root.className`
    match) and the keyframe-defined / 200 ms / ease-out pins at
    lines 77-98.
  - **reduce-motion guard extended** — `polishStyles.ts:194-203`
    @media block now lists `.${POLISH_CLASS_COMPANION_MOUNT}` in
    the `animation: none` suppression set. Pinned by
    `Phase32C_polish_bundle.test.tsx:102-111` (substring AFTER
    `prefers-reduced-motion: reduce` block matches
    `fm04a-companion-mount`). WCAG SC 2.3.3 holds.
  - **Opacity-only (no transform)** — the keyframe is `opacity 0
    → 1` ONLY, no `translateY` companion. Compositor-friendly,
    no layout thrash on mount, and (Dim 4 cross-tie) safer for
    SR users than the probe-row's `translateY(-6px)` lift.
  - HONEST GAP (toward 99): the 200 ms vocabulary is now broad
    (7 surfaces) but still single-curve (all ease-out, all 200 ms).
    Rubric 99 anchor requires spring physics / momentum-based
    gestures / haptic hooks — none shipped. Layout-swap motion
    is still Phase 31 D's gap/flex-basis; companion-mount opacity
    is additive not coordinated.
- Anchor: rubric 90 anchor was "chevron + accordion + promo
  entrance in same vocabulary" (Phase 29 B+C); Phase 31 D landed
  92 by adding layout-swap as a 6th surface. Phase 32 C adds
  companion-mount as a 7th surface — explicitly closing Phase 31's
  honest gap #3 ("Companion entrance fade NOT shipped"). The
  vocabulary breadth is now genuinely past the 90 anchor toward
  the 99 anchor's "cohesive across all 7 trust panels" bullet
  (motion is now cohesive across 7 component surfaces, though
  the rubric's 7 specifically named TRUST panels are not all
  animated). **Interpolated 94.** The +2 over Phase 31 reflects
  a real new motion surface — closing the SPECIFIC honest gap the
  Phase 31 audit named — held below 96 because the curve is still
  single (no spring/momentum).

### 2. Visual hierarchy + typography: **90/100**

- Evidence:
  - No new typography surface in Phase 32. C1 (coord-readout
    gating) HIDES an existing tooltip in basic mode rather than
    introducing new type; C2 (companion fade) is opacity-only with
    zero text or weight changes; C3 (Compare-cuts unlock) makes
    an existing toggle button visible to more users but the button
    itself is byte-identical.
  - The Phase 31 D companion-prefix marker in `ProbeListPanel.tsx`
    (0.62 rem / weight 600 / slate-400 @ 92% / monospace) — the
    Phase 31 hierarchy element — is now reachable from MORE users
    (basic-mode reviewers can drive the companion via C3); this
    is a "exposure breadth" change, not a "hierarchy depth" change.
  - C2 fade is structurally INVISIBLE in the typography axis (no
    new text node, no new font-size, no new weight, no new
    letter-spacing).
  - HONEST GAP: SectionFrame primitive still hasn't extended into
    Visual-tab slider/legend (Phase 29 carryover); no custom
    sans+mono type pairs; no responsive density breakpoints.
- Anchor: rubric 90 anchor (Phase 29 B SectionFrame + collapse
  summary in header). Phase 31 D landed 90 with the companion-
  prefix marker. Phase 32 makes no typography change.
  **Held at 90 verbatim.** Honest no-credit for "more users see
  the existing hierarchy" — exposure ≠ hierarchy lift.

### 3. Color system + tonal discipline: **90/100**

- Evidence:
  - Zero new color tokens in Phase 32. C2 fade is opacity-only
    (`from { opacity: 0 } to { opacity: 1 }` at
    `polishStyles.ts:103-105`); the companion's underlying color
    palette (slate-950 / slate-400 / accent borders inherited
    from CompanionViewport's existing inline styles) is byte-
    unchanged.
  - The Phase 31 D warning-toast token
    (`POLISH_CLASS_WARNING_TOAST` with `#fda4af` + rose-500 @ 55%
    border) is unchanged at `polishStyles.ts:128-133`. Phase 30
    FINAL gap #12 closure remains stable.
  - C1 gating REMOVES a colored surface (CoordReadoutTooltip's
    own color tokens) from basic-mode users — net effect: fewer
    palette consumers on the basic-mode canvas, not more or
    different.
  - HONEST GAP: still no dark/light theme toggle with token
    re-mapping (rubric 99-anchor).
- Anchor: rubric 90 anchor (Phase 29 B+ Phase 31 D's token
  warning-toast). Phase 32 ships ZERO new tokens, ZERO new
  colors. **Held at 90.** Honest no-credit for "removed a
  basic-mode color surface" — that's a cog-load improvement
  (UX axis), not a palette discipline lift.

### 4. Accessibility (a11y): **89/100**

- Evidence:
  - **Opacity-only fade is SR-safer than transform-based motion**
    — `polishStyles.ts:103-105` keyframe is `opacity 0 → 1` only.
    Screen readers attached to live regions don't get spurious
    "element moved" events that a `translateY` keyframe would
    fire on layout repaint. Tiny but real lift over Phase 31 D's
    probe-row motion vocabulary (which uses translateY).
  - **C1 coord-readout gating eliminates SR noise in basic mode**
    — `ResultMeshPlaybackPanel.tsx:795-798` wraps
    `<CoordReadoutTooltip info={hoverCoords} />` in
    `viewportMode === 'webgl' && shouldShowFeature(uiMode,
    'coord-readout')`. The Phase 30 C tooltip's `aria-live="off"`
    region (30 Hz position updates) no longer mounts in basic
    mode at all — SR users get a quieter default canvas. Phase
    30 FINAL gap #9 + Phase 31 UX honest gap #2 closed.
  - **reduce-motion universally honored** — `polishStyles.ts:
    194-203` @media block now lists 5 animation classes
    (probe-row mount, probe-row unmount, restored-toast,
    advanced-mode-promo, companion-mount). WCAG SC 2.3.3
    compliance extended to the new surface; pinned by
    `Phase32C_polish_bundle.test.tsx:102-111`.
  - **No new ARIA surfaces, no new focus traps** — C2 fade adds
    no role / aria-label; C1 gating doesn't change the
    CoordReadoutTooltip's own a11y attributes (Phase 30 C's
    aria-live="off" survives unchanged in advanced mode).
  - HONEST GAP: SR fixtures still absent (Phase 30-31 carry);
    keyboard-nav path through the 3-tier toast stack still
    undocumented; Phase 29 audit P29-1 `aria-describedby` on
    promo body STILL UNSHIPPED; no `aria-hidden="true"` on the
    companion-mount fade target (rare oversight: SR may read
    "companion viewport" twice as it fades in, though duration
    is short).
- Anchor: rubric 85 anchor (Phase 29 C focus-trap); Phase 31 D
  landed 88 via context-loss toast a11y + companion prefix
  aria-label. Phase 32 C adds opacity-only motion (SR-safer than
  transform) AND removes a basic-mode SR noise source
  (coord-readout 30 Hz updates). Two small wins. **Interpolated
  89.** Held below 92 (no SR fixtures; no keyboard-nav doc;
  aria-describedby still unshipped).

### 5. Industrial-software parity: **90/100**

- Evidence (KEY LIFT — closes Phase 30 FINAL gap #10 + Phase 31
  UI honest gap #11):
  - **Compare-cuts basic-mode unlock** —
    `ResultMeshPlaybackPanel.tsx:253` is now
    `const showCompanionViewportToggle = true;` UNCONDITIONALLY.
    Phase 30 B / Phase 31 used `shouldShowFeature(uiMode,
    'companion-viewport')` — that gate is REMOVED. The toggle
    button block at line 511 still has `&& viewportMode ===
    'webgl'` (correct safety — SVG fallback has no shared
    contract with companion). Pinned by:
    - `uiMode.ts:39-50` — `'companion-viewport'` REMOVED from
      `AdvancedFeatureId` TS union AND from
      `ADVANCED_FEATURE_IDS` runtime array. `coord-readout` took
      its place, count unchanged at 5 (Phase 25 C registry-size
      invariant holds).
    - `Phase32C_polish_bundle.test.tsx:130-147` — C3 block
      asserts the removal explicitly.
    - `Phase30B_companion_viewport.test.tsx` registry pin
      REWRITTEN to assert `'companion-viewport'` is NO LONGER
      in `ADVANCED_FEATURE_IDS`; "toggle button HIDDEN in basic
      mode" test INVERTED to "VISIBLE in basic mode" (structural
      pin update flagged in commit body — not a behavioral
      regression but the intended Phase 32 C surface change).
  - **2-quadrant Compare-cuts now matches Hyperworks / Abaqus
    parity for ALL reviewers** — not just advanced-mode users.
    Phase 31 D's companion node-pick wiring + `origin:
    'companion'` stamp (Phase 31 D
    `CompanionViewport.tsx:105`) eliminated the write-conflict
    risk that originally motivated the gate; with that safety
    rail in place, the gate becomes pure cog-load overhead. C3
    is the correct un-gating.
  - **Companion mount fade is the industrial-CAE polish
    convention** — Abaqus/CAE / Hyperworks new-panel opens
    fade in, not snap in. C2 brings the workbench in line.
  - HONEST SCOPE BRAKES still in effect (each holds 1-3 points
    back from 95):
    1. **No 4-quadrant default** — Abaqus / ANSYS Mechanical
       still set the industrial reference at 4-quadrant; Phase
       32 ships only 2-quadrant (now available to all reviewers).
    2. **No collapsible left/right rails** — rubric 88-anchor's
       third sub-bullet still unshipped (Phase 30-31 carry).
    3. **No drag-to-resize between primary + companion** — fixed
       50/50 split via `flex: 1`; Phase 31 honest gap #1 / Phase
       30 FINAL gap #13 still open.
    4. **No real-WebGL playwright E2E** — context-loss + coord-
       readout gating still verified only by unit-level pins.
- Anchor: rubric 88 anchor was Phase 31 ceiling; Phase 32 C closes
  the SPECIFIC named honest brake (Compare-cuts advanced-gating)
  that Phase 31 audit cited as "1-2 points held back from 90".
  The un-gating delivers exactly the lift the Phase 31 audit
  forecasted ("Lift Compare-cuts gating to basic-mode... Expected
  Dim 5 lift: 88 → 89-90"). **Interpolated 90.** The +2 reflects
  a CONCRETE Hyperworks-parity advance (every reviewer now gets
  2-quadrant on demand), held below 92 because three named
  brakes still hold (4-quadrant default / rails / drag-to-resize).

### 6. Density + reviewer ergonomics: **87/100**

- Evidence:
  - **useAppUiMode hook adds separation-of-concerns at App
    root** — `frontend/src/state/useAppUiMode.ts:82-110`
    (104 LOC NEW) owns the `appUiMode` + `appTourDismissedInSession`
    cluster with `{ state, actions }` shape; testable in isolation
    via `Phase32B_use_app_ui_mode.test.tsx` (14 tests).
    Maintainability lift (cog-load for future engineers reading
    App.tsx is slightly reduced because the uiMode logic is
    behind a named hook boundary, not inline `useState` +
    `useEffect` blocks).
  - **HONEST SCOPE COUNTER-EVIDENCE** — `wc -l frontend/src/
    App.tsx` returns **1457** lines, byte-identical LOC count
    to Phase 31 (commit `682e8f6` shows 17+/17- swap, net
    zero). The blueprint projected "1457 → 1200-1250" but
    Phase 32 B documents the honest scope reduction in the
    commit body: "App.tsx has ~38 useState/useEffect/useMemo
    surfaces. A full extraction would carry high regression
    risk in a single slice. Phase 32 B does the SMALLEST
    cohesive extraction." ~36 state surfaces remain in App.tsx
    deferred to Phase 33+. This is the honest scope-discipline
    pattern (same as Phase 31 A contact→heat and Phase 31 C
    cylinder-pv pivots) but the ergonomic claim must be muted:
    reviewers reading App.tsx still see the same wall.
  - **C2 companion fade reduces layout-swap cognitive jolt** —
    when basic-mode users toggle Compare-cuts on (now possible
    via C3), the new viewport fades in over 200 ms instead of
    appearing instantly. Adjacent to density ergonomics
    (softening cognitive transitions) but does not change
    information density per row / column.
  - **C1 gating reclaims basic-mode canvas real estate** — the
    coord-readout was a continuous 30 Hz overlay anchored to
    the primary viewport. In basic mode it now does not mount
    at all (`ResultMeshPlaybackPanel.tsx:795-798`), freeing a
    small but real region of the viewport from continuous
    visual noise. Density lift (less competing chrome on the
    primary canvas) for basic-mode reviewers specifically.
  - HONEST GAP: drag-to-resize between primary + companion
    STILL UNSHIPPED (Phase 30 FINAL gap #13 / Phase 31 honest
    gap #1); density toggle (compact/comfortable) UNSHIPPED;
    Phase 32 B's App.tsx LOC pickaxe didn't land. Rubric Dim 6
    92-anchor explicitly requires "drag-to-resize panels +
    density toggle (compact/comfortable)" — neither present.
- Anchor: rubric 85 anchor (Phase 29 B per-section collapse);
  Phase 30-31 held at 86. Phase 32 ships separation-of-concerns
  (useAppUiMode hook) + basic-mode canvas reclaim (C1 gating)
  + softened layout transition (C2 fade). Three small additive
  ergonomic lifts, but App.tsx is byte-identical LOC and no
  drag-to-resize / density toggle. **Interpolated 87.** The +1
  reflects the hook + canvas reclaim genuinely improving daily
  reviewer ergonomics. Held below 88-89 because the structural
  lifts (drag-to-resize / density toggle / App.tsx LOC) all
  remain Phase 33+ work.

---

## Composite UI score: **90.0/100**

(94 + 90 + 90 + 89 + 90 + 87) / 6 = 540 / 6 = **90.0**

## Phase-32 lift over Phase 31 UI (89.0): **+1.0**

Phase 31 FINAL projected Phase 32 UI lift roughly at
"+0.5 (Tier 2 polish bundle) ... putting Phase 32 at ~89.5".
The Phase 32 C bundle landed slightly stronger than the
projection because Dim 5 lifted +2 (full anchor 90 reached)
rather than the projected +1, and Dim 1 lifted +2 (94 vs
projected 92-93).

| Phase 31 honest gap | Phase 32 delivery | Outcome |
|---|---|---|
| #2 / Phase 30 gap #9 — coord-readout NOT advanced-gated | C1 closure: 'coord-readout' added to ADVANCED_FEATURE_IDS + render gated | **Dim 4 +1, Dim 6 +1** |
| #3 — Companion entrance fade NOT shipped | C2 closure: POLISH_CLASS_COMPANION_MOUNT + opacity 0→1 200ms ease-out | **Dim 1 +2, Dim 4 +0** |
| #11 / Phase 30 gap #10 — Compare-cuts advanced-mode-gated | C3 closure: companion-viewport REMOVED from ADVANCED_FEATURE_IDS; toggle visible unconditionally | **Dim 5 +2** |
| #7 — App.tsx reducer debt | B PARTIAL closure: useAppUiMode hook (NET ZERO LOC on App.tsx; 36 surfaces deferred) | **Dim 6 +1 modest** |

Net axis Δ: +2 (Dim 1) +0 (Dim 2) +0 (Dim 3) +1 (Dim 4) +2
(Dim 5) +1 (Dim 6) = +6 axis points / 6 axes = **+1.0
composite**. The +1.0 matches the Phase 31 audit's "+0.5"
forecast plus a +0.5 outperform on Dim 5 (full anchor 90
match) and Dim 1 (vocabulary breadth went from 6 → 7
surfaces, not just a polish increment).

Anti-gaming guards holding the score down from 92-93:
- Dim 2 / Dim 3 held FLAT — no typography or color token
  changes shipped; honest no-credit for exposure-only changes.
- Dim 5 held at 90 NOT 92: 4-quadrant default + rails +
  drag-to-resize still UNSHIPPED.
- Dim 6 held at 87 NOT 92: App.tsx LOC byte-identical;
  drag-to-resize + density toggle still UNSHIPPED.
- Dim 4 held at 89 NOT 92: no SR fixtures; no keyboard-nav
  doc for 3-tier toast stack; no `aria-hidden` on companion-
  mount fade target.
- Dim 1 held at 94 NOT 96: still single-curve (200 ms
  ease-out); no spring physics / momentum / haptics.

## Phase 32 honest gaps (Phase 33 forward look)

1. **Full App.tsx reducer extraction (Phase 31 gap #7 remainder).**
   Phase 32 B closed only the appUiMode cluster (9 LOC of state);
   ~36 surfaces remain inline (case selection / comparison cases
   / job tracking / materials / analysis flow / file upload /
   logs / palette / tabs). Each cluster needs a dedicated slice
   for safe extraction. Expected Dim 6 lift: 87 → ~90 over 2-3
   phases.

2. **Drag-to-resize between primary + companion + density
   toggle** (carryover from Phase 30 FINAL gap #13 / Phase 31
   honest gap #1). With Compare-cuts now in basic-mode (Phase
   32 C C3), the 50/50 fixed split is reached by MORE users —
   the lift becomes higher-priority. Expected Dim 6 lift: 87
   → 92 anchor exact (+5 axis ≈ +0.83 composite).

3. **4-quadrant default + collapsible left/right rails** (Phase
   30-31 carry toward 88-anchor full match → 99 trail). Rubric
   88-anchor has 3 sub-bullets; Phase 32 ships 2 of 3
   (multi-viewport split + measurement/coord). 4-quadrant
   default + rails are the unfinished third. Multi-phase
   architectural item (Milestone 5 by current roadmap).

4. **Spring physics / momentum on the motion vocabulary** —
   the 200 ms ease-out vocabulary is now 7 surfaces broad
   (Phase 32 C C2) but still single-curve. Rubric Dim 1
   99-anchor requires spring physics / momentum-based
   gestures / haptic feedback hooks. Touch / mobile parity
   not on near-term roadmap.

5. **SR fixtures + keyboard-nav documentation for 3-tier toast
   stack + companion-mount fade** (Phase 30-31 carry). With
   one more animated surface (companion mount) and one fewer
   basic-mode aria-live region (coord-readout gating), the
   SR/keyboard-nav coverage gap is shifting shape but still
   open. Expected Dim 4 lift: 89 → 92.

6. **`aria-hidden="true"` during companion-mount fade** (Phase
   32 C residual nit) — the 200 ms opacity fade is short but
   SR users may briefly hear the companion content read as it
   transitions. Minimal fix (≤5 LOC); pairs naturally with
   item 5.

7. **Real-WebGL playwright E2E** (Phase 26-32 perennial
   carryover) — context-loss + coord-readout gating + companion
   fade now all rely on unit-level pins. A real-browser E2E
   would unlock the integration anchor.

8. **Phase 32 C registry swap audit** — `companion-viewport`
   left ADVANCED_FEATURE_IDS and `coord-readout` joined it,
   keeping count at 5. The pattern is correct (Phase 25 C
   registry-size invariant preserved) but the swap pattern is
   load-bearing on downstream consumers (test pins, mode-toggle
   docs). Phase 33 should consider whether the registry should
   grow (add `coord-readout` WITHOUT removing
   `companion-viewport`, accept count=6) versus remain a
   fixed-size swap canvas.

> Phase 33 composite math (honest, conservative): Dim 6 87 →
> 90 (+0.5 composite from continued App.tsx slices + density
> toggle), Dim 5 90 → 92 (+0.33 from drag-to-resize), Dim 4
> 89 → 91 (+0.33 from SR fixtures + aria-hidden) ≈ +1.17
> composite, putting Phase 33 UI at ~91.2. The 90-92 UI band
> is increasingly the rubric "approaching the ~95 ethical
> ceiling" zone; Phase 33-35 should target ~91-93 max and
> reserve remaining points for external-validation surfaces
> (NOT under this contract). 4-quadrant default + rails
> remains a multi-phase architectural arc (Milestone 5),
> likely a Phase 35+ landing.

Tier 1 / Tier 2 engineering candidate; not signed validation;
not benchmark agreement. 16th consecutive Tier-2 phase under
the 绝对诚实客观 contract.
