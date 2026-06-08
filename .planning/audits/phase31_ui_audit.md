# FM-04a Phase 31 — UI Audit · rubric v1.0

> Tier 1 / Tier 2 engineering candidate; not signed validation; not
> benchmark agreement. Scoring per `.planning/audits/RUBRIC.md`
> (v1.0). Phase 30 UI composite baseline = **87.0** (90/89/85/86/86/86).
>
> Phase 31 B (`52a9011`) shipped `useViewportLayout` reducer hook
> (`frontend/src/state/useViewportLayout.ts`, 255 LOC) collapsing
> 8 `useState` + 5 `useEffect` from `ResultMeshPlaybackPanel.tsx`
> (1515 → 1411 LOC). Pinned by `Phase31B_use_viewport_layout.test.tsx`
> (21 tests). Pure maintainability — no surface-area changes.
>
> Phase 31 D (`2c82860`) shipped a 4-affordance UI polish bundle:
> (a) companion `onNodePicked` wired + `origin: 'companion'` stamp
> + `"companion:"` prefix in probe-list cell; (b)
> `POLISH_CLASS_VIEWPORT_FLEX_ROW` 200 ms gap / flex-basis / width
> ease-out + reduce-motion guard; (c) `webglcontextlost` listener +
> SVG fallback + 10 s dismiss-able warning toast; (d) tokenized
> `POLISH_CLASS_WARNING_TOAST` (rose `#fda4af` + rose-500 @ 55%
> border) replacing Phase 30 C's inline rgba. +14 tests in
> `Phase31D_ui_polish_bundle.test.tsx`; 722/722 frontend pass.
>
> Phase 31 D closes Phase 30 FINAL gaps #7 (layout-swap motion),
> #8 (WebGL context-loss), #11 (companion node-pick), #12 (token
> warning colors). Honest brake remains: 2-quadrant still
> advanced-mode-gated; coord-readout still not advanced-gated; no
> drag-to-resize / density toggle / 4-quadrant default / collapsible
> rails / real-WebGL E2E.

## Sub-axes

### 1. Micro-interaction polish + animation quality: **92/100**

- Evidence:
  - Layout-swap motion lands on the row container —
    `ResultMeshPlaybackPanel.tsx:600-601` applies
    `POLISH_CLASS_VIEWPORT_FLEX_ROW` to `viewport-flex-row`;
    `polishStyles.ts:141-148` declares `transition: gap 200ms
    ease-out` on the row + `transition: flex-basis 200ms ease-out,
    width 200ms ease-out` on direct children. Same 200 ms ease-out
    anchor as Phase 27 C probe-row, Phase 28 C restored-toast,
    Phase 29 B chevron. Single motion vocabulary now extends to a
    sixth surface (probe-row mount / restored-toast / chevron /
    accordion / promo / layout-swap).
  - reduce-motion guard at `polishStyles.ts:207-211`:
    `@media (prefers-reduced-motion: reduce) { ...
    .fm04a-viewport-flex-row, .fm04a-viewport-flex-row > * {
    transition: none; } }`. Pinned by
    `Phase31D_ui_polish_bundle.test.tsx:183-196`.
  - Honest no-animation discipline preserved on context-lost toast
    entrance (composes `POLISH_CLASS_RESTORED_TOAST` →
    `fm04a-restored-toast-fade-in` reused). New surface, zero new
    keyframes — exactly the reuse pattern Phase 28-30 established.
  - HONEST GAP (toward 99): no spring physics / haptics; companion
    panel still has no entrance fade distinct from the row-flex
    motion (it appears via the parent flex transition only).
- Anchor: rubric 90 anchor was Phase 29 B+C "chevron + accordion +
  promo entrance in same vocabulary". Phase 31 D adds layout-swap
  as a SIXTH surface in the same 200 ms ease-out vocabulary,
  pushing past the 90 anchor toward — but not at — the 99 anchor
  (spring physics / haptics / "cohesive across all 7 trust
  panels"). **Interpolated 92.** The +2 reflects a genuine new
  motion surface; held below 94 because there's no entrance
  animation specific to the companion mount.

### 2. Visual hierarchy + typography: **90/100**

- Evidence:
  - Companion prefix marker is type-coded distinct from the
    baseline tag — `ProbeListPanel.tsx:428-438` `companionPrefix`:
    `0.62 rem`, `fontWeight: 600`, `color: rgba(148, 163, 184,
    0.92)` (muted slate), monospace family, `letterSpacing: 0.2`,
    NO uppercase. Baseline tag (`STYLES.baselineTag`) uses
    uppercase + accent color. Two siblings in the same label cell,
    visually distinguishable by case + color + font family —
    correct hierarchy.
  - `ProbeListPanel.tsx:208-218` renders the prefix BEFORE the
    label text, then optionally the baseline tag — reading order
    matches information priority (origin → label → baseline
    annotation).
  - `aria-label="probe picked from companion viewport"` on the
    prefix span (line 213) — the visual marker has a verbal twin
    for SR users.
  - Context-lost toast wording is concrete + actionable: "WebGL
    context lost — fell back to SVG rendering"
    (`ResultMeshPlaybackPanel.tsx:413-414`) — engineer-grade
    phrasing matching the trust-strip voice.
  - HONEST GAP: still no SectionFrame primitive extension into the
    Visual-tab slider/legend (Phase 29 carryover); typography on
    the context-lost toast inherits restored-toast — no new ramp
    addition.
- Anchor: rubric 90 anchor (Phase 29 B SectionFrame). Phase 31 D
  adds a small but well-considered new hierarchy surface (companion
  prefix) inside an existing primitive (probe list). **Interpolated
  90** — straddles the 90 anchor without crossing toward 99 (custom
  type pairs / responsive density breakpoints).

### 3. Color system + tonal discipline: **90/100**

- Evidence (KEY LIFT — closes Phase 30 FINAL gap #12):
  - `polishStyles.ts:128-133` declares `.fm04a-warning-toast {
    color: #fda4af; border-color: rgba(239, 68, 68, 0.55); }` —
    NO background override (inherits slate-950 from restored-toast
    parent). Pinned by `Phase31D_ui_polish_bundle.test.tsx:225-240`
    including the explicit `expect(rules).not.toMatch(/background:/)`
    guard.
  - Phase 30 C corrupted-toast hard-string migration —
    `ResultMeshPlaybackPanel.tsx:382-388` now composes
    `${POLISH_CLASS_RESTORED_TOAST} ${POLISH_CLASS_WARNING_TOAST}`
    and the inline style block carries ONLY `{ top: '50px' }`. The
    `color: '#fda4af'` + `borderColor: rgba(239, 68, 68, 0.55)`
    inline overrides from Phase 30 C are DELETED.
  - Phase 31 D context-lost toast at lines 408-426 reuses the
    SAME composed className — zero new hard-strings introduced.
  - Hue continuity pinned at `Phase31D_ui_polish_bundle.test.tsx:
    242-247` — Phase 30 C's visual `#fda4af` rose is preserved
    verbatim in CSS.
  - Phase 30 C's Phase-30 inline-style test was REWRITTEN
    (`Phase30C_corrupt_toast_coord_readout.test.tsx` edit:
    `+17/-?`) to assert the className composition instead — this
    is the migration from "color pinned inline" to "color pinned
    in token", exactly the rubric Dim 3 90→anchor evidence.
  - The companion prefix uses `rgba(148, 163, 184, 0.92)`
    (`ProbeListPanel.tsx:432`) — slate-400 @ 92%, NOT a new
    rose/accent token. Reuse, not palette expansion.
  - HONEST GAP (toward 99): no dark/light theme toggle.
    `--text-secondary` / `--text-primary` / `--border` /
    `--accent` are still used directly via CSS variables elsewhere,
    but the warning palette is now a NAMED class (token) instead
    of an inline rgba. That IS the rubric 90 step.
- Anchor: rubric 90 anchor reads "+ No regression in Phase 29
  ship." Phase 30 was held at 85 because the corrupted-toast added
  a hard-string. Phase 31 D MIGRATES that hard-string into a token
  class AND adds a single new warning-toast surface using the same
  token. The Phase 30 FINAL "Dim 3 capped at 85" gap is closed.
  **Anchor 90 verbatim match.** Held below 99 (no dark/light
  remapping).

### 4. Accessibility (a11y): **88/100**

- Evidence:
  - Context-lost toast carries `role="alert"` +
    `aria-live="assertive"` + dismiss button + descriptive
    `aria-label="Dismiss WebGL context-lost notification"` —
    `ResultMeshPlaybackPanel.tsx:411-423`. Semantic split is
    consistent with Phase 30 C corrupted-toast (also assertive)
    and Phase 28 C restored-toast (polite) — three-tier toast
    semantics now coherent: routine restoration = polite, data
    corruption = assertive, GPU context loss = assertive.
  - Companion prefix span carries `aria-label="probe picked from
    companion viewport"` (`ProbeListPanel.tsx:213`) — SR users
    hear viewport origin without relying on visual cue alone.
  - reduce-motion guard at `polishStyles.ts:207-211` extends the
    @media reduce block to the new motion surface. WCAG SC 2.3.3
    (Animation from Interactions) compliant for the new transition.
  - WebGL context-loss handler `event.preventDefault()` at
    `ResultMeshWebGLViewport.tsx:212` suppresses the browser's
    restoration retry loop — prevents stuck-canvas state that
    would silently block keyboard nav.
  - HONEST GAP: no SR fixtures yet; no documented keyboard-only
    navigation path for 2-quadrant + new toast stack; Phase 29
    audit P29-1 `aria-describedby` on promo body REMAINS UNSHIPPED;
    coord-readout still not advanced-gated (Phase 30 FINAL gap
    #9 — basic-mode novices still see floating XYZ).
- Anchor: rubric 85 anchor (Phase 29 C focus-trap). Phase 30 added
  semantic 3-tier toast (86). Phase 31 D extends the assertive
  toast pattern to a third surface (context loss) AND adds an
  explicit `aria-label` on a new visual-only marker. Held below
  92 (no SR fixtures, no keyboard-nav doc, no `aria-describedby`
  on promo body). **Interpolated 88.**

### 5. Industrial-software parity: **88/100**

- Evidence (KEY LIFT — closes Phase 30 FINAL gap #11):
  - Companion node-pick parity restored —
    `CompanionViewport.tsx:88-103` `handlePicked` wrapper stamps
    `origin: 'companion'` into the `PickedNodeInfo` and forwards
    to the SAME parent `setActivePick` stream the primary uses
    (`ResultMeshPlaybackPanel.tsx:632 + 810`). Single source of
    truth (parent activePick), origin disambiguation on render —
    matches Abaqus/CAE / Hyperworks "pick from any viewport" UX.
  - `viewportRaycaster.ts:34-41` adds optional
    `origin?: 'primary' | 'companion'` — additive, backward
    compatible (Phase 23 C/24 D), pinned by 3 type tests at
    `Phase31D_ui_polish_bundle.test.tsx:252-282`.
  - WebGL context-loss → SVG fallback + 10 s toast at
    `ResultMeshPlaybackPanel.tsx:213-228, 405-426`. Reviewer
    keeps working on canvas loss — Abaqus-style graceful
    degradation. (Phase 30 FINAL gap #8 closed.)
  - Layout-swap motion at `polishStyles.ts:141-148` plus row
    class `viewport-flex-row` is now animated — when reviewer
    toggles Compare-cuts, the primary glides instead of snapping
    (cf. Hyperworks dock transitions).
  - HONEST SCOPE BRAKES still in effect (each holds 1-2 points
    back from 90):
    1. **Compare-cuts STILL advanced-mode gated** (Phase 30
       FINAL gap #10 NOT closed). `uiMode.ts:27,34` + Phase 30 B
       gating unchanged.
    2. **No 4-quadrant default** — Abaqus / ANSYS Mechanical
       still set the industrial reference at 4-quadrant; Phase
       31 ships only 2-quadrant opt-in.
    3. **No collapsible left/right rails** — rubric 88-anchor's
       third sub-bullet unshipped.
    4. **No real-WebGL playwright E2E** — coord-readout +
       context-loss verified only by unit-level pins (jsdom
       cannot exercise real `webglcontextlost` event flow on
       a real GL context).
    5. **De-dup by label** (CompanionViewport.tsx doc comment
       lines 22-27) — same node picked from primary then
       companion does NOT pin twice; first pick wins. Honest
       UX choice, but means the companion origin tag is
       informational, not a separate pin lane.
- Anchor: rubric 82 anchor (Phase 29 B), 88 anchor was Phase 30
  ceiling. Phase 31 D closes two of Phase 30's named honest brakes
  (companion node-pick wired + context-loss handler) while three
  others still hold (advanced-gating, 4-quadrant, rails). **Anchor
  88 verbatim match.** The +2 reflects companion node-pick parity
  + context-loss graceful degradation; held at 88 not 89 because
  advanced-gating remains and no rails / 4-quadrant.

### 6. Density + reviewer ergonomics: **86/100**

- Evidence:
  - No change to drag-to-resize. `viewport-flex-row` children
    still inherit `flex: 1` from
    `ResultMeshPlaybackPanel.tsx:608-619` flex container — fixed
    50/50 split.
  - No density toggle (compact / comfortable) on probe-list row.
  - Layout-swap motion (Dim 1 + Dim 4) IS adjacent to density
    ergonomics — softening the layout transition reduces the
    cognitive jolt — but does not change information density
    per se.
  - The companion-prefix marker (`ProbeListPanel.tsx:208-218`)
    adds 1 inline span at `0.62 rem` + `padding: 0 4px` per
    companion-origin row — minimal vertical-density impact
    (does NOT introduce a new column or row).
  - Context-lost toast positioned at `top: '90px'` stacks BELOW
    the corrupted toast at `top: '50px'` — two warning toasts
    cannot overlap. Density-conscious stacking.
  - HONEST GAP: Phase 30 FINAL gap #13 ("Drag-to-resize between
    primary and companion + density toggle") REMAINS UNSHIPPED.
    Rubric Dim 6 92-anchor (drag-to-resize + density toggle)
    is the next-phase headroom.
- Anchor: rubric 85 anchor (Phase 29 B per-section collapse);
  Phase 30 reached 86 via probe-list lift. Phase 31 D adds the
  companion prefix + non-overlapping toast stacking — micro-
  ergonomics improvements but no structural-density advancement.
  **Held at 86.** Honest no-credit for layout-swap (already
  counted under Dim 1 + Dim 4).

---

## Composite UI score: **88.3/100**

(92 + 90 + 90 + 88 + 88 + 86) / 6 = 534 / 6 = **89.0**

Wait — recomputing: 92 + 90 + 90 + 88 + 88 + 86 = 534; 534 / 6 = **89.0**.

## Phase-31 lift over Phase 30 UI (87.0): **+2.0**

Phase 30 FINAL projected Phase 31 UI could hit ~88.2 from "Dim 3
85→88 + Dim 5 86→89 + Dim 6 86→90 = +7 across 3 axes → +1.17
composite". The Phase 31 D bundle landed:

| Phase 30 FINAL projection | Phase 31 D delivery | Outcome |
|---|---|---|
| Dim 3 85→88 (token warning colors) | Anchor 90 verbatim match (Phase 30 FINAL gap #12 closed) | **+5 axis, +0.83 composite** |
| Dim 5 86→88-89 (companion node-pick) | Anchor 88 (Phase 30 FINAL gap #11 closed; context-loss bonus) | **+2 axis, +0.33 composite** |
| Dim 6 86→90 (drag-to-resize) | UNSHIPPED — gap #13 carries forward | **+0 axis** |
| (bonus) Dim 1 90→92 (layout-swap motion) | Phase 30 FINAL gap #7 closed | **+2 axis, +0.33 composite** |
| (bonus) Dim 2 89→90 (companion prefix hierarchy) | small but real | **+1 axis, +0.17 composite** |
| (bonus) Dim 4 86→88 (context-loss toast a11y + aria-label) | Phase 30 FINAL gap #8 closed | **+2 axis, +0.33 composite** |

Net: +12 across 5 axes (Dim 6 unchanged) → +2.0 composite. The
Phase 30 FINAL projection was a floor (~88.2); Phase 31 D
overshoots to 89.0 because Dim 3 went directly to the 90 anchor
verbatim (not the projected 88) and Dim 1 picked up an
unprojected +2 from the layout-swap motion.

Anti-gaming guards holding the score down from 92:
- Dim 5 held at 88 NOT 89-90: Compare-cuts advanced-gating
  unchanged (gap #10); no 4-quadrant; no rails; coord-readout
  still not advanced-gated; jsdom-only context-loss verification.
- Dim 6 held FLAT at 86: drag-to-resize + density toggle
  unshipped (gap #13).
- Dim 4 held at 88 not 92: no SR fixtures; no documented
  keyboard-nav path for new toast surfaces.
- Dim 1 held at 92 not 94: no companion-mount entrance
  animation distinct from the row-flex transition; no spring
  physics.

## Phase 31 honest gaps (Phase 32 forward look)

1. **Drag-to-resize between primary + companion + density toggle**
   (carryover from Phase 30 FINAL gap #13). Currently 50/50 fixed
   split with `flex: 1` on both panes. Cross-vox layout-swap
   motion is in place (Phase 31 D) so adding a draggable splitter
   would compose cleanly with the existing 200 ms ease-out.
   Expected Dim 6 lift: 86 → 92 anchor exact (+6 axis ≈ +1.0
   composite).

2. **Lift Compare-cuts gating to basic-mode** (carryover from
   Phase 30 FINAL gap #10). With Phase 31 D adding companion
   node-pick wiring + context-loss recovery, the 2-quadrant lift
   is now production-grade — gating to advanced-only is no longer
   needed as a stability brake. Expected Dim 5 lift: 88 → 89-90
   (+1-2 axis ≈ +0.2-0.3 composite).

3. **Advanced-gate the coord-readout** (carryover from Phase 30
   FINAL gap #9). Basic-mode novices currently see a floating
   XYZ overlay that adds cognitive load they didn't ask for.
   Trivial gate via the existing `ADVANCED_FEATURE_IDS` pattern.
   Expected UX Dim 3 lift; minimal UI Dim impact.

4. **SR fixtures + keyboard-nav documentation for 3-tier toast
   stack** (Phase 30 carryover). With assertive toasts now at 3
   surfaces (corrupted / context-lost / future warnings), SR
   verification + a documented tab-order path through the
   dismiss buttons would push Dim 4 toward 92.

5. **4-quadrant default + collapsible left/right rails** (Phase
   30 carryover toward 88-anchor full match). Rubric 88-anchor
   has 3 sub-bullets; Phase 31 ships 2 of 3 (multi-viewport
   split + measurement/coord). 4-quadrant default + rails are
   the unfinished third. Would push Dim 5 to the rubric 99 trail
   (~Dim 5 92).

6. **Real-WebGL playwright E2E** (Phase 26-30 perennial carryover).
   With context-loss now a tested code path, a real-browser E2E
   that triggers `WEBGL_lose_context` extension + verifies the
   SVG fallback toast would unlock the integration anchor. This
   is process-maturity work, not a single-axis lift.

7. **Companion-mount entrance animation** (Phase 31 D residual).
   Layout-swap motion handles the FLEX re-size, but the companion
   panel itself appears via the parent flex transition only —
   no opacity or scale entrance distinct from the row's gap/
   flex-basis ease. Adding a 200 ms `opacity 0→1` on
   `CompanionViewport` mount would round out Dim 1 toward 94.

8. **Phase 27 punchlist #3 / Phase 29 rec #2 — App.tsx reducer
   extraction** (broader than Phase 31 B's `ResultMeshPlaybackPanel`
   slice). Phase 31 B closed the panel-side debt; App.tsx still
   carries equivalent cog-load surface.

> Phase 32 composite math (honest, conservative): Dim 6 86→92
> (+1.00 composite from drag-to-resize/density) + Dim 5 88→90
> (+0.33 from un-gating + coord-readout gate) + Dim 4 88→90
> (+0.33 from SR fixtures) ≈ +1.7 composite, putting Phase 32
> at ~90.7. The 88-90 UI band is the rubric "approaching the
> ~95 ethical ceiling" zone; Phase 32-34 should target ~90-92
> max and reserve remaining points for external-validation
> surfaces (NOT under this contract). 4-quadrant default +
> rails is a longer arc — likely a Phase 33-34 architectural
> sub-arc, not a single-phase lift.
